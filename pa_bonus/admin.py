import logging
from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple, AdminDateWidget
from import_export import resources, fields, widgets
from import_export.widgets import DateWidget
from import_export.admin import ExportMixin, ImportExportMixin
from django.forms.models import BaseInlineFormSet
from pa_bonus.models import (
    User, Brand, UserContract, UserContractGoal, PointsTransaction, BrandBonus, 
    FileUpload, Reward, RewardRequest, RewardRequestItem, EmailNotification, Invoice, InvoiceBrandTurnover,
    Region, RegionRep,
)
from .resources import UserResource, UserContractResource, UserContractGoalResource, RewardResource, OptimizedUserResource


logger = logging.getLogger(__name__)

# INLINE FORMS
class UserContractGoalInlineForm(forms.ModelForm):
    class Meta:
        model = UserContractGoal
        fields = '__all__'
        widgets = {
            'goal_period_from': AdminDateWidget(),
            'goal_period_to': AdminDateWidget(),
            'brands': FilteredSelectMultiple("Brands", is_stacked=False),
        }

# INLINES
class RewardRequestItemInline(admin.TabularInline):
    model = RewardRequestItem
    extra = 1  # Number of empty forms shown

class UserContractInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        kwargs['initial'] = [
            {'contract_date_from': '2025-01-01', 'contract_date_to': '2025-12-31'}
        ]
        super(UserContractInlineFormSet, self).__init__(*args, **kwargs)

class UserContractInline(admin.TabularInline):
    model = UserContract
    extra = 1  # Number of empty forms shown
    formset = UserContractInlineFormSet

class UserContractGoalInline(admin.TabularInline):
    model = UserContractGoal
    fk_name = "user_contract"
    form = UserContractGoalInlineForm
    extra = 0

class InvoiceBrandTurnoverInline(admin.TabularInline):
    model = InvoiceBrandTurnover
    extra = 0
    

# CUSTOM ACTIONS
def approve_requests(modeladmin, request, queryset):
    queryset.update(status='ACCEPTED')

def reject_requests(modeladmin, request, queryset):
    queryset.update(status='REJECTED')

def confirm_transactions(modeladmin, request, queryset):
    queryset.update(status='CONFIRMED')

def pending_transactions(modeladmin, request, queryset):
    queryset.update(status='PENDING')

def cancel_transactions(modeladmin, request, queryset):
    queryset.update(status='CANCELLED')


approve_requests.short_description = "Approve selected requests"
reject_requests.short_description = "Reject selected requests"
confirm_transactions.short_description = "Confirm selected transactions"
pending_transactions.short_description = "Mark selected transactions as pending"
cancel_transactions.short_description = "Cancel selected transactions"


# REGISTERING AND SETTING UP MODELS FOR DJANGO ADMIN

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)

@admin.register(RegionRep)
class RegionRepAdmin(admin.ModelAdmin):
    list_display = ('user', 'region', 'is_primary', 'date_from', 'date_to', 'is_active')
    list_filter = ('is_active', 'is_primary', 'region')
    search_fields = ('user__username', 'user__email', 'user__last_name', 'region__name')
    date_hierarchy = 'date_from'
    raw_id_fields = ('user',)
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Customize the form to only show users in the Sales Reps group.
        """
        form = super().get_form(request, obj, **kwargs)
        if 'user' in form.base_fields:
            form.base_fields['user'].queryset = User.objects.filter(
                groups__name='Sales Reps'
            )
        return form

@admin.register(User)
class UserAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = OptimizedUserResource
    list_display = ('username', 'email', 'last_name', 'first_name', 'user_number', 'user_phone', 'region')
    search_fields = ('username', 'email', 'last_name', 'user_number')
    list_filter = ('is_staff', 'is_active', 'region')
    inlines = [UserContractInline]

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'prefix')
    search_fields = ('name', 'prefix')

@admin.register(UserContract)
class UserContractAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = UserContractResource
    list_display = ('user_id', 'contract_date_from', 'contract_date_to', 'is_active')
    search_fields = ('user_id__username', 'user_id__email', 'user_id__user_number')
    list_filter = ('is_active', 'contract_date_from', 'contract_date_to')
    inlines = [UserContractGoalInline]

@admin.register(UserContractGoal)
class UserContractGoalAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = UserContractGoalResource
    list_display = ('user_contract', 'goal_period_from', 'goal_period_to', 'goal_value', 'goal_base')
    list_filter = ('goal_period_from', 'goal_period_to')
    search_fields = ('user_contract__user_id__email',)

@admin.register(PointsTransaction)
class PointsTransactionAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ('user', 'type', 'value', 'status', 'date', 'description')
    search_fields = ('user__username', 'user__email', 'user__user_number')
    list_filter = ('type', 'status', 'date')
    readonly_fields = ('created_at',)
    actions = [confirm_transactions, pending_transactions, cancel_transactions]

@admin.register(BrandBonus)
class BrandBonusAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ('name', 'brand_id', 'points_ratio')
    search_fields = ('name', 'brand_id__name')

@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = ('status', 'uploaded_at', 'file', 'processed_at', 'uploaded_by')
    list_filter = ('status', 'uploaded_at', 'uploaded_by')
    readonly_fields = ('uploaded_at', 'processed_at', 'status', 'error_message')

@admin.register(Reward)
class RewardAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = RewardResource
    list_display = ('abra_code', 'name', 'point_cost', 'brand', 'is_active')
    list_filter = ('brand', 'is_active')
    search_fields = ('abra_code', 'name')
    readonly_fields = ('created_at',)

@admin.register(RewardRequest)
class RewardRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'requested_at', 'status', 'total_points')
    list_filter = ('status',)
    search_fields = ('user__username', 'user__email')
    actions = [approve_requests, reject_requests]
    inlines = [RewardRequestItemInline]

@admin.register(RewardRequestItem)
class RewardRequestItemAdmin(admin.ModelAdmin):
    list_display = ('reward_request', 'reward', 'quantity', 'point_cost')

@admin.register(EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'status', 'created_at', 'sent_at')
    list_filter = ('status', 'created_at', 'sent_at')
    search_fields = ('user__username', 'user__email', 'subject')
    readonly_fields = ('created_at', 'sent_at')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'client_number', 'invoice_date', 'invoice_type', 'total_amount')
    list_filter = ('invoice_type', 'invoice_date')
    search_fields = ('invoice_number', 'client_number')
    date_hierarchy = 'invoice_date'
    inlines = [InvoiceBrandTurnoverInline]

@admin.register(InvoiceBrandTurnover)
class InvoiceBrandTurnoverAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'brand', 'amount')
    list_filter = ('brand',)
    search_fields = ('invoice__invoice_number', 'invoice__client_number', 'brand__name')