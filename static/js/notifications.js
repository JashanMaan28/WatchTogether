// Simple notification management system
class NotificationManager {
    constructor() {
        this.loadingModal = null;
        this.init();
    }

    init() {
        const modalElement = document.getElementById('loadingModal');
        if (modalElement) {
            this.loadingModal = new bootstrap.Modal(modalElement);
        }

        this.bindEventListeners();
    }

    bindEventListeners() {
        document.querySelectorAll('.accept-friend-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleAcceptFriend(e));
        });

        document.querySelectorAll('.decline-friend-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleDeclineFriend(e));
        });

        document.querySelectorAll('.dismiss-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleDismissNotification(e));
        });

        const markAllBtn = document.getElementById('markAllBtn');
        if (markAllBtn) {
            markAllBtn.addEventListener('click', (e) => this.handleMarkAllAsRead(e));
        }
    }

    showLoading() {
        if (this.loadingModal) {
            this.loadingModal.show();
        }
    }

    hideLoading() {
        if (this.loadingModal) {
            this.loadingModal.hide();
        }
    }

    showToast(message, type = 'success') {
        const toastId = 'toast-' + Date.now();
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type} border-0" id="${toastId}" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        let toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            // Create toast container if it doesn't exist
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '11000';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 4000 });
        toast.show();
        
        // Remove toast element after it's hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }

    async makeApiCall(url, data) {
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(data),
            credentials: 'same-origin'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    async handleAcceptFriend(event) {
        const button = event.target.closest('.accept-friend-btn');
        const userId = button.dataset.userId;
        const userName = button.dataset.userName;
        const notificationId = button.dataset.notificationId;

        if (!userId) {
            this.showToast('Error: Missing user information', 'danger');
            return;
        }

        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="bi bi-hourglass-split"></i> Accepting...';
        this.showLoading();

        try {
            const result = await this.makeApiCall('/auth/api/friend-request/accept', { user_id: userId });

            if (result.success) {
                this.showToast(`✅ Accepted friend request from ${userName}!`, 'success');
                this.removeNotificationActions(notificationId);
                this.markNotificationAsRead(notificationId);
                this.hideLoading(); // Hide modal after actions removed
            } else {
                throw new Error(result.message || 'Failed to accept friend request');
            }

        } catch (error) {
            this.showToast(`❌ Error: ${error.message}`, 'danger');
            button.disabled = false;
            button.innerHTML = originalText;
            this.hideLoading();
        }
    }

    async handleDeclineFriend(event) {
        const button = event.target.closest('.decline-friend-btn');
        const userId = button.dataset.userId;
        const userName = button.dataset.userName;
        const notificationId = button.dataset.notificationId;

        if (!userId) {
            this.showToast('Error: Missing user information', 'danger');
            return;
        }

        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="bi bi-hourglass-split"></i> Declining...';
        this.showLoading();

        try {
            const result = await this.makeApiCall('/auth/api/friend-request/decline', { user_id: userId });

            if (result.success) {
                this.showToast(`Declined friend request from ${userName}`, 'info');
                this.removeNotificationActions(notificationId);
                this.markNotificationAsRead(notificationId);
                this.hideLoading(); // Hide modal after actions removed
            } else {
                throw new Error(result.message || 'Failed to decline friend request');
            }

        } catch (error) {
            this.showToast(`❌ Error: ${error.message}`, 'danger');
            button.disabled = false;
            button.innerHTML = originalText;
            this.hideLoading();
        }
    }

    async handleDismissNotification(event) {
        const button = event.target.closest('.dismiss-btn');
        const notificationId = button.dataset.notificationId;

        if (!notificationId) {
            this.showToast('Error: Missing notification ID', 'danger');
            return;
        }

        button.disabled = true;

        try {
            const result = await this.makeApiCall(`/auth/api/notifications/${notificationId}/mark-read`, {});

            if (result.success) {
                this.markNotificationAsRead(notificationId);
                this.showToast('📫 Notification marked as read', 'success');
            } else {
                throw new Error(result.message || 'Failed to mark notification as read');
            }

        } catch (error) {
            this.showToast(`❌ Error: ${error.message}`, 'danger');
            button.disabled = false;
        }
    }

    async handleMarkAllAsRead(event) {
        const button = event.target.closest('#markAllBtn');
        
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="bi bi-hourglass-split"></i> Processing...';
        this.showLoading();

        try {
            const result = await this.makeApiCall('/auth/api/notifications/mark-all-read', {});

            if (result.success) {
                // Mark all notifications as read in UI
                document.querySelectorAll('.notification-item').forEach(item => {
                    this.markNotificationAsReadElement(item);
                });

                this.showToast('📫 All notifications marked as read', 'success');
                button.style.display = 'none';
            } else {
                throw new Error(result.message || 'Failed to mark all notifications as read');
            }

        } catch (error) {
            this.showToast(`❌ Error: ${error.message}`, 'danger');
            button.disabled = false;
            button.innerHTML = originalText;
        } finally {
            this.hideLoading();
        }
    }

    removeNotificationActions(notificationId) {
        const actionsElement = document.getElementById(`actions-${notificationId}`);
        if (actionsElement) {
            actionsElement.remove();
        }
    }

    markNotificationAsRead(notificationId) {
        const notificationElement = document.getElementById(`notification-${notificationId}`);
        if (notificationElement) {
            this.markNotificationAsReadElement(notificationElement);
        }
    }

    markNotificationAsReadElement(element) {
        // Remove highlight
        element.classList.remove('bg-light');
        
        // Remove "New" badge
        const badge = element.querySelector('.badge');
        if (badge) {
            badge.remove();
        }
        
        // Remove dismiss button
        const dismissBtn = element.querySelector('.dismiss-btn');
        if (dismissBtn) {
            dismissBtn.remove();
        }
        
        // Remove bold from title
        const title = element.querySelector('h6');
        if (title) {
            title.classList.remove('fw-bold');
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    window.notificationManager = new NotificationManager();
});
