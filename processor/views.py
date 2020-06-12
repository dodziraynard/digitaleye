from django.shortcuts import render, redirect
from django.views import View
from . models import Order, File
from . tasks import (task_convert_pdf_to_selectable_pdf, 
                    task_remove_pdf_watermark, 
                    task_convet_pdf_to_pngs, 
                    task_merge_pdfs,
                    task_extract_text_from_pdf)

def validate_files(files, acceptable_extensions) -> bool:
    for file in files:
        file_extension = file.name.split(".")[-1]
        if not file_extension in acceptable_extensions:
            return False
        return True

class ConvertionOptions(View):
    template_name = "processor/convertion_options.html"

    def get(self, request):
        return render(request, self.template_name)

class StaticPDFToSelectablePDFView(View):
    template_name = "processor/convert_to_pdf.html"
    acceptable_extensions = ["pdf"]

    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        file = request.FILES.get("pdf")
        if validate_files([file], self.acceptable_extensions):
            new_file = File.objects.create(file=file)
            order = Order.objects.create()
            order.files.add(new_file)
            task_convert_pdf_to_selectable_pdf(order.id)
            # return redirect("processor:convertion_options")
        else:
            request.session["error_message"] = "Only .pdf files are acceptable"
            return redirect("processor:convert_to_selectable_pdf")

        return render(request, self.template_name)


class RemoveWatermarkFromPDFView(View):
    template_name = "processor/remove_water_from_pdf.html"
    acceptable_extensions = ["pdf"]

    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        file = request.FILES.get("pdf")
        if validate_files([file], self.acceptable_extensions):
            new_file = File.objects.create(file=file)
            order = Order.objects.create()
            order.files.add(new_file)
            task_remove_pdf_watermark(order.id)
            # return redirect("processor:convertion_options")
        else:
            request.session["error_message"] = "Only .pdf files are acceptable"
            return redirect("processor:remove_watermark_from_pdf")

        return render(request, self.template_name)


class ConvertPDFToPNGsView(View):
    template_name = "processor/convert_to_png.html"
    acceptable_extensions = ["pdf"]

    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        file = request.FILES.get("pdf")
        if validate_files([file], self.acceptable_extensions):
            new_file = File.objects.create(file=file)
            order = Order.objects.create()
            order.files.add(new_file)
            task_convet_pdf_to_pngs(order.id)
            # return redirect("processor:convertion_options")
        else:
            request.session["error_message"] = "Only .pdf files are acceptable"
            return redirect("processor:convert_pdf_to_pngs")

        return render(request, self.template_name)

class MergePDFFilesView(View):
    template_name = "processor/merge_pdf_files.html"
    acceptable_extensions = ["pdf"]

    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        files = request.FILES.getlist("pdf")
        if validate_files(files, self.acceptable_extensions):
            order = Order.objects.create()
            for file in files:
                new_file = File.objects.create(file=file)
                order.files.add(new_file)
            task_merge_pdfs(order.id)
            # return redirect("processor:convertion_options")
        else:
            request.session["error_message"] = "Only .pdf files are acceptable"
            return redirect("processor:merg_pdfs")

        return render(request, self.template_name)


class ExtractTextFromPDFView(View):
    template_name = "processor/extract_text_from_pdf.html"
    acceptable_extensions = ["pdf"]

    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        file = request.FILES.get("pdf")
        if validate_files([file], self.acceptable_extensions):
            new_file = File.objects.create(file=file)
            order = Order.objects.create()
            order.files.add(new_file)
            task_extract_text_from_pdf(order.id)
            # return redirect("processor:convertion_options")
        else:
            request.session["error_message"] = "Only .pdf files are acceptable"
            return redirect("processor:extract_text_from_pdf")

        return render(request, self.template_name)