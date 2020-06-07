from django.urls import path
from .import views

app_name = "webapp"

urlpatterns = [
    path("", views.convertion_options, name="convertion_options"),
    path("convert-to-pdf", views.convert_to_pdf, name="convert_to_pdf"),
    path("convert-to-png", views.convert_to_png, name="convert_to_png"),
    path("convert-images-to-png", views.images_to_pdf, name="images_to_pdf"),
    path("merge-pdfs", views.MergePDFsView.as_view(), name="merge_pdfs"),


    path("order/<str:task_id>", views.processing_view, name="processing"),
    path('stream/<str:task_id>', views.stream_task_progress, name='stream_task_progress')
]
