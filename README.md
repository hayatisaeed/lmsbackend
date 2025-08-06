# MentorHub Authentication Service

A Django REST API project implementing a comprehensive authentication system with phone number-based OTP authentication and profile completion workflow.

## Features

- **Custom User Model**: Phone number as primary identifier
- **OTP Authentication**: Primary authentication method
- **Password Authentication**: Optional username/password login
- **JWT Token Authentication**: Secure token-based sessions
- **Profile Completion System**: Multi-step profile completion workflow
- **Rate Limiting**: Identity verification rate limiting (5/day)
- **Educational Data Management**: Levels, branches, olympiads
- **Parent Contact Verification**: SMS-based verification system

## Project Structure

```
config/
├── users/
│   ├── models.py          # All data models
│   ├── serializers.py     # API serializers
│   ├── views.py           # API views (using DRF views, not viewsets)
│   ├── permissions.py     # Custom permissions
│   ├── utils.py           # OTP and utility functions
│   ├── admin.py           # Django admin configuration
│   └── urls.py            # URL routing
├── config/
│   ├── settings.py        # Django settings
│   └── urls.py            # Main URL configuration
└── requirements.txt       # Python dependencies
```

## Models

### User Model
- `phone`: Primary key, phone number
- `display_name`: Required display name
- `email`: Optional email
- `is_profile_complete`: Profile completion status

### Identity Information
- `national_id`: National ID number
- `date_of_birth`: Date of birth
- `first_name`, `last_name`, `father_name`: Personal details
- `gender`: Gender selection
- `is_verified`: Verification status
- `submission_count`: Rate limiting counter

### Educational System
- **EducationalLevel**: Education stages (Elementary, Middle, High School)
- **StudyBranch**: Specialization tracks (for high school only)
- **Olympiad**: Competition information
- **EducationalProfile**: User's educational details

### Location & Parent Contact
- **Location**: Province and city information
- **ParentContact**: Parent/guardian contact with verification

## API Endpoints

### Authentication

#### 1. User Registration
```http
POST /api/auth/register/
Content-Type: application/json

{
    "phone": "09914307462",
    "display_name": "John Doe",
    "email": "john@example.com",
    "password": "optional_password"
}
```

#### 2. OTP Request
```http
POST /api/auth/login/otp/
Content-Type: application/json

{
    "phone": "09914307462"
}
```

#### 3. OTP Verification
```http
POST /api/auth/verify/otp/
Content-Type: application/json

{
    "phone": "09914307462",
    "code": "123456"
}
```

#### 4. Password Login
```http
POST /api/auth/login/password/
Content-Type: application/json

{
    "phone": "09914307462",
    "password": "user_password"
}
```

### Educational Data

#### 5. List Educational Levels
```http
GET /api/educational-levels/
Authorization: Bearer <token>
```

#### 6. List Study Branches
```http
GET /api/study-branches/?level=3
Authorization: Bearer <token>
```

#### 7. List Olympiads
```http
GET /api/olympiads/
Authorization: Bearer <token>
```

### Profile Completion

#### 8. Identity Information
```http
POST /api/profile/identity/
Authorization: Bearer <token>
Content-Type: application/json

{
    "national_id": "1234567890",
    "date_of_birth": "2000-01-01"
}
```

#### 9. Educational Profile
```http
POST /api/profile/education/
Authorization: Bearer <token>
Content-Type: application/json

{
    "level": 3,
    "grade": 11,
    "study_branch": 1,
    "olympiad_ids": [1, 2, 3]
}
```

#### 10. Location Information
```http
POST /api/profile/location/
Authorization: Bearer <token>
Content-Type: application/json

{
    "province": "Tehran",
    "city": "Tehran"
}
```

#### 11. Parent Contact
```http
POST /api/profile/parent/
Authorization: Bearer <token>
Content-Type: application/json

{
    "phone": "09914307462",
    "relation": "father"
}
```

#### 12. Parent Verification
```http
POST /api/profile/parent/verify/
Authorization: Bearer <token>
Content-Type: application/json

{
    "code": "123456"
}
```

### Profile Status

#### 13. Check Profile Completion
```http
GET /api/profile/completion/
Authorization: Bearer <token>
```

#### 14. User Profile
```http
GET /api/profile/
Authorization: Bearer <token>
```

### Protected Resources

#### 15. Protected Resource (Requires Complete Profile)
```http
GET /api/protected/
Authorization: Bearer <token>
```

## Authentication Flow

### 1. Registration
1. User registers with phone and display name
2. Account created with restricted access
3. User must complete profile to access features

### 2. OTP Authentication
1. User requests OTP via `/api/auth/login/otp/`
2. OTP sent to phone number (simulated in console)
3. User verifies OTP via `/api/auth/verify/otp/`
4. JWT tokens returned for authenticated access

### 3. Profile Completion
Users must complete all sections in order:
1. **Identity Information**: National ID + DoB (triggers API call)
2. **Educational Profile**: Level, grade, branch, olympiads
3. **Location Information**: Province and city
4. **Parent Contact**: Phone and verification

### 4. Access Control
- **IsNotVerifiedPermission**: For initial registration
- **IsProfileCompletePermission**: For main features
- **IsIdentityVerifiedPermission**: For identity-dependent features

## Validation Rules

### Educational Profile
- Grade must be within level's min/max range
- Study branch required only for high school levels
- Maximum 3 olympiads per user

### Identity Information
- Rate limiting: 5 submissions per 24 hours
- National ID + DoB triggers API call to fetch other fields
- Verification required for profile completion

### Parent Contact
- SMS verification code sent to parent's phone
- 10-minute expiration for verification codes
- Verification required for profile completion

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Migrations
```bash
python manage.py migrate
```

### 3. Setup Sample Data
```bash
python manage.py setup_sample_data
```

### 4. Create Superuser
```bash
python manage.py createsuperuser
```

### 5. Run Development Server
```bash
python manage.py runserver
```

## Testing the API

### 1. Register a User
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "09914307462",
    "display_name": "Test User"
  }'
```

### 2. Request OTP
```bash
curl -X POST http://localhost:8000/api/auth/login/otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "09914307462"
  }'
```

### 3. Verify OTP (check console for code)
```bash
curl -X POST http://localhost:8000/api/auth/verify/otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "09914307462",
    "code": "123456"
  }'
```

### 4. Complete Profile Sections
```bash
# Identity
curl -X POST http://localhost:8000/api/profile/identity/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "national_id": "1234567890",
    "date_of_birth": "2000-01-01"
  }'

# Education
curl -X POST http://localhost:8000/api/profile/education/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "level": 3,
    "grade": 11,
    "study_branch": 1,
    "olympiad_ids": [1, 2]
  }'

# Location
curl -X POST http://localhost:8000/api/profile/location/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "province": "Tehran",
    "city": "Tehran"
  }'

# Parent Contact
curl -X POST http://localhost:8000/api/profile/parent/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "09914307462",
    "relation": "father"
  }'
```

## Admin Interface

Access Django admin at `http://localhost:8000/admin/` to:
- Manage users and their profiles
- View OTP codes and verification status
- Reset submission counts
- Resend verification codes
- Monitor profile completion status

## Key Features

- **Phone Number Validation**: Uses `django-phonenumber-field`
- **JWT Authentication**: Secure token-based sessions
- **Rate Limiting**: Identity submission protection
- **Profile Completion State Machine**: Automatic status updates
- **Educational Data Validation**: Grade ranges, branch requirements
- **Parent Contact Verification**: SMS-based verification
- **Comprehensive Admin Interface**: Full management capabilities

## Security Features

- JWT token authentication
- Rate limiting on identity submissions
- OTP expiration (5 minutes)
- Parent verification expiration (10 minutes)
- Profile completion gates
- Custom permissions for access control

This implementation follows Django best practices and provides a complete authentication and profile management system suitable for educational platforms. 
