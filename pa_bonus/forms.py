from django import forms
from .models import FileUpload

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