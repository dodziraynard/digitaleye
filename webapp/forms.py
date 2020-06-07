from . models import PDFOperationOrder, ImageOperationOrder
from django import forms
from django.contrib.auth.models import User

class PDFOperationOrderForm(forms.ModelForm):
    class Meta:
        model = PDFOperationOrder
        fields = ['file', 'remove_bg']

class ImageOperationOrderForm(forms.ModelForm):
    class Meta:
        model = ImageOperationOrder
        fields = ['images', 'remove_bg']