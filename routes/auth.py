from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import User, Friendship, Notification
from app import db
from forms import LoginForm, RegistrationForm, UpdateProfileForm, ChangePasswordForm, UserPreferencesForm, PrivacySettingsForm, UserSearchForm
import os
from werkzeug.utils import secure_filename
from PIL import Image
import uuid
from datetime import datetime

auth = Blueprint('auth', __name__)

def save_picture(form_picture):
    random_hex = uuid.uuid4().hex
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    
    upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'profile_pics')
    os.makedirs(upload_path, exist_ok=True)
    
    picture_path = os.path.join(upload_path, picture_fn)
    
    output_size = (150, 150)
    img = Image.open(form_picture)
    img = img.resize(output_size, Image.Resampling.LANCZOS)
    img.save(picture_path)
    
    return picture_fn

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            user.update_login_info()
            login_user(user, remember=form.remember_me.data)
            db.session.commit()
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
        if form.profile_picture.data:
            try:
                picture_file = save_picture(form.profile_picture.data)
                current_user.profile_picture = picture_file
            except Exception as e:
                flash('Error uploading profile picture. Please try again.', 'error')
                return render_template('auth/edit_profile.html', form=form)
        
        current_user.username = form.username.data
        current_user.email = form.email.data.lower()
        if form.bio.data:
            current_user.bio = form.bio.data
        if form.first_name.data:
            current_user.first_name = form.first_name.data
        if form.last_name.data:
            current_user.last_name = form.last_name.data
        if form.location.data:
            current_user.location = form.location.data
        if form.website_url.data:
            current_user.website_url = form.website_url.data
        
        try:
            db.session.commit()
            flash('Your profile has been updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your profile. Please try again.', 'error')
    
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.bio.data = current_user.bio or ''
        form.first_name.data = current_user.first_name or ''
        form.last_name.data = current_user.last_name or ''
        form.location.data = current_user.location or ''
        form.website_url.data = current_user.website_url or ''
    
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

@auth.route('/profile/preferences', methods=['GET', 'POST'])
@login_required
def preferences():
    """User preferences page"""
    form = UserPreferencesForm()
    
    if form.validate_on_submit():
        if form.first_name.data:
            current_user.first_name = form.first_name.data
        if form.last_name.data:
            current_user.last_name = form.last_name.data
        if form.date_of_birth.data:
            current_user.date_of_birth = form.date_of_birth.data
        if form.location.data:
            current_user.location = form.location.data
        if form.bio.data:
            current_user.bio = form.bio.data
        if form.website_url.data:
            current_user.website_url = form.website_url.data
        
        current_user.set_favorite_genres(form.favorite_genres.data)
        current_user.set_content_types(form.content_types.data)
        
        viewing_habits = {
            'preferred_viewing_time': form.preferred_viewing_time.data,
            'preferred_duration': form.preferred_duration.data,
            'binge_watcher': form.binge_watcher.data,
            'subtitles_preference': form.subtitles_preference.data
        }
        current_user.set_viewing_habits(viewing_habits)
        
        social_links = {}
        if form.twitter_url.data:
            social_links['twitter'] = form.twitter_url.data
        if form.instagram_url.data:
            social_links['instagram'] = form.instagram_url.data
        if form.facebook_url.data:
            social_links['facebook'] = form.facebook_url.data
        current_user.set_social_links(social_links)
        
        try:
            db.session.commit()
            flash('Your preferences have been updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your preferences. Please try again.', 'error')
    
    elif request.method == 'GET':
        form.first_name.data = current_user.first_name or ''
        form.last_name.data = current_user.last_name or ''
        form.date_of_birth.data = current_user.date_of_birth
        form.location.data = current_user.location or ''
        form.bio.data = current_user.bio or ''
        form.website_url.data = current_user.website_url or ''
        
        form.favorite_genres.data = current_user.get_favorite_genres()
        form.content_types.data = current_user.get_content_types()
        
        viewing_habits = current_user.get_viewing_habits()
        form.preferred_viewing_time.data = viewing_habits.get('preferred_viewing_time', '')
        form.preferred_duration.data = viewing_habits.get('preferred_duration', '')
        form.binge_watcher.data = viewing_habits.get('binge_watcher', False)
        form.subtitles_preference.data = viewing_habits.get('subtitles_preference', False)
        
        social_links = current_user.get_social_links()
        form.twitter_url.data = social_links.get('twitter', '')
        form.instagram_url.data = social_links.get('instagram', '')
        form.facebook_url.data = social_links.get('facebook', '')
    
    return render_template('auth/preferences.html', form=form)

@auth.route('/profile/privacy', methods=['GET', 'POST'])
@login_required
def privacy():
    """Privacy settings page"""
    form = PrivacySettingsForm()
    
    if form.validate_on_submit():
        current_user.is_profile_public = form.is_profile_public.data
        current_user.show_email = form.show_email.data
        current_user.show_location = form.show_location.data
        current_user.show_age = form.show_age.data
        current_user.allow_friend_requests = form.allow_friend_requests.data
        
        try:
            db.session.commit()
            flash('Your privacy settings have been updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your privacy settings. Please try again.', 'error')
    
    elif request.method == 'GET':
        # Pre-populate form with current user data
        form.is_profile_public.data = current_user.is_profile_public
        form.show_email.data = current_user.show_email
        form.show_location.data = current_user.show_location
        form.show_age.data = current_user.show_age
        form.allow_friend_requests.data = current_user.allow_friend_requests
    
    return render_template('auth/privacy.html', form=form)

@auth.route('/users/search', methods=['GET', 'POST'])
@login_required
def search_users():
    """Search for users"""
    form = UserSearchForm()
    users = []
    
    if form.validate_on_submit():
        query = form.search_query.data.strip()
        users = User.search_users(query, current_user.id)
        if not users:
            flash(f'No users found matching "{query}"', 'info')
    
    return render_template('auth/search_users.html', form=form, users=users)

@auth.route('/users/<int:user_id>')
@login_required
def view_profile(user_id):
    """View another user's profile"""
    user = User.query.get_or_404(user_id)
    
    # Check if profile is public or if it's the current user
    if not user.is_profile_public and user.id != current_user.id:
        flash('This profile is private.', 'error')
        return redirect(url_for('auth.search_users'))
    
    return render_template('auth/view_profile.html', user=user, is_own_profile=(user.id == current_user.id))

@auth.route('/friends')
@login_required
def friends():
    """Friends list page"""
    friends = current_user.get_friends()
    pending_requests = current_user.get_pending_friend_requests()
    sent_requests = current_user.get_sent_friend_requests()
    blocked_users = current_user.get_blocked_users()
    
    return render_template('auth/friends.html', 
                         friends=friends,
                         pending_requests=pending_requests,
                         sent_requests=sent_requests,
                         blocked_users=blocked_users)

@auth.route('/notifications')
@login_required
def notifications():
    """Notifications page"""
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).limit(50).all()
    
    # Mark notifications as read
    unread_notifications = [n for n in notifications if not n.is_read]
    for notification in unread_notifications:
        notification.is_read = True
    
    if unread_notifications:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
    
    return render_template('auth/notifications.html', notifications=notifications)

# AJAX API endpoints for friend actions
@auth.route('/api/friend-request/send', methods=['POST'])
@login_required
def api_send_friend_request():
    """API endpoint to send friend request"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID is required'})
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        success, message = current_user.send_friend_request(user)
        return jsonify({'success': success, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'An error occurred'})

@auth.route('/api/friend-request/accept', methods=['POST'])
@login_required
def api_accept_friend_request():
    """API endpoint to accept friend request"""
    try:
        data = request.get_json(force=True)
        current_app.logger.info(f"Friend request accept API called with data: {data}")
        user_id = data.get('user_id')
        if not user_id:
            current_app.logger.error("No user_id provided in request data")
            return jsonify({'success': False, 'message': 'User ID is required'}), 400
        user = User.query.get(user_id)
        if not user:
            current_app.logger.error(f"User not found for user_id: {user_id}")
            return jsonify({'success': False, 'message': 'User not found'}), 404
        success, message = current_user.accept_friend_request(user)
        current_app.logger.info(f"Accept friend request result: success={success}, message={message}")
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Exception in accept friend request: {str(e)}")
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

@auth.route('/api/friend-request/decline', methods=['POST'])
@login_required
def api_decline_friend_request():
    """API endpoint to decline friend request"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID is required'})
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        success, message = current_user.decline_friend_request(user)
        return jsonify({'success': success, 'message': message})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'})

@auth.route('/api/friend/remove', methods=['POST'])
@login_required
def api_remove_friend():
    """API endpoint to remove friend"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID is required'})
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        success, message = current_user.remove_friend(user)
        return jsonify({'success': success, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'An error occurred'})

@auth.route('/api/user/block', methods=['POST'])
@login_required
def api_block_user():
    """API endpoint to block user"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID is required'})
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        success, message = current_user.block_user(user)
        return jsonify({'success': success, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'An error occurred'})

@auth.route('/api/user/unblock', methods=['POST'])
@login_required
def api_unblock_user():
    """API endpoint to unblock user"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID is required'})
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        success, message = current_user.unblock_user(user)
        return jsonify({'success': success, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'An error occurred'})

@auth.route('/api/friend-status/<int:user_id>')
@login_required
def api_get_friend_status(user_id):
    """API endpoint to get friend status with a user"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        status = current_user.get_friend_status_with(user)
        return jsonify({'success': True, 'status': status})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'An error occurred'})

@auth.route('/api/notifications/count')
@login_required
def api_get_notifications_count():
    """API endpoint to get unread notifications count"""
    try:
        count = current_user.get_unread_notifications_count()
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        return jsonify({'success': False, 'message': 'An error occurred'})

@auth.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
def api_mark_all_notifications_read():
    """API endpoint to mark all notifications as read"""
    try:
        # Mark all unread notifications as read
        unread_notifications = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).all()
        
        for notification in unread_notifications:
            notification.is_read = True
        
        if unread_notifications:
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Marked {len(unread_notifications)} notifications as read'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Failed to mark notifications as read'
        }), 500

@auth.route('/api/notifications/<int:notification_id>/mark-read', methods=['POST'])
@login_required
def api_mark_notification_read(notification_id):
    """API endpoint to mark a specific notification as read"""
    try:
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first()
        
        if not notification:
            return jsonify({
                'success': False,
                'message': 'Notification not found'
            }), 404
        
        notification.is_read = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Notification marked as read'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Failed to mark notification as read'
        }), 500
