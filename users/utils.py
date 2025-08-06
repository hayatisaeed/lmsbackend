import random
from datetime import timedelta
from django.utils import timezone
from .models import OTPCode


def send_otp(phone_number):
    """
    Generate and send OTP code to the provided phone number.
    
    Args:
        phone_number: PhoneNumberField instance
        
    Returns:
        str: The generated OTP code (for testing purposes)
    """
    # Generate 6-digit code
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
    
    # In production: Integrate with SMS gateway here
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


def generate_parent_verification_code():
    """Generate a 6-digit verification code for parent contact verification"""
    return str(random.randint(100000, 999999)) 