#!/usr/bin/env python3
"""
Test script for the new unified authentication system.
This script demonstrates how the new system works with minimal user input.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api/users"

def get_test_phone_info():
    """Get information about the test phone number"""
    print("=== Getting Test Phone Information ===")
    
    response = requests.get(f"{BASE_URL}/auth/test-info/")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Test phone information retrieved:")
        print(f"📱 Test Phone: {data['test_phone']}")
        print(f"🔑 Test OTP: {data['test_otp']}")
        print(f"📝 Description: {data['description']}")
        print("\n📋 Usage Instructions:")
        for key, value in data['usage'].items():
            print(f"  {key}: {value}")
        return data
    else:
        print(f"❌ Failed to get test info: {response.status_code}")
        print(f"Error: {response.text}")
        return None

def test_unified_login():
    """Test the new unified login/registration endpoint with test phone"""
    print("\n=== Testing Unified Login/Registration (Test Phone) ===")
    
    # Get test phone info first
    test_info = get_test_phone_info()
    if not test_info:
        return
    
    phone = test_info['test_phone']
    test_otp = test_info['test_otp']
    
    print(f"\n1. Requesting OTP for test phone: {phone}")
    
    response = requests.post(
        f"{BASE_URL}/auth/login/",
        json={"phone": phone},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ OTP sent successfully!")
        print(f"Response: {json.dumps(data, indent=2)}")
        
        # Check if test mode is detected
        if data.get('is_test_user'):
            print("🧪 Test mode detected! No real SMS sent.")
            print(f"📱 Use OTP code: {data.get('test_info', 'Check response for OTP')}")
        
        print(f"\n2. Verifying OTP with test code: {test_otp}")
        
        # Verify OTP with test code
        verify_response = requests.post(
            f"{BASE_URL}/auth/verify/otp/",
            json={
                "phone": phone,
                "code": test_otp,
                "display_name": "Test User",
                "email": "test@example.com"
            },
            headers={"Content-Type": "application/json"}
        )
        
        if verify_response.status_code == 200:
            verify_data = verify_response.json()
            print("✅ OTP verification successful!")
            print(f"Response: {json.dumps(verify_data, indent=2)}")
            
            # Check if user was created or updated
            if verify_data.get('is_new_user'):
                print("🆕 New user was created!")
            else:
                print("🔄 Existing user was updated!")
                
            # Save tokens for further testing
            if 'access' in verify_data:
                print("🔑 JWT tokens received successfully!")
                return verify_data.get('access')
        else:
            print(f"❌ OTP verification failed: {verify_response.status_code}")
            print(f"Error: {verify_response.text}")
            
    else:
        print(f"❌ Failed to send OTP: {response.status_code}")
        print(f"Error: {response.text}")
    
    return None

def test_traditional_registration():
    """Test the traditional registration endpoint (now optional)"""
    print("\n=== Testing Traditional Registration (Optional) ===")
    
    phone = "09914307463"
    print(f"\n1. Traditional registration for phone: {phone}")
    
    response = requests.post(
        f"{BASE_URL}/auth/register/",
        json={
            "phone": phone,
            "display_name": "Traditional User",
            "email": "traditional@example.com"
        },
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 201:
        print("✅ User registered successfully!")
        print(f"Response: {response.json()}")
    else:
        print(f"❌ Registration failed: {response.status_code}")
        print(f"Error: {response.text}")

def test_minimal_registration():
    """Test registration with only phone number"""
    print("\n=== Testing Minimal Registration (Phone Only) ===")
    
    phone = "09914307464"
    print(f"\n1. Minimal registration for phone: {phone}")
    
    response = requests.post(
        f"{BASE_URL}/auth/register/",
        json={"phone": phone},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 201:
        print("✅ User registered with phone only!")
        print(f"Response: {response.json()}")
        
        # Check if display_name was auto-generated
        user_data = response.json().get('user', {})
        display_name = user_data.get('display_name', '')
        if display_name.startswith('User_'):
            print(f"✅ Display name auto-generated: {display_name}")
        else:
            print(f"⚠️  Display name not auto-generated: {display_name}")
            
    else:
        print(f"❌ Minimal registration failed: {response.status_code}")
        print(f"Error: {response.text}")

def test_protected_endpoint(access_token):
    """Test accessing a protected endpoint with the JWT token"""
    if not access_token:
        print("❌ No access token available for protected endpoint test")
        return
    
    print("\n=== Testing Protected Endpoint ===")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Test user profile endpoint
    response = requests.get(f"{BASE_URL}/profile/", headers=headers)
    
    if response.status_code == 200:
        print("✅ Protected endpoint accessed successfully!")
        print(f"User profile: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"❌ Failed to access protected endpoint: {response.status_code}")
        print(f"Error: {response.text}")

def main():
    """Run all tests"""
    print("🚀 Testing New Authentication System with Test Phone")
    print("=" * 60)
    
    try:
        # Test with test phone number (no real SMS)
        access_token = test_unified_login()
        
        # Test traditional methods
        test_traditional_registration()
        test_minimal_registration()
        
        # Test protected endpoint if we have a token
        if access_token:
            test_protected_endpoint(access_token)
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("\n📋 Summary of Changes:")
        print("• Only phone number is required for user creation")
        print("• Display name is auto-generated if not provided")
        print("• Email and password are completely optional")
        print("• Unified login endpoint handles both new and existing users")
        print("• Users can update profile during OTP verification")
        print("• Test phone number (+989123456789) bypasses real SMS sending")
        print("• Test OTP code is always: 123456")
        
        print("\n🧪 Test Phone Usage:")
        print("1. POST /api/auth/login/ with phone: +989123456789")
        print("2. POST /api/auth/verify/otp/ with phone: +989123456789 and code: 123456")
        print("3. No real SMS will be sent for this number")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server.")
        print("Make sure the Django server is running on http://localhost:8000")
        print("Run: python manage.py runserver")
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    main() 