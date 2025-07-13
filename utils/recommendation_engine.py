"""
Recommendation Engine for WatchTogether
Implements content-based filtering, collaborative filtering, and hybrid approaches
"""

from app import db
from models import User, Content, ContentRating, UserWatchlist, Group, GroupMember
from models.recommendations import (
    UserPreferenceProfile, GroupPreferenceProfile, Recommendation, 
    RecommendationFeedback, RecommendationHistory, ABTestExperiment
)
from datetime import datetime, timedelta
import json
import math
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional
from sqlalchemy import and_, or_, func, desc


class RecommendationEngine:
    """Main recommendation engine class"""
    
    def __init__(self):
        self.algorithms = {
            'content_based': self._content_based_filtering,
            'collaborative': self._collaborative_filtering,
            'hybrid': self._hybrid_filtering,
            'trending': self._trending_content,
            'group_consensus': self._group_consensus_filtering
        }
    
    def generate_recommendations(self, user_id: int = None, group_id: int = None, 
                               algorithm: str = 'hybrid', limit: int = 10,
                               experiment_id: str = None) -> List[Recommendation]:
        """Generate recommendations for a user or group"""
        
        if user_id and group_id:
            raise ValueError("Cannot generate recommendations for both user and group")
        
        if not user_id and not group_id:
            raise ValueError("Must specify either user_id or group_id")
        
        # Clean up expired recommendations first
        self._cleanup_expired_recommendations(user_id=user_id, group_id=group_id)
        
        # Get or create preference profile
        if user_id:
            profile = self._get_or_create_user_profile(user_id)
            target_type = 'user'
            target_id = user_id
        else:
            profile = self._get_or_create_group_profile(group_id)
            target_type = 'group'
            target_id = group_id
        
        # Check for A/B test assignment
        variant = None
        if experiment_id and user_id:
            experiment = ABTestExperiment.query.filter_by(
                experiment_id=experiment_id, 
                status='running'
            ).first()
            if experiment:
                variant = experiment.assign_variant(user_id)
                # Modify algorithm based on variant
                variant_config = experiment.get_variants().get(variant, {})
                algorithm = variant_config.get('algorithm', algorithm)
        
        # Generate recommendations using specified algorithm
        algorithm_func = self.algorithms.get(algorithm, self._hybrid_filtering)
        recommendations = algorithm_func(profile, limit * 2)  # Generate more for filtering
        
        # Filter out already seen/rated content
        filtered_recommendations = self._filter_recommendations(
            recommendations, user_id, group_id
        )
        
        # Limit to requested number
        final_recommendations = filtered_recommendations[:limit]
        
        # Save recommendations to database
        saved_recommendations = []
        for content, score, reasoning in final_recommendations:
            rec = Recommendation(
                user_id=user_id,
                group_id=group_id,
                content_id=content.id,
                score=score,
                algorithm=algorithm,
                reasoning=reasoning,
                experiment_id=experiment_id,
                variant=variant,
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            db.session.add(rec)
            saved_recommendations.append(rec)
        
        # Update recommendation history
        self._update_recommendation_history(
            user_id, group_id, algorithm, len(saved_recommendations),
            experiment_id, variant
        )
        
        db.session.commit()
        return saved_recommendations
    
    def _cleanup_expired_recommendations(self, user_id: int = None, group_id: int = None):
        """Remove expired and old recommendations to prevent clutter"""
        query = Recommendation.query.filter(
            Recommendation.expires_at < datetime.utcnow()
        )
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        elif group_id:
            query = query.filter_by(group_id=group_id)
        
        expired_recs = query.all()
        for rec in expired_recs:
            rec.status = 'expired'
        
        # Also limit the number of active recommendations per user/group
        active_query = Recommendation.query.filter_by(status='active')
        if user_id:
            active_query = active_query.filter_by(user_id=user_id)
        elif group_id:
            active_query = active_query.filter_by(group_id=group_id)
        
        active_recs = active_query.order_by(Recommendation.created_at.desc()).all()
        
        # Keep only the most recent 50 active recommendations
        if len(active_recs) > 50:
            old_recs = active_recs[50:]
            for rec in old_recs:
                rec.status = 'archived'
    
    def _should_generate_new_recommendations(self, user_id: int = None, group_id: int = None, 
                                           min_interval_hours: int = 6) -> bool:
        """Check if enough time has passed since last recommendation generation"""
        query = Recommendation.query.filter_by(status='active')
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        elif group_id:
            query = query.filter_by(group_id=group_id)
        
        latest_rec = query.order_by(Recommendation.created_at.desc()).first()
        
        if not latest_rec:
            return True  # No previous recommendations
        
        time_since_last = datetime.utcnow() - latest_rec.created_at
        return time_since_last.total_seconds() > (min_interval_hours * 3600)
    
    def _get_or_create_user_profile(self, user_id: int) -> UserPreferenceProfile:
        """Get or create user preference profile"""
        profile = UserPreferenceProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = UserPreferenceProfile(user_id=user_id)
            db.session.add(profile)
            self._analyze_user_preferences(profile)
        elif profile.last_updated < datetime.utcnow() - timedelta(days=7):
            # Update profile if it's older than a week
            self._analyze_user_preferences(profile)
        
        return profile
    
    def _get_or_create_group_profile(self, group_id: int) -> GroupPreferenceProfile:
        """Get or create group preference profile"""
        profile = GroupPreferenceProfile.query.filter_by(group_id=group_id).first()
        if not profile:
            profile = GroupPreferenceProfile(group_id=group_id)
            db.session.add(profile)
            self._analyze_group_preferences(profile)
        elif profile.last_updated < datetime.utcnow() - timedelta(days=7):
            # Update profile if it's older than a week
            self._analyze_group_preferences(profile)
        
        return profile
    
    def _analyze_user_preferences(self, profile: UserPreferenceProfile):
        """Analyze user's ratings and watchlist to build preference profile"""
        user = profile.user
        
        # Analyze ratings
        ratings = ContentRating.query.filter_by(user_id=user.id).all()
        genre_scores = defaultdict(list)
        type_scores = defaultdict(list)
        
        for rating in ratings:
            content = rating.content
            score = rating.rating
            
            # Weight by rating (higher ratings contribute more)
            weight = score / 5.0
            
            # Analyze genres
            for genre in content.get_genres():
                genre_scores[genre].append(weight)
            
            # Analyze content types
            type_scores[content.type].append(weight)
        
        # Calculate average scores for genres and types
        genre_preferences = {
            genre: sum(scores) / len(scores) 
            for genre, scores in genre_scores.items()
        }
        type_preferences = {
            content_type: sum(scores) / len(scores)
            for content_type, scores in type_scores.items()
        }
        
        # Analyze watchlist for additional preferences
        watchlist_items = UserWatchlist.query.filter_by(user_id=user.id).all()
        for item in watchlist_items:
            content = item.content
            # Give moderate weight to watchlisted items
            weight = 0.6
            
            for genre in content.get_genres():
                if genre not in genre_preferences:
                    genre_preferences[genre] = weight
                else:
                    genre_preferences[genre] = (genre_preferences[genre] + weight) / 2
            
            if content.type not in type_preferences:
                type_preferences[content.type] = weight
            else:
                type_preferences[content.type] = (type_preferences[content.type] + weight) / 2
        
        # Update profile
        profile.set_genre_preferences(genre_preferences)
        profile.set_content_type_preferences(type_preferences)
        
        # Calculate confidence score based on data available
        total_ratings = len(ratings)
        total_watchlist = len(watchlist_items)
        confidence = min(1.0, (total_ratings * 0.7 + total_watchlist * 0.3) / 20)
        profile.confidence_score = confidence
        
        profile.last_updated = datetime.utcnow()
    
    def _analyze_group_preferences(self, profile: GroupPreferenceProfile):
        """Analyze group members' preferences to build group profile"""
        group = profile.group
        members = GroupMember.query.filter_by(group_id=group.id).all()
        
        all_genre_prefs = []
        all_type_prefs = []
        
        for member in members:
            user_profile = self._get_or_create_user_profile(member.user_id)
            user_genre_prefs = user_profile.get_genre_preferences()
            user_type_prefs = user_profile.get_content_type_preferences()
            
            if user_genre_prefs:
                all_genre_prefs.append(user_genre_prefs)
            if user_type_prefs:
                all_type_prefs.append(user_type_prefs)
        
        # Aggregate preferences using average
        aggregated_genres = defaultdict(list)
        aggregated_types = defaultdict(list)
        
        for prefs in all_genre_prefs:
            for genre, score in prefs.items():
                aggregated_genres[genre].append(score)
        
        for prefs in all_type_prefs:
            for content_type, score in prefs.items():
                aggregated_types[content_type].append(score)
        
        # Calculate group consensus
        group_genre_prefs = {
            genre: sum(scores) / len(scores)
            for genre, scores in aggregated_genres.items()
        }
        group_type_prefs = {
            content_type: sum(scores) / len(scores)
            for content_type, scores in aggregated_types.items()
        }
        
        profile.set_genre_preferences(group_genre_prefs)
        profile.set_content_type_preferences(group_type_prefs)
        profile.member_count = len(members)
        profile.confidence_score = min(1.0, len(members) / 10)
        profile.last_updated = datetime.utcnow()
    
    def _content_based_filtering(self, profile, limit: int) -> List[Tuple]:
        """Content-based filtering using user/group preferences"""
        genre_prefs = profile.get_genre_preferences()
        type_prefs = profile.get_content_type_preferences()
        
        # If no preferences are available, provide popular content as fallback
        if not genre_prefs and not type_prefs:
            return self._get_popular_content_fallback(profile, limit)
        
        # Query content
        content_query = Content.query.filter_by(status='active')
        
        # Apply preference filters if available
        if hasattr(profile, 'get_rating_range'):
            min_rating, max_rating = profile.get_rating_range()
            content_query = content_query.filter(
                and_(Content.rating >= min_rating, Content.rating <= max_rating)
            )
        
        if hasattr(profile, 'get_year_range'):
            min_year, max_year = profile.get_year_range()
            content_query = content_query.filter(
                and_(Content.year >= min_year, Content.year <= max_year)
            )
        
        content_items = content_query.all()
        scored_content = []
        
        for content in content_items:
            score = self._calculate_content_score(content, genre_prefs, type_prefs)
            if score > 0:
                reasoning = self._generate_content_reasoning(content, genre_prefs, type_prefs)
                scored_content.append((content, score, reasoning))
        
        # Sort by score and return top items
        scored_content.sort(key=lambda x: x[1], reverse=True)
        return scored_content[:limit]
    
    def _collaborative_filtering(self, profile, limit: int) -> List[Tuple]:
        """Collaborative filtering based on similar users"""
        if isinstance(profile, GroupPreferenceProfile):
            # For groups, find similar groups or aggregate member similarities
            return self._group_collaborative_filtering(profile, limit)
        
        user_id = profile.user_id
        
        # Find users with similar rating patterns
        user_ratings = ContentRating.query.filter_by(user_id=user_id).all()
        if not user_ratings:
            return []
        
        user_content_ratings = {r.content_id: r.rating for r in user_ratings}
        similar_users = self._find_similar_users(user_id, user_content_ratings)
        
        # Get recommendations from similar users
        recommendations = defaultdict(list)
        
        for similar_user_id, similarity in similar_users[:20]:  # Top 20 similar users
            similar_user_ratings = ContentRating.query.filter_by(
                user_id=similar_user_id
            ).filter(
                ContentRating.rating >= 4  # Only high ratings
            ).all()
            
            for rating in similar_user_ratings:
                if rating.content_id not in user_content_ratings:
                    # Weight by similarity and rating
                    score = similarity * (rating.rating / 5.0)
                    recommendations[rating.content_id].append(score)
        
        # Average scores and get content
        scored_content = []
        for content_id, scores in recommendations.items():
            avg_score = sum(scores) / len(scores)
            content = Content.query.get(content_id)
            if content:
                reasoning = f"Recommended based on {len(scores)} similar users"
                scored_content.append((content, avg_score, reasoning))
        
        scored_content.sort(key=lambda x: x[1], reverse=True)
        return scored_content[:limit]
    
    def _hybrid_filtering(self, profile, limit: int) -> List[Tuple]:
        """Hybrid approach combining content-based and collaborative filtering"""
        content_recs = self._content_based_filtering(profile, limit)
        collab_recs = self._collaborative_filtering(profile, limit)
        
        # If both methods return empty results, fall back to trending
        if not content_recs and not collab_recs:
            return self._trending_content(profile, limit)
        
        # If only one method has results, use that with full weight
        if not content_recs:
            return collab_recs[:limit]
        if not collab_recs:
            return content_recs[:limit]
        
        # Combine recommendations with weights
        content_weight = 0.6
        collab_weight = 0.4
        
        combined_scores = defaultdict(list)
        
        # Add content-based scores
        for content, score, reasoning in content_recs:
            combined_scores[content.id].append({
                'content': content,
                'score': score * content_weight,
                'reasoning': f"Content-based: {reasoning}"
            })
        
        # Add collaborative scores
        for content, score, reasoning in collab_recs:
            if content.id in combined_scores:
                combined_scores[content.id].append({
                    'content': content,
                    'score': score * collab_weight,
                    'reasoning': f"Collaborative: {reasoning}"
                })
            else:
                combined_scores[content.id].append({
                    'content': content,
                    'score': score * collab_weight,
                    'reasoning': f"Collaborative: {reasoning}"
                })
        
        # Calculate final scores
        final_recommendations = []
        for content_id, score_data in combined_scores.items():
            total_score = sum(item['score'] for item in score_data)
            content = score_data[0]['content']
            
            # Combine reasoning
            reasons = [item['reasoning'] for item in score_data]
            combined_reasoning = " + ".join(reasons)
            
            final_recommendations.append((content, total_score, combined_reasoning))
        
        final_recommendations.sort(key=lambda x: x[1], reverse=True)
        return final_recommendations[:limit]
    
    def _trending_content(self, profile, limit: int) -> List[Tuple]:
        """Recommend trending content based on recent ratings and watchlist additions"""
        # Calculate trending score based on recent activity
        recent_cutoff = datetime.utcnow() - timedelta(days=30)
        
        # Get content with recent ratings
        trending_query = db.session.query(
            Content,
            func.count(ContentRating.id).label('rating_count'),
            func.avg(ContentRating.rating).label('avg_rating'),
            func.count(UserWatchlist.id).label('watchlist_count')
        ).outerjoin(
            ContentRating,
            and_(ContentRating.content_id == Content.id,
                 ContentRating.created_at >= recent_cutoff)
        ).outerjoin(
            UserWatchlist,
            and_(UserWatchlist.content_id == Content.id,
                 UserWatchlist.added_at >= recent_cutoff)
        ).group_by(Content.id).having(
            or_(func.count(ContentRating.id) > 0,
                func.count(UserWatchlist.id) > 0)
        ).all()
        
        scored_content = []
        for content, rating_count, avg_rating, watchlist_count in trending_query:
            # Calculate trending score
            rating_score = (rating_count or 0) * (avg_rating or 0) / 5.0
            watchlist_score = (watchlist_count or 0) * 0.5
            trending_score = rating_score + watchlist_score
            
            reasoning = f"Trending: {rating_count or 0} recent ratings, {watchlist_count or 0} watchlist adds"
            scored_content.append((content, trending_score, reasoning))
        
        scored_content.sort(key=lambda x: x[1], reverse=True)
        return scored_content[:limit]
    
    def _get_popular_content_fallback(self, profile, limit: int) -> List[Tuple]:
        """Fallback recommendations for users with no preference data"""
        # Get highly-rated, popular content for new users
        content_query = Content.query.filter_by(status='active')
        
        # Filter by rating if available
        if hasattr(profile, 'get_rating_range'):
            min_rating, max_rating = profile.get_rating_range()
            content_query = content_query.filter(
                and_(Content.rating >= min_rating, Content.rating <= max_rating)
            )
        else:
            # Default to well-rated content (7.0+)
            content_query = content_query.filter(Content.rating >= 7.0)
        
        # Order by rating and popularity
        content_items = content_query.order_by(
            desc(Content.rating)
        ).limit(limit * 2).all()  # Get more items to have variety
        
        scored_content = []
        for content in content_items:
            # Base score on rating
            score = (content.rating or 0)
            reasoning = f"Popular choice: High rating ({content.rating}/10)"
            scored_content.append((content, score, reasoning))
        
        # Add some variety by shuffling highly-scored items
        import random
        random.shuffle(scored_content)
        return scored_content[:limit]

    def _group_consensus_filtering(self, profile: GroupPreferenceProfile, limit: int) -> List[Tuple]:
        """Recommend content that would appeal to the group consensus"""
        group = profile.group
        members = GroupMember.query.filter_by(group_id=group.id).all()
        
        if not members:
            return []
        
        # Get all member preferences
        member_profiles = []
        for member in members:
            user_profile = self._get_or_create_user_profile(member.user_id)
            member_profiles.append(user_profile)
        
        # Find content that would score well for most members
        content_items = Content.query.filter_by(status='active').all()
        consensus_recommendations = []
        
        for content in content_items:
            member_scores = []
            
            for user_profile in member_profiles:
                genre_prefs = user_profile.get_genre_preferences()
                type_prefs = user_profile.get_content_type_preferences()
                score = self._calculate_content_score(content, genre_prefs, type_prefs)
                member_scores.append(score)
            
            if member_scores:
                # Calculate consensus metrics
                avg_score = sum(member_scores) / len(member_scores)
                min_score = min(member_scores)
                disagreement = max(member_scores) - min_score
                
                # Consensus score favors content with high average and low disagreement
                consensus_score = avg_score * (1 - disagreement / 5.0) * min_score
                
                if consensus_score > 0:
                    reasoning = f"Group consensus: avg {avg_score:.2f}, min {min_score:.2f}"
                    consensus_recommendations.append((content, consensus_score, reasoning))
        
        consensus_recommendations.sort(key=lambda x: x[1], reverse=True)
        return consensus_recommendations[:limit]
    
    def _calculate_content_score(self, content: Content, genre_prefs: Dict, type_prefs: Dict) -> float:
        """Calculate content score based on preferences"""
        score = 0.0
        
        # Genre matching
        content_genres = content.get_genres()
        if content_genres and genre_prefs:
            genre_scores = [genre_prefs.get(genre, 0) for genre in content_genres]
            if genre_scores:
                score += max(genre_scores) * 0.6  # Use best matching genre
        
        # Content type matching
        if content.type in type_prefs:
            score += type_prefs[content.type] * 0.3
        
        # Quality boost for high-rated content
        if content.rating:
            score += (content.rating / 10.0) * 0.1
        
        return score
    
    def _generate_content_reasoning(self, content: Content, genre_prefs: Dict, type_prefs: Dict) -> str:
        """Generate human-readable reasoning for recommendation"""
        reasons = []
        
        content_genres = content.get_genres()
        if content_genres and genre_prefs:
            matching_genres = [g for g in content_genres if g in genre_prefs and genre_prefs[g] > 0.5]
            if matching_genres:
                reasons.append(f"matches your interest in {', '.join(matching_genres)}")
        
        if content.type in type_prefs and type_prefs[content.type] > 0.5:
            reasons.append(f"you enjoy {content.type}s")
        
        if content.rating and content.rating >= 7.0:
            reasons.append(f"highly rated ({content.rating}/10)")
        
        return "Recommended because " + " and ".join(reasons) if reasons else "Recommended for you"
    
    def _find_similar_users(self, user_id: int, user_ratings: Dict) -> List[Tuple[int, float]]:
        """Find users with similar rating patterns using cosine similarity"""
        if not user_ratings:
            return []
        
        # Get other users who have rated common content
        common_content_ids = list(user_ratings.keys())
        other_ratings = db.session.query(
            ContentRating.user_id,
            ContentRating.content_id,
            ContentRating.rating
        ).filter(
            and_(ContentRating.content_id.in_(common_content_ids),
                 ContentRating.user_id != user_id)
        ).all()
        
        # Group by user
        user_rating_maps = defaultdict(dict)
        for user_id_other, content_id, rating in other_ratings:
            user_rating_maps[user_id_other][content_id] = rating
        
        # Calculate similarities
        similarities = []
        for other_user_id, other_ratings in user_rating_maps.items():
            # Find common content
            common_content = set(user_ratings.keys()) & set(other_ratings.keys())
            if len(common_content) >= 3:  # Need at least 3 common ratings
                similarity = self._cosine_similarity(
                    [user_ratings[cid] for cid in common_content],
                    [other_ratings[cid] for cid in common_content]
                )
                if similarity > 0.1:  # Only consider reasonably similar users
                    similarities.append((other_user_id, similarity))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _filter_recommendations(self, recommendations: List[Tuple], 
                              user_id: int = None, group_id: int = None) -> List[Tuple]:
        """Filter out content user/group has already seen, rated, or has active recommendations for"""
        if not recommendations:
            return []
        
        filtered = []
        seen_content_ids = set()
        
        # Get already rated/watchlisted content
        excluded_content_ids = set()
        
        if user_id:
            # User's ratings and watchlist
            user_ratings = ContentRating.query.filter_by(user_id=user_id).all()
            user_watchlist = UserWatchlist.query.filter_by(user_id=user_id).all()
            
            excluded_content_ids.update(r.content_id for r in user_ratings)
            excluded_content_ids.update(w.content_id for w in user_watchlist)
            
            # Add existing active recommendations to prevent duplicates
            existing_recs = Recommendation.query.filter_by(
                user_id=user_id,
                status='active'
            ).filter(
                Recommendation.expires_at > datetime.utcnow()
            ).all()
            excluded_content_ids.update(r.content_id for r in existing_recs)
        
        if group_id:
            # Group's watchlist
            from models import GroupWatchlist
            group_watchlist = GroupWatchlist.query.filter_by(group_id=group_id).all()
            excluded_content_ids.update(gw.content_id for gw in group_watchlist)
            
            # Add existing active group recommendations to prevent duplicates
            existing_group_recs = Recommendation.query.filter_by(
                group_id=group_id,
                status='active'
            ).filter(
                Recommendation.expires_at > datetime.utcnow()
            ).all()
            excluded_content_ids.update(r.content_id for r in existing_group_recs)
        
        # Filter recommendations and remove duplicates within this batch
        for content, score, reasoning in recommendations:
            if content.id not in excluded_content_ids and content.id not in seen_content_ids:
                filtered.append((content, score, reasoning))
                seen_content_ids.add(content.id)
        
        return filtered
    
    def _update_recommendation_history(self, user_id: int, group_id: int, 
                                     algorithm: str, total_recs: int,
                                     experiment_id: str = None, variant: str = None):
        """Update recommendation history for tracking"""
        history = RecommendationHistory(
            user_id=user_id,
            group_id=group_id,
            algorithm=algorithm,
            total_recommendations=total_recs,
            experiment_id=experiment_id,
            variant=variant
        )
        db.session.add(history)
    
    def _get_popular_content_fallback(self, profile, limit: int) -> List[Tuple]:
        """Fallback recommendations for users with no preference data"""
        # Get highly-rated, popular content for new users
        content_query = Content.query.filter_by(status='active')
        
        # Filter by rating if available
        if hasattr(profile, 'get_rating_range'):
            min_rating, max_rating = profile.get_rating_range()
            content_query = content_query.filter(
                and_(Content.rating >= min_rating, Content.rating <= max_rating)
            )
        else:
            # Default to well-rated content (7.0+)
            content_query = content_query.filter(Content.rating >= 7.0)
        
        # Order by rating and popularity
        content_items = content_query.order_by(
            desc(Content.rating),
            desc(Content.popularity if hasattr(Content, 'popularity') else Content.rating)
        ).limit(limit * 2).all()  # Get more items to have variety
        
        scored_content = []
        for content in content_items:
            # Base score on rating and add small random factor for variety
            base_score = (content.rating or 0) * 0.8
            popularity_score = getattr(content, 'popularity', 5.0) * 0.2
            score = base_score + popularity_score
            
            reasoning = f"Popular choice: High rating ({content.rating}/10)"
            scored_content.append((content, score, reasoning))
        
        # Add some variety by shuffling highly-scored items
        import random
        random.shuffle(scored_content)
        return scored_content[:limit]

    def _group_collaborative_filtering(self, profile: GroupPreferenceProfile, limit: int) -> List[Tuple]:
        """Collaborative filtering for groups based on similar groups"""
        # This is a simplified version - could be enhanced with more sophisticated group similarity
        return []


# Utility functions for recommendation management
def mark_recommendation_feedback(recommendation_id: int, user_id: int, 
                               feedback_type: str, comment: str = None):
    """Record user feedback on a recommendation"""
    # Check if feedback already exists
    existing = RecommendationFeedback.query.filter_by(
        recommendation_id=recommendation_id,
        user_id=user_id
    ).first()
    
    if existing:
        existing.feedback_type = feedback_type
        existing.comment = comment
        existing.created_at = datetime.utcnow()
    else:
        feedback = RecommendationFeedback(
            recommendation_id=recommendation_id,
            user_id=user_id,
            feedback_type=feedback_type,
            comment=comment
        )
        db.session.add(feedback)
    
    db.session.commit()


def update_recommendation_metrics():
    """Update performance metrics for recommendation history"""
    # Get recent recommendation histories that need metric updates
    histories = RecommendationHistory.query.filter(
        RecommendationHistory.updated_at < datetime.utcnow() - timedelta(hours=1)
    ).all()
    
    for history in histories:
        # Get recommendations for this history
        if history.user_id:
            recommendations = Recommendation.query.filter(
                and_(
                    Recommendation.user_id == history.user_id,
                    Recommendation.algorithm == history.algorithm,
                    Recommendation.created_at >= history.generation_date,
                    Recommendation.created_at < history.generation_date + timedelta(hours=1)
                )
            ).all()
        else:
            recommendations = Recommendation.query.filter(
                and_(
                    Recommendation.group_id == history.group_id,
                    Recommendation.algorithm == history.algorithm,
                    Recommendation.created_at >= history.generation_date,
                    Recommendation.created_at < history.generation_date + timedelta(hours=1)
                )
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
    
    db.session.commit()
