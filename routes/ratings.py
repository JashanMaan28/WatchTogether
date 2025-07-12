from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app import db
from models import ContentRating, Content, GroupRating, ReviewHelpfulnessVote, RatingStatistics, Group, GroupMember
from sqlalchemy import and_, desc, func
from datetime import datetime

# Flash message constants
INVALID_RATING_MSG = 'Please provide a valid rating between 1 and 5 stars.'
RATING_UPDATED_MSG = 'Your rating has been updated!'
RATING_SAVED_MSG = 'Your rating has been saved!'
RATING_ERROR_MSG = 'An error occurred while saving your rating.'
RATING_DELETED_MSG = 'Your rating has been deleted.'
DELETE_ERROR_MSG = 'An error occurred while deleting your rating.'
PERMISSION_ERROR_MSG = 'You can only edit your own ratings.'
DELETE_PERMISSION_ERROR_MSG = 'You can only delete your own ratings.'
GROUP_MEMBER_ERROR_MSG = 'You are not a member of this group.'

ratings_bp = Blueprint('ratings', __name__)

@ratings_bp.route('/content/<int:content_id>/rate', methods=['GET', 'POST'])
@login_required
def rate_content(content_id):
    """Rate and review content"""
    content = Content.query.get_or_404(content_id)
    existing_rating = ContentRating.query.filter_by(
        user_id=current_user.id,
        content_id=content_id
    ).first()
    
    if request.method == 'POST':
        rating_value = request.form.get('rating', type=int)
        review_text = request.form.get('review_text', '').strip()
        is_spoiler = bool(request.form.get('is_spoiler'))
        is_public = bool(request.form.get('is_public', True))
        
        # Validate rating
        if not rating_value or rating_value < 1 or rating_value > 5:
            flash(INVALID_RATING_MSG, 'error')
            return redirect(url_for('ratings.rate_content', content_id=content_id))
        
        try:
            if existing_rating:
                # Update existing rating
                existing_rating.rating = rating_value
                existing_rating.review_text = review_text if review_text else None
                existing_rating.is_spoiler = is_spoiler
                existing_rating.is_public = is_public
                existing_rating.updated_at = datetime.utcnow()
                flash(RATING_UPDATED_MSG, 'success')
            else:
                # Create new rating
                new_rating = ContentRating(
                    user_id=current_user.id,
                    content_id=content_id,
                    rating=rating_value,
                    review_text=review_text if review_text else None,
                    is_spoiler=is_spoiler,
                    is_public=is_public
                )
                db.session.add(new_rating)
                flash(RATING_SAVED_MSG, 'success')
            
            db.session.commit()
            
            # Update statistics
            content.update_rating_statistics()
            
            # Update group ratings for groups this user belongs to
            update_group_ratings_for_content(content_id, current_user.id)
            
            return redirect(url_for('content.detail', tmdb_id=content.tmdb_id, content_type=content.type))
            
        except Exception as e:
            db.session.rollback()
            flash(RATING_ERROR_MSG, 'error')
            return redirect(url_for('ratings.rate_content', content_id=content_id))
    
    return render_template('ratings/rate_content.html', 
                         content=content, 
                         existing_rating=existing_rating)

@ratings_bp.route('/content/<int:content_id>/reviews')
def view_reviews(content_id):
    """View all reviews for content"""
    content = Content.query.get_or_404(content_id)
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', 'newest')  # newest, oldest, helpful, rating_high, rating_low
    
    # Base query for public reviews
    query = ContentRating.query.filter_by(
        content_id=content_id,
        is_public=True
    ).filter(ContentRating.review_text.isnot(None))
    
    # Apply sorting
    if sort_by == 'oldest':
        query = query.order_by(ContentRating.created_at.asc())
    elif sort_by == 'helpful':
        query = query.order_by(desc(ContentRating.helpful_votes))
    elif sort_by == 'rating_high':
        query = query.order_by(desc(ContentRating.rating))
    elif sort_by == 'rating_low':
        query = query.order_by(ContentRating.rating.asc())
    else:  # newest
        query = query.order_by(desc(ContentRating.created_at))
    
    reviews = query.paginate(
        page=page, 
        per_page=10, 
        error_out=False
    )
    
    # Get user's votes on these reviews
    user_votes = {}
    if current_user.is_authenticated:
        review_ids = [review.id for review in reviews.items]
        votes = ReviewHelpfulnessVote.query.filter(
            and_(
                ReviewHelpfulnessVote.rating_id.in_(review_ids),
                ReviewHelpfulnessVote.user_id == current_user.id
            )
        ).all()
        user_votes = {vote.rating_id: vote.is_helpful for vote in votes}
    
    return render_template('ratings/reviews.html',
                         content=content,
                         reviews=reviews,
                         user_votes=user_votes,
                         sort_by=sort_by)

@ratings_bp.route('/rating/<int:rating_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_rating(rating_id):
    """Edit user's own rating"""
    rating = ContentRating.query.get_or_404(rating_id)
    
    if not rating.can_edit(current_user):
        flash(PERMISSION_ERROR_MSG, 'error')
        return redirect(url_for('content.detail', tmdb_id=rating.content_ref.tmdb_id, content_type=rating.content_ref.type))
    
    if request.method == 'POST':
        rating_value = request.form.get('rating', type=int)
        review_text = request.form.get('review_text', '').strip()
        is_spoiler = bool(request.form.get('is_spoiler'))
        is_public = bool(request.form.get('is_public', True))
        
        if not rating_value or rating_value < 1 or rating_value > 5:
            flash(INVALID_RATING_MSG, 'error')
            return render_template('ratings/edit_rating.html', rating=rating)
        
        try:
            rating.rating = rating_value
            rating.review_text = review_text if review_text else None
            rating.is_spoiler = is_spoiler
            rating.is_public = is_public
            rating.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Update statistics
            rating.content.update_rating_statistics()
            
            # Update group ratings
            update_group_ratings_for_content(rating.content_id, current_user.id)
            
            flash(RATING_UPDATED_MSG, 'success')
            return redirect(url_for('content.detail', tmdb_id=rating.content_ref.tmdb_id, content_type=rating.content_ref.type))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your rating.', 'error')
    
    return render_template('ratings/edit_rating.html', rating=rating)

@ratings_bp.route('/rating/<int:rating_id>/delete', methods=['POST'])
@login_required
def delete_rating(rating_id):
    """Delete user's own rating"""
    rating = ContentRating.query.get_or_404(rating_id)
    
    if not rating.can_edit(current_user):
        flash(DELETE_PERMISSION_ERROR_MSG, 'error')
        return redirect(url_for('content.detail', tmdb_id=rating.content_ref.tmdb_id, content_type=rating.content_ref.type))
    
    try:
        content_id = rating.content_id
        db.session.delete(rating)
        db.session.commit()
        
        # Update statistics
        content = Content.query.get(content_id)
        content.update_rating_statistics()
        
        # Update group ratings
        update_group_ratings_for_content(content_id, current_user.id)
        
        flash(RATING_DELETED_MSG, 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(DELETE_ERROR_MSG, 'error')
    
    return redirect(url_for('content.detail', tmdb_id=content.tmdb_id, content_type=content.type))

@ratings_bp.route('/review/<int:rating_id>/vote', methods=['POST'])
@login_required
def vote_review_helpfulness(rating_id):
    """Vote on review helpfulness"""
    rating = ContentRating.query.get_or_404(rating_id)
    
    # Users can't vote on their own reviews
    if rating.user_id == current_user.id:
        return jsonify({'error': 'Cannot vote on your own review'}), 400
    
    is_helpful = request.json.get('is_helpful')
    if is_helpful is None:
        return jsonify({'error': 'Invalid vote'}), 400
    
    try:
        # Check for existing vote
        existing_vote = ReviewHelpfulnessVote.query.filter_by(
            rating_id=rating_id,
            user_id=current_user.id
        ).first()
        
        if existing_vote:
            # Update existing vote
            old_helpful = existing_vote.is_helpful
            existing_vote.is_helpful = is_helpful
            existing_vote.updated_at = datetime.utcnow()
            
            # Update counters
            if old_helpful != is_helpful:
                if is_helpful:
                    rating.helpful_votes += 1
                else:
                    rating.helpful_votes -= 1
        else:
            # Create new vote
            new_vote = ReviewHelpfulnessVote(
                rating_id=rating_id,
                user_id=current_user.id,
                is_helpful=is_helpful
            )
            db.session.add(new_vote)
            
            # Update counters
            rating.total_votes += 1
            if is_helpful:
                rating.helpful_votes += 1
        
        db.session.commit()
        
        return jsonify({
            'helpful_votes': rating.helpful_votes,
            'total_votes': rating.total_votes,
            'helpfulness_percentage': rating.get_helpfulness_percentage()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An error occurred while voting'}), 500

@ratings_bp.route('/group/<int:group_id>/content/<int:content_id>/rating')
@login_required
def view_group_rating(group_id, content_id):
    """View group consensus rating for content"""
    group = Group.query.get_or_404(group_id)
    content = Content.query.get_or_404(content_id)
    
    # Check if user is a group member
    membership = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=current_user.id,
        status='active'
    ).first()
    
    if not membership:
        flash(GROUP_MEMBER_ERROR_MSG, 'error')
        return redirect(url_for('groups.view', group_id=group_id))
    
    # Get or create group rating
    group_rating = GroupRating.query.filter_by(
        group_id=group_id,
        content_id=content_id
    ).first()
    
    if not group_rating:
        group_rating = GroupRating(
            group_id=group_id,
            content_id=content_id
        )
        db.session.add(group_rating)
        db.session.commit()
    
    # Calculate current group rating
    group_rating.calculate_group_rating()
    db.session.commit()
    
    # Get individual ratings from group members
    member_ids = [member.user_id for member in group.members if member.status == 'active']
    member_ratings = ContentRating.query.filter(
        and_(
            ContentRating.content_id == content_id,
            ContentRating.user_id.in_(member_ids),
            ContentRating.is_public == True
        )
    ).all()
    
    return render_template('ratings/group_rating.html',
                         group=group,
                         content=content,
                         group_rating=group_rating,
                         member_ratings=member_ratings)

@ratings_bp.route('/api/content/<int:content_id>/statistics')
def get_rating_statistics(content_id):
    """API endpoint for rating statistics"""
    content = Content.query.get_or_404(content_id)
    stats = content.rating_statistics
    
    if not stats:
        stats = RatingStatistics.get_or_create_for_content(content_id)
        stats.update_statistics()
        db.session.commit()
    
    return jsonify(stats.to_dict())

def update_group_ratings_for_content(content_id, user_id):
    """Update group ratings when a user rates content"""
    # Get all groups the user belongs to
    user_groups = GroupMember.query.filter_by(
        user_id=user_id,
        status='active'
    ).all()
    
    for membership in user_groups:
        # Get or create group rating
        group_rating = GroupRating.query.filter_by(
            group_id=membership.group_id,
            content_id=content_id
        ).first()
        
        if not group_rating:
            group_rating = GroupRating(
                group_id=membership.group_id,
                content_id=content_id
            )
            db.session.add(group_rating)
        
        # Recalculate group rating
        group_rating.calculate_group_rating()
    
    db.session.commit()
