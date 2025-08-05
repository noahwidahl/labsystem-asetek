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
                // Use the same logic as identification step for consistency
                const totalAmount = parseInt(document.querySelector('[name="totalAmount"]')?.value) || 0;
                const sampleType = document.querySelector('[name="sampleTypeOption"]:checked')?.value;
                const expectedCount = (sampleType === 'bulk') ? 1 : totalAmount;
                
                console.log('🔍 VALIDATION DEBUG for step 3:', {
                    totalAmount: totalAmount,
                    sampleType: sampleType,
                    expectedCount: expectedCount,
                    scannedCount: registerApp.scannedItems.length
                });
                
                if (registerApp.scannedItems.length < expectedCount) {
                    showErrorMessage(`${expectedCount - registerApp.scannedItems.length} more samples need to be scanned`);
                    return false;
                }
                
                // Serial number uniqueness validation is handled asynchronously in form navigation
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
        case 5:
            // Print step - always valid (user can choose to print or skip)
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
    const partNumber = document.querySelector('[name="partNumber"]')?.value || '';
    const trackingNumber = document.querySelector('[name="trackingNumber"]')?.value || '';
    const owner = document.querySelector('[name="owner"] option:checked')?.textContent || '';
    const expireDate = document.querySelector('[name="expireDate"]')?.value || '';
    const taskAssignment = document.querySelector('[name="task"] option:checked')?.textContent || '';
    const supplier = getSelectedSupplier();
    
    let summaryHtml = `
        <div class="row">
            <div class="col-md-6">
                <div class="summary-item mb-3">
                    <div class="summary-title"><i class="fas fa-flask me-2"></i>Sample Information</div>
                    <div class="summary-content">
                        <p><strong>${description}</strong></p>
                        <p><i class="fas fa-cubes me-2"></i>Amount: ${totalAmount} ${unitText}</p>
                        <p><i class="fas fa-tag me-2"></i>Type: ${getSampleTypeText(sampleType)}</p>
                        ${partNumber ? `<p><i class="fas fa-barcode me-2"></i>Part Number: ${partNumber}</p>` : ''}
                        ${expireDate ? `<p><i class="fas fa-calendar me-2"></i>Expire Date: ${formatDate(expireDate)}</p>` : ''}
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="summary-item mb-3">
                    <div class="summary-title"><i class="fas fa-info-circle me-2"></i>Administrative Details</div>
                    <div class="summary-content">
                        ${owner ? `<p><i class="fas fa-user me-2"></i>Responsible: ${owner}</p>` : ''}
                        ${supplier ? `<p><i class="fas fa-truck me-2"></i>Supplier: ${supplier}</p>` : ''}
                        ${trackingNumber ? `<p><i class="fas fa-shipping-fast me-2"></i>Tracking: ${trackingNumber}</p>` : ''}
                        ${taskAssignment ? `<p><i class="fas fa-tasks me-2"></i>Task: ${taskAssignment}</p>` : ''}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    
    // Add storage info
    summaryHtml += `
        <div class="summary-item mb-3">
            <div class="summary-title"><i class="fas fa-warehouse me-2"></i>Storage Details</div>
            <div class="summary-content">
                <p><i class="fas fa-box me-2"></i>Storage Type: ${storageOption === 'direct' ? 'Direct storage on shelf' : 'Storage in container'}</p>
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
        const serialNumbers = registerApp.scannedItems || [];
        summaryHtml += `
            <div class="summary-item">
                <div class="summary-title"><i class="fas fa-qrcode me-2"></i>Identification</div>
                <div class="summary-content">
                    <p><i class="fas fa-list me-2"></i>${serialNumbers.length} serial numbers recorded</p>
                    ${serialNumbers.length > 0 ? `<div class="small text-muted mt-2">Serial numbers: ${serialNumbers.join(', ')}</div>` : ''}
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
    
    // Helper function to get selected supplier
    function getSelectedSupplier() {
        const selectedSupplierName = document.getElementById('selectedSupplierName');
        if (selectedSupplierName && selectedSupplierName.textContent !== 'No supplier selected') {
            return selectedSupplierName.textContent;
        }
        return '';
    }
    
    // Helper function to format date
    function formatDate(dateString) {
        if (!dateString) return '';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('da-DK', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });
        } catch (e) {
            return dateString;
        }
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
        task: document.querySelector('[name="task"]')?.value || null,
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
                
                // Container location will be set from the main location selection in step 4
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
            
            // Don't show success message yet - wait until print/skip step
            // Store success message for later
            window.registrationSuccessMessage = successMessage;
            
            // Populate print step with sample data and go to print step (step 5)
            if (data.sample_data && typeof window.populatePrintStep === 'function') {
                console.log('Moving to print step with sample data:', data.sample_data);
                
                // Store container information for print step
                if (data.container_ids && data.container_ids.length > 0) {
                    window.registrationContainerIds = data.container_ids;
                    console.log('Stored container IDs for print step:', data.container_ids);
                } else {
                    window.registrationContainerIds = null;
                }
                
                // Populate the print step with sample data
                window.populatePrintStep(data.sample_data);
                
                // Go to step 5 (print step)
                registerApp.currentStep = 5;
                showStep(5);
            } else {
                console.log('Sample data not available or print function not loaded - redirecting to dashboard');
                // If print step is not available, redirect to dashboard
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 2000);
            }
        } else {
            showErrorMessage(`Error during registration: ${data.error}`);
        }
    })
    .catch(error => {
        showErrorMessage(`An error occurred: ${error}`);
    });
}

// Async function to validate serial numbers against database
async function validateSerialNumbersAsync(serialNumbers) {
    if (!serialNumbers || serialNumbers.length === 0) {
        return { success: true };
    }
    
    try {
        console.log('🔍 SERIAL VALIDATION: Checking serial numbers:', serialNumbers);
        
        const response = await fetch('/api/validate-serial-numbers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                serialNumbers: serialNumbers
            })
        });
        
        const data = await response.json();
        console.log('🔍 SERIAL VALIDATION: Response:', data);
        
        if (!data.success) {
            showErrorToast(data.error);
            return { success: false, error: data.error };
        }
        
        return { success: true };
        
    } catch (error) {
        console.error('Error validating serial numbers:', error);
        showErrorToast('Error validating serial numbers: ' + error.message);
        return { success: false, error: error.message };
    }
}

// Explicitly export all functions to the global scope to ensure they're available
// Run immediately, don't wait for DOMContentLoaded
(function() {
    // Ensure critical functions are exported globally
    window.validateCurrentStep = validateCurrentStep;
    window.updateRegistrationSummary = updateRegistrationSummary;
    window.handleFormSubmission = handleFormSubmission;
    window.validateSerialNumbersAsync = validateSerialNumbersAsync;
    
    console.log('Critical registration functions explicitly exported to global scope immediately');
})();