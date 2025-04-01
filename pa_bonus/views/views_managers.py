from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.views.generic import ListView, View
from pa_bonus.forms import FileUploadForm
from pa_bonus.tasks import process_uploaded_file
from pa_bonus.models import FileUpload, Reward, RewardRequest, RewardRequestItem
from pa_bonus.utilities import ManagerGroupRequiredMixin

# Create your views here.
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

    Attributes:
        template_name (str): Template name to render
    """
    template_name = 'manager/reward_request_detail.html'

    def get(self, request, pk):
        reward_request = get_object_or_404(RewardRequest, pk=pk)
        items = reward_request.rewardrequestitem_set.select_related('reward')
        item_quantities = {
            item.reward.id: item.quantity for item in reward_request.rewardrequestitem_set.all()
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

    def post(self, request, pk):
        reward_request = get_object_or_404(RewardRequest, pk=pk)
        user_balance = reward_request.user.get_balance()
        override_limit = request.POST.get('allow_negative', '') == 'on'

        # Clear and rebuild items
        reward_request.rewardrequestitem_set.all().delete()
        total_points = 0

        for reward in Reward.objects.filter(is_active=True):
            field_name = f'reward_{reward.id}'
            qty = request.POST.get(field_name)
            if qty and qty.isdigit() and int(qty) > 0:
                quantity = int(qty)
                RewardRequestItem.objects.create(
                    reward_request=reward_request,
                    reward=reward,
                    quantity=quantity,
                    point_cost=reward.point_cost
                )
                total_points += quantity * reward.point_cost

        # Validate against user balance
        if not override_limit and total_points > user_balance:
            messages.error(request, f"Total points required ({total_points}) exceeds user's available balance ({user_balance}).")
            return redirect(request.path)

        reward_request.description = request.POST.get('manager_message', '')
        reward_request.status = request.POST.get('status')
        reward_request.save()

        messages.success(request, f"Request {reward_request.pk} updated.")
        return redirect('manager_reward_requests')