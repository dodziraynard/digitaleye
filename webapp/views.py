import datetime
import time
from django.shortcuts import render, redirect
from . forms import PDFOperationOrderForm, ImageOperationOrderForm
from . models import Image, ImageOperationOrder, UploadedFile, MultipleFile
from . tasks import static_pdf_to_selectable_pdf, pdf_to_pngs, images_to_pdf_task, task_merge_pdfs
from django.core.files.storage import FileSystemStorage
from core.celery import get_celery_worker_status
from celery.result import AsyncResult
from django.http import StreamingHttpResponse
from django.views import View


def convertion_options(request):
    template_name = "webapp/convertion_options.html"
    return render(request, template_name)

class ValidateFileMixin(View):
    """ This class validates the files uploaded by the user against defined
        acceptable extensions.
    """
    def validate_files(self, files, acceptable_extensions) -> bool:
        for file in files:
            file_extension = file.name.split(".")[-1]
            if not file_extension in acceptable_extensions:
                return False
            return True
 
def convert_to_png(request):
    template_name = "webapp/convert_to_png.html"
    form = PDFOperationOrderForm()

    if request.method == "POST":
        form = PDFOperationOrderForm(request.POST, request.FILES)
        if form.is_valid():
            order = form.save()
            input_file = order.file.name
            fn = "".join(input_file.split("/")[-1].split(".")[:1])
            request.session["pngs_url"] = "http://127.0.0.1:8000/resources/processed/"+fn+".zip"
            
            # initiate pdf processing tast
            task = pdf_to_pngs.delay(order.id)
            return redirect("webapp:processing", task.task_id)

    context = {
        "form":form,
    }
    return render(request, template_name, context)


def images_to_pdf(request):
    template_name = "webapp/images_to_pdf.html"
    acceptable_extensions = ["png", "jpg"]

    if request.method == "POST":
        files = request.FILES.getlist("images")
        remove_bg = False if request.POST.get("remove_bg") == None else True

        # Validating images
        for file in files:
            file_extension = file.name.split(".")[-1]
            if not file_extension in acceptable_extensions:
                request.session["error_message"] = "Only .png and .jpg files are acceptable"
                return redirect("webapp:images_to_pdf")

        # saving images
        images = []
        for file in files:
            images.append(Image.objects.create(file=file))
        
        order = ImageOperationOrder.objects.create(remove_bg=remove_bg)
        order.images.add(*images)

        request.session["pdf_url"] = "http://127.0.0.1:8000/resources/processed/"+"images_to_pdf"+str(order.pk)+".pdf"
        
        # initiate pdf processing tast
        task = images_to_pdf_task.delay(order.id)
        return redirect("webapp:processing", task.task_id)
    return render(request, template_name)


def convert_to_pdf(request):
    template_name = "webapp/convert_to_pdf.html"
    form = PDFOperationOrderForm()

    if request.method == "POST":
        form = PDFOperationOrderForm(request.POST, request.FILES)
        if form.is_valid():
            order = form.save()
            input_file = order.file.name
            fn = input_file.split("/")[-1]
            request.session["pdf_url"] = "http://127.0.0.1:8000/resources/processed/"+fn
            
            # initiate pdf processing tast
            task = static_pdf_to_selectable_pdf.delay(order.id)
            return redirect("webapp:processing", task.task_id)

    context = {
        "form":form,
    }
    return render(request, template_name, context)


def processing_view(request, task_id):
    template_name = "webapp/processing.html"
    
    pdf_url = request.session.pop("pdf_url", "")
    pngs_url = request.session.pop("pngs_url", "")
    context = {
        "pdf_url" : pdf_url,
        "pngs_url" : pngs_url,
        "task_id":task_id,
    }
    return render(request, template_name, context)

def stream_task_progress(request, task_id):
    result = AsyncResult(task_id)
    def get_task_progress():
        i = 1
        while True:
            data = str(result.status) + "," + str(result.info)
            time.sleep(0.05)
            i +=1
            if result.status == "SUCCESS":
                yield 'data: SUCCESS\n\n'
                break

            yield 'data: %s\n\n' % data
    return StreamingHttpResponse(get_task_progress(), content_type='text/event-stream')


class MergePDFsView(ValidateFileMixin):
    """Merge PDFs 

    """
    template_name = "webapp/merge_pdfs.html"
    form_class  = PDFOperationOrderForm
    acceptable_extensions = ["pdf"]
    
    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request):
        files  = request.FILES.getlist("pdfs")
        if files is None:
            return rediret("webapp:merge_pdfs")

        if not self.validate_files(files, self.acceptable_extensions):
            request.session["error_message"] = "Only .pdf files are acceptable"        
            return redirect("webapp:merge_pdfs")

        # saving pdfs
        pdfs = []
        for file in files:
            pdfs.append(UploadedFile.objects.create(type="pdf", file=file))
        order = MultipleFile.objects.create()
        order.files.add(*pdfs)
        task_merge_pdfs(order.id)

        return redirect("webapp:merge_pdfs")