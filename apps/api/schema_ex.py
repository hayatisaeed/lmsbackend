# e.g. apps/api/schema_ext.py
from drf_spectacular.extensions import OpenApiAuthenticationExtension

class CustomJWTExt(OpenApiAuthenticationExtension):
    target_class = 'apps.users.auth.JWTAuthentication'  # your class path
    name = 'JWTAuth'  # security scheme name

    def get_security_definition(self, auto_schema):
        return {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'}
