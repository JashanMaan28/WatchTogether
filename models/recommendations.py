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
