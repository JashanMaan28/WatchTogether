from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy import desc, asc, and_, or_
from datetime import datetime, timedelta
import re

from app import db
from models import (Discussion, DiscussionLike, DiscussionReport, DiscussionNotification,
                   DiscussionSearch, Content, Group, GroupMember, User)
from forms import DiscussionForm, ReportDiscussionForm

discussion_bp = Blueprint('discussion', __name__, url_prefix='/discussions')

@discussion_bp.route('/content/<int:content_id>')
@login_required
def content_discussions(content_id):
    content = Content.query.get_or_404(content_id)
    
    sort_by = request.args.get('sort_by', 'recent')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Base query for top-level discussions only
    query = Discussion.query.filter_by(
        content_id=content_id,
        parent_id=None,
        is_hidden=False
    )
    
    # Apply sorting
    if sort_by == 'popular':
        # Sort by like count and reply count
        query = query.outerjoin(DiscussionLike).group_by(Discussion.id).order_by(
            desc(db.func.count(DiscussionLike.id.distinct())),
            desc(Discussion.created_at)
        )
    elif sort_by == 'oldest':
        query = query.order_by(asc(Discussion.created_at))
    else:  # recent
        query = query.order_by(desc(Discussion.created_at))
    
    # Get pinned discussions separately
    pinned_discussions = Discussion.query.filter_by(
        content_id=content_id,
        parent_id=None,
        is_hidden=False,
        is_pinned=True
    ).order_by(desc(Discussion.created_at)).all()
    
    discussions = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    form = DiscussionForm()
    
    return render_template('discussions/content_discussions.html',
                         content=content,
                         discussions=discussions,
                         pinned_discussions=pinned_discussions,
                         form=form,
                         sort_by=sort_by)


@discussion_bp.route('/group/<int:group_id>')
@login_required
def group_discussions(group_id):
    """Display discussions for a specific group"""
    group = Group.query.get_or_404(group_id)
    
    # Check if user is a member
    if not group.is_member(current_user.id):
        flash('You must be a member of this group to view discussions.', 'error')
        return redirect(url_for('groups.view_group', group_id=group_id))
    
    # Get sorting parameters
    sort_by = request.args.get('sort_by', 'recent')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Base query for top-level discussions only
    query = Discussion.query.filter_by(
        group_id=group_id,
        parent_id=None,
        is_hidden=False
    )
    
    # Apply sorting
    if sort_by == 'popular':
        query = query.outerjoin(DiscussionLike).group_by(Discussion.id).order_by(
            desc(db.func.count(DiscussionLike.id.distinct())),
            desc(Discussion.created_at)
        )
    elif sort_by == 'oldest':
        query = query.order_by(asc(Discussion.created_at))
    else:  # recent
        query = query.order_by(desc(Discussion.created_at))
    
    # Get pinned discussions separately
    pinned_discussions = Discussion.query.filter_by(
        group_id=group_id,
        parent_id=None,
        is_hidden=False,
        is_pinned=True
    ).order_by(desc(Discussion.created_at)).all()
    
    discussions = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    form = DiscussionForm()
    
    return render_template('discussions/group_discussions.html',
                         group=group,
                         discussions=discussions,
                         pinned_discussions=pinned_discussions,
                         form=form,
                         sort_by=sort_by)


@discussion_bp.route('/thread/<int:discussion_id>')
@login_required
def view_thread(discussion_id):
    """View a discussion thread with all replies"""
    discussion = Discussion.query.get_or_404(discussion_id)
    
    # Check permissions
    if discussion.content_id:
        # Content discussions are public
        pass
    elif discussion.group_id:
        # Check group membership
        group = Group.query.get(discussion.group_id)
        if not group.is_member(current_user.id):
            abort(403)
    
    # Get the root discussion if this is a reply
    root_discussion = discussion
    while root_discussion.parent_id:
        root_discussion = root_discussion.parent
    
    # Get all replies in thread order
    def get_thread_replies(parent_id, depth=0):
        replies = Discussion.query.filter_by(
            parent_id=parent_id,
            is_hidden=False
        ).order_by(Discussion.created_at.asc()).all()
        
        thread_data = []
        for reply in replies:
            reply_data = {
                'discussion': reply,
                'depth': depth,
                'replies': get_thread_replies(reply.id, depth + 1)
            }
            thread_data.append(reply_data)
        
        return thread_data
    
    thread_replies = get_thread_replies(root_discussion.id)
    
    form = DiscussionForm()
    
    return render_template('discussions/thread.html',
                         discussion=root_discussion,
                         thread_replies=thread_replies,
                         form=form)


# Discussion Management Routes

@discussion_bp.route('/create', methods=['POST'])
@login_required
def create_discussion():
    """Create a new discussion or reply"""
    form = DiscussionForm()
    
    if form.validate_on_submit():
        # Validate content_id or group_id
        content_id = request.form.get('content_id', type=int)
        group_id = request.form.get('group_id', type=int)
        parent_id = request.form.get('parent_id', type=int)
        
        if not content_id and not group_id:
            flash('Discussion must be associated with content or a group.', 'error')
            return redirect(request.referrer)
        
        # Validate permissions
        if group_id:
            group = Group.query.get_or_404(group_id)
            if not group.is_member(current_user.id):
                abort(403)
        
        # Check for spoilers in message
        has_spoilers = form.has_spoilers.data or detect_spoilers(form.message.data)
        
        discussion = Discussion(
            content_id=content_id,
            group_id=group_id,
            user_id=current_user.id,
            parent_id=parent_id,
            message=form.message.data,
            has_spoilers=has_spoilers
        )
        
        db.session.add(discussion)
        db.session.commit()
        
        # Create search index
        DiscussionSearch.create_or_update_for_discussion(discussion)
        
        # Create notifications
        create_discussion_notifications(discussion)
        
        flash('Discussion posted successfully!', 'success')
        
        # Redirect to appropriate page
        if content_id:
            return redirect(url_for('discussion.content_discussions', content_id=content_id))
        else:
            return redirect(url_for('discussion.group_discussions', group_id=group_id))
    
    flash('Error posting discussion. Please check your message.', 'error')
    return redirect(request.referrer)


@discussion_bp.route('/edit/<int:discussion_id>', methods=['GET', 'POST'])
@login_required
def edit_discussion(discussion_id):
    """Edit a discussion"""
    discussion = Discussion.query.get_or_404(discussion_id)
    
    if not discussion.can_user_edit(current_user.id):
        abort(403)
    
    form = DiscussionForm()
    
    if form.validate_on_submit():
        discussion.message = form.message.data
        discussion.has_spoilers = form.has_spoilers.data or detect_spoilers(form.message.data)
        discussion.edited_at = datetime.utcnow()
        
        db.session.commit()
        
        # Update search index
        DiscussionSearch.create_or_update_for_discussion(discussion)
        
        flash('Discussion updated successfully!', 'success')
        return redirect(url_for('discussion.view_thread', discussion_id=discussion_id))
    
    # Pre-populate form
    form.message.data = discussion.message
    form.has_spoilers.data = discussion.has_spoilers
    
    return render_template('discussions/edit.html', discussion=discussion, form=form)


@discussion_bp.route('/delete/<int:discussion_id>', methods=['POST'])
@login_required
def delete_discussion(discussion_id):
    """Delete a discussion"""
    discussion = Discussion.query.get_or_404(discussion_id)
    
    if not discussion.can_user_delete(current_user.id):
        abort(403)
    
    # Store redirect info before deletion
    content_id = discussion.content_id
    group_id = discussion.group_id
    parent_id = discussion.parent_id
    
    # Instead of hard delete, mark as hidden
    discussion.is_hidden = True
    db.session.commit()
    
    flash('Discussion deleted successfully.', 'success')
    
    # Redirect appropriately
    if parent_id:
        # If this was a reply, go back to the parent thread
        parent = Discussion.query.get(parent_id)
        while parent.parent_id:
            parent = parent.parent
        return redirect(url_for('discussion.view_thread', discussion_id=parent.id))
    elif content_id:
        return redirect(url_for('discussion.content_discussions', content_id=content_id))
    else:
        return redirect(url_for('discussion.group_discussions', group_id=group_id))


@discussion_bp.route('/pin/<int:discussion_id>', methods=['POST'])
@login_required
def toggle_pin_discussion(discussion_id):
    """Pin or unpin a discussion"""
    discussion = Discussion.query.get_or_404(discussion_id)
    
    if not discussion.can_user_pin(current_user.id):
        abort(403)
    
    discussion.is_pinned = not discussion.is_pinned
    db.session.commit()
    
    action = 'pinned' if discussion.is_pinned else 'unpinned'
    flash(f'Discussion {action} successfully.', 'success')
    
    return redirect(request.referrer)


# Interaction Routes

@discussion_bp.route('/like/<int:discussion_id>/<action>')
@login_required
def toggle_like(discussion_id, action):
    """Like or dislike a discussion"""
    discussion = Discussion.query.get_or_404(discussion_id)
    
    if action not in ['like', 'dislike', 'remove']:
        abort(400)
    
    existing_like = DiscussionLike.query.filter_by(
        discussion_id=discussion_id,
        user_id=current_user.id
    ).first()
    
    if action == 'remove':
        if existing_like:
            db.session.delete(existing_like)
    else:
        is_like = action == 'like'
        
        if existing_like:
            existing_like.is_like = is_like
        else:
            like = DiscussionLike(
                discussion_id=discussion_id,
                user_id=current_user.id,
                is_like=is_like
            )
            db.session.add(like)
            
            # Create notification for the discussion author
            if discussion.user_id != current_user.id and is_like:
                notification = DiscussionNotification(
                    discussion_id=discussion_id,
                    user_id=discussion.user_id,
                    trigger_user_id=current_user.id,
                    notification_type='like'
                )
                db.session.add(notification)
    
    db.session.commit()
    
    # Return JSON for AJAX requests
    if request.headers.get('Content-Type') == 'application/json':
        return jsonify({
            'success': True,
            'like_count': discussion.get_like_count(),
            'dislike_count': discussion.get_dislike_count(),
            'user_reaction': discussion.get_user_reaction(current_user.id)
        })
    
    return redirect(request.referrer)


@discussion_bp.route('/report/<int:discussion_id>', methods=['GET', 'POST'])
@login_required
def report_discussion(discussion_id):
    """Report a discussion for inappropriate content"""
    discussion = Discussion.query.get_or_404(discussion_id)
    
    # Check if already reported by this user
    existing_report = DiscussionReport.query.filter_by(
        discussion_id=discussion_id,
        reporter_id=current_user.id
    ).first()
    
    if existing_report:
        flash('You have already reported this discussion.', 'info')
        return redirect(request.referrer)
    
    form = ReportDiscussionForm()
    
    if form.validate_on_submit():
        report = DiscussionReport(
            discussion_id=discussion_id,
            reporter_id=current_user.id,
            reason=form.reason.data,
            description=form.description.data
        )
        
        db.session.add(report)
        db.session.commit()
        
        flash('Discussion reported successfully. Thank you for helping keep our community safe.', 'success')
        return redirect(request.referrer)
    
    return render_template('discussions/report.html', discussion=discussion, form=form)


# Search Routes

@discussion_bp.route('/search')
@login_required
def search_discussions():
    """Search discussions"""
    query = request.args.get('q', '').strip()
    content_id = request.args.get('content_id', type=int)
    group_id = request.args.get('group_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    discussions = []
    
    if query:
        # Use the search index
        all_results = DiscussionSearch.search_discussions(
            query=query,
            content_id=content_id,
            group_id=group_id,
            limit=200
        )
        
        # Paginate results
        start = (page - 1) * per_page
        end = start + per_page
        discussions = all_results[start:end]
        
        # Create pagination object
        has_prev = page > 1
        has_next = end < len(all_results)
        pagination = {
            'has_prev': has_prev,
            'has_next': has_next,
            'prev_num': page - 1 if has_prev else None,
            'next_num': page + 1 if has_next else None,
            'page': page,
            'pages': (len(all_results) + per_page - 1) // per_page,
            'total': len(all_results)
        }
    else:
        pagination = None
    
    # Get context info
    content = Content.query.get(content_id) if content_id else None
    group = Group.query.get(group_id) if group_id else None
    
    return render_template('discussions/search.html',
                         discussions=discussions,
                         pagination=pagination,
                         query=query,
                         content=content,
                         group=group)


# API Routes for Real-time Updates

@discussion_bp.route('/api/recent/<int:content_id>')
@login_required
def api_recent_content_discussions(content_id):
    """Get recent discussions for content (for polling)"""
    since = request.args.get('since')
    limit = request.args.get('limit', 10, type=int)
    
    query = Discussion.query.filter_by(
        content_id=content_id,
        is_hidden=False
    )
    
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            query = query.filter(Discussion.created_at > since_dt)
        except ValueError:
            pass
    
    discussions = query.order_by(desc(Discussion.created_at)).limit(limit).all()
    
    return jsonify([
        discussion.to_dict(user_id=current_user.id) 
        for discussion in discussions
    ])


@discussion_bp.route('/api/recent/group/<int:group_id>')
@login_required
def api_recent_group_discussions(group_id):
    """Get recent discussions for group (for polling)"""
    group = Group.query.get_or_404(group_id)
    
    if not group.is_member(current_user.id):
        abort(403)
    
    since = request.args.get('since')
    limit = request.args.get('limit', 10, type=int)
    
    query = Discussion.query.filter_by(
        group_id=group_id,
        is_hidden=False
    )
    
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            query = query.filter(Discussion.created_at > since_dt)
        except ValueError:
            pass
    
    discussions = query.order_by(desc(Discussion.created_at)).limit(limit).all()
    
    return jsonify([
        discussion.to_dict(user_id=current_user.id) 
        for discussion in discussions
    ])


@discussion_bp.route('/api/thread/<int:discussion_id>')
@login_required
def api_thread(discussion_id):
    """Get discussion thread with replies (for real-time updates)"""
    discussion = Discussion.query.get_or_404(discussion_id)
    
    # Check permissions
    if discussion.content_id:
        pass
    elif discussion.group_id:
        group = Group.query.get(discussion.group_id)
        if not group.is_member(current_user.id):
            abort(403)
    
    return jsonify(discussion.to_dict(include_replies=True, user_id=current_user.id))


@discussion_bp.route('/api/notifications')
@login_required
def api_notifications():
    """Get user's discussion notifications"""
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    limit = request.args.get('limit', 50, type=int)
    
    query = DiscussionNotification.query.filter_by(user_id=current_user.id)
    
    if unread_only:
        query = query.filter_by(is_read=False)
    
    notifications = query.order_by(desc(DiscussionNotification.created_at)).limit(limit).all()
    
    return jsonify([notification.to_dict() for notification in notifications])


@discussion_bp.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def api_mark_notification_read(notification_id):
    """Mark a notification as read"""
    notification = DiscussionNotification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.id:
        abort(403)
    
    notification.mark_as_read()
    
    return jsonify({'success': True})


# Utility Functions

def detect_spoilers(message):
    """Detect potential spoilers in message text"""
    spoiler_keywords = [
        'spoiler', 'spoilers', 'ending', 'dies', 'death', 'killed',
        'plot twist', 'finale', 'final episode', 'season finale'
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in spoiler_keywords)


def create_discussion_notifications(discussion):
    """Create notifications for discussion replies and mentions"""
    
    # Notify parent discussion author if this is a reply
    if discussion.parent_id:
        parent = Discussion.query.get(discussion.parent_id)
        if parent and parent.user_id != discussion.user_id:
            notification = DiscussionNotification(
                discussion_id=discussion.id,
                user_id=parent.user_id,
                trigger_user_id=discussion.user_id,
                notification_type='reply'
            )
            db.session.add(notification)
    
    # Check for @mentions in the message
    mentions = re.findall(r'@(\w+)', discussion.message)
    for username in mentions:
        user = User.query.filter_by(username=username).first()
        if user and user.id != discussion.user_id:
            # Check if user has access to this discussion
            has_access = False
            if discussion.content_id:
                has_access = True  # Content discussions are public
            elif discussion.group_id:
                group = Group.query.get(discussion.group_id)
                has_access = group.is_member(user.id)
            
            if has_access:
                notification = DiscussionNotification(
                    discussion_id=discussion.id,
                    user_id=user.id,
                    trigger_user_id=discussion.user_id,
                    notification_type='mention'
                )
                db.session.add(notification)
    
    db.session.commit()
