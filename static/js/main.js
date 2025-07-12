// WatchTogether JavaScript Functions

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    initializeTooltips();
    initializeFormValidation();
    initializeSmoothScrolling();
    initializeFadeInAnimations();
    updateNotificationCount();
}

function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function initializeFormValidation() {
    const registerForm = document.querySelector('#registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirm_password').value;
            
            if (password !== confirmPassword) {
                e.preventDefault();
                showAlert('Passwords do not match!', 'error');
                return false;
            }
            
            if (password.length < 8) {
                e.preventDefault();
                showAlert('Password must be at least 8 characters long!', 'error');
                return false;
            }
        });
    }
    
    // Real-time password confirmation
    const confirmPasswordField = document.getElementById('confirm_password');
    if (confirmPasswordField) {
        confirmPasswordField.addEventListener('input', function() {
            const password = document.getElementById('password').value;
            const confirmPassword = this.value;
            
            if (confirmPassword && password !== confirmPassword) {
                this.classList.add('is-invalid');
                this.classList.remove('is-valid');
            } else if (confirmPassword) {
                this.classList.add('is-valid');
                this.classList.remove('is-invalid');
            }
        });
    }
}

// Smooth scrolling for anchor links
function initializeSmoothScrolling() {
    const anchors = document.querySelectorAll('a[href^="#"]');
    anchors.forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Fade-in animations on scroll
function initializeFadeInAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-up');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe cards and other elements
    const animatedElements = document.querySelectorAll('.card, .feature-icon');
    animatedElements.forEach(el => observer.observe(el));
}

// Utility function to show alerts
function showAlert(message, type = 'info') {
    // Remove existing alerts
    const existingAlerts = document.querySelectorAll('.alert-custom');
    existingAlerts.forEach(alert => alert.remove());
    
    // Create new alert
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show alert-custom`;
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.style.minWidth = '300px';
    
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Loading state management
function showLoading(button) {
    const originalText = button.innerHTML;
    button.innerHTML = '<span class="loading-spinner me-2"></span>Loading...';
    button.disabled = true;
    return originalText;
}

function hideLoading(button, originalText) {
    button.innerHTML = originalText;
    button.disabled = false;
}

// AJAX helper function
async function makeRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Request failed:', error);
        showAlert('An error occurred. Please try again.', 'error');
        throw error;
    }
}

// Local storage helpers
function saveToLocalStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
        console.error('Failed to save to localStorage:', error);
    }
}

function getFromLocalStorage(key) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : null;
    } catch (error) {
        console.error('Failed to get from localStorage:', error);
        return null;
    }
}

// Theme management (for future dark mode implementation)
function toggleTheme() {
    const currentTheme = getFromLocalStorage('theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    saveToLocalStorage('theme', newTheme);
    
    showAlert(`Switched to ${newTheme} mode`, 'success');
}

// Initialize theme on load
function initializeTheme() {
    const savedTheme = getFromLocalStorage('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
}

// Export functions for use in other scripts
window.WatchTogether = {
    showAlert,
    showLoading,
    hideLoading,
    makeRequest,
    saveToLocalStorage,
    getFromLocalStorage,
    toggleTheme
};
