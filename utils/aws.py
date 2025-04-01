import re
import boto3
from typing import Dict, Any, List, Optional
import uuid
import logging
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

def get_s3_client():
    """Create and return an S3 client"""
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )

def get_textract_client():
    """Create and return a Textract client"""
    return boto3.client(
        'textract',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )

async def fetch_image_from_s3(s3_url: str) -> bytes:
    """Fetch an image from S3 and return the binary content"""
    get_s3_client = get_s3_client()
    response = get_s3_client.get_object(Bucket=settings.RECEIPT_IMAGES_BUCKET, Key=s3_url)
    return response['Body'].read()

async def upload_image_to_s3(file_content: bytes, filename: str) -> str:
    """
    Upload a file to S3 bucket and return the URL
    
    Args:
        file_content: The binary content of the file
        filename: Original filename
        
    Returns:
        S3 URL of the uploaded file
    """
    try:
        # Generate a unique filename
        file_extension = filename.split('.')[-1] if '.' in filename else 'jpg'
        s3_filename = f"{uuid.uuid4()}.{file_extension}"
        
        # Upload to S3
        s3_client = get_s3_client()
        s3_client.put_object(
            Bucket=settings.RECEIPT_IMAGES_BUCKET,
            Key=s3_filename,
            Body=file_content,
            ContentType=f"image/{file_extension}"
        )
        
        # Return the URL
        return f"https://{settings.RECEIPT_IMAGES_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_filename}"
    
    except ClientError as e:
        logger.error(f"Error uploading file to S3: {str(e)}")
        raise

async def process_receipt_with_textract(image_url: str) -> Dict[str, Any]:
    """
    Process a receipt image with AWS Textract
    
    Args:
        image_url: S3 URL of the image
        
    Returns:
        Dict with extracted information
    """
    try:
        # Extract bucket and key from S3 URL
        parts = image_url.replace('https://', '').split('.')
        bucket = parts[0]
        key = '.'.join(parts[3:]).split('/')[1] # what is this?
        
        # Process with Textract
        textract_client = get_textract_client()
        # response = textract_client.analyze_expense(
        #     Document={
        #         'S3Object': {
        #             'Bucket': bucket,
        #             'Name': key
        #         }
        #     }
        # )

        response = textract_client.analyze_document(
            Document={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            }
        )
        # Extract relevant information
        result = {
            # 'raw_response': response,
            'merchant_name': _extract_merchant_name(response),
            'total_amount': _extract_total_amount(response),
            'transaction_date': _extract_transaction_date(response),
            'items': _extract_line_items(response)
        }
        
        return result
    
    except ClientError as e:
        logger.error(f"Error processing image with Textract: {str(e)}")
        raise

def _extract_merchant_name(textract_response: Dict[str, Any]) -> Optional[str]:
    """Extract merchant name from Textract response"""
    # Simplified implementation - in a real app, you'd have more robust parsing
    for expense_document in textract_response.get('ExpenseDocuments', []):
        for expense_field in expense_document.get('SummaryFields', []):
            if expense_field.get('Type', {}).get('Text') == 'VENDOR_NAME':
                return expense_field.get('ValueDetection', {}).get('Text').replace("\n", " ")
    return None

def _extract_total_amount(textract_response: Dict[str, Any]) -> Optional[float]:
    """Extract total amount from Textract response"""
    for expense_document in textract_response.get('ExpenseDocuments', []):
        for expense_field in expense_document.get('SummaryFields', []):
            if expense_field.get('Type', {}).get('Text') == 'TOTAL':
                amount_str = expense_field.get('ValueDetection', {}).get('Text', '0')
                try:
                    # use regext string to remove text
                    amount_str = _validate_amount_str(amount_str)
                    return float(amount_str)
                except ValueError:
                    return None
    return None

def _validate_amount_str(amount_str: str) -> str:
    """Validate amount string"""
    amount_str = re.sub(r'[a-zA-Z]', '', amount_str)
    amount_str_array = amount_str.split(",")
    if len(amount_str_array) > 1 and amount_str_array[len(amount_str_array) - 1] == "00":
        amount_str = amount_str_array[0:len(amount_str_array) - 1][0]
    return amount_str.replace(".", "").replace(",", "")

def _extract_transaction_date(textract_response: Dict[str, Any]) -> Optional[str]:
    """Extract transaction date from Textract response"""
    for expense_document in textract_response.get('ExpenseDocuments', []):
        for expense_field in expense_document.get('SummaryFields', []):
            if expense_field.get('Type', {}).get('Text') == 'INVOICE_RECEIPT_DATE':
                return expense_field.get('ValueDetection', {}).get('Text')
    return None

def _extract_line_items(textract_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract line items from Textract response"""
    line_items = []
    
    for expense_document in textract_response.get('ExpenseDocuments', []):
        for line_item_group in expense_document.get('LineItemGroups', []):
            for line_item in line_item_group.get('LineItems', []):
                item = {}
                for expense_field in line_item.get('LineItemExpenseFields', []):
                    field_type = expense_field.get('Type', {}).get('Text')
                    field_value = expense_field.get('ValueDetection', {}).get('Text')
                    
                    if field_type == 'ITEM':
                        item['name'] = field_value
                    elif field_type == 'PRICE':
                        try:
                            field_value = _validate_amount_str(field_value)
                            item['price'] = float(field_value)
                        except (ValueError, AttributeError):
                            item['price'] = 0.0
                    elif field_type == 'QUANTITY':
                        try:
                            field_value = _validate_amount_str(field_value)
                            item['quantity'] = float(field_value)
                        except (ValueError, AttributeError):
                            item['quantity'] = 1.0
                
                if item:
                    line_items.append(item)
    
    return line_items