from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.views.generic import TemplateView, ListView, DetailView
from django.db.models import Sum
from .forms import FileUploadForm
from .tasks import process_uploaded_file
from .models import FileUpload, PointsTransaction, UserContract

# Create your views here.
@login_required
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

@login_required
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
        total_points = PointsTransaction.objects.filter(
            user = user,
            status = 'CONFIRMED'
        ).aggregate(
            total = Sum('value')
        )['total'] or 0

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

class HistoryDetailView(LoginRequiredMixin, TemplateView):
    pass

class RewardsView(LoginRequiredMixin, TemplateView):
    pass

class RewardsRequestsView(LoginRequiredMixin, TemplateView):
    pass

class RequestsDetailView(LoginRequiredMixin, TemplateView):
    pass