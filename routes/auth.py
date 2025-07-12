from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from app import db
from forms import LoginForm, RegistrationForm, UpdateProfileForm, ChangePasswordForm
import os
from werkzeug.utils import secure_filename
from PIL import Image
import uuid

auth = Blueprint('auth', __name__)

def save_picture(form_picture):
    """Save uploaded profile picture with resizing"""
    # Generate random filename
    random_hex = uuid.uuid4().hex
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    
    # Create upload directory if it doesn't exist
    upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'profile_pics')
    os.makedirs(upload_path, exist_ok=True)
    
    picture_path = os.path.join(upload_path, picture_fn)
    
    # Resize image to 150x150
    output_size = (150, 150)
    img = Image.open(form_picture)
    img = img.resize(output_size, Image.Resampling.LANCZOS)
    img.save(picture_path)
    
    return picture_fn

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """User login page with form validation"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('Invalid username or password. Please check your credentials and try again.', 'error')
    
    return render_template('auth/login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page with comprehensive validation"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data.lower()
        )
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash(f'Account created successfully! Welcome to WatchTogether, {user.username}!', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating your account. Please try again.', 'error')
    
    return render_template('auth/register.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    """User logout"""
    username = current_user.username
    logout_user()
    flash(f'Goodbye, {username}! You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))

@auth.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html', user=current_user)

@auth.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    form = UpdateProfileForm(current_user.username, current_user.email)
    
    if form.validate_on_submit():
        # Handle profile picture upload
        if form.profile_picture.data:
            try:
                picture_file = save_picture(form.profile_picture.data)
                current_user.profile_picture = picture_file
            except Exception as e:
                flash('Error uploading profile picture. Please try again.', 'error')
                return render_template('auth/edit_profile.html', form=form)
        
        # Update user data
        current_user.username = form.username.data
        current_user.email = form.email.data.lower()
        if form.bio.data:
            current_user.bio = form.bio.data
        
        try:
            db.session.commit()
            flash('Your profile has been updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your profile. Please try again.', 'error')
    
    elif request.method == 'GET':
        # Pre-populate form with current user data
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.bio.data = current_user.bio or ''
    
    return render_template('auth/edit_profile.html', form=form)

@auth.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            try:
                db.session.commit()
                flash('Your password has been updated successfully!', 'success')
                return redirect(url_for('auth.profile'))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while changing your password. Please try again.', 'error')
        else:
            flash('Current password is incorrect. Please try again.', 'error')
    
    return render_template('auth/change_password.html', form=form)
