# Expense Tracker Mobile App - Development Instructions
## Overview
This document provides comprehensive instructions for implementing an expense tracker mobile application that allows users to scan receipts or share digital receipts. The app will analyze expenses to help users track their spending.

---

# Instruction 2: Authentication and User Management

## 1. User Registration

### API Endpoint: Register User
- **Endpoint**: `POST /api/auth/register`
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "email": "string",
    "password": "string",
    "full_name": "string"
  }
  ```
- **Response**:
  ```json
  {
    "user_id": "uuid",
    "email": "string",
    "full_name": "string",
    "created_at": "ISO8601 timestamp",
    "status": "active"
  }
  ```
- **Process**:
  1. Validate input data (email format, password strength)
  2. Check if email already exists
  3. Hash password using bcrypt
  4. Create new user record
  5. Send verification email (optional)
  6. Return user data without sensitive information

## 2. User Authentication

### API Endpoint: Login
- **Endpoint**: `POST /api/auth/login`
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "email": "string",
    "password": "string",
    "device_info": "string" (optional)
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "string",
    "refresh_token": "string",
    "expires_in": "number" (seconds),
    "user": {
      "user_id": "uuid",
      "email": "string",
      "full_name": "string"
    }
  }
  ```
- **Process**:
  1. Validate credentials
  2. Generate JWT access token (short-lived, e.g., 15 minutes)
  3. Generate refresh token (longer-lived, e.g., 7 days)
  4. Store refresh token in auth_tokens table
  5. Update last_login in users table
  6. Return tokens and user info

### API Endpoint: Refresh Token
- **Endpoint**: `POST /api/auth/refresh`
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "refresh_token": "string"
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "string",
    "expires_in": "number" (seconds)
  }
  ```
- **Process**:
  1. Validate refresh token
  2. Check if token is in auth_tokens table and not expired
  3. Generate new JWT access token
  4. Return new access token and expiration time

### API Endpoint: Logout
- **Endpoint**: `POST /api/auth/logout`
- **Authentication**: Bearer token required
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "refresh_token": "string" (optional)
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Successfully logged out"
  }
  ```
- **Process**:
  1. Invalidate refresh token in auth_tokens table
  2. Return success message

## 3. User Profile Management

### API Endpoint: Get User Profile
- **Endpoint**: `GET /api/users/profile`
- **Authentication**: Bearer token required
- **Response**:
  ```json
  {
    "user_id": "uuid",
    "email": "string",
    "full_name": "string",
    "created_at": "ISO8601 timestamp",
    "status": "string",
    "statistics": {
      "total_expenses": "number",
      "total_amount": "decimal",
      "last_activity": "ISO8601 timestamp"
    }
  }
  ```

### API Endpoint: Update User Profile
- **Endpoint**: `PATCH /api/users/profile`
- **Authentication**: Bearer token required
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "full_name": "string" (optional),
    "email": "string" (optional),
    "current_password": "string" (required if changing email or password),
    "new_password": "string" (optional)
  }
  ```
- **Response**:
  ```json
  {
    "user_id": "uuid",
    "email": "string",
    "full_name": "string",
    "updated_at": "ISO8601 timestamp",
    "status": "string"
  }
  ```
- **Process**:
  1. Validate current password if changing email or password
  2. Update user record with new information
  3. Return updated user data

## 4. Password Reset

### API Endpoint: Request Password Reset
- **Endpoint**: `POST /api/auth/forgot-password`
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "email": "string"
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "message": "If the email exists, a reset link has been sent"
  }
  ```
- **Process**:
  1. Check if email exists in the system
  2. Generate password reset token
  3. Store token in the database with expiration time
  4. Send email with reset link
  5. Return success message (even if email not found, for security)

### API Endpoint: Reset Password
- **Endpoint**: `POST /api/auth/reset-password`
- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "token": "string",
    "new_password": "string"
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Password has been reset successfully"
  }
  ```
- **Process**:
  1. Validate reset token
  2. Check if token is expired
  3. Update user's password with new hashed password
  4. Invalidate all refresh tokens for the user
  5. Return success message

## 5. Security Considerations
- Implement password complexity requirements
- Rate limit authentication attempts
- Use secure HTTP-only cookies for refresh tokens
- Implement CSRF protection
- Set proper security headers
- Implement account lockout after multiple failed attempts
- Require re-authentication for sensitive operations
- Log all authentication events for security auditing

---