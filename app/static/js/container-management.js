// app/static/js/container-management.js
document.addEventListener('DOMContentLoaded', function() {
    console.log('Container management initialized');
    
    // Debug info
    const containers = document.querySelectorAll('table tbody tr[data-container-id]');
    console.log(`Found ${containers.length} container rows in DOM`);
    
    // Search functionality for container table
    const searchInput = document.getElementById('containerSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const tableRows = document.querySelectorAll('tbody tr');
            
            tableRows.forEach(row => {
                const rowText = row.textContent.toLowerCase();
                row.style.display = rowText.includes(searchTerm) ? '' : 'none';
            });
        });
    }
    
    // Filter buttons
    setupFilterButtons();
    
    // Add event listener to delete buttons
    document.querySelectorAll('.delete-container-btn').forEach(button => {
        button.addEventListener('click', function() {
            const containerId = this.getAttribute('data-container-id');
            deleteContainer(containerId);
        });
    });
    
    // Add event listeners to "Add sample" buttons
    document.querySelectorAll('.add-sample-btn').forEach(button => {
        button.addEventListener('click', function() {
            const containerId = this.getAttribute('data-container-id');
            document.getElementById('targetContainerId').value = containerId;
        });
    });
    
    // Setup container type creation toggle
    setupContainerTypeToggle();
    
    // Setup container type selection change
    setupContainerTypeSelection();
    
    // Add an event listener to the disposal link in the sidebar navigation using the ID
    const disposalLink = document.getElementById('disposalLink');
    if (disposalLink) {
        console.log("Container page: Found disposal link - replacing click handler");
        
        // Remove any existing click handler by cloning and replacing the node
        const newDisposalLink = disposalLink.cloneNode(true);
        disposalLink.parentNode.replaceChild(newDisposalLink, disposalLink);
        
        // Add a fresh click handler that will call our container-specific function
        newDisposalLink.addEventListener('click', function(e) {
            e.preventDefault();
            console.log("Container disposal link clicked - showing container-specific disposal modal");
            showContainerDisposalModal();
        });
        
        // Remove the onclick attribute to prevent double execution
        newDisposalLink.removeAttribute('onclick');
    } else {
        console.error("Container page: Could not find disposal link with ID 'disposalLink'");
    }
});

function setupFilterButtons() {
    const filterAll = document.getElementById('filterAll');
    const filterEmpty = document.getElementById('filterEmpty');
    const filterFull = document.getElementById('filterFull');
    
    if (!filterAll || !filterEmpty || !filterFull) return;
    
    // All containers
    filterAll.addEventListener('click', function() {
        resetButtonStates([filterAll, filterEmpty, filterFull]);
        this.classList.add('active');
        filterContainers('all');
    });
    
    // Empty containers
    filterEmpty.addEventListener('click', function() {
        resetButtonStates([filterAll, filterEmpty, filterFull]);
        this.classList.add('active');
        filterContainers('empty');
    });
    
    // Filled containers
    filterFull.addEventListener('click', function() {
        resetButtonStates([filterAll, filterEmpty, filterFull]);
        this.classList.add('active');
        filterContainers('full');
    });
    
    // Default: Show all
    filterAll.classList.add('active');
}

function resetButtonStates(buttons) {
    buttons.forEach(button => {
        button.classList.remove('active');
    });
}

function filterContainers(filter) {
    const rows = document.querySelectorAll('tbody tr');
    
    rows.forEach(row => {
        const sampleCount = row.querySelector('td:nth-child(5)');
        
        if (!sampleCount) {
            row.style.display = '';
            return;
        }
        
        const countText = sampleCount.textContent;
        // Find first number in text (samples X / units Y)
        const firstNumber = parseInt(countText.match(/\d+/) || [0]);
        
        if (filter === 'all') {
            row.style.display = '';
        } else if (filter === 'empty') {
            row.style.display = firstNumber === 0 ? '' : 'none';
        } else if (filter === 'full') {
            row.style.display = firstNumber > 0 ? '' : 'none';
        }
    });
}

// Function to add sample to container
function addSampleToContainer() {
    const containerId = document.getElementById('targetContainerId').value;
    const sampleId = document.getElementById('sampleSelect').value;
    const amount = parseInt(document.getElementById('sampleAmount').value) || 1;
    
    // Validation
    if (!sampleId) {
        showErrorMessage('Please select a sample');
        return;
    }
    
    if (amount < 1) {
        showErrorMessage('Amount must be at least 1');
        return;
    }
    
    // Create data object
    const data = {
        containerId: containerId,
        sampleId: sampleId,
        amount: amount
    };
    
    // Send to server
    fetch('/api/containers/add-sample', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data),
        cache: 'no-store' // Ensure we don't use cached response
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage('Sample added to container!');
            
            // Close modal and reload page
            const modal = bootstrap.Modal.getInstance(document.getElementById('addSampleToContainerModal'));
            modal.hide();
            
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showErrorMessage(`Error adding sample: ${data.error}`);
        }
    })
    .catch(error => {
        showErrorMessage(`An error occurred: ${error}`);
    });
}

// Create new container
function createContainer() {
    // Clear previous validation errors
    clearValidationErrors();
    
    const description = document.getElementById('containerDescription').value;
    const createNewType = document.getElementById('createContainerType').checked;
    const isMixed = document.getElementById('containerIsMixed').checked;
    const locationId = document.getElementById('containerLocation').value;
    const capacityInput = document.getElementById('containerCapacity');
    const capacity = capacityInput.value;
    
    // Get type data - either existing or new
    let typeId = null;
    let newContainerType = null;
    
    // Validation
    let isValid = true;
    
    // Description is required
    if (!description) {
        showFieldError('containerDescription', 'Please enter a description for the container');
        isValid = false;
    }
    
    // Location is required
    if (!locationId) {
        showFieldError('containerLocation', 'Storage location is required');
        isValid = false;
    }
    
    // Only validate capacity if not creating a new container type
    if (!createNewType && !capacity) {
        showFieldError('containerCapacity', 'Container capacity is required');
        isValid = false;
    }
    
    if (createNewType) {
        // Creating a new container type
        const typeNameInput = document.getElementById('newContainerTypeName');
        const typeName = typeNameInput.value;
        const typeCapacity = document.getElementById('newContainerTypeCapacity').value;
        const typeDescription = document.getElementById('newContainerTypeDescription').value;
        
        if (!typeName) {
            showFieldError('newContainerTypeName', 'Container type name is required');
            isValid = false;
        }
        
        newContainerType = {
            typeName: typeName,
            capacity: typeCapacity || null,
            description: typeDescription || ''
        };
        
        // Use the new type's capacity if not specified directly
        if (!capacity && typeCapacity) {
            capacityInput.value = typeCapacity;
        }
    } else {
        // Using existing container type
        const containerTypeSelect = document.getElementById('containerType');
        typeId = containerTypeSelect.value;
        
        if (!typeId) {
            showFieldError('containerType', 'Container type is required');
            isValid = false;
        }
    }
    
    // If validation failed, stop here
    if (!isValid) {
        return;
    }
    
    // Debug log
    console.log('Creating container with data:', {
        description,
        typeId: typeId || 'new type',
        capacity: capacity || 'null',
        isMixed,
        locationId: locationId || 'default',
        newContainerType
    });
    
    // Create container object
    const containerData = {
        description: description,
        containerTypeId: typeId || null,
        capacity: capacity || null,
        isMixed: isMixed,
        locationId: locationId || null,
        newContainerType: newContainerType
    };
    
    // Send to server
    fetch('/api/containers', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(containerData)
    })
    .then(response => {
        console.log('Server response status:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('Server response data:', data);
        if (data.success) {
            showSuccessMessage('Container created successfully!');
            
            // Close modal and reload page
            const modal = bootstrap.Modal.getInstance(document.getElementById('createContainerModal'));
            if (modal) modal.hide();
            
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            // If there's a field-specific error, show it on that field
            if (data.field) {
                const fieldMapping = {
                    'description': 'containerDescription',
                    'locationId': 'containerLocation',
                    'containerTypeId': 'containerType',
                    'capacity': 'containerCapacity',
                    'newContainerTypeName': 'newContainerTypeName',
                    'newContainerTypeCapacity': 'newContainerTypeCapacity'
                };
                
                // Map backend field names to frontend element IDs
                const fieldId = fieldMapping[data.field] || data.field;
                showFieldError(fieldId, data.error);
                
                // Focus on the field with the error
                const field = document.getElementById(fieldId);
                if (field) {
                    field.focus();
                }
            } else {
                showErrorMessage(`Error during creation: ${data.error}`);
            }
        }
    })
    .catch(error => {
        console.error('Error creating container:', error);
        showErrorMessage(`An error occurred: ${error}`);
    });
}

// Helper function to clear validation errors
function clearValidationErrors() {
    // Remove is-invalid class from all inputs
    document.querySelectorAll('.is-invalid').forEach(element => {
        element.classList.remove('is-invalid');
    });
    
    // Remove all validation feedback elements
    document.querySelectorAll('.invalid-feedback').forEach(element => {
        element.remove();
    });
}

// Helper function to show field-specific errors
function showFieldError(fieldId, errorMessage) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    
    // Add invalid class to the field
    field.classList.add('is-invalid');
    
    // Create feedback element if it doesn't exist
    let feedback = field.nextElementSibling;
    if (!feedback || !feedback.classList.contains('invalid-feedback')) {
        feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        field.parentNode.insertBefore(feedback, field.nextSibling);
    }
    
    // Set error message
    feedback.textContent = errorMessage;
}

// Delete container
function deleteContainer(containerId) {
    if (confirm(`Are you sure you want to delete container ${containerId}?`)) {
        console.log('Deleting container:', containerId);
        
        fetch(`/api/containers/${containerId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSuccessMessage('Container deleted successfully!');
                
                // Remove row from table
                const row = document.querySelector(`tr[data-container-id="${containerId}"]`);
                if (row) {
                    row.remove();
                } else {
                    // Reload page if row not found
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                }
            } else {
                showErrorMessage(`Error during deletion: ${data.error}`);
            }
        })
        .catch(error => {
            console.error('Error deleting container:', error);
            showErrorMessage(`An error occurred: ${error}`);
        });
    }
}

// Message functions
function showSuccessMessage(message) {
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

    // Add 'show' class after short delay (for animation effect)
    setTimeout(() => successToast.classList.add('show'), 10);

    // Remove automatically after 3 seconds
    setTimeout(() => {
        successToast.classList.remove('show');
        setTimeout(() => successToast.remove(), 300);
    }, 3000);
}

function showErrorMessage(message) {
    // Check if there's a global showErrorMessageDisposal function
    if (typeof showErrorMessageDisposal === 'function') {
        // Use the global function instead to avoid conflicts
        showErrorMessageDisposal(message);
        return;
    }
    
    // Fallback in case the global function isn't available
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

    // Add 'show' class after short delay (for animation effect)
    setTimeout(() => errorToast.classList.add('show'), 10);

    // Remove automatically after 5 seconds
    setTimeout(() => {
        errorToast.classList.remove('show');
        setTimeout(() => errorToast.remove(), 300);
    }, 5000);
}

// Function to set up container type toggle
function setupContainerTypeToggle() {
    const createTypeCheckbox = document.getElementById('createContainerType');
    const containerTypeSelect = document.getElementById('containerType');
    const newTypeSection = document.getElementById('newContainerTypeSection');
    const capacityInput = document.getElementById('containerCapacity');
    
    if (!createTypeCheckbox || !containerTypeSelect || !newTypeSection) return;
    
    // Toggle between container type dropdown and create new section
    createTypeCheckbox.addEventListener('change', function() {
        const createNew = this.checked;
        
        containerTypeSelect.disabled = createNew;
        capacityInput.disabled = createNew; // Also disable capacity when creating new type
        newTypeSection.classList.toggle('d-none', !createNew);
        
        // Clear validation errors on toggle
        if (createNew) {
            // We're creating a new type, clear validation on select
            containerTypeSelect.classList.remove('is-invalid');
            const selectFeedback = containerTypeSelect.nextElementSibling;
            if (selectFeedback && selectFeedback.classList.contains('invalid-feedback')) {
                selectFeedback.remove();
            }
            
            // Clear container type selection
            containerTypeSelect.value = '';
            
            // Focus on new type name field
            setTimeout(() => {
                document.getElementById('newContainerTypeName').focus();
            }, 100);
        } else {
            // We're using existing type, clear validation on new type fields
            document.getElementById('newContainerTypeName').classList.remove('is-invalid');
            const typeFeedback = document.getElementById('newContainerTypeName').nextElementSibling;
            if (typeFeedback && typeFeedback.classList.contains('invalid-feedback')) {
                typeFeedback.remove();
            }
            
            // Re-enable capacity input
            capacityInput.disabled = false;
            
            // If container type is already selected, update the capacity
            if (containerTypeSelect.value) {
                const selectedOption = containerTypeSelect.options[containerTypeSelect.selectedIndex];
                const typeData = selectedOption.dataset;
                
                if (typeData.capacity && !capacityInput.value) {
                    capacityInput.value = typeData.capacity;
                }
            }
            
            // Focus on container type select
            setTimeout(() => {
                containerTypeSelect.focus();
            }, 100);
        }
    });
}

// Function to handle container type selection
function setupContainerTypeSelection() {
    const containerTypeSelect = document.getElementById('containerType');
    const capacityInput = document.getElementById('containerCapacity');
    
    if (!containerTypeSelect || !capacityInput) return;
    
    // Lookup capacity when type changes
    containerTypeSelect.addEventListener('change', function() {
        const typeId = this.value;
        if (!typeId) {
            capacityInput.value = '';
            capacityInput.placeholder = 'Capacity (required)';
            return;
        }
        
        // Find the selected option
        const selectedOption = this.options[this.selectedIndex];
        const typeData = selectedOption.dataset;
        
        // Set default capacity if available
        if (typeData.capacity) {
            capacityInput.value = typeData.capacity;
            capacityInput.placeholder = `Default: ${typeData.capacity}`;
        }
        
        // Remove any validation error on container type
        containerTypeSelect.classList.remove('is-invalid');
        const feedback = containerTypeSelect.nextElementSibling;
        if (feedback && feedback.classList.contains('invalid-feedback')) {
            feedback.remove();
        }
    });
    
    // Initial setup - populate capacity if a type is already selected
    if (containerTypeSelect.value) {
        const selectedOption = containerTypeSelect.options[containerTypeSelect.selectedIndex];
        const typeData = selectedOption.dataset;
        
        if (typeData.capacity && !capacityInput.value) {
            capacityInput.value = typeData.capacity;
            capacityInput.placeholder = `Default: ${typeData.capacity}`;
        }
    }
}

// Custom function to show disposal modal specifically from the container page
// This ensures compatibility with the container management code
function showContainerDisposalModal() {
    console.log("Container management: showContainerDisposalModal called");
    
    // Check if Bootstrap is available
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap is not loaded. Cannot show modal.');
        alert('An error occurred. Please try reloading the page.');
        return;
    }
    
    // Check if modal element exists
    const modalElement = document.getElementById('disposalModal');
    if (!modalElement) {
        console.error('Modal element not found:', 'disposalModal');
        alert('Modal not found. Please contact the administrator.');
        return;
    }
    
    console.log("Container management: Starting to load disposal modal data");
    
    // Modify this from the original showDisposalModal function to handle any
    // container-specific issues with the disposal modal
    
    // Show loading indicator
    showOverlayMessage("Loading samples...");
    
    // Get available samples and recent disposals with explicit handling
    Promise.all([
        // Use explicit fetch with full error handling for active samples
        fetch('/api/activeSamples')
            .then(response => {
                if (!response.ok) {
                    console.error(`Server error: ${response.status} ${response.statusText}`);
                    throw new Error(`Server error: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("Active samples response:", data);
                
                // Check for success flag
                if (!data.success) {
                    throw new Error(data.error || "Failed to get active samples");
                }
                
                return data;
            }),
            
        // Fetch recent disposals
        fetch('/api/recentDisposals')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Server error: ${response.status}`);
                }
                return response.json();
            })
    ])
    .then(([samplesData, disposalsData]) => {
        // Hide loading message
        hideOverlayMessage();
        
        console.log("Sample data fetched for disposal modal:", samplesData);
        
        // Update dropdown with available samples using the function from disposal-functions.js
        if (typeof populateDisposalSampleSelect === 'function') {
            populateDisposalSampleSelect(samplesData.samples || []);
        } else {
            console.error("populateDisposalSampleSelect function not available");
        }
        
        // Update table with recent disposals
        if (typeof populateRecentDisposalsTable === 'function') {
            populateRecentDisposalsTable(disposalsData.disposals || []);
        } else {
            console.error("populateRecentDisposalsTable function not available");
        }
        
        // Show modal
        try {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
        } catch (modalError) {
            console.error('Error showing modal:', modalError);
            alert('Could not show modal. Please try reloading the page.');
        }
    })
    .catch(error => {
        // Hide loading message
        hideOverlayMessage();
        
        console.error("Error fetching disposal data:", error);
        showErrorMessage(`Could not load disposal data: ${error.message}`);
    });
}

// Helper function to show a message overlay during loading
function showOverlayMessage(message) {
    // Create overlay if it doesn't exist
    if (!document.getElementById('messageOverlay')) {
        const overlay = document.createElement('div');
        overlay.id = 'messageOverlay';
        overlay.className = 'message-overlay';
        overlay.innerHTML = `
            <div class="overlay-content">
                <div class="spinner-border text-light" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="overlay-message mt-2">${message}</div>
            </div>
        `;
        document.body.appendChild(overlay);
    } else {
        // Update message if overlay exists
        document.querySelector('#messageOverlay .overlay-message').textContent = message;
    }
}

// Helper function to hide message overlay
function hideOverlayMessage() {
    const overlay = document.getElementById('messageOverlay');
    if (overlay) {
        overlay.classList.add('fade-out');
        setTimeout(() => {
            overlay.remove();
        }, 300);
    }
}