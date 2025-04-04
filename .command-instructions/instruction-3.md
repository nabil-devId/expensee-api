# Expense Tracker Mobile App - Development Instructions
## Overview
This document provides comprehensive instructions for implementing an expense tracker mobile application that allows users to scan receipts or share digital receipts. The app will analyze expenses to help users track their spending.

---

# Instruction 3: Expense Categories and Budget Management

## 1. Category Management

### Predefined Categories
- Implement the following default expense categories:
  - Groceries
  - Dining
  - Transportation
  - Utilities
  - Housing
  - Entertainment
  - Health
  - Shopping
  - Travel
  - Education
  - Personal Care
  - Miscellaneous

### Database Schema
#### Tables Structure
1. **categories**
   - `category_id` (UUID, PK)
   - `name` (VARCHAR)
   - `icon` (VARCHAR) - Icon identifier
   - `color` (VARCHAR) - HEX color code
   - `is_default` (BOOLEAN)
   - `created_at` (TIMESTAMP)
   - `updated_at` (TIMESTAMP)

2. **user_categories**
   - `user_category_id` (UUID, PK)
   - `user_id` (UUID, FK to users.user_id)
   - `name` (VARCHAR)
   - `icon` (VARCHAR)
   - `color` (VARCHAR)
   - `created_at` (TIMESTAMP)
   - `updated_at` (TIMESTAMP)

### API Endpoint: Get Categories
- **Endpoint**: `GET /api/categories`
- **Authentication**: Bearer token required
- **Response**:
  ```json
  {
    "default_categories": [
      {
        "category_id": "uuid",
        "name": "string",
        "icon": "string",
        "color": "string"
      }
    ],
    "user_categories": [
      {
        "user_category_id": "uuid",
        "name": "string",
        "icon": "string",
        "color": "string"
      }
    ]
  }
  ```

### API Endpoint: Create Custom Category
- **Endpoint**: `POST /api/categories`
- **Authentication**: Bearer token required
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "name": "string",
    "icon": "string",
    "color": "string"
  }
  ```
- **Response**:
  ```json
  {
    "user_category_id": "uuid",
    "name": "string",
    "icon": "string",
    "color": "string",
    "created_at": "ISO8601 timestamp"
  }
  ```

### API Endpoint: Update Custom Category
- **Endpoint**: `PUT /api/categories/{user_category_id}`
- **Authentication**: Bearer token required
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "name": "string",
    "icon": "string",
    "color": "string"
  }
  ```
- **Response**:
  ```json
  {
    "user_category_id": "uuid",
    "name": "string",
    "icon": "string",
    "color": "string",
    "updated_at": "ISO8601 timestamp"
  }
  ```

### API Endpoint: Delete Custom Category
- **Endpoint**: `DELETE /api/categories/{user_category_id}`
- **Authentication**: Bearer token required
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Category deleted successfully"
  }
  ```

## 2. Budget Management

### Database Schema
#### Tables Structure
1. **budgets**
   - `budget_id` (UUID, PK)
   - `user_id` (UUID, FK to users.user_id)
   - `category_id` (UUID, nullable) - NULL for overall budget
   - `user_category_id` (UUID, nullable) - NULL for default categories
   - `amount` (DECIMAL)
   - `period` (VARCHAR) - ['monthly', 'quarterly', 'yearly']
   - `start_date` (DATE)
   - `end_date` (DATE, nullable) - NULL for recurring budgets
   - `created_at` (TIMESTAMP)
   - `updated_at` (TIMESTAMP)

### API Endpoint: Create Budget
- **Endpoint**: `POST /api/budgets`
- **Authentication**: Bearer token required
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "category_id": "uuid" (optional),
    "user_category_id": "uuid" (optional),
    "amount": "decimal",
    "period": "monthly|quarterly|yearly",
    "start_date": "ISO8601 date",
    "end_date": "ISO8601 date" (optional)
  }
  ```
- **Response**:
  ```json
  {
    "budget_id": "uuid",
    "category": {
      "id": "uuid",
      "name": "string",
      "icon": "string",
      "color": "string",
      "is_custom": "boolean"
    },
    "amount": "decimal",
    "period": "string",
    "start_date": "ISO8601 date",
    "end_date": "ISO8601 date",
    "created_at": "ISO8601 timestamp"
  }
  ```

### API Endpoint: Get Budgets
- **Endpoint**: `GET /api/budgets`
- **Authentication**: Bearer token required
- **Query Parameters**:
  - `period`: "monthly|quarterly|yearly" (optional)
  - `active_on`: ISO8601 date (optional, default: current date)
- **Response**:
  ```json
  {
    "budgets": [
      {
        "budget_id": "uuid",
        "category": {
          "id": "uuid",
          "name": "string",
          "icon": "string",
          "color": "string",
          "is_custom": "boolean"
        },
        "amount": "decimal",
        "period": "string",
        "start_date": "ISO8601 date",
        "end_date": "ISO8601 date",
        "current_spending": "decimal",
        "remaining": "decimal",
        "percentage_used": "decimal"
      }
    ],
    "overall_budget": {
      "budget_id": "uuid",
      "amount": "decimal",
      "current_spending": "decimal",
      "remaining": "decimal",
      "percentage_used": "decimal"
    }
  }
  ```

### API Endpoint: Update Budget
- **Endpoint**: `PUT /api/budgets/{budget_id}`
- **Authentication**: Bearer token required
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "amount": "decimal",
    "period": "monthly|quarterly|yearly",
    "start_date": "ISO8601 date",
    "end_date": "ISO8601 date" (optional)
  }
  ```
- **Response**:
  ```json
  {
    "budget_id": "uuid",
    "category": {
      "id": "uuid",
      "name": "string",
      "icon": "string",
      "color": "string",
      "is_custom": "boolean"
    },
    "amount": "decimal",
    "period": "string",
    "start_date": "ISO8601 date",
    "end_date": "ISO8601 date",
    "updated_at": "ISO8601 timestamp"
  }
  ```

### API Endpoint: Delete Budget
- **Endpoint**: `DELETE /api/budgets/{budget_id}`
- **Authentication**: Bearer token required
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Budget deleted successfully"
  }
  ```

### API Endpoint: Get Budget Progress
- **Endpoint**: `GET /api/budgets/progress`
- **Authentication**: Bearer token required
- **Query Parameters**:
  - `period`: "monthly|quarterly|yearly" (optional, default: "monthly")
  - `date`: ISO8601 date (optional, default: current date)
- **Response**:
  ```json
  {
    "period_start": "ISO8601 date",
    "period_end": "ISO8601 date",
    "overall_budget": {
      "budget_amount": "decimal",
      "current_spending": "decimal",
      "remaining": "decimal",
      "percentage_used": "decimal"
    },
    "categories": [
      {
        "category": {
          "id": "uuid",
          "name": "string",
          "icon": "string",
          "color": "string",
          "is_custom": "boolean"
        },
        "budget_amount": "decimal",
        "current_spending": "decimal",
        "remaining": "decimal",
        "percentage_used": "decimal",
        "status": "under_budget|approaching_limit|over_budget"
      }
    ]
  }
  ```

## 3. Budget Notifications
- Implement budget threshold alerts (50%, 75%, 90%, 100% of budget used)
- Configure in-app notifications for budget milestones
- Provide weekly and monthly budget summaries

---