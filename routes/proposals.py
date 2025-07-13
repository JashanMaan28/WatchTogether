from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, abort
from flask_login import login_required, current_user
from app import db
from models import Group, GroupMember, User, Content, ContentProposal, ProposalVote, ProposalAnalytics, Discussion
from forms import (ContentProposalForm, EditProposalForm, VoteProposalForm, 
                  ProposalFilterForm, ProposalSearchForm, ProposalActionForm, ProposalSettingsForm)
from datetime import datetime, timedelta
from sqlalchemy import desc, asc, or_, and_
import json

proposals_bp = Blueprint('proposals', __name__)

@proposals_bp.route('/groups/<int:group_id>/proposals')
@login_required
def group_proposals(group_id):
    """View all proposals for a group"""
    group = Group.query.get_or_404(group_id)
    
    # Check if user is a member
    if not group.is_member(current_user.id):
        flash('You must be a member of this group to view proposals.', 'error')
        return redirect(url_for('groups.view_group', group_id=group_id))
    
    # Get filter parameters
    filter_form = ProposalFilterForm()
    search_form = ProposalSearchForm()
    
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    content_type_filter = request.args.get('content_type', 'all')
    proposer_filter = request.args.get('proposer', '')
    sort_by = request.args.get('sort_by', 'created_desc')
    search_query = request.args.get('search', '')
    
    # Build query
    query = ContentProposal.query.filter_by(group_id=group_id)
    
    # Apply filters
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if priority_filter != 'all':
        query = query.filter_by(priority=priority_filter)
    
    if content_type_filter != 'all':
        query = query.filter_by(content_type=content_type_filter)
    
    if proposer_filter:
        proposer_user = User.query.filter_by(username=proposer_filter).first()
        if proposer_user:
            query = query.filter_by(proposer_id=proposer_user.id)
    
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                ContentProposal.title.ilike(search_pattern),
                ContentProposal.description.ilike(search_pattern),
                ContentProposal.reason.ilike(search_pattern)
            )
        )
    
    # Apply sorting
    if sort_by == 'created_desc':
        query = query.order_by(desc(ContentProposal.created_at))
    elif sort_by == 'created_asc':
        query = query.order_by(asc(ContentProposal.created_at))
    elif sort_by == 'votes_desc':
        query = query.order_by(desc(ContentProposal.upvotes + ContentProposal.downvotes))
    elif sort_by == 'approval_desc':
        query = query.order_by(desc(ContentProposal.upvotes))
    elif sort_by == 'priority_desc':
        # Order by priority: high, medium, low
        query = query.order_by(
            db.case(
                (ContentProposal.priority == 'high', 1),
                (ContentProposal.priority == 'medium', 2),
                (ContentProposal.priority == 'low', 3)
            )
        )
    
    # Paginate
    page = request.args.get('page', 1, type=int)
    proposals = query.paginate(
        page=page, per_page=10, error_out=False
    )
    
    # Get user's votes for each proposal
    user_votes = {}
    if proposals.items:
        proposal_ids = [p.id for p in proposals.items]
        votes = ProposalVote.query.filter(
            ProposalVote.proposal_id.in_(proposal_ids),
            ProposalVote.user_id == current_user.id
        ).all()
        user_votes = {vote.proposal_id: vote for vote in votes}
    
    # Set form defaults
    filter_form.status.data = status_filter
    filter_form.priority.data = priority_filter
    filter_form.content_type.data = content_type_filter
    filter_form.proposer.data = proposer_filter
    filter_form.sort_by.data = sort_by
    search_form.query.data = search_query
    
    return render_template('proposals/group_proposals.html',
                         group=group,
                         proposals=proposals,
                         filter_form=filter_form,
                         search_form=search_form,
                         user_votes=user_votes)


@proposals_bp.route('/groups/<int:group_id>/proposals/create', methods=['GET', 'POST'])
@login_required
def create_proposal(group_id):
    """Create a new content proposal"""
    group = Group.query.get_or_404(group_id)
    
    if not group.is_member(current_user.id):
        flash('You must be a member of this group to create proposals.', 'error')
        return redirect(url_for('groups.view_group', group_id=group_id))
    
    member = GroupMember.query.filter_by(group_id=group_id, user_id=current_user.id).first()
    if member.role not in ['admin', 'moderator']:
        pass  # Allow all members for now
    

    # Fetch user's watchlist content for selection
    watchlist_content = current_user.get_watchlist_content(only_status='want_to_watch')

    # Prepare choices for SelectField: (id, title)
    watchlist_choices = [(str(c.id), f"{c.title} ({c.year})" if c.year else c.title) for c in watchlist_content]
    form = ContentProposalForm()
    form.existing_content_id.choices = [('', '-- Select a movie or show --')] + watchlist_choices
    
    if form.validate_on_submit():
        try:
            proposal = ContentProposal(
                group_id=group_id,
                proposer_id=current_user.id,
                reason=form.reason.data,
                priority=form.priority.data,
                proposed_watch_date=form.proposed_watch_date.data,
                required_votes=form.required_votes.data,
                approval_threshold=form.approval_threshold.data / 100,
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            
            if form.content_type_choice.data == 'existing':
                if form.existing_content_id.data:
                    try:
                        content_id = int(form.existing_content_id.data)
                        content = Content.query.get(content_id)
                    except (ValueError, TypeError):
                        content = None
                    if content:
                        proposal.content_id = content.id
                    else:
                        flash('Selected content not found.', 'error')
                        return render_template('proposals/create_proposal.html', form=form, group=group, watchlist_content=watchlist_content)
            else:
                # New content - store details in proposal
                proposal.title = form.title.data
                proposal.content_type = form.content_type.data
                proposal.release_year = form.release_year.data
                proposal.genre = form.genre.data
                proposal.description = form.description.data
                proposal.external_id = form.external_id.data
                proposal.external_source = form.external_source.data
            
            db.session.add(proposal)
            db.session.commit()
            
            # Create discussion thread for the proposal
            discussion = Discussion(
                group_id=group_id,
                user_id=current_user.id,
                message=f"Discussion thread for proposal: {proposal.get_content_title()}",
                is_pinned=True
            )
            db.session.add(discussion)
            db.session.commit()
            
            # Link the discussion to the proposal
            proposal.discussion_id = discussion.id
            db.session.commit()
            
            flash('Content proposal created successfully!', 'success')
            return redirect(url_for('proposals.view_proposal', proposal_id=proposal.id))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating the proposal. Please try again.', 'error')
    
    return render_template('proposals/create_proposal.html', form=form, group=group, watchlist_content=watchlist_content)


@proposals_bp.route('/proposals/<int:proposal_id>')
@login_required
def view_proposal(proposal_id):
    """View a specific proposal"""
    proposal = ContentProposal.query.get_or_404(proposal_id)
    
    # Check if user can view this proposal
    if not proposal.group.is_member(current_user.id):
        flash('You must be a member of this group to view this proposal.', 'error')
        return redirect(url_for('groups.view_group', group_id=proposal.group_id))
    
    # Get user's vote if any
    user_vote = proposal.get_user_vote(current_user.id)
    
    # Get all votes for display
    votes = ProposalVote.query.filter_by(proposal_id=proposal_id).order_by(desc(ProposalVote.created_at)).all()
    
    # Get discussion thread
    discussion = Discussion.query.filter_by(group_id=proposal.group_id).filter(
        Discussion.message.like(f"%proposal: {proposal.get_content_title()}%")
    ).first()
    
    # Check if proposal has expired
    if proposal.is_expired():
        proposal.expire_proposal()
    
    # Forms
    vote_form = VoteProposalForm()
    action_form = ProposalActionForm()
    
    # Check permissions
    can_vote = proposal.can_user_vote(current_user.id)[0]
    can_edit = proposal.can_user_edit(current_user.id)
    can_delete = proposal.can_user_delete(current_user.id)
    is_admin = proposal.group.get_member_role(current_user.id) in ['admin', 'moderator']
    
    return render_template('proposals/view_proposal.html',
                         proposal=proposal,
                         user_vote=user_vote,
                         votes=votes,
                         discussion=discussion,
                         vote_form=vote_form,
                         action_form=action_form,
                         can_vote=can_vote,
                         can_edit=can_edit,
                         can_delete=can_delete,
                         is_admin=is_admin)


@proposals_bp.route('/proposals/<int:proposal_id>/vote', methods=['POST'])
@login_required
def vote_proposal(proposal_id):
    """Vote on a proposal"""
    proposal = ContentProposal.query.get_or_404(proposal_id)
    
    # Check if user can vote
    can_vote, message = proposal.can_user_vote(current_user.id)
    if not can_vote:
        flash(message, 'error')
        return redirect(url_for('proposals.view_proposal', proposal_id=proposal_id))
    
    form = VoteProposalForm()
    
    if form.validate_on_submit():
        try:
            # Cast vote
            success = ProposalVote.cast_vote(
                proposal_id=proposal_id,
                user_id=current_user.id,
                vote_type=form.vote_type.data,
                comment=form.comment.data
            )
            
            if success:
                flash('Your vote has been recorded!', 'success')
            else:
                flash('An error occurred while recording your vote.', 'error')
                
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while recording your vote.', 'error')
    
    return redirect(url_for('proposals.view_proposal', proposal_id=proposal_id))


@proposals_bp.route('/proposals/<int:proposal_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_proposal(proposal_id):
    """Edit a proposal"""
    proposal = ContentProposal.query.get_or_404(proposal_id)
    
    # Check permissions
    if not proposal.can_user_edit(current_user.id):
        flash('You do not have permission to edit this proposal.', 'error')
        return redirect(url_for('proposals.view_proposal', proposal_id=proposal_id))
    
    form = EditProposalForm()
    is_admin = proposal.group.get_member_role(current_user.id) in ['admin', 'moderator']
    
    if form.validate_on_submit():
        try:
            proposal.reason = form.reason.data
            proposal.priority = form.priority.data
            proposal.proposed_watch_date = form.proposed_watch_date.data
            proposal.updated_at = datetime.utcnow()
            
            # Admin-only fields
            if is_admin:
                proposal.admin_notes = form.admin_notes.data
            
            db.session.commit()
            flash('Proposal updated successfully!', 'success')
            return redirect(url_for('proposals.view_proposal', proposal_id=proposal_id))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the proposal.', 'error')
    
    # Pre-populate form
    form.reason.data = proposal.reason
    form.priority.data = proposal.priority
    form.proposed_watch_date.data = proposal.proposed_watch_date
    if is_admin:
        form.admin_notes.data = proposal.admin_notes
    
    return render_template('proposals/edit_proposal.html', form=form, proposal=proposal, is_admin=is_admin)


@proposals_bp.route('/proposals/<int:proposal_id>/delete', methods=['POST'])
@login_required
def delete_proposal(proposal_id):
    """Delete a proposal"""
    proposal = ContentProposal.query.get_or_404(proposal_id)
    
    # Check permissions
    if not proposal.can_user_delete(current_user.id):
        flash('You do not have permission to delete this proposal.', 'error')
        return redirect(url_for('proposals.view_proposal', proposal_id=proposal_id))
    
    try:
        group_id = proposal.group_id
        db.session.delete(proposal)
        db.session.commit()
        flash('Proposal deleted successfully.', 'success')
        return redirect(url_for('proposals.group_proposals', group_id=group_id))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the proposal.', 'error')
        return redirect(url_for('proposals.view_proposal', proposal_id=proposal_id))


@proposals_bp.route('/proposals/<int:proposal_id>/action', methods=['POST'])
@login_required
def proposal_action(proposal_id):
    """Admin actions on proposals"""
    proposal = ContentProposal.query.get_or_404(proposal_id)
    
    # Check admin permissions
    member = GroupMember.query.filter_by(group_id=proposal.group_id, user_id=current_user.id).first()
    if not member or member.role not in ['admin', 'moderator']:
        flash('You do not have permission to perform this action.', 'error')
        return redirect(url_for('proposals.view_proposal', proposal_id=proposal_id))
    
    form = ProposalActionForm()
    
    if form.validate_on_submit():
        try:
            action = form.action.data
            admin_notes = form.admin_notes.data
            
            if action == 'approve':
                proposal.status = 'approved'
                proposal.approved_at = datetime.utcnow()
                proposal.approved_by = current_user.id
                flash('Proposal approved successfully!', 'success')
                
            elif action == 'reject':
                proposal.status = 'rejected'
                flash('Proposal rejected.', 'info')
                
            elif action == 'feature':
                proposal.is_featured = True
                flash('Proposal featured successfully!', 'success')
                
            elif action == 'unfeature':
                proposal.is_featured = False
                flash('Proposal unfeatured.', 'info')
                
            elif action == 'extend':
                proposal.expires_at = datetime.utcnow() + timedelta(days=14)
                flash('Voting period extended by 14 days.', 'success')
                
            elif action == 'close':
                proposal.expires_at = datetime.utcnow()
                proposal.expire_proposal()
                flash('Voting closed early.', 'info')
            
            if admin_notes:
                proposal.admin_notes = admin_notes
            
            proposal.updated_at = datetime.utcnow()
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while performing the action.', 'error')
    
    return redirect(url_for('proposals.view_proposal', proposal_id=proposal_id))


@proposals_bp.route('/groups/<int:group_id>/proposals/analytics')
@login_required
def proposal_analytics(group_id):
    """View proposal analytics for a group"""
    group = Group.query.get_or_404(group_id)
    
    # Check admin permissions
    member = GroupMember.query.filter_by(group_id=group_id, user_id=current_user.id).first()
    if not member or member.role not in ['admin', 'moderator']:
        flash('You do not have permission to view analytics.', 'error')
        return redirect(url_for('proposals.group_proposals', group_id=group_id))
    
    # Update analytics
    monthly_analytics = ProposalAnalytics.update_analytics(group_id, 'monthly')
    weekly_analytics = ProposalAnalytics.update_analytics(group_id, 'weekly')
    
    # Get recent proposals
    recent_proposals = ContentProposal.query.filter_by(group_id=group_id).order_by(
        desc(ContentProposal.created_at)
    ).limit(10).all()
    
    # Get top contributors
    proposer_stats = db.session.query(
        User.username,
        db.func.count(ContentProposal.id).label('proposal_count')
    ).join(ContentProposal).filter(
        ContentProposal.group_id == group_id
    ).group_by(User.id).order_by(desc('proposal_count')).limit(5).all()
    
    voter_stats = db.session.query(
        User.username,
        db.func.count(ProposalVote.id).label('vote_count')
    ).join(ProposalVote).join(ContentProposal).filter(
        ContentProposal.group_id == group_id
    ).group_by(User.id).order_by(desc('vote_count')).limit(5).all()
    
    return render_template('proposals/analytics.html',
                         group=group,
                         monthly_analytics=monthly_analytics,
                         weekly_analytics=weekly_analytics,
                         recent_proposals=recent_proposals,
                         proposer_stats=proposer_stats,
                         voter_stats=voter_stats)


@proposals_bp.route('/api/proposals/<int:proposal_id>')
@login_required
def api_proposal_details(proposal_id):
    """API endpoint for proposal details"""
    proposal = ContentProposal.query.get_or_404(proposal_id)
    
    # Check permissions
    if not proposal.group.is_member(current_user.id):
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify(proposal.to_dict())


@proposals_bp.route('/api/groups/<int:group_id>/proposals')
@login_required
def api_group_proposals(group_id):
    """API endpoint for group proposals"""
    group = Group.query.get_or_404(group_id)
    
    # Check permissions
    if not group.is_member(current_user.id):
        return jsonify({'error': 'Permission denied'}), 403
    
    status = request.args.get('status')
    limit = request.args.get('limit', 20, type=int)
    
    proposals = ContentProposal.get_group_proposals(group_id, status, limit)
    
    return jsonify({
        'proposals': [proposal.to_dict() for proposal in proposals],
        'total': len(proposals)
    })


@proposals_bp.route('/my-proposals')
@login_required
def my_proposals():
    """View current user's proposals"""
    page = request.args.get('page', 1, type=int)
    
    proposals = ContentProposal.query.filter_by(proposer_id=current_user.id).order_by(
        desc(ContentProposal.created_at)
    ).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('proposals/my_proposals.html', proposals=proposals)
