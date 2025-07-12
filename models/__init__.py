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

    def get_friendship_status_with(self, user):
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

    def get_friend_status_with(self, user):
        """Get friendship status with another user"""
        return Friendship.get_friend_status(self.id, user.id)

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
