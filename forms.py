from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField, DateField, SelectMultipleField, widgets, IntegerField, FloatField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, URL, NumberRange
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
        if not re.match(r'^[a-zA-Z0-9_]+$', username.data):
            raise ValidationError('Username can only contain letters, numbers, and underscores')
        
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username is already taken. Please choose a different one.')
    
    def validate_email(self, email):
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

class CreateGroupForm(FlaskForm):
    """Form for creating a new group"""
    name = StringField('Group Name', validators=[
        DataRequired(message='Group name is required'),
        Length(min=3, max=100, message='Group name must be between 3-100 characters')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500, message='Description must be less than 500 characters')
    ])
    privacy_level = SelectField('Privacy Level', choices=[
        ('public', 'Public - Anyone can find and join'),
        ('invite_only', 'Invite Only - Members can invite others'),
        ('private', 'Private - Admin approval required')
    ], default='public', validators=[DataRequired()])
    max_members = SelectField('Maximum Members', choices=[
        (10, '10 members'),
        (25, '25 members'),
        (50, '50 members'),
        (100, '100 members'),
        (250, '250 members')
    ], coerce=int, default=50, validators=[DataRequired()])
    allow_member_invites = BooleanField('Allow members to invite others', default=True)
    auto_accept_requests = BooleanField('Automatically accept join requests', default=False)
    submit = SubmitField('Create Group')
    
    def validate_name(self, field):
        from models import Group
        is_valid, message = Group.validate_group_name(field.data)
        if not is_valid:
            raise ValidationError(message)

class EditGroupForm(FlaskForm):
    """Form for editing group settings"""
    name = StringField('Group Name', validators=[
        DataRequired(message='Group name is required'),
        Length(min=3, max=100, message='Group name must be between 3-100 characters')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500, message='Description must be less than 500 characters')
    ])
    privacy_level = SelectField('Privacy Level', choices=[
        ('public', 'Public - Anyone can find and join'),
        ('invite_only', 'Invite Only - Members can invite others'),
        ('private', 'Private - Admin approval required')
    ], validators=[DataRequired()])
    max_members = SelectField('Maximum Members', choices=[
        (10, '10 members'),
        (25, '25 members'),
        (50, '50 members'),
        (100, '100 members'),
        (250, '250 members')
    ], coerce=int, validators=[DataRequired()])
    allow_member_invites = BooleanField('Allow members to invite others')
    auto_accept_requests = BooleanField('Automatically accept join requests')
    submit = SubmitField('Update Group')
    
    def __init__(self, group_id=None, *args, **kwargs):
        super(EditGroupForm, self).__init__(*args, **kwargs)
        self.group_id = group_id
    
    def validate_name(self, field):
        from models import Group
        is_valid, message = Group.validate_group_name(field.data, self.group_id)
        if not is_valid:
            raise ValidationError(message)

class JoinGroupForm(FlaskForm):
    """Form for joining a group"""
    submit = SubmitField('Join Group')

class LeaveGroupForm(FlaskForm):
    """Form for leaving a group"""
    submit = SubmitField('Leave Group')

class SearchGroupsForm(FlaskForm):
    """Form for searching groups"""
    search_query = StringField('Search Groups', validators=[
        Optional(),
        Length(max=50, message='Search term must be less than 50 characters')
    ])
    submit = SubmitField('Search')

class ManageMemberForm(FlaskForm):
    """Form for managing group members"""
    action = SelectField('Action', choices=[
        ('promote_admin', 'Promote to Admin'),
        ('promote_moderator', 'Promote to Moderator'),
        ('demote_member', 'Demote to Member'),
        ('remove', 'Remove from Group')
    ], validators=[DataRequired()])
    submit = SubmitField('Apply Action')

class DeleteGroupForm(FlaskForm):
    """Form for deleting a group"""
    confirm_name = StringField('Type group name to confirm deletion', validators=[
        DataRequired(message='Please type the group name to confirm deletion')
    ])
    submit = SubmitField('Delete Group')
    
    def __init__(self, group_name=None, *args, **kwargs):
        super(DeleteGroupForm, self).__init__(*args, **kwargs)
        self.group_name = group_name
    
    def validate_confirm_name(self, field):
        if self.group_name and field.data != self.group_name:
            raise ValidationError('Group name does not match')



class ContentSearchForm(FlaskForm):
    """Form for content search and filtering"""
    search = StringField('Search', validators=[Optional()])
    genre = SelectField('Genre', choices=[('', 'All Genres')], validators=[Optional()])
    year = SelectField('Year', choices=[('', 'All Years')], validators=[Optional()])
    rating = SelectField('Minimum Rating', 
                        choices=[
                            ('', 'Any Rating'),
                            ('7.0', '7.0+'),
                            ('8.0', '8.0+'),
                            ('9.0', '9.0+')
                        ], 
                        validators=[Optional()])
    platform = SelectField('Platform', choices=[('', 'All Platforms')], validators=[Optional()])
    content_type = SelectField('Content Type', 
                              choices=[
                                  ('', 'All Types'),
                                  ('movie', 'Movies'),
                                  ('tv_show', 'TV Shows'),
                                  ('documentary', 'Documentaries')
                              ], 
                              validators=[Optional()])
    sort = SelectField('Sort By',
                      choices=[
                          ('title', 'Title A-Z'),
                          ('year', 'Newest First'),
                          ('rating', 'Highest Rated'),
                          ('created', 'Recently Added')
                      ],
                      default='title',
                      validators=[Optional()])
    submit = SubmitField('Search')

class ContentRatingForm(FlaskForm):
    """Form for rating content"""
    rating = FloatField('Rating (1-10)', validators=[
        DataRequired(message='Rating is required'),
        NumberRange(min=1, max=10, message='Rating must be between 1 and 10')
    ])
    review = TextAreaField('Review (optional)', validators=[
        Optional(),
        Length(max=1000, message='Review cannot exceed 1000 characters')
    ])
    submit = SubmitField('Submit Rating')

class TMDBImportForm(FlaskForm):
    """Form for importing content from TMDB"""
    tmdb_id = IntegerField('TMDB ID', validators=[
        DataRequired(message='TMDB ID is required'),
        NumberRange(min=1, message='Invalid TMDB ID')
    ])
    content_type = SelectField('Content Type',
                              choices=[
                                  ('movie', 'Movie'),
                                  ('tv', 'TV Show')
                              ],
                              default='movie',
                              validators=[DataRequired()])
    submit = SubmitField('Import from TMDB')



class AddToWatchlistForm(FlaskForm):
    """Form for adding content to personal watchlist"""
    status = SelectField('Status', choices=[
        ('want_to_watch', 'Want to Watch'),
        ('watching', 'Currently Watching'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('dropped', 'Dropped')
    ], default='want_to_watch', validators=[DataRequired()])
    
    priority = SelectField('Priority', choices=[
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low')
    ], default='medium', validators=[DataRequired()])
    
    personal_notes = TextAreaField('Personal Notes', validators=[
        Optional(),
        Length(max=1000, message='Notes must be less than 1000 characters')
    ])
    
    personal_rating = FloatField('Personal Rating (1-10)', validators=[
        Optional(),
        NumberRange(min=1, max=10, message='Rating must be between 1 and 10')
    ])
    
    is_public = BooleanField('Make this visible to friends', default=True)
    
    submit = SubmitField('Add to Watchlist')


class UpdateWatchlistForm(FlaskForm):
    """Form for updating watchlist items"""
    status = SelectField('Status', choices=[
        ('want_to_watch', 'Want to Watch'),
        ('watching', 'Currently Watching'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('dropped', 'Dropped')
    ], validators=[DataRequired()])
    
    priority = SelectField('Priority', choices=[
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low')
    ], validators=[DataRequired()])
    
    current_season = IntegerField('Current Season', validators=[
        Optional(),
        NumberRange(min=1, message='Season must be at least 1')
    ])
    
    current_episode = IntegerField('Current Episode', validators=[
        Optional(),
        NumberRange(min=1, message='Episode must be at least 1')
    ])
    
    personal_notes = TextAreaField('Personal Notes', validators=[
        Optional(),
        Length(max=1000, message='Notes must be less than 1000 characters')
    ])
    
    personal_rating = FloatField('Personal Rating (1-10)', validators=[
        Optional(),
        NumberRange(min=1, max=10, message='Rating must be between 1 and 10')
    ])
    
    is_public = BooleanField('Make this visible to friends')
    
    submit = SubmitField('Update')


class AddToGroupWatchlistForm(FlaskForm):
    """Form for adding content to group watchlist"""
    status = SelectField('Status', choices=[
        ('planned', 'Planned'),
        ('watching', 'Currently Watching'),
        ('completed', 'Completed')
    ], default='planned', validators=[DataRequired()])
    
    priority = SelectField('Priority', choices=[
        ('high', 'High Priority'),
        ('medium', 'Medium Priority'),
        ('low', 'Low Priority')
    ], default='medium', validators=[DataRequired()])
    
    description = TextAreaField('Why should we watch this?', validators=[
        Optional(),
        Length(max=500, message='Description must be less than 500 characters')
    ])
    
    scheduled_for = DateField('Scheduled Date (Optional)', validators=[Optional()])
    
    submit = SubmitField('Add to Group Watchlist')


class ShareWatchlistForm(FlaskForm):
    """Form for sharing personal watchlist with friends"""
    friend_id = SelectField('Share With', coerce=int, validators=[DataRequired(message='Please select a friend')])
    
    share_type = SelectField('Permission Level', choices=[
        ('view', 'View Only'),
        ('edit', 'View and Edit')
    ], default='view', validators=[DataRequired()])
    
    shared_statuses = SelectMultipleField('Share Which Lists?', choices=[
        ('want_to_watch', 'Want to Watch'),
        ('watching', 'Currently Watching'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('dropped', 'Dropped')
    ], default=['want_to_watch', 'watching', 'completed'])
    
    submit = SubmitField('Share Watchlist')


class CreateWatchSessionForm(FlaskForm):
    """Form for creating group watch sessions"""
    session_name = StringField('Session Name', validators=[
        Optional(),
        Length(max=200, message='Session name must be less than 200 characters')
    ])
    
    scheduled_time = DateField('Scheduled Date', validators=[DataRequired()])
    
    season_number = IntegerField('Season (for TV shows)', validators=[
        Optional(),
        NumberRange(min=1, message='Season must be at least 1')
    ])
    
    episode_number = IntegerField('Episode (for TV shows)', validators=[
        Optional(),
        NumberRange(min=1, message='Episode must be at least 1')
    ])
    
    max_participants = IntegerField('Max Participants', validators=[
        DataRequired(),
        NumberRange(min=2, max=50, message='Participants must be between 2 and 50')
    ], default=10)
    
    is_public = BooleanField('Allow non-members to join', default=False)
    
    notes = TextAreaField('Session Notes', validators=[
        Optional(),
        Length(max=1000, message='Notes must be less than 1000 characters')
    ])
    
    submit = SubmitField('Create Watch Session')


class WatchlistFilterForm(FlaskForm):
    """Form for filtering watchlist items"""
    status = SelectField('Status', choices=[
        ('', 'All Statuses'),
        ('want_to_watch', 'Want to Watch'),
        ('watching', 'Currently Watching'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('dropped', 'Dropped')
    ], default='')
    
    priority = SelectField('Priority', choices=[
        ('', 'All Priorities'),
        ('high', 'High Priority'),
        ('medium', 'Medium Priority'),
        ('low', 'Low Priority')
    ], default='')
    
    content_type = SelectField('Content Type', choices=[
        ('', 'All Types'),
        ('movie', 'Movies'),
        ('tv_show', 'TV Shows'),
        ('documentary', 'Documentaries')
    ], default='')
    
    genre = StringField('Genre', validators=[Optional()])
    
    sort_by = SelectField('Sort By', choices=[
        ('added_at_desc', 'Recently Added'),
        ('added_at_asc', 'Oldest First'),
        ('priority_high', 'Priority (High to Low)'),
        ('priority_low', 'Priority (Low to High)'),
        ('title_asc', 'Title (A-Z)'),
        ('title_desc', 'Title (Z-A)'),
        ('rating_desc', 'Highest Rated'),
        ('year_desc', 'Newest Content'),
        ('year_asc', 'Oldest Content')
    ], default='added_at_desc')
    
    submit = SubmitField('Apply Filters')



class DiscussionForm(FlaskForm):
    """Form for creating and editing discussions"""
    message = TextAreaField('Message', validators=[
        DataRequired(message='Message is required'),
        Length(min=1, max=2000, message='Message must be between 1-2000 characters')
    ], render_kw={
        'placeholder': 'Share your thoughts... Use @username to mention someone',
        'rows': 4
    })
    has_spoilers = BooleanField('Contains Spoilers', default=False)
    submit = SubmitField('Post Discussion')


class ReportDiscussionForm(FlaskForm):
    """Form for reporting inappropriate discussions"""
    reason = SelectField('Reason', validators=[DataRequired()], choices=[
        ('spam', 'Spam'),
        ('inappropriate', 'Inappropriate Content'),
        ('spoilers', 'Unmarked Spoilers'),
        ('harassment', 'Harassment'),
        ('off_topic', 'Off Topic'),
        ('other', 'Other')
    ])
    description = TextAreaField('Additional Details', validators=[
        Length(max=500, message='Description must be less than 500 characters')
    ], render_kw={
        'placeholder': 'Please provide additional details about why you are reporting this discussion...',
        'rows': 3
    })
    submit = SubmitField('Submit Report')


class DiscussionSearchForm(FlaskForm):
    """Form for searching discussions"""
    query = StringField('Search Discussions', validators=[
        Length(min=1, max=100, message='Search query must be between 1-100 characters')
    ], render_kw={
        'placeholder': 'Search for discussions...'
    })
    submit = SubmitField('Search')



class ContentProposalForm(FlaskForm):
    """Form for creating content proposals"""
    
    # Content selection (existing or new)
    content_type_choice = SelectField('Content Type', choices=[
        ('existing', 'Existing Content'),
        ('new', 'New Content')
    ], validators=[DataRequired()])
    
    # For existing content
    existing_content_id = IntegerField('Content ID', validators=[Optional()])
    
    # For new content
    title = StringField('Title', validators=[
        Optional(),
        Length(max=200, message='Title must be less than 200 characters')
    ])
    content_type = SelectField('Type', choices=[
        ('movie', 'Movie'),
        ('tv_show', 'TV Show'),
        ('documentary', 'Documentary'),
        ('anime', 'Anime'),
        ('series', 'Series'),
        ('mini_series', 'Mini Series'),
        ('other', 'Other')
    ], validators=[Optional()])
    release_year = IntegerField('Release Year', validators=[
        Optional(),
        NumberRange(min=1900, max=2030, message='Enter a valid release year')
    ])
    genre = StringField('Genre', validators=[
        Optional(),
        Length(max=100, message='Genre must be less than 100 characters')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=1000, message='Description must be less than 1000 characters')
    ])
    external_id = StringField('TMDB/IMDB ID', validators=[
        Optional(),
        Length(max=100, message='External ID must be less than 100 characters')
    ])
    external_source = SelectField('External Source', choices=[
        ('tmdb', 'TMDB'),
        ('imdb', 'IMDB'),
        ('other', 'Other')
    ], validators=[Optional()])
    
    # Proposal details
    reason = TextAreaField('Reason for Proposal', validators=[
        DataRequired(message='Please provide a reason for this proposal'),
        Length(min=10, max=1000, message='Reason must be between 10-1000 characters')
    ], render_kw={
        'placeholder': 'Why should the group watch this content? What makes it interesting or relevant?'
    })
    
    priority = SelectField('Priority', choices=[
        ('high', 'High - Watch Soon'),
        ('medium', 'Medium - Normal Priority'),
        ('low', 'Low - Watch Eventually')
    ], default='medium', validators=[DataRequired()])
    
    proposed_watch_date = DateField('Proposed Watch Date', validators=[Optional()])
    
    # Voting settings
    required_votes = IntegerField('Minimum Votes Required', validators=[
        NumberRange(min=1, max=50, message='Must be between 1-50 votes'),
        DataRequired()
    ], default=3)
    
    approval_threshold = FloatField('Approval Threshold (%)', validators=[
        NumberRange(min=50.0, max=100.0, message='Must be between 50-100%'),
        DataRequired()
    ], default=60.0)
    
    submit = SubmitField('Submit Proposal')
    
    def validate_content_details(self):
        """Custom validation for content details"""
        if self.content_type_choice.data == 'existing':
            if not self.existing_content_id.data:
                raise ValidationError('Please select existing content or choose "New Content"')
        else:  # new content
            if not self.title.data:
                raise ValidationError('Title is required for new content')
            if not self.content_type.data:
                raise ValidationError('Content type is required for new content')


class EditProposalForm(FlaskForm):
    """Form for editing existing proposals"""
    
    reason = TextAreaField('Reason for Proposal', validators=[
        DataRequired(message='Please provide a reason for this proposal'),
        Length(min=10, max=1000, message='Reason must be between 10-1000 characters')
    ])
    
    priority = SelectField('Priority', choices=[
        ('high', 'High - Watch Soon'),
        ('medium', 'Medium - Normal Priority'),
        ('low', 'Low - Watch Eventually')
    ], validators=[DataRequired()])
    
    proposed_watch_date = DateField('Proposed Watch Date', validators=[Optional()])
    
    # Admin-only fields
    admin_notes = TextAreaField('Admin Notes', validators=[
        Optional(),
        Length(max=500, message='Admin notes must be less than 500 characters')
    ])
    
    submit = SubmitField('Update Proposal')


class VoteProposalForm(FlaskForm):
    """Form for voting on proposals"""
    
    vote_type = SelectField('Vote', choices=[
        ('upvote', 'Approve - I want to watch this'),
        ('downvote', 'Reject - I don\'t want to watch this')
    ], validators=[DataRequired()])
    
    comment = TextAreaField('Comment (Optional)', validators=[
        Optional(),
        Length(max=500, message='Comment must be less than 500 characters')
    ], render_kw={
        'placeholder': 'Share your thoughts about this proposal...'
    })
    
    submit = SubmitField('Cast Vote')


class ProposalFilterForm(FlaskForm):
    """Form for filtering proposals"""
    
    status = SelectField('Status', choices=[
        ('all', 'All Proposals'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired')
    ], default='all')
    
    priority = SelectField('Priority', choices=[
        ('all', 'All Priorities'),
        ('high', 'High Priority'),
        ('medium', 'Medium Priority'),
        ('low', 'Low Priority')
    ], default='all')
    
    content_type = SelectField('Content Type', choices=[
        ('all', 'All Types'),
        ('movie', 'Movies'),
        ('tv_show', 'TV Shows'),
        ('documentary', 'Documentaries'),
        ('anime', 'Anime'),
        ('series', 'Series'),
        ('other', 'Other')
    ], default='all')
    
    proposer = StringField('Proposed By', validators=[
        Optional(),
        Length(max=50, message='Username must be less than 50 characters')
    ])
    
    sort_by = SelectField('Sort By', choices=[
        ('created_desc', 'Newest First'),
        ('created_asc', 'Oldest First'),
        ('votes_desc', 'Most Votes'),
        ('approval_desc', 'Highest Approval Rate'),
        ('priority_desc', 'Highest Priority')
    ], default='created_desc')
    
    submit = SubmitField('Apply Filters')


class ProposalSearchForm(FlaskForm):
    """Form for searching proposals"""
    
    query = StringField('Search Proposals', validators=[
        Length(min=1, max=100, message='Search query must be between 1-100 characters')
    ], render_kw={
        'placeholder': 'Search by title, description, or proposer...'
    })
    
    submit = SubmitField('Search')


class ProposalActionForm(FlaskForm):
    """Form for admin actions on proposals"""
    
    action = SelectField('Action', choices=[
        ('approve', 'Approve Proposal'),
        ('reject', 'Reject Proposal'),
        ('feature', 'Feature Proposal'),
        ('unfeature', 'Remove Featured Status'),
        ('extend', 'Extend Voting Period'),
        ('close', 'Close Voting Early')
    ], validators=[DataRequired()])
    
    admin_notes = TextAreaField('Admin Notes', validators=[
        Optional(),
        Length(max=500, message='Admin notes must be less than 500 characters')
    ])
    
    submit = SubmitField('Execute Action')


class ProposalSettingsForm(FlaskForm):
    """Form for group proposal settings"""
    
    auto_approval_enabled = BooleanField('Enable Automatic Approval')
    
    default_required_votes = IntegerField('Default Minimum Votes', validators=[
        NumberRange(min=1, max=50, message='Must be between 1-50 votes'),
        DataRequired()
    ], default=3)
    
    default_approval_threshold = FloatField('Default Approval Threshold (%)', validators=[
        NumberRange(min=50.0, max=100.0, message='Must be between 50-100%'),
        DataRequired()
    ], default=60.0)
    
    proposal_expiry_days = IntegerField('Proposal Expiry (Days)', validators=[
        NumberRange(min=1, max=365, message='Must be between 1-365 days'),
        DataRequired()
    ], default=30)
    
    allow_member_proposals = BooleanField('Allow All Members to Create Proposals', default=True)
    
    require_admin_approval = BooleanField('Require Admin Approval for New Proposals')
    
    submit = SubmitField('Update Settings')
