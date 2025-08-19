

## Goal

Create a **working Django + DRF project skeleton** with best practices, so subsequent tasks (AUTH_P0, PROFILE_P0, TAXONOMY_P0, etc.) can be implemented cleanly.

---

## Scope

1. **Project Scaffold**
    
    - New Django project root (`mentorhub/`).
        
    - `users` app with `models.py`, `serializers.py`, `views.py`, `permissions.py`, `urls.py`, `admin.py`, `utils/`.
        
    - Settings module with environment-based config.
        
2. **Dependencies**
    
    - `djangorestframework`
        
    - `djangorestframework-simplejwt`
        
    - `django-phonenumber-field[phonenumberslite]`
        
    - `django-ratelimit`
        
    - `django-environ`
        
    - `pytest-django`, `factory_boy`
        
    - `drf-spectacular` (OpenAPI)
        
    - `black`, `isort`, `ruff` (lint/format)
        
3. **Custom User Model**
    
    - Phone (`phonenumber_field`) as primary identifier.
        
    - `display_name` required.
        
    - `email` optional.
        
    - `password` optional.
        
    - Default role: student.
        
4. **Base Utilities**
    
    - `utils/otp_utils.py` stub with `send_otp(phone_number)` (print OTP to console for now).
        
    - `permissions.py` stub with:
        
        - `IsProfileComplete`
            
        - `IsIdentityVerified`
            
        - `IsNotVerified`
            
5. **Settings**
    
    - Config via `.env` (12-factor).
        
    - Installed apps: `rest_framework`, `users`, `phonenumber_field`, `drf_spectacular`.
        
    - REST framework default auth: JWT via `SimpleJWT`.
        
    - `SPECTACULAR_SETTINGS` for OpenAPI schema.
        
6. **Routing**
    
    - Root `urls.py` with DRF router + `users/urls.py`.
        
    - `/api/schema/` and `/api/docs/` endpoints.
        
7. **CI/CD Ready**
    
    - `requirements.txt` and `requirements-dev.txt`.
        
    - Pre-commit config for lint/format.
        
    - GitHub Actions workflow stub (`lint`, `test`, `migrate`).
        
8. **Tests**
    
    - Basic pytest setup.
        
    - Factories for User.
        
    - Sanity test: create user, assert phone unique.
        

---

## Deliverables

- New PR `bootstrap/p0` with working Django skeleton.
    
- Repo structure:
    

```
mentorhub/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── users/
│   ├── __init__.py
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── permissions.py
│   ├── urls.py
│   ├── admin.py
│   └── utils/
│       └── otp_utils.py
├── manage.py
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
└── .pre-commit-config.yaml
```

---

## Definition of Done

- `python manage.py migrate` works cleanly.
    
- `pytest` passes with at least one user test.
    
- `python manage.py runserver` runs local API at `/api/schema/`.
    
- PR passes lint (`black`, `isort`, `ruff`) and tests in CI.
    
