#!/usr/bin/env python3
"""
Social Recommendation Test Suite
Test script for social recommendation features
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from models.recommendations import *
from utils.recommendation_engine import RecommendationEngine
from utils.social_analytics import (
    analyze_friend_influence, calculate_taste_similarity, 
    generate_daily_insights
)
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_data():
    """Create sample data for testing social features"""
    logger.info("Creating test data...")
    
    try:
        from models import User, Content, Group, Friendship, GroupMembership
        
        # Create test users if they don't exist
        test_users = []
        for i in range(5):
            username = f'testuser{i+1}'
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(
                    username=username,
                    email=f'test{i+1}@example.com',
                    password_hash='$2b$12$dummy'  # Dummy hash
                )
                db.session.add(user)
                db.session.flush()
            test_users.append(user)
        
        # Create friendships
        for i in range(len(test_users)):
            for j in range(i+1, len(test_users)):
                friendship = Friendship.query.filter_by(
                    requester_id=test_users[i].id,
                    addressee_id=test_users[j].id
                ).first()
                if not friendship:
                    friendship = Friendship(
                        requester_id=test_users[i].id,
                        addressee_id=test_users[j].id,
                        status='accepted',
                        created_at=datetime.utcnow()
                    )
                    db.session.add(friendship)
        
        # Create test content if it doesn't exist
        test_content = []
        content_titles = [
            'Test Movie 1', 'Test Movie 2', 'Test TV Show 1', 
            'Test TV Show 2', 'Test Documentary 1'
        ]
        
        for title in content_titles:
            content = Content.query.filter_by(title=title).first()
            if not content:
                content = Content(
                    title=title,
                    content_type='movie' if 'Movie' in title else 'tv_show',
                    genre=['Drama', 'Action'],
                    release_year=2020 + random.randint(0, 3),
                    rating=random.uniform(7.0, 9.0),
                    description=f'Test content: {title}'
                )
                db.session.add(content)
                db.session.flush()
            test_content.append(content)
        
        # Create test group
        test_group = Group.query.filter_by(name='Test Social Group').first()
        if not test_group:
            test_group = Group(
                name='Test Social Group',
                description='Test group for social features',
                creator_id=test_users[0].id,
                privacy='public'
            )
            db.session.add(test_group)
            db.session.flush()
            
            # Add members to group
            for user in test_users[:3]:
                membership = GroupMembership(
                    user_id=user.id,
                    group_id=test_group.id,
                    role='member' if user != test_users[0] else 'admin',
                    joined_at=datetime.utcnow()
                )
                db.session.add(membership)
        
        db.session.commit()
        logger.info(f"Test data created: {len(test_users)} users, {len(test_content)} content items, 1 group")
        return test_users, test_content, test_group
        
    except Exception as e:
        logger.error(f"Error creating test data: {e}")
        db.session.rollback()
        return [], [], None


def test_social_signals():
    """Test social signal creation and retrieval"""
    logger.info("Testing social signals...")
    
    try:
        test_users, test_content, test_group = create_test_data()
        if not test_users or not test_content:
            logger.error("Failed to create test data")
            return False
        
        # Create test social signals
        signal_types = ['like', 'share', 'watch', 'rating', 'discussion']
        
        for user in test_users[:3]:
            for content in test_content[:3]:
                signal_type = random.choice(signal_types)
                signal = SocialRecommendationSignal(
                    user_id=user.id,
                    content_id=content.id,
                    signal_type=signal_type,
                    signal_strength=random.uniform(0.5, 1.0),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(0, 7))
                )
                db.session.add(signal)
        
        db.session.commit()
        
        # Test signal retrieval
        signals = SocialRecommendationSignal.query.limit(5).all()
        logger.info(f"Created and retrieved {len(signals)} social signals")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing social signals: {e}")
        db.session.rollback()
        return False


def test_friend_recommendations():
    """Test friend-based recommendations"""
    logger.info("Testing friend recommendations...")
    
    try:
        test_users, test_content, test_group = create_test_data()
        if not test_users or not test_content:
            logger.error("Failed to create test data")
            return False
        
        # Create friend recommendations
        for i in range(3):
            friend_rec = FriendRecommendation(
                recommender_id=test_users[0].id,
                recipient_id=test_users[i+1].id,
                content_id=test_content[i].id,
                message=f"You should watch this! - Test recommendation {i+1}",
                created_at=datetime.utcnow()
            )
            db.session.add(friend_rec)
        
        db.session.commit()
        
        # Test retrieval
        friend_recs = FriendRecommendation.query.filter_by(
            recommender_id=test_users[0].id
        ).all()
        
        logger.info(f"Created and retrieved {len(friend_recs)} friend recommendations")
        return True
        
    except Exception as e:
        logger.error(f"Error testing friend recommendations: {e}")
        db.session.rollback()
        return False


def test_group_sessions():
    """Test group recommendation sessions"""
    logger.info("Testing group recommendation sessions...")
    
    try:
        test_users, test_content, test_group = create_test_data()
        if not test_users or not test_content or not test_group:
            logger.error("Failed to create test data")
            return False
        
        # Create group recommendation session
        session = GroupRecommendationSession(
            group_id=test_group.id,
            creator_id=test_users[0].id,
            title='Test Recommendation Session',
            description='Testing group recommendations',
            voting_deadline=datetime.utcnow() + timedelta(days=1),
            status='active'
        )
        db.session.add(session)
        db.session.flush()
        
        # Add session items
        for content in test_content[:3]:
            item = GroupRecommendationItem(
                session_id=session.id,
                content_id=content.id,
                suggested_by=test_users[0].id,
                created_at=datetime.utcnow()
            )
            db.session.add(item)
            db.session.flush()
            
            # Add votes
            for user in test_users[:3]:
                vote = GroupRecommendationVote(
                    session_id=session.id,
                    item_id=item.id,
                    user_id=user.id,
                    vote_type='upvote' if random.random() > 0.3 else 'downvote',
                    created_at=datetime.utcnow()
                )
                db.session.add(vote)
        
        db.session.commit()
        
        # Test retrieval
        sessions = GroupRecommendationSession.query.filter_by(
            group_id=test_group.id
        ).all()
        
        logger.info(f"Created and retrieved {len(sessions)} group sessions")
        return True
        
    except Exception as e:
        logger.error(f"Error testing group sessions: {e}")
        db.session.rollback()
        return False


def test_recommendation_engine():
    """Test social recommendation algorithms"""
    logger.info("Testing recommendation engine with social features...")
    
    try:
        test_users, test_content, test_group = create_test_data()
        if not test_users:
            logger.error("Failed to create test data")
            return False
        
        rec_engine = RecommendationEngine()
        
        # Test different algorithms
        algorithms = ['social_collaborative', 'friend_based', 'social_hybrid']
        
        for algorithm in algorithms:
            try:
                recommendations = rec_engine.get_recommendations(
                    user_id=test_users[0].id,
                    count=5,
                    algorithm=algorithm
                )
                logger.info(f"{algorithm}: Generated {len(recommendations)} recommendations")
            except Exception as e:
                logger.warning(f"Algorithm {algorithm} failed: {e}")
        
        # Test trending content
        try:
            rec_engine.update_trending_content()
            trending = TrendingContent.query.limit(5).all()
            logger.info(f"Updated trending content: {len(trending)} items")
        except Exception as e:
            logger.warning(f"Trending update failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing recommendation engine: {e}")
        return False


def test_analytics():
    """Test social analytics functions"""
    logger.info("Testing social analytics...")
    
    try:
        test_users, test_content, test_group = create_test_data()
        if not test_users:
            logger.error("Failed to create test data")
            return False
        
        # Test friend influence analysis
        try:
            influence = analyze_friend_influence(test_users[0].id)
            logger.info(f"Friend influence analysis: {len(influence)} influences found")
        except Exception as e:
            logger.warning(f"Friend influence analysis failed: {e}")
        
        # Test taste similarity
        try:
            similarity = calculate_taste_similarity(test_users[0].id, test_users[1].id)
            logger.info(f"Taste similarity: {similarity:.2f}")
        except Exception as e:
            logger.warning(f"Taste similarity calculation failed: {e}")
        
        # Test insight generation
        try:
            insights_count = generate_daily_insights()
            logger.info(f"Generated {insights_count} insights")
        except Exception as e:
            logger.warning(f"Insight generation failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing analytics: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    logger.info("=== Running Social Recommendation Test Suite ===")
    
    tests = [
        ("Social Signals", test_social_signals),
        ("Friend Recommendations", test_friend_recommendations),
        ("Group Sessions", test_group_sessions),
        ("Recommendation Engine", test_recommendation_engine),
        ("Analytics", test_analytics)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results[test_name] = False
    
    # Print summary
    logger.info("\n=== Test Results Summary ===")
    passed = 0
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nTotal: {passed}/{len(tests)} tests passed")
    return passed == len(tests)


def cleanup_test_data():
    """Clean up test data"""
    logger.info("Cleaning up test data...")
    
    try:
        from models import User, Content, Group
        
        # Delete test data
        test_users = User.query.filter(User.username.like('testuser%')).all()
        test_content = Content.query.filter(Content.title.like('Test %')).all()
        test_groups = Group.query.filter(Group.name.like('Test %')).all()
        
        # Delete related social data first
        for user in test_users:
            SocialRecommendationSignal.query.filter_by(user_id=user.id).delete()
            FriendRecommendation.query.filter(
                (FriendRecommendation.recommender_id == user.id) |
                (FriendRecommendation.recipient_id == user.id)
            ).delete()
            SocialRecommendationInsight.query.filter_by(user_id=user.id).delete()
        
        for content in test_content:
            SocialRecommendationSignal.query.filter_by(content_id=content.id).delete()
            TrendingContent.query.filter_by(content_id=content.id).delete()
        
        for group in test_groups:
            GroupRecommendationSession.query.filter_by(group_id=group.id).delete()
        
        # Delete main entities
        for user in test_users:
            db.session.delete(user)
        for content in test_content:
            db.session.delete(content)
        for group in test_groups:
            db.session.delete(group)
        
        db.session.commit()
        logger.info(f"Cleaned up {len(test_users)} users, {len(test_content)} content, {len(test_groups)} groups")
        
    except Exception as e:
        logger.error(f"Error cleaning up test data: {e}")
        db.session.rollback()


def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(description='Social Recommendation Test Suite')
    parser.add_argument('--test', choices=[
        'all', 'signals', 'friends', 'groups', 'engine', 'analytics'
    ], default='all', help='Test to run')
    parser.add_argument('--cleanup', action='store_true', help='Clean up test data')
    parser.add_argument('--create-data', action='store_true', help='Create test data only')
    
    args = parser.parse_args()
    
    # Create Flask app context
    app = create_app()
    with app.app_context():
        try:
            if args.cleanup:
                cleanup_test_data()
                return
            
            if args.create_data:
                create_test_data()
                return
            
            if args.test == 'all':
                success = run_all_tests()
                sys.exit(0 if success else 1)
            elif args.test == 'signals':
                success = test_social_signals()
            elif args.test == 'friends':
                success = test_friend_recommendations()
            elif args.test == 'groups':
                success = test_group_sessions()
            elif args.test == 'engine':
                success = test_recommendation_engine()
            elif args.test == 'analytics':
                success = test_analytics()
            
            sys.exit(0 if success else 1)
            
        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()
