import logging
from typing import Any, Dict
from google.genai import types

logger = logging.getLogger(__name__)

import io
import os
import uuid
import datetime
import json
from PIL import Image
from typing import List

from google import genai
from schemas.receipt import OCRResultCategory

from .gcs import GCSUploader  # Import GCSUploader

# --- Configuration for GCS and Gemini ---
# These values are loaded from environment variables.
# Ensure GCS_PREPROCESSED_IMAGE_BUCKET and GEMINI_API_KEY are set in your deployment environment.

GCS_BUCKET_NAME = "expense_ocr_receipt"
GEMINI_API_KEY = "AIzaSyAt6WqfZj4nsajkWVH7cpSiTAVGHpDLbhY"

# Initial check at module load time. Functions using these will also check and raise errors if missing.
if not GCS_BUCKET_NAME:
    logger.warning(
        "GCS_PREPROCESSED_IMAGE_BUCKET environment variable is not set at module load time. "
        "Image preprocessing and GCS-dependent functions might fail if not configured at runtime."
    )

if not GEMINI_API_KEY:
    logger.warning(
        "GEMINI_API_KEY environment variable is not set at module load time. "
        "Gemini API calls will fail if not configured at runtime."
    )

# --- End Configuration ---

def process_receipt_with_gemini(image_bytes_for_gemini: bytes) -> Dict[str, Any]:
    """Processes a receipt image (optionally fetching from GCS after preprocessing)
       and extracts information using Gemini.
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not configured.")
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    if not GCS_BUCKET_NAME:
        logger.error("GCS_BUCKET_NAME is not configured for GCSUploader.")
        raise ValueError("GCS_BUCKET_NAME is not configured.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    # model = "gemini-2.0-flash-lite"  # cheapest model
    model = "gemini-2.5-pro-preview-06-05"

    json_schema = """
    {
        'merchant_name': [string],
        'total_amount': [number string],
        'transaction_date': [string],
        'payment_method': [string],
        'total_discount': [positive number string],
        'tax': [number string],
        'items': [
            {
            'name': [string],
            'quantity': [number string],
            'price': [number string],
            'total_price': [number string],
            'discount': [positive number string],
            },
            {
            'name': [string],
            'quantity': [number string],
            'price': [number string],
            'total_price': [number string],
            'discount': [positive number string],
            }
        ]
    }
    """
    
    prompt_text = f"""Extract receipt to JSON:
                {json_schema}
                Rules: Use integers for money. transaction_date must formatted YYYY-MM-DD dates, if the data doesnt complete date, make it with yours. Keep capitalization. Skip empty fields. JSON only. merchant name is required, find for this pattern "nama merchant", the total usually using this pattern "total", "grand total", or "total amount". The date usually using this pattern "tanggal" or "date". The time usually using this pattern "jam" or "time". The cashier usually using this pattern "kasir" or "cashier". The item name usually using this pattern "menu" or "item name". The item price usually using this pattern "harga" or "price". The item quantity usually using this pattern "qty" or "quantity". The payment method usually using this pattern "payment method" or "payment type". The payment amount usually using this pattern "amount" or "total amount" and it should be not less than 100.
                the "total_amount" should be sum of all items price, if the the "total_amount" and sum of all items price doesnt match, try to re-read or recalculate the items price.
                """

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_bytes(
                    mime_type="image/png",
                    data=image_bytes_for_gemini,
                ),
                types.Part(text=prompt_text),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        # Assuming _parse_response handles the actual parsing of response.text to dict
        # If Gemini is configured for JSON output, response.text might already be a JSON string.
        return _parse_response(response.text)
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        # Consider how to handle Gemini API errors, e.g., return a specific error structure or re-raise
        raise

def _parse_response(response_text):
    try:
        # Remove markdown formatting if present
        clean_text = response_text.replace('```json', '').replace('```', '').strip()
        # Parse JSON
        data = json.loads(clean_text)
        return data
    except Exception as e:
        return {'error': f"Error parsing response: {str(e)}"}


def generate_unique_filename(extension='.png'):
    """Generate a unique filename using UUID and timestamp"""
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]  # Use first 8 chars of UUID
    return f"{timestamp}_{unique_id}{extension}"


def preprocess_image(image_bytes: bytes) -> bytes:
    # Generate a unique .png filename for this image
    unique_png_filename = generate_unique_filename(extension='.png')

    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ('RGBA', 'LA', 'P'):  # Convert to RGB if it has alpha or is palette-based
        img = img.convert('RGB')

    temp_buffer_check_initial_size = io.BytesIO()
    img.save(temp_buffer_check_initial_size, format="PNG")
    
    img_to_resize = img
    if temp_buffer_check_initial_size.tell() > 400 * 1024: 
        try:
            img_to_resize = img.resize((max(1, img.width // 2), max(1, img.height // 2)), Image.Resampling.LANCZOS)
        except ValueError:
            print(f"Warning: Initial image dimensions ({img.width}x{img.height}) too small for halving. Proceeding with original.")

    processed_bytes_buffer = io.BytesIO()
    while True:
        processed_bytes_buffer.seek(0)
        processed_bytes_buffer.truncate()
        img_to_resize.save(processed_bytes_buffer, format="PNG")
        
        current_size_bytes = processed_bytes_buffer.tell()
        if current_size_bytes <= 400 * 1024:
            break

        if img_to_resize.width <= 50 or img_to_resize.height <= 50:
            print(f"Warning: Image resized to {img_to_resize.width}x{img_to_resize.height} ({current_size_bytes // 1024}KB) but still might be over 400KB. Using current state.")
            break
        
        new_width = max(1, img_to_resize.width // 2)
        new_height = max(1, img_to_resize.height // 2)

        if new_width == img_to_resize.width and new_height == img_to_resize.height:
            print(f"Warning: Cannot resize image further from {img_to_resize.width}x{img_to_resize.height}. Using current state.")
            break
        try:
            img_to_resize = img_to_resize.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except ValueError:
            print(f"Warning: Cannot resize image further from {img_to_resize.width}x{img_to_resize.height} due to dimensions. Using current state.")
            break
    
    processed_bytes = processed_bytes_buffer.getvalue()
    return processed_bytes


def upload_to_gcs(processed_bytes: bytes) -> str:
    try:
        # Check if GCS_BUCKET_NAME global exists and is not a placeholder or empty
        if 'GCS_BUCKET_NAME' not in globals() or not GCS_BUCKET_NAME or GCS_BUCKET_NAME == "your-default-fallback-bucket" or GCS_BUCKET_NAME == "your-gcs-bucket-name-for-preprocessed-images":
            current_gcs_bucket_name = os.environ.get("GCS_PREPROCESSED_IMAGE_BUCKET")
            if not current_gcs_bucket_name:
                raise ValueError(
                    "GCS bucket name is not configured. "
                    "Set GCS_BUCKET_NAME at module level or GCS_PREPROCESSED_IMAGE_BUCKET environment variable."
                )
        else:
            current_gcs_bucket_name = GCS_BUCKET_NAME
    except NameError:  # Fallback if GCS_BUCKET_NAME global variable doesn't exist at all
        current_gcs_bucket_name = os.environ.get("GCS_PREPROCESSED_IMAGE_BUCKET")
        if not current_gcs_bucket_name:
            raise ValueError(
                "GCS_BUCKET_NAME global variable not found and GCS_PREPROCESSED_IMAGE_BUCKET env var is not set."
            )

    gcs_uploader = GCSUploader(bucket_name=current_gcs_bucket_name)
    unique_png_filename = generate_unique_filename(extension='.png')
    destination_blob_name = f"preprocessed/{unique_png_filename}"
    gcs_uri = gcs_uploader.upload_bytes(
        data=processed_bytes,
        destination_blob_name=destination_blob_name,
        content_type="image/png"
    )
    print(f"Preprocessed image uploaded to GCS: {gcs_uri}")
    return gcs_uri

# def preprocess_image(image_bytes: bytes) -> str:
#     """
#     Preprocess the image (resize, ensure <400KB PNG) and upload to GCS.

#     Args:
#         image_bytes: Raw image bytes.

#     Returns:
#         str: The GCS URI of the preprocessed image (e.g., "gs://bucket_name/preprocessed/filename.png").

#     Raises:
#         ValueError: If GCS_BUCKET_NAME is not properly configured.
#         Exception: If image processing or GCS upload fails.
#     """
#     # Access GCS_BUCKET_NAME (expected to be a module-level global, configured via env var ideally)
#     # This function relies on GCS_BUCKET_NAME being defined in the module's global scope.
#     try:
#         # Check if GCS_BUCKET_NAME global exists and is not a placeholder or empty
#         if 'GCS_BUCKET_NAME' not in globals() or not GCS_BUCKET_NAME or GCS_BUCKET_NAME == "your-default-fallback-bucket" or GCS_BUCKET_NAME == "your-gcs-bucket-name-for-preprocessed-images":
#             current_gcs_bucket_name = os.environ.get("GCS_PREPROCESSED_IMAGE_BUCKET")
#             if not current_gcs_bucket_name:
#                 raise ValueError(
#                     "GCS bucket name is not configured. "
#                     "Set GCS_BUCKET_NAME at module level or GCS_PREPROCESSED_IMAGE_BUCKET environment variable."
#                 )
#         else:
#             current_gcs_bucket_name = GCS_BUCKET_NAME
#     except NameError:  # Fallback if GCS_BUCKET_NAME global variable doesn't exist at all
#         current_gcs_bucket_name = os.environ.get("GCS_PREPROCESSED_IMAGE_BUCKET")
#         if not current_gcs_bucket_name:
#             raise ValueError(
#                 "GCS_BUCKET_NAME global variable not found and GCS_PREPROCESSED_IMAGE_BUCKET env var is not set."
#             )

#     gcs_uploader = GCSUploader(bucket_name=current_gcs_bucket_name)

#     try:
#         # Generate a unique .png filename for this image
#         unique_png_filename = generate_unique_filename(extension='.png')

#         img = Image.open(io.BytesIO(image_bytes))
#         if img.mode in ('RGBA', 'LA', 'P'): # Convert to RGB if it has alpha or is palette-based
#             img = img.convert('RGB')

#         temp_buffer_check_initial_size = io.BytesIO()
#         img.save(temp_buffer_check_initial_size, format="PNG")
        
#         img_to_resize = img
#         if temp_buffer_check_initial_size.tell() > 400 * 1024: 
#             try:
#                 img_to_resize = img.resize((max(1, img.width // 2), max(1, img.height // 2)), Image.Resampling.LANCZOS)
#             except ValueError:
#                 print(f"Warning: Initial image dimensions ({img.width}x{img.height}) too small for halving. Proceeding with original.")

#         processed_bytes_buffer = io.BytesIO()
#         while True:
#             processed_bytes_buffer.seek(0)
#             processed_bytes_buffer.truncate()
#             img_to_resize.save(processed_bytes_buffer, format="PNG")
            
#             current_size_bytes = processed_bytes_buffer.tell()
#             if current_size_bytes <= 400 * 1024:
#                 break

#             if img_to_resize.width <= 50 or img_to_resize.height <= 50:
#                 print(f"Warning: Image resized to {img_to_resize.width}x{img_to_resize.height} ({current_size_bytes // 1024}KB) but still might be over 400KB. Using current state.")
#                 break
            
#             new_width = max(1, img_to_resize.width // 2)
#             new_height = max(1, img_to_resize.height // 2)

#             if new_width == img_to_resize.width and new_height == img_to_resize.height:
#                 print(f"Warning: Cannot resize image further from {img_to_resize.width}x{img_to_resize.height}. Using current state.")
#                 break
#             try:
#                 img_to_resize = img_to_resize.resize((new_width, new_height), Image.Resampling.LANCZOS)
#             except ValueError:
#                 print(f"Warning: Cannot resize image further from {img_to_resize.width}x{img_to_resize.height} due to dimensions. Using current state.")
#                 break
        
#         processed_bytes = processed_bytes_buffer.getvalue()

#         destination_blob_name = f"preprocessed/{unique_png_filename}"
#         gcs_uri = gcs_uploader.upload_bytes(
#             data=processed_bytes,
#             destination_blob_name=destination_blob_name,
#             content_type="image/png"
#         )
#         print(f"Preprocessed image uploaded to GCS: {gcs_uri}")

#         return gcs_uri

    # except Exception as e:
    #     print(f"Error in preprocess_image: {str(e)}")
    #     raise

def find_category(expense_history_raw: str, category: List[str]) -> OCRResultCategory:
    client = genai.Client(
        api_key="AIzaSyAt6WqfZj4nsajkWVH7cpSiTAVGHpDLbhY",
    )
    model = "gemini-2.0-flash-lite"

    json_schema = """
    {
        "category_name": "string",
        "category_id": "string", 
        "is_user_category": boolean
    }
    """

    full_prompt = f"""
                    Categorize this transaction using the provided categories. Prioritize user-defined categories over predefined ones. Return only JSON format.
                    Available Categories:
                    ${str(category)}
                    Transaction to Categorize:
                    ${str(expense_history_raw)}
                    Required Response Format:
                    ${str(json_schema)}
                """
    print(f"category_prompt: {full_prompt}")
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part(text=full_prompt),
            ],
        )
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
    )

    result = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )
    result = _parse_response(result.text)
    # return _parse_response(result.text)
    # convert to dict
    return OCRResultCategory(
        category_id=result['category_id'],
        category_name=result['category_name'],
        is_user_category=result['is_user_category'],
    )
