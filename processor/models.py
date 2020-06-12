from django.db import models
from django.utils import timezone


class Order(models.Model):
    files = models.ManyToManyField("File")
    date_pub = models.DateTimeField(default=timezone.now)
    processed = models.BooleanField(default=False)
    result_file = models.FileField(upload_to="results")

    def __str__(self):
        return f"Order {self.id}"


class File(models.Model):
    file = models.FileField(upload_to="uploads")
