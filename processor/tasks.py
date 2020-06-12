"""
This module is responsible for processing files using the celery worker
"""
import os
import shutil
import cv2
import fitz
import sys 
import pytesseract 
import numpy as np
from celery import shared_task
from PIL import Image 
from pdf2image import convert_from_bytes
from PyPDF2 import PdfFileMerger
from django.utils import timezone
from django.core.files.storage import FileSystemStorage
from django.contrib.sites.models import Site
from . models import Order


pytesseract.pytesseract.tesseract_cmd = "C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe"

# A function for setting the task processing status for retrieve in the front end
def set_task_state(task, message, current, total=5, info="Processing"):
    try:
        task.update_state(
            state = message,
            meta = {
                "current": str(current),
                "total"  : total,
                "info"   : info
            }
        )	
    except Exception as e:
        return

def extract_pages_from_pdf(self, pdf_file_path, output_dir):
    pdf_file = fitz.open(pdf_file_path)
    page_count = pdf_file.pageCount
    fs = FileSystemStorage()
    output_images = []
    for i in range(page_count): 
        filename = output_dir+"/page_"+str(i)+".png"
        page = pdf_file.loadPage(i)
        pix = page.getPixmap()
        pix.writePNG(filename)
        output_images.append(filename)
        info = str(i+1) + " pages found"
        set_task_state(self, "EXTRACTING PAGES", 3, info=info)
    return output_images

def convert_images_to_pdf(self, images, output_dir):
    pdfs = []
    for page_number, image in enumerate(images):
        pdf = pytesseract.image_to_pdf_or_hocr(Image.open(image))
        filename = output_dir+"/page_"+str(page_number)+".pdf"
        with open(filename, "wb") as file:
            file.write(pdf)
            pdfs.append(filename)
    return pdfs

def remove_watermark_from_images(self, images):
    for filename in images:
        # Load the image
        img = cv2.imread(filename)

        # Convert the image to grayscale
        gr = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Make a copy of the grayscale image
        bg = gr.copy()

        # Apply morphological transformations
        for i in range(5):
            kernel2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                                (2 * i + 1, 2 * i + 1))
            bg = cv2.morphologyEx(bg, cv2.MORPH_CLOSE, kernel2)
            bg = cv2.morphologyEx(bg, cv2.MORPH_OPEN, kernel2)

        # Subtract the grayscale image from its processed copy
        dif = cv2.subtract(bg, gr)

        # Apply thresholding
        bw = cv2.threshold(dif, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        dark = cv2.threshold(bg, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

        # Extract pixels in the dark region
        darkpix = gr[np.where(dark > 0)]

        # Threshold the dark region to get the darker pixels inside it
        darkpix = cv2.threshold(darkpix, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        try:
            # Paste the extracted darker pixels in the watermark region
            bw[np.where(dark > 0)] = darkpix.T
        except AttributeError:
            return
        cv2.imwrite(filename, bw)
    return images

def merge_pdfs(pdfs, output_file_name):
    merger = PdfFileMerger()
    for pdf in pdfs:
        merger.append(pdf)
    merger.write(output_file_name)
    merger.close()

@shared_task(bind=True)
def task_convert_pdf_to_selectable_pdf(self, order_id):
    print("REMOVE SELECTABLE")
    fs = FileSystemStorage()
    order = Order.objects.get(pk=order_id)
    pdf_file_path = order.files.first().file.file

    # Make temp directory for storing pdf images
    dir_name = "selectable_pdf"+str(order.id)
    os.mkdir(fs.path("temp/"+dir_name))

    # Extracting the pages in the pdf files as images
    set_task_state(self, "EXTRACTING PAGES", 3)
    output_dir = fs.path("temp/"+dir_name)
    images = extract_pages_from_pdf(self, pdf_file_path, output_dir)

    # Convert images to pdf
    pdfs = convert_images_to_pdf(self, images, output_dir)

    # Merge the pdfs back
    uploaded_file_name = "".join(order.files.first().file.name.split("/")[-1])
    output_file_name =  fs.path("processed")+"\\"+uploaded_file_name
    merge_pdfs(pdfs, output_file_name)
    
    # Getting the resultant file url
    domain = Site.objects.get(name="production").domain
    url = f"{domain}{'/resources/processed/'+uploaded_file_name}"
    return url

@shared_task(bind=True)
def task_remove_pdf_watermark(self, order_id):
    print("REMOVE WATERMARK")
    fs = FileSystemStorage()
    order = Order.objects.get(pk=order_id)
    pdf_file_path = order.files.first().file.file

    # Make temp directory for storing pdf images
    dir_name = "remove_watermark"+str(order.id)
    os.mkdir(fs.path("temp/"+dir_name))

    # Extracting the pages in the pdf files as images
    set_task_state(self, "EXTRACTING PAGES", 3)
    output_dir = fs.path("temp/"+dir_name)
    images = extract_pages_from_pdf(self, pdf_file_path, output_dir)

    # Remove watermark in images
    images = remove_watermark_from_images(self, images)

    # Convert images to pdf
    pdfs = convert_images_to_pdf(self, images, output_dir)

    # Merge the pdfs back
    uploaded_file_name = "".join(order.files.first().file.name.split("/")[-1])
    output_file_name =  fs.path("processed")+"\\"+uploaded_file_name
    merge_pdfs(pdfs, output_file_name)

    # Getting the resultant file url
    domain = Site.objects.get(name="production").domain
    url = f"{domain}{'/resources/processed/'+uploaded_file_name}"
    print(url)
    return url

@shared_task(bind=True)
def task_convet_pdf_to_pngs(self, order_id):
    print("CONVERT TO PNGS")
    fs = FileSystemStorage()
    order = Order.objects.get(pk=order_id)
    pdf_file_path = order.files.first().file.file

    # Make temp directory for storing pdf images
    dir_name = "pngs"+str(order.id)
    os.mkdir(fs.path("temp/"+dir_name))

    # Extracting the pages in the pdf files as images
    set_task_state(self, "EXTRACTING PAGES", 3)
    output_dir = fs.path("temp/"+dir_name)
    images = extract_pages_from_pdf(self, pdf_file_path, output_dir)

    # Zipping images
    uploaded_file_name = "".join(order.files.first().file.name.split("/")[-1].split(".")[:1])
    output_file_name =  fs.path("processed")+"\\"+uploaded_file_name
    shutil.make_archive(output_file_name, 'zip', output_dir)

    # Getting the resultant file url
    domain = Site.objects.get(name="production").domain
    url = f"{domain}{'/resources/processed/'+uploaded_file_name+'.zip'}"
    print(url)
    return url

@shared_task(bind=True)
def task_merge_pdfs(self, order_id):
    print("MERGING PDFS")
    fs = FileSystemStorage()
    order = Order.objects.get(pk=order_id)
    pdfs_files = order.files.all()
    pdfs = []
    for pdf in pdfs_files:
        pdfs.append(pdf.file.file)

    # Merging
    uploaded_file_name = "merged__"+"".join(order.files.first().file.name.split("/")[-1])
    output_file_name =  fs.path("processed")+"\\"+uploaded_file_name
    merge_pdfs(pdfs, output_file_name)

    # Getting the resultant file url
    domain = Site.objects.get(name="production").domain
    url = f"{domain}{'/resources/processed/'+uploaded_file_name}"
    print(url)
    return url

@shared_task(bind=True)
def task_extract_text_from_pdf(self, order_id):
    print("EXTRACTING TEXTS")
    fs = FileSystemStorage()
    order = Order.objects.get(pk=order_id)
    pdf_file_path = order.files.first().file.file

    # Make temp directory for storing pdf images
    dir_name = "texts"+str(order.id)
    os.mkdir(fs.path("temp/"+dir_name))

    # Extracting the pages in the pdf files as images
    set_task_state(self, "EXTRACTING PAGES", 3)
    output_dir = fs.path("temp/"+dir_name)
    images = extract_pages_from_pdf(self, pdf_file_path, output_dir)

    text = ""
    for image in images:
        string = pytesseract.image_to_string(Image.open(image))
        text += string + "\n\n"
    
    # Writing into text file
    uploaded_file_name = "".join(order.files.first().file.name.split("/")[-1].split(".")[:1])
    output_file_name =  fs.path("processed")+"\\"+uploaded_file_name+".txt"
    with open(output_file_name, "w") as file:
        file.write(text)

    # Getting the resultant file url
    domain = Site.objects.get(name="production").domain
    url = f"{domain}{'/resources/processed/'+uploaded_file_name+'.txt'}"
    print(url)
    return url