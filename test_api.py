"""
Test script for authentication APIs.
Run this while the Django server is running.
"""

import requests

BASE_URL = "http://localhost:8000/api/v1/auth"

def test_signup():
    """Test user registration."""
    print("=" * 50)
    print("Testing SIGNUP...")
    print("=" * 50)
    
    response = requests.post(f"{BASE_URL}/signup/", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!",
        "password_confirm": "TestPass123!"
    })
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response

def test_verify_otp(email, otp):
    """Test OTP verification."""
    print("\n" + "=" * 50)
    print("Testing VERIFY OTP...")
    print("=" * 50)
    
    response = requests.post(f"{BASE_URL}/verify-otp/", json={
        "email": email,
        "otp": otp
    })
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response

def test_login(email_or_username, password):
    """Test login."""
    print("\n" + "=" * 50)
    print("Testing LOGIN...")
    print("=" * 50)
    
    response = requests.post(f"{BASE_URL}/login/", json={
        "email_or_username": email_or_username,
        "password": password
    })
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response

def test_profile(access_token):
    """Test profile endpoint."""
    print("\n" + "=" * 50)
    print("Testing PROFILE...")
    print("=" * 50)
    
    response = requests.get(
        f"{BASE_URL}/profile/",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response

if __name__ == "__main__":
    # Test signup
    signup_response = test_signup()
    
    print("\n\n" + "!" * 50)
    print("CHECK THE SERVER CONSOLE FOR THE OTP CODE")
    print("(Since we're using console email backend)")
    print("!" * 50)
