# API Documentation for Postman

Base URL: `http://localhost:8000`

---

## 1. Sign Up

**POST** `/api/v1/auth/signup/`

**Headers:**
```
Content-Type: application/json
```

**Body (raw JSON):**
```json
{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!"
}
```

**Success Response (201):**
```json
{
    "message": "Registration successful. Please check your email for OTP.",
    "email": "john@example.com"
}
```

**Error Response (400):**
```json
{
    "username": ["Username already taken."],
    "email": ["Email already registered."],
    "password": ["This password is too common."],
    "password_confirm": ["Passwords do not match."]
}
```

---

## 2. Verify OTP

**POST** `/api/v1/auth/verify-otp/`

**Headers:**
```
Content-Type: application/json
```

**Body (raw JSON):**
```json
{
    "email": "john@example.com",
    "otp": "123456"
}
```

**Success Response (200):**
```json
{
    "message": "Email verified successfully!",
    "verified": true
}
```

**Error Response (400):**
```json
{
    "error": "Invalid OTP. 2 attempts remaining."
}
```

---

## 3. Resend OTP

**POST** `/api/v1/auth/resend-otp/`

**Headers:**
```
Content-Type: application/json
```

**Body (raw JSON):**
```json
{
    "email": "john@example.com"
}
```

**Success Response (200):**
```json
{
    "message": "OTP sent successfully. Please check your email."
}
```

---

## 4. Login

**POST** `/api/v1/auth/login/`

**Headers:**
```
Content-Type: application/json
```

**Body (raw JSON):**
```json
{
    "email_or_username": "john@example.com",
    "password": "SecurePass123!"
}
```

OR with username:
```json
{
    "email_or_username": "johndoe",
    "password": "SecurePass123!"
}
```

**Success Response (200):**
```json
{
    "message": "Login successful",
    "tokens": {
        "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    },
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "username": "johndoe",
        "email": "john@example.com"
    }
}
```

**Error Responses (400):**
```json
{
    "email_or_username": ["No account found with this email/username."]
}
```
```json
{
    "password": ["Incorrect password."]
}
```
```json
{
    "email_or_username": ["Please verify your email before logging in."]
}
```

---

## 5. Refresh Token

**POST** `/api/v1/auth/token/refresh/`

**Headers:**
```
Content-Type: application/json
```

**Body (raw JSON):**
```json
{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200):**
```json
{
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## 6. Logout

**POST** `/api/v1/auth/logout/`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

**Body (raw JSON):**
```json
{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200):**
```json
{
    "message": "Logout successful"
}
```

---

## 7. Forgot Password

**POST** `/api/v1/auth/forgot-password/`

**Headers:**
```
Content-Type: application/json
```

**Body (raw JSON):**
```json
{
    "email": "john@example.com"
}
```

**Success Response (200):**
```json
{
    "message": "If an account exists with this email, a reset link has been sent."
}
```

---

## 8. Reset Password

**POST** `/api/v1/auth/reset-password/`

**Headers:**
```
Content-Type: application/json
```

**Body (raw JSON):**
```json
{
    "token": "550e8400-e29b-41d4-a716-446655440000",
    "password": "NewSecurePass123!",
    "password_confirm": "NewSecurePass123!"
}
```

**Success Response (200):**
```json
{
    "message": "Password reset successful. You can now login."
}
```

**Error Response (400):**
```json
{
    "error": "Invalid or expired reset token."
}
```

---

## 9. Change Password (Authenticated)

**POST** `/api/v1/auth/change-password/`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

**Body (raw JSON):**
```json
{
    "old_password": "SecurePass123!",
    "new_password": "NewSecurePass456!",
    "new_password_confirm": "NewSecurePass456!"
}
```

**Success Response (200):**
```json
{
    "message": "Password changed successfully."
}
```

**Error Response (400):**
```json
{
    "error": "Current password is incorrect."
}
```

---

## 10. Get Profile (Authenticated)

**GET** `/api/v1/auth/profile/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "johndoe",
    "email": "john@example.com",
    "auth_provider": "email",
    "is_email_verified": true,
    "date_joined": "2026-02-06T00:00:00Z"
}
```

**Error Response (401):**
```json
{
    "detail": "Authentication credentials were not provided."
}
```

---

## 11. Update Profile (Authenticated)

**PATCH** `/api/v1/auth/profile/`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

**Body (raw JSON):**
```json
{
    "username": "newusername"
}
```

**Success Response (200):**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "newusername",
    "email": "john@example.com",
    "auth_provider": "email",
    "is_email_verified": true,
    "date_joined": "2026-02-06T00:00:00Z"
}
```

---

## 12. Google Login

**POST** `/api/v1/auth/google/`

**Headers:**
```
Content-Type: application/json
```

**Body (raw JSON):**
```json
{
    "token": "<google-id-token-from-frontend>"
}
```

**Success Response (200):**
```json
{
    "message": "Google authentication successful",
    "tokens": {
        "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    },
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "username": "johndoe",
        "email": "john@gmail.com"
    }
}
```

---

## 13. Apple Login

**POST** `/api/v1/auth/apple/`

**Headers:**
```
Content-Type: application/json
```

**Body (raw JSON):**
```json
{
    "token": "<apple-id-token>",
    "user_info": {
        "name": "John Doe",
        "email": "john@privaterelay.appleid.com"
    }
}
```

**Success Response (200):**
```json
{
    "message": "Apple authentication successful",
    "tokens": {
        "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    },
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "username": "johndoe",
        "email": "john@privaterelay.appleid.com"
    }
}
```

---

## Postman Setup Tips

1. **Create Environment Variables:**
   - `base_url`: `http://localhost:8000`
   - `access_token`: (set after login)
   - `refresh_token`: (set after login)

2. **Auto-save tokens after login:**
   In your Login request, go to **Tests** tab and add:
   ```javascript
   var jsonData = pm.response.json();
   pm.environment.set("access_token", jsonData.tokens.access);
   pm.environment.set("refresh_token", jsonData.tokens.refresh);
   ```

3. **Use token in authenticated requests:**
   - In Headers: `Authorization: Bearer {{access_token}}`

---

## Note: Finding OTP in Development

Since email backend is set to console, OTPs are printed to the server terminal. Look for:
```
Your OTP code for email verification is: 123456
```
