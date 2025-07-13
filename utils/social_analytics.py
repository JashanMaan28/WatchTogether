"""
Social Recommendation Analytics and Insights Generator
"""

from app import db
from models import User, Content, ContentRating, Group, GroupMember, Friendship
from models.recommendations import (
    SocialRecommendationSignal, FriendRecommendation, TrendingContent,
    SocialRecommendationInsight, Recommendation, RecommendationFeedback
)
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json


class SocialRecommendationAnalytics:
    """Generate insights and analytics for social recommendations"""
    
    def __init__(self):
        self.insight_generators = {
            'friend_influence': self._analyze_friend_influence,
            'group_consensus': self._analyze_group_consensus,
            'trending_alert': self._analyze_trending_patterns,
            'recommendation_accuracy': self._analyze_recommendation_accuracy,
            'social_discovery': self._analyze_social_discovery,
            'taste_similarity': self._analyze_taste_similarity
        }
    
    def generate_insights_for_user(self, user_id):
        """Generate all types of insights for a user"""
        user = User.query.get(user_id)
        if not user:
            return []
        
        insights = []
        for insight_type, generator in self.insight_generators.items():
            try:
                insight_data = generator(user)
                if insight_data:
                    insights.append(self._create_insight(user_id, insight_type, insight_data))
            except Exception as e:
                print(f"Error generating {insight_type} insight for user {user_id}: {e}")
        
        return insights
    
    def generate_insights_for_group(self, group_id):
        """Generate group-specific insights"""
        group = Group.query.get(group_id)
        if not group:
            return []
        
        insights = []
        
        # Group consensus insights
        consensus_data = self._analyze_group_consensus_patterns(group)
        if consensus_data:
            insights.append(self._create_group_insight(group_id, 'group_consensus', consensus_data))
        
        # Group trending insights
        trending_data = self._analyze_group_trending(group)
        if trending_data:
            insights.append(self._create_group_insight(group_id, 'group_trending', trending_data))
        
        return insights
    
    def _analyze_friend_influence(self, user):
        """Analyze how friends influence user's content choices"""
        friends = user.get_friends()
        if not friends:
            return None
        
        friend_ids = [friend.id for friend in friends]
        
        # Get user's ratings
        user_ratings = ContentRating.query.filter_by(user_id=user.id).all()
        if not user_ratings:
            return None
        
        # Find content that was rated by both user and friends
        influenced_content = []
        for rating in user_ratings:
            friend_ratings = ContentRating.query.filter(
                ContentRating.content_id == rating.content_id,
                ContentRating.user_id.in_(friend_ids),
                ContentRating.created_at < rating.created_at  # Friend rated before user
            ).all()
            
            if friend_ratings:
                avg_friend_rating = sum(r.rating for r in friend_ratings) / len(friend_ratings)
                influenced_content.append({
                    'content': rating.content,
                    'user_rating': rating.rating,
                    'friend_avg_rating': avg_friend_rating,
                    'friend_count': len(friend_ratings),
                    'influence_score': abs(rating.rating - avg_friend_rating)
                })
        
        if not influenced_content:
            return None
        
        # Calculate overall influence metrics
        total_influence = sum(item['influence_score'] for item in influenced_content)
        avg_influence = total_influence / len(influenced_content)
        
        # Find most influential friends
        friend_influence = defaultdict(list)
        for item in influenced_content:
            for friend_rating in ContentRating.query.filter(
                ContentRating.content_id == item['content'].id,
                ContentRating.user_id.in_(friend_ids)
            ).all():
                friend_influence[friend_rating.user_id].append(
                    abs(item['user_rating'] - friend_rating.rating)
                )
        
        most_influential_friends = []
        for friend_id, scores in friend_influence.items():
            avg_score = sum(scores) / len(scores)
            friend = User.query.get(friend_id)
            most_influential_friends.append({
                'friend': friend,
                'influence_score': avg_score,
                'content_count': len(scores)
            })
        
        most_influential_friends.sort(key=lambda x: x['influence_score'])
        
        return {
            'influenced_content_count': len(influenced_content),
            'average_influence_score': avg_influence,
            'most_influential_friends': most_influential_friends[:3],
            'top_influenced_content': sorted(influenced_content, 
                                           key=lambda x: x['influence_score'])[:5]
        }
    
    def _analyze_group_consensus(self, user):
        """Analyze user's alignment with group preferences"""
        user_groups = GroupMember.query.filter_by(user_id=user.id).all()
        if not user_groups:
            return None
        
        consensus_data = []
        
        for membership in user_groups:
            group = membership.group
            member_ids = [m.user_id for m in group.members if m.user_id != user.id]
            
            if not member_ids:
                continue
            
            # Get content rated by both user and other group members
            user_ratings = ContentRating.query.filter_by(user_id=user.id).all()
            group_consensus_scores = []
            
            for rating in user_ratings:
                group_ratings = ContentRating.query.filter(
                    ContentRating.content_id == rating.content_id,
                    ContentRating.user_id.in_(member_ids)
                ).all()
                
                if len(group_ratings) >= max(1, len(member_ids) * 0.3):  # At least 30% rated it
                    avg_group_rating = sum(r.rating for r in group_ratings) / len(group_ratings)
                    consensus_score = abs(rating.rating - avg_group_rating)
                    group_consensus_scores.append({
                        'content': rating.content,
                        'user_rating': rating.rating,
                        'group_avg_rating': avg_group_rating,
                        'consensus_score': consensus_score
                    })
            
            if group_consensus_scores:
                avg_consensus = sum(item['consensus_score'] for item in group_consensus_scores) / len(group_consensus_scores)
                consensus_data.append({
                    'group': group,
                    'average_consensus_score': avg_consensus,
                    'rated_content_count': len(group_consensus_scores),
                    'alignment': 'high' if avg_consensus < 1.0 else 'medium' if avg_consensus < 2.0 else 'low'
                })
        
        return consensus_data if consensus_data else None
    
    def _analyze_trending_patterns(self, user):
        """Analyze trending content relevant to user"""
        friends = user.get_friends()
        if not friends:
            return None
        
        # Get recent trending content
        recent_trending = TrendingContent.query.filter(
            TrendingContent.period_end >= datetime.utcnow() - timedelta(days=7)
        ).order_by(TrendingContent.trending_score.desc()).limit(10).all()
        
        if not recent_trending:
            return None
        
        # Analyze user's potential interest in trending content
        user_genres = self._get_user_preferred_genres(user.id)
        relevant_trends = []
        
        for trend in recent_trending:
            content = trend.content
            content_genres = content.get_genres() if hasattr(content, 'get_genres') else []
            
            # Calculate relevance based on genre overlap
            genre_overlap = len(set(user_genres) & set(content_genres))
            relevance_score = genre_overlap / max(len(user_genres), 1)
            
            if relevance_score > 0.2:  # At least 20% genre overlap
                relevant_trends.append({
                    'content': content,
                    'trending_score': trend.trending_score,
                    'relevance_score': relevance_score,
                    'scope': trend.scope,
                    'unique_viewers': trend.unique_viewers
                })
        
        return {
            'relevant_trends': relevant_trends,
            'total_trending_count': len(recent_trending),
            'relevant_count': len(relevant_trends)
        } if relevant_trends else None
    
    def _analyze_recommendation_accuracy(self, user):
        """Analyze accuracy of recommendations for user"""
        recommendations = Recommendation.query.filter_by(user_id=user.id).limit(50).all()
        if not recommendations:
            return None
        
        accuracy_data = defaultdict(list)
        
        for rec in recommendations:
            feedback = RecommendationFeedback.query.filter_by(
                recommendation_id=rec.id,
                user_id=user.id
            ).first()
            
            if feedback:
                liked = feedback.feedback_type == 'like'
                accuracy_data[rec.algorithm].append({
                    'recommendation': rec,
                    'liked': liked,
                    'score': rec.score
                })
        
        algorithm_accuracy = {}
        for algorithm, data in accuracy_data.items():
            if data:
                accuracy = sum(1 for item in data if item['liked']) / len(data)
                algorithm_accuracy[algorithm] = {
                    'accuracy': accuracy,
                    'total_count': len(data),
                    'liked_count': sum(1 for item in data if item['liked'])
                }
        
        return algorithm_accuracy if algorithm_accuracy else None
    
    def _analyze_social_discovery(self, user):
        """Analyze how social features help user discover new content"""
        # Get content discovered through social features
        friend_recs = FriendRecommendation.query.filter_by(friend_id=user.id).all()
        social_signals = SocialRecommendationSignal.query.filter_by(user_id=user.id).all()
        
        discovered_content = set()
        discovery_sources = defaultdict(int)
        
        for rec in friend_recs:
            discovered_content.add(rec.content_id)
            discovery_sources['friend_recommendations'] += 1
        
        for signal in social_signals:
            discovered_content.add(signal.content_id)
            discovery_sources[signal.signal_type] += 1
        
        if not discovered_content:
            return None
        
        # Calculate how much of user's rated content came from social discovery
        user_ratings = ContentRating.query.filter_by(user_id=user.id).all()
        socially_discovered_ratings = [
            r for r in user_ratings if r.content_id in discovered_content
        ]
        
        social_discovery_rate = len(socially_discovered_ratings) / len(user_ratings) if user_ratings else 0
        
        return {
            'total_discovered_content': len(discovered_content),
            'discovery_sources': dict(discovery_sources),
            'social_discovery_rate': social_discovery_rate,
            'socially_discovered_ratings': len(socially_discovered_ratings)
        }
    
    def _analyze_taste_similarity(self, user):
        """Analyze taste similarity with friends"""
        friends = user.get_friends()
        if not friends:
            return None
        
        user_ratings = {r.content_id: r.rating for r in ContentRating.query.filter_by(user_id=user.id).all()}
        if not user_ratings:
            return None
        
        similarity_scores = []
        
        for friend in friends:
            friend_ratings = {r.content_id: r.rating for r in ContentRating.query.filter_by(user_id=friend.id).all()}
            
            # Find common rated content
            common_content = set(user_ratings.keys()) & set(friend_ratings.keys())
            
            if len(common_content) >= 3:  # Need at least 3 common ratings
                # Calculate Pearson correlation coefficient
                user_scores = [user_ratings[content_id] for content_id in common_content]
                friend_scores = [friend_ratings[content_id] for content_id in common_content]
                
                correlation = self._calculate_correlation(user_scores, friend_scores)
                
                similarity_scores.append({
                    'friend': friend,
                    'similarity_score': correlation,
                    'common_content_count': len(common_content)
                })
        
        if not similarity_scores:
            return None
        
        similarity_scores.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return {
            'most_similar_friends': similarity_scores[:3],
            'average_similarity': sum(s['similarity_score'] for s in similarity_scores) / len(similarity_scores),
            'friends_with_data': len(similarity_scores)
        }
    
    def _calculate_correlation(self, x, y):
        """Calculate Pearson correlation coefficient"""
        n = len(x)
        if n == 0:
            return 0
        
        sum_x = sum(x)
        sum_y = sum(y)
        sum_x_sq = sum(xi * xi for xi in x)
        sum_y_sq = sum(yi * yi for yi in y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        
        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x_sq - sum_x * sum_x) * (n * sum_y_sq - sum_y * sum_y)) ** 0.5
        
        if denominator == 0:
            return 0
        
        return numerator / denominator
    
    def _get_user_preferred_genres(self, user_id):
        """Get user's preferred genres based on ratings"""
        ratings = ContentRating.query.filter_by(user_id=user_id).filter(ContentRating.rating >= 4).all()
        
        genre_counts = Counter()
        for rating in ratings:
            if hasattr(rating.content, 'get_genres'):
                for genre in rating.content.get_genres():
                    genre_counts[genre] += 1
        
        return [genre for genre, count in genre_counts.most_common(5)]
    
    def _create_insight(self, user_id, insight_type, data):
        """Create a social recommendation insight"""
        title, description, importance_score = self._generate_insight_content(insight_type, data)
        
        insight = SocialRecommendationInsight(
            user_id=user_id,
            insight_type=insight_type,
            title=title,
            description=description,
            importance_score=importance_score,
            relevance_score=min(1.0, importance_score + 0.1),
            confidence_score=0.8,  # Default confidence
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        insight.set_insight_data(data)
        
        return insight
    
    def _create_group_insight(self, group_id, insight_type, data):
        """Create a group-specific insight"""
        title, description, importance_score = self._generate_group_insight_content(insight_type, data)
        
        insight = SocialRecommendationInsight(
            group_id=group_id,
            insight_type=insight_type,
            scope='group',
            title=title,
            description=description,
            importance_score=importance_score,
            relevance_score=min(1.0, importance_score + 0.1),
            confidence_score=0.8,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        insight.set_insight_data(data)
        
        return insight
    
    def _generate_insight_content(self, insight_type, data):
        """Generate title, description, and importance score for insight"""
        if insight_type == 'friend_influence':
            influenced_count = data['influenced_content_count']
            top_friend = data['most_influential_friends'][0] if data['most_influential_friends'] else None
            
            title = f"Friend Influence on {influenced_count} Items"
            description = f"Your friends have influenced your ratings on {influenced_count} pieces of content."
            if top_friend:
                description += f" {top_friend['friend'].username} has been most influential."
            
            importance_score = min(1.0, influenced_count / 20)  # Scale based on content count
            
        elif insight_type == 'group_consensus':
            total_groups = len(data)
            high_alignment_groups = sum(1 for group_data in data if group_data['alignment'] == 'high')
            
            title = f"Group Alignment Analysis"
            description = f"You have high taste alignment with {high_alignment_groups} out of {total_groups} groups."
            
            importance_score = high_alignment_groups / total_groups if total_groups > 0 else 0
            
        elif insight_type == 'trending_alert':
            relevant_count = data['relevant_count']
            
            title = f"{relevant_count} Trending Items Match Your Taste"
            description = f"Found {relevant_count} trending items that align with your preferences."
            
            importance_score = min(1.0, relevant_count / 5)
            
        elif insight_type == 'recommendation_accuracy':
            best_algorithm = max(data.items(), key=lambda x: x[1]['accuracy']) if data else None
            
            if best_algorithm:
                title = f"Best Algorithm: {best_algorithm[0].replace('_', ' ').title()}"
                description = f"The {best_algorithm[0]} algorithm has {best_algorithm[1]['accuracy']:.1%} accuracy for you."
                importance_score = best_algorithm[1]['accuracy']
            else:
                title = "Recommendation Accuracy Analysis"
                description = "Not enough feedback data to analyze accuracy."
                importance_score = 0.2
                
        elif insight_type == 'social_discovery':
            discovery_rate = data['social_discovery_rate']
            
            title = f"Social Discovery: {discovery_rate:.1%} of Your Content"
            description = f"Social features helped you discover {discovery_rate:.1%} of the content you've rated."
            
            importance_score = discovery_rate
            
        elif insight_type == 'taste_similarity':
            if data['most_similar_friends']:
                most_similar = data['most_similar_friends'][0]
                title = f"Most Similar Friend: {most_similar['friend'].username}"
                description = f"You and {most_similar['friend'].username} have {most_similar['similarity_score']:.1%} taste similarity."
                importance_score = most_similar['similarity_score']
            else:
                title = "Taste Similarity Analysis"
                description = "Not enough common ratings to analyze taste similarity."
                importance_score = 0.2
        
        else:
            title = f"{insight_type.replace('_', ' ').title()} Insight"
            description = "Social recommendation insight generated."
            importance_score = 0.5
        
        return title, description, importance_score
    
    def _generate_group_insight_content(self, insight_type, data):
        """Generate group-specific insight content"""
        if insight_type == 'group_consensus':
            title = "Group Consensus Patterns"
            description = "Analysis of how group members align on content preferences."
            importance_score = 0.7
            
        elif insight_type == 'group_trending':
            title = "Group Trending Content"
            description = "Content that's gaining popularity within your group."
            importance_score = 0.6
            
        else:
            title = f"Group {insight_type.replace('_', ' ').title()}"
            description = "Group-specific insight generated."
            importance_score = 0.5
        
        return title, description, importance_score


def generate_daily_insights():
    """Generate daily insights for all users (can be run as a scheduled task)"""
    analytics = SocialRecommendationAnalytics()
    
    # Get active users (users who have rated content in the last 30 days)
    recent_date = datetime.utcnow() - timedelta(days=30)
    active_users = db.session.query(User).join(ContentRating).filter(
        ContentRating.created_at >= recent_date
    ).distinct().all()
    
    insights_created = 0
    
    for user in active_users:
        try:
            insights = analytics.generate_insights_for_user(user.id)
            for insight in insights:
                # Check if similar insight already exists
                existing = SocialRecommendationInsight.query.filter_by(
                    user_id=user.id,
                    insight_type=insight.insight_type,
                    status='active'
                ).filter(
                    SocialRecommendationInsight.created_at >= datetime.utcnow() - timedelta(days=1)
                ).first()
                
                if not existing:
                    db.session.add(insight)
                    insights_created += 1
            
        except Exception as e:
            print(f"Error generating insights for user {user.id}: {e}")
    
    try:
        db.session.commit()
        print(f"Generated {insights_created} new insights")
    except Exception as e:
        db.session.rollback()
        print(f"Error saving insights: {e}")
    
    return insights_created
