# Expense Tracker Mobile App - Development Instructions
## Overview
This document provides comprehensive instructions for implementing an expense tracker mobile application that allows users to scan receipts or share digital receipts. The app will analyze expenses to help users track their spending.

---

# Instruction 5: Receipt OCR Integration

## 1. OCR Service Configuration
- Configure integration with OCR service provider (e.g., Google Cloud Vision, Amazon Textract, or custom solution, but for now, lets focus on amazon textract)
- Set up necessary authentication and API keys(this already done, the api keys and the others already provided on .env)
- Configure environment variables for OCR service connection

## 2. Receipt Processing Pipeline

### OCR Processing Flow
1. Extract text from receipt image
2. Identify key information:
   - Merchant name and information
   - Transaction date and time
   - Total amount
   - Payment method
   - Individual items and prices
   - Tax and tip information
3. Apply machine learning model to categorize items
4. Format and structure the extracted data
5. Return confidence scores for each extracted field

### Database Schema Updates
1. **ocr_confidence**
   - `ocr_confidence_id` (UUID, PK)
   - `ocr_id` (UUID, FK to ocr_results.ocr_id)
   - `field_name` (VARCHAR) - e.g., 'merchant_name', 'total_amount', 'date'
   - `confidence_score` (DECIMAL) - from 0.0 to 1.0
   - `created_at` (TIMESTAMP)

2. **ocr_training_feedback**
   - `feedback_id` (UUID, PK)
   - `ocr_id` (UUID, FK to ocr_results.ocr_id)
   - `field_name` (VARCHAR)
   - `original_value` (VARCHAR)
   - `corrected_value` (VARCHAR)
   - `created_at` (TIMESTAMP)
   - `user_id` (UUID, FK to users.user_id)

## 3. OCR Feedback Loop

### API Endpoint: Submit OCR Feedback
- **Endpoint**: `POST /api/receipts/{ocr_id}/feedback`
- **Authentication**: Bearer token required
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "corrections": [
      {
        "field_name": "string",
        "original_value": "string",
        "corrected_value": "string"
      }
    ]
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Feedback submitted successfully",
    "feedback_id": "uuid"
  }
  ```
- **Process**:
  1. Save user corrections to ocr_training_feedback table
  2. Flag data for model retraining
  3. Return success message

## 4. OCR Performance Optimization
- Implement pre-processing for uploaded images:
  - Image normalization
  - Contrast enhancement
  - Noise reduction
  - Rotation correction
- Configure post-processing for OCR results:
  - Regular expression validation for structured fields
  - Merchant name matching with existing database
  - Date and time format standardization
  - Currency and amount validation

---