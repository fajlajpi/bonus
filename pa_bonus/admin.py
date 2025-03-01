import logging
from django.contrib import admin
from import_export import resources, fields
from import_export.widgets import DateWidget
from import_export.admin import ExportMixin, ImportExportMixin
from django.contrib.auth.hashers import make_password
from pa_bonus.models import (
    User, Brand, UserContract, PointsTransaction, BrandBonus, PointsBalance, 
    FileUpload, Reward, RewardRequest, RewardRequestItem
)

logger = logging.getLogger(__name__)

# IMPORT EXPORT FUNCTIONALITY
class UserResource(resources.ModelResource):
    """
    Defines import/export settings for the User model.

    - Can import from XLSX file
    - Hashes passwords
    - Uses email as the primary identifier
    """

    password = fields.Field(
        column_name='password',
        attribute='password',
        widget=None  # We override save_instance to hash passwords
    )

    class Meta:
        model = User
        import_id_fields = ['email']  # Email is the unique identifier
        fields = ('username', 'email', 'first_name', 'last_name', 'user_number', 'user_phone', 'password', 'is_active')

    def before_import_row(self, row, **kwargs):
        """
        Automatically sets the default password to user_number and hashes it.
        """
        row['password'] = make_password(str(row['user_number']))
        super().before_import_row(row, **kwargs)


    def before_save_instance(self, instance, *args, **kwargs):
        """
        Ensures passwords are hashed before saving
        """
        logger.debug(f"before_save_instance called with: args={args}, kwargs={kwargs}")

        instance.password = make_password(instance.password)
        super().before_save_instance(instance, *args, **kwargs)

# INLINES
class RewardRequestItemInline(admin.TabularInline):
    model = RewardRequestItem
    extra = 1  # Number of empty forms shown

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
@admin.register(User)
class UserAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = UserResource
    list_display = ('username', 'email', 'last_name', 'first_name', 'user_number', 'user_phone')
    search_fields = ('username', 'email', 'last_name', 'user_number')
    list_filter = ('is_staff', 'is_active')

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'prefix')
    search_fields = ('name', 'prefix')

@admin.register(UserContract)
class UserContractAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'contract_date_from', 'contract_date_to', 'is_active')
    search_fields = ('user_id__username', 'user_id__email', 'user_id__user_number')
    list_filter = ('is_active', 'contract_date_from', 'contract_date_to')

@admin.register(PointsTransaction)
class PointsTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'value', 'status', 'date', 'description')
    search_fields = ('user__username', 'user__email', 'user__user_number')
    list_filter = ('type', 'status', 'date')
    readonly_fields = ('created_at',)
    actions = [confirm_transactions, pending_transactions, cancel_transactions]

@admin.register(BrandBonus)
class BrandBonusAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand_id', 'points_ratio')
    search_fields = ('name', 'brand_id__name')

@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = ('status', 'uploaded_at', 'file', 'processed_at', 'uploaded_by')
    list_filter = ('status', 'uploaded_at', 'uploaded_by')
    readonly_fields = ('uploaded_at', 'processed_at', 'status', 'error_message')

@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ('abra_code', 'name', 'point_cost', 'brand', 'is_active')
    list_filter = ('brand', 'is_active')
    search_fields = ('abra_code', 'name')

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
