from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from models import User, Content, Group, GroupMember
from models.recommendations import (
    Recommendation, RecommendationFeedback, UserPreferenceProfile,
    GroupPreferenceProfile, RecommendationHistory
)
from utils.recommendation_engine import RecommendationEngine, mark_recommendation_feedback
from datetime import datetime, timedelta
import json

recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/recommendations')

# Initialize recommendation engine
rec_engine = RecommendationEngine()


@recommendations_bp.route('/')
@login_required
def index():
    """Main recommendations page"""
    # Get user recommendations
    user_recommendations = Recommendation.query.filter_by(
        user_id=current_user.id,
        status='active'
    ).filter(
        Recommendation.expires_at > datetime.utcnow()
    ).order_by(Recommendation.score.desc()).limit(20).all()
    
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
    
    for group_data in group_recommendations:
        for rec in group_data['recommendations']:
            rec.mark_viewed()
    
    db.session.commit()
    
    return render_template('recommendations/index.html',
                         user_recommendations=user_recommendations,
                         group_recommendations=group_recommendations)


@recommendations_bp.route('/generate')
@login_required
def generate_recommendations():
    """Generate new recommendations for current user"""
    algorithm = request.args.get('algorithm', 'hybrid')
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
    data = request.get_json()
    recommendation_id = data.get('recommendation_id')
    feedback_type = data.get('feedback_type')  # like, dislike, not_interested, already_seen
    comment = data.get('comment', '')
    
    if not recommendation_id or not feedback_type:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Verify recommendation exists and user has access
    recommendation = Recommendation.query.get(recommendation_id)
    if not recommendation:
        return jsonify({'error': 'Recommendation not found'}), 404
    
    # Check if user has access to this recommendation
    if recommendation.user_id != current_user.id:
        # Check if it's a group recommendation and user is in the group
        if recommendation.group_id:
            membership = GroupMember.query.filter_by(
                user_id=current_user.id,
                group_id=recommendation.group_id
            ).first()
            if not membership:
                return jsonify({'error': 'Access denied'}), 403
        else:
            return jsonify({'error': 'Access denied'}), 403
    
    try:
        mark_recommendation_feedback(recommendation_id, current_user.id, feedback_type, comment)
        
        # Mark recommendation as clicked
        recommendation.mark_clicked()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Feedback recorded'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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


# Error handlers
@recommendations_bp.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404


@recommendations_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500
