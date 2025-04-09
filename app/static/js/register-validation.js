/**
 * Register Validation - Form validation functions for the registration form
 */

// Initialize when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Validation module loading...');
    
    // Mark this module as loaded in the global state
    if (window.registerApp) {
        window.registerApp.modulesLoaded.validation = true;
        console.log('Validation module loaded');
    } else {
        console.error('registerApp not found - validation module cannot register');
    }
});

// Check if PackageLocations module is available
function checkPackageLocations() {
    if (typeof window.PackageLocations === 'undefined') {
        // Create a simple implementation if missing
        window.PackageLocations = {
            _locations: [],
            
            addLocation: function(packageNumber, locationId, locationName) {
                this._locations.push({packageNumber, locationId, locationName});
            },
            
            removeLocation: function(packageNumber) {
                this._locations = this._locations.filter(loc => loc.packageNumber != packageNumber);
            },
            
            removeLocationByName: function(locationName) {
                this._locations = this._locations.filter(loc => loc.locationName !== locationName);
            },
            
            getSelectedLocations: function() {
                return this._locations;
            },
            
            getLocationByPackage: function(packageNumber) {
                return this._locations.find(loc => loc.packageNumber == packageNumber);
            },
            
            reset: function() {
                this._locations = [];
            }
        };
        
        console.warn("Created fallback PackageLocations module");
    }
}

// Function to validate the current step
// Make it globally accessible with proper exporting
function validateCurrentStep() {
    console.log('Validation function called for step:', registerApp.currentStep);
    
    // Export to window object on first call
    if (!window.validateCurrentStep) {
        window.validateCurrentStep = validateCurrentStep;
    }
    
    // Ensure PackageLocations is available
    checkPackageLocations();
    
    clearValidationErrors();
    
    switch(registerApp.currentStep) {
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
            
            // Minimal container validation
            const storageOption = document.querySelector('input[name="storageOption"]:checked')?.value || 'direct';
            
            if (storageOption === 'container') {
                // Check if existing container option is selected
                const existingContainerOption = document.getElementById('existingContainerOption');
                
                // Only validate existing container selection
                if (existingContainerOption && existingContainerOption.checked) {
                    const existingContainerSelect = document.getElementById('existingContainerSelect');
                    if (!existingContainerSelect || !existingContainerSelect.value) {
                        showErrorMessage('Please select an existing container', 'existingContainerSelect');
                        isValid = false;
                    }
                }
            }
            
            return isValid;
        case 3:
            // Validation of identification
            const hasSerialNumbers = document.getElementById('hasSerialNumbers')?.checked;
            if (hasSerialNumbers) {
                const expectedCount = parseInt(document.querySelector('[name="totalAmount"]')?.value) || 0;
                if (registerApp.scannedItems.length < expectedCount) {
                    showErrorMessage(`${expectedCount - registerApp.scannedItems.length} more samples need to be scanned`);
                    return false;
                }
            }
            return true;
        case 4:
            // Get sample type and storage options
            const sampleType = document.querySelector('input[name="sampleTypeOption"]:checked')?.value || 'single';
            const storageOption = document.querySelector('input[name="storageOption"]:checked')?.value || 'direct';
            const separateStorage = document.getElementById('separateStorage')?.checked || false;
            const useExistingContainer = storageOption === 'container' && document.getElementById('existingContainerOption')?.checked;
            
            // Skip location validation if we're using existing container with a location
            if (registerApp.skipLocationSelection || (useExistingContainer && registerApp.selectedContainerLocation)) {
                console.log("Skipping location validation as using container location:", 
                    registerApp.selectedContainerLocation ? registerApp.selectedContainerLocation.LocationName : "Unknown");
                
                // If not already selected in the grid, use the container location
                if (!registerApp.selectedLocation && registerApp.selectedContainerLocation) {
                    registerApp.selectedLocation = registerApp.selectedContainerLocation.LocationID;
                }
                
                return true;
            }
            
            // For multiple samples with separate storage
            if (sampleType === 'multiple' && separateStorage) {
                const packageCount = parseInt(document.querySelector('[name="packageCount"]')?.value) || 1;
                
                // Ensure PackageLocations is available
                checkPackageLocations();
                
                const selectedLocations = PackageLocations.getSelectedLocations();
                if (selectedLocations.length < packageCount) {
                    showErrorMessage(`You need to select ${packageCount} locations. You have selected ${selectedLocations.length}.`);
                    return false;
                }
                return true;
            }
            // For multiple samples with container storage - one container per package
            else if (sampleType === 'multiple' && storageOption === 'container') {
                const oneContainerPerPackage = document.getElementById('oneContainerPerPackage')?.checked || false;
                if (oneContainerPerPackage) {
                    const packageCount = parseInt(document.querySelector('[name="packageCount"]')?.value) || 1;
                    
                    // Ensure PackageLocations is available
                    checkPackageLocations();
                    
                    const selectedLocations = PackageLocations.getSelectedLocations();
                    if (selectedLocations.length < packageCount) {
                        showErrorMessage(`You need to select ${packageCount} locations for containers. You have selected ${selectedLocations.length}.`);
                        return false;
                    }
                    return true;
                }
                // For one container for all - need just one location
                else {
                    if (!registerApp.selectedLocation) {
                        showErrorMessage('Please select a location by clicking on an available space in the grid.');
                        return false;
                    }
                    return true;
                }
            }
            // Standard single location validation
            else {
                if (!registerApp.selectedLocation) {
                    showErrorMessage('Please select a location by clicking on an available space in the grid.');
                    return false;
                }
                return true;
            }
        default:
            return true;
    }
}

// Update the registration summary - make it globally accessible
// Export directly to window object to ensure it's available
function updateRegistrationSummary() {
    console.log('Registration summary update called');
    
    // Initial definition for immediate reference
    if (!window.updateRegistrationSummary) {
        window.updateRegistrationSummary = updateRegistrationSummary;
    }
    const summaryContent = document.getElementById('summaryContent');
    if (!summaryContent) return;
    
    // Get form data
    const sampleType = document.querySelector('input[name="sampleTypeOption"]:checked')?.value || 'single';
    const storageOption = document.querySelector('input[name="storageOption"]:checked')?.value || 'direct';
    const description = document.querySelector('[name="description"]')?.value || 'Unnamed sample';
    const totalAmount = document.querySelector('[name="totalAmount"]')?.value || '0';
    const unitText = document.querySelector('[name="unit"] option:checked')?.textContent || '';
    
    let summaryHtml = `
        <div class="summary-item mb-3">
            <div class="summary-title">Sample Information</div>
            <div class="summary-content">
                <p><strong>${description}</strong> - ${totalAmount} ${unitText}</p>
                <p>Type: ${getSampleTypeText(sampleType)}</p>
            </div>
        </div>
    `;
    
    // Add multiple sample info if applicable
    if (sampleType === 'multiple') {
        const packageCount = document.querySelector('[name="packageCount"]')?.value || '1';
        const amountPerPackage = document.querySelector('[name="amountPerPackage"]')?.value || '0';
        const separateStorage = document.getElementById('separateStorage')?.checked;
        
        summaryHtml += `
            <div class="summary-item mb-3">
                <div class="summary-title">Multiple Sample Details</div>
                <div class="summary-content">
                    <p>${packageCount} packages with ${amountPerPackage} samples per package</p>
                    <p>Storage: ${separateStorage ? 'Separate location for each package' : 'Same location for all packages'}</p>
                </div>
            </div>
        `;
    }
    
    // Add storage info
    summaryHtml += `
        <div class="summary-item mb-3">
            <div class="summary-title">Storage Details</div>
            <div class="summary-content">
                <p>Storage Type: ${storageOption === 'direct' ? 'Direct storage on shelf' : 'Storage in container'}</p>
    `;
    
    // Add container details if applicable
    if (storageOption === 'container') {
        if (document.getElementById('existingContainerOption')?.checked) {
            const containerSelect = document.getElementById('existingContainerSelect');
            const containerText = containerSelect?.options[containerSelect.selectedIndex]?.textContent || 'Unknown container';
            
            summaryHtml += `<p>Using existing container: ${containerText}</p>`;
        } else if (sampleType === 'multiple' && document.getElementById('oneContainerPerPackage')?.checked) {
            summaryHtml += `<p>Creating one container for each package</p>`;
        } else {
            const containerDescription = document.getElementById('containerDescription')?.value || 'New container';
            const containerTypeSelect = document.getElementById('containerType');
            const containerTypeText = containerTypeSelect?.options[containerTypeSelect.selectedIndex]?.textContent || 'Custom type';
            
            summaryHtml += `<p>Creating new container: ${containerDescription} (${containerTypeText})</p>`;
        }
    }
    
    // Add location info
    const locationName = getSelectedLocationName();
    if (locationName) {
        summaryHtml += `<p>Location: ${locationName}</p>`;
    } else if (sampleType === 'multiple' && (document.getElementById('separateStorage')?.checked || 
               (storageOption === 'container' && document.getElementById('oneContainerPerPackage')?.checked))) {
        const locationCount = PackageLocations?.getSelectedLocations().length || 0;
        summaryHtml += `<p>Multiple locations selected: ${locationCount}</p>`;
    }
    
    summaryHtml += `
            </div>
        </div>
    `;
    
    // Add serial number info if applicable
    if (document.getElementById('hasSerialNumbers')?.checked) {
        summaryHtml += `
            <div class="summary-item">
                <div class="summary-title">Identification</div>
                <div class="summary-content">
                    <p>${registerApp.scannedItems.length} serial numbers recorded</p>
                </div>
            </div>
        `;
    }
    
    summaryContent.innerHTML = summaryHtml;
    
    // Helper function to get readable sample type text
    function getSampleTypeText(type) {
        switch (type) {
            case 'single': return 'Single Sample';
            case 'multiple': return 'Multiple Identical Samples';
            case 'bulk': return 'Bulk Material';
            default: return 'Unknown';
        }
    }
    
    // Helper function to get selected location name
    function getSelectedLocationName() {
        if (storageOption === 'container' && document.getElementById('existingContainerOption')?.checked && registerApp.selectedContainerLocation) {
            return registerApp.selectedContainerLocation.LocationName || 'Container location';
        }
        
        const locationCell = document.querySelector('.storage-cell.selected');
        if (locationCell) {
            return locationCell.dataset.locationName || 'Selected location';
        }
        
        return '';
    }
}

// Handle form submission - make it globally accessible
// Export directly to window object to ensure it's available
function handleFormSubmission() {
    console.log('Form submission handler called');
    
    // Initial definition for immediate reference
    if (!window.handleFormSubmission) {
        window.handleFormSubmission = handleFormSubmission;
    }

    // Extra validation for location step
    if (registerApp.currentStep === 4) {
        const sampleType = document.querySelector('input[name="sampleTypeOption"]:checked')?.value || 'single';
        const storageOption = document.querySelector('input[name="storageOption"]:checked')?.value || 'direct';
        const separateStorage = document.getElementById('separateStorage')?.checked || false;
        
        if (sampleType === 'multiple' && separateStorage) {
            // Multiple samples with separate storage - check if we have enough locations
            const packageCount = parseInt(document.querySelector('[name="packageCount"]')?.value) || 1;
            
            // Ensure PackageLocations is available
            checkPackageLocations();
            
            const selectedLocations = PackageLocations.getSelectedLocations();
            if (selectedLocations.length < packageCount) {
                showErrorMessage(`You need to select ${packageCount} locations. You have selected ${selectedLocations.length}.`);
                return false;
            }
        } else if (!registerApp.selectedLocation && !registerApp.skipLocationSelection) {
            // Standard location check if not using container location
            showErrorMessage('Please select a location by clicking on an available space in the grid.');
            return false;
        }
    }
    
    // Regular validation
    if (!validateCurrentStep()) return;
    
    // Show the registration summary before submitting
    const registrationSummary = document.getElementById('registrationSummary');
    if (registrationSummary) {
        registrationSummary.classList.remove('d-none');
        updateRegistrationSummary();
    }
    
    // Collect all data from form
    const formData = {
        // Reception information
        supplier: document.querySelector('[name="supplier"]')?.value || '',
        trackingNumber: document.querySelector('[name="trackingNumber"]')?.value || '',
        custodian: document.querySelector('input[name="custodian"]')?.value || '',
        
        // Sample information
        partNumber: document.querySelector('[name="partNumber"]')?.value || '',
        description: document.querySelector('[name="description"]')?.value || '',
        
        // Sample type
        sampleType: document.querySelector('input[name="sampleTypeOption"]:checked')?.value || 'single',
        
        // Amount information
        totalAmount: parseInt(document.querySelector('[name="totalAmount"]')?.value) || 0,
        unit: document.querySelector('[name="unit"]')?.value || '',
        
        // Storage type
        storageOption: document.querySelector('input[name="storageOption"]:checked')?.value || 'direct',
        
        // Additional fields
        owner: document.querySelector('[name="owner"]')?.value || '',
        expiryDate: document.querySelector('[name="expiryDate"]')?.value || '',
        hasSerialNumbers: document.getElementById('hasSerialNumbers')?.checked || false,
        other: document.querySelector('[name="other"]')?.value || '',
        
        // Identification
        serialNumbers: registerApp.scannedItems || [],
    };
    
    // Add multiple sample specific data
    if (formData.sampleType === 'multiple') {
        formData.packageCount = parseInt(document.querySelector('[name="packageCount"]')?.value) || 1;
        formData.amountPerPackage = parseInt(document.querySelector('[name="amountPerPackage"]')?.value) || 0;
        formData.separateStorage = document.getElementById('separateStorage')?.checked || false;
    }
    
    // Add bulk sample specific data
    if (formData.sampleType === 'bulk') {
        formData.isBulkSample = true;
    }
    
    // Container functionality
    if (formData.storageOption === 'container') {
        formData.useContainers = true;
        
        // For single sample or bulk material
        if (formData.sampleType !== 'multiple') {
            // Check if using existing or creating new container
            const existingContainerOption = document.getElementById('existingContainerOption');
            
            // Option 1: Use existing container
            if (existingContainerOption && existingContainerOption.checked) {
                const containerId = document.getElementById('existingContainerSelect')?.value;
                if (containerId) {
                    formData.useExistingContainer = true;
                    formData.existingContainerId = containerId;
                    
                    // If we have container location, use it
                    if (registerApp.selectedContainerLocation) {
                        formData.storageLocation = registerApp.selectedContainerLocation.LocationID;
                        console.log("Using existing container location:", registerApp.selectedContainerLocation.LocationName);
                    }
                }
            }
            // Option 2: Create new container
            else {
                // Create new container
                formData.createNewContainer = true;
                formData.containerDescription = document.getElementById('containerDescription')?.value || '';
                formData.containerIsMixed = document.getElementById('containerIsMixed')?.checked || false;
                
                // Check if we're creating a new container type
                const createContainerType = document.getElementById('createContainerType')?.checked || false;
                
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
                
                // Save container location separately
                const containerLocationSelect = document.getElementById('containerLocation');
                if (containerLocationSelect && containerLocationSelect.value) {
                    formData.containerLocationId = containerLocationSelect.value;
                    console.log("Container location set to:", containerLocationSelect.value);
                }
            }
        }
        // For multiple samples
        else {
            const oneContainerForAll = document.getElementById('oneContainerForAll');
            const oneContainerPerPackage = document.getElementById('oneContainerPerPackage');
            
            // Option 1: One container for all samples
            if (oneContainerForAll && oneContainerForAll.checked) {
                formData.createSingleContainer = true;
                formData.containerDescription = document.getElementById('containerDescription')?.value || '';
                formData.containerIsMixed = document.getElementById('containerIsMixed')?.checked || false;
                
                // Check if we're creating a new container type
                const createContainerType = document.getElementById('createContainerType')?.checked || false;
                
                if (createContainerType) {
                    // Creating a new container type
                    formData.newContainerType = {
                        typeName: document.getElementById('newContainerTypeName')?.value || '',
                        description: document.getElementById('newContainerTypeDescription')?.value || '',
                        capacity: document.getElementById('newContainerTypeCapacity')?.value || ''
                    };
                } else {
                    // Using existing container type
                    formData.containerTypeId = document.getElementById('containerType')?.value || '';
                    formData.containerCapacity = document.getElementById('containerCapacity')?.value || '';
                }
                
                // Save container location
                const containerLocationSelect = document.getElementById('containerLocation');
                if (containerLocationSelect && containerLocationSelect.value) {
                    formData.containerLocationId = containerLocationSelect.value;
                }
            }
            // Option 2: One container per package
            else if (oneContainerPerPackage && oneContainerPerPackage.checked) {
                formData.createMultipleContainers = true;
                formData.containerDescription = document.getElementById('containerDescription')?.value || '';
                formData.containerIsMixed = document.getElementById('containerIsMixed')?.checked || false;
                
                // Check if we're creating a new container type
                const createContainerType = document.getElementById('createContainerType')?.checked || false;
                
                if (createContainerType) {
                    // Creating a new container type for all containers
                    formData.newContainerType = {
                        typeName: document.getElementById('newContainerTypeName')?.value || '',
                        description: document.getElementById('newContainerTypeDescription')?.value || '',
                        capacity: document.getElementById('newContainerTypeCapacity')?.value || ''
                    };
                } else {
                    // Using existing container type for all containers
                    formData.containerTypeId = document.getElementById('containerType')?.value || '';
                    formData.containerCapacity = document.getElementById('containerCapacity')?.value || '';
                }
                
                // For multiple containers, each container will use its own location
                // Ensure PackageLocations is available
                checkPackageLocations();
                
                const packageLocations = PackageLocations.getSelectedLocations();
                formData.containerLocations = packageLocations.map(loc => ({
                    packageNumber: loc.packageNumber,
                    locationId: loc.locationId
                }));
                console.log("Using multiple container locations:", formData.containerLocations);
            }
        }
    }
    
    // Handle location for non-container storage or for samples outside containers
    if (formData.storageOption === 'direct' || 
        (formData.storageOption === 'container' && !formData.useExistingContainer)) {
        
        // For multiple samples with separate storage
        if (formData.sampleType === 'multiple' && formData.separateStorage) {
            // Ensure PackageLocations is available
            checkPackageLocations();
            
            const packageLocations = PackageLocations.getSelectedLocations();
            formData.packageLocations = packageLocations.map(loc => ({
                packageNumber: loc.packageNumber,
                locationId: loc.locationId
            }));
            console.log("Using separate locations for packages:", formData.packageLocations);
        } else {
            // Standard location selection
            formData.storageLocation = document.getElementById('selectedLocationInput')?.value || registerApp.selectedLocation || '';
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

// Explicitly export all functions to the global scope to ensure they're available
// Run immediately, don't wait for DOMContentLoaded
(function() {
    // Ensure critical functions are exported globally
    window.validateCurrentStep = validateCurrentStep;
    window.updateRegistrationSummary = updateRegistrationSummary;
    window.handleFormSubmission = handleFormSubmission;
    
    console.log('Critical registration functions explicitly exported to global scope immediately');
})();