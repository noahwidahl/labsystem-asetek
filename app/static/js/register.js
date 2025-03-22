// Basic variables for multistep
let currentStep = 1;
const totalSteps = 4;
let scannedItems = [];
let selectedLocation = null;
const REGISTRATION_EXPIRY_MONTHS = 2;

// Initialize when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Set default expiry date to 2 months ahead
    setDefaultExpiryDate();
    
    // Setup registration form steps
    setupRegistrationSteps();
    
    // Setup serial number toggle
    setupSerialNumberToggle();
    
    // Setup multi-package handling
    setupMultiPackageHandling();
    
    // Setup scanner functionality
    setupScannerListeners();
    
    // Setup bulk sample handling (for units)
    setupBulkSampleHandling();
    
    // Setup container options
    setupContainerOptions();
    
    // Initialize first step
    showStep(1);
});

// Function to handle container options
function setupContainerOptions() {
    const createContainersCheckbox = document.getElementById('createContainers');
    const existingContainerSection = document.getElementById('existingContainerSection');
    const newContainerOption = document.getElementById('newContainerOption');
    const existingContainerOption = document.getElementById('existingContainerOption');
    const containerDetailsSection = document.getElementById('containerDetailsSection');
    const existingContainerSelectArea = document.getElementById('existingContainerSelectArea');
    
    if (!createContainersCheckbox || !existingContainerSection) return;
    
    // Show/hide container options based on whether containers are enabled
    createContainersCheckbox.addEventListener('change', function() {
        existingContainerSection.classList.toggle('d-none', !this.checked);
        containerDetailsSection.classList.toggle('d-none', !this.checked || existingContainerOption.checked);
    });
    
    // Handle radio button selection
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

// Function to fetch existing containers
function fetchExistingContainers() {
    const existingContainerSelect = document.getElementById('existingContainerSelect');
    if (!existingContainerSelect) return;
    
    // Clear existing options except the first one
    while (existingContainerSelect.options.length > 1) {
        existingContainerSelect.remove(1);
    }
    
    // Add a "loading..." option
    const loadingOption = document.createElement('option');
    loadingOption.textContent = 'Loading containers...';
    loadingOption.disabled = true;
    existingContainerSelect.appendChild(loadingOption);
    
    // Fetch containers from server
    fetch('/api/containers/available')
        .then(response => response.json())
        .then(data => {
            // Remove "loading..." option
            existingContainerSelect.remove(existingContainerSelect.options.length - 1);
            
            if (data.containers && data.containers.length > 0) {
                data.containers.forEach(container => {
                    const option = document.createElement('option');
                    option.value = container.ContainerID;
                    option.textContent = `${container.ContainerID}: ${container.Description} (${container.sample_count || 0} samples)`;
                    existingContainerSelect.appendChild(option);
                });
            } else {
                const noContainersOption = document.createElement('option');
                noContainersOption.textContent = 'No available containers found';
                noContainersOption.disabled = true;
                existingContainerSelect.appendChild(noContainersOption);
            }
        })
        .catch(error => {
            console.error('Error fetching containers:', error);
            const errorOption = document.createElement('option');
            errorOption.textContent = 'Error fetching containers';
            errorOption.disabled = true;
            existingContainerSelect.appendChild(errorOption);
        });
}

// Set default expiry date
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

        // Initialize the current page
        if (step === 1) {
            initReceptionDate();
        } else if (step === 3 && document.getElementById('hasSerialNumbers').checked) {
            setupBarcodeInput();
        } else if (step === 4) {
            setupStorageGrid();
        }
        
        // Update current step global variable
        currentStep = step;
    }
}

function updateProgress(step) {
    const progress = ((step - 1) / (totalSteps - 1)) * 100;
    
    // Update all progress bars on the page
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        bar.style.width = `${progress}%`;
    });
    
    // Update steps display
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
        nextButton.textContent = step === totalSteps ? 'Save' : 'Next';
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
        
        // Always increment to next step first
        currentStep += 1;
        
        // If we land on identification step (step 3) and there are no serial numbers, skip to step 4
        if (currentStep === 3 && !hasSerialNumbers) {
            currentStep = 4;
        }
        
        // Make sure we don't go beyond the maximum number of steps
        currentStep = Math.min(currentStep, totalSteps);
        
        showStep(currentStep);
    }
}

function previousStep() {
    const hasSerialNumbers = document.getElementById('hasSerialNumbers')?.checked || false;
    
    // Always decrement to previous step first
    currentStep -= 1;
    
    // If we land on identification step (step 3) and there are no serial numbers, skip to step 2
    if (currentStep === 3 && !hasSerialNumbers) {
        currentStep = 2;
    }
    
    // Make sure we don't go below the first step
    currentStep = Math.max(currentStep, 1);
    
    showStep(currentStep);
}

// Function to validate the current step
function validateCurrentStep() {
    clearValidationErrors();
    
    switch(currentStep) {
        case 1:
            // Validation of reception information - no mandatory fields
            return true;
        case 2:
            // Validation of sample information
            const description = document.querySelector('[name="description"]');
            const totalAmount = document.querySelector('[name="totalAmount"]');
            const unit = document.querySelector('[name="unit"]');
            
            let isValid = true;
            
            if (!description || !description.value.trim()) {
                showErrorMessage('Please enter a description', 'description');
                isValid = false;
            }
            
            if (!totalAmount || totalAmount.value <= 0) {
                showErrorMessage('Please enter a valid amount', 'totalAmount');
                isValid = false;
            }
            
            if (!unit || !unit.value) {
                showErrorMessage('Please select a unit', 'unit');
                isValid = false;
            }
            
            return isValid;
        case 3:
            // Validation of identification
            const hasSerialNumbers = document.getElementById('hasSerialNumbers')?.checked;
            if (hasSerialNumbers) {
                const expectedCount = parseInt(document.querySelector('[name="totalAmount"]')?.value) || 0;
                if (scannedItems.length < expectedCount) {
                    showErrorMessage(`${expectedCount - scannedItems.length} more samples need to be scanned`);
                    return false;
                }
            }
            return true;
        case 4:
            // Validation of location
            const isMultiPackage = document.getElementById('isMultiPackage')?.checked || false;
            const packageCount = isMultiPackage ? (parseInt(document.querySelector('[name="packageCount"]')?.value) || 1) : 1;
            
            // For multi-packages, check if locations are selected for all packages
            if (isMultiPackage && packageCount > 1) {
                if (typeof PackageLocations !== 'undefined') {
                    const selectedLocations = PackageLocations.getSelectedLocations();
                    if (selectedLocations.length < packageCount) {
                        showErrorMessage(`You need to select ${packageCount} locations. You have selected ${selectedLocations.length}.`);
                        return false;
                    }
                }
                return true;
            } else {
                // Standard validation for one location
                if (!selectedLocation) {
                    showErrorMessage('Please select a location by clicking on an available space in the grid.');
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

// Function to handle bulk quantity vs. pieces
function setupBulkSampleHandling() {
    const isBulkSampleCheckbox = document.getElementById('isBulkSample');
    const unitSelect = document.querySelector('[name="unit"]');
    
    if (isBulkSampleCheckbox && unitSelect) {
        // Save all original options for later use
        const allOptions = Array.from(unitSelect.options);
        const stkOption = Array.from(unitSelect.options).find(opt => 
            opt.textContent.trim().toLowerCase() === 'pcs' || 
            opt.textContent.trim().toLowerCase() === 'pcs');
        
        // Default setting: Only pcs is available
        updateUnitOptions(false);
        
        // Handle changes in the checkbox
        isBulkSampleCheckbox.addEventListener('change', function() {
            updateUnitOptions(this.checked);
        });
        
        // Helper function to update unit options
        function updateUnitOptions(isBulk) {
            // Save the current selection
            const currentValue = unitSelect.value;
            
            // Clear all options
            unitSelect.innerHTML = '';
            
            // Add empty option
            const emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = 'Select unit';
            unitSelect.appendChild(emptyOption);
            
            if (isBulk) {
                // For bulk quantity: Add all units except pcs
                allOptions.forEach(option => {
                    if (option.value && option.textContent.trim().toLowerCase() !== 'pcs' && 
                        option.textContent.trim().toLowerCase() !== 'pcs') {
                        unitSelect.appendChild(option.cloneNode(true));
                    }
                });
                
                // Reset value (forces the user to select a unit)
                unitSelect.value = '';
            } else {
                // For pieces: Only pcs is available
                if (stkOption) {
                    unitSelect.appendChild(stkOption.cloneNode(true));
                    unitSelect.value = stkOption.value;
                } else {
                    // Fallback if we didn't find pcs option
                    const newStkOption = document.createElement('option');
                    newStkOption.value = "1"; // Assuming pcs has ID=1
                    newStkOption.textContent = 'pcs';
                    unitSelect.appendChild(newStkOption);
                    unitSelect.value = "1";
                }
            }
        }
    }
}

// Listen for changes in checkboxes for multi-packages and different locations
function setupMultiPackageHandling() {
    const isMultiPackageCheckbox = document.getElementById('isMultiPackage');
    const multiplePackageFields = document.getElementById('multiplePackageFields');
    const packageCountInput = document.querySelector('[name="packageCount"]');
    const amountPerPackageInput = document.querySelector('[name="amountPerPackage"]');
    const totalAmountInput = document.querySelector('[name="totalAmount"]');
    const calculatedTotal = document.getElementById('calculatedTotal');
    const totalAmountHelper = document.getElementById('totalAmountHelper');
    const totalCounter = document.getElementById('totalCount');
    
    // Remove the part that shows "different locations" in step 2
    // It should only be shown in step 4
    const differentLocationsCheckbox = document.getElementById('differentLocations');
    if (differentLocationsCheckbox) {
        // Hide this checkbox and its label
        const parentElement = differentLocationsCheckbox.closest('.form-check');
        if (parentElement) {
            parentElement.classList.add('d-none');
        }
    }
    
    // Show/hide fields for multiple packages
    if (isMultiPackageCheckbox && multiplePackageFields) {
        isMultiPackageCheckbox.addEventListener('change', function() {
            multiplePackageFields.classList.toggle('d-none', !this.checked);
            
            if (this.checked) {
                totalAmountHelper.textContent = "Total amount is automatically calculated from package information";
                totalAmountInput.readOnly = true;
            } else {
                totalAmountHelper.textContent = "Total number of units received";
                totalAmountInput.readOnly = false;
                
                // Reset package locations
                if (typeof PackageLocations !== 'undefined') {
                    PackageLocations.reset();
                }
            }
            
            // Update total amount when checkbox changes
            updateTotalAmount();
        });
    }
    
    // Calculate total amount based on number of packages and amount per package
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
            
            // Also update totalCounter for scanning
            if (totalCounter) {
                totalCounter.textContent = total;
            }
        }
    }
    
    // Listen for changes in package fields
    if (packageCountInput && amountPerPackageInput) {
        packageCountInput.addEventListener('input', updateTotalAmount);
        amountPerPackageInput.addEventListener('input', updateTotalAmount);
        
        // Also listen for changes in totalAmount
        if (totalAmountInput) {
            totalAmountInput.addEventListener('input', function() {
                if (totalCounter) {
                    totalCounter.textContent = this.value || 0;
                }
            });
        }
    }
}

// Scanner functionality
function setupScannerListeners() {
    const scannerInput = document.getElementById('barcodeInput');
    const addManualBtn = document.getElementById('addManualBtn');
    const scanButton = document.getElementById('scanButton');
    const bulkEntryButton = document.getElementById('bulkEntryButton');
    const bulkEntrySection = document.querySelector('.bulk-entry');
    const addBulkBtn = document.getElementById('addBulkBtn');
    const clearAllScannedBtn = document.getElementById('clearAllScannedBtn');
    
    if (scannerInput && addManualBtn) {
        // Scanner input handling
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
        
        // Manual addition
        addManualBtn.addEventListener('click', function() {
            const barcode = scannerInput.value.trim();
            if (barcode) {
                processScan(barcode);
                scannerInput.value = '';
            }
            scannerInput.focus();
        });
    }
    
    // Toggle scanning state
    if (scanButton) {
        scanButton.addEventListener('click', function() {
            const isActive = this.classList.contains('btn-primary');
            
            if (isActive) {
                // Deactivate scanning
                this.classList.remove('btn-primary');
                this.classList.add('btn-outline-primary');
                this.innerHTML = '<i class="fas fa-barcode"></i> Start Scanning';
                if (scannerInput) {
                    scannerInput.disabled = true;
                    scannerInput.placeholder = "Scanning disabled";
                }
            } else {
                // Activate scanning
                this.classList.remove('btn-outline-primary');
                this.classList.add('btn-primary');
                this.innerHTML = '<i class="fas fa-barcode"></i> Scanning Active';
                if (scannerInput) {
                    scannerInput.disabled = false;
                    scannerInput.placeholder = "Scan or enter serial number";
                    scannerInput.focus();
                }
            }
        });
    }
    
    // Show/hide bulk entry
    if (bulkEntryButton && bulkEntrySection) {
        bulkEntryButton.addEventListener('click', function() {
            bulkEntrySection.classList.toggle('d-none');
            
            if (!bulkEntrySection.classList.contains('d-none')) {
                document.getElementById('bulkBarcodes').focus();
            }
        });
    }
    
    // Add bulk serial numbers
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
                    showErrorMessage(`Cannot add ${barcodes.length} barcodes. Maximum count is ${totalExpected} (${currentCount} already scanned)`);
                    return;
                }
                
                barcodes.forEach(barcode => {
                    processScan(barcode);
                });
                
                bulkBarcodes.value = '';
                showSuccessMessage(`${barcodes.length} barcodes added successfully`);
                
                // Hide bulk entry after addition
                bulkEntrySection.classList.add('d-none');
            }
        });
    }
    
    // Clear all scanned items
    if (clearAllScannedBtn) {
        clearAllScannedBtn.addEventListener('click', function() {
            if (confirm('Are you sure you want to remove all scanned samples?')) {
                scannedItems = [];
                updateScanUI();
                showSuccessMessage('All scanned samples have been removed');
            }
        });
    }
}

// Handle scanning a barcode
function processScan(barcode) {
    if (!barcode) return;

    const totalExpected = parseInt(document.querySelector('[name="totalAmount"]')?.value) || 0;
    
    // Check for duplicates
    if (scannedItems.includes(barcode)) {
        showWarningMessage(`Barcode "${barcode}" has already been scanned`);
        return;
    }

    if (scannedItems.length < totalExpected) {
        scannedItems.push(barcode);
        updateScanUI();
        // Play a sound to indicate successful scanning
        playSuccessSound();
    } else {
        showErrorMessage('Maximum number of samples reached');
    }
}

// Update UI with scanned items
function updateScanUI() {
    const counter = document.getElementById('scannedCount');
    const totalCounter = document.getElementById('totalCount');
    const total = document.querySelector('[name="totalAmount"]')?.value || 0;
    const emptyMessage = document.querySelector('.empty-scanned-message');

    if (counter) counter.textContent = scannedItems.length;
    if (totalCounter) totalCounter.textContent = total;

    const container = document.querySelector('.scanned-items');
    if (container) {
        // Remove empty message if there are scanned items
        if (emptyMessage) {
            emptyMessage.style.display = scannedItems.length > 0 ? 'none' : 'block';
        }
        
        // If no scanned items, show empty message and return
        if (scannedItems.length === 0) {
            container.innerHTML = `<div class="empty-scanned-message text-center p-3 text-muted">
                No samples scanned yet. Use the scanner or enter serial numbers manually above.
            </div>`;
            return;
        }
        
        // Build list of scanned items
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
        
        // Add event listeners to remove buttons
        container.querySelectorAll('.remove-item').forEach(button => {
            button.addEventListener('click', function() {
                const index = parseInt(this.getAttribute('data-index'));
                removeScannedItem(index);
            });
        });
    }
}

// Remove a scanned item
function removeScannedItem(index) {
    scannedItems.splice(index, 1);
    updateScanUI();
}

// Play a success sound when scanning
function playSuccessSound() {
    try {
        // Create a simple sound
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
        // Sound effects are not crucial, so we ignore errors
        console.log('Sound effects not supported');
    }
}

// Focus on barcode input
function setupBarcodeInput() {
    const barcodeInput = document.getElementById('barcodeInput');
    if (barcodeInput) {
        barcodeInput.focus();
    }
}

function createGridFromLocations(locations) {
    console.log("createGridFromLocations with", locations.length, "locations");
    
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '';
    
    // Sort locations to ensure consistent display
    locations.sort((a, b) => a.LocationName.localeCompare(b.LocationName));

    // Build grid with data from API
    locations.forEach(location => {
        const cell = document.createElement('div');
        cell.className = 'storage-cell';
        
        // Debug info
        console.log("Processing location:", location);
        
        // Mark the cell as occupied if there are samples at the location
        if (location.status === 'occupied') {
            cell.classList.add('occupied');
        }

        const locationEl = document.createElement('div');
        locationEl.className = 'location';
        locationEl.textContent = location.LocationName;

        const capacity = document.createElement('div');
        capacity.className = 'capacity';
        capacity.textContent = location.status === 'occupied' ? 'Occupied' : 'Available';

        cell.appendChild(locationEl);
        cell.appendChild(capacity);
        grid.appendChild(cell);

        // Only add event listener to available cells
        if (location.status !== 'occupied') {
            cell.addEventListener('click', () => selectStorageCell(cell));
        }
    });
}

function setupStorageGrid() {
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '<div class="text-center p-3"><div class="spinner-border"></div><p>Loading storage locations...</p></div>';

    // Fetch storage locations from API
    fetch('/api/storage-locations')
        .then(response => response.json())
        .then(data => {
            console.log("Received storage location data:", data);
            if (data.locations) {
                createGridFromLocations(data.locations);
            } else {
                console.error("No locations in response");
                // Fallback to hardcoded locations
                createSpecificStorageGrid();
            }
        })
        .catch(error => {
            console.error('Error fetching storage locations:', error);
            // Fallback to hardcoded locations
            createSpecificStorageGrid();
        });
}

// We maintain our grid creation function
function createSpecificStorageGrid() {
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '';
    
    // Create 12 storage spaces with format A1.B1 to A3.B4
    for (let i = 1; i <= 3; i++) {
        for (let j = 1; j <= 4; j++) {
            const cell = document.createElement('div');
            cell.className = 'storage-cell';
            
            // Simulate that some cells are occupied (for demonstration)
            // In a real implementation, this data would come from the server
            if ((i === 1 && j === 3) || (i === 2 && j === 2)) {
                cell.classList.add('occupied');
            }

            const locationEl = document.createElement('div');
            locationEl.className = 'location';
            locationEl.textContent = `A${i}.B${j}`;

            const capacity = document.createElement('div');
            capacity.className = 'capacity';
            capacity.textContent = cell.classList.contains('occupied') ? 'Occupied' : 'Available';

            cell.appendChild(locationEl);
            cell.appendChild(capacity);
            grid.appendChild(cell);

            // Important: Only add event listener to available cells
            if (!cell.classList.contains('occupied')) {
                cell.addEventListener('click', () => selectStorageCell(cell));
            }
        }
    }
}

// Highlight a number of cells in the storage grid based on package count
function storageGridHighlightForPackages(packageCount) {
    // Reset grid highlighting first
    resetStorageGridHighlighting();
    
    // Mark all AVAILABLE cells as available
    const gridCells = document.querySelectorAll('.storage-cell:not(.occupied)');
    gridCells.forEach(cell => {
        cell.classList.add('multi-package-available');
    });
    
    // Add info message if necessary
    if (packageCount > 1) {
        const existingMessage = document.querySelector('.multi-package-message');
        if (!existingMessage) {
            const message = document.createElement('div');
            message.className = 'alert alert-info multi-package-message mt-3';
            message.innerHTML = `<i class="fas fa-info-circle"></i> Select ${packageCount} different locations for your packages.`;
            
            const storageSelector = document.querySelector('.storage-selector');
            if (storageSelector) {
                storageSelector.appendChild(message);
            }
        }
    }
}

// Remove highlighting from storage grid
function resetStorageGridHighlighting() {
    document.querySelectorAll('.storage-cell').forEach(cell => {
        cell.classList.remove('multi-package-available', 'multi-package-selected');
    });
    
    // Remove any info message
    const message = document.querySelector('.multi-package-message');
    if (message) {
        message.remove();
    }
    
    // Remove any package summary message
    const packageSummary = document.querySelector('.package-selection-summary');
    if (packageSummary) {
        packageSummary.remove();
    }
}

// Updated selectStorageCell function - with direct saving of location without dropdown
function selectStorageCell(cell) {
    if (cell.classList.contains('occupied')) {
        // Block selection of occupied cells
        showWarningMessage("This location is already occupied. Please select an available location.");
        return;
    }
    
    const isMultiPackage = document.getElementById('isMultiPackage')?.checked || false;
    const packageCount = isMultiPackage ? (parseInt(document.querySelector('[name="packageCount"]')?.value) || 1) : 1;
    
    if (isMultiPackage && packageCount > 1) {
        // Handle multi-package selection
        handleMultiPackageSelection(cell);
    } else {
        // Standard location selection (one location)
        handleSingleLocationSelection(cell);
    }
    
    // Update display of selected packages
    updatePackageSelectionSummary();
}

// Handles location selection for individual samples
function handleSingleLocationSelection(cell) {
    // Remove marking from all cells
    document.querySelectorAll('.storage-cell').forEach(c => c.classList.remove('selected'));
    
    // Mark the selected cell
    cell.classList.add('selected');
    
    // Save the location directly in a hidden input field
    const locationText = cell.querySelector('.location').textContent;
    
    // Find existing or create new hidden input to store the location
    let locationInput = document.getElementById('selectedLocationInput');
    if (!locationInput) {
        locationInput = document.createElement('input');
        locationInput.type = 'hidden';
        locationInput.name = 'storageLocation';
        locationInput.id = 'selectedLocationInput';
        document.querySelector('.storage-selector').appendChild(locationInput);
    }
    
    // Save the location name (we find the actual ID during form submission)
    locationInput.value = locationText;
    
    // Update a visible indicator as well
    let locationIndicator = document.querySelector('.selected-location-indicator');
    if (!locationIndicator) {
        locationIndicator = document.createElement('div');
        locationIndicator.className = 'selected-location-indicator mt-3 p-2 bg-light rounded';
        document.querySelector('.storage-selector').appendChild(locationIndicator);
    }
    
    locationIndicator.innerHTML = `<strong>Selected location:</strong> ${locationText}`;
    
    // Also save as global variable for compatibility
    selectedLocation = locationText;
}

// Function to handle multi-package selection
function handleMultiPackageSelection(cell) {
    const packageCount = parseInt(document.querySelector('[name="packageCount"]')?.value) || 1;
    const selectedCellsCount = document.querySelectorAll('.storage-cell.multi-package-selected').length;
    
    // Check if cell is already selected
    if (cell.classList.contains('multi-package-selected')) {
        // Deselect cell
        cell.classList.remove('multi-package-selected');
        cell.classList.add('multi-package-available');
        
        // Find location and remove it from package-locations list
        const locationText = cell.querySelector('.location').textContent;
        
        // Find package number based on selection order
        if (typeof PackageLocations !== 'undefined') {
            PackageLocations.removeLocationByName(locationText);
        }
    } else {
        // Check if we already selected maximum number of locations
        if (selectedCellsCount < packageCount) {
            // Select cell
            cell.classList.add('multi-package-selected');
            cell.classList.remove('multi-package-available');
            
            // Add to package locations (with next available package number)
            if (typeof PackageLocations !== 'undefined') {
                const locationText = cell.querySelector('.location').textContent;
                
                // Add location to next available package
                PackageLocations.addLocation(selectedCellsCount + 1, mapLocationNameToId(locationText), locationText);
            }
        } else {
            // We already selected max count - show error
            showWarningMessage(`You can only select ${packageCount} locations. Remove a location before adding a new one.`);
        }
    }
}

// Update display of selected packages and locations
function updatePackageSelectionSummary() {
    const isMultiPackage = document.getElementById('isMultiPackage')?.checked || false;
    const packageCount = isMultiPackage ? (parseInt(document.querySelector('[name="packageCount"]')?.value) || 1) : 1;
    
    // Only show summary for multi-packages
    if (!isMultiPackage || packageCount <= 1) return;
    
    // Find or create summary container
    let summaryContainer = document.querySelector('.package-selection-summary');
    if (!summaryContainer) {
        summaryContainer = document.createElement('div');
        summaryContainer.className = 'package-selection-summary mt-4';
        
        const storageSelector = document.querySelector('.storage-selector');
        if (storageSelector) {
            storageSelector.appendChild(summaryContainer);
        }
    }
    
    // Get selected package locations
    if (typeof PackageLocations === 'undefined') return;
    
    const selectedLocations = PackageLocations.getSelectedLocations();
    
    // Update summary
    if (selectedLocations.length === 0) {
        summaryContainer.innerHTML = '';
        summaryContainer.classList.add('d-none');
        return;
    }
    
    summaryContainer.classList.remove('d-none');
    
    // Sort by package number
    const sortedLocations = [...selectedLocations].sort((a, b) => 
        parseInt(a.packageNumber) - parseInt(b.packageNumber));
    
    let html = `
        <div class="card">
            <div class="card-header bg-light">
                <h5 class="mb-0">Selected Package Locations</h5>
            </div>
            <div class="card-body">
                <ul class="list-group list-group-flush">
    `;
    
    sortedLocations.forEach(pkg => {
        html += `
            <li class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <span class="badge bg-primary me-2">Package ${pkg.packageNumber}</span>
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
                    <span>${selectedLocations.length} of ${packageCount} locations selected</span>
                    <button type="button" class="btn btn-sm btn-outline-secondary" id="clearAllLocations">
                        Clear all
                    </button>
                </div>
            </div>
        </div>
    `;
    
    summaryContainer.innerHTML = html;
    
    // Add event listeners to remove buttons
    summaryContainer.querySelectorAll('.remove-location').forEach(button => {
        button.addEventListener('click', function() {
            const packageNumber = this.getAttribute('data-package');
            const locationData = PackageLocations.getLocationByPackage(packageNumber);
            
            if (locationData) {
                // Find and update the corresponding grid cell
                const gridCells = document.querySelectorAll('.storage-cell');
                gridCells.forEach(cell => {
                    const locationText = cell.querySelector('.location')?.textContent;
                    if (locationText === locationData.locationName) {
                        cell.classList.remove('multi-package-selected');
                        cell.classList.add('multi-package-available');
                    }
                });
                
                // Remove from package locations
                PackageLocations.removeLocation(packageNumber);
                
                // Update summary
                updatePackageSelectionSummary();
            }
        });
    });
    
    // Add event listener to "clear all" button
    const clearAllBtn = document.getElementById('clearAllLocations');
    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', function() {
            // Remove all selected locations
            PackageLocations.reset();
            
            // Reset grid cells
            const gridCells = document.querySelectorAll('.storage-cell.multi-package-selected');
            gridCells.forEach(cell => {
                cell.classList.remove('multi-package-selected');
                cell.classList.add('multi-package-available');
            });
            
            // Update summary
            updatePackageSelectionSummary();
        });
    }
}

// Initialize reception date if needed
function initReceptionDate() {
    // Nothing to do here in this implementation
}

// Helper function to map location name to ID
function mapLocationNameToId(locationName) {
    // This is a simple implementation. In a real system, this
    // would probably look up in a table or API
    
    // Format: A{row}.B{column} where row=1-3, column=1-4
    const match = locationName.match(/A(\d+)\.B(\d+)/);
    if (match) {
        const row = parseInt(match[1]);
        const column = parseInt(match[2]);
        
        // Calculate an ID based on row and column
        // Assuming IDs start from 1 and go up to 12
        const id = (row - 1) * 4 + column;
        
        return id.toString();
    }
    
    // Fallback
    return "1";
}

// Handle form submission
function handleFormSubmission() {
    if (!validateCurrentStep()) return;
    
    // Collect all data from form
    const formData = {
        // Reception information
        supplier: document.querySelector('[name="supplier"]')?.value || '',
        trackingNumber: document.querySelector('[name="trackingNumber"]')?.value || '',
        
        // Sample information
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
        
        // Container functionality
        createContainers: document.getElementById('createContainers')?.checked || false,
        containerDescription: document.getElementById('containerDescription')?.value || '',
        containerIsMixed: document.getElementById('containerIsMixed')?.checked || false,
        
        // Identification
        serialNumbers: scannedItems || [],
        
        // Location - now from selected cell instead of dropdown
        storageLocation: document.getElementById('selectedLocationInput')?.value || selectedLocation || ''
    };
    
    // If we have selected location by clicking on a cell, convert locationName to an ID
    if (formData.storageLocation && !formData.storageLocation.match(/^\d+$/)) {
        formData.storageLocation = mapLocationNameToId(formData.storageLocation);
    }
    
    // If PackageLocations module is available, get package data
    if (typeof PackageLocations !== 'undefined') {
        const packageLocationsData = PackageLocations.getData();
        
        // For each selected location name, convert to location ID
        if (packageLocationsData.packageLocations) {
            packageLocationsData.packageLocations = packageLocationsData.packageLocations.map(pkg => {
                if (pkg.locationName && (!pkg.locationId || isNaN(pkg.locationId))) {
                    // Convert locationName to locationId
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
    
    // If ContainerModule is available, get container data
    if (typeof ContainerModule !== 'undefined') {
        // The ContainerModule will add its data to the formData object
        ContainerModule.addToFormData(formData);
    }
    
    console.log("Sending form data:", formData);
    
    // Send data to server
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
            let successMessage = `Sample ${data.sample_id} has been registered successfully!`;
            
            // Add information about containers if relevant
            if (data.container_ids && data.container_ids.length > 0) {
                successMessage += ` ${data.container_ids.length} containers were created.`;
            }
            
            showSuccessMessage(successMessage);
            
            // Reset the form and go back to step 1 after a short pause
            setTimeout(() => {
                resetForm();
                
                // Send the user back to dashboard
                window.location.href = '/dashboard';
            }, 2000);
        } else {
            showErrorMessage(`Error during registration: ${data.error}`);
        }
    })
    .catch(error => {
        showErrorMessage(`An error occurred: ${error}`);
    });
}

// Reset form
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
    
    // Reset package locations
    if (typeof PackageLocations !== 'undefined') {
        PackageLocations.reset();
    }
    
    // Hide multiple package fields
    const multiplePackageFields = document.getElementById('multiplePackageFields');
    if (multiplePackageFields) {
        multiplePackageFields.classList.add('d-none');
    }
    
    // Clear scanned items
    const scannedItemsContainer = document.querySelector('.scanned-items');
    if (scannedItemsContainer) {
        scannedItemsContainer.innerHTML = `
        <div class="empty-scanned-message text-center p-3 text-muted">
            No samples scanned yet. Use the scanner or enter serial numbers manually above.
        </div>`;
    }

    setDefaultExpiryDate();
    showStep(1);
}

// UI Message functions
function showSuccessMessage(message) {
    // Remove existing error messages
    clearValidationErrors();
    
    const successToast = document.createElement('div');
    successToast.className = 'custom-toast success-toast';
    successToast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-check-circle"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">Success</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    document.body.appendChild(successToast);

    // Add 'show' class after a short delay (for animation effect)
    setTimeout(() => successToast.classList.add('show'), 10);

    // Remove automatically after 3 seconds
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
            <div class="toast-title">Error</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    document.body.appendChild(errorToast);

    // Add 'show' class after a short delay (for animation effect)
    setTimeout(() => errorToast.classList.add('show'), 10);

    // Remove automatically after 5 seconds
    setTimeout(() => {
        errorToast.classList.remove('show');
        setTimeout(() => errorToast.remove(), 300);
    }, 5000);
    
    // If a specific field is specified, mark it with an error
    if (field) {
        const fieldElement = document.querySelector(`[name="${field}"]`);
        if (fieldElement) {
            fieldElement.classList.add('field-error');
            
            // Add error message below the field
            const fieldContainer = fieldElement.closest('.form-group');
            if (fieldContainer) {
                // Remove any existing error messages
                const existingError = fieldContainer.querySelector('.field-error-message');
                if (existingError) existingError.remove();
                
                // Add new error message
                const errorMsg = document.createElement('div');
                errorMsg.className = 'field-error-message';
                errorMsg.textContent = message;
                fieldContainer.appendChild(errorMsg);
                
                // Add listeners to remove error marking on input
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
            <div class="toast-title">Warning</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    document.body.appendChild(warningToast);

    // Add 'show' class after a short delay (for animation effect)
    setTimeout(() => warningToast.classList.add('show'), 10);

    // Remove automatically after 4 seconds
    setTimeout(() => {
        warningToast.classList.remove('show');
        setTimeout(() => warningToast.remove(), 300);
    }, 4000);
}

// Helper function to remove all validation errors
function clearValidationErrors() {
    // Remove error classes from all fields
    document.querySelectorAll('.field-error').forEach(field => {
        field.classList.remove('field-error');
    });
    
    // Remove all error messages
    document.querySelectorAll('.field-error-message').forEach(msg => {
        msg.remove();
    });
}