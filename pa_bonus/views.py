from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.views.generic import TemplateView, ListView, DetailView, View
from django.db.models import Sum, Q
from django.db import transaction
from .forms import FileUploadForm
from .tasks import process_uploaded_file
from .models import FileUpload, PointsTransaction, PointsBalance, UserContract, Reward, RewardRequest, RewardRequestItem

# Create your views here.
@permission_required('pa_bonus.can_manage', raise_exception=True)
def upload_file(request):
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
    uploads = FileUpload.objects.all().order_by('-uploaded_at')
    return render(request, 'upload_history.html', {'uploads': uploads})


# Client-facing views
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get the user's active contract and bonuses
        try:
            contract = UserContract.objects.get(
                user_id = user,
                is_active = True
            )
            context['contract'] = contract
            context['brand_bonuses'] = contract.brandbonuses.all()
        except UserContract.DoesNotExist:
            context['contract'] = None
            context['brand_bonuses'] = []
        
        # Calculate current point total
        # TODO: Use PointsBalance model to avoid this calculation
        total_points = user.get_balance()

        context['total_points'] = total_points
        return context

class HistoryView(LoginRequiredMixin, ListView):
    template_name = 'history.html'
    context_object_name = 'transactions'
    login_url = 'login'

    def get_queryset(self):
        return PointsTransaction.objects.filter(
            user = self.request.user
        ).select_related('brand')

class HistoryDetailView(LoginRequiredMixin, DetailView):
    template_name = 'history_detail.html'
    context_object_name = 'transaction'
    login_url = 'login'

    def get_queryset(self):
        return PointsTransaction.objects.filter(
            user = self.request.user
        ).select_related('brand')

class RewardsView(LoginRequiredMixin, View):
    template_name = 'rewards.html'
    login_url = 'login'

    def get(self, request, *args, **kwargs):
        user = request.user

        # Get user's brands
        user_contracts = UserContract.objects.filter(user_id = user, is_active = True)
        user_brands = set()
        for contract in user_contracts:
            for bonus in contract.brandbonuses.all():
                user_brands.add(bonus.brand_id)

        # Get available rewards
        available_rewards = Reward.objects.filter(is_active=True).filter(Q(brand__in=user_brands) | Q(brand__isnull=True)).distinct()
        
        # Get user's point balance
        # TODO: Use PointsBalance model to avoid this calculation
        total_points = user.get_balance()

        context = {
            'rewards': available_rewards,
            'user_balance': total_points,
        }

        return render(request, self.template_name, context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user = request.user
        reward_quantities = {}

        # Collect reward quantities from form
        for key, value in request.POST.items():
            if key.startswith('reward_quantity_') and value.isdigit():
                reward_id = key.split('reward_quantity_')[1]
                reward_quantities[reward_id] = int(value)
        
        # Create reward request
        reward_request = RewardRequest(user=user)
        reward_request.save()

        # Create reward request items
        for reward_id, quantity in reward_quantities.items():
            if quantity <= 0:
                continue
            reward = Reward.objects.get(pk=reward_id)
            RewardRequestItem.objects.create(
                reward_request=reward_request,
                reward=reward,
                quantity=quantity
            )
        
        # Save the request and update total points
        try:
            reward_request.save()  # This calculates the point total as well
        except Exception:
            messages.error(request, f"Error: {e}")
            return redirect('rewards')
        
        messages.success(request, "Request saved successfully.")
        return redirect('rewards_request_detail', pk=reward_request.pk)


class RewardsRequestsView(LoginRequiredMixin, TemplateView):
    template_name = 'reward_requests.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #PLACEHOLDER MESSAGE
        context['message'] = "Rewards system coming soon!"
        return context

class RequestsDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'request_detail.html'
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #PLACEHOLDER MESSAGE
        context['message'] = "Rewards system coming soon!"
        return context
    
class RewardsRequestDetailView(View):
    template_name = 'rewards_request_detail.html'

    def get(self, request, pk):
        reward_request = get_object_or_404(RewardRequest, pk=pk)
        reward_request_items = RewardRequestItem.objects.filter(reward_request=reward_request)
        user_balance = request.user.get_balance()

        context = {
            'request': reward_request,
            'items': reward_request_items,
            'user_balance': user_balance,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        reward_request = get_object_or_404(RewardRequest, pk=pk)
        # Update the status to Pending
        reward_request.status = "PENDING"
        reward_request.save()

        # Create a claim transaction so that the points are already blocked off
        points_transaction = PointsTransaction.objects.create(
            value = -reward_request.total_points,
            date=reward_request.requested_at,
            user=request.user,
            description="Reward claim",
            type="REWARD_CLAIM",
            status="CONFIRMED",
        )

        messages.success(request, f"Request {reward_request.id} confirmed successfully.")
        return redirect('rewards')