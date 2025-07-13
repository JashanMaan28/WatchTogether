#!/usr/bin/env python3
"""
Social Recommendation Scheduler
Scheduled tasks for social recommendation features
"""

import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from utils.social_analytics import generate_daily_insights
from utils.recommendation_engine import RecommendationEngine
from models.recommendations import TrendingContent, SocialRecommendationInsight
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/social_recommendations.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def update_trending_content():
    """Update trending content metrics"""
    logger.info("Starting trending content update...")
    
    try:
        rec_engine = RecommendationEngine()
        rec_engine.update_trending_content()
        
        # Clean up old trending records (older than 30 days)
        old_date = datetime.utcnow() - timedelta(days=30)
        old_trends = TrendingContent.query.filter(
            TrendingContent.period_end < old_date
        ).all()
        
        for trend in old_trends:
            db.session.delete(trend)
        
        db.session.commit()
        logger.info(f"Trending content updated. Cleaned up {len(old_trends)} old records.")
        
    except Exception as e:
        logger.error(f"Error updating trending content: {e}")
        db.session.rollback()


def generate_insights():
    """Generate daily insights for all users"""
    logger.info("Starting daily insights generation...")
    
    try:
        insights_count = generate_daily_insights()
        logger.info(f"Generated {insights_count} new insights")
        
    except Exception as e:
        logger.error(f"Error generating insights: {e}")


def cleanup_old_insights():
    """Clean up old or expired insights"""
    logger.info("Cleaning up old insights...")
    
    try:
        # Delete expired insights
        expired_insights = SocialRecommendationInsight.query.filter(
            SocialRecommendationInsight.expires_at < datetime.utcnow()
        ).all()
        
        # Delete dismissed insights older than 7 days
        old_dismissed = SocialRecommendationInsight.query.filter(
            SocialRecommendationInsight.status == 'dismissed',
            SocialRecommendationInsight.dismissed_at < datetime.utcnow() - timedelta(days=7)
        ).all()
        
        total_deleted = len(expired_insights) + len(old_dismissed)
        
        for insight in expired_insights + old_dismissed:
            db.session.delete(insight)
        
        db.session.commit()
        logger.info(f"Cleaned up {total_deleted} old insights")
        
    except Exception as e:
        logger.error(f"Error cleaning up insights: {e}")
        db.session.rollback()


def update_recommendation_history():
    """Update recommendation history metrics"""
    logger.info("Updating recommendation history metrics...")
    
    try:
        from models.recommendations import RecommendationHistory, Recommendation, RecommendationFeedback
        
        # Get recommendation histories that need updating
        histories = RecommendationHistory.query.filter(
            RecommendationHistory.updated_at < datetime.utcnow() - timedelta(hours=6)
        ).all()
        
        updated_count = 0
        
        for history in histories:
            # Get recommendations for this history
            if history.user_id:
                recommendations = Recommendation.query.filter_by(
                    user_id=history.user_id,
                    algorithm=history.algorithm
                ).filter(
                    Recommendation.created_at >= history.generation_date - timedelta(hours=1),
                    Recommendation.created_at <= history.generation_date + timedelta(hours=1)
                ).all()
            else:
                recommendations = Recommendation.query.filter_by(
                    group_id=history.group_id,
                    algorithm=history.algorithm
                ).filter(
                    Recommendation.created_at >= history.generation_date - timedelta(hours=1),
                    Recommendation.created_at <= history.generation_date + timedelta(hours=1)
                ).all()
            
            if recommendations:
                total = len(recommendations)
                viewed = sum(1 for r in recommendations if r.viewed_at)
                clicked = sum(1 for r in recommendations if r.clicked_at)
                
                # Calculate feedback metrics
                liked = 0
                for rec in recommendations:
                    like_feedback = RecommendationFeedback.query.filter_by(
                        recommendation_id=rec.id,
                        feedback_type='like'
                    ).count()
                    if like_feedback > 0:
                        liked += 1
                
                # Update metrics
                history.view_rate = viewed / total if total > 0 else 0
                history.click_rate = clicked / total if total > 0 else 0
                history.like_rate = liked / total if total > 0 else 0
                history.updated_at = datetime.utcnow()
                
                updated_count += 1
        
        db.session.commit()
        logger.info(f"Updated {updated_count} recommendation histories")
        
    except Exception as e:
        logger.error(f"Error updating recommendation history: {e}")
        db.session.rollback()


def run_daily_tasks():
    """Run all daily maintenance tasks"""
    logger.info("=== Starting daily social recommendation tasks ===")
    
    update_trending_content()
    generate_insights()
    cleanup_old_insights()
    update_recommendation_history()
    
    logger.info("=== Daily tasks completed ===")


def run_hourly_tasks():
    """Run hourly maintenance tasks"""
    logger.info("=== Starting hourly social recommendation tasks ===")
    
    update_trending_content()
    
    logger.info("=== Hourly tasks completed ===")


def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(description='Social Recommendation Scheduler')
    parser.add_argument('--task', choices=['daily', 'hourly', 'trending', 'insights', 'cleanup'],
                      default='daily', help='Task to run')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    
    args = parser.parse_args()
    
    # Create Flask app context
    app = create_app()
    with app.app_context():
        logger.info(f"Running task: {args.task}")
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
            return
        
        try:
            if args.task == 'daily':
                run_daily_tasks()
            elif args.task == 'hourly':
                run_hourly_tasks()
            elif args.task == 'trending':
                update_trending_content()
            elif args.task == 'insights':
                generate_insights()
            elif args.task == 'cleanup':
                cleanup_old_insights()
            
        except Exception as e:
            logger.error(f"Task failed: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()
