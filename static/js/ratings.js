/**
 * Rating and Review System JavaScript
 */

// Star Rating Interactivity
function initializeStarRating() {
    const starRatingInputs = document.querySelectorAll('.star-rating-input');
    
    starRatingInputs.forEach(ratingInput => {
        const stars = ratingInput.querySelectorAll('label');
        const radioInputs = ratingInput.querySelectorAll('input[type="radio"]');
        
        stars.forEach((star, index) => {
            // Hover effect
            star.addEventListener('mouseenter', () => {
                highlightStars(stars, index);
            });
            
            // Reset on mouse leave
            ratingInput.addEventListener('mouseleave', () => {
                const checkedInput = ratingInput.querySelector('input[type="radio"]:checked');
                if (checkedInput) {
                    const checkedIndex = Array.from(radioInputs).indexOf(checkedInput);
                    highlightStars(stars, checkedIndex);
                } else {
                    clearStars(stars);
                }
            });
            
            // Click handler
            star.addEventListener('click', () => {
                highlightStars(stars, index);
            });
        });
        
        // Initialize with current selection
        const checkedInput = ratingInput.querySelector('input[type="radio"]:checked');
        if (checkedInput) {
            const checkedIndex = Array.from(radioInputs).indexOf(checkedInput);
            highlightStars(stars, checkedIndex);
        }
    });
}

function highlightStars(stars, upToIndex) {
    stars.forEach((star, index) => {
        if (index <= upToIndex) {
            star.style.color = '#ffc107';
        } else {
            star.style.color = '#ddd';
        }
    });
}

function clearStars(stars) {
    stars.forEach(star => {
        star.style.color = '#ddd';
    });
}

// Review Helpfulness Voting
async function voteReviewHelpfulness(ratingId, isHelpful) {
    try {
        const response = await fetch(`/review/${ratingId}/vote`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ is_helpful: isHelpful })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to vote');
        }
        
        const data = await response.json();
        
        // Update the UI
        updateHelpfulnessDisplay(ratingId, data);
        updateVoteButtons(ratingId, isHelpful);
        
        // Show success message
        showNotification('Vote recorded successfully!', 'success');
        
    } catch (error) {
        console.error('Error voting on review:', error);
        showNotification(error.message || 'Failed to vote on review', 'error');
    }
}

function updateHelpfulnessDisplay(ratingId, data) {
    const helpfulCount = document.getElementById(`helpful-count-${ratingId}`);
    const totalCount = document.getElementById(`total-count-${ratingId}`);
    const percentage = document.getElementById(`percentage-${ratingId}`);
    
    if (helpfulCount) helpfulCount.textContent = data.helpful_votes;
    if (totalCount) totalCount.textContent = data.total_votes;
    if (percentage) percentage.textContent = data.helpfulness_percentage;
}

function updateVoteButtons(ratingId, isHelpful) {
    const reviewCard = document.querySelector(`[data-review-id="${ratingId}"]`);
    if (!reviewCard) return;
    
    const helpfulBtn = reviewCard.querySelector('.vote-helpful');
    const notHelpfulBtn = reviewCard.querySelector('.vote-not-helpful');
    
    // Reset button classes
    if (helpfulBtn) {
        helpfulBtn.className = 'vote-btn vote-helpful';
        if (isHelpful) helpfulBtn.classList.add('helpful');
    }
    
    if (notHelpfulBtn) {
        notHelpfulBtn.className = 'vote-btn vote-not-helpful';
        if (!isHelpful) notHelpfulBtn.classList.add('not-helpful');
    }
}

// Spoiler Toggle
function toggleSpoiler(reviewId) {
    const spoilerContent = document.getElementById(`review-text-${reviewId}`);
    const toggleBtn = document.querySelector(`[onclick="toggleSpoiler(${reviewId})"]`);
    
    if (!spoilerContent || !toggleBtn) return;
    
    if (spoilerContent.classList.contains('hidden')) {
        spoilerContent.classList.remove('hidden');
        spoilerContent.classList.add('revealed');
        toggleBtn.textContent = 'Hide Spoilers';
    } else {
        spoilerContent.classList.add('hidden');
        spoilerContent.classList.remove('revealed');
        toggleBtn.textContent = 'Show Review';
    }
}

// Rating Form Validation
function validateRatingForm() {
    const ratingInputs = document.querySelectorAll('input[name="rating"]');
    const selectedRating = Array.from(ratingInputs).find(input => input.checked);
    
    if (!selectedRating) {
        showNotification('Please select a rating before submitting', 'error');
        return false;
    }
    
    const ratingValue = parseInt(selectedRating.value);
    if (ratingValue < 1 || ratingValue > 5) {
        showNotification('Rating must be between 1 and 5 stars', 'error');
        return false;
    }
    
    return true;
}

// Content Rating Quick Actions
async function quickRate(contentId, rating) {
    try {
        const response = await fetch('/api/content/rate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                content_id: contentId,
                rating: rating,
                review_text: '',
                is_public: true
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to rate content');
        }
        
        const data = await response.json();
        showNotification(`Rated ${rating} stars!`, 'success');
        
        // Refresh rating display
        window.location.reload();
        
    } catch (error) {
        console.error('Error rating content:', error);
        showNotification(error.message || 'Failed to rate content', 'error');
    }
}

// Load Rating Statistics
async function loadRatingStatistics(contentId) {
    try {
        const response = await fetch(`/api/content/${contentId}/statistics`);
        
        if (!response.ok) {
            throw new Error('Failed to load rating statistics');
        }
        
        const data = await response.json();
        updateRatingStatisticsDisplay(data);
        
    } catch (error) {
        console.error('Error loading rating statistics:', error);
    }
}

function updateRatingStatisticsDisplay(stats) {
    // Update overall rating
    const avgRating = document.getElementById('average-rating');
    if (avgRating && stats.average_rating) {
        avgRating.textContent = stats.average_rating.toFixed(1);
    }
    
    // Update rating count
    const ratingCount = document.getElementById('rating-count');
    if (ratingCount) {
        ratingCount.textContent = `${stats.total_ratings} rating${stats.total_ratings !== 1 ? 's' : ''}`;
    }
    
    // Update review count
    const reviewCount = document.getElementById('review-count');
    if (reviewCount) {
        reviewCount.textContent = `${stats.total_reviews} review${stats.total_reviews !== 1 ? 's' : ''}`;
    }
    
    // Update rating distribution
    const distribution = stats.rating_distribution;
    if (distribution && distribution.percentages) {
        for (let rating = 1; rating <= 5; rating++) {
            const bar = document.getElementById(`rating-bar-${rating}`);
            const count = document.getElementById(`rating-count-${rating}`);
            
            if (bar) {
                bar.style.width = `${distribution.percentages[rating]}%`;
            }
            if (count) {
                count.textContent = distribution.counts[rating];
            }
        }
    }
}

// Notification System
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        max-width: 500px;
    `;
    
    notification.innerHTML = `
        <div>${message}</div>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Confirmation Dialogs
function confirmDeleteRating(ratingId) {
    if (confirm('Are you sure you want to delete your rating? This action cannot be undone.')) {
        document.getElementById(`delete-rating-form-${ratingId}`).submit();
    }
}

function confirmDeleteReview(reviewId) {
    if (confirm('Are you sure you want to delete your review? This action cannot be undone.')) {
        document.getElementById(`delete-review-form-${reviewId}`).submit();
    }
}

// Pagination and Sorting
function updateReviewSort(contentId, sortBy) {
    const currentUrl = new URL(window.location);
    currentUrl.searchParams.set('sort', sortBy);
    currentUrl.searchParams.delete('page'); // Reset to first page
    window.location.href = currentUrl.toString();
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeStarRating();
    
    // Add click handlers for vote buttons
    document.querySelectorAll('.vote-helpful').forEach(btn => {
        btn.addEventListener('click', function() {
            const ratingId = this.dataset.ratingId;
            voteReviewHelpfulness(ratingId, true);
        });
    });
    
    document.querySelectorAll('.vote-not-helpful').forEach(btn => {
        btn.addEventListener('click', function() {
            const ratingId = this.dataset.ratingId;
            voteReviewHelpfulness(ratingId, false);
        });
    });
    
    // Add form validation
    const ratingForms = document.querySelectorAll('.rating-form');
    ratingForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateRatingForm()) {
                e.preventDefault();
            }
        });
    });
    
    // Load rating statistics if content ID is available
    const contentId = document.body.dataset.contentId;
    if (contentId) {
        loadRatingStatistics(contentId);
    }
});

// Export functions for global access
window.ratingSystem = {
    voteReviewHelpfulness,
    toggleSpoiler,
    quickRate,
    confirmDeleteRating,
    confirmDeleteReview,
    updateReviewSort,
    loadRatingStatistics
};
