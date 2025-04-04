# Expense Tracker Mobile App - Development Instructions
## Overview
This document provides comprehensive instructions for implementing an expense tracker mobile application that allows users to scan receipts or share digital receipts. The app will analyze expenses to help users track their spending.

---

# Instruction 1: Core System Setup and Receipt Processing

## 1. System Initialization
### Database Configuration
- **Database Type**: PostgreSQL
- **Host**: [Connection string placeholder - replace with actual deployed DB address]
- **Authentication**: [Authentication details placeholder]
- **Environment Variables**: Required environment variables for DB connection

### Database Schema
#### Tables Structure
1. **users**
   - `user_id` (UUID, PK)
   - `email` (VARCHAR, UNIQUE)
   - `password_hash` (VARCHAR)
   - `full_name` (VARCHAR)
   - `created_at` (TIMESTAMP)
   - `updated_at` (TIMESTAMP)
   - `last_login` (TIMESTAMP)
   - `status` (VARCHAR) - ['active', 'inactive', 'suspended']

2. **auth_tokens**
   - `token_id` (UUID, PK)
   - `user_id` (UUID, FK to users.user_id)
   - `token` (VARCHAR)
   - `type` (VARCHAR) - ['access', 'refresh']
   - `expires_at` (TIMESTAMP)
   - `created_at` (TIMESTAMP)
   - `device_info` (VARCHAR)

3. **ocr_results**
   - `ocr_id` (UUID, PK)
   - `user_id` (UUID, FK to users.user_id)
   - `image_path` (VARCHAR) - S3 path to receipt image
   - `merchant_name` (VARCHAR)
   - `total_amount` (DECIMAL)
   - `transaction_date` (TIMESTAMP)
   - `payment_method` (VARCHAR)
   - `receipt_status` (VARCHAR) - ['pending', 'processed', 'accepted', 'rejected']
   - `raw_ocr_data` (JSON) - Original OCR response
   - `created_at` (TIMESTAMP)
   - `updated_at` (TIMESTAMP)

4. **expense_items**
   - `item_id` (UUID, PK)
   - `ocr_id` (UUID, FK to ocr_results.ocr_id)
   - `name` (VARCHAR)
   - `quantity` (INT)
   - `unit_price` (DECIMAL)
   - `total_price` (DECIMAL)
   - `category` (VARCHAR)
   - `created_at` (TIMESTAMP)
   - `updated_at` (TIMESTAMP)

5. **expense_history**
   - `expense_id` (UUID, PK)
   - `user_id` (UUID, FK to users.user_id)
   - `ocr_id` (UUID, FK to ocr_results.ocr_id, nullable)
   - `merchant_name` (VARCHAR)
   - `total_amount` (DECIMAL)
   - `transaction_date` (TIMESTAMP)
   - `payment_method` (VARCHAR)
   - `category` (VARCHAR)
   - `notes` (TEXT)
   - `created_at` (TIMESTAMP)
   - `updated_at` (TIMESTAMP)
   - `is_manual_entry` (BOOLEAN) - True if manually entered, false if from OCR

## 2. Receipt Processing Flow

### API Endpoint: Receipt Upload
- **Endpoint**: `POST /api/receipts/upload`
- **Authentication**: Bearer token required
- **Content-Type**: `multipart/form-data`
- **Request Body**:
  ```
  {
    "receipt_image": [FILE],
    "user_notes": "string" (optional)
  }
  ```
- **Response**:
  ```json
  {
    "ocr_id": "uuid",
    "status": "pending|processing|complete|error",
    "message": "string",
    "estimated_completion_time": "number" (seconds)
  }
  ```
- **Process**:
  1. Validate user authentication
  2. Validate image file (format, size, resolution)
  3. Generate unique file name
  4. Upload image to S3 bucket
  5. Create entry in ocr_results table with status "pending"
  6. Trigger OCR processing job (asynchronous)
   Notes: OCR processing job will happening on instructions-5, so for now make it dummy process inside OCR processing job.
  7. Return response with ocr_id and status
  

### API Endpoint: Receipt Processing Status
- **Endpoint**: `GET /api/receipts/{ocr_id}/status`
- **Authentication**: Bearer token required
- **Response**:
  ```json
  {
    "ocr_id": "uuid",
    "status": "pending|processing|complete|error",
    "message": "string",
    "estimated_completion_time": "number" (seconds, if pending/processing)
  }
  ```

### API Endpoint: Receipt OCR Results
- **Endpoint**: `GET /api/receipts/{ocr_id}`
- **Authentication**: Bearer token required
- **Response**:
  ```json
  {
    "ocr_id": "uuid",
    "merchant_name": "string",
    "total_amount": "decimal",
    "transaction_date": "ISO8601 timestamp",
    "payment_method": "string",
    "items": [
      {
        "name": "string",
        "quantity": "number",
        "unit_price": "decimal",
        "total_price": "decimal",
        "category": "string"
      }
    ],
    "confidence_score": "decimal",
    "image_url": "string",
    "receipt_status": "pending|processed|accepted|rejected"
  }
  ```

### API Endpoint: Accept OCR Results
- **Endpoint**: `POST /api/receipts/{ocr_id}/accept`
- **Authentication**: Bearer token required
- **Request Body**:
  ```json
  {
    "merchant_name": "string" (optional, override),
    "total_amount": "decimal" (optional, override),
    "transaction_date": "ISO8601 timestamp" (optional, override),
    "payment_method": "string" (optional, override),
    "category": "string" (required),
    "items": [
      {
        "item_id": "uuid" (if editing existing),
        "name": "string",
        "quantity": "number",
        "unit_price": "decimal",
        "total_price": "decimal",
        "category": "string"
      }
    ],
    "notes": "string" (optional)
  }
  ```
- **Response**:
  ```json
  {
    "expense_id": "uuid",
    "ocr_id": "uuid",
    "message": "Expense successfully recorded",
    "status": "success|error"
  }
  ```
- **Process**:
  1. Validate user authentication
  2. Update ocr_results table with status "accepted"
  3. Create new record in expense_history
  4. Insert/update items in expense_items table
  5. Return success with expense_id

## 3. Expense History Management

### API Endpoint: Get Expense History
- **Endpoint**: `GET /api/expenses`
- **Authentication**: Bearer token required
- **Query Parameters**:
  - `from_date`: ISO8601 date (optional)
  - `to_date`: ISO8601 date (optional)
  - `category`: string (optional)
  - `merchant`: string (optional)
  - `min_amount`: decimal (optional)
  - `max_amount`: decimal (optional)
  - `page`: number (optional, default: 1)
  - `limit`: number (optional, default: 20)
  - `sort_by`: string (optional, default: "transaction_date")
  - `sort_order`: "asc"|"desc" (optional, default: "desc")
- **Response**:
  ```json
  {
    "expenses": [
      {
        "expense_id": "uuid",
        "merchant_name": "string",
        "total_amount": "decimal",
        "transaction_date": "ISO8601 timestamp",
        "category": "string",
        "payment_method": "string",
        "has_receipt_image": "boolean",
        "notes": "string",
        "created_at": "ISO8601 timestamp"
      }
    ],
    "pagination": {
      "total_count": "number",
      "page": "number",
      "limit": "number",
      "total_pages": "number"
    },
    "summary": {
      "total_expenses": "decimal",
      "avg_expense": "decimal",
      "max_expense": "decimal",
      "min_expense": "decimal",
      "expense_by_category": {
        "category1": "decimal",
        "category2": "decimal"
      }
    }
  }
  ```

### API Endpoint: Get Expense Detail
- **Endpoint**: `GET /api/expenses/{expense_id}`
- **Authentication**: Bearer token required
- **Response**:
  ```json
  {
    "expense_id": "uuid",
    "ocr_id": "uuid" (if from OCR),
    "merchant_name": "string",
    "total_amount": "decimal",
    "transaction_date": "ISO8601 timestamp",
    "category": "string",
    "payment_method": "string",
    "notes": "string",
    "receipt_image_url": "string" (if available),
    "items": [
      {
        "item_id": "uuid",
        "name": "string",
        "quantity": "number",
        "unit_price": "decimal",
        "total_price": "decimal",
        "category": "string"
      }
    ],
    "created_at": "ISO8601 timestamp",
    "updated_at": "ISO8601 timestamp",
    "is_manual_entry": "boolean"
  }
  ```

## 4. Error Handling
- All APIs should return appropriate HTTP status codes
- Error responses should follow the format:
  ```json
  {
    "status": "error",
    "error_code": "string",
    "message": "string",
    "details": {} (optional)
  }
  ```
- Common error codes:
  - `authentication_failed`: User is not authenticated
  - `authorization_failed`: User doesn't have permission
  - `validation_error`: Request data is invalid
  - `resource_not_found`: Requested resource doesn't exist
  - `server_error`: Internal server error

## 5. Security Considerations
- All API endpoints must be secured with HTTPS
- Authentication via JWT tokens
- Implement rate limiting to prevent abuse
- Sanitize all user inputs to prevent SQL injection
- Implement proper error handling to prevent information leakage
- Use parameterized queries for database operations
- Implement proper access controls for S3 resources

## 6. Performance Considerations
- Implement caching for frequently accessed data
- Use pagination for list endpoints
- Consider implementing database indexes for frequently queried fields
- Optimize image uploads by compressing images on the client side

---