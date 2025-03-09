// Simplificeret script for at teste grundlæggende funktionalitet
console.log('Modified script loaded');

// Constants
const DEFAULT_EXPIRY_MONTHS = 2;
const NOTIFICATION_THRESHOLDS = {
    WARNING: 14, // days
    CRITICAL: 7  // days
};
let currentStep = 1;
const totalSteps = 4;

// Initialize when document loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded');
    
    try {
        // Grundlæggende initialiseringer - begræns til det mest nødvendige
        initUserProfile();
        setupEventListeners();
        
        // Vis en testbesked for at bekræfte at alt virker
        showSuccessMessage('System indlæst korrekt');
    } catch (err) {
        console.error('Fejl ved initialisering:', err);
    }
});

// Meget simpel brugerprofilhåndtering
function initUserProfile() {
    console.log('Initializing user profile');
    // Ingen funktionalitet for nu - bare en stub
}

// Opsæt grundlæggende event listeners
function setupEventListeners() {
    console.log('Setting up event listeners');
    
    // Profile modal
    const profileBtn = document.querySelector('button[onclick="showProfileModal()"]');
    if (profileBtn) {
        profileBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Profile button clicked');
            const profileModal = new bootstrap.Modal(document.getElementById('profileModal'));
            profileModal.show();
        });
    }
}

// Vis succesbesked
function showSuccessMessage(message) {
    const successToast = document.createElement('div');
    successToast.className = 'toast show';
    successToast.style.position = 'fixed';
    successToast.style.top = '20px';
    successToast.style.right = '20px';
    successToast.style.background = '#d4edda';
    successToast.style.color = '#155724';
    successToast.style.padding = '15px';
    successToast.style.borderRadius = '5px';
    successToast.style.zIndex = '9999';
    successToast.innerHTML = `<div>${message}</div>`;
    
    document.body.appendChild(successToast);
    
    setTimeout(() => {
        successToast.remove();
    }, 3000);
}