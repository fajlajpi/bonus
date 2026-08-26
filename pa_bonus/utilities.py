# UTILITY FUNCTIONS
from functools import wraps

from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

MANAGER_GROUP_NAME = 'Managers'


def is_manager(user):
    """
    Return True if the user belongs to the Managers group.

    This is the single definition of "this user is a manager". Both the mixin
    used by class-based views and the decorator used by function-based views
    delegate to it, so the two entry points cannot drift apart.

    Superuser status is deliberately not a bypass. Access to client data is
    granted explicitly through group membership and nothing else.
    """
    return user.is_authenticated and user.groups.filter(name=MANAGER_GROUP_NAME).exists()


def manager_required(view_func):
    """
    Restrict a function-based view to members of the Managers group.

    Decorator counterpart to ManagerGroupRequiredMixin. Raises PermissionDenied
    (403) instead of redirecting, which matches the behaviour of the
    permission_required(..., raise_exception=True) decorators it replaced.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_manager(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped_view


class ManagerGroupRequiredMixin(UserPassesTestMixin):
    """Restricts access to users in the 'Managers' group."""

    def test_func(self):
        return is_manager(self.request.user)


class SalesRepRequiredMixin(UserPassesTestMixin):
    """Restricts access to users in the 'Sales Reps' group."""
    login_url = 'login'

    def test_func(self):
        return self.request.user.groups.filter(name='Sales Reps').exists()
    

from django.db.models import Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from pa_bonus.models import InvoiceBrandTurnover

def calculate_turnover_for_goal(user, brands, start_date, end_date):
    """
    Calculate turnover for a user and brands in date range.
    
    This is a utility function used by multiple views to calculate
    the total net turnover (invoices minus credit notes) for a specific
    user, set of brands, and date range.
    
    Args:
        user: User object
        brands: QuerySet or list of Brand objects
        start_date: Start date for calculation
        end_date: End date for calculation
        
    Returns:
        Decimal: Net turnover amount
    """
    # Get invoice turnover
    invoice_turnover = InvoiceBrandTurnover.objects.filter(
        invoice__client_number=user.user_number,
        invoice__invoice_date__gte=start_date,
        invoice__invoice_date__lt=end_date,
        invoice__invoice_type='INVOICE',
        brand__in=brands
    ).aggregate(
        total=Coalesce(Sum('amount'), Value(0, output_field=DecimalField()))
    )['total']
    
    # Get credit note turnover
    credit_turnover = InvoiceBrandTurnover.objects.filter(
        invoice__client_number=user.user_number,
        invoice__invoice_date__gte=start_date,
        invoice__invoice_date__lt=end_date,
        invoice__invoice_type='CREDIT_NOTE',
        brand__in=brands
    ).aggregate(
        total=Coalesce(Sum('amount'), Value(0, output_field=DecimalField()))
    )['total']
    
    return invoice_turnover - credit_turnover