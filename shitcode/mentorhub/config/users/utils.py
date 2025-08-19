import random
from datetime import timedelta
from django.utils import timezone
from .models import OTPCode
import requests
from django.conf import settings
import logging
import re

logger = logging.getLogger(__name__)

OTP_API_URL = "https://s.api.ir/api/sw1/"
OTP_API_KEY = settings.OTP_API_KEY

# Test phone number that bypasses real OTP sending
TEST_PHONE_NUMBER = "+989123456789"  # You can change this to any number you prefer
TEST_OTP_CODE = "123456"  # Fixed OTP code for test user

def send_otp(phone_number, method='sms', template=None):
    """
    Generate and send OTP code to the provided phone number via external provider.
    
    Args:
        phone_number: PhoneNumberField instance
        method: 'sms' or 'call' - method to send OTP
        template: int or None - template id for SMS
        
    Returns:
        str: The generated OTP code (for testing purposes)
    """
    phone_str = str(phone_number)
    
    # Check if this is a test phone number
    if phone_str == TEST_PHONE_NUMBER:
        logger.info(f"Test phone number detected: {phone_str}. Using fixed OTP code: {TEST_OTP_CODE}")
        print(f"🧪 TEST MODE: Using fixed OTP code {TEST_OTP_CODE} for test phone {phone_str}")
        
        # Create OTP record with test code
        expires_at = timezone.now() + timedelta(minutes=5)
        OTPCode.objects.update_or_create(
            phone_number=phone_number,
            defaults={
                'code': TEST_OTP_CODE, 
                'expires_at': expires_at, 
                'is_used': False
            }
        )
        
        return TEST_OTP_CODE
    
    # Regular OTP generation for real phone numbers
    code = str(random.randint(100000, 999999))
    expires_at = timezone.now() + timedelta(minutes=5)
    
    # Create or update OTP record
    OTPCode.objects.update_or_create(
        phone_number=phone_number,
        defaults={
            'code': code, 
            'expires_at': expires_at, 
            'is_used': False
        }
    )
    
    # Send OTP via external provider
    number = str(phone_number)
    # Remove all spaces and non-digit characters
    number = re.sub(r'[^\d]', '', number)
    
    if method == 'call':
        service = 'CallOTP'
        payload = {"code": code, "number": number}
    elif method == 'sms':
        service = 'SmsOTP'
        payload = {"code": code, "mobile": number}
        if template is not None:
            payload["template"] = template
    else:
        raise ValueError("method must be 'sms' or 'call'")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OTP_API_KEY}"
    }

    try:
        response = requests.post(f"{OTP_API_URL}{service}", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"OTP sent via {method} to {number}: {response.text}")
        print(response.text)
        print(f"Original: {str(phone_number)}, Cleaned: {number}")
    except requests.RequestException as e:
        logger.error(f"OTP sending failed for {number} via {method}: {e} | {getattr(e.response, 'text', '')}")
        # In development, still print the code for testing
        print(f"OTP for {phone_number}: {code} (Expires: {expires_at})")
    
    return code  # Return for testing purposes


def verify_otp(phone_number, code):
    """
    Verify OTP code for the provided phone number.
    
    Args:
        phone_number: PhoneNumberField instance
        code: str - The OTP code to verify
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        otp = OTPCode.objects.get(
            phone_number=phone_number,
            code=code,
            is_used=False
        )
        
        if otp.is_valid():
            otp.is_used = True
            otp.save()
            return True
        return False
    except OTPCode.DoesNotExist:
        return False


def is_test_phone_number(phone_number):
    """
    Check if the given phone number is a test number.
    
    Args:
        phone_number: PhoneNumberField instance or string
        
    Returns:
        bool: True if it's a test phone number
    """
    return str(phone_number) == TEST_PHONE_NUMBER


def get_test_phone_info():
    """
    Get information about the test phone number for documentation.
    
    Returns:
        dict: Test phone number details
    """
    return {
        'test_phone': TEST_PHONE_NUMBER,
        'test_otp': TEST_OTP_CODE,
        'description': 'Use this phone number for testing. OTP will not be sent via SMS.'
    }


def generate_parent_verification_code():
    """Generate a 6-digit verification code for parent contact verification"""
    return str(random.randint(100000, 999999)) 