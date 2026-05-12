"""
ABRA GEN ERP integration.

Provides a thin REST client and a high-level helper for submitting reward
redemption requests as Received Orders ("Objednávky přijaté") into ABRA GEN.

Configuration is read from Django settings:

    ABRA_BASE_URL       - e.g. "http://host:port/connection_alias"
    ABRA_USERNAME       - API user (must have "non-visual login" flag in ABRA)
    ABRA_TOKEN          - API token, used as the HTTP Basic password
    ABRA_DOCQUEUE_ID    - Document queue (packed GUID)
    ABRA_PERIOD_ID      - Accounting period (packed GUID, changes annually)
    ABRA_STORE_ID       - Warehouse (packed GUID)
    ABRA_DIVISION_ID    - Division (packed GUID)
    ABRA_VATRATE_ID     - VAT rate (packed GUID)

Public surface:

    AbraClient                  - low-level HTTP client with auth + session
    submit_reward_request(rr)   - end-to-end submission of a RewardRequest

All integration failures bubble up as subclasses of AbraError. Callers
should catch AbraError to surface failures to the user without needing to
distinguish HTTP errors from lookup failures.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable

import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# ABRA row types. We use these names instead of magic numbers at the call site.
ROWTYPE_TEXT_ONLY = 0          # text only, no price (unused here)
ROWTYPE_TEXT_PRICE = 1         # text + total price, no quantity
ROWTYPE_TEXT_PRICE_QTY = 2     # text + unit price + quantity
ROWTYPE_STORECARD = 3          # real storecard line

# The bonus point redemption storecard. The existing telemarketing export
# uses this same code. It MUST exist as a storecard in ABRA.
BONBOD_CODE = "BONBOD"

# VAT divisor for converting a point cost (which we treat as a VAT-inclusive
# CZK value) into a VAT-exclusive unit price.
VAT_DIVISOR = Decimal("1.21")

# Text preceding Rowtype 2 bonus name
ROWTYPE_TEXT_PRICE_PREFIX = "Bonusový program EC/AE - "


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AbraError(Exception):
    """Base class for all ABRA integration failures."""


class AbraConfigurationError(AbraError):
    """Raised when required Django settings are missing."""


class AbraNotFoundError(AbraError):
    """Raised when an expected record (firm, storecard) is missing in ABRA."""


class AbraRequestError(AbraError):
    """Raised on transport errors and non-2xx responses from the ABRA API."""


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class SubmissionResult:
    """
    The outcome of a successful submit_reward_request call.

    Carries the data needed both to update our RewardRequest record
    (id + displayname) and to show the manager what happened.
    """
    abra_order_id: str
    displayname: str
    # raw_response is kept for logging / debugging only - not for persistence.
    # repr=False keeps it out of accidental error messages.
    raw_response: dict = field(repr=False)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class AbraClient:
    """
    Thin wrapper around the ABRA GEN REST API.

    Holds a single requests.Session so repeated calls reuse the underlying
    TCP connection. One client per submission is plenty; do not bother
    caching at module level.
    """

    # 10 seconds matches the standalone test script. ABRA's lookups are
    # quick; if anything takes longer than this, something is wrong.
    DEFAULT_TIMEOUT = 10

    def __init__(self) -> None:
        base_url = getattr(settings, "ABRA_BASE_URL", "")
        username = getattr(settings, "ABRA_USERNAME", "")
        token = getattr(settings, "ABRA_TOKEN", "")

        if not base_url or not username or not token:
            raise AbraConfigurationError(
                "ABRA_BASE_URL, ABRA_USERNAME and ABRA_TOKEN must all be set."
            )

        # Strip trailing slash so endpoint joining is predictable.
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, token)

    # --- Internal HTTP helpers -------------------------------------------

    def _get(self, endpoint: str, params: dict[str, str]) -> Any:
        """GET an ABRA endpoint and return parsed JSON, raising on errors."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=self.DEFAULT_TIMEOUT)
        except requests.RequestException as exc:
            raise AbraRequestError(f"GET {endpoint} failed: {exc}") from exc

        if not response.ok:
            raise AbraRequestError(
                f"GET {endpoint} returned {response.status_code}: {response.text}"
            )
        return response.json()

    def _post(self, endpoint: str, payload: dict) -> dict:
        """POST JSON to an ABRA endpoint and return parsed JSON, raising on errors."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.post(url, json=payload, timeout=self.DEFAULT_TIMEOUT)
        except requests.RequestException as exc:
            raise AbraRequestError(f"POST {endpoint} failed: {exc}") from exc

        if not response.ok:
            raise AbraRequestError(
                f"POST {endpoint} returned {response.status_code}: {response.text}"
            )
        return response.json()

    # --- Lookups ---------------------------------------------------------

    def get_firm_by_code(self, code: str) -> dict | None:
        """
        Look up a firm (address book entry) by its `code` field.

        Returns the first matching record as a dict, or None when no record
        matches. We deliberately don't raise on "not found" here - the
        caller is in a better position to decide whether absence is fatal.
        """
        data = self._get("firms", params={
            "where": f"code eq '{code}'",
            "select": "id,code,name",
        })
        records = data if isinstance(data, list) else []
        return records[0] if records else None

    def get_storecards_by_codes(self, codes: Iterable[str]) -> dict[str, dict]:
        """
        Batched storecard lookup. Returns a dict keyed by storecard code.

        Codes not present in ABRA are simply absent from the returned dict
        - this is deliberate, because we want the caller to compare the
        requested set against the returned set and decide what to do
        about anything missing.

        Empty input yields an empty dict, not a wasted HTTP call.
        """
        codes_list = list(codes)
        if not codes_list:
            return {}

        # OR the requested codes together into a single query. ABRA's
        # `where` clause accepts arbitrarily many terms; we keep it
        # readable rather than worrying about query length.
        or_clauses = " or ".join(f"code eq '{c}'" for c in codes_list)

        data = self._get("storecards", params={
            "where": or_clauses,
            "select": "id,code,name",
        })
        records = data if isinstance(data, list) else []
        return {r["code"]: r for r in records}

    # --- Mutations -------------------------------------------------------

    def create_received_order(self, payload: dict) -> dict:
        """
        POST a Received Order and return the response body.

        Fills in the header IDs from settings if the caller hasn't already.
        This keeps call sites focused on the per-request data (firm, rows,
        description) without restating the boilerplate every time.
        """
        payload.setdefault("docqueue_id", settings.ABRA_DOCQUEUE_ID)
        payload.setdefault("period_id", settings.ABRA_PERIOD_ID)
        payload.setdefault("docdate$date", date.today().isoformat())
        return self._post("receivedorders", payload)


# ---------------------------------------------------------------------------
# High-level orchestration
# ---------------------------------------------------------------------------

def _round_excl_vat(point_cost: int) -> Decimal:
    """
    Convert a points value to a CZK price excluding 21% VAT.

    We use Decimal arithmetic with ROUND_HALF_UP to match what an accountant
    would expect on the cent. Floats here would drift; better safe.
    """
    value = Decimal(point_cost) / VAT_DIVISOR
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _build_rows_for_request(reward_request, storecards: dict[str, dict]) -> list[dict]:
    """
    Translate a RewardRequest's items into ABRA order rows.

    Per business rules:

    * Real ABRA storecards (Reward.is_in_abra_storecards = True)
      -> emit ONE rowtype-3 row, unitprice = 1, quantity = item.quantity.

    * Non-ABRA rewards (Reward.is_in_abra_storecards = False)
      -> emit TWO rows that cancel each other on the order total:
         (a) rowtype-2: text = reward.name, qty, unitprice = point_cost / 1.21
         (b) rowtype-1: text = "Bonusový program - sleva", totalprice = -(a)
         The pair leaves the order net at 0 while still showing both the
         reward and the discount on the document.

    * BONBOD line (always appended once at the end)
      -> rowtype-3 with quantity = reward_request.total_points (one unit
         per redeemed point), unitprice = 0, giving totalprice = 0. The
         BONBOD line functions as a counter of points consumed, not as a
         monetary entry on the order.

    Storecards needed for resolution must already be in the `storecards`
    dict (caller-validated). Looking them up here would defeat the point
    of batching.
    """
    store_id = settings.ABRA_STORE_ID
    division_id = settings.ABRA_DIVISION_ID
    vatrate_id = settings.ABRA_VATRATE_ID

    rows: list[dict] = []

    items = reward_request.rewardrequestitem_set.select_related("reward").filter(
        quantity__gt=0
    )

    for item in items:
        reward = item.reward

        if reward.is_in_abra_storecards:
            storecard = storecards[reward.abra_code]
            rows.append({
                "rowtype": ROWTYPE_STORECARD,
                "storecard_id": storecard["id"],
                "store_id": store_id,
                "division_id": division_id,
                "vatrate_id": vatrate_id,
                "quantity": item.quantity,
                "qunit": "ks",
                "unitprice": 1,
            })
        else:
            unit_excl_vat = _round_excl_vat(reward.point_cost)
            line_total = unit_excl_vat * item.quantity

            # Row (a): the named line at the VAT-excluded unit price
            rows.append({
                "rowtype": ROWTYPE_TEXT_PRICE_QTY,
                "text": ROWTYPE_TEXT_PRICE_PREFIX + reward.abra_code + " " + reward.name,
                "quantity": item.quantity,
                "qunit": "ks",
                "unitprice": float(unit_excl_vat),
                "division_id": division_id,
                "vatrate_id": vatrate_id,
            })
            # Row (b): the discount line that zeroes (a)'s contribution
            rows.append({
                "rowtype": ROWTYPE_TEXT_PRICE,
                "text": "Bonusový program - sleva",
                "totalprice": float(-line_total),
                "division_id": division_id,
                "vatrate_id": vatrate_id,
            })

    # The BONBOD point-redemption line.
    # quantity is the request's total points so the line reads as a counter
    # of points consumed. unitprice is 0 so the line contributes nothing to
    # the order total - the goal is to record the point count, not a price.
    bonbod = storecards[BONBOD_CODE]
    rows.append({
        "rowtype": ROWTYPE_STORECARD,
        "storecard_id": bonbod["id"],
        "store_id": store_id,
        "division_id": division_id,
        "vatrate_id": vatrate_id,
        "quantity": int(reward_request.total_points),
        "qunit": "ks",
        "totalprice": 1,
    })

    return rows


def submit_reward_request(reward_request) -> SubmissionResult:
    """
    Submit a RewardRequest to ABRA as a new Received Order.

    The full flow:

    1. Look up the firm by the user's `user_number`.
    2. Collect every ABRA code we need (storecards + BONBOD) and resolve
       them all in one batched call.
    3. If any code is missing from ABRA's response, abort. A partial order
       is much worse than no order - we never want to half-submit.
    4. Build the row list and POST the order.
    5. Return id + displayname for the caller to persist on the request.

    Raises AbraError (or subclass) on any failure. The caller is responsible
    for translating that into a user-facing message and for persisting the
    SubmissionResult on success.
    """
    client = AbraClient()

    # 1. Firm lookup
    user = reward_request.user
    firm = client.get_firm_by_code(user.user_number)
    if not firm:
        raise AbraNotFoundError(
            f"Customer code '{user.user_number}' not found in ABRA address book."
        )

    # 2. Determine the storecards we need
    items = reward_request.rewardrequestitem_set.select_related("reward").filter(
        quantity__gt=0
    )
    if not items.exists():
        raise AbraError("Reward request has no items with positive quantity.")

    required_codes: set[str] = {
        item.reward.abra_code
        for item in items
        if item.reward.is_in_abra_storecards
    }
    required_codes.add(BONBOD_CODE)

    # 3. Batched lookup + completeness check
    storecards = client.get_storecards_by_codes(required_codes)
    missing = sorted(required_codes - storecards.keys())
    if missing:
        raise AbraNotFoundError(
            f"Storecard(s) not found in ABRA: {', '.join(missing)}. "
            "Submission aborted; no order was created."
        )

    # 4. Build payload and post
    rows = _build_rows_for_request(reward_request, storecards)
    payload = {
        "firm_id": firm["id"],
        "description": f"Bonusový program č. {reward_request.id}",
        "rows": rows,
    }

    logger.info(
        "Submitting RewardRequest %s to ABRA (firm=%s, rows=%d)",
        reward_request.id, firm["id"], len(rows),
    )
    response = client.create_received_order(payload)

    # 5. Extract id + displayname
    abra_id = response.get("id")
    displayname = response.get("displayname", "")
    if not abra_id:
        # Defensive: ABRA returned 2xx but no id. Treat as failure so we
        # don't mark the request as submitted with bogus tracking data.
        raise AbraRequestError(
            f"ABRA accepted the order but returned no id. Response: {response}"
        )

    logger.info(
        "RewardRequest %s submitted to ABRA as %s (id=%s)",
        reward_request.id, displayname, abra_id,
    )
    return SubmissionResult(
        abra_order_id=abra_id,
        displayname=displayname,
        raw_response=response,
    )
