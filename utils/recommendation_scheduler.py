"""
Scheduled tasks for the recommendation system
Handles periodic updates, maintenance, and optimization
"""

from datetime import datetime, timedelta
from app import create_app, db
from models import User, Group
from models.recommendations import (
    UserPreferenceProfile, GroupPreferenceProfile, Recommendation,
    RecommendationHistory, ABTestExperiment
)
from utils.recommendation_engine import RecommendationEngine, update_recommendation_metrics
import logging


def setup_logging():
    """Setup logging for scheduled tasks"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/recommendations.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('recommendations.scheduler')


def daily_profile_updates():
    """Daily task: Update user and group preference profiles"""
    logger = setup_logging()
    app = create_app()
    engine = RecommendationEngine()
    
    with app.app_context():
        logger.info("Starting daily profile updates")
        
        # Update stale user profiles (older than 3 days)
        cutoff_date = datetime.utcnow() - timedelta(days=3)
        stale_profiles = UserPreferenceProfile.query.filter(
            UserPreferenceProfile.last_updated < cutoff_date
        ).all()
        
        updated_users = 0
        for profile in stale_profiles:
            try:
                engine._analyze_user_preferences(profile)
                updated_users += 1
            except Exception as e:
                logger.error(f"Error updating user profile {profile.user_id}: {str(e)}")
        
        # Update stale group profiles (older than 1 week)
        group_cutoff = datetime.utcnow() - timedelta(days=7)
        stale_group_profiles = GroupPreferenceProfile.query.filter(
            GroupPreferenceProfile.last_updated < group_cutoff
        ).all()
        
        updated_groups = 0
        for profile in stale_group_profiles:
            try:
                engine._analyze_group_preferences(profile)
                updated_groups += 1
            except Exception as e:
                logger.error(f"Error updating group profile {profile.group_id}: {str(e)}")
        
        db.session.commit()
        logger.info(f"Updated {updated_users} user profiles and {updated_groups} group profiles")


def weekly_recommendation_generation():
    """Weekly task: Generate fresh recommendations for active users"""
    logger = setup_logging()
    app = create_app()
    engine = RecommendationEngine()
    
    with app.app_context():
        logger.info("Starting weekly recommendation generation")
        
        # Get users who need fresh recommendations
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        # Users with no recent recommendations
        users_needing_recs = db.session.query(User).filter(
            User.is_active == True
        ).filter(
            ~User.id.in_(
                db.session.query(Recommendation.user_id).filter(
                    Recommendation.created_at > cutoff_date,
                    Recommendation.user_id.isnot(None)
                )
            )
        ).all()
        
        generated_count = 0
        error_count = 0
        
        for user in users_needing_recs:
            try:
                # Check if user has enough activity for meaningful recommendations
                user_ratings = db.session.query(db.func.count()).filter_by(user_id=user.id).scalar()
                if user_ratings < 1:
                    continue  # Skip users with no ratings
                
                recommendations = engine.generate_recommendations(
                    user_id=user.id,
                    algorithm='hybrid',
                    limit=10
                )
                generated_count += len(recommendations)
                
                # Commit in batches of 50 users
                if generated_count % 500 == 0:
                    db.session.commit()
                    
            except Exception as e:
                logger.error(f"Error generating recommendations for user {user.id}: {str(e)}")
                error_count += 1
        
        db.session.commit()
        logger.info(f"Generated recommendations for {len(users_needing_recs)} users")
        logger.info(f"Total recommendations: {generated_count}, Errors: {error_count}")


def daily_metrics_update():
    """Daily task: Update recommendation performance metrics"""
    logger = setup_logging()
    app = create_app()
    
    with app.app_context():
        logger.info("Starting daily metrics update")
        
        try:
            update_recommendation_metrics()
            logger.info("Metrics updated successfully")
        except Exception as e:
            logger.error(f"Error updating metrics: {str(e)}")


def weekly_cleanup():
    """Weekly task: Clean up old recommendations and data"""
    logger = setup_logging()
    app = create_app()
    
    with app.app_context():
        logger.info("Starting weekly cleanup")
        
        # Remove expired recommendations
        expired_cutoff = datetime.utcnow()
        expired_recs = Recommendation.query.filter(
            Recommendation.expires_at < expired_cutoff
        ).all()
        
        for rec in expired_recs:
            db.session.delete(rec)
        
        # Remove very old dismissed recommendations (older than 30 days)
        old_dismissed_cutoff = datetime.utcnow() - timedelta(days=30)
        old_dismissed = Recommendation.query.filter(
            Recommendation.status == 'dismissed',
            Recommendation.created_at < old_dismissed_cutoff
        ).all()
        
        for rec in old_dismissed:
            db.session.delete(rec)
        
        # Remove old recommendation history (older than 90 days)
        history_cutoff = datetime.utcnow() - timedelta(days=90)
        old_history = RecommendationHistory.query.filter(
            RecommendationHistory.generation_date < history_cutoff
        ).all()
        
        for history in old_history:
            db.session.delete(history)
        
        db.session.commit()
        
        logger.info(f"Cleaned up {len(expired_recs)} expired recommendations")
        logger.info(f"Cleaned up {len(old_dismissed)} old dismissed recommendations")
        logger.info(f"Cleaned up {len(old_history)} old history records")


def experiment_management():
    """Daily task: Manage A/B testing experiments"""
    logger = setup_logging()
    app = create_app()
    
    with app.app_context():
        logger.info("Checking experiment status")
        
        # Check for experiments that should be automatically stopped
        now = datetime.utcnow()
        
        # Stop experiments that have passed their end date
        expired_experiments = ABTestExperiment.query.filter(
            ABTestExperiment.status == 'running',
            ABTestExperiment.end_date < now
        ).all()
        
        for experiment in expired_experiments:
            experiment.status = 'completed'
            logger.info(f"Automatically stopped experiment {experiment.experiment_id}")
        
        # Start experiments that have reached their start date
        ready_experiments = ABTestExperiment.query.filter(
            ABTestExperiment.status == 'draft',
            ABTestExperiment.start_date <= now
        ).all()
        
        for experiment in ready_experiments:
            experiment.status = 'running'
            logger.info(f"Automatically started experiment {experiment.experiment_id}")
        
        db.session.commit()


def algorithm_performance_analysis():
    """Weekly task: Analyze algorithm performance and log insights"""
    logger = setup_logging()
    app = create_app()
    
    with app.app_context():
        logger.info("Starting algorithm performance analysis")
        
        # Get performance data for the last week
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # Algorithm performance by metrics
        algorithm_stats = db.session.query(
            RecommendationHistory.algorithm,
            db.func.avg(RecommendationHistory.view_rate).label('avg_view_rate'),
            db.func.avg(RecommendationHistory.click_rate).label('avg_click_rate'),
            db.func.avg(RecommendationHistory.like_rate).label('avg_like_rate'),
            db.func.count(RecommendationHistory.id).label('total_batches')
        ).filter(
            RecommendationHistory.generation_date >= week_ago
        ).group_by(RecommendationHistory.algorithm).all()
        
        logger.info("=== Weekly Algorithm Performance ===")
        for stats in algorithm_stats:
            algorithm, view_rate, click_rate, like_rate, batches = stats
            logger.info(f"{algorithm}: "
                       f"View Rate: {view_rate:.3f}, "
                       f"Click Rate: {click_rate:.3f}, "
                       f"Like Rate: {like_rate:.3f}, "
                       f"Batches: {batches}")
        
        # Find best performing algorithm
        if algorithm_stats:
            best_algorithm = max(algorithm_stats, key=lambda x: x.like_rate or 0)
            logger.info(f"Best performing algorithm this week: {best_algorithm.algorithm}")


def user_engagement_analysis():
    """Weekly task: Analyze user engagement with recommendations"""
    logger = setup_logging()
    app = create_app()
    
    with app.app_context():
        logger.info("Starting user engagement analysis")
        
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # Users with recommendations in the last week
        users_with_recs = db.session.query(
            db.func.count(db.distinct(Recommendation.user_id))
        ).filter(
            Recommendation.created_at >= week_ago,
            Recommendation.user_id.isnot(None)
        ).scalar()
        
        # Users who interacted with recommendations
        users_who_clicked = db.session.query(
            db.func.count(db.distinct(Recommendation.user_id))
        ).filter(
            Recommendation.created_at >= week_ago,
            Recommendation.clicked_at.isnot(None),
            Recommendation.user_id.isnot(None)
        ).scalar()
        
        # Users who provided feedback
        users_who_gave_feedback = db.session.query(
            db.func.count(db.distinct(Recommendation.user_id))
        ).join(
            Recommendation.feedback
        ).filter(
            Recommendation.created_at >= week_ago,
            Recommendation.user_id.isnot(None)
        ).scalar()
        
        engagement_rate = users_who_clicked / users_with_recs if users_with_recs > 0 else 0
        feedback_rate = users_who_gave_feedback / users_with_recs if users_with_recs > 0 else 0
        
        logger.info(f"=== Weekly User Engagement ===")
        logger.info(f"Users with recommendations: {users_with_recs}")
        logger.info(f"Users who clicked: {users_who_clicked} ({engagement_rate:.1%})")
        logger.info(f"Users who gave feedback: {users_who_gave_feedback} ({feedback_rate:.1%})")


# Task scheduling configuration
SCHEDULED_TASKS = {
    'daily': [
        daily_profile_updates,
        daily_metrics_update,
        experiment_management
    ],
    'weekly': [
        weekly_recommendation_generation,
        weekly_cleanup,
        algorithm_performance_analysis,
        user_engagement_analysis
    ]
}


def run_daily_tasks():
    """Run all daily scheduled tasks"""
    logger = setup_logging()
    logger.info("Starting daily tasks")
    
    for task in SCHEDULED_TASKS['daily']:
        try:
            task()
        except Exception as e:
            logger.error(f"Error in daily task {task.__name__}: {str(e)}")
    
    logger.info("Daily tasks completed")


def run_weekly_tasks():
    """Run all weekly scheduled tasks"""
    logger = setup_logging()
    logger.info("Starting weekly tasks")
    
    for task in SCHEDULED_TASKS['weekly']:
        try:
            task()
        except Exception as e:
            logger.error(f"Error in weekly task {task.__name__}: {str(e)}")
    
    logger.info("Weekly tasks completed")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'daily':
            run_daily_tasks()
        elif sys.argv[1] == 'weekly':
            run_weekly_tasks()
        else:
            print("Usage: python recommendation_scheduler.py [daily|weekly]")
    else:
        print("Usage: python recommendation_scheduler.py [daily|weekly]")
