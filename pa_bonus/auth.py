from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from pa_bonus.models import User

class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Check if the username is an email (contains @)
            is_email = '@' in username if username else False
            
            if is_email:
                user = User.objects.get(email=username)
            else:
                user = User.objects.get(username=username)
            
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None
        
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None