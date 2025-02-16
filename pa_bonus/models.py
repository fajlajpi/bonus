from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    USER_TYPES = (
        ('CLIENT', 'Client'),
        ('ADMIN', 'Admin')
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='CLIENT')
    user_id = models.CharField(max_length=10, unique=True, primary_key=True)
    user_email = models.EmailField(max_length=100, unique=True)
    user_phone = models.CharField(max_length=10, unique=True)
    user_joined = models.DateField(auto_now_add=True)

class UserContract(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    contract_date_from = models.DateField()

    

class PointsTransaction(models.Model):
    TRANSACTION_STATUS = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed')
    )
    value = models.IntegerField()
    date = models.DateField()
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.CharField(max_length=100)


class ContractBrands(models.Model):
    pass

class PointsBalance(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    points = models.IntegerField()

class BrandBonus(models.Model):
    pass