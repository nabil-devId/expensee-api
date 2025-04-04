# Expense Tracker Mobile App - Development Instructions
## Overview
This document provides comprehensive instructions for implementing an expense tracker mobile application that allows users to scan receipts or share digital receipts. The app will analyze expenses to help users track their spending.

---

# Instruction 4: Analytics and Reporting

## 1. Expense Analytics

### API Endpoint: Get Expense Trends
- **Endpoint**: `GET /api/analytics/trends`
- **Authentication**: Bearer token required
- **Query Parameters**:
  - `period`: "weekly|monthly|yearly" (optional, default: "monthly")
  - `start_date`: ISO8601 date (optional)
  - `end_date`: ISO8601 date (optional)
  - `category_id`: uuid (optional)
- **Response**:
  ```json
  {
    "period": "string",
    "start_date": "ISO8601 date",
    "end_date": "ISO8601 date",
    "data_points": [
      {
        "date": "ISO8601 date",
        "total_amount": "decimal",
        "count": "number"
      }
    ],
    "total_amount": "decimal",
    "average_per_period": "decimal",
    "max_amount": {
      "date": "ISO8601 date",
      "amount": "decimal"
    },
    "min_amount": {
      "date": "ISO8601 date",
      "amount": "decimal"
    },
    "trend_percentage": "decimal" // Positive or negative percentage change
  }
  ```

### API Endpoint: Get Category Distribution
- **Endpoint**: `GET /api/analytics/category-distribution`
- **Authentication**: Bearer token required
- **Query Parameters**:
  - `start_date`: ISO8601 date (optional)
  - `end_date`: ISO8601 date (optional)
- **Response**:
  ```json
  {
    "start_date": "ISO8601 date",
    "end_date": "ISO8601 date",
    "total_amount": "decimal",
    "categories": [
      {
        "category": {
          "id": "uuid",
          "name": "string",
          "icon": "string",
          "color": "string"
        },
        "amount": "decimal",
        "percentage": "decimal",
        "count": "number"
      }
    ]
  }
  ```

### API Endpoint: Get Merchant Analysis
- **Endpoint**: `GET /api/analytics/merchants`
- **Authentication**: Bearer token required
- **Query Parameters**:
  - `start_date`: ISO8601 date (optional)
  - `end_date`: ISO8601 date (optional)
  - `limit`: number (optional, default: 10)
- **Response**:
  ```json
  {
    "start_date": "ISO8601 date",
    "end_date": "ISO8601 date",
    "total_merchants": "number",
    "top_merchants": [
      {
        "merchant_name": "string",
        "total_amount": "decimal",
        "percentage": "decimal",
        "transaction_count": "number",
        "avg_transaction": "decimal",
        "categories": [
          {
            "name": "string",
            "count": "number"
          }
        ]
      }
    ]
  }
  ```

## 2. Expense Reports

### API Endpoint: Generate Monthly Report
- **Endpoint**: `GET /api/reports/monthly`
- **Authentication**: Bearer token required
- **Query Parameters**:
  - `year`: number (optional, default: current year)
  - `month`: number (optional, default: current month)
  - `format`: "json|pdf" (optional, default: "json")
- **Response** (for JSON format):
  ```json
  {
    "period": {
      "year": "number",
      "month": "number",
      "label": "string" // e.g., "April 2025"
    },
    "summary": {
      "total_expenses": "decimal",
      "total_transactions": "number",
      "avg_transaction": "decimal",
      "largest_expense": {
        "amount": "decimal",
        "merchant_name": "string",
        "date": "ISO8601 date"
      }
    },
    "category_breakdown": [
      {
        "category": {
          "name": "string",
          "icon": "string",
          "color": "string"
        },
        "amount": "decimal",
        "percentage": "decimal",
        "budget": {
          "amount": "decimal",
          "remaining": "decimal",
          "status": "under_budget|over_budget"
        }
      }
    ],
    "daily_expenses": [
      {
        "date": "ISO8601 date",
        "amount": "decimal",
        "transaction_count": "number"
      }
    ],
    "recurring_expenses": [
      {
        "merchant_name": "string",
        "amount": "decimal",
        "category": "string",
        "last_date": "ISO8601 date",
        "frequency": "string" // e.g., "Monthly", "Bi-weekly"
      }
    ],
    "comparative_analysis": {
      "previous_period": {
        "amount": "decimal",
        "change_percentage": "decimal"
      },
      "year_ago_period": {
        "amount": "decimal",
        "change_percentage": "decimal"
      }
    }
  }
  ```
- For PDF format, return a PDF file with the same information formatted as a report.

### API Endpoint: Generate Custom Report
- **Endpoint**: `POST /api/reports/custom`
- **Authentication**: Bearer token required
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "start_date": "ISO8601 date",
    "end_date": "ISO8601 date",
    "include_categories": ["uuid"] (optional),
    "include_merchants": ["string"] (optional),
    "min_amount": "decimal" (optional),
    "max_amount": "decimal" (optional),
    "payment_methods": ["string"] (optional),
    "format": "json|pdf|csv" (optional, default: "json"),
    "group_by": "day|week|month|category|merchant" (optional)
  }
  ```
- **Response** (for JSON format):
  ```json
  {
    "report_id": "uuid",
    "parameters": {
      "start_date": "ISO8601 date",
      "end_date": "ISO8601 date",
      "include_categories": ["uuid"],
      "include_merchants": ["string"],
      "min_amount": "decimal",
      "max_amount": "decimal",
      "payment_methods": ["string"],
      "group_by": "string"
    },
    "summary": {
      "total_expenses": "decimal",
      "total_transactions": "number",
      "avg_transaction": "decimal",
      "period_days": "number",
      "avg_daily_expense": "decimal"
    },
    "grouped_data": [
      {
        "group_key": "string", // Date, category name, or merchant name based on group_by
        "total_amount": "decimal",
        "transaction_count": "number",
        "percentage": "decimal"
      }
    ],
    "detailed_expenses": [
      {
        "expense_id": "uuid",
        "date": "ISO8601 date",
        "merchant_name": "string",
        "category": "string",
        "amount": "decimal",
        "payment_method": "string"
      }
    ]
  }
  ```
- For other formats, return the appropriate file type with the report data.

## 3. Export Functionality

### API Endpoint: Export Expenses
- **Endpoint**: `GET /api/exports/expenses`
- **Authentication**: Bearer token required
- **Query Parameters**:
  - `start_date`: ISO8601 date (required)
  - `end_date`: ISO8601 date (required)
  - `format`: "csv|pdf|xlsx" (optional, default: "csv")
  - `include_items`: "true|false" (optional, default: "false")
- **Response**: File download in the requested format

---