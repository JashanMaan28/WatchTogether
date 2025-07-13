/**
 * Recommendations System JavaScript
 * Handles user interactions, feedback, and real-time updates
 */

class RecommendationSystem {
    constructor() {
        this.init();
        // Make this instance globally accessible
        window.recommendationSystem = this;
    }

    init() {
        this.bindEvents();
        this.initializeTooltips();
        this.setupFeedbackModals();
        this.startPeriodicUpdates();
    }

    bindEvents() {
        // Feedback buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.feedback-btn')) {
                this.handleFeedbackClick(e.target.closest('.feedback-btn'));
            }
        });

        // Recommendation clicks
        document.addEventListener('click', (e) => {
            if (e.target.closest('.recommendation-card .btn')) {
                const card = e.target.closest('.recommendation-card');
                if (card && card.dataset.recommendationId) {
                    this.trackRecommendationClick(card.dataset.recommendationId);
                }
            }
        });

        // Generate recommendations
        document.addEventListener('click', (e) => {
            if (e.target.closest('.generate-recommendations-btn')) {
                this.generateRecommendations(e.target.closest('.generate-recommendations-btn'));
            }
        });

        // Algorithm selection
        const algorithmSelect = document.getElementById('algorithmSelect');
        if (algorithmSelect) {
            algorithmSelect.addEventListener('change', (e) => {
                this.handleAlgorithmChange(e.target.value);
            });
        }

        // Preference updates
        const preferenceForm = document.getElementById('preferenceForm');
        if (preferenceForm) {
            preferenceForm.addEventListener('submit', (e) => {
                this.handlePreferenceUpdate(e);
            });
        }
    }

    handleFeedbackClick(button) {
        const recommendationId = button.dataset.recommendationId;
        const feedbackType = button.dataset.feedbackType;
        
        // Show feedback modal for detailed feedback
        this.showFeedbackModal(recommendationId, feedbackType);
    }

    showFeedbackModal(recommendationId, feedbackType) {
        const modal = document.getElementById('feedbackModal');
        if (!modal) {
            // If no modal, submit simple feedback
            this.submitFeedback(recommendationId, feedbackType);
            return;
        }

        const modalInstance = new bootstrap.Modal(modal);
        
        // Set modal data
        document.getElementById('feedbackRecommendationId').value = recommendationId;
        document.getElementById('feedbackType').value = feedbackType;
        
        // Update modal title based on feedback type
        const modalTitle = modal.querySelector('.modal-title');
        const feedbackTypeNames = {
            'like': 'Why did you like this?',
            'dislike': 'Why didn\'t you like this?',
            'not_interested': 'Why are you not interested?',
            'already_seen': 'Already seen this content?'
        };
        modalTitle.textContent = feedbackTypeNames[feedbackType] || 'Feedback';
        
        modalInstance.show();
    }

    async submitFeedback(recommendationId, feedbackType, comment = '') {
        console.log('RecommendationSystem.submitFeedback called with:', { recommendationId, feedbackType, comment });
        
        try {
            const csrfToken = document.querySelector('meta[name=csrf-token]');
            
            if (!csrfToken) {
                console.error('CSRF token not found in page');
                throw new Error('CSRF token not found');
            }

            console.log('CSRF token found:', csrfToken.getAttribute('content'));
            console.log('Submitting feedback:', { recommendationId, feedbackType, comment });
            
            const response = await fetch('/recommendations/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken.getAttribute('content')
                },
                body: JSON.stringify({
                    recommendation_id: parseInt(recommendationId),
                    feedback_type: feedbackType,
                    comment: comment
                })
            });

            console.log('Response status:', response.status);
            
            if (!response.ok) {
                const errorData = await response.json();
                console.error('Server error response:', errorData);
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();
            console.log('Server response:', data);
            
            if (data.success) {
                this.updateFeedbackUI(recommendationId, feedbackType);
                this.showAlert('Feedback recorded successfully!', 'success');
                
                // Close modal if open
                const modal = bootstrap.Modal.getInstance(document.getElementById('feedbackModal'));
                if (modal) {
                    modal.hide();
                }
            } else {
                throw new Error(data.error || 'Unknown error occurred');
            }
        } catch (error) {
            console.error('Error submitting feedback:', error);
            this.showAlert('Error recording feedback: ' + error.message, 'danger');
        }
    }

    updateFeedbackUI(recommendationId, feedbackType) {
        // Update button states
        const buttons = document.querySelectorAll(`[data-recommendation-id="${recommendationId}"]`);
        buttons.forEach(btn => {
            if (btn.classList.contains('feedback-btn')) {
                btn.classList.remove('selected');
                if (btn.dataset.feedbackType === feedbackType) {
                    btn.classList.add('selected');
                    btn.disabled = true;
                    
                    // Add visual feedback
                    const icon = btn.querySelector('i');
                    if (icon) {
                        icon.classList.add('animate__animated', 'animate__bounce');
                        setTimeout(() => {
                            icon.classList.remove('animate__animated', 'animate__bounce');
                        }, 1000);
                    }
                }
            }
        });

        // Update recommendation card appearance
        const card = document.querySelector(`[data-recommendation-id="${recommendationId}"]`);
        if (card) {
            card.classList.add('feedback-provided');
            
            // Add feedback indicator
            if (!card.querySelector('.feedback-indicator')) {
                const indicator = document.createElement('div');
                indicator.className = 'feedback-indicator';
                indicator.innerHTML = this.getFeedbackIcon(feedbackType);
                card.querySelector('.card-body').appendChild(indicator);
            }
        }
    }

    getFeedbackIcon(feedbackType) {
        const icons = {
            'like': '<i class="fas fa-thumbs-up text-success"></i>',
            'dislike': '<i class="fas fa-thumbs-down text-danger"></i>',
            'not_interested': '<i class="fas fa-times text-warning"></i>',
            'already_seen': '<i class="fas fa-eye text-info"></i>'
        };
        return icons[feedbackType] || '';
    }

    async trackRecommendationClick(recommendationId) {
        try {
            const csrfToken = document.querySelector('meta[name=csrf-token]');
            
            if (!csrfToken) {
                return; // Silently fail for click tracking
            }
            
            await fetch('/recommendations/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken.getAttribute('content')
                },
                body: JSON.stringify({
                    recommendation_id: parseInt(recommendationId),
                    feedback_type: 'clicked'
                })
            });
        } catch (error) {
            console.error('Error tracking click:', error);
            // Don't show user error for click tracking
        }
    }

    generateRecommendations(button) {
        const algorithm = button.dataset.algorithm || 'hybrid';
        const limit = button.dataset.limit || 10;
        const groupId = button.dataset.groupId;
        
        // Show loading state
        button.disabled = true;
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Generating...';
        
        let url = '/recommendations/generate';
        const params = new URLSearchParams({
            algorithm: algorithm,
            limit: limit
        });
        
        if (groupId) {
            url = `/recommendations/group/${groupId}/generate`;
        }
        
        fetch(`${url}?${params}`)
        .then(response => {
            if (response.redirected) {
                window.location.href = response.url;
            } else {
                return response.json();
            }
        })
        .then(data => {
            if (data && data.error) {
                this.showAlert('Error generating recommendations: ' + data.error, 'danger');
            } else {
                // Refresh the page to show new recommendations
                window.location.reload();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.showAlert('Error generating recommendations', 'danger');
        })
        .finally(() => {
            // Restore button state
            button.disabled = false;
            button.innerHTML = originalText;
        });
    }

    handleAlgorithmChange(algorithm) {
        // Update UI to reflect algorithm choice
        const algorithmInfo = {
            'hybrid': 'Combines multiple recommendation approaches for best results',
            'content_based': 'Recommends based on content you\'ve liked before',
            'collaborative': 'Recommends based on similar users\' preferences',
            'trending': 'Shows what\'s popular and trending now',
            'group_consensus': 'Finds content that appeals to your group'
        };
        
        const infoElement = document.getElementById('algorithmInfo');
        if (infoElement) {
            infoElement.textContent = algorithmInfo[algorithm] || '';
        }
    }

    handlePreferenceUpdate(e) {
        e.preventDefault();
        
        const form = e.target;
        const formData = new FormData(form);
        const submitButton = form.querySelector('button[type="submit"]');
        
        // Show loading state
        submitButton.disabled = true;
        const originalText = submitButton.innerHTML;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';
        
        fetch(form.action, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.redirected) {
                window.location.href = response.url;
            } else {
                return response.text();
            }
        })
        .then(html => {
            if (html) {
                // Update page content if needed
                this.showAlert('Preferences updated successfully!', 'success');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.showAlert('Error updating preferences', 'danger');
        })
        .finally(() => {
            // Restore button state
            submitButton.disabled = false;
            submitButton.innerHTML = originalText;
        });
    }

    showAlert(message, type) {
        // Remove existing alerts
        const existingAlerts = document.querySelectorAll('.alert.recommendation-alert');
        existingAlerts.forEach(alert => alert.remove());
        
        // Create new alert
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show recommendation-alert`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insert at top of main content
        const container = document.querySelector('.container-fluid, .container');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
        }
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }

    initializeTooltips() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    setupFeedbackModals() {
        // Setup feedback modal submission
        const submitFeedbackBtn = document.getElementById('submitFeedbackBtn');
        if (submitFeedbackBtn) {
            submitFeedbackBtn.addEventListener('click', () => {
                const recommendationId = document.getElementById('feedbackRecommendationId').value;
                const feedbackType = document.getElementById('feedbackType').value;
                const comment = document.getElementById('feedbackComment').value;
                
                this.submitFeedback(recommendationId, feedbackType, comment);
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('feedbackModal'));
                if (modal) {
                    modal.hide();
                }
            });
        }
    }

    startPeriodicUpdates() {
        // Periodically update recommendation metrics (every 5 minutes)
        setInterval(() => {
            this.updateMetrics();
        }, 5 * 60 * 1000);
    }

    updateMetrics() {
        // Fetch and update recommendation metrics
        fetch('/recommendations/api/metrics')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.updateMetricsUI(data.metrics);
            }
        })
        .catch(error => console.error('Error updating metrics:', error));
    }

    updateMetricsUI(metrics) {
        // Update metrics display
        const elements = {
            'totalRecommendations': document.getElementById('totalRecommendations'),
            'viewRate': document.getElementById('viewRate'),
            'clickRate': document.getElementById('clickRate'),
            'likeRate': document.getElementById('likeRate')
        };
        
        Object.keys(elements).forEach(key => {
            const element = elements[key];
            if (element && metrics[key] !== undefined) {
                element.textContent = metrics[key];
                
                // Add animation for value changes
                element.classList.add('metric-updated');
                setTimeout(() => {
                    element.classList.remove('metric-updated');
                }, 1000);
            }
        });
    }

    // API methods for external use
    async getRecommendations(options = {}) {
        const params = new URLSearchParams({
            algorithm: options.algorithm || 'hybrid',
            limit: options.limit || 10,
            ...(options.groupId && { group_id: options.groupId })
        });
        
        const response = await fetch(`/recommendations/api/recommendations?${params}`);
        return await response.json();
    }
}

// Initialize recommendation system when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.recommendationSystem = new RecommendationSystem();
    
    // Global helper functions for template usage
    window.submitFeedback = function(recommendationId, feedbackType, comment = '') {
        console.log('Global submitFeedback called with:', { recommendationId, feedbackType, comment });
        
        if (window.recommendationSystem) {
            console.log('Using recommendationSystem instance');
            window.recommendationSystem.submitFeedback(recommendationId, feedbackType, comment);
        } else {
            console.error('RecommendationSystem not initialized');
        }
    };
    
    window.trackRecommendationClick = function(recommendationId) {
        if (window.recommendationSystem) {
            window.recommendationSystem.trackRecommendationClick(recommendationId);
        } else {
            console.error('RecommendationSystem not initialized');
        }
    };
});

// Animation utilities
function animateCountUp(element, target, duration = 1000) {
    const start = parseInt(element.textContent) || 0;
    const increment = (target - start) / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= target) || (increment < 0 && current <= target)) {
            current = target;
            clearInterval(timer);
        }
        element.textContent = Math.round(current);
    }, 16);
}

// CSS class additions for dynamic styling
document.head.insertAdjacentHTML('beforeend', `
<style>
.metric-updated {
    animation: pulse 0.5s ease-in-out;
}

@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.05); }
    100% { transform: scale(1); }
}

.feedback-provided {
    border: 2px solid #28a745;
    background-color: rgba(40, 167, 69, 0.05);
}

.feedback-indicator {
    position: absolute;
    top: 10px;
    right: 10px;
    background: rgba(255, 255, 255, 0.9);
    border-radius: 50%;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.recommendation-alert {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1050;
    min-width: 300px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
</style>
`);
