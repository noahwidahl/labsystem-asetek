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
    
    // Add event listener to delete container buttons
    document.querySelectorAll('.delete-container-btn').forEach(button => {
        button.addEventListener('click', function() {
            const containerId = this.getAttribute('data-container-id');
            deleteContainer(containerId);
        });
    });
    
    // Add event listener to container detail buttons
    document.querySelectorAll('button.btn-secondary[data-container-id]').forEach(button => {
        button.addEventListener('click', function() {
            const containerId = this.getAttribute('data-container-id');
            
            // Implementer direkte i denne fil
            showContainerDetails(containerId);
        });
    });
    
    // Add event listener to delete container type buttons
    document.querySelectorAll('.delete-container-type-btn').forEach(button => {
        button.addEventListener('click', function() {
            const containerTypeId = this.getAttribute('data-container-type-id');
            const containerTypeName = this.getAttribute('data-container-type-name');
            deleteContainerType(containerTypeId, containerTypeName);
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

// Direkte implementation af container details funktion
function showContainerDetails(containerId) {
    // Clear previous content
    document.getElementById('container-id').textContent = '-';
    document.getElementById('container-description').textContent = '-';
    document.getElementById('container-type').textContent = '-';
    document.getElementById('container-status').textContent = '-';
    document.getElementById('container-mixed').textContent = '-';
    document.getElementById('container-location').textContent = '-';
    document.getElementById('container-samples-list').innerHTML = '<p class="text-center text-muted">Loading samples...</p>';
    document.getElementById('container-history-list').innerHTML = '<p class="text-center text-muted">Loading history...</p>';
    
    // Set the modal title
    document.getElementById('containerDetailsModalLabel').textContent = `Container ${containerId} Details`;
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('containerDetailsModal'));
    modal.show();
    
    // Fetch container details
    fetch(`/api/containers/${containerId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.container) {
                const container = data.container;
                
                // Update container information safely
                document.getElementById('container-id').textContent = String(container.ContainerID || '-');
                document.getElementById('container-description').textContent = container.Description || '-';
                document.getElementById('container-type').textContent = container.TypeName || 'Standard';
                document.getElementById('container-status').innerHTML = `<span class="badge bg-primary">${container.Status || 'Active'}</span>`;
                
                // Safely handle IsMixed which can be 0/1 or true/false
                let isMixed = 'No';
                if (container.IsMixed === 1 || container.IsMixed === '1' || container.IsMixed === true) {
                    isMixed = 'Yes';
                }
                document.getElementById('container-mixed').textContent = isMixed;
                
                // Get location data
                if (container.LocationID) {
                    // Try the new API endpoint first
                    fetch(`/api/locations/${container.LocationID}`)
                        .then(response => {
                            if (!response.ok) {
                                // Fall back to the container-specific endpoint
                                return fetch(`/api/containers/${containerId}/location`);
                            }
                            return response;
                        })
                        .then(response => response.json())
                        .then(locationData => {
                            if (locationData.success && locationData.location) {
                                document.getElementById('container-location').textContent = locationData.location.LocationName || '-';
                            } else {
                                document.getElementById('container-location').textContent = 'No location information';
                            }
                        })
                        .catch(error => {
                            console.error('Error fetching container location:', error);
                            document.getElementById('container-location').textContent = 'Error loading location';
                        });
                } else {
                    document.getElementById('container-location').textContent = 'No location assigned';
                }
                
                // Display samples with more detail
                if (data.samples && data.samples.length > 0) {
                    let samplesHtml = '<div class="table-responsive"><table class="table table-sm table-hover">';
                    samplesHtml += `
                        <thead>
                            <tr>
                                <th>Sample ID</th>
                                <th>Description</th>
                                <th>Part Number</th>
                                <th>Quantity</th>
                                <th>Registered</th>
                                <th>Details</th>
                            </tr>
                        </thead>
                        <tbody>
                    `;
                    
                    data.samples.forEach(sample => {
                        const sampleId = sample.SampleID;
                        const sampleIdFormatted = `SMP-${sampleId}`;
                        
                        // Format amount safely
                        let displayAmount = '-';
                        if (sample.Amount !== null && sample.Amount !== undefined) {
                            // Try to format the amount, handle both string and number
                            try {
                                displayAmount = Number(sample.Amount).toString();
                            } catch (e) {
                                displayAmount = String(sample.Amount);
                            }
                        }
                        
                        samplesHtml += `
                            <tr>
                                <td>${sampleIdFormatted}</td>
                                <td>${sample.Description || '-'}</td>
                                <td>${sample.PartNumber || '-'}</td>
                                <td>${displayAmount} ${sample.Unit || 'pcs'}</td>
                                <td>${sample.RegisteredDate || '-'}</td>
                                <td>
                                    <button class="btn btn-sm btn-secondary sample-details-btn" 
                                           data-sample-id="${sampleId}">
                                        Details
                                    </button>
                                </td>
                            </tr>
                        `;
                    });
                    
                    samplesHtml += '</tbody></table></div>';
                    document.getElementById('container-samples-list').innerHTML = samplesHtml;
                    
                    // Add event listeners to the sample detail buttons
                    document.querySelectorAll('#container-samples-list .sample-details-btn').forEach(button => {
                        button.addEventListener('click', function() {
                            const sampleId = this.dataset.sampleId;
                            if (sampleId) {
                                // Hide container details modal
                                const containerModal = bootstrap.Modal.getInstance(document.getElementById('containerDetailsModal'));
                                if (containerModal) containerModal.hide();
                                
                                // Show sample details modal if it exists
                                const sampleDetailsModal = document.getElementById('sampleDetailsModal');
                                if (sampleDetailsModal) {
                                    // Try to call loadSampleDetails if it exists in window
                                    if (typeof window.loadSampleDetails === 'function') {
                                        window.loadSampleDetails(sampleId);
                                        const sampleModal = new bootstrap.Modal(sampleDetailsModal);
                                        sampleModal.show();
                                    }
                                }
                            }
                        });
                    });
                } else {
                    document.getElementById('container-samples-list').innerHTML = 
                        '<p class="text-center text-muted">No samples in this container</p>';
                }
                
                // Display history
                if (data.history && data.history.length > 0) {
                    let historyHtml = `
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead>
                                    <tr>
                                        <th>Date</th>
                                        <th>Action</th>
                                        <th>User</th>
                                        <th>Notes</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;
                    data.history.forEach(item => {
                        // Safely format timestamp
                        let timestamp = '-';
                        if (item.Timestamp) {
                            // Handle both string and date objects
                            try {
                                if (typeof item.Timestamp === 'object' && item.Timestamp instanceof Date) {
                                    timestamp = item.Timestamp.toLocaleString();
                                } else {
                                    timestamp = String(item.Timestamp);
                                }
                            } catch (e) {
                                console.error("Error formatting timestamp:", e);
                                timestamp = String(item.Timestamp);
                            }
                        }
                        
                        historyHtml += `
                            <tr>
                                <td>${timestamp}</td>
                                <td>${item.ActionType || '-'}</td>
                                <td>${item.UserName || '-'}</td>
                                <td>${item.Notes || '-'}</td>
                            </tr>
                        `;
                    });
                    historyHtml += '</tbody></table></div>';
                    document.getElementById('container-history-list').innerHTML = historyHtml;
                } else {
                    document.getElementById('container-history-list').innerHTML = 
                        '<p class="text-center text-muted">No history found for this container</p>';
                }
            } else {
                showErrorMessage(data.error || 'Error loading container details');
            }
        })
        .catch(error => {
            console.error('Error fetching container details:', error);
            showErrorMessage('An error occurred while loading container details');
        });
}

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
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('addSampleToContainerModal'));
            modal.hide();
            
            // Show print prompt for container update
            showContainerUpdatePrintPrompt(containerId, {
                description: `Container after adding sample`,
                action: 'Sample added'
            });
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
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('createContainerModal'));
            if (modal) modal.hide();
            
            // Show print prompt with container data from the form
            showContainerPrintPrompt(data.container_id, containerData);
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

// Delete container type
function deleteContainerType(containerTypeId, typeName) {
    // Create and show confirmation modal instead of browser alert
    const modalHtml = `
        <div class="modal fade" id="deleteTypeConfirmModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-danger text-white">
                        <h5 class="modal-title">Delete Container Type</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p>Are you sure you want to delete container type <strong>"${typeName}"</strong>?</p>
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            <span>This action can only be performed if the type is not used by any active containers.</span>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-danger" id="confirmDeleteType">Delete</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove any existing modal
    const existingModal = document.getElementById('deleteTypeConfirmModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Initialize the modal
    const modal = new bootstrap.Modal(document.getElementById('deleteTypeConfirmModal'));
    modal.show();
    
    // Handle confirm button click
    document.getElementById('confirmDeleteType').addEventListener('click', function() {
        // Hide the modal
        modal.hide();
        
        // Show loading message
        const loadingToast = document.createElement('div');
        loadingToast.className = 'custom-toast show';
        loadingToast.style.borderLeftColor = '#17a2b8';
        loadingToast.innerHTML = `
            <div class="toast-icon">
                <i class="fas fa-spinner fa-spin"></i>
            </div>
            <div class="toast-content">
                <div class="toast-title">Processing</div>
                <div class="toast-message">Deleting container type...</div>
            </div>
        `;
        document.body.appendChild(loadingToast);
        
        console.log('Deleting container type:', containerTypeId, typeName);
        
        fetch(`/api/containers/types/${containerTypeId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading toast
            loadingToast.remove();
            
            if (data.success) {
                showSuccessMessage(`Container type "${typeName}" deleted successfully!`);
                
                // Find and remove the card for this container type
                const card = document.querySelector(`.delete-container-type-btn[data-container-type-id="${containerTypeId}"]`).closest('.col-md-4');
                if (card) {
                    // Animate the removal
                    card.style.transition = 'opacity 0.3s ease';
                    card.style.opacity = '0';
                    setTimeout(() => {
                        card.remove();
                        
                        // Check if there are no container types left and show message if needed
                        const remainingCards = document.querySelectorAll('.card-title');
                        if (remainingCards.length === 0) {
                            const containerTypesRow = document.querySelector('.card:last-of-type .row');
                            if (containerTypesRow) {
                                containerTypesRow.innerHTML = `
                                    <div class="col-12">
                                        <p class="text-center text-muted">No container types defined</p>
                                    </div>
                                `;
                            }
                        }
                    }, 300);
                } else {
                    // Reload page if card not found
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                }
            } else {
                // Use custom error modal instead of toast for clearer message
                showDeletionErrorModal(typeName, data.error);
            }
        })
        .catch(error => {
            // Remove loading toast
            loadingToast.remove();
            
            console.error('Error deleting container type:', error);
            showDeletionErrorModal(typeName, 'A server error occurred while processing your request.');
        });
    });
}

// Show professional error modal
function showDeletionErrorModal(typeName, errorMessage) {
    const errorModalHtml = `
        <div class="modal fade" id="deletionErrorModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-danger text-white">
                        <h5 class="modal-title">Cannot Delete Container Type</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="d-flex align-items-center mb-3">
                            <i class="fas fa-exclamation-circle text-danger me-3" style="font-size: 2rem;"></i>
                            <p class="mb-0">Unable to delete container type <strong>"${typeName}"</strong>.</p>
                        </div>
                        <div class="alert alert-secondary">
                            <strong>Reason:</strong> ${errorMessage}
                        </div>
                        <p class="text-muted small mt-3">To delete this container type, you must first remove all references to it from active containers, samples, and tests.</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary" data-bs-dismiss="modal">OK</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove any existing error modal
    const existingModal = document.getElementById('deletionErrorModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', errorModalHtml);
    
    // Initialize and show the modal
    const errorModal = new bootstrap.Modal(document.getElementById('deletionErrorModal'));
    errorModal.show();
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

// Container print prompt functionality
let currentPrintContainer = null;

function showContainerPrintPrompt(containerId, containerData) {
    console.log('Container print prompt called with:', { containerId, containerData });
    
    // Store container info for printing
    currentPrintContainer = {
        id: containerId,
        data: containerData
    };
    
    // Create modal if it doesn't exist
    let modal = document.getElementById('containerPrintConfirmModal');
    if (!modal) {
        modal = createContainerPrintModal();
        document.body.appendChild(modal);
    }
    
    // Update modal content
    document.getElementById('printContainerId').textContent = `CNT-${containerId}`;
    document.getElementById('printContainerDescription').textContent = containerData?.description || 'Container';
    
    // Show modal
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

function createContainerPrintModal() {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'containerPrintConfirmModal';
    modal.tabIndex = -1;
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Print Container Label</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>Would you like to print the label for this container now?</p>
                    <div class="alert alert-info">
                        <strong>Container:</strong> <span id="printContainerId"></span><br>
                        <strong>Description:</strong> <span id="printContainerDescription"></span>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="skipContainerPrint()">
                        <i class="fas fa-times me-1"></i>Skip
                    </button>
                    <button type="button" class="btn btn-primary" onclick="printContainerNow()">
                        <i class="fas fa-print me-1"></i>Print Now
                    </button>
                </div>
            </div>
        </div>
    `;
    return modal;
}

async function printContainerNow() {
    if (!currentPrintContainer) return;
    
    try {
        const response = await fetch(`/api/print/container/${currentPrintContainer.id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                auto_print: true
            })
        });
        
        const result = await response.json();
        
        // Add to print job queue regardless of result
        const containerData = {
            id: currentPrintContainer.id,
            description: currentPrintContainer.data?.description || `Container CNT-${currentPrintContainer.id}`,
            type: 'container'
        };
        
        let status = 'failed';
        if (result && result.status === 'success') {
            status = 'printed';
            showSuccessMessage('Container label printed successfully!');
        } else if (result && result.status === 'warning') {
            status = 'queued'; // Printer not available, but can retry later
            showSuccessMessage('Container label queued for printing.');
        } else {
            status = 'queued'; // Failed but can retry
            showSuccessMessage('Container label added to print queue.');
        }
        
        // Add to print job queue
        addContainerPrintJob(containerData, status);
        
        // Hide modal and reload page
        bootstrap.Modal.getInstance(document.getElementById('containerPrintConfirmModal')).hide();
        currentPrintContainer = null;
        
        // Reload page to show the new container
        setTimeout(() => {
            window.location.reload();
        }, 1000);
        
    } catch (error) {
        console.error('Print error:', error);
        
        // Add to print job queue as failed/queued
        const containerData = {
            id: currentPrintContainer.id,
            description: currentPrintContainer.data?.description || `Container CNT-${currentPrintContainer.id}`,
            type: 'container'
        };
        addContainerPrintJob(containerData, 'queued');
        
        showSuccessMessage('Container label added to print queue due to printer issues.');
        
        // Hide modal and reload page
        bootstrap.Modal.getInstance(document.getElementById('containerPrintConfirmModal')).hide();
        currentPrintContainer = null;
        
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }
}

function skipContainerPrint() {
    // Add to print job queue when skipping
    if (currentPrintContainer) {
        const containerData = {
            id: currentPrintContainer.id,
            description: currentPrintContainer.data?.description || `Container CNT-${currentPrintContainer.id}`,
            type: 'container'
        };
        addContainerPrintJob(containerData, 'queued');
        showSuccessMessage('Container label added to print queue.');
    }
    
    // Hide modal and reload page
    bootstrap.Modal.getInstance(document.getElementById('containerPrintConfirmModal')).hide();
    currentPrintContainer = null;
    
    // Reload page to show the new container
    setTimeout(() => {
        window.location.reload();
    }, 1000);
}

// Container update print prompt functionality (for when samples are added/removed)
function showContainerUpdatePrintPrompt(containerId, updateInfo) {
    console.log('Container update print prompt called with:', { containerId, updateInfo });
    
    // Store container info for printing
    currentPrintContainer = {
        id: containerId,
        data: updateInfo
    };
    
    // Create modal if it doesn't exist
    let modal = document.getElementById('containerUpdatePrintModal');
    if (!modal) {
        modal = createContainerUpdatePrintModal();
        document.body.appendChild(modal);
    }
    
    // Update modal content
    document.getElementById('updateContainerId').textContent = `CNT-${containerId}`;
    document.getElementById('updateContainerAction').textContent = updateInfo?.action || 'Container updated';
    
    // Show modal
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

function createContainerUpdatePrintModal() {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'containerUpdatePrintModal';
    modal.tabIndex = -1;
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Container Updated - Print Label?</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>Container has been updated. Would you like to print an updated label with current contents?</p>
                    <div class="alert alert-info">
                        <strong>Container:</strong> <span id="updateContainerId"></span><br>
                        <strong>Change:</strong> <span id="updateContainerAction"></span>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="skipContainerUpdatePrint()">
                        <i class="fas fa-times me-1"></i>Skip
                    </button>
                    <button type="button" class="btn btn-primary" onclick="printContainerUpdateNow()">
                        <i class="fas fa-print me-1"></i>Print Updated Label
                    </button>
                </div>
            </div>
        </div>
    `;
    return modal;
}

async function printContainerUpdateNow() {
    if (!currentPrintContainer) return;
    
    try {
        const response = await fetch(`/api/print/container/${currentPrintContainer.id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                auto_print: true
            })
        });
        
        const result = await response.json();
        
        // Add to print job queue regardless of result
        const containerData = {
            id: currentPrintContainer.id,
            description: `Container CNT-${currentPrintContainer.id} (${currentPrintContainer.data?.action || 'Updated'})`,
            type: 'container'
        };
        
        let status = 'failed';
        if (result && result.status === 'success') {
            status = 'printed';
            showSuccessMessage('Container label printed successfully!');
        } else if (result && result.status === 'warning') {
            status = 'queued'; // Printer not available, but can retry later
            showSuccessMessage('Container label queued for printing.');
        } else {
            status = 'queued'; // Failed but can retry
            showSuccessMessage('Container label added to print queue.');
        }
        
        // Add to print job queue
        addContainerPrintJob(containerData, status);
        
        // Hide modal and reload page
        bootstrap.Modal.getInstance(document.getElementById('containerUpdatePrintModal')).hide();
        currentPrintContainer = null;
        
        // Reload page to show updated container
        setTimeout(() => {
            window.location.reload();
        }, 1000);
        
    } catch (error) {
        console.error('Print error:', error);
        
        // Add to print job queue as failed/queued
        const containerData = {
            id: currentPrintContainer.id,
            description: `Container CNT-${currentPrintContainer.id} (${currentPrintContainer.data?.action || 'Updated'})`,
            type: 'container'
        };
        addContainerPrintJob(containerData, 'queued');
        
        showSuccessMessage('Container label added to print queue due to printer issues.');
        
        // Hide modal and reload page
        bootstrap.Modal.getInstance(document.getElementById('containerUpdatePrintModal')).hide();
        currentPrintContainer = null;
        
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }
}

function skipContainerUpdatePrint() {
    // Add to print job queue when skipping
    if (currentPrintContainer) {
        const containerData = {
            id: currentPrintContainer.id,
            description: `Container CNT-${currentPrintContainer.id} (${currentPrintContainer.data?.action || 'Updated'})`,
            type: 'container'
        };
        addContainerPrintJob(containerData, 'queued');
        showSuccessMessage('Container label added to print queue.');
    }
    
    // Hide modal and reload page
    bootstrap.Modal.getInstance(document.getElementById('containerUpdatePrintModal')).hide();
    currentPrintContainer = null;
    
    // Reload page to show updated container
    setTimeout(() => {
        window.location.reload();
    }, 1000);
}

// Function to add container print job to queue
function addContainerPrintJob(containerData, status) {
    try {
        let printJobs = JSON.parse(localStorage.getItem('printJobs') || '[]');
        
        const printJob = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            containerId: containerData.id,
            containerIdFormatted: `CNT-${containerData.id}`,
            // For compatibility with scanner page - use container data as sample data
            sampleId: containerData.id,
            sampleIdFormatted: `CNT-${containerData.id}`,
            barcode: `CNT-${containerData.id}`,
            description: containerData.description,
            type: 'container',
            status: status // 'queued', 'printed', 'failed'
        };
        
        printJobs.unshift(printJob); // Add to beginning
        
        // Keep only last 50 jobs
        if (printJobs.length > 50) {
            printJobs = printJobs.slice(0, 50);
        }
        
        localStorage.setItem('printJobs', JSON.stringify(printJobs));
        console.log('Container print job added to queue:', printJob);
        
    } catch (error) {
        console.error('Error adding container print job to queue:', error);
    }
}

// Make container print functions globally available for other scripts
window.showContainerPrintPrompt = showContainerPrintPrompt;
window.showContainerUpdatePrintPrompt = showContainerUpdatePrintPrompt;