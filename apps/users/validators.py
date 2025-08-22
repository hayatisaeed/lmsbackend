import re
from phonenumber_field.phonenumber import PhoneNumber
from django.core.exceptions import ValidationError
from rest_framework import serializers

class PhoneNumberValidator:
    """
    Validator for Persian phone numbers with Persian digit support
    Converts Persian digits to English and validates
    """
    message = "invalid_phone_format"
    
    def __call__(self, value):
        # Convert Persian digits to English
        persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        normalized_value = value.translate(persian_to_english)
        
        # Clean the number (remove spaces, dashes, etc.)
        cleaned_value = re.sub(r'[^\d+]', '', normalized_value)
        
        # Convert to international format for validation
        if cleaned_value.startswith('0'):
            international_format = '+98' + cleaned_value[1:]
        elif cleaned_value.startswith('98'):
            international_format = '+' + cleaned_value
        elif cleaned_value.startswith('+98'):
            international_format = cleaned_value
        else:
            international_format = '+98' + cleaned_value
        
        try:
            # Validate using django-phonenumber-field with international format
            phone_number = PhoneNumber.from_string(international_format, region='IR')
            if not phone_number.is_valid():
                raise ValidationError(self.message)
        except:
            raise ValidationError(self.message)