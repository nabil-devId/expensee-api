import logging
from typing import Any, Dict
from google.genai import types

logger = logging.getLogger(__name__)



# To run this code you need to install the following dependencies:
# pip install google-genai

import io
import os
import uuid
import datetime
import json
from PIL import Image
import numpy as np
import cv2
from google import genai

def process_receipt_with_gemini(files, type) -> Dict[str, Any]:
    client = genai.Client(
        api_key="AIzaSyCm2MDTDNvknht5K4TMJRjbZcMWwBZz0BQ",
    )
    # model = "gemini-2.0-flash"
    model = "gemini-2.0-flash-lite"
    
    # Preprocess image if it's an image type
    if type.startswith('image/'):
        processed_data = preprocess_image(files, save_images=True)
    else:
        processed_data = files
    
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
            'total_amount': [number],
            'transaction_date': [string],
            'payment_method': [string],
            'items': [
                {
                    'name': [string],
                    'quantity': [number],
                    'price': [number],
                    'total': [number]
                },
                {
                    'name': [string],
                    'quantity': [number],
                    'price': [number],
                    'total': [number]
                }
            ],
            'confidence_scores': {
                'merchant_name': [number],
                'total_amount': [number],
                'transaction_date': [number],
                'payment_method': [number]
            },
        }
"""
    
    contents = [
        types.Content(
            role="user",
            parts=[
                file_part,
                types.Part(text=f"""Extract receipt to JSON:
                ${json_schema}
                Rules: Use integers for money. YYYY-MM-DD dates. HH:MM times. Keep capitalization. Skip empty fields. JSON only. merchant name is required, find for this pattern "nama merchant", the total usually using this pattern "total", "grand total", or "total amount". The date usually using this pattern "tanggal" or "date". The time usually using this pattern "jam" or "time". The cashier usually using this pattern "kasir" or "cashier". The item name usually using this pattern "menu" or "item name". The item price usually using this pattern "harga" or "price". The item quantity usually using this pattern "qty" or "quantity". The payment method usually using this pattern "payment method" or "payment type". The payment amount usually using this pattern "amount" or "total amount" and it should be not less than 100. The verification code usually using this pattern "verification code" or "code".
                the "grandTotal" should be sum of all items price, if the the grandTotal and sum of all items price doesnt match, try to re-read or recalculate the items price.
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
