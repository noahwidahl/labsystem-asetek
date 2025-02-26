// ============================================
// Konstanter og globale variabler
// ============================================
const DEFAULT_EXPIRY_MONTHS = 2;
const NOTIFICATION_THRESHOLDS = { WARNING: 14, CRITICAL: 7 };

let currentStep = 1;
const MAX_STEPS_WITH_SERIAL = 3;
const MAX_STEPS_WITHOUT_SERIAL = 2;
let scannedItems = [];
let selectedLocation = null;

// ============================================
// Initialisering
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    initializeApplication();
});

function initializeApplication() {
    console.log("initializeApplication kører");
    // Global initialisering – fx navigation, dashboard og brugerprofil
    setupNavigationListeners();
    initializeUserProfile();
    loadDashboardData();
    updateUIWithDomainUser({ username: 'BWM', domain: 'ASETEK', roles: ['Admin'] });

    // Find hvilken sektion, der skal vises ud fra URL-hash (default: dashboard)
    const initialSection = window.location.hash.substring(1) || 'dashboard';
    showContent(initialSection);

    // Registrerings-side initialisering, hvis vi er på siden (findes .form-step)
    if (document.querySelector('.form-step')) {
        showStep(1);
        setDefaultExpiryDate();
        setupFormListeners();
        setupScannerListeners();
        setupStorageGridListeners();
        setupRegistrationSteps(); // Dummy – tilpas med logik senere
        setupSerialNumberToggle();
    }

    // Hvis storage-siden er synlig ved load, initialiser grid
    if (document.getElementById('storage')) {
        setupStorageGrid();
    }
}

// ============================================
// Dummy registration steps function (tilpass efter behov)
// ============================================
function setupRegistrationSteps() {
    console.log("setupRegistrationSteps kaldt (ingen logik implementeret).");
}

// ============================================
// Funktion til at opdatere UI for profiler
// ============================================
function updateUIForProfiles(profiles) {
    const userRoles = document.querySelector('.user-roles');
    if (userRoles) {
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
}

// ============================================
// Funktion til at opdatere UI med domæne-bruger
// ============================================
function updateUIWithDomainUser(userInfo) {
    const userNameElem = document.querySelector('.user-name');
    if (userNameElem) {
        userNameElem.textContent = userInfo.username;
    }
    const userRoles = document.querySelector('.user-roles');
    if (userRoles) {
        userRoles.innerHTML = '';
        userInfo.roles.forEach(role => {
            userRoles.innerHTML += `<span class="role-badge ${role.toLowerCase()}">${role}</span>`;
        });
    }
}

// ============================================
// Funktion til at initialisere brugerprofilen
// ============================================
function initializeUserProfile() {
    const storedProfiles = localStorage.getItem('userProfiles');
    if (storedProfiles) {
        updateUIForProfiles(JSON.parse(storedProfiles));
    }
}

// ============================================
// Navigation og sidevisning
// ============================================
function showContent(sectionId) {
    // Skjul alle content-sektioner
    document.querySelectorAll('.content-section').forEach(section => {
        section.style.display = 'none';
        section.classList.remove('active');
    });

    // Fjern active-klasse fra alle nav-items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });

    // Vis den ønskede sektion, hvis den findes
    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.style.display = 'block';
        targetSection.classList.add('active');
    }

    // Hvis storage-siden vælges, initialiser storage grid
    if (sectionId === 'storage') {
        setupStorageGrid();
    }

    // Marker det tilsvarende navigationselement
    const activeNav = document.querySelector(`a[href="#${sectionId}"]`);
    if (activeNav) {
        activeNav.classList.add('active');
    }
}

// ============================================
// Registreringsfunktioner (kører kun hvis .form-step findes)
// ============================================
function updateProgress(step) {
    const serialCheckbox = document.getElementById('hasSerialNumbers');
    const hasSerial = serialCheckbox ? serialCheckbox.checked : false;
    const totalSteps = hasSerial ? MAX_STEPS_WITH_SERIAL : MAX_STEPS_WITHOUT_SERIAL;

    if (!serialCheckbox) {
        console.warn('Elementet med id "hasSerialNumbers" blev ikke fundet.');
    }
    const progress = ((step - 1) / (totalSteps - 1)) * 100;
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
    }

    document.querySelectorAll('.step').forEach((el, index) => {
        el.classList.remove('active', 'completed');
        if (!hasSerial && index === 1) return; // Spring step 2 over, hvis ingen serienumre
        if (index + 1 < step) {
            el.classList.add('completed');
        } else if (index + 1 === step) {
            el.classList.add('active');
        }
    });
}

function showStep(step) {
    const formSteps = document.querySelectorAll('.form-step');
    if (formSteps.length === 0) return;

    formSteps.forEach(el => el.classList.remove('active'));
    const targetStep = document.querySelector(`.form-step:nth-child(${step})`);
    if (targetStep) {
        targetStep.classList.add('active');
    }
    updateProgress(step);
    updateNavigationButtons(step);

    // Hvis sidste trin (f.eks. lagertrin), opsæt lagergrid
    if (step === MAX_STEPS_WITH_SERIAL || step === MAX_STEPS_WITHOUT_SERIAL) {
        setupStorageGrid();
    }
}

function updateNavigationButtons(step) {
    const prevButton = document.getElementById('prevButton');
    const nextButton = document.getElementById('nextButton');

    if (prevButton) {
        prevButton.style.display = (step === 1 ? 'none' : 'block');
    }
    if (nextButton) {
        const serialCheckbox = document.getElementById('hasSerialNumbers');
        const hasSerial = serialCheckbox ? serialCheckbox.checked : false;
        const totalSteps = hasSerial ? MAX_STEPS_WITH_SERIAL : MAX_STEPS_WITHOUT_SERIAL;
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
        const serialCheckbox = document.getElementById('hasSerialNumbers');
        const hasSerial = serialCheckbox ? serialCheckbox.checked : false;
        if (currentStep === 1 && !hasSerial) {
            currentStep = MAX_STEPS_WITHOUT_SERIAL;
        } else {
            currentStep = Math.min(
                currentStep + 1,
                hasSerial ? MAX_STEPS_WITH_SERIAL : MAX_STEPS_WITHOUT_SERIAL
            );
        }
        showStep(currentStep);
    }
}

function previousStep() {
    const serialCheckbox = document.getElementById('hasSerialNumbers');
    const hasSerial = serialCheckbox ? serialCheckbox.checked : false;
    if (currentStep === (hasSerial ? MAX_STEPS_WITH_SERIAL : MAX_STEPS_WITHOUT_SERIAL)) {
        currentStep = 1;
    } else {
        currentStep = Math.max(currentStep - 1, 1);
    }
    showStep(currentStep);
    const prevButton = document.getElementById('prevButton');
    if (prevButton) {
        prevButton.disabled = (currentStep === 1);
    }
}

function handleFormSubmission() {
    showSuccessMessage('Prøver er blevet registreret succesfuldt');
    setTimeout(() => {
        resetForm();
        showContent('storage');
    }, 1500);
}

function validateCurrentStep() {
    // Implementer evt. specifik validering for hvert trin
    return true;
}

// ============================================
// Lager / Storage grid funktioner
// ============================================
function setupStorageGrid() {
    // Forsøg at finde containeren med id "storage"
    const storageContainer = document.getElementById('storage');
    if (!storageContainer) {
        console.warn('Storage container (id="storage") blev ikke fundet.');
        return;
    }
    
    // Forsøg at finde et eksisterende grid inde i containeren
    let grid = storageContainer.querySelector('.storage-grid');
    if (!grid) {
        // Opret grid'et dynamisk, hvis det ikke findes
        grid = document.createElement('div');
        grid.className = 'storage-grid';
        storageContainer.appendChild(grid);
        console.log('Storage grid oprettet dynamisk.');
    }
    
    // Nulstil grid-indholdet
    grid.innerHTML = '';
    
    // Opret 12 celler med tilfældig "occupied"-status
    for (let i = 1; i <= 12; i++) {
        const cell = document.createElement('div');
        cell.className = 'storage-cell';
        if (Math.random() > 0.7) {
            cell.classList.add('occupied');
        }

        const location = document.createElement('div');
        location.className = 'location';
        location.textContent = `A${Math.ceil(i / 4)}.B${i % 4 || 4}`;

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
    const locElem = cell.querySelector('.location');
    if (locElem) selectedLocation = locElem.textContent;
}

// ============================================
// Scanner funktioner
// ============================================
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
    const totalExpectedInput = document.querySelector('[name="amount"]');
    const totalExpected = totalExpectedInput ? parseInt(totalExpectedInput.value) : 0;
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
    const totalInput = document.querySelector('[name="amount"]');
    const total = totalInput ? totalInput.value : 0;
    if (counter) counter.textContent = scannedItems.length;
    if (totalCounter) totalCounter.textContent = total;
    const container = document.querySelector('.scanned-items');
    if (container) {
        container.innerHTML = scannedItems.map((code, index) => `
            <div class="scanned-item">
                <span>${code}</span>
                <button onclick="removeScannedItem(${index})" class="btn btn-sm btn-danger">Fjern</button>
            </div>
        `).join('');
    }
}

// ============================================
// Globale event listeners
// ============================================
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
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', event => {
            event.preventDefault();
            const sectionId = item.getAttribute('href').substring(1);
            showContent(sectionId);
        });
    });
    const prevButton = document.getElementById('prevButton');
    if (prevButton) {
        prevButton.addEventListener('click', previousStep);
    }
    const nextButton = document.getElementById('nextButton');
    if (nextButton) {
        nextButton.addEventListener('click', nextStep);
    }
}

function setupSerialNumberToggle() {
    const checkbox = document.getElementById('hasSerialNumbers');
    if (checkbox) {
        checkbox.addEventListener('change', () => {
            // Genberegn registrerings-trinene ved ændring
            showStep(currentStep);
        });
    }
}

// ============================================
// Utility funktioner
// ============================================
function showSuccessMessage(message) {
    const toast = document.createElement('div');
    toast.className = 'toast show';
    toast.role = 'alert';
    toast.ariaLive = 'assertive';
    toast.style.position = 'fixed';
    toast.style.top = '20px';
    toast.style.right = '20px';
    toast.style.zIndex = '1050';
    toast.innerHTML = `
        <div class="toast-header bg-success text-white">
            <strong class="me-auto">Succes</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;
    document.body.appendChild(toast);
    setTimeout(() => { toast.remove(); }, 3000);
}

function showErrorMessage(message) {
    const toast = document.createElement('div');
    toast.className = 'toast show';
    toast.role = 'alert';
    toast.ariaLive = 'assertive';
    toast.style.position = 'fixed';
    toast.style.top = '20px';
    toast.style.right = '20px';
    toast.style.zIndex = '1050';
    toast.innerHTML = `
        <div class="toast-header bg-danger text-white">
            <strong class="me-auto">Fejl</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;
    document.body.appendChild(toast);
    setTimeout(() => { toast.remove(); }, 3000);
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
        const date = new Date();
        date.setMonth(date.getMonth() + DEFAULT_EXPIRY_MONTHS);
        expiryInput.valueAsDate = date;
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

function loadDashboardData() {
    console.log('Loading dashboard data...');
    // evt. AJAX/fetch kald
}

function enableAdminFeatures() {
    console.log('Admin features enabled');
    // evt. implementer admin logik
}

function disableEditingFeatures() {
    console.log('Editing features disabled');
    // evt. implementer read-only logik
}

function removeScannedItem(index) {
    scannedItems.splice(index, 1);
    updateScanUI();
}

// ============================================
// Test- og oprettelsesfunktioner
// ============================================
function showCreateTestModal() {
    const modalElem = document.getElementById('createTestModal');
    if (modalElem) {
        const modal = new bootstrap.Modal(modalElem);
        modal.show();
    }
}

function createTest() {
    const testTypeInput = document.querySelector('[name="testType"]');
    const testOwnerInput = document.querySelector('[name="testOwner"]');
    const testData = {
        type: testTypeInput ? testTypeInput.value : '',
        owner: testOwnerInput ? testOwnerInput.value : '',
        samples: getSelectedSamples()
    };
    console.log('Creating test:', testData);
    showSuccessMessage('Test oprettet succesfuldt');
    const modalElem = document.getElementById('createTestModal');
    if (modalElem) {
        const modal = bootstrap.Modal.getInstance(modalElem);
        if (modal) modal.hide();
    }
    updateTestOverview();
}

function getSelectedSamples() {
    const selectedSamples = [];
    document.querySelectorAll('[name="selectedSamples"]:checked').forEach(checkbox => {
        const row = checkbox.closest('tr');
        if (row) {
            const idCell = row.querySelector('td:nth-child(2)');
            const amountInput = row.querySelector('input[type="number"]');
            if (idCell && amountInput) {
                selectedSamples.push({
                    id: idCell.textContent,
                    amount: parseInt(amountInput.value)
                });
            }
        }
    });
    return selectedSamples;
}

function updateTestOverview() {
    console.log('Updating test overview');
    // evt. opdatering af UI for testoversigt
}

// ============================================
// Udløbsdato og ekspiration
// ============================================
function showExpiringDetails() {
    const modalElem = document.getElementById('expiringDetailsModal');
    if (modalElem) {
        const modal = new bootstrap.Modal(modalElem);
        modal.show();
    }
}

function checkForExpiringSamples() {
    console.log('Checking for expiring samples...');
    // evt. backend kald eller lokal logik
}

// ============================================
// Eksporter funktioner (til test mv.)
// ============================================
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        validateForm,
        handleScan,
        showContent,
        updateUIForProfiles
    };
}