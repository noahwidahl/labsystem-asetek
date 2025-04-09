// Basic variables for multistep
let currentStep = 1;
const totalSteps = 4;
let scannedItems = [];
let selectedLocation = null;
let selectedContainerLocation = null;
let skipLocationSelection = false;
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
    
    // Initialize ContainerModule if available
    if (typeof ContainerModule !== 'undefined') {
        console.log('Initializing ContainerModule');
        ContainerModule.init();
    } else {
        console.log('ContainerModule not available');
    }
    
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

    // Listen for container selection to get its location
    const existingContainerSelect = document.getElementById('existingContainerSelect');
    if (existingContainerSelect) {
        existingContainerSelect.addEventListener('change', function() {
            fetchContainerLocation(this.value);
        });
    }
}

// Funktion til at hente containerplacering
function fetchContainerLocation(containerId) {
    if (!containerId) return;
    
    fetch(`/api/containers/${containerId}/location`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.location) {
                console.log("Container placering:", data.location);
                // Gem containerens placering til senere brug
                selectedContainerLocation = data.location;
                
                // Set skipLocationSelection to true since we'll use container's location
                // This will make the location grid auto-select this location in step 4
                skipLocationSelection = true;
                console.log("Setting skipLocationSelection=true, will use container location:", data.location.LocationName);
            }
        })
        .catch(error => console.error("Fejl ved hentning af containerplacering:", error));
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
    
    // Fetch containers from server with cache-busting query parameter
    // This ensures we get fresh data every time, not cached results
    const timestamp = new Date().getTime();
    fetch(`/api/containers/available?_=${timestamp}`)
        .then(response => response.json())
        .then(data => {
            // Remove "loading..." option
            existingContainerSelect.remove(existingContainerSelect.options.length - 1);
            
            if (data.containers && data.containers.length > 0) {
                data.containers.forEach(container => {
                    const option = document.createElement('option');
                    option.value = container.ContainerID;
                    // Include location information in the dropdown for better identification
                    const locationInfo = container.LocationName ? ` - Location: ${container.LocationName}` : '';
                    
                    // Add capacity information if available
                    let capacityInfo = '';
                    if (container.ContainerCapacity !== null) {
                        const availableCapacity = container.available_capacity !== undefined 
                            ? container.available_capacity 
                            : (container.ContainerCapacity - (container.sample_count || 0));
                        capacityInfo = ` (${container.sample_count || 0} samples, ${availableCapacity}/${container.ContainerCapacity} available)`;
                    } else {
                        capacityInfo = ` (${container.sample_count || 0} samples)`;
                    }
                    
                    option.textContent = `${container.ContainerID}: ${container.Description}${locationInfo}${capacityInfo}`;
                    existingContainerSelect.appendChild(option);
                });
                
                console.log(`Loaded ${data.containers.length} available containers`);
                
                // Enable the dropdown and select the first container by default
                if (data.containers.length > 0) {
                    existingContainerSelect.disabled = false;
                    // If there's a container, select the first one to fetch its location 
                    existingContainerSelect.selectedIndex = 1;
                    
                    // Trigger the change event to load the container's location
                    const event = new Event('change');
                    existingContainerSelect.dispatchEvent(event);
                }
            } else {
                const noContainersOption = document.createElement('option');
                noContainersOption.textContent = 'No available containers found';
                noContainersOption.disabled = true;
                existingContainerSelect.appendChild(noContainersOption);
                
                console.log('No available containers found');
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
            // Check if we need to use container location
            const existingContainerOption = document.getElementById('existingContainerOption');
            const useContainersFeature = document.getElementById('createContainers')?.checked || false;
            
            if (useContainersFeature && existingContainerOption && existingContainerOption.checked && selectedContainerLocation) {
                console.log("Step 4: Will use container location for grid:", selectedContainerLocation.LocationName);
                // Make sure the grid will use the container location
                skipLocationSelection = true;
            }
            
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
        
        // Never skip to location selection step (as requested)
        // Always go to the grid to select a location for better overview
        
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
                showErrorMessage('Please enter a sample name', 'description');
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
            
            // Validate container data if using containers
            const createContainers = document.getElementById('createContainers')?.checked || false;
            if (createContainers) {
                // Use the container module to validate container data
                if (typeof ContainerModule !== 'undefined' && !ContainerModule.validate()) {
                    isValid = false;
                }
            }
            
            return isValid;
        case 3:
            // Validation of identification
            const hasSerialNumbers = document.getElementById('hasSerialNumbers')?.checked;
            if (hasSerialNumbers) {
                const expectedCount = parseInt(document.querySelector('[name="totalAmount"]')?.value) || 0;
                if (scannedItems.length < expectedCount) {
                    showErrorMessage(`${expectedCount - scannedItems.length} flere prøver skal scannes`);
                    return false;
                }
            }
            return true;
        case 4:
            // Check if we're using an existing container's location
            const useContainers = document.getElementById('createContainers')?.checked || false;
            const existingContainerOption = document.getElementById('existingContainerOption');
            const useExistingContainer = useContainers && existingContainerOption && existingContainerOption.checked;
            
            // Skip location validation if we're using existing container with a location
            if (skipLocationSelection || (useExistingContainer && selectedContainerLocation)) {
                console.log("Skipping location validation as using container location:", 
                    selectedContainerLocation ? selectedContainerLocation.LocationName : "Unknown");
                
                // If not already selected in the grid, use the container location
                if (!selectedLocation && selectedContainerLocation) {
                    selectedLocation = selectedContainerLocation.LocationID;
                }
                
                return true;
            }
            
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
        
        // Find stk/pcs option and rename to pcs if it's "stk"
        const pcsOption = Array.from(unitSelect.options).find(opt => 
            opt.textContent.trim().toLowerCase() === 'stk' || 
            opt.textContent.trim().toLowerCase() === 'pcs');
            
        // Rename any "stk" options to "pcs" for consistency across the app
        allOptions.forEach(option => {
            if (option.textContent.trim().toLowerCase() === 'stk') {
                option.textContent = 'pcs';
            }
        });
        
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
                    if (option.value && option.textContent.trim().toLowerCase() !== 'pcs') {
                        unitSelect.appendChild(option.cloneNode(true));
                    }
                });
                
                // Reset value (forces the user to select a unit)
                unitSelect.value = '';
            } else {
                // For pieces: Only pcs is available
                if (pcsOption) {
                    // Make a clone of the pcs option
                    const pcsOptionClone = pcsOption.cloneNode(true);
                    // Ensure it says "pcs" not "stk"
                    pcsOptionClone.textContent = 'pcs';
                    unitSelect.appendChild(pcsOptionClone);
                    unitSelect.value = pcsOption.value;
                } else {
                    // Fallback if we didn't find pcs option
                    const newPcsOption = document.createElement('option');
                    newPcsOption.value = "1"; // Assuming pcs has ID=1
                    newPcsOption.textContent = 'pcs';
                    unitSelect.appendChild(newPcsOption);
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
                totalAmountHelper.textContent = "Totalt antal beregnes automatisk ud fra pakke-information";
                totalAmountInput.readOnly = true;
            } else {
                totalAmountHelper.textContent = "Totalt antal modtagne enheder";
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
                    scannerInput.placeholder = "Scanning deaktiveret";
                }
            } else {
                // Activate scanning
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
                    showErrorMessage(`Kan ikke tilføje ${barcodes.length} stregkoder. Maksimalt antal er ${totalExpected} (${currentCount} allerede scannet)`);
                    return;
                }
                
                barcodes.forEach(barcode => {
                    processScan(barcode);
                });
                
                bulkBarcodes.value = '';
                showSuccessMessage(`${barcodes.length} stregkoder tilføjet succesfuldt`);
                
                // Hide bulk entry after addition
                bulkEntrySection.classList.add('d-none');
            }
        });
    }
    
    // Clear all scanned items
    if (clearAllScannedBtn) {
        clearAllScannedBtn.addEventListener('click', function() {
            if (confirm('Er du sikker på, at du vil fjerne alle scannede prøver?')) {
                scannedItems = [];
                updateScanUI();
                showSuccessMessage('Alle scannede prøver er blevet fjernet');
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
        showWarningMessage(`Stregkode "${barcode}" er allerede scannet`);
        return;
    }

    if (scannedItems.length < totalExpected) {
        scannedItems.push(barcode);
        updateScanUI();
        // Play a sound to indicate successful scanning
        playSuccessSound();
    } else {
        showErrorMessage('Maksimalt antal prøver nået');
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
                Ingen prøver scannet endnu. Brug scanneren eller indtast serienumre manuelt ovenfor.
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

function createGridFromLocations(locations, preSelectedLocationId = null) {
    console.log("createGridFromLocations with", locations.length, "locations", preSelectedLocationId ? `and pre-selected location ${preSelectedLocationId}` : "");
    
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '';
    
    // Organize locations by rack, section, shelf
    const organizedLocations = organizeLocationsByStructure(locations);
    
    // Keep track of the cell for pre-selected location
    let preSelectedCell = null;
    
    // Add fixed button bar at the bottom for navigation
    let buttonBar = document.querySelector('.fixed-button-bar');
    if (!buttonBar) {
        buttonBar = document.createElement('div');
        buttonBar.className = 'fixed-button-bar position-sticky bottom-0 bg-white border-top py-3 px-4 d-flex justify-content-between';
        buttonBar.style.zIndex = '1000';
        buttonBar.style.marginTop = 'auto';
        buttonBar.innerHTML = `
            <button type="button" class="btn btn-secondary" id="fixedPrevButton">
                <i class="fas fa-arrow-left me-2"></i>Back
            </button>
            <button type="button" class="btn btn-primary" id="fixedNextButton">
                Next<i class="fas fa-arrow-right ms-2"></i>
            </button>
        `;
        
        // Find the parent to attach the button bar to
        const storageSelector = document.querySelector('.storage-selector');
        if (storageSelector) {
            storageSelector.style.paddingBottom = '70px'; // Make room for the fixed bar
            storageSelector.appendChild(buttonBar);
            
            // Add event listeners to buttons
            buttonBar.querySelector('#fixedPrevButton').addEventListener('click', function() {
                const prevButton = document.getElementById('prevButton');
                if (prevButton) prevButton.click();
            });
            
            buttonBar.querySelector('#fixedNextButton').addEventListener('click', function() {
                const nextButton = document.getElementById('nextButton');
                if (nextButton) nextButton.click();
            });
        }
    }
    
    // Create rack sections
    Object.keys(organizedLocations).sort((a, b) => parseInt(a) - parseInt(b)).forEach(reolNum => {
        const reolSection = document.createElement('div');
        reolSection.className = 'reol-section mb-4';
        
        // Determine if this rack should be expanded
        const isSelectedRack = (window.selectedRackNum === reolNum) || (preSelectedLocationId && preSelectedLocationId.toString().startsWith(reolNum));
        
        const reolHeader = document.createElement('div');
        reolHeader.className = 'mb-2 d-flex justify-content-between align-items-center bg-light p-2 rounded';
        
        // Create clickable header with toggle functionality
        const titleSpan = document.createElement('h5');
        titleSpan.textContent = `Rack ${reolNum}`;
        titleSpan.className = 'mb-0';
        titleSpan.style.cursor = 'pointer';
        
        // Add rack header elements
        reolHeader.appendChild(titleSpan);
        reolSection.appendChild(reolHeader);
        
        // Create container for sections
        const sektionsContainer = document.createElement('div');
        sektionsContainer.className = 'd-flex flex-wrap';
        sektionsContainer.style.display = isSelectedRack ? 'flex' : 'none';
        
        // Add toggle functionality to header
        reolHeader.addEventListener('click', () => {
            if (sektionsContainer.style.display === 'none') {
                // Collapse all other racks first
                if (!event.ctrlKey) { // Unless ctrl key is pressed (for multiple expanding)
                    const allSektionsContainers = document.querySelectorAll('.reol-section .d-flex.flex-wrap');
                    
                    allSektionsContainers.forEach(container => {
                        if (container !== sektionsContainer) {
                            container.style.display = 'none';
                        }
                    });
                }
                
                // Now expand this rack
                sektionsContainer.style.display = 'flex';
                reolHeader.classList.add('bg-primary', 'text-white');
            } else {
                sektionsContainer.style.display = 'none';
                reolHeader.classList.remove('bg-primary', 'text-white');
            }
        });
        
        // For each section in the rack
        Object.keys(organizedLocations[reolNum]).sort((a, b) => parseInt(a) - parseInt(b)).forEach(sektionNum => {
            const sektionDiv = document.createElement('div');
            sektionDiv.className = 'sektion-container me-3 mb-3';
            
            const sektionHeader = document.createElement('div');
            sektionHeader.textContent = `Section ${sektionNum}`;
            sektionHeader.className = 'sektion-header small text-muted mb-1';
            sektionDiv.appendChild(sektionHeader);
            
            const hyldeContainer = document.createElement('div');
            hyldeContainer.className = 'd-flex flex-column';
            
            // For each shelf in the section
            Object.keys(organizedLocations[reolNum][sektionNum]).sort((a, b) => parseInt(a) - parseInt(b)).forEach(hyldeNum => {
                const location = organizedLocations[reolNum][sektionNum][hyldeNum];
                const locationName = `${reolNum}.${sektionNum}.${hyldeNum}`;
                
                // Create shelf cell
                const cell = document.createElement('div');
                cell.className = 'storage-cell mb-1';
                cell.dataset.locationId = location.LocationID;
                cell.dataset.locationName = locationName;
                
                // Show number of samples on the shelf instead of "occupied"
                const count = location.count || 0;
                
                const locationEl = document.createElement('div');
                locationEl.className = 'location fw-bold';
                locationEl.textContent = locationName;
                
                const capacity = document.createElement('div');
                capacity.className = 'capacity small';
                capacity.textContent = count > 0 ? `${count} sample(s)` : 'Available';
                
                cell.appendChild(locationEl);
                cell.appendChild(capacity);
                hyldeContainer.appendChild(cell);
                
                // Add click event to the cell - always clickable regardless of content
                cell.addEventListener('click', () => selectStorageCell(cell));
                
                // If this is the pre-selected location, save the cell reference
                if (preSelectedLocationId && location.LocationID == preSelectedLocationId) {
                    preSelectedCell = cell;
                }
            });
            
            sektionDiv.appendChild(hyldeContainer);
            sektionsContainer.appendChild(sektionDiv);
        });
        
        reolSection.appendChild(sektionsContainer);
        grid.appendChild(reolSection);
    });
    
    // After the grid is created, auto-select the pre-selected location if any
    if (preSelectedCell) {
        console.log("Auto-selecting pre-selected location");
        
        // Scroll to make the location visible (with some delay to ensure DOM is ready)
        setTimeout(() => {
            preSelectedCell.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Select the cell
            selectStorageCell(preSelectedCell);
            
            // Add a highlight animation
            preSelectedCell.classList.add('highlight-animation');
            setTimeout(() => {
                preSelectedCell.classList.remove('highlight-animation');
            }, 1500);
            
            // If using container location, show a message
            if (selectedContainerLocation) {
                showSuccessMessage(`Using container location: ${selectedContainerLocation.LocationName}`);
            }
        }, 200);
    } 
    // If we have container location but couldn't find the cell, still store the ID
    else if (selectedContainerLocation && selectedContainerLocation.LocationID) {
        console.log("Container location exists but cell not found in grid. Using location ID:", selectedContainerLocation.LocationID);
        selectedLocation = selectedContainerLocation.LocationID;
        
        // Show a location indicator even without a cell
        let locationIndicator = document.querySelector('.selected-location-indicator');
        if (!locationIndicator) {
            locationIndicator = document.createElement('div');
            locationIndicator.className = 'selected-location-indicator mt-3 p-2 bg-light rounded';
            document.querySelector('.storage-selector').appendChild(locationIndicator);
        }
        
        locationIndicator.innerHTML = `<strong>Selected location:</strong> ${selectedContainerLocation.LocationName} <span class="badge bg-info">Container Location</span>`;
        
        // Create hidden input
        let locationInput = document.getElementById('selectedLocationInput');
        if (!locationInput) {
            locationInput = document.createElement('input');
            locationInput.type = 'hidden';
            locationInput.name = 'storageLocation';
            locationInput.id = 'selectedLocationInput';
            document.querySelector('.storage-selector').appendChild(locationInput);
        }
        
        locationInput.value = selectedContainerLocation.LocationID;
    }
}

// Organize locations by structure
function organizeLocationsByStructure(locations) {
    const organized = {};
    let selectedRackNum = null;
    
    locations.forEach(location => {
        let reolNum, sektionNum, hyldeNum;
        
        // If we have Rack, Section, Shelf columns directly
        if (location.Rack !== undefined && location.Section !== undefined && location.Shelf !== undefined) {
            reolNum = location.Rack;
            sektionNum = location.Section;
            hyldeNum = location.Shelf;
        } else {
            // Parse LocationName (assumes format rack.section.shelf)
            const parts = location.LocationName.split('.');
            if (parts.length === 3) {
                [reolNum, sektionNum, hyldeNum] = parts;
            } else if (parts.length === 2) {
                // Handle older A1.B1 format
                reolNum = location.LocationName.substring(1, 2);
                sektionNum = "1";
                hyldeNum = location.LocationName.substring(4);
            } else {
                console.log("Unknown format:", location.LocationName);
                return; // Skip if format not recognized
            }
        }
        
        // Create necessary objects if they don't exist
        if (!organized[reolNum]) organized[reolNum] = {};
        if (!organized[reolNum][sektionNum]) organized[reolNum][sektionNum] = {};
        
        // Store location in organizational structure
        organized[reolNum][sektionNum][hyldeNum] = location;
        
        // Check if this is the selected location
        if (selectedContainerLocation && selectedContainerLocation.LocationID == location.LocationID) {
            selectedRackNum = reolNum;
        }
    });
    
    // Store the selected rack number for later use
    if (selectedRackNum) {
        window.selectedRackNum = selectedRackNum;
    }
    
    return organized;
    
    return organized;
}

function setupStorageGrid() {
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '<div class="text-center p-3"><div class="spinner-border"></div><p>Loading storage locations...</p></div>';

    // Check if there's a pre-selected location from container details
    const containerLocationSelect = document.getElementById('containerLocation');
    let selectedLocationId = null;
    
    // Reset the saved rack number
    window.selectedRackNum = null;
    window.allRacksCollapsed = true;
    
    // First check if we have a selected container location from existing container
    if (selectedContainerLocation && selectedContainerLocation.LocationID) {
        selectedLocationId = selectedContainerLocation.LocationID;
        
        // Parse the location name to get the rack number
        if (selectedContainerLocation.LocationName) {
            const parts = selectedContainerLocation.LocationName.split('.');
            if (parts.length >= 1) {
                window.selectedRackNum = parts[0];
            }
        }
        
        console.log("Using location from existing container:", selectedLocationId, selectedContainerLocation.LocationName, "Rack:", window.selectedRackNum);
    }
    // Otherwise use the selected container location from the new container form
    else if (containerLocationSelect && containerLocationSelect.value) {
        selectedLocationId = containerLocationSelect.value;
        
        // Try to extract rack number
        if (containerLocationSelect.selectedOptions && containerLocationSelect.selectedOptions[0]) {
            const locationText = containerLocationSelect.selectedOptions[0].textContent;
            const match = locationText.match(/(\d+)\.(\d+)\.(\d+)/);
            if (match) {
                window.selectedRackNum = match[1];
            }
        }
        
        console.log("Using pre-selected location from container form:", selectedLocationId, "Rack:", window.selectedRackNum);
    }

    // Fetch storage locations from API
    fetch('/api/storage-locations')
        .then(response => response.json())
        .then(data => {
            console.log("Received storage location data:", data);
            if (data.locations) {
                createGridFromLocations(data.locations, selectedLocationId);
            } else {
                console.error("No locations in response");
                // Fallback to rack.section.shelf format
                createDefaultStorageGrid(selectedLocationId);
            }
        })
        .catch(error => {
            console.error('Error fetching storage locations:', error);
            // Fallback to rack.section.shelf format
            createDefaultStorageGrid(selectedLocationId);
        });
}

// We maintain our grid creation function with updated format
function createDefaultStorageGrid(preSelectedLocationId = null) {
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '';
    
    // Keep track of the cell for pre-selected location
    let preSelectedCell = null;
    
    // Create default storage grid with rack.section.shelf format
    for (let rack = 1; rack <= 3; rack++) {
        const reolSection = document.createElement('div');
        reolSection.className = 'reol-section mb-4';
        
        const reolHeader = document.createElement('h5');
        reolHeader.textContent = `Rack ${rack}`;
        reolHeader.className = 'mb-2';
        reolSection.appendChild(reolHeader);
        
        const sektionsContainer = document.createElement('div');
        sektionsContainer.className = 'd-flex flex-wrap';
        
        for (let section = 1; section <= 2; section++) {
            const sektionDiv = document.createElement('div');
            sektionDiv.className = 'sektion-container me-3 mb-3';
            
            const sektionHeader = document.createElement('div');
            sektionHeader.textContent = `Section ${section}`;
            sektionHeader.className = 'sektion-header small text-muted mb-1';
            sektionDiv.appendChild(sektionHeader);
            
            const hyldeContainer = document.createElement('div');
            hyldeContainer.className = 'd-flex flex-column';
            
            for (let shelf = 1; shelf <= 5; shelf++) {
                const cell = document.createElement('div');
                cell.className = 'storage-cell mb-1';
                
                const locationName = `${rack}.${section}.${shelf}`;
                cell.dataset.locationName = locationName;
                
                // Generate a simulated ID matching format in DB (LocationID)
                const simulatedId = `${rack}${section}${shelf}`;
                cell.dataset.locationId = simulatedId;
                
                const locationEl = document.createElement('div');
                locationEl.className = 'location fw-bold';
                locationEl.textContent = locationName;
                
                const capacity = document.createElement('div');
                capacity.className = 'capacity small';
                capacity.textContent = 'Available';
                
                cell.appendChild(locationEl);
                cell.appendChild(capacity);
                hyldeContainer.appendChild(cell);
                
                // Add click event to the cell
                cell.addEventListener('click', () => selectStorageCell(cell));
                
                // If this is the pre-selected location, save the cell reference
                if (preSelectedLocationId && simulatedId == preSelectedLocationId) {
                    preSelectedCell = cell;
                }
            }
            
            sektionDiv.appendChild(hyldeContainer);
            sektionsContainer.appendChild(sektionDiv);
        }
        
        reolSection.appendChild(sektionsContainer);
        grid.appendChild(reolSection);
    }
    
    // After the grid is created, auto-select the pre-selected location if any
    if (preSelectedCell) {
        console.log("Auto-selecting pre-selected location in default grid");
        
        // Scroll to make the location visible (with some delay to ensure DOM is ready)
        setTimeout(() => {
            preSelectedCell.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Select the cell
            selectStorageCell(preSelectedCell);
            
            // Add a highlight animation
            preSelectedCell.classList.add('highlight-animation');
            setTimeout(() => {
                preSelectedCell.classList.remove('highlight-animation');
            }, 1500);
        }, 200);
    }
}

// Updated selectStorageCell function - with direct saving of location without dropdown
function selectStorageCell(cell) {
    // All cells are clickable, regardless of how many samples are on a shelf
    
    // Remove marking from all cells
    document.querySelectorAll('.storage-cell').forEach(c => c.classList.remove('selected'));
    
    // Mark the selected cell
    cell.classList.add('selected');
    
    // Get location ID and name
    const locationId = cell.dataset.locationId;
    const locationName = cell.dataset.locationName;
    
    // Save the location for form submission
    selectedLocation = locationId;
    
    // Display selected location
    let locationIndicator = document.querySelector('.selected-location-indicator');
    if (!locationIndicator) {
        locationIndicator = document.createElement('div');
        locationIndicator.className = 'selected-location-indicator mt-3 p-2 bg-light rounded';
        document.querySelector('.storage-selector').appendChild(locationIndicator);
    }
    
    locationIndicator.innerHTML = `<strong>Selected location:</strong> ${locationName}`;
    
    // Update hidden input fields
    let locationInput = document.getElementById('selectedLocationInput');
    if (!locationInput) {
        locationInput = document.createElement('input');
        locationInput.type = 'hidden';
        locationInput.name = 'storageLocation';
        locationInput.id = 'selectedLocationInput';
        document.querySelector('.storage-selector').appendChild(locationInput);
    }
    
    locationInput.value = locationId;
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
                const locationId = cell.dataset.locationId;
                PackageLocations.addLocation(selectedCellsCount + 1, locationId, locationText);
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
        
        // Identification
        serialNumbers: scannedItems || [],
    };
    
    // Container functionality
    const containersFeatureCheckbox = document.getElementById('createContainers');
    if (containersFeatureCheckbox && containersFeatureCheckbox.checked) {
        formData.createContainers = true;
        
        // Check if we're using existing container or creating new
        const existingContainerOption = document.getElementById('existingContainerOption');
        if (existingContainerOption && existingContainerOption.checked) {
            // Use existing container
            const containerId = document.getElementById('existingContainerSelect')?.value;
            if (containerId) {
                formData.useExistingContainer = true;
                formData.existingContainerId = containerId;
                
                // If we have container location, use it
                if (selectedContainerLocation) {
                    formData.storageLocation = selectedContainerLocation.LocationID;
                    console.log("Using existing container location:", selectedContainerLocation.LocationName);
                }
            }
        } else {
            // Create new container
            formData.containerDescription = document.getElementById('containerDescription')?.value || '';
            formData.containerIsMixed = document.getElementById('containerIsMixed')?.checked || false;
            
            // Check if we're creating a new container type
            const createContainerType = document.getElementById('createContainerType')?.checked || false;
            console.log("Creating container type?", createContainerType);
            
            if (createContainerType) {
                // Creating a new container type
                formData.newContainerType = {
                    typeName: document.getElementById('newContainerTypeName')?.value || '',
                    description: document.getElementById('newContainerTypeDescription')?.value || '',
                    capacity: document.getElementById('newContainerTypeCapacity')?.value || ''
                };
                console.log("Creating new container type:", formData.newContainerType);
            } else {
                // Using existing container type
                formData.containerTypeId = document.getElementById('containerType')?.value || '';
                formData.containerCapacity = document.getElementById('containerCapacity')?.value || '';
            }
            
            // Save container location separately from sample location
            const containerLocationSelect = document.getElementById('containerLocation');
            if (containerLocationSelect && containerLocationSelect.value) {
                formData.containerLocationId = containerLocationSelect.value;
                console.log("Container location set to:", containerLocationSelect.value);
            }
            
            // Always use the standard selected location from the grid for the sample
            formData.storageLocation = document.getElementById('selectedLocationInput')?.value || selectedLocation || '';
        }
    } else {
        // Standard location without container
        formData.storageLocation = document.getElementById('selectedLocationInput')?.value || selectedLocation || '';
    }
    
    // If PackageLocations module is available, get package data
    if (typeof PackageLocations !== 'undefined') {
        const packageLocationsData = PackageLocations.getData();
        Object.assign(formData, packageLocationsData);
    }
    
    // If ContainerModule is available, get container data
    if (typeof ContainerModule !== 'undefined') {
        // ContainerModule will add its data to the formData object
        const containerData = ContainerModule.addToFormData(formData);
        
        // Check if we need to handle new container type separately
        if (document.getElementById('createContainerType')?.checked) {
            // Make sure newContainerType is transferred from ContainerModule data
            if (!formData.newContainerType && containerData.newContainerType) {
                formData.newContainerType = containerData.newContainerType;
                console.log("Using container type from ContainerModule:", formData.newContainerType);
            }
        }
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
                
                // Redirect user back to dashboard
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