// Constants
const DEFAULT_EXPIRY_MONTHS = 2;
const NOTIFICATION_THRESHOLDS = {
    WARNING: 14, // days
    CRITICAL: 7  // days
};
let currentStep = 1;
const totalSteps = 4;
let scannedItems = [];
let selectedLocation = null;

// Initialize when document loads
document.addEventListener('DOMContentLoaded', () => {
    initializeApplication();
});

// Initialization
function initializeApplication() {
    // Generelle initialiseringer
    initializeUserProfile();
    setupFormListeners();
    setupScannerListeners();
    setupStorageGridListeners();
    
    // Initialiser funktioner baseret på den aktuelle sti
    const currentPath = window.location.pathname;
    
    if (currentPath === '/' || currentPath.includes('/dashboard')) {
        loadDashboardData();
    } else if (currentPath.includes('/register')) {
        setDefaultExpiryDate();
        setupRegistrationSteps();
        setupSerialNumberToggle();
        setupMultiPackageHandling();
        setupBulkSampleHandling(); // Tilføj denne linje
        showStep(1);
    } else if (currentPath.includes('/storage')) {
        // Lager-specifikke initialiseringer
    } else if (currentPath.includes('/testing')) {
        // Test-specifikke initialiseringer
    }
    
    // Kald med dummy data for at undgå fejl
    updateUIWithDomainUser({});
}

// Opdateret updateUIWithDomainUser funktion
function updateUIWithDomainUser(userInfo) {
    // Hardcoded dummy data - virker altid
    const usernameElement = document.querySelector('.user-name');
    if (usernameElement) {
        usernameElement.textContent = "BWM";
    }
    
    const userRolesElement = document.querySelector('.user-roles');
    if (userRolesElement) {
        userRolesElement.innerHTML = '<span class="role-badge admin">Admin</span>';
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
    
    // Container option radio buttons handling
    const containerRadios = document.querySelectorAll('input[name="containerOption"]');
    if (containerRadios.length) {
        containerRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                toggleContainerFields(this.value);
            });
        });
    }
    
    // Initialize container fields visibility
    const selectedOption = document.querySelector('input[name="containerOption"]:checked');
    if (selectedOption) {
        toggleContainerFields(selectedOption.value);
    }
}

// Function to toggle container fields based on selected option
function toggleContainerFields(option) {
    const newContainerFields = document.getElementById('newContainerFields');
    const existingContainerFields = document.getElementById('existingContainerFields');
    
    if (!newContainerFields || !existingContainerFields) return;
    
    // Hide all first
    newContainerFields.classList.add('d-none');
    existingContainerFields.classList.add('d-none');
    
    // Show relevant fields
    if (option === 'new') {
        newContainerFields.classList.remove('d-none');
    } else if (option === 'existing') {
        existingContainerFields.classList.remove('d-none');
    }
}

// Load Storage Locations
function loadStorageLocations() {
    fetch('/api/storage-locations')
        .then(response => response.json())
        .then(data => {
            if (data.locations) {
                updateStorageGrid(data.locations);
            }
        })
        .catch(error => console.error('Error loading storage locations:', error));
}

function updateStorageGrid(locations) {
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '';
    
    // Kun vis de første 12 lokationer for at holde det kompakt
    const limitedLocations = locations.slice(0, 12);

    limitedLocations.forEach(location => {
        const cell = document.createElement('div');
        cell.className = 'storage-cell';
        if(location.status === 'occupied') {
            cell.classList.add('occupied');
        }

        const locationEl = document.createElement('div');
        locationEl.className = 'location';
        locationEl.textContent = location.LocationName;

        const capacity = document.createElement('div');
        capacity.className = 'capacity';
        capacity.textContent = location.status === 'occupied' ? `${location.count}` : 'Ledig';

        cell.appendChild(locationEl);
        cell.appendChild(capacity);
        grid.appendChild(cell);
    });
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
    // Hardcoded dummy data - virker altid
    document.querySelector('.user-name').textContent = "BWM";
    
    const userRolesElement = document.querySelector('.user-roles');
    if (userRolesElement) {
        userRolesElement.innerHTML = '<span class="role-badge admin">Admin</span>';
    }
}

// Registration Steps Functions
function updateProgress(step) {
    const progress = ((step - 1) / (totalSteps - 1)) * 100;
    
    // Opdater alle progress-bars på siden
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        bar.style.width = `${progress}%`;
    });
    
    console.log(`Progress: ${progress}%`); // Debug output

    // Opdater steps visning
    const steps = document.querySelectorAll('.step');
    steps.forEach((el, index) => {
        el.classList.remove('active', 'completed');
        
        if (index + 1 < step) {
            el.classList.add('completed');
        } else if (index + 1 === step) {
            el.classList.add('active');
        }
    });
}

function setupSerialNumberToggle() {
    const checkbox = document.getElementById('hasSerialNumbers');
    if (checkbox) {
        checkbox.addEventListener('change', () => {
            const currentStep = document.querySelector('.form-step.active').id.replace('step', '');
            updateProgress(parseInt(currentStep));
        });
    }
}

function showStep(step) {
    const formSteps = document.querySelectorAll('.form-step');
    formSteps.forEach(el => {
        el.classList.remove('active');
    });

    const currentStepElement = document.querySelector(`#step${step}`);
    if (currentStepElement) {
        currentStepElement.classList.add('active');
        updateProgress(step);
        updateNavigationButtons(step);

        // Initialiser den aktuelle side
        if (step === 1) {
            initReceptionDate();
        } else if (step === 3 && document.getElementById('hasSerialNumbers').checked) {
            focusBarcodeInput();
        } else if (step === 4) {
            setupStorageGrid();
        }
        
        // Opdater current step global variabel
        currentStep = step;
    }
}

function initReceptionDate() {
    const today = new Date();
    const receptionDateInput = document.querySelector('[name="receptionDate"]');
    if (receptionDateInput && !receptionDateInput.value) {
        receptionDateInput.valueAsDate = today;
    }
}

function updateNavigationButtons(step) {
    const prevButton = document.getElementById('prevButton');
    const nextButton = document.getElementById('nextButton');

    if (prevButton) {
        prevButton.style.display = step === 1 ? 'none' : 'block';
    }

    if (nextButton) {
        nextButton.textContent = step === totalSteps ? 'Gem' : 'Næste';
    }
}

function nextStep() {
    if (validateCurrentStep()) {
        const hasSerialNumbers = document.getElementById('hasSerialNumbers')?.checked || false;
        
        // Inkrementer altid til næste trin først
        currentStep += 1;
        
        // Hvis vi lander på identifikationstrinnet (trin 3) og der ikke er serienumre, spring til trin 4
        if (currentStep === 3 && !hasSerialNumbers) {
            currentStep = 4;
        }
        
        // Sørg for, at vi ikke går udover det maksimale antal trin
        currentStep = Math.min(currentStep, totalSteps);
        
        showStep(currentStep);
    }
}

function previousStep() {
    const hasSerialNumbers = document.getElementById('hasSerialNumbers')?.checked || false;
    
    // Dekrementer altid til forrige trin først
    currentStep -= 1;
    
    // Hvis vi lander på identifikationstrinnet (trin 3) og der ikke er serienumre, spring til trin 2
    if (currentStep === 3 && !hasSerialNumbers) {
        currentStep = 2;
    }
    
    // Sørg for, at vi ikke går under det første trin
    currentStep = Math.max(currentStep, 1);
    
    showStep(currentStep);
}

// Form Validation and Submission
async function handleFormSubmission() {
    if (!validateCurrentStep()) return;
    
    // Saml container data baseret på valg
    let containerData = {};
    const containerOption = document.querySelector('input[name="containerOption"]:checked')?.value || 'none';
    
    if (containerOption === 'new') {
        containerData = {
            createContainer: true,
            containerType: document.querySelector('[name="containerType"]')?.value || '',
            containerDescription: document.querySelector('[name="containerDescription"]')?.value || '',
            containerMixed: document.getElementById('containerMixed')?.checked || false
        };
    } else if (containerOption === 'existing') {
        containerData = {
            useExistingContainer: true,
            existingContainerId: document.querySelector('[name="existingContainerId"]')?.value || ''
        };
    }
    
    // Saml pakke data
    const isMultiPackage = document.getElementById('isMultiPackage')?.checked || false;
    const packageCount = isMultiPackage ? parseInt(document.querySelector('[name="packageCount"]')?.value) || 1 : 1;
    const amountPerPackage = isMultiPackage ? parseInt(document.querySelector('[name="amountPerPackage"]')?.value) || 0 : 0;
    
    const formData = {
        // Modtagelsesoplysninger
        supplier: document.querySelector('[name="supplier"]')?.value || '',
        trackingNumber: document.querySelector('[name="trackingNumber"]')?.value || '',
        custodian: document.querySelector('[name="custodian"]')?.value || '',
        receptionDate: document.querySelector('[name="receptionDate"]')?.value || '',
        
        // Prøve information
        partNumber: document.querySelector('[name="partNumber"]')?.value || '',
        description: document.querySelector('[name="description"]')?.value || '',
        isBulkSample: document.getElementById('isBulkSample')?.checked || false,
        isMultiPackage: isMultiPackage,
        packageCount: packageCount,
        amountPerPackage: amountPerPackage,
        totalAmount: parseInt(document.querySelector('[name="totalAmount"]')?.value) || 0,
        unit: document.querySelector('[name="unit"]')?.value || '',
        owner: document.querySelector('[name="owner"]')?.value || '',
        expiryDate: document.querySelector('[name="expiryDate"]')?.value || '',
        hasSerialNumbers: document.getElementById('hasSerialNumbers')?.checked || false,
        other: document.querySelector('[name="other"]')?.value || '',
        
        // Identifikation
        serialNumbers: scannedItems || [],
        
        // Placering
        storageLocation: document.querySelector('[name="storageLocation"]')?.value || selectedLocation || '',
        
        // Container information
        containerOption: containerOption,
        ...containerData
    };
    
    console.log("Sending form data:", formData);
    
    try {
        const response = await fetch('/api/samples', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccessMessage(`Prøve ${result.sample_id} er blevet registreret succesfuldt!`);
            
            // Nulstil formularen og gå tilbage til step 1 efter kort pause
            setTimeout(() => {
                resetForm();
                currentStep = 1;
                showStep(1);
                
                // Tilføj dette: Send brugeren tilbage til dashboard efter succesfuld registrering
                window.location.href = '/dashboard';
            }, 2000);
        } else {
            showErrorMessage(`Fejl ved registrering: ${result.error}`);
        }
    } catch (error) {
        // Håndter fejl
    }
}

function resetForm() {
    currentStep = 1;
    scannedItems = [];
    selectedLocation = null;

    document.querySelectorAll('input:not([type="radio"]):not([type="checkbox"])').forEach(input => {
        input.value = '';
        input.classList.remove('invalid');
    });
    
    document.querySelectorAll('select').forEach(select => {
        select.selectedIndex = 0;
        select.classList.remove('invalid');
    });
    
    // Reset checkboxes
    if (document.getElementById('hasSerialNumbers')) {
        document.getElementById('hasSerialNumbers').checked = false;
    }
    
    if (document.getElementById('isBulkSample')) {
        document.getElementById('isBulkSample').checked = false;
    }
    
    if (document.getElementById('isMultiPackage')) {
        document.getElementById('isMultiPackage').checked = false;
    }
    
    // Sæt standard container option
    const noContainerRadio = document.getElementById('noContainer');
    if (noContainerRadio) {
        noContainerRadio.checked = true;
    }
    
    // Skjul multiple package felter
    const multiplePackageFields = document.getElementById('multiplePackageFields');
    if (multiplePackageFields) {
        multiplePackageFields.classList.add('d-none');
    }
    
    // Clear scanned items container
    const scannedItemsContainer = document.querySelector('.scanned-items');
    if (scannedItemsContainer) {
        scannedItemsContainer.innerHTML = '';
    }

    setDefaultExpiryDate();
    showStep(1);
}
    
function validateCurrentStep() {
    switch (currentStep) {
        case 1:
            // Modtagelsesinfo
            return validateRequiredFields(['custodian']); // supplier er valgfri
            
        case 2:
            // Prøveinfo
            return validateRequiredFields(['description', 'totalAmount', 'unit', 'owner', 'expiryDate']);
            
        case 3:
            // Identifikation (serienumre) - kun relevant hvis hasSerialNumbers er true
            const hasSerialNumbers = document.getElementById('hasSerialNumbers')?.checked || false;
            
            if (hasSerialNumbers) {
                const totalAmount = parseInt(document.querySelector('[name="totalAmount"]')?.value) || 0;
                
                if (scannedItems.length < totalAmount) {
                    showErrorMessage(`Der mangler at blive scannet ${totalAmount - scannedItems.length} prøver`);
                    return false;
                }
            }
            return true;
            
        case 4:
            // Placering
            const locationSelect = document.querySelector('[name="storageLocation"]');
            
            if ((!locationSelect || !locationSelect.value) && !selectedLocation) {
                showErrorMessage('Vælg venligst en lagerplacering');
                return false;
            }
            
            return true;
            
        default:
            return true;
    }
}
    
// Storage Grid Functions
function setupStorageGrid() {
    // Hent lagerplaceringer fra API'en
    fetch('/api/storage-locations')
        .then(response => response.json())
        .then(data => {
            if (data.locations) {
                updateStorageGrid(data.locations);
            }
        })
        .catch(error => {
            console.error('Error loading storage locations:', error);
            // Fallback til dummy data hvis API-kaldet fejler
            createDummyStorageGrid();
        });
}

function validateRequiredFields(fieldNames) {
    let isValid = true;
    
    fieldNames.forEach(field => {
        const input = document.querySelector(`[name="${field}"]`);
        if (!input || !input.value.trim()) {
            if (input) {
                markInvalid(input);
            } else {
                console.warn(`Feltet "${field}" blev ikke fundet i DOM`);
            }
            isValid = false;
        } else {
            markValid(input);
        }
    });
    
    return isValid;
}

function validateStorageLocation() {
    const locationSelect = document.querySelector('[name="storageLocation"]');
    
    if ((!locationSelect || !locationSelect.value) && !selectedLocation) {
        showErrorMessage('Vælg venligst en lagerplacering');
        return false;
    }
    
    return true;
}
    
function createDummyStorageGrid() {
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
        const barcode = event.target.value.trim();
        if (barcode) {
            processScan(barcode);
            event.target.value = '';
        }
    }
}
    
function processScan(barcode) {
    if (!barcode) return;

    const totalExpected = parseInt(document.querySelector('[name="totalAmount"]')?.value) || 0;
    
    // Tjek for duplikater
    if (scannedItems.includes(barcode)) {
        showWarningMessage(`Stregkode "${barcode}" er allerede scannet`);
        return;
    }

    if (scannedItems.length < totalExpected) {
        scannedItems.push(barcode);
        updateScanUI();
        // Afspil en lyd for at indikere succesfuld scanning
        playSuccessSound();
    } else {
        showErrorMessage('Maksimalt antal prøver er nået');
    }
}

// Afspil en lyd for at indikere succesfuld scanning
function playSuccessSound() {
    // Opret en simpel lyd
    const context = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = context.createOscillator();
    const gainNode = context.createGain();
    
    oscillator.type = 'sine';
    oscillator.frequency.value = 1000;
    oscillator.connect(gainNode);
    gainNode.connect(context.destination);
    
    gainNode.gain.value = 0.1;
    oscillator.start(0);
    
    setTimeout(function() {
        oscillator.stop();
    }, 100);
}
    
function updateScanUI() {
    const counter = document.getElementById('scannedCount');
    const totalCounter = document.getElementById('totalCount');
    const total = document.querySelector('[name="totalAmount"]')?.value || 0;
    const emptyMessage = document.querySelector('.empty-scanned-message');

    if (counter) counter.textContent = scannedItems.length;
    if (totalCounter) totalCounter.textContent = total;

    const container = document.querySelector('.scanned-items');
    if (container) {
        // Fjern tom besked hvis der er scannede items
        if (emptyMessage) {
            emptyMessage.style.display = scannedItems.length > 0 ? 'none' : 'block';
        }
        
        // Opbyg liste af scannede items
        const itemsList = document.createElement('div');
        itemsList.className = 'scanned-items-list';
        
        scannedItems.forEach((code, index) => {
            const itemEl = document.createElement('div');
            itemEl.className = 'scanned-item';
            itemEl.innerHTML = `
                <div class="item-number">${index + 1}</div>
                <div class="item-code">${code}</div>
                <button onclick="removeScannedItem(${index})" class="btn btn-sm btn-danger">
                    <i class="fas fa-times"></i>
                </button>
            `;
            itemsList.appendChild(itemEl);
        });
        
        // Ryd container og tilføj nye elementer
        container.innerHTML = '';
        if (scannedItems.length > 0) {
            container.appendChild(itemsList);
        } else if (emptyMessage) {
            container.appendChild(emptyMessage);
        }
    }
}
    
// Scanner
function setupScannerListeners() {
    const scannerInput = document.getElementById('barcodeInput');
    const addManualBtn = document.getElementById('addManualBtn');
    const scanButton = document.getElementById('scanButton');
    const bulkEntryButton = document.getElementById('bulkEntryButton');
    const bulkEntrySection = document.querySelector('.bulk-entry');
    const addBulkBtn = document.getElementById('addBulkBtn');
    const clearAllScannedBtn = document.getElementById('clearAllScannedBtn');
    
    if (scannerInput && addManualBtn) {
        // Scanner input håndtering
        scannerInput.addEventListener('keypress', handleScan);
        
        // Manuel tilføjelse
        addManualBtn.addEventListener('click', function() {
            const barcode = scannerInput.value.trim();
            if (barcode) {
                processScan(barcode);
                scannerInput.value = '';
            }
            scannerInput.focus();
        });
    }
    
    // Toggle scanning tilstand
    if (scanButton) {
        scanButton.addEventListener('click', function() {
            const isActive = this.classList.contains('btn-primary');
            
            if (isActive) {
                // Deaktiver scanning
                this.classList.remove('btn-primary');
                this.classList.add('btn-outline-primary');
                this.innerHTML = '<i class="fas fa-barcode"></i> Start Scanning';
                if (scannerInput) {
                    scannerInput.disabled = true;
                    scannerInput.placeholder = "Scanning deaktiveret";
                }
            } else {
                // Aktiver scanning
                this.classList.remove('btn-outline-primary');
                this.classList.add('btn-primary');
                this.innerHTML = '<i class="fas fa-barcode"></i> Scanning Aktiv';
                if (scannerInput) {
                    scannerInput.disabled = false;
                    scannerInput.placeholder = "Scan eller indtast serienummer";
                    scannerInput.focus();
                }
            }
        });
    }
    
    // Vis/skjul masse-indtastning
    if (bulkEntryButton && bulkEntrySection) {
        bulkEntryButton.addEventListener('click', function() {
            bulkEntrySection.classList.toggle('d-none');
            
            if (!bulkEntrySection.classList.contains('d-none')) {
                document.getElementById('bulkBarcodes').focus();
            }
        });
    }
    
    // Håndter masse-indtastning
    if (addBulkBtn) {
        addBulkBtn.addEventListener('click', function() {
            const bulkBarcodes = document.getElementById('bulkBarcodes');
            if (bulkBarcodes) {
                const barcodes = bulkBarcodes.value.split('\n')
                    .map(code => code.trim())
                    .filter(code => code.length > 0);
                
                const totalExpected = parseInt(document.querySelector('[name="totalAmount"]')?.value) || 0;
                const currentCount = scannedItems.length;
                
                if (currentCount + barcodes.length > totalExpected) {
                    showErrorMessage(`Kan ikke tilføje ${barcodes.length} stregkoder. Maksimalt antal er ${totalExpected} (${currentCount} allerede scannet)`);
                    return;
                }
                
                barcodes.forEach(barcode => {
                    processScan(barcode);
                });
                
                bulkBarcodes.value = '';
                showSuccessMessage(`${barcodes.length} stregkoder tilføjet succesfuldt`);
                
                // Skjul masse-indtastning efter tilføjelse
                bulkEntrySection.classList.add('d-none');
            }
        });
    }
    
    // Ryd alle scannede items
    if (clearAllScannedBtn) {
        clearAllScannedBtn.addEventListener('click', function() {
            if (confirm('Er du sikker på at du vil fjerne alle scannede prøver?')) {
                scannedItems = [];
                updateScanUI();
                showSuccessMessage('Alle scannede prøver er blevet fjernet');
            }
        });
    }
}

// Multi-pakke håndtering
document.addEventListener('DOMContentLoaded', function() {
    // Multi-pakke håndtering
    const isMultiPackageCheckbox = document.getElementById('isMultiPackage');
    const multiplePackageFields = document.getElementById('multiplePackageFields');
    const packageCountInput = document.querySelector('[name="packageCount"]');
    const amountPerPackageInput = document.querySelector('[name="amountPerPackage"]');
    const totalAmountInput = document.querySelector('[name="totalAmount"]');
    const calculatedTotal = document.getElementById('calculatedTotal');
    const totalAmountHelper = document.getElementById('totalAmountHelper');
    
    // Vis/skjul felter for multiple pakker
    if (isMultiPackageCheckbox && multiplePackageFields) {
        isMultiPackageCheckbox.addEventListener('change', function() {
            multiplePackageFields.classList.toggle('d-none', !this.checked);
            
            if (this.checked) {
                totalAmountHelper.textContent = "Total mængde beregnes automatisk fra pakkeoplysninger";
                totalAmountInput.readOnly = true;
            } else {
                totalAmountHelper.textContent = "Samlet antal enheder der modtages";
                totalAmountInput.readOnly = false;
            }
            
            // Opdater total mængde når checkbox ændres
            updateTotalAmount();
        });
    }
    
    // Beregn total mængde baseret på antal pakker og mængde pr. pakke
    function updateTotalAmount() {
        if (isMultiPackageCheckbox && isMultiPackageCheckbox.checked && 
            packageCountInput && amountPerPackageInput && totalAmountInput) {
            const packageCount = parseInt(packageCountInput.value) || 0;
            const amountPerPackage = parseInt(amountPerPackageInput.value) || 0;
            const total = packageCount * amountPerPackage;
            
            totalAmountInput.value = total;
            if (calculatedTotal) {
                calculatedTotal.textContent = total;
            }
        }
    }
    
    // Lyt efter ændringer i pakke-felterne
    if (packageCountInput && amountPerPackageInput) {
        packageCountInput.addEventListener('input', updateTotalAmount);
        amountPerPackageInput.addEventListener('input', updateTotalAmount);
    }
    
    // Kopier sidste registrering
    const copyLastButton = document.getElementById('copyLastButton');
    if (copyLastButton) {
        copyLastButton.addEventListener('click', function() {
            fetch('/api/last-sample')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Fyld form med data fra sidste registrering
                        document.querySelector('[name="partNumber"]').value = data.sample.partNumber || '';
                        document.querySelector('[name="description"]').value = data.sample.description || '';
                        document.querySelector('[name="unit"]').value = data.sample.unit || '';
                        document.querySelector('[name="owner"]').value = data.sample.owner || '';
                        
                        // Behold mængde, serienumre og lokation tomme
                        document.querySelector('[name="totalAmount"]').value = '';
                        if (document.getElementById('hasSerialNumbers')) {
                            document.getElementById('hasSerialNumbers').checked = data.sample.hasSerialNumbers || false;
                        }
                        
                        // Vis bekræftelsesmeddelelse
                        showSuccessMessage('Information kopieret fra seneste registrering. Opdater venligst mængde og placering.');
                    } else {
                        showErrorMessage('Kunne ikke finde seneste registrering.');
                    }
                })
                .catch(error => {
                    console.error('Error fetching last sample:', error);
                    showErrorMessage('Der opstod en fejl ved hentning af seneste registrering.');
                });
        });
    }
});
    
function setupRegistrationSteps() {
    // Sæt event handlers op direkte på knapperne
    const nextButton = document.getElementById('nextButton');
    const prevButton = document.getElementById('prevButton');
    
    if (nextButton) {
        nextButton.addEventListener('click', function() {
            if (currentStep === totalSteps) {
                handleFormSubmission();
            } else {
                nextStep();
            }
        });
    }
    
    if (prevButton) {
        prevButton.addEventListener('click', function() {
            previousStep();
        });
    }
    
    // Initialiser første step
    showStep(1);
}

// Håndtering af multi-pakke-funktionalitet
function setupMultiPackageHandling() {
    document.addEventListener('DOMContentLoaded', function() {
        const isMultiPackageCheckbox = document.getElementById('isMultiPackage');
        const multiplePackageFields = document.getElementById('multiplePackageFields');
        const packageCountInput = document.querySelector('[name="packageCount"]');
        const amountPerPackageInput = document.querySelector('[name="amountPerPackage"]');
        const totalAmountInput = document.querySelector('[name="totalAmount"]');
        
        // Vis/skjul felter for multiple pakker
        if (isMultiPackageCheckbox && multiplePackageFields) {
            isMultiPackageCheckbox.addEventListener('change', function() {
                multiplePackageFields.classList.toggle('d-none', !this.checked);
                
                // Opdater total mængde når checkbox ændres
                updateTotalAmount();
            });
        }
        
        // Beregn total mængde baseret på antal pakker og mængde pr. pakke
        function updateTotalAmount() {
            if (isMultiPackageCheckbox && isMultiPackageCheckbox.checked && packageCountInput && amountPerPackageInput && totalAmountInput) {
                const packageCount = parseInt(packageCountInput.value) || 0;
                const amountPerPackage = parseInt(amountPerPackageInput.value) || 0;
                const total = packageCount * amountPerPackage;
                
                totalAmountInput.value = total;
                totalAmountInput.readOnly = isMultiPackageCheckbox.checked;
            } else if (totalAmountInput) {
                totalAmountInput.readOnly = false;
            }
        }
        
        // Lyt efter ændringer i pakke-felterne
        if (packageCountInput && amountPerPackageInput) {
            packageCountInput.addEventListener('input', updateTotalAmount);
            amountPerPackageInput.addEventListener('input', updateTotalAmount);
        }
    });
}
    
// Test Creation Functions
function showCreateTestModal() {
    const modal = new bootstrap.Modal(document.getElementById('createTestModal'));
    modal.show();
}
    
function createTest() {
    // Valider inputs
    const testType = document.querySelector('[name="testType"]');
    const testOwner = document.querySelector('[name="testOwner"]');

    // Hvis testOwner er et skjult felt med current_user, skal vi ikke validere det
    if (testOwner.type === 'hidden') {
        // Værdien er allerede sat fra server-side
    } else if (!testOwner.value) {
        testOwner.classList.add('invalid');
        return;
    }
    
    if (!testType.value) {
        testType.classList.add('invalid');
        return;
    }
    
    if (!testOwner.value) {
        testOwner.classList.add('invalid');
        return;
    }
    
    const selectedSamples = getSelectedSamples();
    if (selectedSamples.length === 0) {
        showErrorMessage('Vælg mindst én prøve til testen');
        return;
    }
    
    const testData = {
        type: testType.value,
        owner: testOwner.value,
        testName: `${testType.options[testType.selectedIndex].text} Test`,
        description: `Test oprettet ${new Date().toLocaleDateString('da-DK')}`,
        samples: selectedSamples
    };

    // Send til API
    fetch('/api/createTest', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(testData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage(`Test ${data.test_id} oprettet succesfuldt`);
            
            const modal = bootstrap.Modal.getInstance(document.getElementById('createTestModal'));
            modal.hide();
            
            // Reload testing page efter kortere delay
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            showErrorMessage(`Fejl ved oprettelse af test: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error creating test:', error);
        showErrorMessage('Der opstod en fejl ved oprettelse af test. Prøv igen senere.');
    });
}
    
function getSelectedSamples() {
    const selectedSamples = [];
    document.querySelectorAll('[name="selectedSamples"]:checked').forEach(checkbox => {
        const row = checkbox.closest('tr');
        const amountInput = row.querySelector('input[type="number"]');
        
        // Kontroller at mængden er gyldig
        if (amountInput && parseInt(amountInput.value) > 0) {
            selectedSamples.push({
                id: row.querySelector('td:nth-child(2)').textContent,
                amount: parseInt(amountInput.value)
            });
        } else if (amountInput) {
            amountInput.classList.add('invalid');
        }
    });
    return selectedSamples;
}
    
function updateTestOverview() {
    // Implementation would update the test overview UI
    console.log('Updating test overview');
}
    
// Expiry Check Functions
function showExpiringDetails() {
    // Indlæs udløbende prøver fra API
    fetch('/api/expiring-samples')
        .then(response => response.json())
        .then(data => {
            if (data.samples && data.samples.length > 0) {
                updateExpiringModal(data.samples);
            } else {
                updateExpiringModal([]);
            }
            const modal = new bootstrap.Modal(document.getElementById('expiringDetailsModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error loading expiring samples:', error);
            showErrorMessage('Kunne ikke indlæse udløbende prøver. Prøv igen senere.');
        });
}
    
function updateExpiringModal(samples) {
    const modalBody = document.querySelector('#expiringDetailsModal .modal-body');
    
    if (samples.length === 0) {
        modalBody.innerHTML = '<div class="alert alert-info">Ingen prøver der udløber inden for de næste 14 dage.</div>';
        return;
    }
    
    let tableContent = `
        <div class="table-responsive">
            <table class="table">
                <thead>
                    <tr>
                        <th>Prøve ID</th>
                        <th>Beskrivelse</th>
                        <th>Udløbsdato</th>
                        <th>Dage til udløb</th>
                        <th>Placering</th>
                        <th>Handling</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    samples.forEach(sample => {
        const warningClass = sample.days_until_expiry <= 7 ? 'danger' : 'warning';
        const formattedDate = new Date(sample.ExpireDate).toLocaleDateString('da-DK');
        
        tableContent += `
            <tr class="${warningClass}">
                <td>${sample.SampleID}</td>
                <td>${sample.Description}</td>
                <td>${formattedDate}</td>
                <td>${sample.days_until_expiry}</td>
                <td>${sample.LocationName}</td>
                <td>
                    <button class="btn btn-sm btn-warning" onclick="extendExpiryDate('${sample.SampleID}')">
                        Forlæng
                    </button>
                </td>
            </tr>
        `;
    });
    
    tableContent += `
                </tbody>
            </table>
        </div>
    `;
    
    modalBody.innerHTML = tableContent;
}
    
function extendExpiryDate(sampleId) {
    // Dette skal implementeres senere med et API-kald
    console.log(`Extending expiry date for sample: ${sampleId}`);
    showSuccessMessage(`Udløbsdato forlænget med 30 dage for ${sampleId}`);
}
    
function checkForExpiringSamples() {
    fetch('/api/expiring-samples')
        .then(response => response.json())
        .then(data => {
            if (data.samples && data.samples.length > 0) {
                // Vis notifikation
                showWarningMessage(`${data.samples.length} prøver udløber snart. Klik for detaljer.`, () => showExpiringDetails());
            }
        })
        .catch(error => console.error('Error checking expiring samples:', error));
}

// Disposal Functions
function showDisposalModal(event) {
    if (event) event.preventDefault();
    
    // Hent aktive prøver til dropdown
    fetch('/api/activeSamples')
        .then(response => response.json())
        .then(data => {
            updateSampleSelect(data.samples);
            
            // Hent seneste kassationer
            fetch('/api/recentDisposals')
                .then(response => response.json())
                .then(data => {
                    updateDisposalTable(data.disposals);
                    
                    // Vis modal
                    const modal = new bootstrap.Modal(document.getElementById('disposalModal'));
                    modal.show();
                });
        })
        .catch(error => {
            console.error('Error loading active samples:', error);
            showErrorMessage('Kunne ikke indlæse prøve data. Prøv igen senere.');
        });
}

function updateSampleSelect(samples) {
    const sampleSelect = document.getElementById('sampleSelect');
    
    if (!sampleSelect) return;
    
    // Behold den første option (Vælg prøve)
    sampleSelect.innerHTML = '<option value="">Vælg prøve</option>';
    
    if (!samples || samples.length === 0) {
        sampleSelect.innerHTML += '<option disabled>Ingen prøver tilgængelige</option>';
        return;
    }
    
    samples.forEach(sample => {
        sampleSelect.innerHTML += `
            <option value="${sample.SampleID}">${sample.SampleIDFormatted} - ${sample.Description} (${sample.AmountRemaining} ${sample.Unit})</option>
        `;
    });
}

function updateDisposalTable(disposals) {
    const tableBody = document.getElementById('disposalTableBody');
    
    if (!tableBody) return;
    
    if (!disposals || disposals.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center">Ingen kassationer fundet</td></tr>';
        return;
    }
    
    let html = '';
    disposals.forEach(disposal => {
        html += `
            <tr>
                <td>${disposal.SampleID}</td>
                <td>${disposal.DisposalDate}</td>
                <td>${disposal.AmountDisposed}</td>
                <td>${disposal.DisposedBy}</td>
            </tr>
        `;
    });
    
    tableBody.innerHTML = html;
}

function createDisposal() {
    const sampleId = document.getElementById('sampleSelect').value;
    const amount = document.getElementById('disposalAmount').value;
    const userId = document.getElementById('disposalUser').value;
    const notes = document.getElementById('disposalNotes').value;
    
    if (!sampleId) {
        showErrorMessage('Vælg venligst en prøve');
        return;
    }
    
    if (!amount || amount <= 0) {
        showErrorMessage('Indtast venligst et gyldigt antal');
        return;
    }
    
    if (!userId) {
        showErrorMessage('Vælg venligst en bruger');
        return;
    }
    
    const disposalData = {
        sampleId: sampleId,
        amount: amount,
        userId: userId,
        notes: notes
    };
    
    fetch('/api/createDisposal', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(disposalData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage(`Kassation ${data.disposal_id} er registreret`);
            
            // Nulstil form
            document.getElementById('sampleSelect').selectedIndex = 0;
            document.getElementById('disposalAmount').value = '';
            document.getElementById('disposalNotes').value = '';
            
            // Opdater prøver og kassationstabel
            fetch('/api/activeSamples')
                .then(response => response.json())
                .then(data => {
                    updateSampleSelect(data.samples);
                });
                
            fetch('/api/recentDisposals')
                .then(response => response.json())
                .then(data => {
                    updateDisposalTable(data.disposals);
                });
        } else {
            showErrorMessage(`Fejl ved registrering af kassation: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error creating disposal:', error);
        showErrorMessage('Der opstod en fejl ved registrering af kassation. Prøv igen senere.');
    });
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
    
function showWarningMessage(message, clickCallback = null) {
    const warningToast = document.createElement('div');
    warningToast.className = 'toast show';
    warningToast.role = 'alert';
    warningToast.ariaLive = 'assertive';
    warningToast.style.position = 'fixed';
    warningToast.style.top = '20px';
    warningToast.style.right = '20px';
    warningToast.style.zIndex = '1050';
    warningToast.style.cursor = clickCallback ? 'pointer' : 'default';
    
    if (clickCallback) {
        warningToast.addEventListener('click', clickCallback);
    }
    
    warningToast.innerHTML = `
        <div class="toast-header bg-warning text-dark">
            <strong class="me-auto">Advarsel</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;
    document.body.appendChild(warningToast);

    setTimeout(() => {
        warningToast.remove();
    }, 5000);
}
    
function resetForm() {
    currentStep = 1;
    scannedItems = [];
    selectedLocation = null;

    document.querySelectorySelectorAll('input:not([type="radio"]):not([type="checkbox"])').forEach(input => {
        input.value = '';
        input.classList.remove('invalid');
    });
    document.querySelectorAll('select').forEach(select => {
        select.selectedIndex = 0;
        select.classList.remove('invalid');
    });
    
    // Reset checkbox
    if (document.getElementById('hasSerialNumbers')) {
        document.getElementById('hasSerialNumbers').checked = false;
    }
    
    // Clear scanned items container
    const scannedItemsContainer = document.querySelector('.scanned-items');
    if (scannedItemsContainer) {
        scannedItemsContainer.innerHTML = '';
    }

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
    if (element) {
        element.classList.add('invalid');
    } else {
        console.warn('Forsøger at markere ikke-eksisterende element som invalid');
    }
}

function markValid(element) {
    if (element) {
        element.classList.remove('invalid');
    }
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
    if (savedProfiles) {
        updateUIForProfiles(JSON.parse(savedProfiles));
    }
}
    
function loadDashboardData() {
    // Hent udløbende prøver
    checkForExpiringSamples();
    
    // Hent lagerpladser
    loadStorageLocations();
    
    // Opdater prøve oversigt
    updateSampleOverview();
    
    // Andre dashboard data kunne hentes her
}

function updateSampleOverview() {
    // Dette er en placeholder-funktion - implementer den med det indhold
    // der skal vises i din prøveoversigt på dashboard
    console.log('Updating sample overview');
    
    // Eksempel på implementering:
    const sampleOverviewContainer = document.querySelector('.sample-overview');
    if (sampleOverviewContainer) {
        fetch('/api/recent-samples')
            .then(response => response.json())
            .then(data => {
                if (data.samples && data.samples.length > 0) {
                    let html = '<table class="table"><thead><tr><th>ID</th><th>Beskrivelse</th><th>Placering</th><th>Status</th></tr></thead><tbody>';
                    
                    data.samples.forEach(sample => {
                        html += `<tr>
                            <td>${sample.SampleID}</td>
                            <td>${sample.Description}</td>
                            <td>${sample.Location}</td>
                            <td>${sample.Status}</td>
                        </tr>`;
                    });
                    
                    html += '</tbody></table>';
                    sampleOverviewContainer.innerHTML = html;
                } else {
                    sampleOverviewContainer.innerHTML = '<div class="alert alert-info">Ingen nylige prøver fundet</div>';
                }
            })
            .catch(error => {
                console.error('Error loading recent samples:', error);
                sampleOverviewContainer.innerHTML = '<div class="alert alert-danger">Fejl ved indlæsning af prøveoversigt</div>';
            });
    }
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

// For at håndtere navigation mellem sider
function showContent(section) {
    // Hvis det er en faktisk URL, så navigér til den
    if (section.startsWith('/')) {
        window.location.href = section;
        return;
    }
    
    // Ellers skjul alle sektioner og vis den forespurgte
    document.querySelectorAll('.content-section').forEach(el => {
        el.classList.remove('active');
    });
    
    const targetSection = document.getElementById(section);
    if (targetSection) {
        targetSection.classList.add('active');
        // Opdater også aktiv klassen i navigationen
        document.querySelectorAll('.nav-item').forEach(el => {
            el.classList.remove('active');
        });
        document.querySelector(`.nav-item[href*="${section}"]`)?.classList.add('active');
    }
}

function createNewSupplier() {
    const newSupplierName = document.getElementById('newSupplierName').value;
    
    if (!newSupplierName) {
        showErrorMessage('Indtast venligst et leverandørnavn');
        return;
    }
    
    fetch('/api/suppliers', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: newSupplierName })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Tilføj den nye leverandør til dropdown
            const supplierSelect = document.getElementById('supplierSelect');
            const newOption = document.createElement('option');
            newOption.value = data.supplier_id;
            newOption.textContent = newSupplierName;
            
            // Indsæt før "Opret ny" muligheden
            supplierSelect.insertBefore(newOption, supplierSelect.lastElementChild);
            
            // Vælg den nye leverandør
            supplierSelect.value = data.supplier_id;
            
            // Luk modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('newSupplierModal'));
            modal.hide();
            
            // Vis succesbesked
            showSuccessMessage(`Leverandør "${newSupplierName}" oprettet`);
        } else {
            showErrorMessage(`Fejl ved oprettelse af leverandør: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error creating supplier:', error);
        showErrorMessage('Der opstod en fejl ved oprettelse af leverandør. Prøv igen senere.');
    });
}

// Når bruger vælger "Opret ny leverandør" i dropdown, åbn modal automatisk
document.getElementById('supplierSelect')?.addEventListener('change', function() {
    if (this.value === 'new') {
        const modal = new bootstrap.Modal(document.getElementById('newSupplierModal'));
        modal.show();
        
        // Reset select til default efter modal åbnes
        setTimeout(() => {
            this.selectedIndex = 0;
        }, 100);
    }
});
    
// Export necessary functions for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        validateForm,
        handleScan,
        showContent,
        updateUIForProfiles,
        showDisposalModal,
        createContainer,
        createDisposal
    };

    function confirmReset() {
        if (confirm("Er du sikker på, at du vil nulstille formularen? Alle indtastede data vil gå tabt.")) {
            resetForm();
            currentStep = 1;
            showStep(1);
        }
    }
}

// Function to toggle container fields based on selected option
function toggleContainerFields(option) {
    const newContainerFields = document.getElementById('newContainerFields');
    const existingContainerFields = document.getElementById('existingContainerFields');
    
    if (!newContainerFields || !existingContainerFields) return;
    
    // Hide all first
    newContainerFields.classList.add('d-none');
    existingContainerFields.classList.add('d-none');
    
    // Show relevant fields
    if (option === 'new') {
        newContainerFields.classList.remove('d-none');
    } else if (option === 'existing') {
        existingContainerFields.classList.remove('d-none');
    }
}

// Add this to your initializeApplication or DOMContentLoaded handler
document.addEventListener('DOMContentLoaded', function() {
    // Find container option radio buttons
    const containerRadios = document.querySelectorAll('input[name="containerOption"]');
    if (containerRadios.length) {
        // Add change event listeners
        containerRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                toggleContainerFields(this.value);
            });
        });
    }
    
    // Initialize container fields visibility
    const selectedOption = document.querySelector('input[name="containerOption"]:checked');
    if (selectedOption) {
        toggleContainerFields(selectedOption.value);
    }
});

// Håndter løs mængde og enhedsvalg
function setupBulkSampleHandling() {
    const isBulkSampleCheckbox = document.getElementById('isBulkSample');
    const unitSelect = document.querySelector('[name="unit"]');
    
    if (isBulkSampleCheckbox && unitSelect) {
        // Når checkboksen ændres, opdater fremhævningen af enheder
        isBulkSampleCheckbox.addEventListener('change', function() {
            highlightRelevantUnits(this.checked);
        });
        
        // Initial fremhævning af enheder
        highlightRelevantUnits(isBulkSampleCheckbox.checked);
    }
}

// Fremhæv relevante enheder baseret på om det er løs mængde
function highlightRelevantUnits(isBulkSample) {
    const unitSelect = document.querySelector('[name="unit"]');
    if (!unitSelect) return;
    
    // Fjern eventuelle eksisterende fremhævninger
    Array.from(unitSelect.options).forEach(option => {
        option.classList.remove('bulk-unit', 'countable-unit');
    });
    
    // Tilføj nye fremhævninger baseret på enhedstypen
    Array.from(unitSelect.options).forEach(option => {
        const unitText = option.textContent.toLowerCase();
        
        if (unitText === 'stk' || unitText === 'pcs' || unitText.includes('styk')) {
            option.classList.add('countable-unit');
            // Hvis det er løs mængde, så flyt stk/pcs til bunden
            if (isBulkSample && unitSelect.options.length > 2) {
                unitSelect.add(option, unitSelect.options.length);
            }
        } else if (unitText === 'kg' || unitText === 'g' || unitText === 'liter' || 
                   unitText === 'l' || unitText === 'ml' || unitText === 'meter' || 
                   unitText === 'm' || unitText === 'cm') {
            option.classList.add('bulk-unit');
            // Hvis det er løs mængde, så flyt disse enheder til toppen
            if (isBulkSample && option.index > 1) {
                unitSelect.add(option, 1);
            }
        }
    });
    
    // Vælg en passende standardenhed baseret på typen
    if (unitSelect.selectedIndex === 0) { // Hvis ingen enhed er valgt endnu
        if (isBulkSample) {
            // Find første løs mængde enhed
            const bulkOption = Array.from(unitSelect.options).find(opt => 
                opt.classList.contains('bulk-unit'));
            if (bulkOption) {
                unitSelect.value = bulkOption.value;
            }
        } else {
            // Find stk eller lignende
            const countableOption = Array.from(unitSelect.options).find(opt => 
                opt.classList.contains('countable-unit'));
            if (countableOption) {
                unitSelect.value = countableOption.value;
            }
        }
    }

    // Alternative implementation - auto-detect bulk samples based on unit
function detectBulkSampleFromUnit() {
    const unitSelect = document.querySelector('[name="unit"]');
    if (!unitSelect) return;
    
    unitSelect.addEventListener('change', function() {
        const selectedUnit = this.options[this.selectedIndex].text.toLowerCase();
        const isBulkUnit = ['kg', 'g', 'liter', 'l', 'ml', 'meter', 'm', 'cm'].includes(selectedUnit);
        
        // Automatically check/uncheck the bulk sample checkbox
        const bulkCheckbox = document.getElementById('isBulkSample');
        if (bulkCheckbox) {
            bulkCheckbox.checked = isBulkUnit;
            document.querySelector('.checkbox-group').style.display = 'none';
        }
    });
}
}

// Funktion til at hente og vise tidligere registreringer
function loadPreviousRegistrations() {
    fetch('/api/previous-registrations')
        .then(response => response.json())
        .then(data => {
            const selectElement = document.getElementById('existingRegistrations');
            if (selectElement) {
                // Ryd nuværende options
                selectElement.innerHTML = '';
                
                // Tilføj "Vælg" option
                const defaultOption = document.createElement('option');
                defaultOption.value = '';
                defaultOption.textContent = 'Vælg en tidligere registrering';
                selectElement.appendChild(defaultOption);
                
                // Tilføj registreringer
                if (data.registrations && data.registrations.length > 0) {
                    data.registrations.forEach(registration => {
                        const option = document.createElement('option');
                        option.value = registration.id;
                        option.textContent = `${registration.description} (${registration.date})`;
                        selectElement.appendChild(option);
                    });
                } else {
                    const noDataOption = document.createElement('option');
                    noDataOption.disabled = true;
                    noDataOption.textContent = 'Ingen tidligere registreringer fundet';
                    selectElement.appendChild(noDataOption);
                }
            }
        })
        .catch(error => {
            console.error('Fejl ved hentning af tidligere registreringer:', error);
            showErrorMessage('Kunne ikke hente tidligere registreringer. Prøv igen senere.');
        });
}