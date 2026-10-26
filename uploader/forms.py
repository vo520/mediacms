from django import forms
from django.conf import settings


class FineUploaderUploadForm(forms.Form):
    qqfile = forms.FileField()
    qquuid = forms.CharField()
    qqfilename = forms.CharField()
    qqpartindex = forms.IntegerField(required=False)
    qqchunksize = forms.IntegerField(required=False)
    qqtotalparts = forms.IntegerField(required=False)
    qqtotalfilesize = forms.IntegerField(required=False)
    qqpartbyteoffset = forms.IntegerField(required=False)

    def clean_qqtotalfilesize(self):
        size = self.cleaned_data.get("qqtotalfilesize")
        if size is not None and size > settings.UPLOAD_MAX_SIZE:
            max_size_mb = settings.UPLOAD_MAX_SIZE / (1024 * 1024)
            raise forms.ValidationError(f"File too large. Maximum size: {max_size_mb:.0f}MB")
        return size


class FineUploaderUploadSuccessForm(forms.Form):
    qquuid = forms.CharField()
    qqfilename = forms.CharField()
    qqtotalparts = forms.IntegerField()
    qqtotalfilesize = forms.IntegerField(required=False)

    def clean_qqtotalfilesize(self):
        size = self.cleaned_data.get("qqtotalfilesize")
        if size is not None and size > settings.UPLOAD_MAX_SIZE:
            max_size_mb = settings.UPLOAD_MAX_SIZE / (1024 * 1024)
            raise forms.ValidationError(f"File too large. Maximum size: {max_size_mb:.0f}MB")
        return size
