from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import re
import json

class User(UserMixin, db.Model):
    """User model for authentication and user management"""
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile_picture = db.Column(db.String(255), default='default.jpg')
    bio = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # profile fields
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    favorite_genres = db.Column(db.Text, nullable=True)  # JSON string
    content_types = db.Column(db.Text, nullable=True)    # JSON string
    viewing_habits = db.Column(db.Text, nullable=True)   # JSON string
    
    # Privacy settings
    is_profile_public = db.Column(db.Boolean, default=True)
    show_email = db.Column(db.Boolean, default=False)
    show_location = db.Column(db.Boolean, default=True)
    show_age = db.Column(db.Boolean, default=False)
    allow_friend_requests = db.Column(db.Boolean, default=True)
    
    # Social features
    website_url = db.Column(db.String(200), nullable=True)
    social_links = db.Column(db.Text, nullable=True)  # JSON string
    
    # Activity tracking
    last_login = db.Column(db.DateTime, nullable=True)
    login_count = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the user's password"""
        return check_password_hash(self.password_hash, password)
    
    # Profile data helpers
    def get_favorite_genres(self):
        """Get favorite genres as a list"""
        if self.favorite_genres:
            try:
                return json.loads(self.favorite_genres)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_favorite_genres(self, genres_list):
        """Set favorite genres from a list"""
        if genres_list:
            self.favorite_genres = json.dumps(genres_list)
        else:
            self.favorite_genres = None
    
    def get_content_types(self):
        """Get preferred content types as a list"""
        if self.content_types:
            try:
                return json.loads(self.content_types)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_content_types(self, types_list):
        """Set content types from a list"""
        if types_list:
            self.content_types = json.dumps(types_list)
        else:
            self.content_types = None
    
    def get_viewing_habits(self):
        """Get viewing habits as a dictionary"""
        if self.viewing_habits:
            try:
                return json.loads(self.viewing_habits)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_viewing_habits(self, habits_dict):
        """Set viewing habits from a dictionary"""
        if habits_dict:
            self.viewing_habits = json.dumps(habits_dict)
        else:
            self.viewing_habits = None
    
    def get_social_links(self):
        """Get social links as a dictionary"""
        if self.social_links:
            try:
                return json.loads(self.social_links)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_social_links(self, links_dict):
        """Set social links from a dictionary"""
        if links_dict:
            self.social_links = json.dumps(links_dict)
        else:
            self.social_links = None
    
    def get_full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return self.username
    
    def get_age(self):
        """Calculate user's age from date of birth"""
        if self.date_of_birth:
            today = datetime.now().date()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None
    
    def is_profile_complete(self):
        """Check if profile is reasonably complete"""
        required_fields = [self.first_name, self.bio]
        optional_fields = [self.location, self.favorite_genres]
        
        required_complete = all(field for field in required_fields)
        optional_complete = any(field for field in optional_fields)
        
        return required_complete and optional_complete
    
    def update_login_info(self):
        """Update login tracking information"""
        self.last_login = datetime.utcnow()
        self.login_count += 1
    
    @classmethod
    def search_users(cls, query, current_user_id=None):
        """Search for users by username, first name, or last name"""
        search_query = f"%{query}%"
        users = cls.query.filter(
            db.and_(
                cls.is_active == True,
                cls.is_profile_public == True,
                cls.id != current_user_id,  # Exclude current user
                db.or_(
                    cls.username.ilike(search_query),
                    cls.first_name.ilike(search_query),
                    cls.last_name.ilike(search_query)
                )
            )
        ).limit(20).all()
        return users
    
    @staticmethod
    def validate_username(username):
        """Validate username format and availability"""
        if not username or len(username) < 3 or len(username) > 20:
            return False, "Username must be between 3-20 characters"
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "Username can only contain letters, numbers, and underscores"
        
        if User.query.filter_by(username=username).first():
            return False, "Username is already taken"
        
        return True, "Valid username"
    
    @staticmethod
    def validate_email(email):
        """Validate email format and availability"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not email or not re.match(email_pattern, email):
            return False, "Please enter a valid email address"
        
        if User.query.filter_by(email=email).first():
            return False, "Email is already registered"
        
        return True, "Valid email"
    
    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if not password or len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        return True, "Strong password"
    
    def get_profile_picture_url(self):
        """Get the URL for the user's profile picture"""
        if self.profile_picture and self.profile_picture != 'default.jpg':
            return f'/static/uploads/profile_pics/{self.profile_picture}'
        return '/static/images/default_avatar.svg'

    # Friend-related methods
    def send_friend_request(self, user):
        """Send a friend request to another user"""
        if not user.allow_friend_requests:
            return False, "User is not accepting friend requests"
        
        if user.id == self.id:
            return False, "You cannot send a friend request to yourself"
        
        existing_friendship = Friendship.get_friendship(self.id, user.id)
        if existing_friendship:
            if existing_friendship.status == 'pending':
                return False, "Friend request already sent"
            elif existing_friendship.status == 'accepted':
                return False, "You are already friends"
            elif existing_friendship.status == 'blocked':
                return False, "Unable to send friend request"
        
        # Create friendship
        friendship = Friendship(
            requester_id=self.id,
            addressee_id=user.id,
            status='pending'
        )
        
        # Create notification
        notification = Notification.create_friend_request_notification(user.id, self)
        
        try:
            db.session.add(friendship)
            db.session.add(notification)
            db.session.commit()
            return True, "Friend request sent successfully"
        except Exception as e:
            db.session.rollback()
            return False, "Failed to send friend request"
    
    def accept_friend_request(self, requester):
        """Accept a friend request from another user"""
        friendship = Friendship.query.filter_by(
            requester_id=requester.id,
            addressee_id=self.id,
            status='pending'
        ).first()
        
        if not friendship:
            return False, "No pending friend request found"
        
        try:
            # Update friendship status
            friendship.status = 'accepted'
            friendship.updated_at = datetime.utcnow()
            
            # Create notification for requester
            notification = Notification.create_friend_accepted_notification(requester.id, self)
            
            # Add both to session and commit
            db.session.add(friendship)  # Explicitly add the updated friendship
            db.session.add(notification)
            db.session.commit()
            return True, "Friend request accepted"
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to accept friend request: {str(e)}"
    
    def decline_friend_request(self, requester):
        """Decline a friend request from another user"""
        friendship = Friendship.query.filter_by(
            requester_id=requester.id,
            addressee_id=self.id,
            status='pending'
        ).first()
        
        if not friendship:
            return False, "No pending friend request found"
        
        try:
            # Update friendship status
            friendship.status = 'declined'
            friendship.updated_at = datetime.utcnow()
            
            # Explicitly add the updated friendship to session
            db.session.add(friendship)
            db.session.commit()
            return True, "Friend request declined"
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to decline friend request: {str(e)}"
    
    def remove_friend(self, friend):
        """Remove a friend (unfriend)"""
        friendship = Friendship.get_friendship(self.id, friend.id)
        
        if not friendship or friendship.status != 'accepted':
            return False, "You are not friends with this user"
        
        try:
            db.session.delete(friendship)
            db.session.commit()
            return True, "Friend removed successfully"
        except Exception as e:
            db.session.rollback()
            return False, "Failed to remove friend"
    
    def block_user(self, user):
        """Block a user"""
        friendship = Friendship.get_friendship(self.id, user.id)
        
        if friendship:
            friendship.status = 'blocked'
            friendship.updated_at = datetime.utcnow()
            # Make sure current user is the one doing the blocking
            if friendship.requester_id != self.id:
                friendship.requester_id = self.id
                friendship.addressee_id = user.id
        else:
            friendship = Friendship(
                requester_id=self.id,
                addressee_id=user.id,
                status='blocked'
            )
            db.session.add(friendship)
        
        try:
            db.session.commit()
            return True, "User blocked successfully"
        except Exception as e:
            db.session.rollback()
            return False, "Failed to block user"
    
    def unblock_user(self, user):
        """Unblock a user"""
        friendship = Friendship.query.filter_by(
            requester_id=self.id,
            addressee_id=user.id,
            status='blocked'
        ).first()
        
        if not friendship:
            return False, "User is not blocked"
        
        try:
            db.session.delete(friendship)
            db.session.commit()
            return True, "User unblocked successfully"
        except Exception as e:
            db.session.rollback()
            return False, "Failed to unblock user"
    
    def get_friends(self):
        """Get list of all friends"""
        friends_as_requester = db.session.query(User).join(
            Friendship, User.id == Friendship.addressee_id
        ).filter(
            Friendship.requester_id == self.id,
            Friendship.status == 'accepted'
        ).all()
        
        friends_as_addressee = db.session.query(User).join(
            Friendship, User.id == Friendship.requester_id
        ).filter(
            Friendship.addressee_id == self.id,
            Friendship.status == 'accepted'
        ).all()
        
        return list(set(friends_as_requester + friends_as_addressee))
    
    def get_pending_friend_requests(self):
        """Get list of pending friend requests received"""
        return db.session.query(User).join(
            Friendship, User.id == Friendship.requester_id
        ).filter(
            Friendship.addressee_id == self.id,
            Friendship.status == 'pending'
        ).all()
    
    def get_sent_friend_requests(self):
        """Get list of sent friend requests that are still pending"""
        return db.session.query(User).join(
            Friendship, User.id == Friendship.addressee_id
        ).filter(
            Friendship.requester_id == self.id,
            Friendship.status == 'pending'
        ).all()
    
    def get_blocked_users(self):
        """Get list of blocked users"""
        return db.session.query(User).join(
            Friendship, User.id == Friendship.addressee_id
        ).filter(
            Friendship.requester_id == self.id,
            Friendship.status == 'blocked'
        ).all()
    
    def get_unread_notifications_count(self):
        """Get count of unread notifications"""
        return Notification.query.filter_by(
            user_id=self.id,
            is_read=False
        ).count()
    
    def get_friendship_status(self, user):
        """Get friendship status with another user for template usage"""
        friendship = Friendship.get_friendship(self.id, user.id)
        
        if not friendship:
            return None
        
        if friendship.status == 'accepted':
            return 'friends'
        elif friendship.status == 'pending':
            if friendship.requester_id == self.id:
                return 'pending_outgoing'
            else:
                return 'pending_incoming'
        elif friendship.status == 'blocked':
            if friendship.requester_id == self.id:
                return 'blocked'
            else:
                return 'blocked_by'
        
        return None
    
    def get_rating_statistics(self):
        """Get rating statistics as a dictionary"""
        stats = self.rating_statistics
        if not stats:
            return None
        
        return {
            'average_rating': stats.average_rating,
            'total_ratings': stats.total_ratings,
            'total_reviews': stats.total_reviews,
            'rating_1_count': stats.rating_1_count,
            'rating_2_count': stats.rating_2_count,
            'rating_3_count': stats.rating_3_count,
            'rating_4_count': stats.rating_4_count,
            'rating_5_count': stats.rating_5_count,
        }


class Friendship(db.Model):
    """Friendship model to handle friend relationships"""
    
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    addressee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, accepted, blocked, declined
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    requester = db.relationship('User', foreign_keys=[requester_id], backref='sent_friend_requests')
    addressee = db.relationship('User', foreign_keys=[addressee_id], backref='received_friend_requests')
    
    __table_args__ = (db.UniqueConstraint('requester_id', 'addressee_id', name='unique_friendship'),)
    
    def __repr__(self):
        return f'<Friendship {self.requester.username} -> {self.addressee.username}: {self.status}>'

    @staticmethod
    def get_friendship(user1_id, user2_id):
        """Get friendship between two users (regardless of who initiated)"""
        return Friendship.query.filter(
            db.or_(
                db.and_(Friendship.requester_id == user1_id, Friendship.addressee_id == user2_id),
                db.and_(Friendship.requester_id == user2_id, Friendship.addressee_id == user1_id)
            )
        ).first()
    
    @staticmethod
    def are_friends(user1_id, user2_id):
        """Check if two users are friends"""
        friendship = Friendship.get_friendship(user1_id, user2_id)
        return friendship and friendship.status == 'accepted'
    
    @staticmethod
    def get_friend_status(user1_id, user2_id):
        """Get the status of friendship between two users"""
        friendship = Friendship.get_friendship(user1_id, user2_id)
        if not friendship:
            return None
        return {
            'status': friendship.status,
            'is_requester': friendship.requester_id == user1_id,
            'created_at': friendship.created_at,
            'updated_at': friendship.updated_at
        }

class Notification(db.Model):
    """Notification model for in-app notifications"""
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # friend_request, friend_accepted, etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    data = db.Column(db.Text, nullable=True)  # JSON data for additional info
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='notifications')
    
    def __repr__(self):
        return f'<Notification {self.type} for {self.user.username}>'
    
    def get_data(self):
        """Get notification data as dictionary"""
        if self.data:
            try:
                return json.loads(self.data)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_data(self, data_dict):
        """Set notification data from dictionary"""
        if data_dict:
            self.data = json.dumps(data_dict)
        else:
            self.data = None
    
    @staticmethod
    def create_friend_request_notification(addressee_id, requester):
        """Create a friend request notification"""
        notification = Notification(
            user_id=addressee_id,
            type='friend_request',
            title='New Friend Request',
            message=f'{requester.get_full_name() or requester.username} sent you a friend request'
        )
        notification.set_data({
            'requester_id': requester.id,
            'requester_username': requester.username,
            'requester_name': requester.get_full_name() or requester.username
        })
        return notification
    
    @staticmethod
    def create_friend_accepted_notification(requester_id, accepter):
        """Create a friend accepted notification"""
        notification = Notification(
            user_id=requester_id,
            type='friend_accepted',
            title='Friend Request Accepted',
            message=f'{accepter.get_full_name() or accepter.username} accepted your friend request'
        )
        notification.set_data({
            'friend_id': accepter.id,
            'friend_username': accepter.username,
            'friend_name': accepter.get_full_name() or accepter.username
        })
        return notification

class Group(db.Model):
    """Group model for managing watch groups"""
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    privacy_level = db.Column(db.String(20), nullable=False, default='public')  # public, private, invite_only
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Group settings
    max_members = db.Column(db.Integer, default=50)
    allow_member_invites = db.Column(db.Boolean, default=True)
    auto_accept_requests = db.Column(db.Boolean, default=False)
    
    # Relationships
    creator = db.relationship('User', backref='created_groups')
    members = db.relationship('GroupMember', back_populates='group', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Group {self.name}>'
    
    def get_member_count(self):
        """Get the number of members in the group"""
        return len(self.members)
    
    def get_admin_count(self):
        """Get the number of admins in the group"""
        return len([m for m in self.members if m.role == 'admin'])
    
    def is_member(self, user_id):
        """Check if a user is a member of the group"""
        return any(member.user_id == user_id for member in self.members)
    
    def get_member_role(self, user_id):
        """Get a user's role in the group"""
        member = next((m for m in self.members if m.user_id == user_id), None)
        return member.role if member else None
    
    def can_user_join(self, user_id):
        """Check if a user can join the group"""
        if self.is_member(user_id):
            return False, "Already a member"
        
        if self.privacy_level == 'private':
            return False, "Group is private"
        
        if self.get_member_count() >= self.max_members:
            return False, "Group is full"
        
        return True, "Can join"
    
    def can_user_edit(self, user_id):
        """Check if a user can edit group settings"""
        role = self.get_member_role(user_id)
        return role in ['admin'] or self.created_by == user_id
    
    def can_user_delete(self, user_id):
        """Check if a user can delete the group"""
        return self.created_by == user_id
    
    def can_user_manage_members(self, user_id):
        """Check if a user can manage group members"""
        role = self.get_member_role(user_id)
        return role in ['admin', 'moderator'] or self.created_by == user_id
    
    @staticmethod
    def search_public_groups(query=None, limit=20):
        """Search for public groups"""
        query_filter = Group.privacy_level == 'public'
        
        if query:
            search_pattern = f"%{query}%"
            query_filter = db.and_(
                Group.privacy_level == 'public',
                db.or_(
                    Group.name.ilike(search_pattern),
                    Group.description.ilike(search_pattern)
                )
            )
        
        return Group.query.filter(query_filter).order_by(Group.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def validate_group_name(name, group_id=None):
        """Validate group name"""
        if not name or len(name.strip()) < 3:
            return False, "Group name must be at least 3 characters long"
        
        if len(name.strip()) > 100:
            return False, "Group name must be less than 100 characters"
        
        # Check for existing group with same name (case insensitive)
        existing_query = Group.query.filter(Group.name.ilike(name.strip()))
        if group_id:
            existing_query = existing_query.filter(Group.id != group_id)
        
        if existing_query.first():
            return False, "A group with this name already exists"
        
        return True, "Valid group name"

class GroupMember(db.Model):
    """Group membership model"""
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='member')  # admin, moderator, member
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='group_memberships')
    group = db.relationship('Group', back_populates='members')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'group_id', name='unique_group_membership'),)
    
    def __repr__(self):
        return f'<GroupMember {self.user.username} in {self.group.name} as {self.role}>'
    
    def can_promote_to_admin(self, promoter_user_id):
        """Check if a user can be promoted to admin by the promoter"""
        if self.role == 'admin':
            return False, "User is already an admin"
        
        promoter_role = self.group.get_member_role(promoter_user_id)
        if promoter_role != 'admin' and self.group.created_by != promoter_user_id:
            return False, "Only admins can promote to admin"
        
        return True, "Can promote to admin"
    
    def can_demote_from_admin(self, demoter_user_id):
        """Check if a user can be demoted from admin by the demoter"""
        if self.role != 'admin':
            return False, "User is not an admin"
        
        if self.group.created_by == self.user_id:
            return False, "Cannot demote the group creator"
        
        if self.group.created_by != demoter_user_id:
            return False, "Only the group creator can demote admins"
        
        # Ensure there will still be at least one admin
        admin_count = self.group.get_admin_count()
        if admin_count <= 1:
            return False, "Cannot demote the last admin"
        
        return True, "Can demote from admin"
    
    def can_be_removed(self, remover_user_id):
        """Check if a user can be removed from the group"""
        remover_role = self.group.get_member_role(remover_user_id)
        
        # Group creator can remove anyone except themselves
        if self.group.created_by == remover_user_id:
            if self.user_id == remover_user_id:
                return False, "Group creator cannot leave the group (must delete it instead)"
            return True, "Creator can remove member"
        
        # Admins can remove non-admins
        if remover_role == 'admin' and self.role != 'admin':
            return True, "Admin can remove member/moderator"
        
        # Moderators can remove regular members
        if remover_role == 'moderator' and self.role == 'member':
            return True, "Moderator can remove member"
        
        # Users can remove themselves (leave group)
        if self.user_id == remover_user_id:
            return True, "User can leave group"
        
        return False, "Insufficient permissions to remove member"

# Content Management Models

class Platform(db.Model):
    """Platform model for streaming services"""
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    logo_url = db.Column(db.String(255), nullable=True)
    website_url = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    content_platforms = db.relationship('ContentPlatform', backref='platform_ref', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Platform {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'logo_url': self.logo_url,
            'website_url': self.website_url,
            'is_active': self.is_active
        }


class Content(db.Model):
    """Content model for movies, TV shows, etc."""
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(50), nullable=False, index=True)  # movie, tv_show, documentary, etc.
    genre = db.Column(db.String(255), nullable=True, index=True)  # JSON string of genres
    year = db.Column(db.Integer, nullable=True, index=True)
    rating = db.Column(db.Float, nullable=True, index=True)  # IMDb/TMDB rating
    duration = db.Column(db.Integer, nullable=True)  # duration in minutes
    poster_url = db.Column(db.String(500), nullable=True)
    backdrop_url = db.Column(db.String(500), nullable=True)
    trailer_url = db.Column(db.String(500), nullable=True)
    
    # External IDs
    tmdb_id = db.Column(db.Integer, nullable=True, unique=True, index=True)
    imdb_id = db.Column(db.String(20), nullable=True, index=True)
    
    # Additional metadata
    director = db.Column(db.String(255), nullable=True)
    cast = db.Column(db.Text, nullable=True)  # JSON string
    country = db.Column(db.String(100), nullable=True)
    language = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(50), default='active')  # active, inactive, coming_soon
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    content_platforms = db.relationship('ContentPlatform', backref='content_ref', lazy='dynamic', cascade='all, delete-orphan')
    user_watchlists = db.relationship('UserWatchlist', backref='content_ref', lazy='dynamic', cascade='all, delete-orphan')
    content_ratings = db.relationship('ContentRating', backref='content_ref', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Content {self.title} ({self.year})>'
    
    def get_genres(self):
        """Get genres as a list"""
        if self.genre:
            try:
                return json.loads(self.genre)
            except:
                return [self.genre]
        return []
    
    def set_genres(self, genres):
        """Set genres from a list"""
        if isinstance(genres, list):
            self.genre = json.dumps(genres)
        else:
            self.genre = genres
    
    def get_cast(self):
        """Get cast as a list"""
        if self.cast:
            try:
                return json.loads(self.cast)
            except:
                return []
        return []
    
    def set_cast(self, cast):
        """Set cast from a list"""
        if isinstance(cast, list):
            self.cast = json.dumps(cast)
        else:
            self.cast = cast
    
    def get_platforms(self):
        """Get all platforms where this content is available"""
        return [cp.platform_ref for cp in self.content_platforms if cp.platform_ref.is_active]
    
    def get_average_rating(self):
        """Get average user rating from statistics"""
        stats = self.rating_statistics
        return stats.average_rating if stats else None
    
    def get_rating_count(self):
        """Get total number of ratings"""
        stats = self.rating_statistics
        return stats.total_ratings if stats else 0
    
    def get_review_count(self):
        """Get total number of reviews"""
        stats = self.rating_statistics
        return stats.total_reviews if stats else 0
    
    def get_rating_distribution(self):
        """Get rating distribution"""
        stats = self.rating_statistics
        return stats.get_rating_distribution() if stats else {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    
    def update_rating_statistics(self):
        """Update or create rating statistics for this content"""
        from models import RatingStatistics
        stats = RatingStatistics.get_or_create_for_content(self.id)
        stats.update_statistics()
        db.session.commit()
        return stats
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'type': self.type,
            'genre': self.get_genres(),
            'year': self.year,
            'rating': self.rating,
            'duration': self.duration,
            'poster_url': self.poster_url,
            'backdrop_url': self.backdrop_url,
            'trailer_url': self.trailer_url,
            'director': self.director,
            'cast': self.get_cast(),
            'country': self.country,
            'language': self.language,
            'platforms': [p.name for p in self.get_platforms()],
            'user_rating': {
                'average': self.get_average_rating(),
                'total_ratings': self.get_rating_count(),
                'total_reviews': self.get_review_count(),
                'distribution': self.get_rating_distribution()
            }
        }


class ContentPlatform(db.Model):
    """Relationship model between Content and Platform"""
    
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    platform_id = db.Column(db.Integer, db.ForeignKey('platform.id'), nullable=False)
    url = db.Column(db.String(500), nullable=True)  # Direct link to content on platform
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate entries
    __table_args__ = (db.UniqueConstraint('content_id', 'platform_id', name='unique_content_platform'),)
    
    def __repr__(self):
        return f'<ContentPlatform {self.content_id}-{self.platform_id}>'


class UserWatchlist(db.Model):
    """Enhanced user's personal watchlist with priority and progress tracking"""
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    status = db.Column(db.String(50), default='want_to_watch')  # want_to_watch, watching, completed, on_hold, dropped
    priority = db.Column(db.String(20), default='medium')  # high, medium, low
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Progress tracking for TV series
    current_season = db.Column(db.Integer, nullable=True, default=1)
    current_episode = db.Column(db.Integer, nullable=True, default=1)
    total_episodes_watched = db.Column(db.Integer, nullable=True, default=0)
    
    # Personal notes and rating
    personal_notes = db.Column(db.Text, nullable=True)
    personal_rating = db.Column(db.Float, nullable=True)  # Personal rating (1-10)
    
    # Sharing settings
    is_public = db.Column(db.Boolean, default=True)  # Whether this entry is visible to friends
    
    # Relationships
    user = db.relationship('User', backref='watchlist_items')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'content_id', name='unique_user_content'),)
    
    def __repr__(self):
        return f'<UserWatchlist {self.user_id}-{self.content_id}: {self.status}>'
    
    def update_status(self, new_status):
        """Update watchlist status with automatic timestamp tracking"""
        old_status = self.status
        self.status = new_status
        
        if new_status == 'watching' and old_status == 'want_to_watch':
            self.started_at = datetime.utcnow()
        elif new_status == 'completed' and old_status in ['watching', 'want_to_watch']:
            self.completed_at = datetime.utcnow()
            if not self.started_at:
                self.started_at = datetime.utcnow()
    
    def update_progress(self, season=None, episode=None):
        """Update progress for TV series"""
        if season is not None:
            self.current_season = season
        if episode is not None:
            self.current_episode = episode
            # Auto-increment total episodes watched
            if self.total_episodes_watched is None:
                self.total_episodes_watched = 1
            else:
                self.total_episodes_watched += 1
        
        # Auto-update status if starting to watch
        if self.status == 'want_to_watch':
            self.update_status('watching')
    
    def get_progress_percentage(self):
        """Calculate progress percentage for TV series (if total episodes known)"""
        if self.content_ref.type != 'tv_show' or not self.total_episodes_watched:
            return None
        
        # This would require additional metadata about total episodes
        # For now, return a simple calculation based on episodes watched
        if self.total_episodes_watched > 0:
            return min(100, (self.total_episodes_watched / 20) * 100)  # Assuming avg 20 eps per season
        return 0
    
    def get_time_spent_watching(self):
        """Calculate estimated time spent watching (for completed content)"""
        if self.status == 'completed' and self.content_ref.duration:
            if self.content_ref.type == 'movie':
                return self.content_ref.duration
            elif self.content_ref.type == 'tv_show' and self.total_episodes_watched:
                avg_episode_duration = self.content_ref.duration or 45  # Default 45 min per episode
                return self.total_episodes_watched * avg_episode_duration
        return 0
    
    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content_ref.to_dict() if self.content_ref else None,
            'status': self.status,
            'priority': self.priority,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'current_season': self.current_season,
            'current_episode': self.current_episode,
            'total_episodes_watched': self.total_episodes_watched,
            'personal_notes': self.personal_notes,
            'personal_rating': self.personal_rating,
            'progress_percentage': self.get_progress_percentage(),
            'time_spent_watching': self.get_time_spent_watching(),
            'is_public': self.is_public
        }


class ContentRating(db.Model):
    """Enhanced user ratings and reviews for content"""
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    review_text = db.Column(db.Text, nullable=True)
    is_spoiler = db.Column(db.Boolean, default=False)
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Review metrics
    helpful_votes = db.Column(db.Integer, default=0)
    total_votes = db.Column(db.Integer, default=0)
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'content_id', name='unique_user_content_rating'),)
    
    # Relationships
    user = db.relationship('User', backref='ratings')
    content = db.relationship('Content', backref=db.backref('ratings', overlaps="content_ratings,content_ref"))
    review_votes = db.relationship('ReviewHelpfulnessVote', backref='rating_ref', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ContentRating {self.user.username}-{self.content.title}: {self.rating}/5>'
    
    def get_helpfulness_percentage(self):
        """Calculate helpfulness percentage"""
        if self.total_votes == 0:
            return 0
        return round((self.helpful_votes / self.total_votes) * 100, 1)
    
    def can_edit(self, current_user):
        """Check if current user can edit this rating"""
        return current_user.id == self.user_id
    
    def to_dict(self, include_user=True):
        """Convert rating to dictionary"""
        data = {
            'id': self.id,
            'content_id': self.content_id,
            'rating': self.rating,
            'review_text': self.review_text,
            'is_spoiler': self.is_spoiler,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'helpful_votes': self.helpful_votes,
            'total_votes': self.total_votes,
            'helpfulness_percentage': self.get_helpfulness_percentage()
        }
        
        if include_user:
            data['user'] = {
                'id': self.user.id,
                'username': self.user.username,
                'profile_picture': self.user.profile_picture,
                'full_name': self.user.get_full_name()
            }
        
        return data

class GroupWatchlist(db.Model):
    """Shared watchlist for groups"""
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    added_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), default='planned')  # planned, watching, completed
    priority = db.Column(db.String(20), default='medium')  # high, medium, low
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_for = db.Column(db.DateTime, nullable=True)  # When group plans to watch
    
    # Group viewing progress
    group_status = db.Column(db.String(50), default='not_started')  # not_started, in_progress, completed
    current_season = db.Column(db.Integer, nullable=True, default=1)
    current_episode = db.Column(db.Integer, nullable=True, default=1)
    
    # Voting and discussion
    upvotes = db.Column(db.Integer, default=0)
    downvotes = db.Column(db.Integer, default=0)
    description = db.Column(db.Text, nullable=True)  # Why this content was added
    
    # Relationships
    group = db.relationship('Group', backref='group_watchlist_items')
    content = db.relationship('Content', backref='group_watchlist_items')
    added_by_user = db.relationship('User', backref='added_group_content')
    votes = db.relationship('GroupWatchlistVote', backref='watchlist_item', cascade='all, delete-orphan')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('group_id', 'content_id', name='unique_group_content'),)
    
    def __repr__(self):
        return f'<GroupWatchlist {self.group_id}-{self.content_id}: {self.status}>'
    
    def get_vote_score(self):
        """Calculate net vote score"""
        return self.upvotes - self.downvotes
    
    def get_user_vote(self, user_id):
        """Get user's vote on this content"""
        vote = GroupWatchlistVote.query.filter_by(
            group_watchlist_id=self.id,
            user_id=user_id
        ).first()
        return vote.vote_type if vote else None
    
    def update_vote_counts(self):
        """Recalculate vote counts from actual votes"""
        votes = GroupWatchlistVote.query.filter_by(group_watchlist_id=self.id).all()
        self.upvotes = len([v for v in votes if v.vote_type == 'up'])
        self.downvotes = len([v for v in votes if v.vote_type == 'down'])
    
    def can_user_edit(self, user_id):
        """Check if user can edit this watchlist item"""
        if self.added_by == user_id:
            return True
        
        # Check group permissions
        member = GroupMember.query.filter_by(group_id=self.group_id, user_id=user_id).first()
        if member and member.role in ['admin', 'moderator']:
            return True
        
        return self.group.created_by == user_id
    
    def to_dict(self):
        return {
            'id': self.id,
            'group_id': self.group_id,
            'content': self.content.to_dict() if self.content else None,
            'added_by': {
                'id': self.added_by_user.id,
                'username': self.added_by_user.username,
                'full_name': self.added_by_user.get_full_name()
            },
            'status': self.status,
            'priority': self.priority,
            'added_at': self.added_at.isoformat(),
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'group_status': self.group_status,
            'current_season': self.current_season,
            'current_episode': self.current_episode,
            'upvotes': self.upvotes,
            'downvotes': self.downvotes,
            'vote_score': self.get_vote_score(),
            'description': self.description
        }


class GroupWatchlistVote(db.Model):
    """Votes on group watchlist items"""
    
    id = db.Column(db.Integer, primary_key=True)
    group_watchlist_id = db.Column(db.Integer, db.ForeignKey('group_watchlist.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vote_type = db.Column(db.String(10), nullable=False)  # 'up' or 'down'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint - one vote per user per item
    __table_args__ = (db.UniqueConstraint('group_watchlist_id', 'user_id', name='unique_user_vote'),)
    
    def __repr__(self):
        return f'<GroupWatchlistVote {self.user_id}: {self.vote_type}>'


class WatchlistShare(db.Model):
    """Sharing personal watchlists with friends"""
    
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shared_with_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    share_type = db.Column(db.String(20), default='view')  # view, edit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Optional: Share specific status categories
    shared_statuses = db.Column(db.String(255), nullable=True)  # JSON list of statuses to share
    
    # Relationships
    owner = db.relationship('User', foreign_keys=[owner_id], backref='shared_watchlists')
    shared_with = db.relationship('User', foreign_keys=[shared_with_id], backref='received_watchlist_shares')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('owner_id', 'shared_with_id', name='unique_watchlist_share'),)
    
    def set_shared_statuses(self, statuses):
        """Set the shared statuses from a list"""
        if statuses:
            self.shared_statuses = json.dumps(statuses)
        else:
            self.shared_statuses = None
    
    def get_shared_statuses(self):
        """Get the shared statuses as a list"""
        if self.shared_statuses:
            return json.loads(self.shared_statuses)
        return []
    
    def __repr__(self):
        return f'<WatchlistShare {self.owner_id} -> {self.shared_with_id}>'

class WatchSession(db.Model):
    """Track group watch sessions"""
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Session details
    session_name = db.Column(db.String(200), nullable=True)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    actual_start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='scheduled')  # scheduled, live, completed, cancelled
    
    # Viewing progress for session
    current_time = db.Column(db.Integer, default=0)  # Current playback time in seconds
    season_number = db.Column(db.Integer, nullable=True)
    episode_number = db.Column(db.Integer, nullable=True)
    
    # Session settings
    is_public = db.Column(db.Boolean, default=False)  # Whether non-members can join
    max_participants = db.Column(db.Integer, default=20)
    notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    group = db.relationship('Group', backref='watch_sessions')
    content = db.relationship('Content', backref='watch_sessions')
    host = db.relationship('User', backref='hosted_sessions')
    participants = db.relationship('WatchSessionParticipant', backref='session', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<WatchSession {self.session_name or self.content.title}>'


class WatchSessionParticipant(db.Model):
    """Track participants in watch sessions"""
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('watch_session.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Participation details
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    left_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Participant preferences
    notifications_enabled = db.Column(db.Boolean, default=True)
    
    # Relationships
    user = db.relationship('User', backref='session_participations')
    
    def __repr__(self):
        return f'<WatchSessionParticipant {self.user.username} in {self.session_id}>'

class GroupRating(db.Model):
    """Group consensus ratings for content"""
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    average_rating = db.Column(db.Float, nullable=True)
    total_ratings = db.Column(db.Integer, default=0)
    consensus_review = db.Column(db.Text, nullable=True)  # Optional group consensus review
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('group_id', 'content_id', name='unique_group_content_rating'),)
    
    # Relationships
    group = db.relationship('Group', backref='group_ratings')
    content = db.relationship('Content', backref='group_ratings')
    
    def __repr__(self):
        return f'<GroupRating {self.group.name}-{self.content.title}: {self.average_rating}/5>'
    
    def calculate_group_rating(self):
        """Calculate average rating from group members' individual ratings"""
        from sqlalchemy import and_
        
        # Get all group members
        member_ids = [member.user_id for member in self.group.members if member.status == 'active']
        
        # Get ratings from group members for this content
        member_ratings = ContentRating.query.filter(
            and_(
                ContentRating.content_id == self.content_id,
                ContentRating.user_id.in_(member_ids),
                ContentRating.is_public == True
            )
        ).all()
        
        if member_ratings:
            total_rating = sum(rating.rating for rating in member_ratings)
            self.average_rating = round(total_rating / len(member_ratings), 2)
            self.total_ratings = len(member_ratings)
        else:
            self.average_rating = None
            self.total_ratings = 0
        
        self.updated_at = datetime.utcnow()
        return self.average_rating
    
    def get_rating_distribution(self):
        """Get rating distribution for group members"""
        from sqlalchemy import and_
        
        member_ids = [member.user_id for member in self.group.members if member.status == 'active']
        member_ratings = ContentRating.query.filter(
            and_(
                ContentRating.content_id == self.content_id,
                ContentRating.user_id.in_(member_ids),
                ContentRating.is_public == True
            )
        ).all()
        
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for rating in member_ratings:
            distribution[rating.rating] += 1
        
        return distribution
    
    def to_dict(self):
        """Convert group rating to dictionary"""
        return {
            'id': self.id,
            'group_id': self.group_id,
            'content_id': self.content_id,
            'average_rating': self.average_rating,
            'total_ratings': self.total_ratings,
            'consensus_review': self.consensus_review,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'rating_distribution': self.get_rating_distribution(),
            'group': {
                'id': self.group.id,
                'name': self.group.name
            },
            'content': {
                'id': self.content.id,
                'title': self.content.title,
                'poster_url': self.content.poster_url
            }
        }


class ReviewHelpfulnessVote(db.Model):
    """Track helpfulness votes on reviews"""
    
    id = db.Column(db.Integer, primary_key=True)
    rating_id = db.Column(db.Integer, db.ForeignKey('content_rating.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_helpful = db.Column(db.Boolean, nullable=False)  # True for helpful, False for not helpful
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint - one vote per user per review
    __table_args__ = (db.UniqueConstraint('rating_id', 'user_id', name='unique_review_vote'),)
    
    def __repr__(self):
        return f'<ReviewHelpfulnessVote {self.user.username}-{self.rating_id}: {"helpful" if self.is_helpful else "not helpful"}>'
    
    def to_dict(self):
        """Convert vote to dictionary"""
        return {
            'id': self.id,
            'rating_id': self.rating_id,
            'user_id': self.user_id,
            'is_helpful': self.is_helpful,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RatingStatistics(db.Model):
    """Aggregated rating statistics for content"""
    
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False, unique=True)
    
    # Rating statistics
    average_rating = db.Column(db.Float, nullable=True)
    total_ratings = db.Column(db.Integer, default=0)
    total_reviews = db.Column(db.Integer, default=0)
    
    # Rating distribution
    rating_1_count = db.Column(db.Integer, default=0)
    rating_2_count = db.Column(db.Integer, default=0)
    rating_3_count = db.Column(db.Integer, default=0)
    rating_4_count = db.Column(db.Integer, default=0)
    rating_5_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    content = db.relationship('Content', backref=db.backref('rating_statistics', uselist=False))
    
    def __repr__(self):
        return f'<RatingStatistics {self.content.title}: {self.average_rating}/5 ({self.total_ratings} ratings)>'

# Discussion System Models

class Discussion(db.Model):
    """Discussion model for content and group discussions"""
    
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=True)  # For content discussions
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)  # For group discussions
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('discussion.id'), nullable=True)  # For threading
    
    message = db.Column(db.Text, nullable=False)
    has_spoilers = db.Column(db.Boolean, default=False)
    is_hidden = db.Column(db.Boolean, default=False)  # For moderation
    is_pinned = db.Column(db.Boolean, default=False)  # For important discussions
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    edited_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    content = db.relationship('Content', backref='discussions')
    group = db.relationship('Group', backref='discussions')
    user = db.relationship('User', backref='discussions')
    parent = db.relationship('Discussion', remote_side=[id], backref='replies')
    
    # Discussion interactions
    likes = db.relationship('DiscussionLike', backref='discussion', cascade='all, delete-orphan')
    reports = db.relationship('DiscussionReport', backref='discussion', cascade='all, delete-orphan')
    notifications = db.relationship('DiscussionNotification', backref='discussion', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Discussion {self.id}: {self.message[:50]}...>'
    
    def get_reply_count(self):
        """Get total number of replies (including nested)"""
        def count_recursive(discussion_id):
            direct_replies = Discussion.query.filter_by(parent_id=discussion_id, is_hidden=False).count()
            total = direct_replies
            for reply in Discussion.query.filter_by(parent_id=discussion_id, is_hidden=False).all():
                total += count_recursive(reply.id)
            return total
        
        return count_recursive(self.id)
    
    def get_like_count(self):
        """Get number of likes"""
        return len([like for like in self.likes if like.is_like])
    
    def get_dislike_count(self):
        """Get number of dislikes"""
        return len([like for like in self.likes if not like.is_like])
    
    def get_user_reaction(self, user_id):
        """Get user's reaction (like/dislike/none)"""
        like = DiscussionLike.query.filter_by(
            discussion_id=self.id,
            user_id=user_id
        ).first()
        if like:
            return 'like' if like.is_like else 'dislike'
        return None
    
    def is_reported_by_user(self, user_id):
        """Check if user has reported this discussion"""
        return DiscussionReport.query.filter_by(
            discussion_id=self.id,
            reporter_id=user_id
        ).first() is not None
    
    def get_thread_depth(self):
        """Get the depth of this discussion in the thread"""
        depth = 0
        current = self
        while current.parent_id:
            depth += 1
            current = current.parent
        return depth
    
    def can_user_edit(self, user_id):
        """Check if user can edit this discussion"""
        if self.user_id == user_id:
            return True
        
        # Check if user is group admin/moderator
        if self.group_id:
            member = GroupMember.query.filter_by(
                group_id=self.group_id,
                user_id=user_id
            ).first()
            return member and member.role in ['admin', 'moderator']
        
        return False
    
    def can_user_delete(self, user_id):
        """Check if user can delete this discussion"""
        return self.can_user_edit(user_id)
    
    def can_user_pin(self, user_id):
        """Check if user can pin this discussion"""
        if self.group_id:
            member = GroupMember.query.filter_by(
                group_id=self.group_id,
                user_id=user_id
            ).first()
            return member and member.role in ['admin', 'moderator']
        
        return False
    
    def get_formatted_message(self):
        """Get message with spoiler tags formatted"""
        if self.has_spoilers:
            return f"<span class='spoiler-warning'>⚠️ Contains Spoilers</span><br>{self.message}"
        return self.message
    
    def to_dict(self, include_replies=False, user_id=None):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'content_id': self.content_id,
            'group_id': self.group_id,
            'user': {
                'id': self.user.id,
                'username': self.user.username,
                'full_name': self.user.get_full_name(),
                'profile_picture': self.user.profile_picture
            },
            'parent_id': self.parent_id,
            'message': self.message,
            'has_spoilers': self.has_spoilers,
            'is_hidden': self.is_hidden,
            'is_pinned': self.is_pinned,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'like_count': self.get_like_count(),
            'dislike_count': self.get_dislike_count(),
            'reply_count': self.get_reply_count(),
            'thread_depth': self.get_thread_depth(),
            'user_reaction': self.get_user_reaction(user_id) if user_id else None,
            'is_reported': self.is_reported_by_user(user_id) if user_id else False,
            'can_edit': self.can_user_edit(user_id) if user_id else False,
            'can_delete': self.can_user_delete(user_id) if user_id else False,
            'can_pin': self.can_user_pin(user_id) if user_id else False
        }
        
        if include_replies:
            data['replies'] = [
                reply.to_dict(include_replies=True, user_id=user_id) 
                for reply in Discussion.query.filter_by(parent_id=self.id, is_hidden=False)
                .order_by(Discussion.created_at.asc()).all()
            ]
        
        return data


class DiscussionLike(db.Model):
    """Like/dislike tracking for discussions"""
    
    id = db.Column(db.Integer, primary_key=True)
    discussion_id = db.Column(db.Integer, db.ForeignKey('discussion.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_like = db.Column(db.Boolean, nullable=False)  # True for like, False for dislike
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='discussion_likes')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('discussion_id', 'user_id', name='unique_discussion_like'),)
    
    def __repr__(self):
        return f'<DiscussionLike {self.discussion_id}-{self.user_id}: {"like" if self.is_like else "dislike"}>'


class DiscussionReport(db.Model):
    """Report system for inappropriate discussions"""
    
    id = db.Column(db.Integer, primary_key=True)
    discussion_id = db.Column(db.Integer, db.ForeignKey('discussion.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.String(100), nullable=False)  # spam, inappropriate, spoilers, etc.
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, reviewed, resolved, dismissed
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    reporter = db.relationship('User', foreign_keys=[reporter_id], backref='reported_discussions')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='reviewed_reports')
    
    def __repr__(self):
        return f'<DiscussionReport {self.id}: {self.reason}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'discussion_id': self.discussion_id,
            'reporter': {
                'id': self.reporter.id,
                'username': self.reporter.username
            },
            'reason': self.reason,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewer': {
                'id': self.reviewer.id,
                'username': self.reviewer.username
            } if self.reviewer else None
        }


class DiscussionNotification(db.Model):
    """Notification system for discussion replies and mentions"""
    
    id = db.Column(db.Integer, primary_key=True)
    discussion_id = db.Column(db.Integer, db.ForeignKey('discussion.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # User to notify
    trigger_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # User who triggered notification
    notification_type = db.Column(db.String(50), nullable=False)  # reply, mention, like
    is_read = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='discussion_notifications')
    trigger_user = db.relationship('User', foreign_keys=[trigger_user_id], backref='triggered_notifications')
    
    def __repr__(self):
        return f'<DiscussionNotification {self.id}: {self.notification_type}>'
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = datetime.utcnow()
        db.session.commit()
    
    def get_message(self):
        """Get formatted notification message"""
        if self.notification_type == 'reply':
            return f"{self.trigger_user.get_full_name() or self.trigger_user.username} replied to your discussion"
        elif self.notification_type == 'mention':
            return f"{self.trigger_user.get_full_name() or self.trigger_user.username} mentioned you in a discussion"
        elif self.notification_type == 'like':
            return f"{self.trigger_user.get_full_name() or self.trigger_user.username} liked your discussion"
        return "New discussion activity"
    
    def to_dict(self):
        return {
            'id': self.id,
            'discussion_id': self.discussion_id,
            'user_id': self.user_id,
            'trigger_user': {
                'id': self.trigger_user.id,
                'username': self.trigger_user.username,
                'full_name': self.trigger_user.get_full_name(),
                'profile_picture': self.trigger_user.profile_picture
            },
            'notification_type': self.notification_type,
            'message': self.get_message(),
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'read_at': self.read_at.isoformat() if self.read_at else None
        }


class DiscussionSearch(db.Model):
    """Search index for discussions (simplified full-text search)"""
    
    id = db.Column(db.Integer, primary_key=True)
    discussion_id = db.Column(db.Integer, db.ForeignKey('discussion.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    search_text = db.Column(db.Text, nullable=False)  # Preprocessed searchable text
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    discussion = db.relationship('Discussion', backref=db.backref('search_index', uselist=False, cascade='all, delete-orphan'))
    content = db.relationship('Content', backref='discussion_searches')
    group = db.relationship('Group', backref='discussion_searches')
    
    def __repr__(self):
        return f'<DiscussionSearch {self.discussion_id}>'
    
    @staticmethod
    def create_or_update_for_discussion(discussion):
        """Create or update search index for a discussion"""
        search_entry = DiscussionSearch.query.filter_by(discussion_id=discussion.id).first()
        
        # Create searchable text
        search_text_parts = [discussion.message]
        if discussion.user:
            search_text_parts.append(discussion.user.username)
            search_text_parts.append(discussion.user.get_full_name() or '')
        
        search_text = ' '.join(search_text_parts).lower()
        
        if search_entry:
            search_entry.search_text = search_text
            search_entry.updated_at = datetime.utcnow()
        else:
            search_entry = DiscussionSearch(
                discussion_id=discussion.id,
                content_id=discussion.content_id,
                group_id=discussion.group_id,
                search_text=search_text
            )
            db.session.add(search_entry)
        
        db.session.commit()
        return search_entry
    
    @staticmethod
    def search_discussions(query, content_id=None, group_id=None, limit=50):
        """Search discussions by query"""
        search_query = DiscussionSearch.query
        
        if content_id:
            search_query = search_query.filter_by(content_id=content_id)
        if group_id:
            search_query = search_query.filter_by(group_id=group_id)
        
        # Simple text search (can be enhanced with full-text search later)
        search_terms = query.lower().split()
        for term in search_terms:
            search_query = search_query.filter(DiscussionSearch.search_text.like(f'%{term}%'))
        
        search_results = search_query.limit(limit).all()
        
        # Return the actual discussions
        discussion_ids = [result.discussion_id for result in search_results]
        return Discussion.query.filter(
            Discussion.id.in_(discussion_ids),
            Discussion.is_hidden == False
        ).order_by(Discussion.created_at.desc()).all()
