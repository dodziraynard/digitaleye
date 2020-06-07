from django.contrib import admin
from . models import PDFOperationOrder, ImageOperationOrder, Image

admin.site.register(PDFOperationOrder)
admin.site.register(ImageOperationOrder)
admin.site.register(Image)