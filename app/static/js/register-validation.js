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


// Function to validate the current step
// Make it globally accessible with proper exporting
function validateCurrentStep() {
    console.log('Validation function called for step:', registerApp.currentStep);
    
    // Export to window object on first call
    if (!window.validateCurrentStep) {
        window.validateCurrentStep = validateCurrentStep;
    }
    
    
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
            
            // Container validation with capacity checks
            const storageOptionStep2 = document.querySelector('input[name="storageOption"]:checked')?.value || 'direct';
            
            if (storageOptionStep2 === 'container') {
                // Check if existing container option is selected
                const existingContainerOption = document.getElementById('existingContainerOption');
                
                if (existingContainerOption && existingContainerOption.checked) {
                    const existingContainerSelect = document.getElementById('existingContainerSelect');
                    if (!existingContainerSelect || !existingContainerSelect.value) {
                        showErrorMessage('Please select an existing container', 'existingContainerSelect');
                        isValid = false;
                    } else {
                        // Check capacity of selected container
                        const selectedOption = existingContainerSelect.options[existingContainerSelect.selectedIndex];
                        if (selectedOption && selectedOption.textContent) {
                            const containerText = selectedOption.textContent;
                            const capacityMatch = containerText.match(/(\d+)\/(\d+) available/);
                            if (capacityMatch) {
                                const availableCapacity = parseInt(capacityMatch[1]);
                                const sampleAmount = parseInt(totalAmount.value) || 0;
                                
                                if (sampleAmount > availableCapacity) {
                                    showErrorMessage(`Sample amount (${sampleAmount}) exceeds available container capacity (${availableCapacity})`, 'totalAmount');
                                    isValid = false;
                                }
                            }
                        }
                    }
                } else {
                    // Validate new container capacity
                    const createNewTypeOption = document.getElementById('createNewTypeOption');
                    const useExistingTypeOption = document.getElementById('useExistingTypeOption');
                    
                    let containerCapacity = 0;
                    
                    if (createNewTypeOption && createNewTypeOption.checked) {
                        // Get capacity from new container type
                        const newTypeCapacity = document.getElementById('newContainerTypeCapacity');
                        if (newTypeCapacity && newTypeCapacity.value) {
                            containerCapacity = parseInt(newTypeCapacity.value) || 0;
                        }
                    } else if (useExistingTypeOption && useExistingTypeOption.checked) {
                        // Get capacity from existing container type
                        const containerTypeSelect = document.getElementById('containerType');
                        const containerCapacityInput = document.getElementById('containerCapacity');
                        
                        if (containerCapacityInput && containerCapacityInput.value) {
                            containerCapacity = parseInt(containerCapacityInput.value) || 0;
                        } else if (containerTypeSelect && containerTypeSelect.selectedIndex > 0) {
                            const selectedTypeOption = containerTypeSelect.options[containerTypeSelect.selectedIndex];
                            const defaultCapacity = selectedTypeOption.getAttribute('data-capacity');
                            if (defaultCapacity) {
                                containerCapacity = parseInt(defaultCapacity) || 0;
                            }
                        }
                    }
                    
                    // Validate that sample amount doesn't exceed container capacity
                    if (containerCapacity > 0) {
                        const sampleAmount = parseInt(totalAmount.value) || 0;
                        if (sampleAmount > containerCapacity) {
                            showErrorMessage(`Sample amount (${sampleAmount}) exceeds container capacity (${containerCapacity}). Please choose a larger container type or reduce the sample amount.`, 'totalAmount');
                            isValid = false;
                        }
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
            const storageOptionStep4 = document.querySelector('input[name="storageOption"]:checked')?.value || 'direct';
            const separateStorage = document.getElementById('separateStorage')?.checked || false;
            const useExistingContainer = storageOptionStep4 === 'container' && document.getElementById('existingContainerOption')?.checked;
            
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
            
            // Standard single location validation
            if (!registerApp.selectedLocation) {
                showErrorMessage('Please select a location by clicking on an available space in the grid.');
                return false;
            }
            return true;
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
            case 'single': return 'Standard Sample';
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
        
        if (!registerApp.selectedLocation && !registerApp.skipLocationSelection) {
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
        expireDate: document.querySelector('[name="expireDate"]')?.value || null,
        hasSerialNumbers: document.getElementById('hasSerialNumbers')?.checked || false,
        other: document.querySelector('[name="other"]')?.value || '',
        
        // Identification
        serialNumbers: registerApp.scannedItems || [],
    };
    
    
    // Add bulk sample specific data
    if (formData.sampleType === 'bulk') {
        formData.isBulkSample = true;
    }
    
    // Container functionality
    if (formData.storageOption === 'container') {
        formData.useContainers = true;
        
        // For single sample or bulk material
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
                const createContainerType = document.getElementById('createNewTypeOption')?.checked || false;
                
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
                
                // Save container location separately - check text input format first
                const containerLocationInput = document.getElementById('containerLocation');
                if (containerLocationInput && containerLocationInput.value) {
                    // For text input like "1.1.1", we need to convert to LocationID
                    const locationText = containerLocationInput.value.trim();
                    
                    // Check if we have the location data in the global state
                    if (window.registerApp && window.registerApp.locations) {
                        const matchingLocation = window.registerApp.locations.find(loc => 
                            loc.LocationName === locationText
                        );
                        if (matchingLocation) {
                            formData.containerLocationId = matchingLocation.LocationID;
                            console.log("Container location set to:", locationText, "(ID:", matchingLocation.LocationID, ")");
                        } else {
                            // If no match found, try to create the location or use fallback
                            formData.containerLocationText = locationText;
                            console.log("Container location text set to:", locationText, "(will be resolved server-side)");
                        }
                    } else {
                        // Fallback - send as text and let server handle
                        formData.containerLocationText = locationText;
                        console.log("Container location text set to:", locationText, "(no location data available)");
                    }
                }
            }
    }
    
    // Handle location for non-container storage or for samples outside containers
    if (formData.storageOption === 'direct' || 
        (formData.storageOption === 'container' && !formData.useExistingContainer)) {
        
        // Standard location selection
        formData.storageLocation = document.getElementById('selectedLocationInput')?.value || registerApp.selectedLocation || '';
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