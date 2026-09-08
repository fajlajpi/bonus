"""
Context processors making per-deployment settings available to every template.
"""
from django.conf import settings


def contact_info(request):
    """
    Add this deployment's identity, contact details and currency to the context.

    These were hardcoded to the Czech company. They now come from settings so
    that each country deployment shows its own details - see the DEPLOYMENT
    PROFILE section of bonus/settings/base.py.

    Currency is deliberately here rather than in the translation catalogue: it
    states what a point is actually worth, which is a business fact and not
    something a translator should be able to change.
    """
    return {
        'programme_name': settings.BONUS_PROGRAMME_NAME,
        'support_email': settings.SUPPORT_EMAIL,
        'company_name': settings.COMPANY_NAME,
        'company_phone': settings.COMPANY_PHONE,
        'company_street': settings.COMPANY_STREET,
        'company_city': settings.COMPANY_CITY,
        'company_zip': settings.COMPANY_ZIP,
        'pentaho_client_card_url': settings.PENTAHO_CLIENT_CARD_URL,
        'currency_code': settings.CURRENCY_CODE,
        'currency_symbol': settings.CURRENCY_SYMBOL,
    }


def features(request):
    """
    Expose the deployment's feature flags to templates as `features`.

    Lets a template hide whatever leads to a disabled feature:

        {% if features.extra_goals %} ... {% endif %}

    A missing key is falsey in the template language, so a typo hides the
    section rather than revealing something the deployment does not run.
    """
    return {'features': settings.FEATURES}
