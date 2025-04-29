from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.views.generic import ListView, View
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count
from django.db import transaction
import logging
from pa_bonus.forms import FileUploadForm
from pa_bonus.tasks import process_uploaded_file
from pa_bonus.models import FileUpload, Reward, RewardRequest, RewardRequestItem, PointsTransaction
from pa_bonus.models import EmailNotification, User, Region, UserContract, InvoiceBrandTurnover, Brand
from pa_bonus.utilities import ManagerGroupRequiredMixin

from pa_bonus.exports import generate_telemarketing_export

import datetime
from dateutil.relativedelta import relativedelta

# Create your views here.

logger = logging.getLogger(__name__)

class ManagerDashboardView(ManagerGroupRequiredMixin, View):
    """
    Main dashboard view for managers.
    
    Provides an overview of system status and links to manager functions.
    """
    template_name = 'manager/dashboard.html'
    
    def get(self, request):
        # System-wide points statistics
        from django.db.models import Sum, Count, Q, F, Value
        from django.db.models.functions import Coalesce
        
        # 1. Total points summary
        points_summary = PointsTransaction.objects.filter(
            status__in=['PENDING', 'CONFIRMED']
        ).values('status').annotate(
            total=Coalesce(Sum('value'), Value(0))
        ).order_by('status')
        
        # Convert to a dictionary for easier access in template
        points_data = {
            'PENDING': 0,
            'CONFIRMED': 0,
        }
        for entry in points_summary:
            points_data[entry['status']] = entry['total']
            
        # 2. Reward requests statistics
        request_stats = RewardRequest.objects.filter(
            status__in=['PENDING', 'ACCEPTED']
        ).values('status').annotate(
            count=Count('id'),
            total_points=Coalesce(Sum('total_points'), Value(0))
        ).order_by('status')
        
        # Convert to dictionary
        request_data = {
            'PENDING': {'count': 0, 'total_points': 0},
            'ACCEPTED': {'count': 0, 'total_points': 0},
        }
        for entry in request_stats:
            request_data[entry['status']] = {
                'count': entry['count'],
                'total_points': entry['total_points']
            }
            
        # 3. Top 10 clients by available points
        top_clients = User.objects.annotate(
            available_points=Coalesce(
                Sum('pointstransaction__value', 
                    filter=Q(pointstransaction__status='CONFIRMED')),
                Value(0)
            ),
            pending_points=Coalesce(
                Sum('pointstransaction__value', 
                    filter=Q(pointstransaction__status='PENDING')),
                Value(0)
            )
        ).filter(
            available_points__gt=0
        ).order_by('-available_points')[:10]
        
        context = {
            'points_data': points_data,
            'request_data': request_data,
            'top_clients': top_clients,
        }
        
        return render(request, self.template_name, context)
    
    
@permission_required('pa_bonus.can_manage', raise_exception=True)
def upload_file(request):
    """
    Handles file uploads for processing invoice data.

    This view allows users with the correct permission to upload invoice data files.
    After a successful upload, the file is processed accordingly.

    Args:
        request (HttpRequest): The HTTP request object containing the file upload.

    Returns:
        HttpResponse: Renders the upload form (GET) or redirects to the upload history (POST).
    """
    if request.method == "POST":
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            upload = form.save(commit=False)
            upload.uploaded_by = request.user
            upload.save()

            # Process the uploaded file
            try:
                process_uploaded_file(upload.id)
                messages.success(
                    request, 
                    'File uploaded successfully and is being processed'
                )
            except Exception as e:
                messages.error(
                    request, 
                    f'Error processing file: {str(e)}'
                )

            return redirect('upload_history')
    else:
        form = FileUploadForm()
    
    return render(request, 'upload.html', {'form': form})

@permission_required('pa_bonus.can_manage', raise_exception=True)
def upload_history(request):
    """
    Displays the history of uploaded files.

    This view lists all uploaded files in the order of uploading.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: Renders the upload history template with the list of uploads.
    """
    uploads = FileUpload.objects.all().order_by('-uploaded_at')
    return render(request, 'upload_history.html', {'uploads': uploads})

class ManagerRewardRequestListView(ManagerGroupRequiredMixin, ListView):
    """
    (Managers Only) Lists the current reward requests in the system.

    Attributes:
        template_name (str): Name of template to render
        context_object_name (str): Name of the context object we're working with in the ListView
        paginate_by (int): Number of requests per page
    """
    template_name = 'manager/reward_requests_list.html'
    context_object_name = 'reward_requests'
    paginate_by = 25

    def get_queryset(self):
        """
        Get the data (queryset) to populate the ListView with. With filtering by 'status'.
        """
        queryset = RewardRequest.objects.select_related('user').order_by('-requested_at')
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset
    
class ManagerRewardRequestDetailView(ManagerGroupRequiredMixin, View):
    """
    (Managers Only) Detail of Reward Request with editing and confirming capability.
    """
    template_name = 'manager/reward_request_detail.html'

    def get(self, request, pk):
        reward_request = get_object_or_404(RewardRequest, pk=pk)
        items = reward_request.rewardrequestitem_set.select_related('reward')
        item_quantities = {
            item.reward.id: item.quantity for item in items
        }
        all_rewards = Reward.objects.filter(is_active=True)
        user_balance = reward_request.user.get_balance()
        return render(request, self.template_name, {
            'request_obj': reward_request,
            'items': items,
            'item_quantities': item_quantities,
            'all_rewards': all_rewards,
            'user_balance': user_balance,
        })

    @transaction.atomic
    def post(self, request, pk):
        reward_request = get_object_or_404(RewardRequest, pk=pk)
        old_status = reward_request.status
        
        # Update the reward request items 
        self._update_reward_items(reward_request, request.POST)
        
        # Update the customer note
        customer_note = request.POST.get('customer_note', '')
        reward_request.note = customer_note
        
        # Update the request status and description
        new_status = request.POST.get('status')
        reward_request.description = request.POST.get('manager_message', '')
        reward_request.status = new_status
        reward_request.save()
        
        # Update the point transaction to match the current state
        self._update_point_transaction(reward_request, old_status, new_status)
        
        messages.success(request, f"Request {reward_request.pk} updated.")
        return redirect('manager_reward_requests')
    
    def _update_reward_items(self, reward_request, post_data):
        """Update the reward request items from form data."""
        # Clear existing items
        reward_request.rewardrequestitem_set.all().delete()
        
        # Add new items
        for reward in Reward.objects.filter(is_active=True):
            field_name = f'reward_{reward.id}'
            qty = post_data.get(field_name)
            if qty and qty.isdigit() and int(qty) > 0:
                RewardRequestItem.objects.create(
                    reward_request=reward_request,
                    reward=reward,
                    quantity=int(qty)
                )
    
    def _update_point_transaction(self, reward_request, old_status, new_status):
        """Update the point transaction to match the current state of the request."""
        transaction = self._get_reward_transaction(reward_request)
        if not transaction:
            return
        
        # If request is rejected/cancelled, cancel the transaction
        if new_status in ['REJECTED', 'CANCELLED']:
            transaction.status = 'CANCELLED'
            transaction.save()
        
        # If request was rejected/cancelled but is now active, reactivate transaction
        elif old_status in ['REJECTED', 'CANCELLED'] and new_status not in ['REJECTED', 'CANCELLED']:
            transaction.status = 'CONFIRMED'
            transaction.save()
        
        # In all cases, ensure the transaction amount matches the request total
        if transaction.status == 'CONFIRMED':
            transaction.value = -reward_request.total_points
            transaction.save()
    
    def _get_reward_transaction(self, reward_request):
        """Get the associated reward claim transaction."""
        try:
            return PointsTransaction.objects.get(
                reward_request=reward_request,
                type='REWARD_CLAIM'
            )
        except PointsTransaction.DoesNotExist:
            logger.warning(f"No transaction found for reward request {reward_request.id}")
            return None
        except PointsTransaction.MultipleObjectsReturned:
            logger.error(f"Multiple transactions found for reward request {reward_request.id}")
            messages.warning(self.request, "Multiple transactions found for this request. Please check manually.")
            return None

        
class ExportTelemarketingFileView(ManagerGroupRequiredMixin, View):
    """
    Export a telemarketing file for a specific reward request
    """
    def get(self, request, pk):
        output = generate_telemarketing_export(pk)
        
        if output is None:
            messages.error(request, "Reward request not found or not in ACCEPTED status.")
            return redirect('manager_reward_requests')
        
        # Prepare response
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=reward_request_{pk}_{timezone.now().strftime("%Y%m%d")}.xlsx'
        
        messages.success(request, f"Reward request {pk} has been exported and marked as FINISHED.")
        return response


class TransactionApprovalView(ManagerGroupRequiredMixin, View):
    """
    View for managers to approve pending transactions based on month/year.
    
    Allows managers to see and approve transactions that are due for approval
    (those from three months ago) in a simple interface.
    """
    template_name = 'manager/transaction_approval.html'
    
    def get(self, request):
        """
        Display the approval form and optionally show transactions for a selected month.
        """
        today = timezone.now().date()
        
        # Default to showing transactions from 3 months ago
        default_approval_date = today - relativedelta(months=3)
        default_year = default_approval_date.year
        default_month = default_approval_date.month
        
        # Get user-selected month and year if provided
        selected_year = int(request.GET.get('year', default_year))
        selected_month = int(request.GET.get('month', default_month))
        
        # Generate a list of years (from 2 years ago to current year)
        available_years = range(today.year - 2, today.year + 1)
        
        # Get month range for filtering
        start_date = datetime.date(selected_year, selected_month, 1)
        if selected_month == 12:
            end_date = datetime.date(selected_year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_date = datetime.date(selected_year, selected_month + 1, 1) - datetime.timedelta(days=1)
        
        # Get pending transactions for the selected month
        pending_transactions = PointsTransaction.objects.filter(
            status='PENDING',
            date__gte=start_date,
            date__lte=end_date
        ).select_related('user', 'brand')
        
        # Get statistics for the selected month
        stats = pending_transactions.aggregate(
            total_transactions=Count('id'),
            total_points=Sum('value')
        )
        
        # Determine if we should highlight this month for approval
        # (if it's the month that is due for approval based on the 3-month rule)
        is_approval_month = (
            selected_year == default_approval_date.year and 
            selected_month == default_approval_date.month
        )
        
        # Get available months (1-12)
        available_months = [(i, datetime.date(2000, i, 1).strftime('%B')) for i in range(1, 13)]
        
        context = {
            'pending_transactions': pending_transactions,
            'stats': stats,
            'selected_year': selected_year,
            'selected_month': selected_month,
            'month_name': datetime.date(selected_year, selected_month, 1).strftime('%B'),
            'available_years': available_years,
            'available_months': available_months,
            'is_approval_month': is_approval_month,
            'start_date': start_date,
            'end_date': end_date,
        }
        
        return render(request, self.template_name, context)
    
    @transaction.atomic
    def post(self, request):
        """
        Process the approval of transactions for the selected month.
        """
        selected_year = int(request.POST.get('year'))
        selected_month = int(request.POST.get('month'))
        
        # Get month range for filtering
        start_date = datetime.date(selected_year, selected_month, 1)
        if selected_month == 12:
            end_date = datetime.date(selected_year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_date = datetime.date(selected_year, selected_month + 1, 1) - datetime.timedelta(days=1)
        
        # Update pending transactions to confirmed
        pending_transactions = PointsTransaction.objects.filter(
            status='PENDING',
            date__gte=start_date,
            date__lte=end_date
        )
        
        # Count before updating for the message
        transaction_count = pending_transactions.count()
        points_total = pending_transactions.aggregate(total=Sum('value'))['total'] or 0
        
        # Update the transactions
        pending_transactions.update(status='CONFIRMED')
        
        # Schedule email notifications for each user with confirmed transactions
        self.schedule_email_notifications(pending_transactions)
        
        # Success message
        messages.success(
            request, 
            f"Successfully approved {transaction_count} transactions totaling {points_total} points."
        )
        
        # Redirect back to the form
        return redirect('transaction_approval')
    
    def schedule_email_notifications(self, transactions):
        """
        Schedule email notifications for users whose transactions were approved.
        
        Creates EmailNotification records for each user who had transactions approved.
        These will be processed by a separate task/process.
        
        Args:
            transactions: QuerySet of approved transactions
        """
        # Get unique users who had transactions approved
        user_ids = transactions.values_list('user_id', flat=True).distinct()
        
        # For each user, create a notification
        for user_id in user_ids:
            # Get the user's transactions that were just approved
            user_transactions = transactions.filter(user_id=user_id)
            user = user_transactions.first().user
            
            # Calculate total points
            total_points = user_transactions.aggregate(total=Sum('value'))['total'] or 0
            
            # Create notification message
            subject = "Your bonus points have been confirmed!"
            message = f"""
Dear {user.first_name} {user.last_name},

We are pleased to inform you that your transactions for {user_transactions.first().date.strftime('%B %Y')} 
have been confirmed, adding {total_points} points to your account.

Your current point balance is now: {user.get_balance()} points.

You can log in to the Bonus Program portal to view these transactions and explore 
available rewards.

Thank you for your business!

Best regards,
The Bonus Program Team
            """
            
            # Create the notification record
            EmailNotification.objects.create(
                user=user,
                subject=subject,
                message=message,
                status='PENDING'
            )


class SMSExportView(ManagerGroupRequiredMixin, View):
    """
    Generates a CSV file for SMS notifications to clients.
    
    This view allows managers to generate a CSV file in the format required by smsbrana.cz
    to send monthly SMS notifications to clients about their point balances.
    """
    template_name = 'manager/sms_export.html'
    
    def get(self, request):
        """
        Display the SMS export form with options.
        """
        # Get all regions for the dropdown
        regions = Region.objects.filter(is_active=True).order_by('name')
        
        context = {
            'regions': regions
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        """
        Generate and return the SMS export CSV file.
        """
        import csv
        from django.http import HttpResponse
        from django.utils import timezone
        
        # Create the HttpResponse object with CSV header
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="sms_export_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
        
        # Create CSV writer with semicolon delimiter
        writer = csv.writer(response, delimiter=';')
        
        # Get active users with phone numbers
        users = User.objects.filter(is_active=True).exclude(user_phone='')
        
        # Filter by region if specified
        region_id = request.POST.get('region')
        if region_id and region_id != 'all':
            users = users.filter(region_id=region_id)
        
        # Set minimum points threshold
        min_points = request.POST.get('min_points', 0)
        try:
            min_points = int(min_points)
        except ValueError:
            min_points = 0
        
        # Count for reporting
        total_sms = 0
        
        # Write SMS data rows
        for user in users:
            # Get user balance
            balance = user.get_balance()
            
            # Skip users with balance below minimum (if specified)
            if balance < min_points:
                continue
            
            # Format phone number correctly
            phone = user.user_phone.strip()
            if not phone.startswith('+'):
                # Add Czech prefix if not present
                if not phone.startswith('420'):
                    phone = '+420' + phone
                else:
                    phone = '+' + phone
            
            # Create SMS text with user's balance
            sms_text = f"OS: Bonus Primavera Andorrana - na konte mate {balance} bodu. Cerpani a informace: https://bonus.primavera-and.cz/ Odhlaseni: SMS STOP na +420778799900."
            
            # Write to CSV
            writer.writerow([phone, sms_text])
            total_sms += 1
        
        # Inform user about how many SMS were generated
        messages.success(request, f"CSV export vytvořen s {total_sms} SMS zprávami.")
        
        return response

class ClientListView(ManagerGroupRequiredMixin, View):
    """
    View for managers to browse all clients with filtering options.
    
    Allows filtering by region, time period, and viewing detailed analytics
    on client turnover and points across their contract brands.
    """
    template_name = 'manager/client_list.html'
    
    def get(self, request):
        from django.db.models import Sum, Count, F, Q, Value, DecimalField
        from django.db.models.functions import Coalesce
        import datetime
        
        # Get filter parameters
        region_id = request.GET.get('region', '')
        year_from = request.GET.get('year_from', datetime.datetime.now().year)
        month_from = request.GET.get('month_from', 1)
        year_to = request.GET.get('year_to', datetime.datetime.now().year)
        month_to = request.GET.get('month_to', 12)
        
        try:
            year_from = int(year_from)
            month_from = int(month_from)
            year_to = int(year_to)
            month_to = int(month_to)
        except (ValueError, TypeError):
            # Use default values if conversion fails
            year_from = datetime.datetime.now().year
            month_from = 1
            year_to = datetime.datetime.now().year
            month_to = 12
        
        # Calculate date range for filtering
        date_from = datetime.date(year_from, month_from, 1)
        if month_to == 12:
            date_to = datetime.date(year_to + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            date_to = datetime.date(year_to, month_to + 1, 1) - datetime.timedelta(days=1)
        
        # Base query - get all active users that are not staff
        clients = User.objects.filter(is_active=True, is_staff=False)
        
        # Apply region filter if specified
        if region_id and region_id != 'all':
            clients = clients.filter(region_id=region_id)
        
        # Annotate with point data for the period
        clients = clients.annotate(
            confirmed_points=Coalesce(
                Sum('pointstransaction__value', 
                    filter=Q(
                        pointstransaction__status='CONFIRMED',
                        pointstransaction__date__gte=date_from,
                        pointstransaction__date__lte=date_to
                    )),
                Value(0)
            ),
            pending_points=Coalesce(
                Sum('pointstransaction__value', 
                    filter=Q(
                        pointstransaction__status='PENDING',
                        pointstransaction__date__gte=date_from,
                        pointstransaction__date__lte=date_to
                    )),
                Value(0)
            ),
            available_points=Coalesce(
                Sum('pointstransaction__value', 
                    filter=Q(pointstransaction__status='CONFIRMED')),
                Value(0)
            )
        )
        
        # Get all regions for the filter dropdown
        regions = Region.objects.filter(is_active=True).order_by('name')
        
        # For each client, get their contract brands turnover
        client_data = []
        for client in clients:
            # Get active contract for further reference
            try:
                active_contract = UserContract.objects.get(
                    user_id=client,
                    is_active=True
                )
                
                # Get all brands in this contract
                contract_brands = [bb.brand_id for bb in active_contract.brandbonuses.all()]
                
                # Calculate total turnover for the period across contract brands
                total_turnover = InvoiceBrandTurnover.objects.filter(
                    invoice__client_number=client.user_number,
                    invoice__invoice_date__gte=date_from,
                    invoice__invoice_date__lte=date_to,
                    invoice__invoice_type='INVOICE',
                    brand__in=contract_brands
                ).aggregate(
                    total=Coalesce(Sum('amount'), Value(0, output_field=DecimalField()))
                )['total']
                
                # Append to results with the contract and turnover info
                client_data.append({
                    'user': client,
                    'contract': active_contract,
                    'turnover': total_turnover,
                    'brand_count': len(contract_brands)
                })
            except UserContract.DoesNotExist:
                # Client has no active contract
                client_data.append({
                    'user': client,
                    'contract': None,
                    'turnover': 0,
                    'brand_count': 0
                })
        
        # Calculate date ranges for quick filter buttons
        current_year = datetime.datetime.now().year
        ytd_from = datetime.date(current_year, 1, 1)
        ytd_to = datetime.date.today()
        last_year_from = datetime.date(current_year - 1, 1, 1)
        last_year_to = datetime.date(current_year - 1, 12, 31)
        
        # Prepare context
        context = {
            'clients': client_data,
            'regions': regions,
            'selected_region': region_id,
            'year_from': year_from,
            'month_from': month_from,
            'year_to': year_to,
            'month_to': month_to,
            'date_from': date_from,
            'date_to': date_to,
            'ytd_from': ytd_from,
            'ytd_to': ytd_to,
            'last_year_from': last_year_from,
            'last_year_to': last_year_to,
            'current_year': current_year,
            'months': [(i, datetime.date(2000, i, 1).strftime('%B')) for i in range(1, 13)]
        }
        
        return render(request, self.template_name, context)
    
class ClientDetailView(ManagerGroupRequiredMixin, View):
    """
    Detailed view of a client for managers.
    
    Shows complete client information including:
    - Contact details
    - Contract information
    - Turnover by brand
    - Points transactions
    - Reward requests
    """
    template_name = 'manager/client_detail.html'
    
    def get(self, request, pk):
        from django.db.models import Sum, Count, F, Q, Value, DecimalField
        from django.db.models.functions import Coalesce
        import datetime
        
        # Get the client
        client = get_object_or_404(User, pk=pk)
        
        # Get filter parameters for date range
        year_from = request.GET.get('year_from', datetime.datetime.now().year)
        month_from = request.GET.get('month_from', 1)
        year_to = request.GET.get('year_to', datetime.datetime.now().year)
        month_to = request.GET.get('month_to', 12)
        
        try:
            year_from = int(year_from)
            month_from = int(month_from)
            year_to = int(year_to)
            month_to = int(month_to)
        except (ValueError, TypeError):
            # Use default values if conversion fails
            year_from = datetime.datetime.now().year
            month_from = 1
            year_to = datetime.datetime.now().year
            month_to = 12
        
        # Calculate date range for filtering
        date_from = datetime.date(year_from, month_from, 1)
        if month_to == 12:
            date_to = datetime.date(year_to + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            date_to = datetime.date(year_to, month_to + 1, 1) - datetime.timedelta(days=1)
        
        # Get client's active contract
        try:
            active_contract = UserContract.objects.get(
                user_id=client, 
                is_active=True
            )
            contract_brands = [bb.brand_id for bb in active_contract.brandbonuses.all()]
        except UserContract.DoesNotExist:
            active_contract = None
            contract_brands = []
        
        # Get all client's contracts for history
        all_contracts = UserContract.objects.filter(
            user_id=client
        ).order_by('-contract_date_from')
        
        # Get all brands turnover for the selected period
        all_brands = Brand.objects.all()
        brand_turnovers = []
        
        for brand in all_brands:
            # Get invoice turnover for this brand
            invoice_turnover = InvoiceBrandTurnover.objects.filter(
                invoice__client_number=client.user_number,
                invoice__invoice_date__gte=date_from,
                invoice__invoice_date__lte=date_to,
                invoice__invoice_type='INVOICE',
                brand=brand
            ).aggregate(
                total=Coalesce(Sum('amount'), Value(0, output_field=DecimalField()))
            )['total']
            
            # Get credit note turnover for this brand (negative)
            credit_turnover = InvoiceBrandTurnover.objects.filter(
                invoice__client_number=client.user_number,
                invoice__invoice_date__gte=date_from,
                invoice__invoice_date__lte=date_to,
                invoice__invoice_type='CREDIT_NOTE',
                brand=brand
            ).aggregate(
                total=Coalesce(Sum('amount'), Value(0, output_field=DecimalField()))
            )['total']
            
            # Calculate points for this brand in the period
            points = PointsTransaction.objects.filter(
                user=client,
                date__gte=date_from,
                date__lte=date_to,
                brand=brand,
                status='CONFIRMED'
            ).aggregate(
                total=Coalesce(Sum('value'), Value(0))
            )['total']
            
            # Only include brands with some activity
            if invoice_turnover > 0 or credit_turnover > 0 or points != 0:
                # Check if this brand is in the client's contract
                in_contract = brand in contract_brands
                
                brand_turnovers.append({
                    'brand': brand,
                    'invoice_turnover': invoice_turnover,
                    'credit_turnover': credit_turnover,
                    'net_turnover': invoice_turnover - credit_turnover,
                    'points': points,
                    'in_contract': in_contract
                })
        
        # Sort by net turnover
        brand_turnovers.sort(key=lambda x: x['net_turnover'], reverse=True)
        
        # Get point totals
        point_totals = {
            'available': client.get_balance(),
            'period_confirmed': PointsTransaction.objects.filter(
                user=client,
                date__gte=date_from,
                date__lte=date_to,
                status='CONFIRMED'
            ).aggregate(
                total=Coalesce(Sum('value'), Value(0))
            )['total'],
            'period_pending': PointsTransaction.objects.filter(
                user=client,
                date__gte=date_from,
                date__lte=date_to,
                status='PENDING'
            ).aggregate(
                total=Coalesce(Sum('value'), Value(0))
            )['total']
        }
        
        # Get recent transactions
        recent_transactions = PointsTransaction.objects.filter(
            user=client
        ).order_by('-date', '-created_at')[:10]
        
        # Get reward requests
        reward_requests = RewardRequest.objects.filter(
            user=client
        ).order_by('-requested_at')[:10]
        
        # Prepare context
        context = {
            'client': client,
            'active_contract': active_contract,
            'all_contracts': all_contracts,
            'brand_turnovers': brand_turnovers,
            'point_totals': point_totals,
            'recent_transactions': recent_transactions,
            'reward_requests': reward_requests,
            'date_from': date_from,
            'date_to': date_to,
            'year_from': year_from,
            'month_from': month_from,
            'year_to': year_to,
            'month_to': month_to,
            'months': [(i, datetime.date(2000, i, 1).strftime('%B')) for i in range(1, 13)]
        }
        
        return render(request, self.template_name, context)
    