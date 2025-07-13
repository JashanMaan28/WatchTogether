document.addEventListener('DOMContentLoaded', function() {
    WatchTogetherApp.init();
});

// Main application class for better organization
class WatchTogetherApp {
    static init() {
        this.initializeTooltips();
        this.initializeFormValidation();
        this.initializeSmoothScrolling();
        this.initializeFadeInAnimations();
        this.initializeTheme();
        this.updateNotificationCount();
        this.initializeKeyboardShortcuts();
        this.initializePerformanceOptimizations();
    }

    static initializeKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Escape key to close modals
            if (e.key === 'Escape') {
                const openModal = document.querySelector('.modal.show');
                if (openModal) {
                    const modalInstance = bootstrap.Modal.getInstance(openModal);
                    if (modalInstance) modalInstance.hide();
                }
            }
            
            // Ctrl/Cmd + K for search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.querySelector('#searchInput, .search-input');
                if (searchInput) {
                    searchInput.focus();
                    searchInput.select();
                }
            }
        });
    }

    static initializePerformanceOptimizations() {
        // Lazy load images
        const images = document.querySelectorAll('img[data-src]');
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        images.forEach(img => imageObserver.observe(img));

        // Debounced window resize handler
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this.handleWindowResize();
            }, 150);
        });
    }

    static handleWindowResize() {
        // Update any size-dependent elements
        const cards = document.querySelectorAll('.card');
        cards.forEach(card => {
            if (card.offsetWidth < 300) {
                card.classList.add('card-compact');
            } else {
                card.classList.remove('card-compact');
            }
        });
    }

    static updateNotificationCount() {
        const notificationBadge = document.querySelector('.notification-badge');
        if (notificationBadge) {
            fetch('/api/notifications/count')
                .then(response => response.json())
                .then(data => {
                    const count = data.unread_count || 0;
                    if (count > 0) {
                        notificationBadge.textContent = count > 99 ? '99+' : count;
                        notificationBadge.style.display = 'inline-block';
                    } else {
                        notificationBadge.style.display = 'none';
                    }
                })
                .catch(error => {
                    console.error('Failed to update notification count:', error);
                });
        }
    }

    static initializeTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    static initializeFormValidation() {
        const registerForm = document.querySelector('#registerForm');
        if (registerForm) {
            registerForm.addEventListener('submit', function(e) {
                const password = document.getElementById('password').value;
                const confirmPassword = document.getElementById('confirm_password').value;
                
                if (password !== confirmPassword) {
                    e.preventDefault();
                    WatchTogetherApp.showAlert('Passwords do not match!', 'error');
                    return false;
                }
                
                if (password.length < 8) {
                    e.preventDefault();
                    WatchTogetherApp.showAlert('Password must be at least 8 characters long!', 'error');
                    return false;
                }
            });
        }
        
        // Real-time password confirmation with enhanced validation
        const confirmPasswordField = document.getElementById('confirm_password');
        if (confirmPasswordField) {
            confirmPasswordField.addEventListener('input', function() {
                const password = document.getElementById('password').value;
                const confirmPassword = this.value;
                
                if (confirmPassword && password !== confirmPassword) {
                    this.classList.add('is-invalid');
                    this.classList.remove('is-valid');
                    this.nextElementSibling?.classList.add('show');
                } else if (confirmPassword) {
                    this.classList.add('is-valid');
                    this.classList.remove('is-invalid');
                    this.nextElementSibling?.classList.remove('show');
                }
            });
        }

        // Enhanced form validation for all forms
        const forms = document.querySelectorAll('.needs-validation');
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                if (!form.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();
                    WatchTogetherApp.showAlert('Please check all required fields.', 'warning');
                }
                form.classList.add('was-validated');
            });
        });
    }

    // Smooth scrolling for anchor links
    static initializeSmoothScrolling() {
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

    // Fade-in animations on scroll with enhanced performance
    static initializeFadeInAnimations() {
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
        
        // Observe cards and other elements with enhanced selectors
        const animatedElements = document.querySelectorAll('.card, .feature-icon, .content-card, .group-card, .proposal-card');
        animatedElements.forEach(el => observer.observe(el));
    }

    // Enhanced toast notification system
    static showAlert(message, type = 'info', duration = 5000) {
        // Remove existing alerts
        const existingAlerts = document.querySelectorAll('.alert-custom');
        existingAlerts.forEach(alert => alert.remove());
        
        // Create new alert with enhanced styling
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show alert-custom`;
        alertDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 320px;
            max-width: 500px;
            backdrop-filter: blur(10px);
            border: 1px solid var(--bs-border-color);
            box-shadow: var(--shadow-lg);
            animation: slideInRight 0.3s ease-out;
        `;
        
        alertDiv.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi bi-${this.getAlertIcon(type)} me-2"></i>
                <div class="flex-grow-1">${message}</div>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-remove after specified duration
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.classList.add('fade-out');
                setTimeout(() => alertDiv.remove(), 300);
            }
        }, duration);
    }

    static getAlertIcon(type) {
        const icons = {
            success: 'check-circle-fill',
            error: 'exclamation-triangle-fill',
            danger: 'exclamation-triangle-fill',
            warning: 'exclamation-triangle-fill',
            info: 'info-circle-fill',
            primary: 'info-circle-fill'
        };
        return icons[type] || 'info-circle-fill';
    }

    // Enhanced loading state management
    static showLoading(button) {
        const originalText = button.innerHTML;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Loading...';
        button.disabled = true;
        button.setAttribute('data-original-text', originalText);
        return originalText;
    }

    static hideLoading(button, originalText = null) {
        const text = originalText || button.getAttribute('data-original-text');
        button.innerHTML = text;
        button.disabled = false;
        button.removeAttribute('data-original-text');
    }

    // Enhanced AJAX helper with better error handling
    static async makeRequest(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
        } catch (error) {
            console.error('Request failed:', error);
            this.showAlert('Network error occurred. Please try again.', 'error');
            throw error;
        }
    }

    // Enhanced local storage helpers with error handling
    static saveToLocalStorage(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.error('Failed to save to localStorage:', error);
            this.showAlert('Failed to save data locally.', 'warning');
            return false;
        }
    }

    static getFromLocalStorage(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Failed to get from localStorage:', error);
            return defaultValue;
        }
    }

    // Enhanced theme management 
    static toggleTheme() {
        const currentTheme = this.getFromLocalStorage('theme', 'dark');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        this.saveToLocalStorage('theme', newTheme);
        
        this.showAlert(`Switched to ${newTheme} mode`, 'success');
        
        // Animate theme transition
        document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
        setTimeout(() => {
            document.body.style.transition = '';
        }, 300);
    }

    // Initialize theme on load with system preference detection
    static initializeTheme() {
        const savedTheme = this.getFromLocalStorage('theme');
        let theme = savedTheme;
        
        if (!savedTheme) {
            // Detect system preference
            theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
            this.saveToLocalStorage('theme', theme);
        }
        
        document.documentElement.setAttribute('data-theme', theme);
        
        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!this.getFromLocalStorage('theme')) {
                const newTheme = e.matches ? 'dark' : 'light';
                document.documentElement.setAttribute('data-theme', newTheme);
            }
        });
    }
}

// Enhanced global API with backward compatibility
window.WatchTogether = {
    // Static method references
    showAlert: (...args) => WatchTogetherApp.showAlert(...args),
    showLoading: (...args) => WatchTogetherApp.showLoading(...args),
    hideLoading: (...args) => WatchTogetherApp.hideLoading(...args),
    makeRequest: (...args) => WatchTogetherApp.makeRequest(...args),
    saveToLocalStorage: (...args) => WatchTogetherApp.saveToLocalStorage(...args),
    getFromLocalStorage: (...args) => WatchTogetherApp.getFromLocalStorage(...args),
    toggleTheme: (...args) => WatchTogetherApp.toggleTheme(...args),
    
    // Additional utilities
    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    throttle: (func, limit) => {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};
