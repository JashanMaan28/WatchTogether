/**
 * Real-time Discussion Updates
 * Handles live updates, notifications, and interactive features for discussions
 */

class DiscussionManager {
    constructor() {
        this.lastUpdate = new Date().toISOString();
        this.pollInterval = null;
        this.notificationCount = 0;
        this.isPolling = false;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.startPolling();
        this.loadNotifications();
        this.setupSpoilerToggles();
        this.setupFormHandlers();
    }
    
    setupEventListeners() {
        // Page visibility change handling
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopPolling();
            } else {
                this.startPolling();
                this.markNotificationsAsRead();
            }
        });
        
        // Like/dislike buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.like-btn, .dislike-btn')) {
                this.handleLikeDislike(e);
            }
        });
        
        // Reply buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.reply-btn')) {
                this.toggleReplyForm(e);
            }
        });
        
        // Spoiler toggles
        document.addEventListener('click', (e) => {
            if (e.target.closest('.spoiler-toggle')) {
                this.toggleSpoiler(e);
            }
        });
        
        // Share buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.share-btn')) {
                this.shareDiscussion(e);
            }
        });
    }
    
    startPolling() {
        if (this.isPolling) return;
        
        this.isPolling = true;
        this.pollInterval = setInterval(() => {
            this.checkForUpdates();
        }, 30000); // Poll every 30 seconds
    }
    
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        this.isPolling = false;
    }
    
    async checkForUpdates() {
        if (document.hidden) return;
        
        try {
            const path = window.location.pathname;
            let apiUrl = '';
            
            // Determine the correct API endpoint based on current page
            if (path.includes('/discussions/content/')) {
                const contentId = path.split('/').pop();
                apiUrl = `/discussions/api/recent/${contentId}?since=${this.lastUpdate}&limit=5`;
            } else if (path.includes('/discussions/group/')) {
                const groupId = path.split('/').pop();
                apiUrl = `/discussions/api/recent/group/${groupId}?since=${this.lastUpdate}&limit=5`;
            } else {
                return; // Not on a discussion page
            }
            
            const response = await fetch(apiUrl);
            const discussions = await response.json();
            
            if (discussions.length > 0) {
                this.lastUpdate = new Date().toISOString();
                this.showNewDiscussionNotification(discussions.length);
            }
        } catch (error) {
            console.error('Error checking for updates:', error);
        }
    }
    
    async loadNotifications() {
        try {
            const response = await fetch('/discussions/api/notifications?unread_only=true');
            const notifications = await response.json();
            
            this.updateNotificationBadge(notifications.length);
            this.displayNotifications(notifications);
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }
    
    updateNotificationBadge(count) {
        this.notificationCount = count;
        const badge = document.getElementById('notification-badge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }
        }
        
        // Update page title
        if (count > 0) {
            document.title = `(${count}) ${document.title.replace(/^\(\d+\)\s/, '')}`;
        } else {
            document.title = document.title.replace(/^\(\d+\)\s/, '');
        }
    }
    
    displayNotifications(notifications) {
        const container = document.getElementById('notifications-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (notifications.length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-3">No new notifications</div>';
            return;
        }
        
        notifications.slice(0, 10).forEach(notification => {
            const notificationEl = this.createNotificationElement(notification);
            container.appendChild(notificationEl);
        });
    }
    
    createNotificationElement(notification) {
        const div = document.createElement('div');
        div.className = 'notification-item d-flex align-items-start p-3 border-bottom';
        div.dataset.notificationId = notification.id;
        
        const timeAgo = this.timeAgo(new Date(notification.created_at));
        
        div.innerHTML = `
            <div class="me-3">
                <img src="${notification.trigger_user.profile_picture ? 
                    `/static/uploads/profile_pics/${notification.trigger_user.profile_picture}` : 
                    '/static/images/default_avatar.svg'}" 
                     alt="${notification.trigger_user.username}" 
                     class="rounded-circle" style="width: 40px; height: 40px; object-fit: cover;">
            </div>
            <div class="flex-grow-1">
                <div class="mb-1">
                    <strong>${notification.trigger_user.full_name || notification.trigger_user.username}</strong>
                    ${notification.message}
                </div>
                <small class="text-muted">${timeAgo}</small>
            </div>
            <div class="ms-2">
                <button type="button" class="btn btn-sm btn-outline-primary" onclick="discussionManager.viewDiscussion(${notification.discussion_id}, ${notification.id})">
                    View
                </button>
            </div>
        `;
        
        return div;
    }
    
    async viewDiscussion(discussionId, notificationId) {
        // Mark notification as read
        try {
            await fetch(`/discussions/api/notifications/${notificationId}/read`, { method: 'POST' });
            this.loadNotifications(); // Refresh notifications
        } catch (error) {
            console.error('Error marking notification as read:', error);
        }
        
        // Navigate to discussion
        window.location.href = `/discussions/thread/${discussionId}`;
    }
    
    async markNotificationsAsRead() {
        const unreadNotifications = document.querySelectorAll('.notification-item[data-notification-id]');
        
        for (const notificationEl of unreadNotifications) {
            const notificationId = notificationEl.dataset.notificationId;
            try {
                await fetch(`/discussions/api/notifications/${notificationId}/read`, { method: 'POST' });
            } catch (error) {
                console.error('Error marking notification as read:', error);
            }
        }
        
        setTimeout(() => this.loadNotifications(), 1000);
    }
    
    showNewDiscussionNotification(count) {
        // Remove existing notifications
        const existingNotifications = document.querySelectorAll('.new-discussion-notification');
        existingNotifications.forEach(n => n.remove());
        
        const notification = document.createElement('div');
        notification.className = 'new-discussion-notification alert alert-info alert-dismissible fade show position-fixed';
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 350px;';
        
        notification.innerHTML = `
            <i class="fas fa-comments me-2"></i>
            <strong>${count} new discussion${count > 1 ? 's' : ''} available</strong>
            <button type="button" class="btn btn-sm btn-info ms-2" onclick="location.reload()">
                <i class="fas fa-refresh"></i> Refresh
            </button>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 10000);
    }
    
    async handleLikeDislike(e) {
        e.preventDefault();
        const btn = e.target.closest('.like-btn, .dislike-btn');
        const discussionId = btn.dataset.discussionId;
        const action = btn.dataset.action;
        const currentReaction = btn.style.backgroundColor ? action : null;
        const newAction = currentReaction === action ? 'remove' : action;
        
        try {
            const response = await fetch(`/discussions/like/${discussionId}/${newAction}`, {
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            
            if (data.success) {
                this.updateLikeButtons(discussionId, data);
                this.showFeedback(btn, newAction === 'remove' ? 'Reaction removed' : `${action}d!`);
            }
        } catch (error) {
            console.error('Error updating reaction:', error);
            this.showError('Failed to update reaction');
        }
    }
    
    updateLikeButtons(discussionId, data) {
        const likeBtn = document.querySelector(`.like-btn[data-discussion-id="${discussionId}"]`);
        const dislikeBtn = document.querySelector(`.dislike-btn[data-discussion-id="${discussionId}"]`);
        
        if (likeBtn && dislikeBtn) {
            // Update counts
            likeBtn.querySelector('.like-count').textContent = data.like_count;
            dislikeBtn.querySelector('.dislike-count').textContent = data.dislike_count;
            
            // Reset styles
            [likeBtn, dislikeBtn].forEach(btn => {
                btn.style.backgroundColor = '';
                btn.style.color = '';
            });
            
            // Apply active styles
            if (data.user_reaction === 'like') {
                likeBtn.style.backgroundColor = '#198754';
                likeBtn.style.color = 'white';
            } else if (data.user_reaction === 'dislike') {
                dislikeBtn.style.backgroundColor = '#dc3545';
                dislikeBtn.style.color = 'white';
            }
        }
    }
    
    toggleReplyForm(e) {
        const btn = e.target.closest('.reply-btn');
        const discussionId = btn.dataset.discussionId;
        const replyForm = document.getElementById(`reply-form-${discussionId}`);
        
        if (replyForm) {
            const isVisible = replyForm.style.display !== 'none';
            replyForm.style.display = isVisible ? 'none' : 'block';
            
            if (!isVisible) {
                const textarea = replyForm.querySelector('textarea');
                if (textarea) {
                    textarea.focus();
                }
            }
        }
    }
    
    setupSpoilerToggles() {
        document.querySelectorAll('.spoiler-toggle').forEach(btn => {
            btn.addEventListener('click', this.toggleSpoiler.bind(this));
        });
    }
    
    toggleSpoiler(e) {
        const btn = e.target.closest('.spoiler-toggle');
        const container = btn.closest('.spoiler-container');
        const content = container.querySelector('.spoiler-content');
        
        if (content.style.display === 'none') {
            content.style.display = 'block';
            btn.innerHTML = '<i class="fas fa-eye-slash"></i> Hide Spoilers';
            btn.classList.remove('btn-outline-warning');
            btn.classList.add('btn-warning');
        } else {
            content.style.display = 'none';
            btn.innerHTML = '<i class="fas fa-eye"></i> Show Spoilers';
            btn.classList.remove('btn-warning');
            btn.classList.add('btn-outline-warning');
        }
    }
    
    async shareDiscussion(e) {
        const btn = e.target.closest('.share-btn');
        const discussionId = btn.dataset.discussionId;
        const url = `${window.location.origin}/discussions/thread/${discussionId}`;
        
        if (navigator.share) {
            try {
                await navigator.share({
                    title: 'Discussion',
                    text: 'Check out this discussion',
                    url: url
                });
            } catch (error) {
                if (error.name !== 'AbortError') {
                    this.fallbackShare(btn, url);
                }
            }
        } else {
            this.fallbackShare(btn, url);
        }
    }
    
    async fallbackShare(btn, url) {
        try {
            await navigator.clipboard.writeText(url);
            this.showFeedback(btn, 'Link copied!');
        } catch (error) {
            // Show share modal as last resort
            this.showShareModal(url);
        }
    }
    
    showShareModal(url) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Share Discussion</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="input-group">
                            <input type="text" class="form-control" value="${url}" readonly>
                            <button class="btn btn-primary" onclick="navigator.clipboard.writeText('${url}')">
                                Copy
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    }
    
    setupFormHandlers() {
        // Auto-resize textareas
        document.querySelectorAll('textarea').forEach(textarea => {
            textarea.addEventListener('input', () => {
                textarea.style.height = 'auto';
                textarea.style.height = textarea.scrollHeight + 'px';
            });
        });
        
        // Cancel reply buttons
        document.querySelectorAll('.cancel-reply-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const form = e.target.closest('.reply-form');
                form.style.display = 'none';
                form.querySelector('textarea').value = '';
            });
        });
        
        // Form submission with loading states
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', (e) => {
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Posting...';
                }
            });
        });
    }
    
    showFeedback(element, message) {
        const originalContent = element.innerHTML;
        element.innerHTML = `<i class="fas fa-check"></i> ${message}`;
        element.classList.add('btn-success');
        
        setTimeout(() => {
            element.innerHTML = originalContent;
            element.classList.remove('btn-success');
        }, 2000);
    }
    
    showError(message) {
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-danger border-0 position-fixed';
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999;';
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
    
    timeAgo(date) {
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) return 'just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)}d ago`;
        
        return date.toLocaleDateString();
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.discussionManager = new DiscussionManager();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.discussionManager) {
        window.discussionManager.stopPolling();
    }
});
