from app import db
from datetime import datetime
import json
import hashlib


class UserPreferenceProfile(db.Model):
    """User preference profile for recommendations"""
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    # Genre preferences (weighted scores)
    genre_preferences = db.Column(db.Text, nullable=True)  # JSON: {genre: weight}
    
    # Content type preferences
    content_type_preferences = db.Column(db.Text, nullable=True)  # JSON: {type: weight}
    
    # Preference for ratings/years/duration
    preferred_rating_range = db.Column(db.String(20), default="3.0-5.0")  # "min-max"
    preferred_year_range = db.Column(db.String(20), default="2000-2025")  # "min-max"
    preferred_duration_range = db.Column(db.String(20), default="60-180")  # "min-max" in minutes
    
    # Language and country preferences
    preferred_languages = db.Column(db.Text, nullable=True)  # JSON: [languages]
    preferred_countries = db.Column(db.Text, nullable=True)  # JSON: [countries]
    
    # Viewing habits
    viewing_frequency = db.Column(db.String(20), default="regular")  # heavy, regular, light
    discovery_preference = db.Column(db.String(20), default="balanced")  # popular, niche, balanced
    
    # Social preferences
    social_weight = db.Column(db.Float, default=0.3)  # How much to weight social signals (0.0-1.0)
    enable_friend_recommendations = db.Column(db.Boolean, default=True)
    share_viewing_activity = db.Column(db.Boolean, default=True)
    enable_group_recommendations = db.Column(db.Boolean, default=True)
    
    # Profile metadata
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    confidence_score = db.Column(db.Float, default=0.0)  # How confident we are in this profile
    
    # Relationships
    user = db.relationship('User', backref=db.backref('preference_profile', uselist=False))
    
    def __repr__(self):
        return f'<UserPreferenceProfile {self.user.username}>'
    
    def get_genre_preferences(self):
        """Get genre preferences as dictionary"""
        if self.genre_preferences:
            try:
                return json.loads(self.genre_preferences)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_genre_preferences(self, preferences):
        """Set genre preferences from dictionary"""
        if preferences:
            self.genre_preferences = json.dumps(preferences)
        else:
            self.genre_preferences = None
    
    def get_content_type_preferences(self):
        """Get content type preferences as dictionary"""
        if self.content_type_preferences:
            try:
                return json.loads(self.content_type_preferences)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_content_type_preferences(self, preferences):
        """Set content type preferences from dictionary"""
        if preferences:
            self.content_type_preferences = json.dumps(preferences)
        else:
            self.content_type_preferences = None
    
    def get_preferred_languages(self):
        """Get preferred languages as list"""
        if self.preferred_languages:
            try:
                return json.loads(self.preferred_languages)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_preferred_languages(self, languages):
        """Set preferred languages from list"""
        if languages:
            self.preferred_languages = json.dumps(languages)
        else:
            self.preferred_languages = None
    
    def get_preferred_countries(self):
        """Get preferred countries as list"""
        if self.preferred_countries:
            try:
                return json.loads(self.preferred_countries)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_preferred_countries(self, countries):
        """Set preferred countries from list"""
        if countries:
            self.preferred_countries = json.dumps(countries)
        else:
            self.preferred_countries = None
    
    def get_rating_range(self):
        """Get preferred rating range as tuple"""
        try:
            min_rating, max_rating = self.preferred_rating_range.split('-')
            return float(min_rating), float(max_rating)
        except:
            return 3.0, 5.0
    
    def get_year_range(self):
        """Get preferred year range as tuple"""
        try:
            min_year, max_year = self.preferred_year_range.split('-')
            return int(min_year), int(max_year)
        except:
            return 2000, 2025
    
    def get_duration_range(self):
        """Get preferred duration range as tuple"""
        try:
            min_duration, max_duration = self.preferred_duration_range.split('-')
            return int(min_duration), int(max_duration)
        except:
            return 60, 180


class GroupPreferenceProfile(db.Model):
    """Aggregated preference profile for groups"""
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False, unique=True)
    
    # Aggregated preferences from group members
    genre_preferences = db.Column(db.Text, nullable=True)  # JSON: {genre: weight}
    content_type_preferences = db.Column(db.Text, nullable=True)  # JSON: {type: weight}
    
    # Group consensus preferences
    preferred_rating_range = db.Column(db.String(20), default="3.0-5.0")
    preferred_year_range = db.Column(db.String(20), default="2000-2025")
    preferred_duration_range = db.Column(db.String(20), default="60-180")
    
    # Group viewing patterns
    consensus_threshold = db.Column(db.Float, default=0.6)  # What % agreement needed
    diversity_factor = db.Column(db.Float, default=0.3)  # How much to favor diverse content
    
    # Profile metadata
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    member_count = db.Column(db.Integer, default=0)
    confidence_score = db.Column(db.Float, default=0.0)
    
    # Relationships
    group = db.relationship('Group', backref=db.backref('preference_profile', uselist=False))
    
    def __repr__(self):
        return f'<GroupPreferenceProfile {self.group.name}>'
    
    def get_genre_preferences(self):
        """Get genre preferences as dictionary"""
        if self.genre_preferences:
            try:
                return json.loads(self.genre_preferences)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_genre_preferences(self, preferences):
        """Set genre preferences from dictionary"""
        if preferences:
            self.genre_preferences = json.dumps(preferences)
        else:
            self.genre_preferences = None
    
    def get_content_type_preferences(self):
        """Get content type preferences as dictionary"""
        if self.content_type_preferences:
            try:
                return json.loads(self.content_type_preferences)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_content_type_preferences(self, preferences):
        """Set content type preferences from dictionary"""
        if preferences:
            self.content_type_preferences = json.dumps(preferences)
        else:
            self.content_type_preferences = None


class Recommendation(db.Model):
    """Individual recommendations for users or groups"""
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    
    # Recommendation metadata
    score = db.Column(db.Float, nullable=False)  # Recommendation confidence score
    algorithm = db.Column(db.String(50), nullable=False)  # Which algorithm generated this
    reasoning = db.Column(db.Text, nullable=True)  # Human-readable explanation
    
    # A/B Testing
    experiment_id = db.Column(db.String(50), nullable=True)
    variant = db.Column(db.String(20), nullable=True)  # A, B, etc.
    
    # Recommendation state
    status = db.Column(db.String(20), default='active')  # active, dismissed, interacted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # User interaction tracking
    viewed_at = db.Column(db.DateTime, nullable=True)
    clicked_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='recommendations')
    group = db.relationship('Group', backref='recommendations')
    content = db.relationship('Content', backref='recommendations')
    feedback = db.relationship('RecommendationFeedback', backref='recommendation', cascade='all, delete-orphan')
    
    def __repr__(self):
        target = self.user.username if self.user else self.group.name
        return f'<Recommendation {target}: {self.content.title} ({self.score:.2f})>'
    
    def mark_viewed(self):
        """Mark recommendation as viewed"""
        if not self.viewed_at:
            self.viewed_at = datetime.utcnow()
    
    def mark_clicked(self):
        """Mark recommendation as clicked"""
        if not self.clicked_at:
            self.clicked_at = datetime.utcnow()
        self.mark_viewed()
    
    def get_feedback_summary(self):
        """Get aggregated feedback for this recommendation"""
        likes = sum(1 for f in self.feedback if f.feedback_type == 'like')
        dislikes = sum(1 for f in self.feedback if f.feedback_type == 'dislike')
        total = likes + dislikes
        
        return {
            'likes': likes,
            'dislikes': dislikes,
            'total': total,
            'like_ratio': likes / total if total > 0 else 0
        }
    
    def to_dict(self):
        """Convert recommendation to dictionary"""
        return {
            'id': self.id,
            'content': self.content.to_dict(),
            'score': self.score,
            'algorithm': self.algorithm,
            'reasoning': self.reasoning,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'feedback': self.get_feedback_summary()
        }


class RecommendationFeedback(db.Model):
    """User feedback on recommendations"""
    
    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(db.Integer, db.ForeignKey('recommendation.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    feedback_type = db.Column(db.String(20), nullable=False)  # like, dislike, not_interested, already_seen
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate feedback
    __table_args__ = (db.UniqueConstraint('recommendation_id', 'user_id', name='unique_user_recommendation_feedback'),)
    
    # Relationships
    user = db.relationship('User', backref='recommendation_feedback')
    
    def __repr__(self):
        return f'<RecommendationFeedback {self.user.username}: {self.feedback_type}>'


class RecommendationHistory(db.Model):
    """Track recommendation history and performance"""
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    
    # Batch information
    generation_date = db.Column(db.DateTime, default=datetime.utcnow)
    algorithm = db.Column(db.String(50), nullable=False)
    total_recommendations = db.Column(db.Integer, default=0)
    
    # Performance metrics
    view_rate = db.Column(db.Float, default=0.0)  # % of recommendations viewed
    click_rate = db.Column(db.Float, default=0.0)  # % of recommendations clicked
    like_rate = db.Column(db.Float, default=0.0)  # % of recommendations liked
    conversion_rate = db.Column(db.Float, default=0.0)  # % that led to watchlist adds
    
    # A/B Testing
    experiment_id = db.Column(db.String(50), nullable=True)
    variant = db.Column(db.String(20), nullable=True)
    
    # Metadata
    parameters = db.Column(db.Text, nullable=True)  # JSON of algorithm parameters
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='recommendation_history')
    group = db.relationship('Group', backref='recommendation_history')
    
    def __repr__(self):
        target = self.user.username if self.user else self.group.name
        return f'<RecommendationHistory {target}: {self.algorithm} ({self.generation_date})>'
    
    def get_parameters(self):
        """Get parameters as dictionary"""
        if self.parameters:
            try:
                return json.loads(self.parameters)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_parameters(self, params):
        """Set parameters from dictionary"""
        if params:
            self.parameters = json.dumps(params)
        else:
            self.parameters = None


class ABTestExperiment(db.Model):
    """A/B testing experiments for recommendations"""
    
    id = db.Column(db.Integer, primary_key=True)
    experiment_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Experiment configuration
    variants = db.Column(db.Text, nullable=False)  # JSON: {variant: {config}}
    traffic_split = db.Column(db.Text, nullable=False)  # JSON: {variant: percentage}
    
    # Experiment status
    status = db.Column(db.String(20), default='draft')  # draft, running, paused, completed
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    
    # Target criteria
    target_users = db.Column(db.Text, nullable=True)  # JSON: criteria for user selection
    target_groups = db.Column(db.Text, nullable=True)  # JSON: criteria for group selection
    
    # Success metrics
    primary_metric = db.Column(db.String(50), default='click_rate')
    secondary_metrics = db.Column(db.Text, nullable=True)  # JSON: [metrics]
    
    # Results
    results = db.Column(db.Text, nullable=True)  # JSON: experiment results
    winner = db.Column(db.String(20), nullable=True)  # Winning variant
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', backref='created_experiments')
    
    def __repr__(self):
        return f'<ABTestExperiment {self.name}: {self.status}>'
    
    def get_variants(self):
        """Get variants as dictionary"""
        if self.variants:
            try:
                return json.loads(self.variants)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_traffic_split(self):
        """Get traffic split as dictionary"""
        if self.traffic_split:
            try:
                return json.loads(self.traffic_split)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_results(self):
        """Get results as dictionary"""
        if self.results:
            try:
                return json.loads(self.results)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def assign_variant(self, user_id):
        """Assign a variant to a user based on traffic split"""
        # Use consistent hashing to assign users to variants
        hash_input = f"{self.experiment_id}_{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        percentage = hash_value % 100
        
        traffic_split = self.get_traffic_split()
        cumulative = 0
        for variant, split in traffic_split.items():
            cumulative += split
            if percentage < cumulative:
                return variant
        
        # Default to first variant if something goes wrong
        return list(traffic_split.keys())[0] if traffic_split else 'A'


class SocialRecommendationSignal(db.Model):
    """Track social signals for recommendations"""
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    
    # Social signal types
    signal_type = db.Column(db.String(50), nullable=False)  # friend_liked, friend_watched, trending, shared
    signal_strength = db.Column(db.Float, default=1.0)  # Weight of this signal
    
    # Source information
    source_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # User who generated the signal
    source_group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)  # Group context
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    context_data = db.Column(db.Text, nullable=True)  # JSON: Additional context
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='received_social_signals')
    source_user = db.relationship('User', foreign_keys=[source_user_id], backref='generated_social_signals')
    content = db.relationship('Content', backref='social_signals')
    source_group = db.relationship('Group', backref='social_signals')
    
    def __repr__(self):
        return f'<SocialSignal {self.signal_type}: {self.user.username} -> {self.content.title}>'
    
    def get_context_data(self):
        """Get context data as dictionary"""
        if self.context_data:
            try:
                return json.loads(self.context_data)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_context_data(self, data):
        """Set context data from dictionary"""
        if data:
            self.context_data = json.dumps(data)
        else:
            self.context_data = None


class FriendRecommendation(db.Model):
    """Recommendations shared between friends"""
    
    id = db.Column(db.Integer, primary_key=True)
    recommender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    
    # Recommendation details
    message = db.Column(db.Text, nullable=True)
    rating = db.Column(db.Float, nullable=True)  # Recommender's rating
    tags = db.Column(db.Text, nullable=True)  # JSON: List of tags
    
    # Status tracking
    status = db.Column(db.String(20), default='sent')  # sent, viewed, liked, dismissed, watched
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    viewed_at = db.Column(db.DateTime, nullable=True)
    responded_at = db.Column(db.DateTime, nullable=True)
    
    # Response
    friend_rating = db.Column(db.Float, nullable=True)
    friend_comment = db.Column(db.Text, nullable=True)
    
    # Relationships
    recommender = db.relationship('User', foreign_keys=[recommender_id], backref='sent_friend_recommendations')
    friend = db.relationship('User', foreign_keys=[friend_id], backref='received_friend_recommendations')
    content = db.relationship('Content', backref='friend_recommendations')
    
    def __repr__(self):
        return f'<FriendRecommendation {self.recommender.username} -> {self.friend.username}: {self.content.title}>'
    
    def get_tags(self):
        """Get tags as list"""
        if self.tags:
            try:
                return json.loads(self.tags)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_tags(self, tags_list):
        """Set tags from list"""
        if tags_list:
            self.tags = json.dumps(tags_list)
        else:
            self.tags = None
    
    def mark_viewed(self):
        """Mark recommendation as viewed"""
        if not self.viewed_at:
            self.viewed_at = datetime.utcnow()
            if self.status == 'sent':
                self.status = 'viewed'
    
    def respond(self, rating=None, comment=None, liked=False):
        """Friend responds to recommendation"""
        self.responded_at = datetime.utcnow()
        if rating:
            self.friend_rating = rating
        if comment:
            self.friend_comment = comment
        
        if liked:
            self.status = 'liked'
        elif self.status == 'viewed':
            self.status = 'responded'


class GroupRecommendationSession(db.Model):
    """Group recommendation sessions for collaborative discovery"""
    __tablename__ = 'group_recommendation_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Session details
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    session_type = db.Column(db.String(50), default='collaborative')  # collaborative, voting, tournament
    
    # Settings
    max_participants = db.Column(db.Integer, default=None)
    voting_duration = db.Column(db.Integer, default=24)  # hours
    require_consensus = db.Column(db.Boolean, default=False)
    min_consensus_percentage = db.Column(db.Float, default=0.6)
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, voting, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    voting_starts_at = db.Column(db.DateTime, nullable=True)
    voting_ends_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Results
    winning_content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=True)
    final_recommendations = db.Column(db.Text, nullable=True)  # JSON: List of content IDs with scores
    
    # Relationships
    group = db.relationship('Group', backref='recommendation_sessions')
    host = db.relationship('User', backref='hosted_recommendation_sessions')
    winning_content = db.relationship('Content', backref='won_recommendation_sessions')
    
    def __repr__(self):
        return f'<GroupRecommendationSession {self.title}: {self.group.name}>'
    
    def get_final_recommendations(self):
        """Get final recommendations as list"""
        if self.final_recommendations:
            try:
                return json.loads(self.final_recommendations)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_final_recommendations(self, recommendations):
        """Set final recommendations from list"""
        if recommendations:
            self.final_recommendations = json.dumps(recommendations)
        else:
            self.final_recommendations = None


class GroupRecommendationItem(db.Model):
    """Individual content items in a group recommendation session"""
    __tablename__ = 'group_recommendation_items'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('group_recommendation_sessions.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    suggested_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    session = db.relationship('GroupRecommendationSession', backref='items')
    content = db.relationship('Content')
    suggester = db.relationship('User')
    
    def __repr__(self):
        return f'<GroupRecommendationItem {self.id}: {self.content_id} in session {self.session_id}>'


class GroupRecommendationVote(db.Model):
    """Votes in group recommendation sessions"""
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('group_recommendation_sessions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    
    # Vote details
    vote_type = db.Column(db.String(20), default='preference')  # preference, veto, must_watch
    score = db.Column(db.Float, default=1.0)  # Vote strength
    comment = db.Column(db.Text, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session = db.relationship('GroupRecommendationSession', backref='votes')
    user = db.relationship('User', backref='group_recommendation_votes')
    content = db.relationship('Content', backref='group_recommendation_votes')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('session_id', 'user_id', 'content_id', name='unique_session_user_content_vote'),)
    
    def __repr__(self):
        return f'<GroupRecommendationVote {self.user.username}: {self.content.title} ({self.score})>'


class TrendingContent(db.Model):
    """Track trending content within social circles"""
    
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    
    # Trending metrics
    scope = db.Column(db.String(20), default='global')  # global, friends, group
    scope_id = db.Column(db.Integer, nullable=True)  # group_id for group scope
    
    # Trend scores
    trending_score = db.Column(db.Float, default=0.0)
    view_velocity = db.Column(db.Float, default=0.0)  # Views per hour
    rating_velocity = db.Column(db.Float, default=0.0)  # Ratings per hour
    social_velocity = db.Column(db.Float, default=0.0)  # Social interactions per hour
    
    # Time period
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Additional metrics
    unique_viewers = db.Column(db.Integer, default=0)
    total_ratings = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0.0)
    social_mentions = db.Column(db.Integer, default=0)
    
    # Relationships
    content = db.relationship('Content', backref='trending_periods')
    
    def __repr__(self):
        return f'<TrendingContent {self.content.title}: {self.scope} ({self.trending_score:.2f})>'


class RecommendationShare(db.Model):
    """Track shared recommendations and their performance"""
    
    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(db.Integer, db.ForeignKey('recommendation.id'), nullable=False)
    sharer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Share details
    share_type = db.Column(db.String(20), default='direct')  # direct, group, public
    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    target_group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    
    message = db.Column(db.Text, nullable=True)
    custom_tags = db.Column(db.Text, nullable=True)  # JSON: Additional tags
    
    # Status and metrics
    status = db.Column(db.String(20), default='active')  # active, viewed, interacted, expired
    view_count = db.Column(db.Integer, default=0)
    click_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    first_viewed_at = db.Column(db.DateTime, nullable=True)
    last_interacted_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    recommendation = db.relationship('Recommendation', backref='shares')
    sharer = db.relationship('User', foreign_keys=[sharer_id], backref='shared_recommendations')
    target_user = db.relationship('User', foreign_keys=[target_user_id], backref='received_recommendation_shares')
    target_group = db.relationship('Group', backref='received_recommendation_shares')
    
    def __repr__(self):
        return f'<RecommendationShare {self.sharer.username}: {self.recommendation.content.title}>'
    
    def get_custom_tags(self):
        """Get custom tags as list"""
        if self.custom_tags:
            try:
                return json.loads(self.custom_tags)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_custom_tags(self, tags_list):
        """Set custom tags from list"""
        if tags_list:
            self.custom_tags = json.dumps(tags_list)
        else:
            self.custom_tags = None
    
    def increment_view(self):
        """Increment view count"""
        self.view_count += 1
        if not self.first_viewed_at:
            self.first_viewed_at = datetime.utcnow()
            self.status = 'viewed'
    
    def increment_click(self):
        """Increment click count"""
        self.click_count += 1
        self.last_interacted_at = datetime.utcnow()
        if self.status in ['active', 'viewed']:
            self.status = 'interacted'
    
    def increment_like(self):
        """Increment like count"""
        self.like_count += 1
        self.last_interacted_at = datetime.utcnow()
        if self.status in ['active', 'viewed']:
            self.status = 'interacted'


class SocialRecommendationInsight(db.Model):
    """Analytics insights for social recommendations"""
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    
    # Insight type and scope
    insight_type = db.Column(db.String(50), nullable=False)  # friend_influence, group_consensus, trending_alert
    scope = db.Column(db.String(20), default='user')  # user, group, global
    
    # Insight data
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    insight_data = db.Column(db.Text, nullable=True)  # JSON: Detailed insight data
    
    # Importance and relevance
    importance_score = db.Column(db.Float, default=0.5)
    relevance_score = db.Column(db.Float, default=0.5)
    confidence_score = db.Column(db.Float, default=0.5)
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, dismissed, archived
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # User interaction
    viewed_at = db.Column(db.DateTime, nullable=True)
    dismissed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='recommendation_insights')
    group = db.relationship('Group', backref='recommendation_insights')
    
    def __repr__(self):
        target = self.user.username if self.user else self.group.name
        return f'<SocialRecommendationInsight {self.insight_type}: {target}>'
    
    def get_insight_data(self):
        """Get insight data as dictionary"""
        if self.insight_data:
            try:
                return json.loads(self.insight_data)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_insight_data(self, data):
        """Set insight data from dictionary"""
        if data:
            self.insight_data = json.dumps(data)
        else:
            self.insight_data = None
    
    def mark_viewed(self):
        """Mark insight as viewed"""
        if not self.viewed_at:
            self.viewed_at = datetime.utcnow()
    
    def dismiss(self):
        """Dismiss insight"""
        self.dismissed_at = datetime.utcnow()
        self.status = 'dismissed'
