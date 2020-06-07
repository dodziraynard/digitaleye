from celery import shared_task
from webapp.models import PDFOperationOrder, ImageOperationOrder, MultipleFile
from PIL import Image 
import pytesseract 
import sys 
from django.utils import timezone
from pdf2image import convert_from_bytes
import os, shutil
import cv2
import numpy as np
from PyPDF2 import PdfFileMerger
from django.core.files.storage import FileSystemStorage
import fitz


pytesseract.pytesseract.tesseract_cmd = "C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe"


@shared_task(bind=True)
def images_to_pdf_task(self, order_id):
	order = ImageOperationOrder.objects.get(pk=order_id)
	fs = FileSystemStorage()
	dir_name = "images_to_pdf"+str(order_id)
	try:
		os.mkdir(fs.path("temp/"+dir_name))
	except Exception as e:
		print(e)
	
	images = order.images.all()
	set_task_state(self, "EXTRACTING PAGES", 1, total=2)
	for page, image in enumerate(images):
		absolute_file_path = image.file.file
		pdf = pytesseract.image_to_pdf_or_hocr(Image.open(absolute_file_path))

		fs = FileSystemStorage()	
		fn = fs.path("temp/"+dir_name)+"/page_"+str(page)+".pdf"
		with open(fn, "wb") as file:
			file.write(pdf)
	
	set_task_state(self, "MERGING PDFS", 2, total=2)
	result_path = merge_pdfs(dir_name, images.count())
	return result_path

@shared_task(bind=True)
def pdf_to_pngs(self, order_id):
	set_task_state(self, "STARTED", 1)
	order = PDFOperationOrder.objects.get(pk=order_id)
	fs = FileSystemStorage()

	set_task_state(self, "EXTRACTING PAGES", 3)
	pdffile_path = order.file.file
	pdffile = fitz.open(pdffile_path)
	page_count = pdffile.pageCount
	
	uploaded_file_name = "".join(order.file.name.split("/")[-1].split(".")[:1])
	make_temp_directories(uploaded_file_name)
	
	#Convert pages to images and store in the temp/dir_name_raw directory
	set_task_state(self, "CONVERTING...", 3)
	convert_pdf_to_images(self, uploaded_file_name, pdffile)
	
	dir_name = fs.path("temp/"+uploaded_file_name+"_raw")
	if order.remove_bg:
		for i in range(0, page_count): 
			filename = fs.path("temp/"+uploaded_file_name+"_raw")+"/page_"+str(i)+".png"
			info = "page " + str(i+1) + " of " + str(page_count) + " pages"
			set_task_state(self, "REMOVING BACKGROUND", 4, info=info)
			new_image =  remove_background(uploaded_file_name, filename, i)
			if new_image: 
				filename = new_image
		
		dir_name = fs.path("temp/"+uploaded_file_name+"_nbg")
	
	output_dir_name = uploaded_file_name
	zip_directory(output_dir_name, dir_name)
	remove_temp_dirs()

@shared_task(bind=True)
def static_pdf_to_selectable_pdf(self, order_id):
	set_task_state(self, "STARTED", 1)
	order = PDFOperationOrder.objects.get(pk=order_id)
	process(self, order)	
	return order_id

def process(self, order):
	fs = FileSystemStorage()	
	set_task_state(self, "GETTING PAGES", 2)
	dir_name = "".join(order.file.name.split("/")[-1].split(".")[:1])
	
	make_temp_directories(dir_name)

	set_task_state(self, "EXTRACTING PAGES", 3)
	pdffile_path = order.file.file
	pdffile = fitz.open(pdffile_path)
	page_count = pdffile.pageCount
	
	#Convet pages to images and store in the temp directory
	convert_pdf_to_images(self, dir_name, pdffile)

	set_task_state(self, "ANALYZING THE PAGES", 3)
	for i in range(0, page_count): 
		filename = fs.path("temp/"+dir_name+"_raw")+"/page_"+str(i)+".png"
		if order.remove_bg:
			info = "page " + str(i+1) + " of " + str(page_count) + " pages"
			set_task_state(self, "REMOVING BACKGROUND", 4, info=info)
			new_image =  remove_background(dir_name, filename, i)
			if new_image: 
				filename = new_image
		
		# Convert to pdf
		convert_to_pdf(self, dir_name, filename, page_number=i)

	# merge pdfs
	set_task_state(self, "MERGING PDFS", 5)
	merge_pdfs(dir_name, page_count)

def convert_pdf_to_images(self, dir_name, pdffile):
	fs = FileSystemStorage()	
	for i in range(pdffile.pageCount): 
		filename = fs.path("temp/"+dir_name+"_raw")+"/page_"+str(i)+".png"
		page = pdffile.loadPage(i)
		pix = page.getPixmap()
		pix.writePNG(filename)
		info = str(i+1) + " pages found"
		set_task_state(self, "EXTRACTING PAGES", 3, info=info)

def convert_to_pdf(self, dir_name, filename, page_number):
	pdf = pytesseract.image_to_pdf_or_hocr(Image.open(filename))
	fs = FileSystemStorage()	
	fn = fs.path("temp/"+dir_name)+"/page_"+str(page_number)+".pdf"
	with open(fn, "wb") as file:
		file.write(pdf)

def remove_background(dir_name, filename, page):
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
	
	fs = FileSystemStorage()
	new_name = fs.path("temp/"+dir_name+"_nbg")+"/page_"+str(page)+".png"
	cv2.imwrite(new_name, bw)
	return new_name


def merge_pdfs(dir_name, page_count):
	merger = PdfFileMerger()
	fs = FileSystemStorage()

	pdfs = []
	for i in range(0, page_count):
		filename = fs.path("temp/"+dir_name)+"/page_"+str(i)+".pdf"
		pdfs.append(filename)

	for pdf in pdfs:
		merger.append(pdf)
	result_path = fs.path("processed")+"/"+dir_name+".pdf"
	merger.write(result_path)
	merger.close()
	return result_path
	remove_temp_dirs()

def zip_directory(output_dir_name, input_dir_name):
	fs = FileSystemStorage()
	output_filename = fs.path("processed")+"/"+output_dir_name
	shutil.make_archive(output_filename, 'zip', input_dir_name)

#TODO: check for idle celery state
def remove_temp_dirs():
	fs = FileSystemStorage()
	tempdir = fs.path("temp") 
	dirs = os.listdir(tempdir)
	for directory in dirs:
		try:
			shutil.rmtree(fs.path("temp/"+directory))
		except Exception as e:
			print(e)

def make_temp_directories(dir_name):
	fs = FileSystemStorage()
	# try:
	os.mkdir(fs.path("temp/"+dir_name))
	os.mkdir(fs.path("temp/"+dir_name+"_raw"))
	os.mkdir(fs.path("temp/"+dir_name+"_nbg"))
	# except Exception as e:
	# 	print(e)

def set_task_state(task, message, current, total=5, info=""):
	task.update_state(
		state = message,
		meta = {
			"current": str(current),
			"total"  : total,
			"info"   : info
		}
	)	

@shared_task(bind=True)
def task_merge_pdfs(self, order_id):
	merger = PdfFileMerger()
	fs = FileSystemStorage()
	order = MultipleFile.objects.get(id=order_id)
	
	pdfs = []
	for file in order.files.all():
		filename = fs.path(str(file.file))
		pdfs.append(filename)

	for pdf in pdfs:
		merger.append(pdf)
	new_name = order_id	
	result_path = fs.path("processed")+"/"+str(new_name)+".pdf"
	merger.write(result_path)
	merger.close()
	print(result_path)
	return result_path
