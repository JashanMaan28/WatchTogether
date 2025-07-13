"""
Configuration settings for the recommendation system
All configurable parameters in one place for easy management
"""

import os
from datetime import timedelta


class RecommendationConfig:
    """Configuration class for recommendation system settings"""
    
    # Algorithm weights for hybrid recommendations
    ALGORITHM_WEIGHTS = {
        'content_based': 0.4,
        'collaborative': 0.3,
        'trending': 0.2,
        'group_consensus': 0.1
    }
    
    # Default recommendation limits
    DEFAULT_RECOMMENDATION_LIMIT = 10
    MAX_RECOMMENDATION_LIMIT = 50
    MIN_RECOMMENDATION_LIMIT = 1
    
    # Content-based filtering settings
    CONTENT_BASED = {
        'min_similarity_threshold': 0.1,
        'genre_weight': 0.4,
        'rating_weight': 0.3,
        'popularity_weight': 0.2,
        'recency_weight': 0.1,
        'max_recommendations_per_genre': 3
    }
    
    # Collaborative filtering settings
    COLLABORATIVE_FILTERING = {
        'min_similarity_threshold': 0.2,
        'min_common_ratings': 3,
        'max_similar_users': 100,
        'similarity_decay_factor': 0.1
    }
    
    # Trending content settings
    TRENDING = {
        'trending_window_days': 30,
        'min_ratings_for_trending': 10,
        'recency_boost_factor': 1.5,
        'popularity_threshold': 0.6
    }
    
    # Group consensus settings
    GROUP_CONSENSUS = {
        'min_group_size': 2,
        'consensus_threshold': 0.7,
        'member_rating_weight': 0.8,
        'admin_rating_weight': 1.2
    }
    
    # User preference profile settings
    USER_PROFILE = {
        'min_ratings_for_profile': 5,
        'profile_update_frequency_days': 3,
        'rating_recency_decay': 0.9,
        'watchlist_weight': 0.3,
        'rating_weight': 0.7
    }
    
    # Group preference profile settings
    GROUP_PROFILE = {
        'min_members_for_profile': 2,
        'profile_update_frequency_days': 7,
        'member_consensus_threshold': 0.6,
        'admin_preference_weight': 1.5
    }
    
    # Recommendation scoring settings
    SCORING = {
        'base_score_range': (0.0, 10.0),
        'diversity_bonus': 0.5,
        'freshness_bonus': 0.3,
        'popularity_penalty': 0.1,
        'already_rated_penalty': 5.0,
        'in_watchlist_bonus': 1.0
    }
    
    # Recommendation expiration settings
    EXPIRATION = {
        'default_expiration_days': 30,
        'trending_expiration_days': 7,
        'group_consensus_expiration_days': 14,
        'personal_expiration_days': 21
    }
    
    # A/B Testing settings
    AB_TESTING = {
        'default_experiment_duration_days': 14,
        'min_sample_size': 100,
        'statistical_significance_threshold': 0.05,
        'max_concurrent_experiments': 3,
        'hash_salt': os.environ.get('AB_TEST_SALT', 'watchtogether_ab_salt')
    }
    
    # Performance metrics settings
    METRICS = {
        'metrics_update_frequency_hours': 6,
        'metrics_retention_days': 90,
        'performance_threshold': {
            'click_rate': 0.1,
            'like_rate': 0.3,
            'view_rate': 0.5
        }
    }
    
    # Caching settings
    CACHING = {
        'enable_recommendation_cache': True,
        'cache_expiration_hours': 6,
        'cache_size_limit': 1000,
        'cache_user_profiles': True,
        'cache_group_profiles': True
    }
    
    # Database settings
    DATABASE = {
        'batch_size': 100,
        'query_timeout_seconds': 30,
        'max_recommendations_per_user': 100,
        'cleanup_frequency_days': 7
    }
    
    # Content filtering settings
    CONTENT_FILTERING = {
        'exclude_adult_content': True,
        'min_content_rating': 0.0,
        'max_content_age_years': None,
        'preferred_languages': ['en'],
        'exclude_genres': []
    }
    
    # Notification settings
    NOTIFICATIONS = {
        'send_recommendation_notifications': True,
        'max_notifications_per_day': 3,
        'notification_delay_hours': 2,
        'batch_notification_size': 10
    }
    
    # Logging settings
    LOGGING = {
        'log_level': 'INFO',
        'log_file_path': 'logs/recommendations.log',
        'max_log_file_size_mb': 10,
        'log_rotation_count': 5,
        'log_performance_metrics': True
    }
    
    # Feature flags
    FEATURE_FLAGS = {
        'enable_collaborative_filtering': True,
        'enable_content_based_filtering': True,
        'enable_trending_recommendations': True,
        'enable_group_recommendations': True,
        'enable_ab_testing': True,
        'enable_recommendation_explanations': True,
        'enable_feedback_system': True,
        'enable_recommendation_history': True,
        'enable_performance_metrics': True
    }
    
    # External API settings
    EXTERNAL_APIS = {
        'tmdb_api_timeout': 10,
        'cache_api_responses': True,
        'api_rate_limit_per_minute': 40
    }
    
    # Security settings
    SECURITY = {
        'validate_user_permissions': True,
        'log_recommendation_access': True,
        'anonymize_metrics_data': True,
        'encrypt_preference_data': False
    }
    
    @classmethod
    def get_algorithm_weight(cls, algorithm_name):
        """Get the weight for a specific algorithm"""
        return cls.ALGORITHM_WEIGHTS.get(algorithm_name, 0.0)
    
    @classmethod
    def get_expiration_days(cls, recommendation_type):
        """Get expiration days for a recommendation type"""
        expiration_map = {
            'trending': cls.EXPIRATION['trending_expiration_days'],
            'group_consensus': cls.EXPIRATION['group_consensus_expiration_days'],
            'personal': cls.EXPIRATION['personal_expiration_days']
        }
        return expiration_map.get(recommendation_type, cls.EXPIRATION['default_expiration_days'])
    
    @classmethod
    def is_feature_enabled(cls, feature_name):
        """Check if a feature is enabled"""
        return cls.FEATURE_FLAGS.get(feature_name, False)
    
    @classmethod
    def get_performance_threshold(cls, metric_name):
        """Get performance threshold for a metric"""
        return cls.METRICS['performance_threshold'].get(metric_name, 0.0)
    
    @classmethod
    def should_send_notifications(cls):
        """Check if notifications should be sent"""
        return cls.NOTIFICATIONS['send_recommendation_notifications']
    
    @classmethod
    def get_cache_expiration(cls):
        """Get cache expiration time"""
        return timedelta(hours=cls.CACHING['cache_expiration_hours'])
    
    @classmethod
    def get_ab_test_duration(cls):
        """Get default A/B test duration"""
        return timedelta(days=cls.AB_TESTING['default_experiment_duration_days'])
    
    @classmethod
    def update_config(cls, section, key, value):
        """Update a configuration value dynamically"""
        if hasattr(cls, section):
            section_dict = getattr(cls, section)
            if isinstance(section_dict, dict) and key in section_dict:
                section_dict[key] = value
                return True
        return False
    
    @classmethod
    def get_config_summary(cls):
        """Get a summary of current configuration"""
        return {
            'algorithm_weights': cls.ALGORITHM_WEIGHTS,
            'feature_flags': cls.FEATURE_FLAGS,
            'performance_thresholds': cls.METRICS['performance_threshold'],
            'expiration_settings': cls.EXPIRATION,
            'ab_testing_enabled': cls.is_feature_enabled('enable_ab_testing'),
            'caching_enabled': cls.CACHING['enable_recommendation_cache']
        }


# Environment-specific configuration overrides
class DevelopmentConfig(RecommendationConfig):
    """Development environment configuration"""
    
    FEATURE_FLAGS = RecommendationConfig.FEATURE_FLAGS.copy()
    FEATURE_FLAGS.update({
        'enable_ab_testing': False,  # Disable A/B testing in development
        'enable_recommendation_explanations': True
    })
    
    CACHING = RecommendationConfig.CACHING.copy()
    CACHING.update({
        'cache_expiration_hours': 1,  # Shorter cache in development
        'cache_size_limit': 100
    })
    
    LOGGING = RecommendationConfig.LOGGING.copy()
    LOGGING.update({
        'log_level': 'DEBUG',
        'log_performance_metrics': True
    })


class ProductionConfig(RecommendationConfig):
    """Production environment configuration"""
    
    FEATURE_FLAGS = RecommendationConfig.FEATURE_FLAGS.copy()
    FEATURE_FLAGS.update({
        'enable_ab_testing': True,
        'enable_performance_metrics': True
    })
    
    SECURITY = RecommendationConfig.SECURITY.copy()
    SECURITY.update({
        'validate_user_permissions': True,
        'log_recommendation_access': True,
        'anonymize_metrics_data': True
    })
    
    CACHING = RecommendationConfig.CACHING.copy()
    CACHING.update({
        'cache_expiration_hours': 12,
        'cache_size_limit': 5000
    })


class TestingConfig(RecommendationConfig):
    """Testing environment configuration"""
    
    FEATURE_FLAGS = RecommendationConfig.FEATURE_FLAGS.copy()
    FEATURE_FLAGS.update({
        'enable_ab_testing': False,
        'enable_recommendation_explanations': False
    })
    
    DATABASE = RecommendationConfig.DATABASE.copy()
    DATABASE.update({
        'batch_size': 10,
        'max_recommendations_per_user': 10
    })
    
    EXPIRATION = RecommendationConfig.EXPIRATION.copy()
    EXPIRATION.update({
        'default_expiration_days': 1,
        'trending_expiration_days': 1
    })


# Configuration factory
def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development').lower()
    
    if env == 'production':
        return ProductionConfig
    elif env == 'testing':
        return TestingConfig
    else:
        return DevelopmentConfig


# Export the active configuration
Config = get_config()
