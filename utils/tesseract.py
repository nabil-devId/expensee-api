# import io
# import re
# from PIL import Image, ImageFilter, ImageEnhance
# from fastapi import HTTPException
# import numpy as np
# import pytesseract
# from utils.model.ExpenseData import ExpenseData, ExpenseItem

# # Configuration
# import os

# # Get tesseract path from environment variable or use default
# TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "/usr/bin/tesseract")
# pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# # Temporary directory for file processing
# TEMP_DIR = os.environ.get("TEMP_DIR", "/app/temp")
# os.makedirs(TEMP_DIR, exist_ok=True)

# def preprocess_image(img_data: bytes) -> str:
#     """Preprocess image to improve OCR results using PIL"""
#     try:
#         # Open Image using PIL
#         img = Image.open(io.BytesIO(img_data))

#         # Convert to RGB if image is in RGBA mode (handles transparent background)
#         if img.mode == 'RGBA':
#             img = img.convert('RGB')

#         # Step 1: Resize if image is very large to improve processing speed
#         max_dimension = 2048
#         width, height = img.size
#         if width > max_dimension or height > max_dimension:
#             if width > height:
#                 new_width = max_dimension
#                 new_height = int(height * (max_dimension / width))
#             else:
#                 new_height = max_dimension
#                 new_width = int(width * (max_dimension / height))
#             img = img.resize((new_width, new_height), Image.LANCZOS)

#         # Step 2: Convert to grayscale
#         img = img.convert('L')

#         # Step 3: Apply adaptive thresholding using local means
#         # Convert PIL image to numpy array for processing
#         img_np = np.array(img)

#         # Calculate local mean using a moving window
#         window_size = 15
#         # Use scipy's generic_filter if available, otherwise use a simple approach

#         try:
#             from scipy.ndimage import generic_filter
#             local_mean = generic_filter(img_np, np.mean, size=window_size)
#         except ImportError:
#             local_mean = img_np.copy()
#             for i in range(img_np.shape[0]):
#                 for j in range(img_np.shape[1]):
#                     # Calculate window boundaries
#                     i_min = max(0, i - window_size//2)
#                     i_max = min(img_np.shape[0], i + window_size//2)
#                     j_min = max(0, j - window_size//2)
#                     j_max = min(img_np.shape[1], j + window_size//2)
#                     # Calculate local mean
#                     local_mean[i, j] = np.mean(img_np[i_min:i_max, j_min:j_max])

#         # Apply threshold (pixel value > local mean - constant)
#         constant = 10
#         img_threshold = np.where(img_np > local_mean - constant, 255, 0).astype(np.uint8)

#         # Convert back to PIL image
#         img = Image.fromarray(img_threshold)

#         # Step 4: Apply noise reduction
#         img = img.filter(ImageFilter.MedianFilter(size=3))

#         # Step 5: Enhance contrast
#         enhancer = ImageEnhance.Contrast(img)
#         img = enhancer.enhance(2.0)

#         # Sharpen to enhance text edges
#         img = img.filter(ImageFilter.SHARPEN)

#         return img

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error processing image: {e}")

    

# def extract_text_from_image(img_data: bytes):
#     """Extract text from image using Tesseract OCR with preprocessing"""
#     try:
#         # Preprocess the image
#         img = preprocess_image(img_data)

#         # Apply additional OCR-specific settings
#         custom_config = r'--oem 3 --psm 6' # OCR Engine Mode & Page Segmentation Mode

#         # Use Tesseract to extract text with additional data
#         ocr_data = pytesseract.image_to_data(img, config=custom_config, output_type=pytesseract.Output.DICT)

#         # Combine text and calculate average confidence
#         text = " ".join([word for word in ocr_data['text'] if word.strip()])
#         confidences = [conf for conf, text in zip(ocr_data['conf'], ocr_data['text']) if text.strip() and conf != -1]

#         # If no valid confidence scores, default to 0
#         confidence = sum(confidences) / len(confidences) if confidences else 0

#         return text, confidence
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"OCR processing error: {str(e)}")
    
# def parse_receipt_text(text: str, confidence: float):
#     """Convert OCR text to structured expense data"""
#     # Extract all relevant information
#     date = extract_date(text)
#     time = extract_time(text)
#     total_amount = extract_total_amount(text)
#     merchant = extract_merchant(text)
#     items = extract_items(text)

#     # Create expense data object
#     expense_data = ExpenseData(
#         merchant=merchant,
#         date=date,
#         time=time,
#         total_amount=total_amount,
#         items=items,
#         receipt_text=text,
#         confidence=confidence
#     )
#     return expense_data

# def extract_date(text: str):
#     """Extract date from receipt text"""
#     # Common date patterns (MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD, etc.)
#     date_patterns = [
#         r'\b(0[1-9]|1[0-2])/(0[1-9]|[12][0-9]|3[01])/(\d{4})\b',  # MM/DD/YYYY
#         r'\b(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/(\d{4})\b',  # DD/MM/YYYY
#         r'\b(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])\b',  # YYYY-MM-DD
#         r'\b(0[1-9]|[12][0-9]|3[01])-(0[1-9]|1[0-2])-(\d{4})\b',  # DD-MM-YYYY
#         r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (0[1-9]|[12][0-9]|3[01])[,]? \d{4}\b'  # Month DD, YYYY
#     ]
    
#     for pattern in date_patterns:
#         match = re.search(pattern, text, re.IGNORECASE)
#         if match:
#             return match.group(0)
#     return None

# def extract_time(text: str):
#     """Extract time from receipt text"""
#     # Match patterns like 14:30 or 2:30 PM
#     time_patterns = [
#         r'\b([01]?[0-9]|2[0-3]):([0-5][0-9])(?:\s*([AP]M))?\b',
#         r'\b([01]?[0-9]|2[0-3])([0-5][0-9])(?:\s*([AP]M))?\b'  # Without colon
#     ]
    
#     for pattern in time_patterns:
#         match = re.search(pattern, text, re.IGNORECASE)
#         if match:
#             return match.group(0)
#     return None

# def extract_total_amount(text: str):
#     """Extract total amount from receipt"""
#     # Look for patterns like "Total: $123.45" or "TOTAL $123.45"
#     total_patterns = [
#         r'(?:total|amt|amount)[^$\d]*?[$]?(\d+\.\d{2})[\s\r\n]',
#         r'(?:total|amt|amount)[^$\d]*?[$]?(\d+\,\d{2})[\s\r\n]',
#         r'[$]?(\d+\.\d{2})(?:[^$\d]*?total)',
#         r'[$]?(\d+\,\d{2})(?:[^$\d]*?total)'
#     ]
    
#     for pattern in total_patterns:
#         match = re.search(pattern, text, re.IGNORECASE)
#         if match:
#             # Replace comma with dot and convert to float
#             amount = match.group(1).replace(',', '.')
#             return float(amount)
    
#     # If no total found, look for the last currency amount in the receipt
#     currency_pattern = r'[$]?(\d+\.\d{2})'
#     matches = re.findall(currency_pattern, text)
#     if matches:
#         return float(matches[-1])  # Return the last currency amount
    
#     return 0.0

# def extract_merchant(text: str):
#     """Extract merchant name from receipt"""
#     # Merchant name is usually at the top of the receipt
#     lines = text.strip().split('\n')
#     if lines:
#         # Take first non-empty line as potential merchant
#         for line in lines[:4]:  # Check first 4 lines
#             if line.strip() and not re.match(r'^\d+|\breceipt\b|^tel|^fax', line.lower()):
#                 return line.strip()
    
#     return None

# def extract_payment_method(text: str):
#     """Extract payment method from receipt"""
#     payment_patterns = [
#         r'\b(visa|mastercard|amex|american express|discover|cash|check|debit|credit card)\b',
#         r'\bcard\s+ending\s+in\s+\d{4}\b'
#     ]
    
#     for pattern in payment_patterns:
#         match = re.search(pattern, text, re.IGNORECASE)
#         if match:
#             return match.group(0)
    
#     return None

# def extract_items(text: str):
#     """Extract line items from receipt"""
#     items = []
    
#     # Split text into lines
#     lines = text.strip().split('\n')
    
#     # Identify potential item lines (looking for price patterns)
#     price_pattern = r'(\d+\.\d{2})'
#     item_pattern = r'(.+?)\s+(\d+(?:\.\d+)?)\s+(?:x\s+)?[$]?(\d+\.\d{2})\s+[$]?(\d+\.\d{2})'
    
#     for line in lines:
#         # Check if line contains a price
#         if re.search(price_pattern, line):
#             # Try to match full item pattern (name, quantity, unit price, total)
#             match = re.search(item_pattern, line)
#             if match:
#                 name, quantity, unit_price, total = match.groups()
#                 items.append(ExpenseItem(
#                     name=name.strip(),
#                     quantity=float(quantity),
#                     unit_price=float(unit_price),
#                     total_price=float(total)
#                 ))
#             else:
#                 # Simplified pattern for items without clear quantity
#                 simple_match = re.match(r'(.+?)\s+[$]?(\d+\.\d{2})$', line.strip())
#                 if simple_match:
#                     name, price = simple_match.groups()
#                     price = float(price)
#                     items.append(ExpenseItem(
#                         name=name.strip(),
#                         quantity=1.0,
#                         unit_price=price,
#                         total_price=price
#                     ))
    
#     return items