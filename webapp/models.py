from django.db import models
from django.utils import timezone

class PDFOperationOrder(models.Model):
    file = models.FileField(upload_to="uploads/documents")
    remove_bg = models.BooleanField(default=False)
    pub_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return str(self.pub_date)

class ImageOperationOrder(models.Model):
    images = models.ManyToManyField("Image")
    remove_bg = models.BooleanField(default=False)
    merge = models.BooleanField(default=True)
    pub_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return str(self.pub_date)
    
class Image(models.Model):
    file = models.FileField(upload_to="uploads/images")


class UploadedFile(models.Model):
    type = models.CharField(max_length=10, blank=True)
    file = models.FileField(upload_to="uploads/files")

class MultipleFile(models.Model):
    files = models.ManyToManyField("UploadedFile")
    pub_date = models.DateTimeField(default=timezone.now)