# Authentication System

A complete user authentication system implementation with modern UI, comprehensive validation, and security features.

## Features

### User Authentication
- User Registration with comprehensive validation
- User Login with session management
- User Logout with proper session cleanup
- Password Security with hashing using Werkzeug

### User Model
The User model includes the following fields:
- `id` - Unique identifier
- `username` - Unique username (3-20 characters, alphanumeric + underscores)
- `email` - Unique email address with format validation
- `password_hash` - Securely hashed password
- `created_at` - Account creation timestamp
- `profile_picture` - Profile picture filename (with image upload support)
- `bio` - Optional user biography (max 500 characters)
- `is_active` - Account status flag

### Form Validation
Comprehensive client-side and server-side validation:

#### Registration Validation
- **Username**: 3-20 characters, letters/numbers/underscores only, uniqueness check
- **Email**: Valid email format, uniqueness check
- **Password**: Minimum 8 characters with complexity requirements:
  - At least one uppercase letter
  - At least one lowercase letter
  - At least one number
  - At least one special character
- **Password Confirmation**: Must match the password
- **Terms Agreement**: Required checkbox

#### Login Validation
- **Username**: Required field validation
- **Password**: Required field validation
- **Remember Me**: Optional session persistence

### Security Features
- **Password Hashing** using PBKDF2 with SHA256
- **CSRF Protection** via Flask-WTF
- **Session Management** with Flask-Login
- **Input Validation** on both client and server side
- **SQL Injection Protection** via SQLAlchemy ORM
- **XSS Protection** via Jinja2 auto-escaping

### User Profile Management
- **Profile Viewing** with account summary
- **Profile Editing** with image upload
- **Password Change** with current password verification
- **Profile Picture Upload** with automatic resizing (150x150px)

## File Structure

```
├── models/__init__.py          # User model with validation methods
├── routes/auth.py              # Authentication routes
├── forms.py                    # Form classes with validation
├── templates/
│   ├── base.html              # Base template with navigation
│   └── auth/
│       ├── login.html         # Login form
│       ├── register.html      # Registration form
│       ├── profile.html       # User profile
│       ├── edit_profile.html  # Profile editing
│       └── change_password.html # Password change
├── static/
│   ├── css/style.css          # Enhanced CSS with auth styles
│   ├── images/
│   │   └── default_avatar.svg # Default profile picture
│   └── uploads/
│       └── profile_pics/      # User uploaded profile pictures
└── requirements.txt           # Updated dependencies
```

## Routes

- `/auth/login` - User login
- `/auth/register` - User registration
- `/auth/logout` - User logout
- `/auth/profile` - User profile view
- `/auth/profile/edit` - Edit profile
- `/auth/profile/change-password` - Change password

## Dependencies

- `Pillow==10.1.0` - Image processing for profile pictures
- `Flask-Login` - Session management
- `Flask-WTF` - CSRF protection and form handling
- `Werkzeug` - Password hashing
- `SQLAlchemy` - Database ORM

## Usage

1. **Start the application**:
   ```bash
   python run.py
   ```

2. **Access the application**:
   - Navigate to `http://127.0.0.1:5000`

3. **Test Registration**:
   - Click "Register" in the navigation
   - Fill out the registration form with validation
   - Submit to create a new account

4. **Test Login**:
   - Use the login form with your credentials
   - Option to "Remember Me" for persistent sessions

5. **Test Profile Management**:
   - Access your profile from the user dropdown
   - Edit profile information and upload a picture
   - Change your password with strength validation

## 📢 NOTICE

Portions of this README were enhanced using AI tools such as [**Claude 4 Sonnet By Anthropic**](https://claude.ai/).  
All final decisions and implementations were made by the project [author](https://github.com/JashanMaan28).