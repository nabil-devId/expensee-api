import logging
from typing import Any, Dict
from google.genai import types
import base64
logger = logging.getLogger(__name__)

# To run this code you need to install the following dependencies:
# pip install google-genai

import io
import os
import uuid
import datetime
import json
from PIL import Image
from typing import List
# Removing cv2 import as it's not used and causes issues in Cloud Run
from google import genai
from schemas.receipt import OCRResultCategory

def process_receipt_with_gemini(files, type) -> Dict[str, Any]:
    client = genai.Client(
        api_key="AIzaSyAt6WqfZj4nsajkWVH7cpSiTAVGHpDLbhY",
    )
    # model = "gemini-2.0-flash"
    model = "gemini-2.0-flash-lite"
    
    # Preprocess image if it's an image type
    if type.startswith('image/'):
        processed_data = preprocess_image(files, save_images=True)
    else:
        processed_data = files

    # convert file to base64
    processed_data = base64.b64encode(processed_data).decode('utf-8')
    
    # Create parts using the binary data
    file_part = types.Part(
        inline_data=types.Blob(
            mime_type=type,
            data=processed_data,
        )
    )

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
    
    contents = [
        types.Content(
            role="user",
            parts=[
                # file_part,

                types.Part.from_bytes(
                    mime_type="image/jpeg",
                    data=processed_data,
                ),
                # make this content text trimmed

                types.Part(text=f"""Extract receipt to JSON:
                ${json_schema}
                Rules: Use integers for money. transaction_date must formatted YYYY-MM-DD dates, if the data doesnt complete date, make it with yours. Keep capitalization. Skip empty fields. JSON only. merchant name is required, find for this pattern "nama merchant", the total usually using this pattern "total", "grand total", or "total amount". The date usually using this pattern "tanggal" or "date". The time usually using this pattern "jam" or "time". The cashier usually using this pattern "kasir" or "cashier". The item name usually using this pattern "menu" or "item name". The item price usually using this pattern "harga" or "price". The item quantity usually using this pattern "qty" or "quantity". The payment method usually using this pattern "payment method" or "payment type". The payment amount usually using this pattern "amount" or "total amount" and it should be not less than 100.
                the "total_amount" should be sum of all items price, if the the "total_amount" and sum of all items price doesnt match, try to re-read or recalculate the items price.
                """),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
    )

    result = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )
    total_tokens = result.usage_metadata.total_token_count
    input_tokens = result.usage_metadata.prompt_token_count
    output_tokens = result.usage_metadata.candidates_token_count
    
    print(f"Total tokens: {total_tokens}")
    print(f"Input tokens: {input_tokens}")
    print(f"Output tokens: {output_tokens}")
    print(f"Parsed result text: {_parse_response(result.text)}")
    print(f"Raw result text: {result.text}")

    # return _parse_response(result.text)
    # convert to dict
    return _parse_response(result.text)


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


def save_image_to_disk(image_bytes, folder, filename=None):
    """Save image bytes to disk in the specified folder"""
    if filename is None:
        filename = generate_unique_filename()
    
    # Ensure folder exists
    os.makedirs(folder, exist_ok=True)
    
    # Save file
    file_path = os.path.join(folder, filename)
    with open(file_path, 'wb') as f:
        f.write(image_bytes)
    
    return file_path


def preprocess_image(image_bytes: bytes, save_images=False) -> bytes:
    """
    Preprocess the image to improve OCR quality
    
    Args:
        image_bytes: Raw image bytes
        save_images: Whether to save original and preprocessed images
        
    Returns:
        Processed image bytes
    """
    try:
        # Generate a unique filename for this image
        filename = generate_unique_filename()
        
        # Save original image if requested
        if save_images:
            original_path = save_image_to_disk(
                image_bytes, 
                os.path.join(os.path.dirname(__file__), 'uploads', 'original'),
                filename
            )
            print(f"Original image saved to: {original_path}")
        
        # Load image
        img = Image.open(io.BytesIO(image_bytes))
        
        # reduce size by half
        # make it less than 200kb
        img = img.resize((img.width // 2, img.height // 2))
        while True:
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            if buffer.tell() < 400 * 1024:  # Less than 400kb
                break
            img = img.resize((img.width // 2, img.height // 2))
        
        # Convert to grayscale
        # img = img.convert('L')
        
        # Enhance contrast
        # enhancer = ImageEnhance.Contrast(img)
        # img = enhancer.enhance(2.0)
        
        # Apply slight sharpening
        # img = img.filter(ImageFilter.SHARPEN)
        
        # Apply noise reduction (Gaussian blur with small radius)
        # img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        # # Apply thresholding to make text stand out
        # img = img.point(lambda x: 0 if x < 128 else 255, '1')
        
        # Ensure correct orientation (analyze later if needed)
        # For now we'll assume the orientation is correct

        # Convert back to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        processed_bytes = buffer.getvalue()
        
        # Save preprocessed image if requested
        if save_images:
            preprocessed_path = save_image_to_disk(
                processed_bytes,
                os.path.join(os.path.dirname(__file__), 'uploads', 'preprocessed'),
                filename
            )
            print(f"Preprocessed image saved to: {preprocessed_path}")
        
        return processed_bytes
    
    except Exception as e:
        print(f"Error preprocessing image: {str(e)}")
        # If preprocessing fails, return original image
        return image_bytes

def find_category(expense_history_raw: str, category: List[str]) -> OCRResultCategory:
    client = genai.Client(
        api_key="AIzaSyAt6WqfZj4nsajkWVH7cpSiTAVGHpDLbhY",
    )
    model = "gemini-2.0-flash-lite"
    # model = "gemini-2.5-flash-preview-04-17"

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
    total_tokens = result.usage_metadata.total_token_count
    input_tokens = result.usage_metadata.prompt_token_count
    output_tokens = result.usage_metadata.candidates_token_count

    print(f"Total tokens for category: {total_tokens}")
    print(f"Input tokens for category: {input_tokens}")
    print(f"Output tokens for category: {output_tokens}")
    print(f"Parsed result text for category: {_parse_response(result.text)}")
    print(f"Raw result text for category: {result.text}")
    result = _parse_response(result.text)
    # return _parse_response(result.text)
    # convert to dict
    return OCRResultCategory(
        category_id=result['category_id'],
        category_name=result['category_name'],
        is_user_category=result['is_user_category'],
    )



