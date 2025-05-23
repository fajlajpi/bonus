from django import forms
from .models import FileUpload
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

class FileUploadForm(forms.ModelForm):
    class Meta:
        model = FileUpload
        fields = ['file']

    def clean_file(self):
        file = self.cleaned_data['file']

        # Check file extension
        ext = file.name.split('.')[-1].lower()
        if ext not in ['xls','xlsx', 'csv']:
            raise forms.ValidationError('Unsupported filetype')
        
        # Check file size (limit 15 MB)
        if file.size > 15 * 1024 * 1024:
            raise forms.ValidationError('File too large (>15 MB)')
        
        return file
    
class EmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email nebo uživatelské jméno",
        widget=forms.TextInput(attrs={'autofocus': True}),
    )
    password = forms.CharField(
        label="Heslo",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )
    
    error_messages = {
        'invalid_login': "Zadejte prosím správné uživatelské jméno (nebo emailovou adresu) a heslo. ",
        'inactive': "Tento účet je neaktivní.",
    }