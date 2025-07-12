from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField, DateField, SelectMultipleField, widgets
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, URL
from models import User
import re
from datetime import datetime, date

class LoginForm(FlaskForm):
    """Login form with validation"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=20, message='Username must be between 3-20 characters')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required')
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    """Registration form with comprehensive validation"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=20, message='Username must be between 3-20 characters')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ])
    terms = BooleanField('I agree to the Terms of Service', validators=[
        DataRequired(message='You must agree to the terms of service')
    ])
    submit = SubmitField('Create Account')
    
    def validate_username(self, username):
        """Custom username validation"""
        # Check format
        if not re.match(r'^[a-zA-Z0-9_]+$', username.data):
            raise ValidationError('Username can only contain letters, numbers, and underscores')
        
        # Check availability
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username is already taken. Please choose a different one.')
    
    def validate_email(self, email):
        """Custom email validation"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email is already registered. Please use a different email or login.')
    
    def validate_password(self, password):
        """Custom password strength validation"""
        password_value = password.data
        
        if not re.search(r'[A-Z]', password_value):
            raise ValidationError('Password must contain at least one uppercase letter')
        
        if not re.search(r'[a-z]', password_value):
            raise ValidationError('Password must contain at least one lowercase letter')
        
        if not re.search(r'\d', password_value):
            raise ValidationError('Password must contain at least one number')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password_value):
            raise ValidationError('Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)')

class UpdateProfileForm(FlaskForm):
    """Profile update form"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=20, message='Username must be between 3-20 characters')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    profile_picture = FileField('Profile Picture', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    first_name = StringField('First Name', validators=[
        Optional(),
        Length(max=50, message='First name must be less than 50 characters')
    ])
    last_name = StringField('Last Name', validators=[
        Optional(),
        Length(max=50, message='Last name must be less than 50 characters')
    ])
    bio = TextAreaField('Bio', validators=[
        Optional(),
        Length(max=500, message='Bio must be less than 500 characters')
    ])
    location = StringField('Location', validators=[
        Optional(),
        Length(max=100, message='Location must be less than 100 characters')
    ])
    website_url = StringField('Website', validators=[
        Optional(),
        URL(message='Please enter a valid URL'),
        Length(max=200, message='URL must be less than 200 characters')
    ])
    submit = SubmitField('Update Profile')
    
    def __init__(self, original_username, original_email, *args, **kwargs):
        super(UpdateProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email
    
    def validate_username(self, username):
        """Custom username validation for updates"""
        if username.data != self.original_username:
            # Check format
            if not re.match(r'^[a-zA-Z0-9_]+$', username.data):
                raise ValidationError('Username can only contain letters, numbers, and underscores')
            
            # Check availability
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Username is already taken. Please choose a different one.')
    
    def validate_email(self, email):
        """Custom email validation for updates"""
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Email is already registered. Please use a different email.')

class ChangePasswordForm(FlaskForm):
    """Change password form"""
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message='Current password is required')
    ])
    new_password = PasswordField('New Password', validators=[
        DataRequired(message='New password is required'),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm your new password'),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Change Password')
    
    def validate_new_password(self, new_password):
        """Custom password strength validation"""
        password_value = new_password.data
        
        if not re.search(r'[A-Z]', password_value):
            raise ValidationError('Password must contain at least one uppercase letter')
        
        if not re.search(r'[a-z]', password_value):
            raise ValidationError('Password must contain at least one lowercase letter')
        
        if not re.search(r'\d', password_value):
            raise ValidationError('Password must contain at least one number')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password_value):
            raise ValidationError('Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)')

# Custom widget for multiple checkboxes
class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class UserPreferencesForm(FlaskForm):
    """Comprehensive user preferences form"""
    # Personal Information
    first_name = StringField('First Name', validators=[
        Optional(),
        Length(max=50, message='First name must be less than 50 characters')
    ])
    last_name = StringField('Last Name', validators=[
        Optional(),
        Length(max=50, message='Last name must be less than 50 characters')
    ])
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    location = StringField('Location', validators=[
        Optional(),
        Length(max=100, message='Location must be less than 100 characters')
    ])
    bio = TextAreaField('Bio', validators=[
        Optional(),
        Length(max=500, message='Bio must be less than 500 characters')
    ])
    website_url = StringField('Website', validators=[
        Optional(),
        URL(message='Please enter a valid URL'),
        Length(max=200, message='URL must be less than 200 characters')
    ])
    
    # Favorite Genres (multiple selection)
    favorite_genres = MultiCheckboxField('Favorite Genres', choices=[
        ('action', 'Action'),
        ('adventure', 'Adventure'),
        ('animation', 'Animation'),
        ('biography', 'Biography'),
        ('comedy', 'Comedy'),
        ('crime', 'Crime'),
        ('documentary', 'Documentary'),
        ('drama', 'Drama'),
        ('family', 'Family'),
        ('fantasy', 'Fantasy'),
        ('history', 'History'),
        ('horror', 'Horror'),
        ('music', 'Music'),
        ('musical', 'Musical'),
        ('mystery', 'Mystery'),
        ('romance', 'Romance'),
        ('sci-fi', 'Sci-Fi'),
        ('sport', 'Sport'),
        ('thriller', 'Thriller'),
        ('war', 'War'),
        ('western', 'Western')
    ])
    
    # Content Types
    content_types = MultiCheckboxField('Preferred Content Types', choices=[
        ('movies', 'Movies'),
        ('tv_series', 'TV Series'),
        ('documentaries', 'Documentaries'),
        ('anime', 'Anime'),
        ('web_series', 'Web Series'),
        ('short_films', 'Short Films'),
        ('music_videos', 'Music Videos'),
        ('podcasts', 'Podcasts')
    ])
    
    # Viewing Habits
    preferred_viewing_time = SelectField('Preferred Viewing Time', choices=[
        ('', 'Select preferred time'),
        ('morning', 'Morning (6 AM - 12 PM)'),
        ('afternoon', 'Afternoon (12 PM - 6 PM)'),
        ('evening', 'Evening (6 PM - 10 PM)'),
        ('night', 'Night (10 PM - 2 AM)'),
        ('late_night', 'Late Night (2 AM - 6 AM)'),
        ('no_preference', 'No Preference')
    ])
    
    preferred_duration = SelectField('Preferred Content Duration', choices=[
        ('', 'Select preferred duration'),
        ('short', 'Short (< 30 minutes)'),
        ('medium', 'Medium (30 minutes - 2 hours)'),
        ('long', 'Long (2+ hours)'),
        ('series', 'Series/Multiple Episodes'),
        ('no_preference', 'No Preference')
    ])
    
    binge_watcher = BooleanField('I enjoy binge-watching')
    subtitles_preference = BooleanField('I prefer content with subtitles')
    
    # Social Links
    twitter_url = StringField('Twitter Profile', validators=[
        Optional(),
        Length(max=200, message='URL must be less than 200 characters')
    ])
    instagram_url = StringField('Instagram Profile', validators=[
        Optional(),
        Length(max=200, message='URL must be less than 200 characters')
    ])
    facebook_url = StringField('Facebook Profile', validators=[
        Optional(),
        Length(max=200, message='URL must be less than 200 characters')
    ])
    
    submit = SubmitField('Save Preferences')
    
    def validate_date_of_birth(self, date_of_birth):
        """Validate date of birth"""
        if date_of_birth.data:
            today = date.today()
            if date_of_birth.data > today:
                raise ValidationError('Date of birth cannot be in the future')
            
            age = today.year - date_of_birth.data.year - ((today.month, today.day) < (date_of_birth.data.month, date_of_birth.data.day))
            if age < 13:
                raise ValidationError('You must be at least 13 years old to use this service')
            if age > 120:
                raise ValidationError('Please enter a valid date of birth')

class PrivacySettingsForm(FlaskForm):
    """Privacy settings form"""
    is_profile_public = BooleanField('Make my profile public', default=True)
    show_email = BooleanField('Show my email on profile')
    show_location = BooleanField('Show my location on profile', default=True)
    show_age = BooleanField('Show my age on profile')
    allow_friend_requests = BooleanField('Allow friend requests', default=True)
    
    submit = SubmitField('Update Privacy Settings')

class UserSearchForm(FlaskForm):
    """User search form"""
    search_query = StringField('Search Users', validators=[
        DataRequired(message='Please enter a search term'),
        Length(min=2, max=50, message='Search term must be between 2-50 characters')
    ])
    submit = SubmitField('Search')
