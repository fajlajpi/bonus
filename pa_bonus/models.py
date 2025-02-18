from django.db import models
from django.contrib.auth.models import AbstractUser
import os

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
    USER_TYPES = (
        ('CLIENT', 'Client'),
        ('ADMIN', 'Admin')
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='CLIENT')
    user_number = models.CharField(max_length=20, unique=True)
    user_phone = models.CharField(max_length=10, unique=True)

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

    class Meta:
        ordering = ['-contract_date_from']

    def __str__(self):
        user_name = self.user_id.last_name + ' ' + self.user_id.first_name

        return user_name + f' ({self.contract_date_from})'
    

class PointsTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('STANDARD_POINTS', 'Standard Points added'),
        ('REWARD_CLAIM', 'Reward Claim'),
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
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f'{self.user} | {self.date} | {self.type} | {self.value}'

class ContractBrands(models.Model):
    contract_id = models.ForeignKey(UserContract, on_delete=models.CASCADE)
    brand_id = models.ForeignKey(Brand, on_delete=models.CASCADE)

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
    file = models.FileField(upload_to=get_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PROCESSING_STATUS, default='PENDING')
    error_message = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'Upload {self.id} | {self.uploaded_at} | {self.status} | by {self.uploaded_by}'