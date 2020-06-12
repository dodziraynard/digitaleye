from django.urls import path
from .import views

app_name = "processor"

urlpatterns = [
    path("", views.ConvertionOptions.as_view(), name="convertion_options"),
    path("convert-to-selectable-pdf", 
        views.StaticPDFToSelectablePDFView.as_view(), 
        name="convert_to_selectable_pdf"),
    
    path("remove-watermark-from-pdf", 
        views.RemoveWatermarkFromPDFView.as_view(), 
        name="remove_watermark_from_pdf"),

    path("convert-pdfs-pngs", 
        views.ConvertPDFToPNGsView.as_view(), 
        name="convert_pdf_to_pngs"),

    path("merge-pdfs", 
        views.MergePDFFilesView.as_view(), 
        name="merg_pdfs"),

    path("extract-text-from-pdf", 
        views.ExtractTextFromPDFView.as_view(), 
        name="extract_text_from_pdf"),

    # path("convert-to-png", views.convert_to_png, name="convert_to_png"),
    # path("convert-images-to-png", views.images_to_pdf, name="images_to_pdf"),
    # path("merge-pdfs", views.MergePDFsView.as_view(), name="merge_pdfs"),


    # path("order/<str:task_id>", views.processing_view, name="processing"),
    # path('stream/<str:task_id>', views.stream_task_progress, name='stream_task_progress')
]
