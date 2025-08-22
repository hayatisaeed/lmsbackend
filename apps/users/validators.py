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
        
        try:
            # Validate using django-phonenumber-field
            phone_number = PhoneNumber.from_string(normalized_value, region='IR')
            if not phone_number.is_valid():
                raise ValidationError(self.message)
        except:
            raise ValidationError(self.message)