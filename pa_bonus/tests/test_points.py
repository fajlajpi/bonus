"""
Tests for the points expiration / allocation system.

These cover the parts that are easy to get subtly wrong: which credit a debit
draws from (soonest-to-expire FIFO), that remaining balances are derived
correctly, that cancelling a claim gives the points back, that an over-drawing
credit note goes negative rather than silently clamping, and that expiration
only touches genuinely-expired, still-unspent points.
"""
import pytest
from datetime import date

from pa_bonus.models import User, Brand, PointsTransaction, PointAllocation
from pa_bonus.services.points import allocate_debit, void_debit, expire_credits


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_user(number="100"):
    return User.objects.create(
        username=f"user{number}", user_number=number, user_phone="123456789"
    )


def credit(user, value, *, grant=date(2025, 1, 1), expires=None,
           status="CONFIRMED", brand=None, ttype="STANDARD_POINTS"):
    """Create a positive transaction with an explicit expiry (no auto-compute)."""
    return PointsTransaction.objects.create(
        user=user, value=value, date=grant, expires_at=expires,
        description="credit", type=ttype, status=status, brand=brand,
    )


def debit(user, value, *, day=date(2025, 6, 1), ttype="REWARD_CLAIM",
          status="CONFIRMED"):
    """Create a negative transaction (value passed as a positive magnitude)."""
    return PointsTransaction.objects.create(
        user=user, value=-value, date=day,
        description="debit", type=ttype, status=status,
    )


# ---------------------------------------------------------------------------
# Brand expiry policy
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestBrandExpiry:
    def test_expiry_is_end_of_month_n_months_later(self):
        brand = Brand.objects.create(name="B", prefix="B", points_validity_months=12)
        # Granted mid-month -> expires end of the month 12 months on.
        assert brand.expiry_for(date(2025, 3, 14)) == date(2026, 3, 31)

    def test_expiry_handles_short_months(self):
        brand = Brand.objects.create(name="B", prefix="B", points_validity_months=1)
        assert brand.expiry_for(date(2025, 1, 31)) == date(2025, 2, 28)

    def test_no_policy_means_no_expiry(self):
        brand = Brand.objects.create(name="B", prefix="B", points_validity_months=None)
        assert brand.expiry_for(date(2025, 1, 1)) is None


@pytest.mark.django_db
class TestExpiresAtAutoSet:
    def test_credit_with_brand_policy_gets_expiry(self):
        user = make_user()
        brand = Brand.objects.create(name="B", prefix="B", points_validity_months=6)
        txn = credit(user, 100, grant=date(2025, 1, 10), expires=None, brand=brand)
        txn.refresh_from_db()
        assert txn.expires_at == date(2025, 7, 31)

    def test_debit_never_gets_expiry(self):
        user = make_user()
        brand = Brand.objects.create(name="B", prefix="B", points_validity_months=6)
        # Negative value -> not a credit -> no expiry even with a branded policy.
        txn = PointsTransaction.objects.create(
            user=user, value=-50, date=date(2025, 1, 10), description="d",
            type="REWARD_CLAIM", status="CONFIRMED", brand=brand,
        )
        assert txn.expires_at is None

    def test_brand_without_policy_leaves_expiry_null(self):
        user = make_user()
        brand = Brand.objects.create(name="B", prefix="B", points_validity_months=None)
        txn = credit(user, 100, expires=None, brand=brand)
        assert txn.expires_at is None


# ---------------------------------------------------------------------------
# Allocation FIFO
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestAllocation:
    def test_draws_from_soonest_to_expire_first(self):
        user = make_user()
        # Older grant but expires LATER:
        long_lived = credit(user, 100, grant=date(2025, 1, 1), expires=date(2027, 1, 1))
        # Newer grant but expires SOONER -> should be consumed first.
        short_lived = credit(user, 100, grant=date(2025, 3, 1), expires=date(2026, 1, 1))

        d = debit(user, 60)
        allocated = allocate_debit(d)

        assert allocated == 60
        assert short_lived.remaining == 40
        assert long_lived.remaining == 100

    def test_never_expiring_credit_is_used_last(self):
        user = make_user()
        forever = credit(user, 100, grant=date(2024, 1, 1), expires=None)
        expiring = credit(user, 100, grant=date(2025, 1, 1), expires=date(2026, 1, 1))

        d = debit(user, 100)
        allocate_debit(d)

        assert expiring.remaining == 0
        assert forever.remaining == 100

    def test_allocation_spans_multiple_credits(self):
        user = make_user()
        c1 = credit(user, 50, expires=date(2026, 1, 1))
        c2 = credit(user, 50, expires=date(2026, 2, 1))

        d = debit(user, 70)
        allocate_debit(d)

        assert c1.remaining == 0
        assert c2.remaining == 30
        # The debit is fully allocated across both credits.
        assert sum(a.amount for a in d.allocations_in.all()) == 70

    def test_only_confirmed_credits_are_drawn(self):
        user = make_user()
        pending = credit(user, 100, expires=date(2026, 1, 1), status="PENDING")
        confirmed = credit(user, 100, expires=date(2026, 2, 1), status="CONFIRMED")

        d = debit(user, 80)
        allocate_debit(d)

        assert pending.remaining == 100  # untouched
        assert confirmed.remaining == 20

    def test_balance_reconciles_with_remaining(self):
        user = make_user()
        credit(user, 100, expires=date(2026, 1, 1))
        credit(user, 100, expires=date(2026, 2, 1))
        d = debit(user, 120)
        allocate_debit(d)

        confirmed_credits = PointsTransaction.objects.filter(
            user=user, status="CONFIRMED", value__gt=0
        )
        remaining_total = sum(c.remaining for c in confirmed_credits)
        # No over-draw, so signed-value balance equals sum of remaining.
        assert user.get_balance() == 80
        assert remaining_total == 80


# ---------------------------------------------------------------------------
# Credit-note over-draw goes negative
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestOverdraw:
    def test_credit_note_overdraw_goes_negative_and_partially_allocates(self):
        user = make_user()
        c = credit(user, 100, expires=date(2026, 1, 1))

        # A credit note larger than the available balance.
        note = debit(user, 150, ttype="CREDIT_NOTE_ADJUST")
        allocated = allocate_debit(note)

        # Only 100 could be allocated; the rest is left uncovered on purpose.
        assert allocated == 100
        assert c.remaining == 0
        assert sum(a.amount for a in note.allocations_in.all()) == 100
        # Balance reflects the full -150, so it goes negative -> visible.
        assert user.get_balance() == -50


# ---------------------------------------------------------------------------
# Void / reallocation (cancel & edit a reward request)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestVoidAndReallocate:
    def test_void_returns_points_to_credits(self):
        user = make_user()
        c = credit(user, 100, expires=date(2026, 1, 1))
        d = debit(user, 60)
        allocate_debit(d)
        assert c.remaining == 40

        void_debit(d)

        d.refresh_from_db()
        assert d.status == "CANCELLED"
        assert c.remaining == 100
        assert PointAllocation.objects.filter(debit=d).count() == 0
        assert user.get_balance() == 100

    def test_reallocate_clears_old_allocations(self):
        user = make_user()
        c1 = credit(user, 100, expires=date(2026, 1, 1))
        c2 = credit(user, 100, expires=date(2026, 2, 1))
        d = debit(user, 50)
        allocate_debit(d)
        assert c1.remaining == 50

        # Simulate the request total growing; allocate again.
        d.value = -150
        d.save(update_fields=["value"])
        allocate_debit(d)

        assert c1.remaining == 0
        assert c2.remaining == 50
        assert sum(a.amount for a in d.allocations_in.all()) == 150

    def test_reactivated_claim_draws_from_currently_available_credits(self):
        user = make_user()
        c_old = credit(user, 100, expires=date(2026, 1, 1))
        d = debit(user, 100)
        allocate_debit(d)
        assert c_old.remaining == 0

        # Claim cancelled -> points returned.
        void_debit(d)
        assert c_old.remaining == 100

        # A newer credit arrives, then the claim is reactivated.
        c_new = credit(user, 100, grant=date(2025, 4, 1), expires=date(2025, 12, 1))
        d.status = "CONFIRMED"
        d.save(update_fields=["status"])
        allocate_debit(d)

        # Soonest-to-expire is c_new now, so it should be drawn first.
        assert c_new.remaining == 0
        assert c_old.remaining == 100


# ---------------------------------------------------------------------------
# Expiration
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestExpiration:
    def test_expires_only_past_due_unspent_points(self):
        user = make_user()
        expired_credit = credit(user, 100, expires=date(2025, 1, 31))
        future_credit = credit(user, 100, expires=date(2099, 1, 31))

        result = expire_credits(as_of=date(2025, 6, 1))

        assert len(result) == 1
        assert result[0][0].id == expired_credit.id
        assert result[0][1] == 100
        # An EXPIRATION debit was created and drew the remaining 100.
        assert expired_credit.remaining == 0
        assert future_credit.remaining == 100
        assert user.get_balance() == 100
        exp = PointsTransaction.objects.get(user=user, type="EXPIRATION")
        assert exp.value == -100
        assert exp.date == date(2025, 1, 31)

    def test_only_unspent_portion_expires(self):
        user = make_user()
        c = credit(user, 100, expires=date(2025, 1, 31))
        # 70 already spent before expiry.
        spend = debit(user, 70, day=date(2025, 1, 10))
        allocate_debit(spend)
        assert c.remaining == 30

        expire_credits(as_of=date(2025, 6, 1))

        assert c.remaining == 0
        exp = PointsTransaction.objects.get(user=user, type="EXPIRATION")
        assert exp.value == -30
        assert user.get_balance() == 0

    def test_expiration_is_idempotent(self):
        user = make_user()
        credit(user, 100, expires=date(2025, 1, 31))

        first = expire_credits(as_of=date(2025, 6, 1))
        second = expire_credits(as_of=date(2025, 6, 1))

        assert len(first) == 1
        assert len(second) == 0
        assert PointsTransaction.objects.filter(user=user, type="EXPIRATION").count() == 1

    def test_dry_run_writes_nothing(self):
        user = make_user()
        c = credit(user, 100, expires=date(2025, 1, 31))

        result = expire_credits(as_of=date(2025, 6, 1), dry_run=True)

        assert len(result) == 1
        assert c.remaining == 100  # untouched
        assert PointsTransaction.objects.filter(user=user, type="EXPIRATION").count() == 0

    def test_never_expiring_credit_is_left_alone(self):
        user = make_user()
        c = credit(user, 100, expires=None)
        result = expire_credits(as_of=date(2099, 1, 1))
        assert result == []
        assert c.remaining == 100
