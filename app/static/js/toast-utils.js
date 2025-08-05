/**
 * Toast Utilities - Professional toast notifications
 */

// Create and show a toast notification
function showToast(message, type = 'success', duration = 5000) {
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        console.error('Toast container not found');
        return;
    }

    // Generate unique ID for toast
    const toastId = 'toast-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    
    // Icon mapping
    const icons = {
        success: 'fas fa-check-circle text-success',
        error: 'fas fa-exclamation-circle text-danger',
        warning: 'fas fa-exclamation-triangle text-warning',
        info: 'fas fa-info-circle text-info'
    };

    // Background color mapping
    const bgColors = {
        success: 'bg-success',
        error: 'bg-danger', 
        warning: 'bg-warning',
        info: 'bg-info'
    };

    // Create toast HTML
    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgColors[type]} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body d-flex align-items-center">
                    <i class="${icons[type]} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;

    // Add toast to container
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    // Get the toast element and show it
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        delay: duration
    });
    
    // Show the toast
    toast.show();
    
    // Remove toast from DOM after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
    
    return toast;
}

// Convenience functions for different toast types
function showSuccessToast(message, duration = 5000) {
    return showToast(message, 'success', duration);
}

function showErrorToast(message, duration = 7000) {
    return showToast(message, 'error', duration);
}

function showWarningToast(message, duration = 6000) {
    return showToast(message, 'warning', duration);
}

function showInfoToast(message, duration = 5000) {
    return showToast(message, 'info', duration);
}

// Make functions globally available
window.showToast = showToast;
window.showSuccessToast = showSuccessToast;
window.showErrorToast = showErrorToast;
window.showWarningToast = showWarningToast;
window.showInfoToast = showInfoToast;