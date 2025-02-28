// Constants
const DEFAULT_EXPIRY_MONTHS = 2;
const NOTIFICATION_THRESHOLDS = {
    WARNING: 14, // days
    CRITICAL: 7  // days
};
let currentStep = 1;
const totalSteps = 3;
let scannedItems = [];
let selectedLocation = null;

// Initialize when document loads
document.addEventListener('DOMContentLoaded', () => {
    initializeApplication();
});

// Initialization
function initializeApplication() {
    showStep(1);
    setDefaultExpiryDate();
    initializeUserProfile();
    loadDashboardData();
    setupFormListeners();
    setupNavigationListeners();
    setupScannerListeners();
    setupStorageGridListeners();
    setupRegistrationSteps();
    setupSerialNumberToggle()

    // Show initial content
    const initialSection = window.location.hash.substring(1) || 'dashboard';
    showContent(initialSection);

    // Mock domain user info
    const domainUser = {
        username: 'BWM',
        domain: 'ASETEK',
        roles: ['Admin']
    };

    // Update UI with domain user
    updateUIWithDomainUser(domainUser);
}

// Navigation
function showContent(sectionId) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.style.display = 'none';
        section.classList.remove('active');
    });

    // Remove active class from all nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });

    // Show the selected section
    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.style.display = 'block';
        targetSection.classList.add('active');
    }

    // Update the navigation item
    const activeNav = document.querySelector(`a[href="#${sectionId}"]`);
    if (activeNav) {
        activeNav.classList.add('active');
    }
}

// Profile Management Functions
function showProfileModal() {
    const modal = new bootstrap.Modal(document.getElementById('profileModal'));
    modal.show();
}

function saveProfiles() {
    const profiles = {
        admin: document.getElementById('adminProfile').checked,
        user: document.getElementById('userProfile').checked,
        guest: document.getElementById('guestProfile').checked
    };

    updateUIForProfiles(profiles);
    saveProfilesToLocalStorage(profiles);

    const modal = bootstrap.Modal.getInstance(document.getElementById('profileModal'));
    modal.hide();
}

function updateUIForProfiles(profiles) {
    const userRoles = document.querySelector('.user-roles');
    userRoles.innerHTML = '';

    if (profiles.admin) {
        userRoles.innerHTML += '<span class="role-badge admin">Admin</span>';
        enableAdminFeatures();
    }
    if (profiles.user) {
        userRoles.innerHTML += '<span class="role-badge user">Bruger</span>';
    }
    if (profiles.guest) {
        userRoles.innerHTML += '<span class="role-badge guest">Gæst</span>';
        disableEditingFeatures();
    }
}

function updateUIWithDomainUser(userInfo) {
    document.querySelector('.user-name').textContent = userInfo.username;

    const userRoles = document.querySelector('.user-roles');
    userRoles.innerHTML = '';

    userInfo.roles.forEach(role => {
        userRoles.innerHTML += `<span class="role-badge ${role.toLowerCase()}">${role}</span>`;
    });
}

// Registration Steps Functions
function updateProgress(step) {
    const hasSerialNumbers = document.getElementById('hasSerialNumbers').checked;
    const totalSteps = hasSerialNumbers ? 3 : 2;
    
    // Beregn progress baseret på antal steps
    const progress = ((step - 1) / (totalSteps - 1)) * 100;
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
    }

    // Opdater steps visning - vis alle steps men markér kun de relevante
    document.querySelectorAll('.step').forEach((el, index) => {
        el.classList.remove('active', 'completed');
        
        // Hvis vi ikke har serienumre og er på step 2, skip denne iteration
        if (!hasSerialNumbers && index === 1) {
            return;
        }

        if (index + 1 < step) {
            el.classList.add('completed');
        } else if (index + 1 === step) {
            el.classList.add('active');
        }
    });
}

function setupSerialNumberToggle() {
    const checkbox = document.getElementById('hasSerialNumbers');
    checkbox.addEventListener('change', () => {
        const currentStep = document.querySelector('.form-step.active').id.replace('step', '');
        updateProgress(parseInt(currentStep));
    });
}

function showStep(step) {
    document.querySelectorAll('.form-step').forEach(el => {
        el.classList.remove('active');
    });

    document.querySelector(`.form-step:nth-child(${step})`).classList.add('active');
    updateProgress(step);
    updateNavigationButtons(step);

    if (step === 3) {
        setupStorageGrid();
    }
}

function updateNavigationButtons(step) {
    const prevButton = document.querySelector('#prevButton');
    const nextButton = document.querySelector('#nextButton');

    if (prevButton) {
        prevButton.style.display = step === 1 ? 'none' : 'block';
    }

    if (nextButton) {
        if (step === totalSteps) {
            nextButton.textContent = 'Afslut';
            nextButton.onclick = handleFormSubmission;
        } else {
            nextButton.textContent = 'Næste';
            nextButton.onclick = nextStep;
        }
    }
}

function nextStep() {
    if (validateCurrentStep()) {
        const hasSerialNumbers = document.getElementById('hasSerialNumbers').checked;
        
        // Hvis vi er på step 1 og der ikke er serienumre, spring til step 3
        if (currentStep === 1 && !hasSerialNumbers) {
            currentStep = 3;
        } else {
            currentStep = Math.min(currentStep + 1, totalSteps);
        }
        
        showStep(currentStep);
    }
}

function previousStep() {
    const hasSerialNumbers = document.getElementById('hasSerialNumbers').checked;
    
    if (currentStep === 3 && !hasSerialNumbers) {
        currentStep = 1;
    } else {
        currentStep = Math.max(currentStep - 1, 1);
    }
    
    showStep(currentStep);
    
    // Aktivér/deaktivér tilbage-knappen
    const prevButton = document.querySelector('#prevButton');
    if (prevButton) {
        prevButton.disabled = currentStep === 1;
    }
}

// Form Validation and Submission
async function handleFormSubmission() {
    showSuccessMessage('Prøver er blevet registreret succesfuldt');
    
    setTimeout(() => {
        resetForm();
        showContent('storage');
    }, 1500);
}

function validateCurrentStep() {
    // For demo formål, godkend altid
    return true;
}

// Storage Grid Functions
function setupStorageGrid() {
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '';

    for (let i = 1; i <= 12; i++) {
        const cell = document.createElement('div');
        cell.className = 'storage-cell';
        if (Math.random() > 0.7) cell.classList.add('occupied');

        const location = document.createElement('div');
        location.className = 'location';
        location.textContent = `A${Math.ceil(i/4)}.B${i % 4 || 4}`;

        const capacity = document.createElement('div');
        capacity.className = 'capacity';
        capacity.textContent = cell.classList.contains('occupied') ? 'Optaget' : 'Ledig';

        cell.appendChild(location);
        cell.appendChild(capacity);
        grid.appendChild(cell);

        if (!cell.classList.contains('occupied')) {
            cell.addEventListener('click', () => selectStorageCell(cell));
        }
    }
}

function setupStorageGridListeners() {
    document.querySelectorAll('.storage-cell').forEach(cell => {
        if (!cell.classList.contains('occupied')) {
            cell.addEventListener('click', () => selectStorageCell(cell));
        }
    });
}

function selectStorageCell(cell) {
    document.querySelectorAll('.storage-cell').forEach(c => c.classList.remove('selected'));
    cell.classList.add('selected');
    selectedLocation = cell.querySelector('.location').textContent;
}

// Scanner Functions
function setupScannerListeners() {
    const scannerInput = document.getElementById('barcodeInput');
    if (scannerInput) {
        scannerInput.addEventListener('keypress', handleScan);
    }
}

function handleScan(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        processScan(event.target.value);
        event.target.value = '';
    }
}

function processScan(barcode) {
    if (!barcode) return;

    const totalExpected = parseInt(document.querySelector('[name="amount"]')?.value) || 0;

    if (scannedItems.length < totalExpected) {
        scannedItems.push(barcode);
        updateScanUI();
    } else {
        showErrorMessage('Maksimalt antal prøver er nået');
    }
}

function updateScanUI() {
    const counter = document.getElementById('scannedCount');
    const totalCounter = document.getElementById('totalCount');
    const total = document.querySelector('[name="amount"]')?.value || 0;

    if (counter) counter.textContent = scannedItems.length;
    if (totalCounter) totalCounter.textContent = total;

    const container = document.querySelector('.scanned-items');
    if (container) {
        container.innerHTML = scannedItems.map((code, index) => `
            <div class="scanned-item">
                <span>${code}</span>
                <button onclick="removeScannedItem(${index})" class="btn btn-sm btn-danger">
                    Fjern
                </button>
            </div>
        `).join('');
    }
}

// Setup Event Listeners
function setupFormListeners() {
    document.querySelectorAll('input, select').forEach(input => {
        input.addEventListener('input', () => {
            if (input.classList.contains('invalid')) {
                validateField(input);
            }
        });
    });
}

function setupNavigationListeners() {
    // Navigation menu click listeners
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (event) => {
            event.preventDefault();
            const sectionId = item.getAttribute('href').substring(1);
            showContent(sectionId);
        });
    });

    // Form navigation listeners
    const prevButton = document.querySelector('#prevButton');
    const nextButton = document.querySelector('#nextButton');
    
    if (prevButton) {
        prevButton.addEventListener('click', previousStep);
    }
}

// Utility Functions
function showSuccessMessage(message) {
    const successToast = document.createElement('div');
    successToast.className = 'toast show';
    successToast.role = 'alert';
    successToast.ariaLive = 'assertive';
    successToast.style.position = 'fixed';
    successToast.style.top = '20px';
    successToast.style.right = '20px';
    successToast.style.zIndex = '1050';
    successToast.innerHTML = `
        <div class="toast-header bg-success text-white">
            <strong class="me-auto">Succes</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;
    document.body.appendChild(successToast);

    setTimeout(() => {
        successToast.remove();
    }, 3000);
}

function showErrorMessage(message) {
    const errorToast = document.createElement('div');
    errorToast.className = 'toast show';
    errorToast.role = 'alert';
    errorToast.ariaLive = 'assertive';
    errorToast.style.position = 'fixed';
    errorToast.style.top = '20px';
    errorToast.style.right = '20px';
    errorToast.style.zIndex = '1050';
    errorToast.innerHTML = `
        <div class="toast-header bg-danger text-white">
            <strong class="me-auto">Fejl</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;
    document.body.appendChild(errorToast);

    setTimeout(() => {
        errorToast.remove();
    }, 3000);
}

function resetForm() {
    currentStep = 1;
    scannedItems = [];
    selectedLocation = null;

    document.querySelectorAll('input:not([type="radio"]):not([type="checkbox"])').forEach(input => {
        input.value = '';
    });
    document.querySelectorAll('select').forEach(select => {
        select.selectedIndex = 0;
    });

    setDefaultExpiryDate();
    showStep(1);
}

// Helper Functions
function validateField(input) {
    if (!input.value) {
        markInvalid(input);
    } else {
        markValid(input);
    }
}

function markInvalid(element) {
    element.classList.add('invalid');
}

function markValid(element) {
    element.classList.remove('invalid');
}

function setDefaultExpiryDate() {
    const expiryInput = document.querySelector('input[name="expiryDate"]');
    if (expiryInput) {
        const defaultDate = new Date();
        defaultDate.setMonth(defaultDate.getMonth() + DEFAULT_EXPIRY_MONTHS);
        expiryInput.valueAsDate = defaultDate;
    }
}

function validateForm() {
    let isValid = true;
    document.querySelectorAll('[required]').forEach(input => {
        if (!input.value) {
            isValid = false;
            markInvalid(input);
        } else {
            markValid(input);
        }
    });
    return isValid;
}

function saveRegistrationData(formData) {
    localStorage.setItem('registeredSamples', JSON.stringify(formData));
}

function saveProfilesToLocalStorage(profiles) {
    localStorage.setItem('userProfiles', JSON.stringify(profiles));
}

function initializeUserProfile() {
    const savedProfiles = localStorage.getItem('userProfiles');
    if (savedProfiles) {updateUIForProfiles(JSON.parse(savedProfiles));
    }
}

function loadDashboardData() {
    console.log('Loading dashboard data...');
}

function enableAdminFeatures() {
    // Implementation af admin features
    console.log('Admin features enabled');
}

function disableEditingFeatures() {
    // Implementation af read-only mode
    console.log('Editing features disabled');
}

function removeScannedItem(index) {
    scannedItems.splice(index, 1);
    updateScanUI();
}

// Test Creation Functions
function showCreateTestModal() {
    const modal = new bootstrap.Modal(document.getElementById('createTestModal'));
    modal.show();
}

function createTest() {
    const testData = {
        type: document.querySelector('[name="testType"]').value,
        owner: document.querySelector('[name="testOwner"]').value,
        samples: getSelectedSamples()
    };

    console.log('Creating test:', testData);
    showSuccessMessage('Test oprettet succesfuldt');

    const modal = bootstrap.Modal.getInstance(document.getElementById('createTestModal'));
    modal.hide();

    updateTestOverview();
}

function getSelectedSamples() {
    const selectedSamples = [];
    document.querySelectorAll('[name="selectedSamples"]:checked').forEach(checkbox => {
        const row = checkbox.closest('tr');
        selectedSamples.push({
            id: row.querySelector('td:nth-child(2)').textContent,
            amount: parseInt(row.querySelector('input[type="number"]').value)
        });
    });
    return selectedSamples;
}

function updateTestOverview() {
    // Implementation would update the test overview UI
    console.log('Updating test overview');
}

// Expiry Check Functions
function showExpiringDetails() {
    const modal = new bootstrap.Modal(document.getElementById('expiringDetailsModal'));
    modal.show();
}

function checkForExpiringSamples() {
    // Implementation would connect to backend
    console.log('Checking for expiring samples...');
}

// Export necessary functions for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        validateForm,
        handleScan,
        showContent,
        updateUIForProfiles
    };
}