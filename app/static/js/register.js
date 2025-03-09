// Globale variabler
let currentStep = 1;
const totalSteps = 4;
let scannedItems = [];
let selectedLocation = null;
const DEFAULT_EXPIRY_MONTHS = 2;

// Initialiser når dokumentet er indlæst
document.addEventListener('DOMContentLoaded', function() {
    // Sæt default udløbsdato til 2 måneder frem
    setDefaultExpiryDate();
    
    // Setup registration form steps
    setupRegistrationSteps();
    
    // Setup serial number toggle
    setupSerialNumberToggle();
    
    // Setup multi-package handling
    setupMultiPackageHandling();
    
    // Setup scanner functionality
    setupScannerListeners();
    
    // Initialiser første skridt
    showStep(1);
});

// Sæt default udløbsdato
function setDefaultExpiryDate() {
    const expiryInput = document.querySelector('input[name="expiryDate"]');
    if (expiryInput) {
        const defaultDate = new Date();
        defaultDate.setMonth(defaultDate.getMonth() + DEFAULT_EXPIRY_MONTHS); // 2 måneder frem
        const dateString = defaultDate.toISOString().split('T')[0];
        expiryInput.value = dateString;
    }
}

// Vis specifikt step og opdater UI
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
            setupBarcodeInput();
        } else if (step === 4) {
            setupStorageGrid();
        }
        
        // Opdater current step global variabel
        currentStep = step;
    }
}

// Opdater progressbar og steps-visning
function updateProgress(step) {
    const progress = ((step - 1) / (totalSteps - 1)) * 100;
    
    // Opdater alle progress-bars på siden
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        bar.style.width = `${progress}%`;
    });
    
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

// Opdater naviation knapper baseret på aktuelt step
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

// Setup registrerings-steps navigation
function setupRegistrationSteps() {
    const nextButton = document.getElementById('nextButton');
    const prevButton = document.getElementById('prevButton');
    
    if (nextButton) {
        nextButton.addEventListener('click', function() {
            if (currentStep === totalSteps) {
                // Sidste trin - her håndterer vi form-submission
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
}

// Gå til næste step (med validering)
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

// Gå til forrige step
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

// Validér aktuelt step før vi går videre
function validateCurrentStep() {
    switch(currentStep) {
        case 1:
            // Validering af modtagelsesoplysninger - ingen obligatoriske felter
            return true;
        case 2:
            // Validering af prøve information
            const description = document.querySelector('[name="description"]');
            const totalAmount = document.querySelector('[name="totalAmount"]');
            const unit = document.querySelector('[name="unit"]');
            
            let isValid = true;
            
            if (!description || !description.value.trim()) {
                alert('Indtast venligst en beskrivelse');
                isValid = false;
            } else if (!totalAmount || totalAmount.value <= 0) {
                alert('Indtast venligst et gyldigt antal');
                isValid = false;
            } else if (!unit || !unit.value) {
                alert('Vælg venligst en enhed');
                isValid = false;
            }
            
            return isValid;
        case 3:
            // Validering af identifikation
            const hasSerialNumbers = document.getElementById('hasSerialNumbers')?.checked;
            if (hasSerialNumbers) {
                const expectedCount = parseInt(document.querySelector('[name="totalAmount"]')?.value) || 0;
                if (scannedItems.length < expectedCount) {
                    alert(`Der mangler at blive scannet ${expectedCount - scannedItems.length} enheder`);
                    return false;
                }
            }
            return true;
        case 4:
            // Validering af placering
            const storageLocation = document.querySelector('[name="storageLocation"]');
            if (!storageLocation || !storageLocation.value) {
                alert('Vælg venligst en placering');
                return false;
            }
            return true;
        default:
            return true;
    }
}

// Setup for serialnummer håndtering
function setupSerialNumberToggle() {
    const checkbox = document.getElementById('hasSerialNumbers');
    if (checkbox) {
        checkbox.addEventListener('change', () => {
            updateProgress(currentStep);
        });
    }
}

// Setup multipakke funktionalitet
function setupMultiPackageHandling() {
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
}

// Scanner funktionalitet
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
        scannerInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                const barcode = event.target.value.trim();
                if (barcode) {
                    processScan(barcode);
                    event.target.value = '';
                }
            }
        });
        
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
    
    // Tilføj bulk serienumre
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
                    alert(`Kan ikke tilføje ${barcodes.length} stregkoder. Maksimalt antal er ${totalExpected} (${currentCount} allerede scannet)`);
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

// Håndter scanning af en barcode
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

// Opdater UI med scannede items
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
        
        // Hvis ingen scannede items, vis tom besked og returner
        if (scannedItems.length === 0) {
            container.innerHTML = `<div class="empty-scanned-message text-center p-3 text-muted">
                Ingen prøver scannet endnu. Brug scanneren eller indtast serienumre manuelt ovenfor.
            </div>`;
            return;
        }
        
        // Opbyg liste af scannede items
        let html = '<div class="list-group">';
        
        scannedItems.forEach((code, index) => {
            html += `
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <span class="badge bg-primary rounded-pill me-3">${index + 1}</span>
                        <span>${code}</span>
                    </div>
                    <button onclick="removeScannedItem(${index})" class="btn btn-sm btn-outline-danger">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        });
        
        html += '</div>';
        container.innerHTML = html;
    }
}

// Fjern en scannet item
function removeScannedItem(index) {
    scannedItems.splice(index, 1);
    updateScanUI();
}

// Spil en succeslyd ved scanning
function playSuccessSound() {
    try {
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
    } catch (e) {
        // Lydeffekter er ikke afgørende, så vi ignorerer fejl
        console.log('Lydeffekter ikke understøttet');
    }
}

// Fokuser på barcode input
function setupBarcodeInput() {
    const barcodeInput = document.getElementById('barcodeInput');
    if (barcodeInput) {
        barcodeInput.focus();
    }
}

// Setup lagerplads grid
function setupStorageGrid() {
    // Hent lagerplaceringer fra API
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

// Opdater storage grid med lokationer
function updateStorageGrid(locations) {
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '';
    
    // Begræns til 12 lokationer for overskuelighed
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
        capacity.textContent = location.status === 'occupied' ? `${location.count} stk` : 'Ledig';

        cell.appendChild(locationEl);
        cell.appendChild(capacity);
        grid.appendChild(cell);
        
        if (!cell.classList.contains('occupied')) {
            cell.addEventListener('click', () => selectStorageCell(cell));
        }
    });
}

// Opret dummy data til lagerplads
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

// Vælg en lagerplads
function selectStorageCell(cell) {
    document.querySelectorAll('.storage-cell').forEach(c => c.classList.remove('selected'));
    cell.classList.add('selected');
    selectedLocation = cell.querySelector('.location').textContent;
    
    // Find og set select element
    const locationSelect = document.querySelector('[name="storageLocation"]');
    if (locationSelect) {
        // Find option med samme tekst
        const option = Array.from(locationSelect.options).find(opt => 
            opt.textContent.includes(selectedLocation));
        if (option) {
            locationSelect.value = option.value;
        }
    }
}

// Initialiser receptionsdato hvis nødvendigt
function initReceptionDate() {
    // Intet at gøre her i denne implementering
}

// Håndter form submission
function handleFormSubmission() {
    if (!validateCurrentStep()) return;
    
    // Saml alle data fra formular
    const formData = {
        // Modtagelsesoplysninger
        supplier: document.querySelector('[name="supplier"]')?.value || '',
        trackingNumber: document.querySelector('[name="trackingNumber"]')?.value || '',
        // Bemærk vi fjerner custodian her eller sikrer at det er et ID
        
        // Prøve information
        partNumber: document.querySelector('[name="partNumber"]')?.value || '',
        description: document.querySelector('[name="description"]')?.value || '',
        isBulkSample: document.getElementById('isBulkSample')?.checked || false,
        isMultiPackage: document.getElementById('isMultiPackage')?.checked || false,
        packageCount: parseInt(document.querySelector('[name="packageCount"]')?.value) || 1,
        amountPerPackage: parseInt(document.querySelector('[name="amountPerPackage"]')?.value) || 0,
        totalAmount: parseInt(document.querySelector('[name="totalAmount"]')?.value) || 0,
        unit: document.querySelector('[name="unit"]')?.value || '',
        owner: document.querySelector('[name="owner"]')?.value || '',
        expiryDate: document.querySelector('[name="expiryDate"]')?.value || '',
        hasSerialNumbers: document.getElementById('hasSerialNumbers')?.checked || false,
        other: document.querySelector('[name="other"]')?.value || '',
        
        // Identifikation
        serialNumbers: scannedItems || [],
        
        // Placering
        storageLocation: document.querySelector('[name="storageLocation"]')?.value || selectedLocation || ''
    };
    
    console.log("Sending form data:", formData);
    
    // Send data til server
    fetch('/api/samples', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage(`Prøve ${data.sample_id} er blevet registreret succesfuldt!`);
            
            // Nulstil formularen og gå tilbage til step 1 efter kort pause
            setTimeout(() => {
                resetForm();
                
                // Send brugeren tilbage til dashboard
                window.location.href = '/dashboard';
            }, 2000);
        } else {
            showErrorMessage(`Fejl ved registrering: ${data.error}`);
        }
    })
    .catch(error => {
        showErrorMessage(`Der opstod en fejl: ${error}`);
    });
}

// Nulstil formular
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
    
    // Skjul multiple package felter
    const multiplePackageFields = document.getElementById('multiplePackageFields');
    if (multiplePackageFields) {
        multiplePackageFields.classList.add('d-none');
    }
    
    // Ryd scannede items
    const scannedItemsContainer = document.querySelector('.scanned-items');
    if (scannedItemsContainer) {
        scannedItemsContainer.innerHTML = `
        <div class="empty-scanned-message text-center p-3 text-muted">
            Ingen prøver scannet endnu. Brug scanneren eller indtast serienumre manuelt ovenfor.
        </div>`;
    }

    setDefaultExpiryDate();
    showStep(1);
}

// UI Besked funktioner
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

function showWarningMessage(message) {
    const warningToast = document.createElement('div');
    warningToast.className = 'toast show';
    warningToast.role = 'alert';
    warningToast.ariaLive = 'assertive';
    warningToast.style.position = 'fixed';
    warningToast.style.top = '20px';
    warningToast.style.right = '20px';
    warningToast.style.zIndex = '1050';
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
    }, 3000);
}

// Kopier seneste prøve
function copyLastSample() {
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
}

// Gør funktioner tilgængelige for HTML-elementer
window.removeScannedItem = removeScannedItem;