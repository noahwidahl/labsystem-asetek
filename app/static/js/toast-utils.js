/**
 * Toast Utilities - ULTRA SIMPLE VERSION
 */

// UNIQUE TOAST FUNCTIONS - No conflicts with other files
function showToastMessage(message, type, duration) {
    console.log('TOAST MESSAGE: Function called');
    console.log('TOAST MESSAGE: Parameters:', message, type, duration);
    
    // Immediate alert as fallback to ensure SOMETHING works
    if (!document.body) {
        alert(message);
        return null;
    }
    
    console.log('TOAST MESSAGE: Creating div');
    var div = document.createElement('div');
    
    console.log('TOAST MESSAGE: Setting styles');
    div.style.position = 'fixed';
    div.style.top = '50%';
    div.style.left = '50%';
    div.style.transform = 'translate(-50%, -50%)';
    div.style.zIndex = '99999';
    div.style.padding = '15px';
    div.style.borderRadius = '5px';
    div.style.minWidth = '250px';
    div.style.fontSize = '14px';
    div.style.textAlign = 'center';
    
    if (type === 'error') {
        div.style.backgroundColor = '#dc3545';
        div.style.color = 'white';
        div.textContent = 'ERROR: ' + message;
    } else {
        div.style.backgroundColor = '#28a745';
        div.style.color = 'white';
        div.textContent = 'SUCCESS: ' + message;
    }
    
    console.log('TOAST MESSAGE: Adding to body');
    document.body.appendChild(div);
    
    console.log('TOAST MESSAGE: Setting timeout');
    setTimeout(function() {
        console.log('TOAST MESSAGE: Removing');
        if (div.parentNode) {
            div.parentNode.removeChild(div);
        }
    }, 5000);
    
    console.log('TOAST MESSAGE: Returning div');
    return div;
}

// UNIQUE convenience functions that won't be overwritten
function showSuccessToast(message, duration) {
    console.log('SUCCESS TOAST: Called with message:', message);
    return showToastMessage(message, 'success', duration);
}

function showErrorToast(message, duration) {
    console.log('ERROR TOAST: Called with message:', message);
    console.log('ERROR TOAST: About to call showToastMessage');
    var result = showToastMessage(message, 'error', duration);
    console.log('ERROR TOAST: showToastMessage returned:', result);
    return result;
}

function showWarningToast(message, duration) {
    console.log('WARNING TOAST: Called');
    return showToastMessage(message, 'warning', duration);
}

function showInfoToast(message, duration) {
    console.log('INFO TOAST: Called');
    return showToastMessage(message, 'info', duration);
}

// Also create the old showToast function that calls our new one
function showToast(message, type, duration) {
    console.log('OLD SHOWTOST: Redirecting to showToastMessage');
    return showToastMessage(message, type, duration);
}

// Make functions globally available
window.showToast = showToast;
window.showSuccessToast = showSuccessToast;
window.showErrorToast = showErrorToast;
window.showWarningToast = showWarningToast;
window.showInfoToast = showInfoToast;