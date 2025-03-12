// Basisvariabler til multistep
let currentStep = 1;
const totalSteps = 4;
let scannedItems = [];
let selectedLocation = null;
const REGISTRATION_EXPIRY_MONTHS = 2;

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
    
    // Setup bulk sample handling (for enheder)
    setupBulkSampleHandling();
    
    // Setup container options
    setupContainerOptions();
    
    // Initialiser første skridt
    showStep(1);
});

// Funktion til at håndtere container options
function setupContainerOptions() {
    const createContainersCheckbox = document.getElementById('createContainers');
    const existingContainerSection = document.getElementById('existingContainerSection');
    const newContainerOption = document.getElementById('newContainerOption');
    const existingContainerOption = document.getElementById('existingContainerOption');
    const containerDetailsSection = document.getElementById('containerDetailsSection');
    const existingContainerSelectArea = document.getElementById('existingContainerSelectArea');
    
    if (!createContainersCheckbox || !existingContainerSection) return;
    
    // Vis/skjul container options baseret på om containere er aktiveret
    createContainersCheckbox.addEventListener('change', function() {
        existingContainerSection.classList.toggle('d-none', !this.checked);
        containerDetailsSection.classList.toggle('d-none', !this.checked || existingContainerOption.checked);
    });
    
    // Håndter radioknap valg
    newContainerOption.addEventListener('change', function() {
        if (this.checked) {
            containerDetailsSection.classList.remove('d-none');
            existingContainerSelectArea.classList.add('d-none');
        }
    });
    
    existingContainerOption.addEventListener('change', function() {
        if (this.checked) {
            containerDetailsSection.classList.add('d-none');
            existingContainerSelectArea.classList.remove('d-none');
            fetchExistingContainers();
        }
    });
}

// Funktion til at hente eksisterende containere
function fetchExistingContainers() {
    const existingContainerSelect = document.getElementById('existingContainerSelect');
    if (!existingContainerSelect) return;
    
    // Ryd eksisterende options bortset fra den første
    while (existingContainerSelect.options.length > 1) {
        existingContainerSelect.remove(1);
    }
    
    // Tilføj en "indlæser..." option
    const loadingOption = document.createElement('option');
    loadingOption.textContent = 'Indlæser containere...';
    loadingOption.disabled = true;
    existingContainerSelect.appendChild(loadingOption);
    
    // Hent containere fra serveren
    fetch('/api/containers/available')
        .then(response => response.json())
        .then(data => {
            // Fjern "indlæser..." option
            existingContainerSelect.remove(existingContainerSelect.options.length - 1);
            
            if (data.containers && data.containers.length > 0) {
                data.containers.forEach(container => {
                    const option = document.createElement('option');
                    option.value = container.ContainerID;
                    option.textContent = `${container.ContainerID}: ${container.Description} (${container.sample_count || 0} prøver)`;
                    existingContainerSelect.appendChild(option);
                });
            } else {
                const noContainersOption = document.createElement('option');
                noContainersOption.textContent = 'Ingen tilgængelige containere fundet';
                noContainersOption.disabled = true;
                existingContainerSelect.appendChild(noContainersOption);
            }
        })
        .catch(error => {
            console.error('Fejl ved hentning af containere:', error);
            const errorOption = document.createElement('option');
            errorOption.textContent = 'Fejl ved hentning af containere';
            errorOption.disabled = true;
            existingContainerSelect.appendChild(errorOption);
        });
}

// Sæt default udløbsdato
function setDefaultExpiryDate() {
    const expiryInput = document.querySelector('input[name="expiryDate"]');
    if (expiryInput) {
        const defaultDate = new Date();
        defaultDate.setMonth(defaultDate.getMonth() + REGISTRATION_EXPIRY_MONTHS);
        const dateString = defaultDate.toISOString().split('T')[0];
        expiryInput.value = dateString;
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
            setupBarcodeInput();
        } else if (step === 4) {
            setupStorageGrid();
        }
        
        // Opdater current step global variabel
        currentStep = step;
    }
}

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

function setupRegistrationSteps() {
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

function validateCurrentStep() {
    clearValidationErrors();
    
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
                showErrorMessage('Indtast venligst en beskrivelse', 'description');
                isValid = false;
            }
            
            if (!totalAmount || totalAmount.value <= 0) {
                showErrorMessage('Indtast venligst et gyldigt antal', 'totalAmount');
                isValid = false;
            }
            
            if (!unit || !unit.value) {
                showErrorMessage('Vælg venligst en enhed', 'unit');
                isValid = false;
            }
            
            return isValid;
        case 3:
            // Validering af identifikation
            const hasSerialNumbers = document.getElementById('hasSerialNumbers')?.checked;
            if (hasSerialNumbers) {
                const expectedCount = parseInt(document.querySelector('[name="totalAmount"]')?.value) || 0;
                if (scannedItems.length < expectedCount) {
                    showErrorMessage(`Der mangler at blive scannet ${expectedCount - scannedItems.length} enheder`);
                    return false;
                }
            }
            return true;
        case 4:
            // Validering af placering
            const isMultiPackage = document.getElementById('isMultiPackage')?.checked || false;
            const packageCount = isMultiPackage ? (parseInt(document.querySelector('[name="packageCount"]')?.value) || 1) : 1;
            
            // For multipakker, tjek om der er valgt lokationer for alle pakker
            if (isMultiPackage && packageCount > 1) {
                if (typeof PackageLocations !== 'undefined') {
                    const selectedLocations = PackageLocations.getSelectedLocations();
                    if (selectedLocations.length < packageCount) {
                        showErrorMessage(`Du skal vælge ${packageCount} lokationer. Du har valgt ${selectedLocations.length}.`);
                        return false;
                    }
                }
                return true;
            } else {
                // Standard validering for én lokation
                if (!selectedLocation) {
                    showErrorMessage('Vælg venligst en placering ved at klikke på en ledig plads i griddet.');
                    return false;
                }
                return true;
            }
        default:
            return true;
    }
}

function setupSerialNumberToggle() {
    const checkbox = document.getElementById('hasSerialNumbers');
    if (checkbox) {
        checkbox.addEventListener('change', () => {
            updateProgress(currentStep);
        });
    }
}

// Funktion til at håndtere løs mængde vs. stk
function setupBulkSampleHandling() {
    const isBulkSampleCheckbox = document.getElementById('isBulkSample');
    const unitSelect = document.querySelector('[name="unit"]');
    
    if (isBulkSampleCheckbox && unitSelect) {
        // Gem alle originale options til senere brug
        const allOptions = Array.from(unitSelect.options);
        const stkOption = Array.from(unitSelect.options).find(opt => 
            opt.textContent.trim().toLowerCase() === 'stk' || 
            opt.textContent.trim().toLowerCase() === 'pcs');
        
        // Standardindstilling: Kun stk er tilgængelig
        updateUnitOptions(false);
        
        // Håndter ændringer i checkboksen
        isBulkSampleCheckbox.addEventListener('change', function() {
            updateUnitOptions(this.checked);
        });
        
        // Hjælpefunktion til at opdatere unit-options
        function updateUnitOptions(isBulk) {
            // Gem det aktuelle valg
            const currentValue = unitSelect.value;
            
            // Ryd alle options
            unitSelect.innerHTML = '';
            
            // Tilføj tom valgmulighed
            const emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = 'Vælg enhed';
            unitSelect.appendChild(emptyOption);
            
            if (isBulk) {
                // Ved løs mængde: Tilføj alle enheder undtagen stk
                allOptions.forEach(option => {
                    if (option.value && option.textContent.trim().toLowerCase() !== 'stk' && 
                        option.textContent.trim().toLowerCase() !== 'pcs') {
                        unitSelect.appendChild(option.cloneNode(true));
                    }
                });
                
                // Nulstil value (tvinger brugeren til at vælge enhed)
                unitSelect.value = '';
            } else {
                // Ved stykgods: Kun stk er tilgængelig
                if (stkOption) {
                    unitSelect.appendChild(stkOption.cloneNode(true));
                    unitSelect.value = stkOption.value;
                } else {
                    // Fallback hvis vi ikke fandt stk-option
                    const newStkOption = document.createElement('option');
                    newStkOption.value = "1"; // Antager at stk har ID=1
                    newStkOption.textContent = 'stk';
                    unitSelect.appendChild(newStkOption);
                    unitSelect.value = "1";
                }
            }
        }
    }
}

// Lyt efter ændringer i checkboxes for multipakker og forskellige lokationer
function setupMultiPackageHandling() {
    const isMultiPackageCheckbox = document.getElementById('isMultiPackage');
    const multiplePackageFields = document.getElementById('multiplePackageFields');
    const packageCountInput = document.querySelector('[name="packageCount"]');
    const amountPerPackageInput = document.querySelector('[name="amountPerPackage"]');
    const totalAmountInput = document.querySelector('[name="totalAmount"]');
    const calculatedTotal = document.getElementById('calculatedTotal');
    const totalAmountHelper = document.getElementById('totalAmountHelper');
    const totalCounter = document.getElementById('totalCount');
    
    // Fjern den del der viser "forskellige lokationer" i step 2
    // Det skal kun vises i step 4
    const differentLocationsCheckbox = document.getElementById('differentLocations');
    if (differentLocationsCheckbox) {
        // Skjul denne checkbox og dens label
        const parentElement = differentLocationsCheckbox.closest('.form-check');
        if (parentElement) {
            parentElement.classList.add('d-none');
        }
    }
    
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
                
                // Nulstil pakkelokationer
                if (typeof PackageLocations !== 'undefined') {
                    PackageLocations.reset();
                }
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
            
            // Opdater også totalCounter for scanning
            if (totalCounter) {
                totalCounter.textContent = total;
            }
        }
    }
    
    // Lyt efter ændringer i pakke-felterne
    if (packageCountInput && amountPerPackageInput) {
        packageCountInput.addEventListener('input', updateTotalAmount);
        amountPerPackageInput.addEventListener('input', updateTotalAmount);
        
        // Lyt også efter ændringer i totalAmount
        if (totalAmountInput) {
            totalAmountInput.addEventListener('input', function() {
                if (totalCounter) {
                    totalCounter.textContent = this.value || 0;
                }
            });
        }
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
                    <button type="button" class="btn btn-sm btn-outline-danger remove-item" data-index="${index}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        });
        
        html += '</div>';
        container.innerHTML = html;
        
        // Tilføj event listeners til fjern-knapper
        container.querySelectorAll('.remove-item').forEach(button => {
            button.addEventListener('click', function() {
                const index = parseInt(this.getAttribute('data-index'));
                removeScannedItem(index);
            });
        });
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

function createGridFromLocations(locations) {
    console.log("createGridFromLocations med", locations.length, "lokationer");
    
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '';
    
    // Sortér lokationerne for at sikre konsistent visning
    locations.sort((a, b) => a.LocationName.localeCompare(b.LocationName));

    // Opbyg grid med data fra API
    locations.forEach(location => {
        const cell = document.createElement('div');
        cell.className = 'storage-cell';
        
        // Debug info
        console.log("Behandler lokation:", location);
        
        // Markér cellen som optaget hvis der er prøver på lokationen
        if (location.status === 'occupied') {
            cell.classList.add('occupied');
        }

        const locationEl = document.createElement('div');
        locationEl.className = 'location';
        locationEl.textContent = location.LocationName;

        const capacity = document.createElement('div');
        capacity.className = 'capacity';
        capacity.textContent = location.status === 'occupied' ? 'Optaget' : 'Ledig';

        cell.appendChild(locationEl);
        cell.appendChild(capacity);
        grid.appendChild(cell);

        // Kun tilføj event listener til ledige celler
        if (location.status !== 'occupied') {
            cell.addEventListener('click', () => selectStorageCell(cell));
        }
    });
}

function setupStorageGrid() {
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '<div class="text-center p-3"><div class="spinner-border"></div><p>Indlæser lagerplaceringer...</p></div>';

    // Hent lagerplaceringer fra API
    fetch('/api/storage-locations')
        .then(response => response.json())
        .then(data => {
            console.log("Modtaget lagerplaceringsdata:", data);
            if (data.locations) {
                createGridFromLocations(data.locations);
            } else {
                console.error("Ingen locations i responsen");
                // Fallback til hardcodede lokationer
                createSpecificStorageGrid();
            }
        })
        .catch(error => {
            console.error('Fejl ved hentning af lagerplaceringer:', error);
            // Fallback til hardcodede lokationer
            createSpecificStorageGrid();
        });
}

// Vi bibeholder vores grid-skabende funktion
function createSpecificStorageGrid() {
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '';
    
    // Opret 12 lagerpladser med format A1.B1 til A3.B4
    for (let i = 1; i <= 3; i++) {
        for (let j = 1; j <= 4; j++) {
            const cell = document.createElement('div');
            cell.className = 'storage-cell';
            
            // Simuler at nogle celler er optaget (for demonstration)
            // I en faktisk implementering ville denne data komme fra serveren
            if ((i === 1 && j === 3) || (i === 2 && j === 2)) {
                cell.classList.add('occupied');
            }

            const locationEl = document.createElement('div');
            locationEl.className = 'location';
            locationEl.textContent = `A${i}.B${j}`;

            const capacity = document.createElement('div');
            capacity.className = 'capacity';
            capacity.textContent = cell.classList.contains('occupied') ? 'Optaget' : 'Ledig';

            cell.appendChild(locationEl);
            cell.appendChild(capacity);
            grid.appendChild(cell);

            // Vigtig: Kun tilføj event listener til ledige celler
            if (!cell.classList.contains('occupied')) {
                cell.addEventListener('click', () => selectStorageCell(cell));
            }
        }
    }
}

// Highlighte et antal celler i storage gridden baseret på pakkeantal
function storageGridHighlightForPackages(packageCount) {
    // Reset grid highlighting først
    resetStorageGridHighlighting();
    
    // Markér alle LEDIGE celler som tilgængelige
    const gridCells = document.querySelectorAll('.storage-cell:not(.occupied)');
    gridCells.forEach(cell => {
        cell.classList.add('multi-package-available');
    });
    
    // Tilføj info-besked hvis nødvendigt
    if (packageCount > 1) {
        const existingMessage = document.querySelector('.multi-package-message');
        if (!existingMessage) {
            const message = document.createElement('div');
            message.className = 'alert alert-info multi-package-message mt-3';
            message.innerHTML = `<i class="fas fa-info-circle"></i> Vælg ${packageCount} forskellige placeringer til dine pakker.`;
            
            const storageSelector = document.querySelector('.storage-selector');
            if (storageSelector) {
                storageSelector.appendChild(message);
            }
        }
    }
}

// Fjern highlighting fra storage grid
function resetStorageGridHighlighting() {
    document.querySelectorAll('.storage-cell').forEach(cell => {
        cell.classList.remove('multi-package-available', 'multi-package-selected');
    });
    
    // Fjern eventuel info-besked
    const message = document.querySelector('.multi-package-message');
    if (message) {
        message.remove();
    }
    
    // Fjern eventuel pakkeopsummering-besked
    const packageSummary = document.querySelector('.package-selection-summary');
    if (packageSummary) {
        packageSummary.remove();
    }
}

// Opdateret selectStorageCell funktion - med direkte gemning af lokation uden dropdown
function selectStorageCell(cell) {
    if (cell.classList.contains('occupied')) {
        // Blokér valg af optagne celler
        showWarningMessage("Denne placering er allerede optaget. Vælg venligst en ledig placering.");
        return;
    }
    
    const isMultiPackage = document.getElementById('isMultiPackage')?.checked || false;
    const packageCount = isMultiPackage ? (parseInt(document.querySelector('[name="packageCount"]')?.value) || 1) : 1;
    
    if (isMultiPackage && packageCount > 1) {
        // Håndter multipakke-valg
        handleMultiPackageSelection(cell);
    } else {
        // Standard valg af lokation (én lokation)
        handleSingleLocationSelection(cell);
    }
    
    // Opdater visning af valgte pakker
    updatePackageSelectionSummary();
}

// Håndterer valg af lokation for enkelte prøver
function handleSingleLocationSelection(cell) {
    // Fjern markering fra alle celler
    document.querySelectorAll('.storage-cell').forEach(c => c.classList.remove('selected'));
    
    // Marker den valgte celle
    cell.classList.add('selected');
    
    // Gem lokationen direkte i et hidden input field
    const locationText = cell.querySelector('.location').textContent;
    
    // Find eksisterende eller opret nyt hidden input til at gemme lokationen
    let locationInput = document.getElementById('selectedLocationInput');
    if (!locationInput) {
        locationInput = document.createElement('input');
        locationInput.type = 'hidden';
        locationInput.name = 'storageLocation';
        locationInput.id = 'selectedLocationInput';
        document.querySelector('.storage-selector').appendChild(locationInput);
    }
    
    // Gem lokationsnavnet (vi finder det faktiske ID ved formularindsendelse)
    locationInput.value = locationText;
    
    // Opdater også en synlig indikator
    let locationIndicator = document.querySelector('.selected-location-indicator');
    if (!locationIndicator) {
        locationIndicator = document.createElement('div');
        locationIndicator.className = 'selected-location-indicator mt-3 p-2 bg-light rounded';
        document.querySelector('.storage-selector').appendChild(locationIndicator);
    }
    
    locationIndicator.innerHTML = `<strong>Valgt placering:</strong> ${locationText}`;
    
    // Gem også som global variabel for kompatibilitet
    selectedLocation = locationText;
}

// Håndterer valg af lokation for multipakker
function handleMultiPackageSelection(cell) {
    const packageCount = parseInt(document.querySelector('[name="packageCount"]')?.value) || 1;
    const selectedCellsCount = document.querySelectorAll('.storage-cell.multi-package-selected').length;
    
    // Tjek om cellen allerede er valgt
    if (cell.classList.contains('multi-package-selected')) {
        // Afvælg cellen
        cell.classList.remove('multi-package-selected');
        cell.classList.add('multi-package-available');
        
        // Find lokationen og fjern den fra pakkelokationer-listen
        const locationText = cell.querySelector('.location').textContent;
        
        // Find pakkenummeret baseret på rækkefølgen af valget
        if (typeof PackageLocations !== 'undefined') {
            PackageLocations.removeLocationByName(locationText);
        }
    } else {
        // Tjek om vi allerede har valgt maksimalt antal lokationer
        if (selectedCellsCount < packageCount) {
            // Vælg cellen
            cell.classList.add('multi-package-selected');
            cell.classList.remove('multi-package-available');
            
            // Tilføj til pakkelokationer (med næste ledige pakkenummer)
            if (typeof PackageLocations !== 'undefined') {
                const locationText = cell.querySelector('.location').textContent;
                
                // Tilføj lokationen til den næste ledige pakke
                PackageLocations.addLocation(selectedCellsCount + 1, mapLocationNameToId(locationText), locationText);
            }
        } else {
            // Vi har allerede valgt max antal - vis fejl
            showWarningMessage(`Du kan maksimalt vælge ${packageCount} lokationer. Fjern en lokation før du tilføjer en ny.`);
        }
    }
}

// Opdater visning af valgte pakker og lokationer
function updatePackageSelectionSummary() {
    const isMultiPackage = document.getElementById('isMultiPackage')?.checked || false;
    const packageCount = isMultiPackage ? (parseInt(document.querySelector('[name="packageCount"]')?.value) || 1) : 1;
    
    // Kun vis opsummering for multipakker
    if (!isMultiPackage || packageCount <= 1) return;
    
    // Find eller opret opsummerings-container
    let summaryContainer = document.querySelector('.package-selection-summary');
    if (!summaryContainer) {
        summaryContainer = document.createElement('div');
        summaryContainer.className = 'package-selection-summary mt-4';
        
        const storageSelector = document.querySelector('.storage-selector');
        if (storageSelector) {
            storageSelector.appendChild(summaryContainer);
        }
    }
    
    // Hent valgte pakkelokationer
    if (typeof PackageLocations === 'undefined') return;
    
    const selectedLocations = PackageLocations.getSelectedLocations();
    
    // Opdater opsummering
    if (selectedLocations.length === 0) {
        summaryContainer.innerHTML = '';
        summaryContainer.classList.add('d-none');
        return;
    }
    
    summaryContainer.classList.remove('d-none');
    
    // Sortér efter pakkenummer
    const sortedLocations = [...selectedLocations].sort((a, b) => 
        parseInt(a.packageNumber) - parseInt(b.packageNumber));
    
    let html = `
        <div class="card">
            <div class="card-header bg-light">
                <h5 class="mb-0">Valgte pakkelokationer</h5>
            </div>
            <div class="card-body">
                <ul class="list-group list-group-flush">
    `;
    
    sortedLocations.forEach(pkg => {
        html += `
            <li class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <span class="badge bg-primary me-2">Pakke ${pkg.packageNumber}</span>
                    <span>${pkg.locationName}</span>
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger remove-location" data-package="${pkg.packageNumber}">
                    <i class="fas fa-times"></i>
                </button>
            </li>
        `;
    });
    
    html += `
                </ul>
            </div>
            <div class="card-footer">
                <div class="d-flex justify-content-between align-items-center">
                    <span>${selectedLocations.length} af ${packageCount} lokationer valgt</span>
                    <button type="button" class="btn btn-sm btn-outline-secondary" id="clearAllLocations">
                        Ryd alle
                    </button>
                </div>
            </div>
        </div>
    `;
    
    summaryContainer.innerHTML = html;
    
    // Tilføj event listeners til fjern-knapper
    summaryContainer.querySelectorAll('.remove-location').forEach(button => {
        button.addEventListener('click', function() {
            const packageNumber = this.getAttribute('data-package');
            const locationData = PackageLocations.getLocationByPackage(packageNumber);
            
            if (locationData) {
                // Find og opdater den tilsvarende grid-celle
                const gridCells = document.querySelectorAll('.storage-cell');
                gridCells.forEach(cell => {
                    const locationText = cell.querySelector('.location')?.textContent;
                    if (locationText === locationData.locationName) {
                        cell.classList.remove('multi-package-selected');
                        cell.classList.add('multi-package-available');
                    }
                });
                
                // Fjern fra pakkelokationer
                PackageLocations.removeLocation(packageNumber);
                
                // Opdater opsummering
                updatePackageSelectionSummary();
            }
        });
    });
    
    // Tilføj event listener til "ryd alle" knappen
    const clearAllBtn = document.getElementById('clearAllLocations');
    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', function() {
            // Fjern alle valgte lokationer
            PackageLocations.reset();
            
            // Nulstil grid-celler
            const gridCells = document.querySelectorAll('.storage-cell.multi-package-selected');
            gridCells.forEach(cell => {
                cell.classList.remove('multi-package-selected');
                cell.classList.add('multi-package-available');
            });
            
            // Opdater opsummering
            updatePackageSelectionSummary();
        });
    }
}

// Initialiser receptionsdato hvis nødvendigt
function initReceptionDate() {
    // Intet at gøre her i denne implementering
}

// Hjælpefunktion til at mappe lokationsnavn til ID
function mapLocationNameToId(locationName) {
    // Dette er en enkel implementering. I et rigtigt system ville dette
    // sandsynligvis slå op i en tabel eller API
    
    // Format: A{row}.B{column} hvor row=1-3, column=1-4
    const match = locationName.match(/A(\d+)\.B(\d+)/);
    if (match) {
        const row = parseInt(match[1]);
        const column = parseInt(match[2]);
        
        // Beregn et ID baseret på række og kolonne
        // Antager at ID'er starter fra 1 og går op til 12
        const id = (row - 1) * 4 + column;
        
        return id.toString();
    }
    
    // Fallback
    return "1";
}

// Håndter form submission
function handleFormSubmission() {
    if (!validateCurrentStep()) return;
    
    // Saml alle data fra formular
    const formData = {
        // Modtagelsesoplysninger
        supplier: document.querySelector('[name="supplier"]')?.value || '',
        trackingNumber: document.querySelector('[name="trackingNumber"]')?.value || '',
        
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
        
        // Container-funktionalitet
        createContainers: document.getElementById('createContainers')?.checked || false,
        
        // Identifikation
        serialNumbers: scannedItems || [],
        
        // Lokation - nu fra valgt celle i stedet for dropdown
        storageLocation: document.getElementById('selectedLocationInput')?.value || selectedLocation || ''
    };
    
    // Hvis vi har valgt location ved at klikke på en celle, konverter locationName til et ID
    if (formData.storageLocation && !formData.storageLocation.match(/^\d+$/)) {
        formData.storageLocation = mapLocationNameToId(formData.storageLocation);
    }
    
    // Hvis PackageLocations modul er tilgængeligt, hent pakkedata
    if (typeof PackageLocations !== 'undefined') {
        const packageLocationsData = PackageLocations.getData();
        
        // For hvert valgt lokationsnavn, omsæt til location ID
        if (packageLocationsData.packageLocations) {
            packageLocationsData.packageLocations = packageLocationsData.packageLocations.map(pkg => {
                if (pkg.locationName && (!pkg.locationId || isNaN(pkg.locationId))) {
                    // Konverter locationName til locationId
                    return {
                        packageNumber: pkg.packageNumber,
                        locationId: mapLocationNameToId(pkg.locationName)
                    };
                }
                return pkg;
            });
        }
        
        Object.assign(formData, packageLocationsData);
    }
    
    // Hvis ContainerModule er tilgængeligt, hent container-data
    if (typeof ContainerModule !== 'undefined') {
        formData.createContainers = ContainerModule.isEnabled();
        ContainerModule.addToFormData(formData);
    }
    
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
            let successMessage = `Prøve ${data.sample_id} er blevet registreret succesfuldt!`;
            
            // Tilføj information om containere hvis relevant
            if (data.container_ids && data.container_ids.length > 0) {
                successMessage += ` ${data.container_ids.length} containere blev oprettet.`;
            }
            
            showSuccessMessage(successMessage);
            
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
    
    // Reset pakkelokationer
    if (typeof PackageLocations !== 'undefined') {
        PackageLocations.reset();
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
    // Fjern eksisterende fejlmeddelelser
    clearValidationErrors();
    
    const successToast = document.createElement('div');
    successToast.className = 'custom-toast success-toast';
    successToast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-check-circle"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">Succes</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    document.body.appendChild(successToast);

    // Tilføj 'show' klasse efter en kort forsinkelse (for animationseffekt)
    setTimeout(() => successToast.classList.add('show'), 10);

    // Fjern automatisk efter 3 sekunder
    setTimeout(() => {
        successToast.classList.remove('show');
        setTimeout(() => successToast.remove(), 300);
    }, 3000);
}

function showErrorMessage(message, field = null) {
    const errorToast = document.createElement('div');
    errorToast.className = 'custom-toast error-toast';
    errorToast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-exclamation-circle"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">Fejl</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    document.body.appendChild(errorToast);

    // Tilføj 'show' klasse efter en kort forsinkelse (for animationseffekt)
    setTimeout(() => errorToast.classList.add('show'), 10);

    // Fjern automatisk efter 5 sekunder
    setTimeout(() => {
        errorToast.classList.remove('show');
        setTimeout(() => errorToast.remove(), 300);
    }, 5000);
    
    // Hvis et bestemt felt er angivet, marker det med en fejl
    if (field) {
        const fieldElement = document.querySelector(`[name="${field}"]`);
        if (fieldElement) {
            fieldElement.classList.add('field-error');
            
            // Tilføj fejlmeddelelse under feltet
            const fieldContainer = fieldElement.closest('.form-group');
            if (fieldContainer) {
                // Fjern eventuelle eksisterende fejlmeddelelser
                const existingError = fieldContainer.querySelector('.field-error-message');
                if (existingError) existingError.remove();
                
                // Tilføj ny fejlmeddelelse
                const errorMsg = document.createElement('div');
                errorMsg.className = 'field-error-message';
                errorMsg.textContent = message;
                fieldContainer.appendChild(errorMsg);
                
                // Tilføj lyttere til at fjerne fejlmarkering ved input
                fieldElement.addEventListener('input', function() {
                    this.classList.remove('field-error');
                    const errorMsg = fieldContainer.querySelector('.field-error-message');
                    if (errorMsg) errorMsg.remove();
                });
            }
        }
    }
}

function showWarningMessage(message) {
    const warningToast = document.createElement('div');
    warningToast.className = 'custom-toast warning-toast';
    warningToast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-exclamation-triangle"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">Advarsel</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    document.body.appendChild(warningToast);

    // Tilføj 'show' klasse efter en kort forsinkelse (for animationseffekt)
    setTimeout(() => warningToast.classList.add('show'), 10);

    // Fjern automatisk efter 4 sekunder
    setTimeout(() => {
        warningToast.classList.remove('show');
        setTimeout(() => warningToast.remove(), 300);
    }, 4000);
}

// Hjælpefunktion til at fjerne alle valideringsfejl
function clearValidationErrors() {
    // Fjern fejlklasser fra alle felter
    document.querySelectorAll('.field-error').forEach(field => {
        field.classList.remove('field-error');
    });
    
    // Fjern alle fejlmeddelelser
    document.querySelectorAll('.field-error-message').forEach(msg => {
        msg.remove();
    });
}