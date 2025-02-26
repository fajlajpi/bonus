from django.contrib import admin
from pa_bonus import models

# Register your models here.
admin.site.register(models.User)
admin.site.register(models.Brand)
admin.site.register(models.UserContract)
admin.site.register(models.PointsTransaction)
admin.site.register(models.BrandBonus)
admin.site.register(models.PointsBalance)
admin.site.register(models.FileUpload)
admin.site.register(models.Reward)
admin.site.register(models.RewardRequest)
admin.site.register(models.RewardRequestItem)