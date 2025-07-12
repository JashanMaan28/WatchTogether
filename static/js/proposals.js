// Proposal and Voting System JavaScript

class ProposalSystem {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
        this.initTooltips();
        this.initModals();
        this.startRealTimeUpdates();
    }

    bindEvents() {
        // Quick vote buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('.quick-vote-btn')) {
                this.handleQuickVote(e);
            }
        });

        // Proposal filters
        const filterForm = document.querySelector('#proposal-filters');
        if (filterForm) {
            filterForm.addEventListener('change', this.debounce(() => {
                this.applyFilters();
            }, 300));
        }

        // Search functionality
        const searchInput = document.querySelector('#proposal-search');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce((e) => {
                this.performSearch(e.target.value);
            }, 500));
        }

        // Auto-refresh for pending proposals
        this.setupAutoRefresh();
    }

    async handleQuickVote(event) {
        event.preventDefault();
        const button = event.target.closest('.quick-vote-btn');
        const proposalId = button.dataset.proposalId;
        const voteType = button.dataset.voteType;
        
        try {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

            const response = await fetch(`/proposals/${proposalId}/vote`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    vote_type: voteType,
                    comment: ''
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showNotification('Vote recorded successfully!', 'success');
                this.updateProposalCard(proposalId, result.proposal);
                this.disableVotingButtons(proposalId);
            } else {
                this.showNotification(result.message || 'Failed to record vote', 'error');
            }
        } catch (error) {
            console.error('Voting error:', error);
            this.showNotification('An error occurred while voting', 'error');
        } finally {
            button.disabled = false;
            this.resetButtonContent(button, voteType);
        }
    }

    updateProposalCard(proposalId, proposalData) {
        const card = document.querySelector(`[data-proposal-id="${proposalId}"]`);
        if (!card) return;

        // Update vote counts
        const upvoteCount = card.querySelector('.upvote-count');
        const downvoteCount = card.querySelector('.downvote-count');
        const approvalRate = card.querySelector('.approval-rate');

        if (upvoteCount) upvoteCount.textContent = proposalData.upvotes;
        if (downvoteCount) downvoteCount.textContent = proposalData.downvotes;
        if (approvalRate) approvalRate.textContent = `${proposalData.approval_rate.toFixed(1)}%`;

        // Update status if changed
        if (proposalData.status !== 'pending') {
            const statusBadge = card.querySelector('.status-badge');
            if (statusBadge) {
                statusBadge.textContent = proposalData.status.charAt(0).toUpperCase() + proposalData.status.slice(1);
                statusBadge.className = `badge status-badge ${this.getStatusBadgeClass(proposalData.status)}`;
            }
        }

        // Add animation to indicate update
        card.classList.add('proposal-updated');
        setTimeout(() => card.classList.remove('proposal-updated'), 2000);
    }

    disableVotingButtons(proposalId) {
        const buttons = document.querySelectorAll(`[data-proposal-id="${proposalId}"] .quick-vote-btn`);
        buttons.forEach(button => {
            button.disabled = true;
            button.classList.add('voted');
        });
    }

    resetButtonContent(button, voteType) {
        const iconClass = voteType === 'upvote' ? 'fa-thumbs-up' : 'fa-thumbs-down';
        button.innerHTML = `<i class="fas ${iconClass}"></i>`;
    }

    getStatusBadgeClass(status) {
        const classes = {
            'pending': 'bg-warning',
            'approved': 'bg-success', 
            'rejected': 'bg-danger',
            'expired': 'bg-secondary'
        };
        return classes[status] || 'bg-secondary';
    }

    async applyFilters() {
        const form = document.querySelector('#proposal-filters');
        const formData = new FormData(form);
        const params = new URLSearchParams(formData);
        
        try {
            const response = await fetch(`${window.location.pathname}?${params}`);
            const html = await response.text();
            
            // Update only the proposals list
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newProposalsList = doc.querySelector('#proposals-list');
            const currentProposalsList = document.querySelector('#proposals-list');
            
            if (newProposalsList && currentProposalsList) {
                currentProposalsList.innerHTML = newProposalsList.innerHTML;
                this.bindEvents(); // Re-bind events for new content
            }
        } catch (error) {
            console.error('Filter error:', error);
        }
    }

    async performSearch(query) {
        if (query.length < 2) return;
        
        try {
            const groupId = this.getGroupIdFromURL();
            const response = await fetch(`/api/groups/${groupId}/proposals?search=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            this.displaySearchResults(data.proposals);
        } catch (error) {
            console.error('Search error:', error);
        }
    }

    displaySearchResults(proposals) {
        const resultsContainer = document.querySelector('#search-results');
        if (!resultsContainer) return;

        if (proposals.length === 0) {
            resultsContainer.innerHTML = '<div class="text-center text-muted py-3">No proposals found</div>';
            return;
        }

        const html = proposals.map(proposal => this.createProposalCard(proposal)).join('');
        resultsContainer.innerHTML = html;
    }

    createProposalCard(proposal) {
        return `
            <div class="col-md-6 col-lg-4 mb-4">
                <div class="card h-100" data-proposal-id="${proposal.id}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <span class="badge status-badge ${this.getStatusBadgeClass(proposal.status)}">
                                ${proposal.status.charAt(0).toUpperCase() + proposal.status.slice(1)}
                            </span>
                            <small class="text-muted">${proposal.priority.charAt(0).toUpperCase() + proposal.priority.slice(1)}</small>
                        </div>
                        <h6 class="card-title">
                            <a href="/proposals/${proposal.id}" class="text-decoration-none">
                                ${proposal.content_title}
                            </a>
                        </h6>
                        <div class="row text-center mb-2">
                            <div class="col-4">
                                <div class="text-success">
                                    <i class="fas fa-thumbs-up"></i>
                                    <span class="upvote-count">${proposal.upvotes}</span>
                                </div>
                            </div>
                            <div class="col-4">
                                <div class="text-danger">
                                    <i class="fas fa-thumbs-down"></i>
                                    <span class="downvote-count">${proposal.downvotes}</span>
                                </div>
                            </div>
                            <div class="col-4">
                                <div class="text-info">
                                    <small class="approval-rate">${proposal.approval_rate.toFixed(1)}%</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    setupAutoRefresh() {
        // Auto-refresh pending proposals every 30 seconds
        if (window.location.pathname.includes('/proposals')) {
            setInterval(() => {
                this.refreshPendingProposals();
            }, 30000);
        }
    }

    async refreshPendingProposals() {
        try {
            const groupId = this.getGroupIdFromURL();
            const response = await fetch(`/api/groups/${groupId}/proposals?status=pending`);
            const data = await response.json();
            
            // Update only pending proposals
            data.proposals.forEach(proposal => {
                const card = document.querySelector(`[data-proposal-id="${proposal.id}"]`);
                if (card && proposal.status !== 'pending') {
                    this.updateProposalCard(proposal.id, proposal);
                }
            });
        } catch (error) {
            console.error('Auto-refresh error:', error);
        }
    }

    startRealTimeUpdates() {
        // If WebSocket support is available, implement real-time updates
        if (window.WebSocket) {
            this.setupWebSocket();
        }
    }

    setupWebSocket() {
        // WebSocket implementation for real-time proposal updates
        // This would require WebSocket support on the backend
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/proposals`;
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleRealTimeUpdate(data);
            };
            
            this.ws.onerror = (error) => {
                console.log('WebSocket error:', error);
            };
        } catch (error) {
            console.log('WebSocket not available');
        }
    }

    handleRealTimeUpdate(data) {
        switch (data.type) {
            case 'proposal_vote':
                this.updateProposalCard(data.proposal_id, data.proposal);
                break;
            case 'proposal_status_change':
                this.showNotification(`Proposal "${data.title}" has been ${data.status}`, 'info');
                this.updateProposalCard(data.proposal_id, data.proposal);
                break;
            case 'new_proposal':
                this.showNotification(`New proposal: "${data.title}"`, 'info');
                break;
        }
    }

    initTooltips() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    initModals() {
        // Initialize proposal-related modals
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            new bootstrap.Modal(modal);
        });
    }

    showNotification(message, type = 'info') {
        // Create and show notification
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    getCSRFToken() {
        return document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || 
               document.querySelector('input[name=csrf_token]')?.value || '';
    }

    getGroupIdFromURL() {
        const match = window.location.pathname.match(/\/groups\/(\d+)/);
        return match ? match[1] : null;
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Proposal form enhancements
class ProposalForm {
    constructor() {
        this.init();
    }

    init() {
        this.setupContentTypeToggle();
        this.setupFormValidation();
        this.setupContentSearch();
    }

    setupContentTypeToggle() {
        const contentTypeChoice = document.querySelector('#content-type-choice');
        if (!contentTypeChoice) return;

        contentTypeChoice.addEventListener('change', () => {
            this.toggleContentSections(contentTypeChoice.value);
        });

        // Initial setup
        this.toggleContentSections(contentTypeChoice.value);
    }

    toggleContentSections(choice) {
        const existingSection = document.querySelector('#existing-content-section');
        const newSection = document.querySelector('#new-content-section');

        if (choice === 'existing') {
            existingSection?.style.setProperty('display', 'block');
            newSection?.style.setProperty('display', 'none');
        } else {
            existingSection?.style.setProperty('display', 'none');
            newSection?.style.setProperty('display', 'block');
        }
    }

    setupFormValidation() {
        const form = document.querySelector('.proposal-form');
        if (!form) return;

        form.addEventListener('submit', (e) => {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    }

    setupContentSearch() {
        // Implementation for content search functionality
        const searchInput = document.querySelector('#content-search');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce((e) => {
                this.searchContent(e.target.value);
            }, 300));
        }
    }

    async searchContent(query) {
        if (query.length < 2) return;

        try {
            const response = await fetch(`/api/content/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            this.displayContentResults(data.content);
        } catch (error) {
            console.error('Content search error:', error);
        }
    }

    displayContentResults(content) {
        const resultsContainer = document.querySelector('#content-results');
        if (!resultsContainer) return;

        const html = content.map(item => `
            <div class="list-group-item list-group-item-action" onclick="selectContent(${item.id}, '${item.title}')">
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${item.title}</h6>
                    <small>${item.release_year || ''}</small>
                </div>
                <p class="mb-1">${item.content_type} ${item.genre ? '• ' + item.genre : ''}</p>
                <small>${item.description || ''}</small>
            </div>
        `).join('');

        resultsContainer.innerHTML = html;
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.proposalSystem = new ProposalSystem();
    window.proposalForm = new ProposalForm();
});

// CSS for animations
const style = document.createElement('style');
style.textContent = `
    .proposal-updated {
        animation: pulse 1s ease-in-out;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    
    .quick-vote-btn.voted {
        opacity: 0.6;
        cursor: not-allowed;
    }
    
    .proposal-card:hover {
        transform: translateY(-2px);
        transition: transform 0.2s ease;
    }
`;
document.head.appendChild(style);
