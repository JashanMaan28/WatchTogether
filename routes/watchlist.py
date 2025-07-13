"""
Watchlist routes for personal and group watchlist management
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, desc, asc
from datetime import datetime, date
import json

from app import db
from models import (User, Content, UserWatchlist, GroupWatchlist, Group, GroupMember, 
                   WatchlistShare, GroupWatchlistVote)
from models.recommendations import Recommendation
from forms import (AddToWatchlistForm, UpdateWatchlistForm, AddToGroupWatchlistForm, 
                  ShareWatchlistForm, CreateWatchSessionForm, WatchlistFilterForm)
from utils.recommendation_engine import RecommendationEngine

watchlist_bp = Blueprint('watchlist', __name__, url_prefix='/watchlist')

# Initialize recommendation engine
rec_engine = RecommendationEngine()

# Personal Watchlist Routes

@watchlist_bp.route('/my')
@login_required
def my_watchlist():
    """Display user's personal watchlist"""
    filter_form = WatchlistFilterForm()
    
    # Build query
    query = UserWatchlist.query.filter_by(user_id=current_user.id).join(Content)
    
    # Apply filters
    if request.args.get('status'):
        query = query.filter(UserWatchlist.status == request.args.get('status'))
        filter_form.status.data = request.args.get('status')
    
    if request.args.get('priority'):
        query = query.filter(UserWatchlist.priority == request.args.get('priority'))
        filter_form.priority.data = request.args.get('priority')
    
    if request.args.get('content_type'):
        query = query.filter(Content.type == request.args.get('content_type'))
        filter_form.content_type.data = request.args.get('content_type')
    
    if request.args.get('genre'):
        genre_filter = f"%{request.args.get('genre')}%"
        query = query.filter(Content.genre.like(genre_filter))
        filter_form.genre.data = request.args.get('genre')
    
    # Apply sorting
    sort_by = request.args.get('sort_by', 'added_at_desc')
    filter_form.sort_by.data = sort_by
    
    if sort_by == 'added_at_asc':
        query = query.order_by(asc(UserWatchlist.added_at))
    elif sort_by == 'priority_high':
        priority_order = db.case(
            (UserWatchlist.priority == 'high', 1),
            (UserWatchlist.priority == 'medium', 2),
            (UserWatchlist.priority == 'low', 3),
            else_=4
        )
        query = query.order_by(priority_order)
    elif sort_by == 'priority_low':
        priority_order = db.case(
            (UserWatchlist.priority == 'low', 1),
            (UserWatchlist.priority == 'medium', 2),
            (UserWatchlist.priority == 'high', 3),
            else_=4
        )
        query = query.order_by(priority_order)
    elif sort_by == 'title_asc':
        query = query.order_by(asc(Content.title))
    elif sort_by == 'title_desc':
        query = query.order_by(desc(Content.title))
    elif sort_by == 'rating_desc':
        query = query.order_by(desc(Content.rating))
    elif sort_by == 'year_desc':
        query = query.order_by(desc(Content.year))
    elif sort_by == 'year_asc':
        query = query.order_by(asc(Content.year))
    else:  # added_at_desc (default)
        query = query.order_by(desc(UserWatchlist.added_at))
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    items = query.paginate(page=page, per_page=20, error_out=False)
    
    # Get statistics
    stats = get_watchlist_stats(current_user.id)
    
    # Get personalized recommendations based on watchlist
    user_recommendations = Recommendation.query.filter_by(
        user_id=current_user.id,
        status='active'
    ).filter(
        Recommendation.expires_at > datetime.utcnow()
    ).order_by(Recommendation.score.desc()).limit(6).all()
    
    # If no recent recommendations, generate some
    if not user_recommendations:
        try:
            user_recommendations = rec_engine.generate_recommendations(
                user_id=current_user.id,
                algorithm='hybrid',
                limit=6
            )
        except Exception as e:
            user_recommendations = []
    
    return render_template('watchlist/my_watchlist.html', 
                         items=items, 
                         filter_form=filter_form,
                         stats=stats,
                         recommendations=user_recommendations)


@watchlist_bp.route('/add/<int:content_id>')
@login_required
def add_to_watchlist(content_id):
    """Add content to personal watchlist"""
    content = Content.query.get_or_404(content_id)
    
    # Check if already in watchlist
    existing = UserWatchlist.query.filter_by(
        user_id=current_user.id,
        content_id=content_id
    ).first()
    
    if existing:
        flash('This content is already in your watchlist.', 'info')
        # Safe redirect - check if content has tmdb_id for proper URL
        if content.tmdb_id:
            return redirect(request.referrer or url_for('content.detail', tmdb_id=content.tmdb_id, content_type=content.type))
        else:
            return redirect(request.referrer or url_for('content.index'))
    
    form = AddToWatchlistForm()
    
    if form.validate_on_submit():
        watchlist_item = UserWatchlist(
            user_id=current_user.id,
            content_id=content_id,
            status=form.status.data,
            priority=form.priority.data,
            personal_notes=form.personal_notes.data,
            personal_rating=form.personal_rating.data,
            is_public=form.is_public.data
        )
        
        # Set timestamps based on status
        if form.status.data == 'watching':
            watchlist_item.started_at = datetime.utcnow()
        elif form.status.data == 'completed':
            watchlist_item.started_at = datetime.utcnow()
            watchlist_item.completed_at = datetime.utcnow()
        
        db.session.add(watchlist_item)
        db.session.commit()
        
        flash(f'"{content.title}" has been added to your watchlist!', 'success')
        return redirect(url_for('watchlist.my_watchlist'))
    
    return render_template('watchlist/add_to_watchlist.html', content=content, form=form)


@watchlist_bp.route('/quick-add/<int:content_id>')
@login_required
def quick_add_to_watchlist(content_id):
    """Quick add content to watchlist with default settings"""
    content = Content.query.get_or_404(content_id)
    
    # Check if already in watchlist
    existing = UserWatchlist.query.filter_by(
        user_id=current_user.id,
        content_id=content_id
    ).first()
    
    if existing:
        return jsonify({'success': False, 'message': 'Already in watchlist'})
    
    watchlist_item = UserWatchlist(
        user_id=current_user.id,
        content_id=content_id,
        status='want_to_watch',
        priority='medium',
        is_public=True
    )
    
    db.session.add(watchlist_item)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'"{content.title}" added to watchlist!',
        'watchlist_id': watchlist_item.id
    })


@watchlist_bp.route('/update/<int:watchlist_id>', methods=['GET', 'POST'])
@login_required
def update_watchlist_item(watchlist_id):
    """Update a watchlist item"""
    item = UserWatchlist.query.get_or_404(watchlist_id)
    
    # Check ownership
    if item.user_id != current_user.id:
        abort(403)
    
    form = UpdateWatchlistForm(obj=item)
    
    if form.validate_on_submit():
        old_status = item.status
        
        # Update fields
        item.status = form.status.data
        item.priority = form.priority.data
        item.current_season = form.current_season.data
        item.current_episode = form.current_episode.data
        item.personal_notes = form.personal_notes.data
        item.personal_rating = form.personal_rating.data
        item.is_public = form.is_public.data
        
        # Update timestamps based on status changes
        if form.status.data == 'watching' and old_status == 'want_to_watch':
            item.started_at = datetime.utcnow()
        elif form.status.data == 'completed' and old_status in ['watching', 'want_to_watch']:
            item.completed_at = datetime.utcnow()
            if not item.started_at:
                item.started_at = datetime.utcnow()
        
        # Update episode count if provided
        if form.current_episode.data and item.content_ref.type == 'tv_show':
            if item.total_episodes_watched is None:
                item.total_episodes_watched = form.current_episode.data
            else:
                item.total_episodes_watched = max(item.total_episodes_watched, form.current_episode.data)
        
        db.session.commit()
        flash('Watchlist item updated successfully!', 'success')
        return redirect(url_for('watchlist.my_watchlist'))
    
    return render_template('watchlist/update_item.html', item=item, form=form)


@watchlist_bp.route('/remove/<int:watchlist_id>')
@login_required
def remove_from_watchlist(watchlist_id):
    """Remove item from personal watchlist"""
    item = UserWatchlist.query.get_or_404(watchlist_id)
    
    # Check ownership
    if item.user_id != current_user.id:
        abort(403)
    
    title = item.content_ref.title
    db.session.delete(item)
    db.session.commit()
    
    flash(f'"{title}" has been removed from your watchlist.', 'info')
    return redirect(url_for('watchlist.my_watchlist'))


@watchlist_bp.route('/progress/<int:watchlist_id>')
@login_required
def update_progress(watchlist_id):
    """Update viewing progress for TV shows"""
    item = UserWatchlist.query.get_or_404(watchlist_id)
    
    # Check ownership
    if item.user_id != current_user.id:
        abort(403)
    
    season = request.args.get('season', type=int)
    episode = request.args.get('episode', type=int)
    
    if season:
        item.current_season = season
    if episode:
        item.current_episode = episode
        # Auto-increment total episodes
        if item.total_episodes_watched is None:
            item.total_episodes_watched = 1
        else:
            item.total_episodes_watched += 1
    
    # Auto-update status if starting to watch
    if item.status == 'want_to_watch':
        item.update_status('watching')
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'current_season': item.current_season,
        'current_episode': item.current_episode,
        'total_episodes': item.total_episodes_watched
    })


# Group Watchlist Routes

@watchlist_bp.route('/group/<int:group_id>')
@login_required
def group_watchlist(group_id):
    """Display group watchlist"""
    group = Group.query.get_or_404(group_id)
    
    # Check if user is a member
    if not group.is_member(current_user.id):
        flash('You must be a member of this group to view its watchlist.', 'error')
        return redirect(url_for('groups.view', id=group_id))
    
    # Get watchlist items with sorting
    sort_by = request.args.get('sort_by', 'vote_score')
    
    query = GroupWatchlist.query.filter_by(group_id=group_id).join(Content)
    
    if sort_by == 'added_at':
        query = query.order_by(desc(GroupWatchlist.added_at))
    elif sort_by == 'title':
        query = query.order_by(asc(Content.title))
    elif sort_by == 'priority':
        priority_order = db.case(
            (GroupWatchlist.priority == 'high', 1),
            (GroupWatchlist.priority == 'medium', 2),
            (GroupWatchlist.priority == 'low', 3),
            else_=4
        )
        query = query.order_by(priority_order)
    else:  # vote_score (default)
        query = query.order_by(desc(GroupWatchlist.upvotes - GroupWatchlist.downvotes))
    
    items = query.all()
    
    return render_template('watchlist/group_watchlist.html', group=group, items=items, sort_by=sort_by)


@watchlist_bp.route('/group/<int:group_id>/add/<int:content_id>', methods=['GET', 'POST'])
@login_required
def add_to_group_watchlist(group_id, content_id):
    """Add content to group watchlist"""
    group = Group.query.get_or_404(group_id)
    content = Content.query.get_or_404(content_id)
    
    # Check if user is a member
    if not group.is_member(current_user.id):
        abort(403)
    
    # Check if already in group watchlist
    existing = GroupWatchlist.query.filter_by(
        group_id=group_id,
        content_id=content_id
    ).first()
    
    if existing:
        flash('This content is already in the group watchlist.', 'info')
        return redirect(url_for('watchlist.group_watchlist', group_id=group_id))
    
    form = AddToGroupWatchlistForm()
    
    if form.validate_on_submit():
        watchlist_item = GroupWatchlist(
            group_id=group_id,
            content_id=content_id,
            added_by=current_user.id,
            status=form.status.data,
            priority=form.priority.data,
            description=form.description.data,
            scheduled_for=form.scheduled_for.data
        )
        
        db.session.add(watchlist_item)
        db.session.commit()
        
        flash(f'"{content.title}" has been added to the group watchlist!', 'success')
        return redirect(url_for('watchlist.group_watchlist', group_id=group_id))
    
    return render_template('watchlist/add_to_group.html', group=group, content=content, form=form)


@watchlist_bp.route('/group/vote/<int:item_id>/<vote_type>')
@login_required
def vote_on_group_item(item_id, vote_type):
    """Vote on a group watchlist item"""
    if vote_type not in ['up', 'down']:
        abort(400)
    
    item = GroupWatchlist.query.get_or_404(item_id)
    
    # Check if user is a group member
    if not item.group.is_member(current_user.id):
        abort(403)
    
    # Check for existing vote
    existing_vote = GroupWatchlistVote.query.filter_by(
        group_watchlist_id=item_id,
        user_id=current_user.id
    ).first()
    
    if existing_vote:
        if existing_vote.vote_type == vote_type:
            # Remove vote if clicking same vote
            db.session.delete(existing_vote)
            message = 'Vote removed'
        else:
            # Change vote
            existing_vote.vote_type = vote_type
            existing_vote.updated_at = datetime.utcnow()
            message = f'Vote changed to {vote_type}'
    else:
        # New vote
        vote = GroupWatchlistVote(
            group_watchlist_id=item_id,
            user_id=current_user.id,
            vote_type=vote_type
        )
        db.session.add(vote)
        message = f'Voted {vote_type}'
    
    # Update vote counts
    item.update_vote_counts()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': message,
        'upvotes': item.upvotes,
        'downvotes': item.downvotes,
        'score': item.get_vote_score()
    })


# Watchlist Sharing Routes

@watchlist_bp.route('/share', methods=['GET', 'POST'])
@login_required
def share_watchlist():
    """Share personal watchlist with friends"""
    form = ShareWatchlistForm()
    
    # Populate friend choices
    friends = current_user.get_friends()
    form.friend_id.choices = [(f.id, f.get_full_name() or f.username) for f in friends]
    
    if form.validate_on_submit():
        # Check if already shared with this friend
        existing = WatchlistShare.query.filter_by(
            owner_id=current_user.id,
            shared_with_id=form.friend_id.data
        ).first()
        
        if existing:
            # Update existing share
            existing.share_type = form.share_type.data
            existing.set_shared_statuses(form.shared_statuses.data)
            existing.is_active = True
            message = 'Watchlist sharing updated!'
        else:
            # Create new share
            share = WatchlistShare(
                owner_id=current_user.id,
                shared_with_id=form.friend_id.data,
                share_type=form.share_type.data
            )
            share.set_shared_statuses(form.shared_statuses.data)
            db.session.add(share)
            message = 'Watchlist shared successfully!'
        
        db.session.commit()
        flash(message, 'success')
        return redirect(url_for('watchlist.my_shares'))
    
    return render_template('watchlist/share_watchlist.html', form=form)


@watchlist_bp.route('/my-shares')
@login_required
def my_shares():
    """View and manage watchlist shares"""
    # Watchlists I've shared
    shared_by_me = WatchlistShare.query.filter_by(
        owner_id=current_user.id,
        is_active=True
    ).all()
    
    # Watchlists shared with me
    shared_with_me = WatchlistShare.query.filter_by(
        shared_with_id=current_user.id,
        is_active=True
    ).all()
    
    return render_template('watchlist/my_shares.html', 
                         shared_by_me=shared_by_me,
                         shared_with_me=shared_with_me)


@watchlist_bp.route('/friend/<int:user_id>')
@login_required
def view_friend_watchlist(user_id):
    """View a friend's shared watchlist"""
    friend = User.query.get_or_404(user_id)
    
    # Check if watchlist is shared with current user
    share = WatchlistShare.query.filter_by(
        owner_id=user_id,
        shared_with_id=current_user.id,
        is_active=True
    ).first()
    
    if not share:
        flash('This watchlist is not shared with you.', 'error')
        return redirect(url_for('watchlist.my_watchlist'))
    
    # Get shared statuses
    shared_statuses = share.get_shared_statuses()
    
    # Get watchlist items
    query = UserWatchlist.query.filter(
        UserWatchlist.user_id == user_id,
        UserWatchlist.status.in_(shared_statuses),
        UserWatchlist.is_public == True
    ).join(Content).order_by(desc(UserWatchlist.added_at))
    
    page = request.args.get('page', 1, type=int)
    items = query.paginate(page=page, per_page=20, error_out=False)
    
    return render_template('watchlist/friend_watchlist.html', 
                         friend=friend, 
                         share=share,
                         items=items)


# Watch Sessions Routes (Commented out until WatchSession models are properly imported)

# Utility Functions

def get_watchlist_stats(user_id):
    """Get comprehensive watchlist statistics"""
    watchlist_items = UserWatchlist.query.filter_by(user_id=user_id).all()
    
    stats = {
        'total_items': len(watchlist_items),
        'want_to_watch': 0,
        'watching': 0,
        'completed': 0,
        'on_hold': 0,
        'dropped': 0,
        'by_priority': {'high': 0, 'medium': 0, 'low': 0},
        'by_type': {},
        'total_watch_time': 0,
        'avg_rating': None,
        'completed_this_month': 0,
        'completed_this_year': 0
    }
    
    ratings = []
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    for item in watchlist_items:
        # Status counts
        stats[item.status] = stats.get(item.status, 0) + 1
        
        # Priority counts
        stats['by_priority'][item.priority] += 1
        
        # Type counts
        content_type = item.content_ref.type if item.content_ref else 'unknown'
        stats['by_type'][content_type] = stats['by_type'].get(content_type, 0) + 1
        
        # Watch time
        stats['total_watch_time'] += item.get_time_spent_watching()
        
        # Ratings
        if item.personal_rating:
            ratings.append(item.personal_rating)
        
        # Completion tracking
        if item.completed_at:
            if item.completed_at.month == current_month and item.completed_at.year == current_year:
                stats['completed_this_month'] += 1
            if item.completed_at.year == current_year:
                stats['completed_this_year'] += 1
    
    if ratings:
        stats['avg_rating'] = sum(ratings) / len(ratings)
    
    return stats


# API Routes for AJAX

@watchlist_bp.route('/api/quick-update-status/<int:watchlist_id>')
@login_required
def api_quick_update_status(watchlist_id):
    """Quick status update via AJAX"""
    item = UserWatchlist.query.get_or_404(watchlist_id)
    
    if item.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    new_status = request.args.get('status')
    if new_status not in ['want_to_watch', 'watching', 'completed', 'on_hold', 'dropped']:
        return jsonify({'success': False, 'message': 'Invalid status'}), 400
    
    item.update_status(new_status)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Status updated to {new_status.replace("_", " ").title()}',
        'new_status': new_status
    })


@watchlist_bp.route('/api/search-content')
@login_required
def api_search_content():
    """Search content for adding to watchlist"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    # Search content
    results = Content.query.filter(
        or_(
            Content.title.ilike(f'%{query}%'),
            Content.description.ilike(f'%{query}%')
        ),
        Content.status == 'active'
    ).limit(10).all()
    
    return jsonify([{
        'id': content.id,
        'title': content.title,
        'year': content.year,
        'type': content.type,
        'poster_url': content.poster_url
    } for content in results])
