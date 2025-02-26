from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.contenttypes.models import ContentType
import os
import logging

# Configure logger
logger = logging.getLogger(__name__)

#Utility functions
def get_upload_path(instance, filename):
    # Files will me uploaded to MEDIA_ROOT/uploads/YYYY/MM/DD/
    return os.path.join(
        'uploads',
        instance.uploaded_at.strftime('%Y/%d/%d'),
        filename
    )

# Create your models here.
class User(AbstractUser):
    user_number = models.CharField(max_length=20, unique=True)
    user_phone = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.username + ' | ' + (self.first_name + ' ' + self.last_name if self.first_name or self.last_name else '')

class Brand(models.Model):
    name = models.CharField(max_length=50)
    prefix = models.CharField(max_length=10)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class UserContract(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    contract_date_from = models.DateField()
    contract_date_to = models.DateField()
    extra_goal_12m = models.IntegerField()
    extra_goal_base = models.IntegerField()
    is_active = models.BooleanField(default=True)
    brandbonuses = models.ManyToManyField('BrandBonus', related_name="user_contract")

    class Meta:
        ordering = ['-contract_date_from']

    def __str__(self):
        user_name = self.user_id.last_name + ' ' + self.user_id.first_name

        return user_name + f' ({self.contract_date_from})'
    

class PointsTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('STANDARD_POINTS', 'Standard Points added'),
        ('REWARD_CLAIM', 'Reward Claim'),
        ('CREDIT_NOTE_ADJUST', 'Credit Note (dobropis) adjustment'),
        ('EXTRA_POINTS', 'Extra Points added'),
        ('ADJUSTMENT', 'Manual Adjustment'),
    )
    TRANSACTION_STATUS = (
        ('NO-CONTRACT', 'No-Contract'),
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled')
    )
    value = models.IntegerField()
    date = models.DateField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS)
    brand = models.ForeignKey(Brand, null=True, blank=True,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f'{self.user} | {self.date} | {self.type} | {self.value}'

class PointsBalance(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    points = models.IntegerField()

class BrandBonus(models.Model):
    name = models.CharField(max_length=100)
    points_ratio = models.FloatField()
    brand_id = models.ForeignKey(Brand, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.name} | {self.brand_id} | {self.points_ratio} points per '

class FileUpload(models.Model):
    PROCESSING_STATUS = (
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )
    file = models.FileField(upload_to="uploads/%Y/%m/%d/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PROCESSING_STATUS, default='PENDING')
    error_message = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-uploaded_at']
        permissions = [
            ('can_manage', 'Can manage file uploads')
        ]

    def __str__(self):
        return f'Upload {self.id} | {self.uploaded_at} | {self.status} | by {self.uploaded_by}'
    
class Reward(models.Model):
    abra_code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    point_cost = models.IntegerField()
    description = models.TextField()
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='reward_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.brand.prefix if self.brand is not None else 'no brand'} | {self.name}'
    
    class Meta:
        ordering = ['abra_code']

class RewardRequest(models.Model):
    REQUEST_STATUS = (
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('FINISHED', 'Finished'),
        ('CANCELLED', 'Cancelled'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=REQUEST_STATUS, default='DRAFT')
    description = models.TextField()
    total_points = models.IntegerField(default=0)

    def __str__(self):
        return f"Request {self.id} | by {self.user} | on {self.requested_at.strftime('%Y-%m-%d')} | TOTAL: {self.total_points} pts"

    def save(self, *args, **kwargs):
        # When saving to model, save the total points 
        try:
            self.total_points = sum(item.quantity * item.point_cost for item in self.rewardrequestitem_set.all())
        except ValueError:
            self.total_points = 0
        super().save(*args, **kwargs)

class RewardRequestItem(models.Model):
    reward_request = models.ForeignKey(RewardRequest, on_delete=models.CASCADE)
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    point_cost = models.IntegerField()  # Storing point cost at the time of request, in case it changes over time

    def __str__(self):
        return f"{self.quantity} x {self.reward.name} | {self.reward_request}"
    
    def save(self, *args, **kwargs):
        #Set point cost from Reward before saving.
        self.point_cost = self.reward.point_cost
        super().save(*args, **kwargs)
    
# Utility function to create group and permissions
def create_manager_group_and_permissions(*args, **options):
    """
    Creates the 'Managers' group and assigns the 'can_manage' permission.
    This function should be called after migrations, like in a data migration.
    """
    try:
        #Create group
        manager_group, created = Group.objects.get_or_create(name='Managers')
        logger.info("Manager group created/retrieved")

        #Get permission object
        content_type = ContentType.objects.get_for_model(FileUpload)
        can_manage_perm = Permission.objects.get(
            codename='can_manage',
            content_type=content_type,
        )
        logger.info("Can manage permission retrieved")

        #Add permission to group
        manager_group.permissions.add(can_manage_perm)
        logger.info("Can manage permission assigned to Manager group")

        print("Manager group and permissions setup successfully")
    except Exception as e:
        logger.error(f"Error creating Manager group and permissions: {e}", exc_info=True)
        print(f"Error creating Manager group and permissions: {e}")
