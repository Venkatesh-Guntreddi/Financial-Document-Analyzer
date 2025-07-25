import os
import pdfplumber
import docx
import pandas as pd
import easyocr
from PIL import Image
import numpy as np

# Initialize EasyOCR reader once to avoid re-loading models for every call.
# This will download the 'en' model the first time it's run.
# For CPU-only, use: reader = easyocr.Reader(['en'], gpu=False)
try:
    reader = easyocr.Reader(['en'])
except Exception as e:
    print(f"Warning: EasyOCR failed to initialize. OCR functionality might be limited or unavailable. Error: {e}")
    reader = None

def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    try:
        if ext == ".pdf":
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text += page_text + "\n"
                    elif reader: # Fallback to OCR if direct text extraction yields nothing
                        print(f"Attempting OCR for PDF page {page_num + 1} of {os.path.basename(file_path)}...")
                        # Render page to an image
                        im = page.to_image(resolution=300) # Higher resolution for better OCR
                        # Convert PIL Image to numpy array for EasyOCR
                        img_array = np.array(im.original)
                        # Perform OCR
                        ocr_results = reader.readtext(img_array, detail=0) # detail=0 for simpler output (just text)
                        if ocr_results:
                            text += " ".join(ocr_results) + "\n"
                        else:
                            print(f"No text extracted (digital or OCR) from PDF page {page_num + 1}.")
            
            # If after trying all pages, no text is found, raise an error
            if not text.strip():
                 raise ValueError("PDF contains no readable digital text and OCR extraction failed or yielded no results.")

        elif ext == ".docx":
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif ext in [".xls", ".xlsx"]:
            xls = pd.ExcelFile(file_path)
            for sheet_name in xls.sheet_names:
                df = xls.parse(sheet_name)
                # Convert DataFrame to string, handling potential NaN values better
                text += df.to_string(index=False, header=True, na_rep='').strip() + "\n\n" 
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]: # Handle direct image files with OCR
            if reader:
                print(f"Performing OCR on image file {os.path.basename(file_path)}...")
                img = Image.open(file_path).convert('RGB') # Ensure RGB for consistent processing
                img_array = np.array(img)
                ocr_results = reader.readtext(img_array, detail=0)
                if ocr_results:
                    text += " ".join(ocr_results)
                else:
                    raise ValueError(f"No text found in image file {ext} using OCR.")
            else:
                raise RuntimeError("EasyOCR not initialized. Cannot process image files.")
        else:
            raise ValueError(f"Unsupported file format: {ext}. Supported types: PDF (with OCR fallback), DOCX, TXT, XLS/XLSX, and Image files (PNG, JPG, JPEG, TIFF, BMP) with OCR.")
        
        text = text.strip()
        if not text:
            raise ValueError("No readable text extracted from the file.")

        return text

    except Exception as e:
        # Catch and re-raise more informative errors
        if "No such file or directory" in str(e):
            raise FileNotFoundError(f"File not found: {file_path}") from e
        elif "BadZipFile" in str(e) or "not a valid Word document" in str(e):
            raise ValueError(f"Invalid or corrupted DOCX file: {str(e)}") from e
        elif "XLRDError" in str(e) or "excel file format" in str(e):
            raise ValueError(f"Invalid or corrupted Excel file: {str(e)}") from e
        elif "PDFInfoNotInstalledError" in str(e) or "pdfplumber.pdf.PDFSyntaxError" in str(e):
             raise ValueError(f"Invalid or corrupted PDF file, or necessary PDF tools not installed: {str(e)}") from e
        else:
            raise RuntimeError(f"Failed to extract text from {os.path.basename(file_path)}: {str(e)}")