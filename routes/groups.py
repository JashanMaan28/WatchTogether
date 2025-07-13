from flask import Blueprint

groups = Blueprint('groups', __name__)

from flask import render_template, request, flash, redirect, url_for, jsonify, abort
from flask_login import login_required, current_user
from app import db
from models import Group, GroupMember, User
from forms import CreateGroupForm, EditGroupForm, JoinGroupForm, LeaveGroupForm, SearchGroupsForm, ManageMemberForm, DeleteGroupForm
from datetime import datetime

@groups.route('/groups')
def discover_groups():
    form = SearchGroupsForm()
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '')
    
    query = Group.query.filter_by(privacy_level='public')
    
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Group.name.ilike(search_pattern),
                Group.description.ilike(search_pattern)
            )
        )
    
    # Paginate results
    groups_pagination = query.order_by(Group.created_at.desc()).paginate(
        page=page, per_page=12, error_out=False
    )
    
    # Get user's groups if logged in
    user_groups = []
    if current_user.is_authenticated:
        user_groups = [membership.group_id for membership in current_user.group_memberships]
    
    return render_template('groups/discover.html', 
                         groups=groups_pagination.items,
                         pagination=groups_pagination,
                         form=form,
                         search_query=search_query,
                         user_groups=user_groups)

@groups.route('/groups/search')
def search_groups():
    """AJAX endpoint for group search"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    groups_list = Group.search_public_groups(query, limit=10)
    
    results = []
    for group in groups_list:
        results.append({
            'id': group.id,
            'name': group.name,
            'description': group.description[:100] + '...' if group.description and len(group.description) > 100 else group.description,
            'member_count': group.get_member_count(),
            'privacy_level': group.privacy_level
        })
    
    return jsonify(results)

@groups.route('/groups/create', methods=['GET', 'POST'])
@login_required
def create_group():
    """Create a new group"""
    form = CreateGroupForm()
    
    if form.validate_on_submit():
        try:
            # Create the group
            group = Group(
                name=form.name.data.strip(),
                description=form.description.data.strip() if form.description.data else None,
                privacy_level=form.privacy_level.data,
                created_by=current_user.id,
                max_members=form.max_members.data,
                allow_member_invites=form.allow_member_invites.data,
                auto_accept_requests=form.auto_accept_requests.data
            )
            
            db.session.add(group)
            db.session.flush()  # Flush to get the group ID
            
            # Add creator as admin
            creator_membership = GroupMember(
                user_id=current_user.id,
                group_id=group.id,
                role='admin'
            )
            
            db.session.add(creator_membership)
            db.session.commit()
            
            flash(f'Group "{group.name}" created successfully!', 'success')
            return redirect(url_for('groups.view_group', group_id=group.id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error creating group. Please try again.', 'danger')
    
    return render_template('groups/create.html', form=form)

@groups.route('/groups/<int:group_id>')
def view_group(group_id):
    """View a specific group"""
    group = Group.query.get_or_404(group_id)
    
    # Check if user can view this group
    if group.privacy_level == 'private' and current_user.is_authenticated:
        if not group.is_member(current_user.id):
            abort(403)
    elif group.privacy_level == 'private':
        abort(403)
    
    # Get group members
    members = db.session.query(GroupMember, User).join(User).filter(
        GroupMember.group_id == group_id
    ).order_by(
        # Order by role (admin first, then moderator, then member) and join date
        db.case(
            (GroupMember.role == 'admin', 1),
            (GroupMember.role == 'moderator', 2),
            else_=3
        ),
        GroupMember.joined_at
    ).all()
    
    # Check user's relationship with the group
    user_membership = None
    can_join = False
    join_form = JoinGroupForm()
    leave_form = LeaveGroupForm()
    
    if current_user.is_authenticated:
        user_membership = GroupMember.query.filter_by(
            user_id=current_user.id,
            group_id=group_id
        ).first()
        
        if not user_membership:
            can_join_result, message = group.can_user_join(current_user.id)
            can_join = can_join_result
    
    # Get recent discussions for activity feed
    from models import Discussion
    recent_discussions = Discussion.query.filter_by(
        group_id=group_id,
        parent_id=None,  # Only top-level discussions
        is_hidden=False
    ).order_by(Discussion.created_at.desc()).limit(5).all()
    
    return render_template('groups/view.html',
                         group=group,
                         members=members,
                         user_membership=user_membership,
                         can_join=can_join,
                         join_form=join_form,
                         leave_form=leave_form,
                         recent_discussions=recent_discussions)

@groups.route('/groups/<int:group_id>/join', methods=['POST'])
@login_required
def join_group(group_id):
    """Join a group"""
    group = Group.query.get_or_404(group_id)
    form = JoinGroupForm()
    
    if form.validate_on_submit():
        # Check if user can join
        can_join, message = group.can_user_join(current_user.id)
        
        if not can_join:
            flash(message, 'warning')
            return redirect(url_for('groups.view_group', group_id=group_id))
        
        try:
            # Create membership
            membership = GroupMember(
                user_id=current_user.id,
                group_id=group_id,
                role='member'
            )
            
            db.session.add(membership)
            db.session.commit()
            
            flash(f'Successfully joined "{group.name}"!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash('Error joining group. Please try again.', 'danger')
    
    return redirect(url_for('groups.view_group', group_id=group_id))

@groups.route('/groups/<int:group_id>/leave', methods=['POST'])
@login_required
def leave_group(group_id):
    """Leave a group"""
    group = Group.query.get_or_404(group_id)
    form = LeaveGroupForm()
    
    if form.validate_on_submit():
        membership = GroupMember.query.filter_by(
            user_id=current_user.id,
            group_id=group_id
        ).first()
        
        if not membership:
            flash('You are not a member of this group.', 'warning')
            return redirect(url_for('groups.view_group', group_id=group_id))
        
        # Check if user can leave
        can_leave, message = membership.can_be_removed(current_user.id)
        
        if not can_leave:
            flash(message, 'warning')
            return redirect(url_for('groups.view_group', group_id=group_id))
        
        try:
            db.session.delete(membership)
            db.session.commit()
            
            flash(f'You have left "{group.name}".', 'info')
            return redirect(url_for('groups.discover_groups'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error leaving group. Please try again.', 'danger')
    
    return redirect(url_for('groups.view_group', group_id=group_id))

@groups.route('/groups/<int:group_id>/settings', methods=['GET', 'POST'])
@login_required
def group_settings(group_id):
    """Group settings page"""
    group = Group.query.get_or_404(group_id)
    
    # Check if user can edit group settings
    if not group.can_user_edit(current_user.id):
        abort(403)
    
    form = EditGroupForm(group_id=group_id)
    delete_form = DeleteGroupForm(group_name=group.name)
    
    if form.validate_on_submit():
        try:
            group.name = form.name.data.strip()
            group.description = form.description.data.strip() if form.description.data else None
            group.privacy_level = form.privacy_level.data
            group.max_members = form.max_members.data
            group.allow_member_invites = form.allow_member_invites.data
            group.auto_accept_requests = form.auto_accept_requests.data
            group.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Group settings updated successfully!', 'success')
            return redirect(url_for('groups.view_group', group_id=group_id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error updating group settings. Please try again.', 'danger')
    
    # Pre-populate form with current values
    if request.method == 'GET':
        form.name.data = group.name
        form.description.data = group.description
        form.privacy_level.data = group.privacy_level
        form.max_members.data = group.max_members
        form.allow_member_invites.data = group.allow_member_invites
        form.auto_accept_requests.data = group.auto_accept_requests
    
    return render_template('groups/settings.html',
                         group=group,
                         form=form,
                         delete_form=delete_form)

@groups.route('/groups/<int:group_id>/members')
@login_required
def group_members(group_id):
    """Group members page with management capabilities"""
    group = Group.query.get_or_404(group_id)
    
    # Check if user is a member
    user_membership = GroupMember.query.filter_by(
        user_id=current_user.id,
        group_id=group_id
    ).first()
    
    if not user_membership:
        abort(403)
    
    # Get all members with user details
    members = db.session.query(GroupMember, User).join(User).filter(
        GroupMember.group_id == group_id
    ).order_by(
        # Order by role (admin first, then moderator, then member) and join date
        db.case(
            (GroupMember.role == 'admin', 1),
            (GroupMember.role == 'moderator', 2),
            else_=3
        ),
        GroupMember.joined_at
    ).all()
    
    manage_form = ManageMemberForm()
    
    return render_template('groups/members.html',
                         group=group,
                         members=members,
                         user_membership=user_membership,
                         manage_form=manage_form,
                         current_user=current_user)

@groups.route('/groups/<int:group_id>/members/<int:user_id>/manage', methods=['POST'])
@login_required
def manage_member(group_id, user_id):
    """Manage a specific group member"""
    group = Group.query.get_or_404(group_id)
    form = ManageMemberForm()
    
    if form.validate_on_submit():
        # Get the target member
        target_member = GroupMember.query.filter_by(
            user_id=user_id,
            group_id=group_id
        ).first()
        
        if not target_member:
            flash('Member not found.', 'warning')
            return redirect(url_for('groups.group_members', group_id=group_id))
        
        action = form.action.data
        
        try:
            if action == 'promote_admin':
                can_promote, message = target_member.can_promote_to_admin(current_user.id)
                if can_promote:
                    target_member.role = 'admin'
                    flash(f'{target_member.user.username} promoted to admin.', 'success')
                else:
                    flash(message, 'warning')
            
            elif action == 'promote_moderator':
                can_promote = group.can_user_manage_members(current_user.id)
                if can_promote and target_member.role == 'member':
                    target_member.role = 'moderator'
                    flash(f'{target_member.user.username} promoted to moderator.', 'success')
                else:
                    flash('Cannot promote this member to moderator.', 'warning')
            
            elif action == 'demote_member':
                if target_member.role == 'admin':
                    can_demote, message = target_member.can_demote_from_admin(current_user.id)
                    if can_demote:
                        target_member.role = 'member'
                        flash(f'{target_member.user.username} demoted to member.', 'success')
                    else:
                        flash(message, 'warning')
                elif target_member.role == 'moderator':
                    if group.can_user_manage_members(current_user.id):
                        target_member.role = 'member'
                        flash(f'{target_member.user.username} demoted to member.', 'success')
                    else:
                        flash('Cannot demote this member.', 'warning')
            
            elif action == 'remove':
                can_remove, message = target_member.can_be_removed(current_user.id)
                if can_remove:
                    username = target_member.user.username
                    db.session.delete(target_member)
                    flash(f'{username} removed from group.', 'info')
                else:
                    flash(message, 'warning')
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            flash('Error managing member. Please try again.', 'danger')
    
    return redirect(url_for('groups.group_members', group_id=group_id))

@groups.route('/groups/<int:group_id>/delete', methods=['POST'])
@login_required
def delete_group(group_id):
    """Delete a group"""
    group = Group.query.get_or_404(group_id)
    form = DeleteGroupForm(group_name=group.name)
    
    if not group.can_user_delete(current_user.id):
        abort(403)
    
    if form.validate_on_submit():
        try:
            group_name = group.name
            db.session.delete(group)
            db.session.commit()
            
            flash(f'Group "{group_name}" has been deleted.', 'info')
            return redirect(url_for('groups.discover_groups'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error deleting group. Please try again.', 'danger')
    
    return redirect(url_for('groups.group_settings', group_id=group_id))

@groups.route('/my-groups')
@login_required
def my_groups():
    """Show user's groups"""
    # Get user's group memberships
    memberships = db.session.query(GroupMember, Group).join(Group).filter(
        GroupMember.user_id == current_user.id
    ).order_by(Group.name).all()
    
    # Separate by role
    admin_groups = []
    member_groups = []
    
    for membership, group in memberships:
        if membership.role == 'admin' or group.created_by == current_user.id:
            admin_groups.append((membership, group))
        else:
            member_groups.append((membership, group))
    
    return render_template('groups/my_groups.html',
                         admin_groups=admin_groups,
                         member_groups=member_groups)

@groups.route('/groups/user-groups')
@login_required
def user_groups():
    """Return a JSON list of groups the user is a member of."""
    groups_ = Group.query.join(GroupMember).filter(GroupMember.user_id == current_user.id).all()
    return jsonify({
        'groups': [
            {'id': g.id, 'name': g.name} for g in groups_
        ]
    })

@groups.route('/groups/<int:group_id>/add_from_tmdb', methods=['POST'])
@login_required
def add_from_tmdb_to_group(group_id):
    """Add content from TMDB to a group watchlist (AJAX endpoint)."""
    from models import Content, GroupWatchlist, GroupMember
    from app import db
    from utils.tmdb_api import TMDBService
    import json, logging
    import os
    # Setup logging
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'recommendations.log')
    logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    try:
        logging.info(f"[add_from_tmdb_to_group] group_id={group_id}, user_id={current_user.id}, data={request.get_json()}")
        group = Group.query.get_or_404(group_id)
        if not group.is_member(current_user.id):
            logging.warning(f"User {current_user.id} is not a member of group {group_id}")
            return jsonify({'error': 'You must be a member of this group.'}), 403
        data = request.get_json()
        tmdb_id = data.get('tmdb_id')
        content_type = data.get('content_type', 'movie')
        if not tmdb_id:
            logging.error("TMDB ID missing in request data")
            return jsonify({'error': 'TMDB ID required'}), 400
        # Get or create local content
        local_content = Content.query.filter_by(tmdb_id=tmdb_id).first()
        if not local_content:
            tmdb = TMDBService()
            content_details = tmdb.get_content_details(tmdb_id, content_type)
            logging.info(f"TMDB fetch for tmdb_id={tmdb_id}, content_type={content_type}: {content_details}")
            if not content_details:
                logging.error(f"Content not found in TMDB for tmdb_id={tmdb_id}")
                return jsonify({'error': 'Content not found in TMDB'}), 404
            local_content = Content(
                title=content_details['title'],
                description=content_details['description'],
                type=content_details['type'],
                genre=', '.join(content_details.get('genres', [])),
                year=content_details.get('year'),
                rating=content_details.get('rating'),
                duration=content_details.get('duration'),
                poster_url=content_details.get('poster_url'),
                backdrop_url=content_details.get('backdrop_url'),
                trailer_url=content_details.get('trailer_url'),
                tmdb_id=tmdb_id,
                imdb_id=content_details.get('imdb_id'),
                director=content_details.get('director'),
                cast=', '.join(content_details.get('cast', [])),
                country=content_details.get('country'),
                language=content_details.get('language'),
                status='active'
            )
            db.session.add(local_content)
            db.session.flush()
        # Check if already in group watchlist
        existing = GroupWatchlist.query.filter_by(group_id=group_id, content_id=local_content.id).first()
        if existing:
            logging.info(f"Content {local_content.id} already in group {group_id} watchlist")
            return jsonify({'success': True, 'message': 'Already in group watchlist.'})
        # Add to group watchlist
        watchlist_item = GroupWatchlist(
            group_id=group_id,
            content_id=local_content.id,
            added_by=current_user.id,
            status='want_to_watch',
            priority='medium'
        )
        db.session.add(watchlist_item)
        db.session.commit()
        logging.info(f"Added content {local_content.id} to group {group_id} by user {current_user.id}")
        return jsonify({'success': True, 'message': 'Added to group watchlist.'})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Exception in add_from_tmdb_to_group: {str(e)}", exc_info=True)
        return jsonify({'error': f'Internal error: {str(e)}'}), 500
