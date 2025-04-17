// app/static/js/container-details.js
document.addEventListener('DOMContentLoaded', function() {
    console.log('Container details initialized');
    
    // Initialize the sample select with search functionality
    setupSampleSelect();
    
    // Add event listeners for container detail buttons
    setupContainerDetailButtons();
    
    // Add listener for add sample button in details modal
    const addSampleBtn = document.getElementById('add-sample-to-container-btn');
    if (addSampleBtn) {
        addSampleBtn.addEventListener('click', function() {
            // Get container ID from the modal
            const containerId = document.getElementById('container-id').textContent;
            if (containerId && containerId !== '-') {
                // Set the container ID in the add sample modal
                document.getElementById('targetContainerId').value = containerId;
                // Hide the details modal
                const detailsModal = bootstrap.Modal.getInstance(document.getElementById('containerDetailsModal'));
                if (detailsModal) detailsModal.hide();
                // Show the add sample modal
                const addSampleModal = new bootstrap.Modal(document.getElementById('addSampleToContainerModal'));
                addSampleModal.show();
            }
        });
    }
});

function setupContainerDetailButtons() {
    // Add event listener for the "Details" button on container rows
    document.querySelectorAll('button.btn-secondary').forEach(button => {
        button.addEventListener('click', function() {
            const containerId = this.closest('tr').dataset.containerId;
            if (containerId) {
                loadContainerDetails(containerId);
                const modal = new bootstrap.Modal(document.getElementById('containerDetailsModal'));
                modal.show();
            }
        });
    });
}

function loadContainerDetails(containerId) {
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
    
    // Fetch container details
    fetch(`/api/containers/${containerId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.container) {
                const container = data.container;
                
                // Update container information
                document.getElementById('container-id').textContent = container.ContainerID;
                document.getElementById('container-description').textContent = container.Description || '-';
                document.getElementById('container-type').textContent = container.TypeName || 'Standard';
                document.getElementById('container-status').innerHTML = `<span class="badge bg-primary">${container.Status || 'Active'}</span>`;
                document.getElementById('container-mixed').textContent = container.IsMixed ? 'Yes' : 'No';
                
                // Fetch and display location
                fetch(`/api/containers/${containerId}/location`)
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
                
                // Display samples
                if (data.samples && data.samples.length > 0) {
                    let samplesHtml = '<ul class="list-group">';
                    data.samples.forEach(sample => {
                        samplesHtml += `
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>${sample.SampleID || `SMP-${sample.SampleID}`}</strong>: ${sample.Description || '-'}
                                    ${sample.LocationName ? `<div class="text-muted small">Location: ${sample.LocationName}</div>` : ''}
                                </div>
                                <span class="badge bg-primary rounded-pill">${sample.Amount || 1}</span>
                            </li>
                        `;
                    });
                    samplesHtml += '</ul>';
                    document.getElementById('container-samples-list').innerHTML = samplesHtml;
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
                        historyHtml += `
                            <tr>
                                <td>${item.Timestamp || '-'}</td>
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

function setupSampleSelect() {
    const sampleSelect = document.getElementById('sampleSelect');
    if (!sampleSelect) return;
    
    // Optionally add search functionality for sample selection
    // This could use a library like select2
}

// Add sample to container
function addSampleToContainer(forceAdd = false) {
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
    
    // If forceAdd is true, add that to the request
    if (forceAdd) {
        data.force_add = true;
    }
    
    // Send to server
    fetch('/api/containers/add-sample', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage('Sample moved to container successfully!');
            
            // Check if there's a capacity warning
            if (data.capacity_warning) {
                showWarningMessage('Container capacity has been exceeded but sample was added anyway.');
            }
            
            // Close modal and reload page
            const modal = bootstrap.Modal.getInstance(document.getElementById('addSampleToContainerModal'));
            if (modal) modal.hide();
            
            setTimeout(() => {
                window.location.reload();
            }, 1500);  // Give a bit more time to see the messages
        } else if (data.warning && data.capacity_exceeded) {
            // Show capacity warning and ask if user wants to continue
            showCapacityWarningConfirm(
                data.error, 
                data.current_amount, 
                data.new_amount, 
                data.capacity,
                () => {
                    // User clicked 'Yes', force add the sample
                    addSampleToContainer(true);
                }
            );
        } else {
            showErrorMessage(`Error adding sample: ${data.error}`);
        }
    })
    .catch(error => {
        showErrorMessage(`An error occurred: ${error}`);
    });
}

// Function to show capacity warning with confirmation
function showCapacityWarningConfirm(message, currentAmount, newAmount, capacity, onConfirm) {
    // Create a modal for confirmation
    const confirmModal = document.createElement('div');
    confirmModal.className = 'modal fade';
    confirmModal.id = 'capacityWarningModal';
    confirmModal.setAttribute('tabindex', '-1');
    confirmModal.setAttribute('aria-hidden', 'true');
    
    confirmModal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header bg-warning">
                    <h5 class="modal-title">Container Capacity Warning</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle"></i> ${message}
                    </div>
                    <div class="progress mb-3">
                        <div class="progress-bar bg-warning" role="progressbar" style="width: ${(newAmount / capacity) * 100}%"></div>
                    </div>
                    <div class="d-flex justify-content-between mb-3">
                        <span>Current: ${currentAmount}</span>
                        <span>New: ${newAmount}</span>
                        <span>Capacity: ${capacity}</span>
                    </div>
                    <p>Do you want to continue adding the sample anyway?</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-warning" id="confirmExceedCapacity">Yes, add anyway</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(confirmModal);
    
    // Initialize the modal
    const modal = new bootstrap.Modal(confirmModal);
    modal.show();
    
    // Add event listener to confirm button
    document.getElementById('confirmExceedCapacity').addEventListener('click', function() {
        modal.hide();
        
        // Call the callback
        if (typeof onConfirm === 'function') {
            onConfirm();
        }
        
        // Remove the modal from DOM after it's hidden
        confirmModal.addEventListener('hidden.bs.modal', function() {
            confirmModal.remove();
        });
    });
    
    // Ensure modal is removed when closed
    confirmModal.addEventListener('hidden.bs.modal', function() {
        setTimeout(() => {
            if (document.body.contains(confirmModal)) {
                confirmModal.remove();
            }
        }, 300);
    });
}
}

// Remove sample from container
function removeSampleFromContainer(containerId, sampleId, amount) {
    if (confirm('Are you sure you want to remove this sample from the container?')) {
        // Create data object
        const data = {
            containerId: containerId,
            sampleId: sampleId,
            amount: amount || 1
        };
        
        // Send to server
        fetch('/api/containers/remove-sample', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSuccessMessage('Sample removed from container!');
                
                // Reload page
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showErrorMessage(`Error removing sample: ${data.error}`);
            }
        })
        .catch(error => {
            showErrorMessage(`An error occurred: ${error}`);
        });
    }
}

// Helper functions for message display
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

    // Add 'show' class after a short delay (for animation effect)
    setTimeout(() => successToast.classList.add('show'), 10);

    // Remove automatically after 3 seconds
    setTimeout(() => {
        successToast.classList.remove('show');
        setTimeout(() => successToast.remove(), 300);
    }, 3000);
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

function showErrorMessage(message) {
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
}