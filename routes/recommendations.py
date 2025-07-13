from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from app import db
from models import User, Content, Group, GroupMember, Friendship
from models.recommendations import (
    Recommendation, RecommendationFeedback, UserPreferenceProfile,
    GroupPreferenceProfile, RecommendationHistory, FriendRecommendation,
    GroupRecommendationSession, GroupRecommendationVote, TrendingContent,
    RecommendationShare, SocialRecommendationInsight, SocialRecommendationSignal
)
from utils.recommendation_engine import RecommendationEngine, mark_recommendation_feedback
from utils.social_analytics import SocialRecommendationAnalytics
from datetime import datetime, timedelta
import json

recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/recommendations')

# Initialize recommendation engine and analytics
rec_engine = RecommendationEngine()
social_analytics = SocialRecommendationAnalytics()


# Helper function to create social signals
def create_social_signal_from_rating(user_id, content_id, rating):
    """Create social signals when user rates content"""
    user = User.query.get(user_id)
    friends = user.get_friends()
    
    signal_type = 'friend_liked' if rating >= 4 else 'friend_watched'
    signal_strength = min(1.0, rating / 5.0)
    
    # Create signals for all friends
    for friend in friends:
        rec_engine.create_social_signal(
            user_id=friend.id,
            content_id=content_id,
            signal_type=signal_type,
            source_user_id=user_id,
            signal_strength=signal_strength,
            context_data={'rating': rating, 'timestamp': datetime.utcnow().isoformat()}
        )
    
    # Create signals for group members
    user_groups = GroupMember.query.filter_by(user_id=user_id).all()
    for membership in user_groups:
        group_members = GroupMember.query.filter_by(group_id=membership.group_id).all()
        for member in group_members:
            if member.user_id != user_id:  # Don't signal to self
                rec_engine.create_social_signal(
                    user_id=member.user_id,
                    content_id=content_id,
                    signal_type=signal_type,
                    source_user_id=user_id,
                    signal_strength=signal_strength * 0.7,  # Slightly lower weight for group signals
                    context_data={
                        'rating': rating, 
                        'group_id': membership.group_id,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                )


@recommendations_bp.route('/')
@login_required
def index():
    """Main recommendations page with social features"""
    # Get user recommendations
    user_recommendations = Recommendation.query.filter_by(
        user_id=current_user.id,
        status='active'
    ).filter(
        Recommendation.expires_at > datetime.utcnow()
    ).order_by(Recommendation.score.desc()).limit(20).all()
    
    # Get friend recommendations
    friend_recommendations = FriendRecommendation.query.filter_by(
        friend_id=current_user.id,
        status='sent'
    ).order_by(FriendRecommendation.created_at.desc()).limit(10).all()
    
    # Get social insights
    social_insights = SocialRecommendationInsight.query.filter_by(
        user_id=current_user.id,
        status='active'
    ).filter(
        or_(
            SocialRecommendationInsight.expires_at.is_(None),
            SocialRecommendationInsight.expires_at > datetime.utcnow()
        )
    ).order_by(SocialRecommendationInsight.importance_score.desc()).limit(5).all()
    
    # Get trending content in friend circle
    friends = current_user.get_friends()
    friend_trending = []
    if friends:
        friend_trending = TrendingContent.query.filter_by(
            scope='friends'
        ).filter(
            TrendingContent.period_end >= datetime.utcnow() - timedelta(days=3)
        ).order_by(TrendingContent.trending_score.desc()).limit(5).all()
    
    # Get group recommendations for user's groups
    user_groups = GroupMember.query.filter_by(user_id=current_user.id).all()
    group_recommendations = []
    
    for membership in user_groups:
        group_recs = Recommendation.query.filter_by(
            group_id=membership.group_id,
            status='active'
        ).filter(
            Recommendation.expires_at > datetime.utcnow()
        ).order_by(Recommendation.score.desc()).limit(5).all()
        
        if group_recs:
            group_recommendations.append({
                'group': membership.group,
                'recommendations': group_recs
            })
    
    # Mark recommendations as viewed
    for rec in user_recommendations:
        rec.mark_viewed()
    
    for friend_rec in friend_recommendations:
        friend_rec.mark_viewed()
    
    for group_data in group_recommendations:
        for rec in group_data['recommendations']:
            rec.mark_viewed()
    
    for insight in social_insights:
        insight.mark_viewed()
    
    db.session.commit()
    
    return render_template('recommendations/index.html',
                         user_recommendations=user_recommendations,
                         friend_recommendations=friend_recommendations,
                         social_insights=social_insights,
                         friend_trending=friend_trending,
                         group_recommendations=group_recommendations)


@recommendations_bp.route('/generate')
@login_required
def generate_recommendations():
    """Generate new recommendations for current user"""
    algorithm = request.args.get('algorithm', 'social_hybrid')  # Default to social hybrid
    limit = int(request.args.get('limit', 10))
    force = request.args.get('force', 'false').lower() == 'true'
    
    try:
        # Check if we should generate new recommendations
        if not force and not rec_engine._should_generate_new_recommendations(user_id=current_user.id):
            flash('Recent recommendations are still available. Use "force=true" to generate new ones.', 'info')
            return redirect(url_for('recommendations.index'))
        
        recommendations = rec_engine.generate_recommendations(
            user_id=current_user.id,
            algorithm=algorithm,
            limit=limit
        )
        flash(f'Generated {len(recommendations)} new recommendations using {algorithm} algorithm!', 'success')
    except Exception as e:
        flash(f'Error generating recommendations: {str(e)}', 'error')
    
    return redirect(url_for('recommendations.index'))


@recommendations_bp.route('/group/<int:group_id>/generate')
@login_required
def generate_group_recommendations(group_id):
    """Generate recommendations for a group"""
    # Check if user is member of the group
    membership = GroupMember.query.filter_by(
        user_id=current_user.id,
        group_id=group_id
    ).first()
    
    if not membership:
        flash('You are not a member of this group.', 'error')
        return redirect(url_for('recommendations.index'))
    
    algorithm = request.args.get('algorithm', 'group_consensus')
    limit = int(request.args.get('limit', 10))
    force = request.args.get('force', 'false').lower() == 'true'
    
    try:
        # Check if we should generate new recommendations
        if not force and not rec_engine._should_generate_new_recommendations(group_id=group_id):
            flash('Recent group recommendations are still available. Use "force=true" to generate new ones.', 'info')
            return redirect(url_for('groups.view', id=group_id))
        
        recommendations = rec_engine.generate_recommendations(
            group_id=group_id,
            algorithm=algorithm,
            limit=limit
        )
        flash(f'Generated {len(recommendations)} new group recommendations!', 'success')
    except Exception as e:
        flash(f'Error generating group recommendations: {str(e)}', 'error')
    
    return redirect(url_for('groups.view', id=group_id))


@recommendations_bp.route('/feedback', methods=['POST'])
@login_required
def submit_feedback():
    """Submit feedback on a recommendation"""
    try:
        # Validate CSRF token for JSON requests
        from flask_wtf.csrf import validate_csrf
        csrf_token = request.headers.get('X-CSRF-Token')
        
        if not csrf_token:
            return jsonify({'success': False, 'error': 'CSRF token missing'}), 400
        
        validate_csrf(csrf_token)
        
        # Get and validate JSON data
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data received'}), 400
        
        recommendation_id = data.get('recommendation_id')
        feedback_type = data.get('feedback_type')
        comment = data.get('comment', '')
        
        if not recommendation_id or not feedback_type:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Validate feedback type
        valid_feedback_types = ['like', 'dislike', 'not_interested', 'already_seen', 'clicked']
        if feedback_type not in valid_feedback_types:
            return jsonify({'success': False, 'error': 'Invalid feedback type'}), 400
        
        # Get and verify recommendation
        recommendation = Recommendation.query.get(recommendation_id)
        if not recommendation:
            return jsonify({'success': False, 'error': 'Recommendation not found'}), 404
        
        # Check user access to recommendation
        has_access = False
        if recommendation.user_id == current_user.id:
            has_access = True
        elif recommendation.group_id:
            membership = GroupMember.query.filter_by(
                user_id=current_user.id,
                group_id=recommendation.group_id
            ).first()
            has_access = membership is not None
        
        if not has_access:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Record feedback using the utility function
        mark_recommendation_feedback(recommendation_id, current_user.id, feedback_type, comment)
        
        # Mark recommendation as clicked if it's a click tracking
        if feedback_type == 'clicked':
            recommendation.mark_clicked()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Feedback recorded successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in submit_feedback: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@recommendations_bp.route('/dismiss/<int:recommendation_id>')
@login_required
def dismiss_recommendation(recommendation_id):
    """Dismiss a recommendation"""
    recommendation = Recommendation.query.get_or_404(recommendation_id)
    
    # Check access
    if recommendation.user_id != current_user.id:
        if recommendation.group_id:
            membership = GroupMember.query.filter_by(
                user_id=current_user.id,
                group_id=recommendation.group_id
            ).first()
            if not membership:
                flash('Access denied.', 'error')
                return redirect(url_for('recommendations.index'))
        else:
            flash('Access denied.', 'error')
            return redirect(url_for('recommendations.index'))
    
    recommendation.status = 'dismissed'
    db.session.commit()
    
    flash('Recommendation dismissed.', 'info')
    return redirect(url_for('recommendations.index'))


@recommendations_bp.route('/preferences')
@login_required
def preferences():
    """View and edit recommendation preferences"""
    profile = UserPreferenceProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        # Create profile with default values
        profile = UserPreferenceProfile(user_id=current_user.id)
        db.session.add(profile)
        db.session.commit()
    
    return render_template('recommendations/preferences.html', profile=profile)


@recommendations_bp.route('/preferences', methods=['POST'])
@login_required
def update_preferences():
    """Update user recommendation preferences"""
    profile = UserPreferenceProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = UserPreferenceProfile(user_id=current_user.id)
        db.session.add(profile)
    
    # Update preferences from form
    profile.preferred_rating_range = request.form.get('rating_range', '3.0-5.0')
    profile.preferred_year_range = request.form.get('year_range', '2000-2025')
    profile.preferred_duration_range = request.form.get('duration_range', '60-180')
    profile.viewing_frequency = request.form.get('viewing_frequency', 'regular')
    profile.discovery_preference = request.form.get('discovery_preference', 'balanced')
    
    # Handle language preferences
    languages = request.form.getlist('languages')
    profile.set_preferred_languages(languages)
    
    # Handle country preferences
    countries = request.form.getlist('countries')
    profile.set_preferred_countries(countries)
    
    profile.last_updated = datetime.utcnow()
    db.session.commit()
    
    flash('Preferences updated successfully!', 'success')
    return redirect(url_for('recommendations.preferences'))


@recommendations_bp.route('/history')
@login_required
def history():
    """View recommendation history and performance"""
    # Get recommendation history
    history_records = RecommendationHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(RecommendationHistory.generation_date.desc()).limit(20).all()
    
    # Get all recommendations with feedback
    recommendations_with_feedback = db.session.query(
        Recommendation, RecommendationFeedback
    ).outerjoin(
        RecommendationFeedback,
        Recommendation.id == RecommendationFeedback.recommendation_id
    ).filter(
        Recommendation.user_id == current_user.id
    ).order_by(Recommendation.created_at.desc()).limit(50).all()
    
    return render_template('recommendations/history.html',
                         history_records=history_records,
                         recommendations_with_feedback=recommendations_with_feedback)


@recommendations_bp.route('/analytics')
@login_required
def analytics():
    """Analytics dashboard for recommendations (admin/power users)"""
    # Basic analytics for now - could be expanded
    total_recommendations = Recommendation.query.filter_by(user_id=current_user.id).count()
    
    # Feedback distribution
    feedback_stats = db.session.query(
        RecommendationFeedback.feedback_type,
        db.func.count(RecommendationFeedback.id)
    ).join(
        Recommendation
    ).filter(
        Recommendation.user_id == current_user.id
    ).group_by(RecommendationFeedback.feedback_type).all()
    
    # Algorithm performance
    algorithm_stats = db.session.query(
        RecommendationHistory.algorithm,
        db.func.avg(RecommendationHistory.view_rate).label('avg_view_rate'),
        db.func.avg(RecommendationHistory.click_rate).label('avg_click_rate'),
        db.func.avg(RecommendationHistory.like_rate).label('avg_like_rate')
    ).filter(
        RecommendationHistory.user_id == current_user.id
    ).group_by(RecommendationHistory.algorithm).all()
    
    return render_template('recommendations/analytics.html',
                         total_recommendations=total_recommendations,
                         feedback_stats=feedback_stats,
                         algorithm_stats=algorithm_stats)


@recommendations_bp.route('/api/recommendations')
@login_required
def api_recommendations():
    """API endpoint for getting recommendations"""
    algorithm = request.args.get('algorithm', 'hybrid')
    limit = int(request.args.get('limit', 10))
    group_id = request.args.get('group_id', type=int)
    
    try:
        if group_id:
            # Check group membership
            membership = GroupMember.query.filter_by(
                user_id=current_user.id,
                group_id=group_id
            ).first()
            if not membership:
                return jsonify({'error': 'Access denied'}), 403
            
            recommendations = rec_engine.generate_recommendations(
                group_id=group_id,
                algorithm=algorithm,
                limit=limit
            )
        else:
            recommendations = rec_engine.generate_recommendations(
                user_id=current_user.id,
                algorithm=algorithm,
                limit=limit
            )
        
        return jsonify({
            'recommendations': [rec.to_dict() for rec in recommendations],
            'algorithm': algorithm,
            'generated_at': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/friend/recommend', methods=['GET', 'POST'])
@login_required
def recommend_to_friend():
    """Recommend content to a friend"""
    if request.method == 'GET':
        content_id = request.args.get('content_id', type=int)
        friends = current_user.get_friends()
        content = Content.query.get_or_404(content_id) if content_id else None
        
        return render_template('recommendations/recommend_to_friend.html',
                             friends=friends, content=content)
    
    # POST request - send recommendation
    friend_id = request.form.get('friend_id', type=int)
    content_id = request.form.get('content_id', type=int)
    message = request.form.get('message', '').strip()
    rating = request.form.get('rating', type=float)
    tags = request.form.getlist('tags')
    
    if not friend_id or not content_id:
        flash('Friend and content are required.', 'error')
        return redirect(url_for('recommendations.recommend_to_friend'))
    
    # Verify friendship
    if not Friendship.are_friends(current_user.id, friend_id):
        flash('You can only recommend content to your friends.', 'error')
        return redirect(url_for('recommendations.recommend_to_friend'))
    
    # Check if already recommended this content to this friend
    existing = FriendRecommendation.query.filter_by(
        recommender_id=current_user.id,
        friend_id=friend_id,
        content_id=content_id
    ).first()
    
    if existing:
        flash('You have already recommended this content to this friend.', 'info')
        return redirect(url_for('recommendations.recommend_to_friend'))
    
    # Create friend recommendation
    friend_rec = FriendRecommendation(
        recommender_id=current_user.id,
        friend_id=friend_id,
        content_id=content_id,
        message=message,
        rating=rating
    )
    friend_rec.set_tags(tags)
    
    # Create social signal
    rec_engine.create_social_signal(
        user_id=friend_id,
        content_id=content_id,
        signal_type='shared',
        source_user_id=current_user.id,
        signal_strength=0.8,
        context_data={'type': 'friend_recommendation', 'has_message': bool(message)}
    )
    
    db.session.add(friend_rec)
    db.session.commit()
    
    flash('Recommendation sent to your friend!', 'success')
    return redirect(url_for('recommendations.index'))


@recommendations_bp.route('/friend/respond/<int:recommendation_id>', methods=['POST'])
@login_required
def respond_to_friend_recommendation(recommendation_id):
    """Respond to a friend's recommendation"""
    friend_rec = FriendRecommendation.query.get_or_404(recommendation_id)
    
    if friend_rec.friend_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('recommendations.index'))
    
    response_type = request.form.get('response_type')  # like, dismiss, comment
    rating = request.form.get('rating', type=float)
    comment = request.form.get('comment', '').strip()
    
    if response_type == 'like':
        friend_rec.respond(liked=True)
        friend_rec.status = 'liked'
        
        # Create positive social signal
        rec_engine.create_social_signal(
            user_id=current_user.id,
            content_id=friend_rec.content_id,
            signal_type='friend_liked',
            source_user_id=friend_rec.recommender_id,
            signal_strength=1.0
        )
        
        flash('You liked this recommendation!', 'success')
    
    elif response_type == 'dismiss':
        friend_rec.status = 'dismissed'
        flash('Recommendation dismissed.', 'info')
    
    elif response_type == 'comment':
        friend_rec.respond(rating=rating, comment=comment)
        flash('Your response has been recorded.', 'success')
    
    db.session.commit()
    return redirect(url_for('recommendations.index'))


@recommendations_bp.route('/group/session/create/<int:group_id>', methods=['GET', 'POST'])
@login_required
def create_group_session(group_id):
    """Create a group recommendation session"""
    # Check group membership
    membership = GroupMember.query.filter_by(
        user_id=current_user.id,
        group_id=group_id
    ).first()
    
    if not membership:
        flash('You are not a member of this group.', 'error')
        return redirect(url_for('recommendations.index'))
    
    if request.method == 'GET':
        group = Group.query.get_or_404(group_id)
        return render_template('recommendations/create_group_session.html', group=group)
    
    # POST request - create session
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    session_type = request.form.get('session_type', 'collaborative')
    voting_duration = request.form.get('voting_duration', 24, type=int)
    require_consensus = request.form.get('require_consensus') == 'on'
    min_consensus_percentage = request.form.get('min_consensus_percentage', 0.6, type=float)
    
    if not title:
        flash('Session title is required.', 'error')
        return redirect(url_for('recommendations.create_group_session', group_id=group_id))
    
    session = GroupRecommendationSession(
        group_id=group_id,
        host_id=current_user.id,
        title=title,
        description=description,
        session_type=session_type,
        voting_duration=voting_duration,
        require_consensus=require_consensus,
        min_consensus_percentage=min_consensus_percentage
    )
    
    db.session.add(session)
    db.session.commit()
    
    flash('Group recommendation session created!', 'success')
    return redirect(url_for('recommendations.group_session', session_id=session.id))


@recommendations_bp.route('/group/session/<int:session_id>')
@login_required
def group_session(session_id):
    """View and participate in group recommendation session"""
    session = GroupRecommendationSession.query.get_or_404(session_id)
    
    # Check group membership
    membership = GroupMember.query.filter_by(
        user_id=current_user.id,
        group_id=session.group_id
    ).first()
    
    if not membership:
        flash('You are not a member of this group.', 'error')
        return redirect(url_for('recommendations.index'))
    
    # Get session votes
    votes = GroupRecommendationVote.query.filter_by(session_id=session_id).all()
    user_votes = {v.content_id: v for v in votes if v.user_id == current_user.id}
    
    # Get vote summary
    from collections import defaultdict
    vote_summary = defaultdict(lambda: {'total': 0, 'avg_score': 0, 'voters': []})
    
    for vote in votes:
        summary = vote_summary[vote.content_id]
        summary['total'] += vote.score
        summary['voters'].append(vote.user.username)
    
    for content_id, summary in vote_summary.items():
        summary['avg_score'] = summary['total'] / len(summary['voters'])
    
    return render_template('recommendations/group_session.html',
                         session=session, user_votes=user_votes,
                         vote_summary=dict(vote_summary))


@recommendations_bp.route('/group/session/<int:session_id>/vote', methods=['POST'])
@login_required
def vote_in_session(session_id):
    """Vote on content in group session"""
    session = GroupRecommendationSession.query.get_or_404(session_id)
    
    # Check group membership
    membership = GroupMember.query.filter_by(
        user_id=current_user.id,
        group_id=session.group_id
    ).first()
    
    if not membership:
        flash('You are not a member of this group.', 'error')
        return redirect(url_for('recommendations.index'))
    
    content_id = request.form.get('content_id', type=int)
    vote_type = request.form.get('vote_type', 'preference')
    score = request.form.get('score', 1.0, type=float)
    comment = request.form.get('comment', '').strip()
    
    if not content_id:
        flash('Content is required for voting.', 'error')
        return redirect(url_for('recommendations.group_session', session_id=session_id))
    
    # Check if user already voted on this content
    existing_vote = GroupRecommendationVote.query.filter_by(
        session_id=session_id,
        user_id=current_user.id,
        content_id=content_id
    ).first()
    
    if existing_vote:
        # Update existing vote
        existing_vote.vote_type = vote_type
        existing_vote.score = score
        existing_vote.comment = comment
        existing_vote.updated_at = datetime.utcnow()
    else:
        # Create new vote
        vote = GroupRecommendationVote(
            session_id=session_id,
            user_id=current_user.id,
            content_id=content_id,
            vote_type=vote_type,
            score=score,
            comment=comment
        )
        db.session.add(vote)
    
    db.session.commit()
    flash('Your vote has been recorded!', 'success')
    return redirect(url_for('recommendations.group_session', session_id=session_id))


@recommendations_bp.route('/social/trending')
@login_required
def social_trending():
    """View trending content in social circles"""
    scope = request.args.get('scope', 'friends')  # friends, groups, global
    
    if scope == 'friends':
        friends = current_user.get_friends()
        if not friends:
            trending_content = []
        else:
            trending_content = TrendingContent.query.filter_by(
                scope='friends'
            ).filter(
                TrendingContent.period_end >= datetime.utcnow() - timedelta(days=7)
            ).order_by(TrendingContent.trending_score.desc()).limit(20).all()
    
    elif scope == 'groups':
        user_groups = GroupMember.query.filter_by(user_id=current_user.id).all()
        group_ids = [membership.group_id for membership in user_groups]
        
        trending_content = TrendingContent.query.filter_by(
            scope='group'
        ).filter(
            TrendingContent.scope_id.in_(group_ids),
            TrendingContent.period_end >= datetime.utcnow() - timedelta(days=7)
        ).order_by(TrendingContent.trending_score.desc()).limit(20).all()
    
    else:  # global
        trending_content = TrendingContent.query.filter_by(
            scope='global'
        ).filter(
            TrendingContent.period_end >= datetime.utcnow() - timedelta(days=7)
        ).order_by(TrendingContent.trending_score.desc()).limit(20).all()
    
    return render_template('recommendations/social_trending.html',
                         trending_content=trending_content, scope=scope)


@recommendations_bp.route('/social/insights')
@login_required
def social_insights():
    """View social recommendation insights"""
    insights = SocialRecommendationInsight.query.filter_by(
        user_id=current_user.id,
        status='active'
    ).order_by(
        SocialRecommendationInsight.importance_score.desc(),
        SocialRecommendationInsight.created_at.desc()
    ).limit(20).all()
    
    return render_template('recommendations/social_insights.html', insights=insights)


@recommendations_bp.route('/social/insights/<int:insight_id>/dismiss', methods=['POST'])
@login_required
def dismiss_insight(insight_id):
    """Dismiss a social insight"""
    insight = SocialRecommendationInsight.query.get_or_404(insight_id)
    
    if insight.user_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('recommendations.social_insights'))
    
    insight.dismiss()
    db.session.commit()
    
    flash('Insight dismissed.', 'info')
    return redirect(url_for('recommendations.social_insights'))


@recommendations_bp.route('/share/<int:recommendation_id>', methods=['GET', 'POST'])
@login_required
def share_recommendation(recommendation_id):
    """Share a recommendation with friends or groups"""
    recommendation = Recommendation.query.get_or_404(recommendation_id)
    
    # Check access
    if recommendation.user_id != current_user.id:
        if recommendation.group_id:
            membership = GroupMember.query.filter_by(
                user_id=current_user.id,
                group_id=recommendation.group_id
            ).first()
            if not membership:
                flash('Access denied.', 'error')
                return redirect(url_for('recommendations.index'))
        else:
            flash('Access denied.', 'error')
            return redirect(url_for('recommendations.index'))
    
    if request.method == 'GET':
        friends = current_user.get_friends()
        user_groups = GroupMember.query.filter_by(user_id=current_user.id).all()
        groups = [membership.group for membership in user_groups]
        
        return render_template('recommendations/share_recommendation.html',
                             recommendation=recommendation, friends=friends, groups=groups)
    
    # POST request - share recommendation
    share_type = request.form.get('share_type')  # direct, group
    target_user_id = request.form.get('target_user_id', type=int) if share_type == 'direct' else None
    target_group_id = request.form.get('target_group_id', type=int) if share_type == 'group' else None
    message = request.form.get('message', '').strip()
    custom_tags = request.form.getlist('custom_tags')
    
    if share_type == 'direct' and not target_user_id:
        flash('Please select a friend to share with.', 'error')
        return redirect(url_for('recommendations.share_recommendation', recommendation_id=recommendation_id))
    
    if share_type == 'group' and not target_group_id:
        flash('Please select a group to share with.', 'error')
        return redirect(url_for('recommendations.share_recommendation', recommendation_id=recommendation_id))
    
    # Create recommendation share
    share = RecommendationShare(
        recommendation_id=recommendation_id,
        sharer_id=current_user.id,
        share_type=share_type,
        target_user_id=target_user_id,
        target_group_id=target_group_id,
        message=message,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    share.set_custom_tags(custom_tags)
    
    # Create social signals
    if target_user_id:
        rec_engine.create_social_signal(
            user_id=target_user_id,
            content_id=recommendation.content_id,
            signal_type='shared',
            source_user_id=current_user.id,
            signal_strength=0.7
        )
    elif target_group_id:
        # Create signals for all group members
        group_members = GroupMember.query.filter_by(group_id=target_group_id).all()
        for member in group_members:
            if member.user_id != current_user.id:  # Don't signal to yourself
                rec_engine.create_social_signal(
                    user_id=member.user_id,
                    content_id=recommendation.content_id,
                    signal_type='shared',
                    source_user_id=current_user.id,
                    signal_strength=0.5,
                    context_data={'shared_in_group': target_group_id}
                )
    
    db.session.add(share)
    db.session.commit()
    
    flash('Recommendation shared successfully!', 'success')
    return redirect(url_for('recommendations.index'))


@recommendations_bp.route('/api/social-signals', methods=['POST'])
@login_required
def create_social_signal_api():
    """API endpoint to create social signals"""
    data = request.get_json()
    
    content_id = data.get('content_id')
    signal_type = data.get('signal_type', 'friend_liked')
    rating = data.get('rating')
    
    if not content_id:
        return jsonify({'error': 'Content ID is required'}), 400
    
    # Create social signal based on rating if provided
    if rating:
        create_social_signal_from_rating(current_user.id, content_id, rating)
        return jsonify({'success': True, 'message': 'Social signals created from rating'})
    
    # Create manual social signal
    signal_strength = data.get('signal_strength', 1.0)
    context_data = data.get('context_data', {})
    
    rec_engine.create_social_signal(
        user_id=current_user.id,
        content_id=content_id,
        signal_type=signal_type,
        source_user_id=current_user.id,
        signal_strength=signal_strength,
        context_data=context_data
    )
    
    return jsonify({'success': True, 'message': 'Social signal created'})


@recommendations_bp.route('/api/generate-insights')
@login_required
def generate_insights_api():
    """API endpoint to generate fresh insights for current user"""
    try:
        insights = social_analytics.generate_insights_for_user(current_user.id)
        
        # Save new insights
        for insight in insights:
            # Check if similar insight already exists
            existing = SocialRecommendationInsight.query.filter_by(
                user_id=current_user.id,
                insight_type=insight.insight_type,
                status='active'
            ).filter(
                SocialRecommendationInsight.created_at >= datetime.utcnow() - timedelta(hours=6)
            ).first()
            
            if not existing:
                db.session.add(insight)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'insights_generated': len(insights),
            'message': f'Generated {len(insights)} new insights'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/api/trending-update')
@login_required
def update_trending_api():
    """API endpoint to trigger trending content update"""
    try:
        rec_engine.update_trending_content()
        return jsonify({'success': True, 'message': 'Trending content updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@recommendations_bp.route('/api/recommendation-stats/<int:user_id>')
@login_required
def get_recommendation_stats(user_id):
    """Get recommendation statistics for a user (for friends only)"""
    # Check if users are friends or if it's the current user
    if user_id != current_user.id and not Friendship.are_friends(current_user.id, user_id):
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    
    # Get recommendation statistics
    total_sent = FriendRecommendation.query.filter_by(recommender_id=user_id).count()
    total_received = FriendRecommendation.query.filter_by(friend_id=user_id).count()
    
    liked_sent = FriendRecommendation.query.filter_by(
        recommender_id=user_id, status='liked'
    ).count()
    
    accuracy = (liked_sent / total_sent * 100) if total_sent > 0 else 0
    
    # Get algorithm performance
    algorithm_stats = db.session.query(
        Recommendation.algorithm,
        func.count(Recommendation.id).label('count'),
        func.avg(Recommendation.score).label('avg_score')
    ).filter_by(user_id=user_id).group_by(Recommendation.algorithm).all()
    
    # Get recent activity
    recent_recommendations = Recommendation.query.filter_by(
        user_id=user_id
    ).filter(
        Recommendation.created_at >= datetime.utcnow() - timedelta(days=7)
    ).count()
    
    return jsonify({
        'total_sent': total_sent,
        'total_received': total_received,
        'accuracy_percentage': round(accuracy, 1),
        'recent_recommendations': recent_recommendations,
        'algorithm_stats': [
            {
                'algorithm': stat.algorithm,
                'count': stat.count,
                'avg_score': round(stat.avg_score, 2)
            }
            for stat in algorithm_stats
        ]
    })


@recommendations_bp.route('/export')
@login_required
def export_recommendations():
    """Export user's recommendation data"""
    user_recommendations = Recommendation.query.filter_by(
        user_id=current_user.id
    ).order_by(Recommendation.created_at.desc()).limit(100).all()
    
    friend_recommendations = FriendRecommendation.query.filter_by(
        friend_id=current_user.id
    ).order_by(FriendRecommendation.created_at.desc()).limit(50).all()
    
    export_data = {
        'user': {
            'username': current_user.username,
            'export_date': datetime.utcnow().isoformat()
        },
        'personal_recommendations': [
            {
                'content_title': rec.content.title,
                'content_type': rec.content.type,
                'score': rec.score,
                'algorithm': rec.algorithm,
                'reasoning': rec.reasoning,
                'created_at': rec.created_at.isoformat(),
                'status': rec.status
            }
            for rec in user_recommendations
        ],
        'friend_recommendations': [
            {
                'content_title': rec.content.title,
                'content_type': rec.content.type,
                'recommender': rec.recommender.username,
                'message': rec.message,
                'rating': rec.rating,
                'created_at': rec.created_at.isoformat(),
                'status': rec.status
            }
            for rec in friend_recommendations
        ]
    }
    
    response = jsonify(export_data)
    response.headers['Content-Disposition'] = f'attachment; filename=recommendations_export_{current_user.username}_{datetime.utcnow().strftime("%Y%m%d")}.json'
    return response


# Error handlers
@recommendations_bp.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404


@recommendations_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500
