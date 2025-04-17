// app/static/js/move-sample.js
document.addEventListener('DOMContentLoaded', function() {
    console.log('Move sample functionality initialized');
    
    // Set up event handler for the move sample button in the sample details modal
    const moveSampleBtn = document.getElementById('move-sample-btn');
    if (moveSampleBtn) {
        moveSampleBtn.addEventListener('click', function() {
            prepareMoveModal('modal');
        });
    }
    
    // Set up event handlers for move buttons in the sample table
    document.querySelectorAll('.sample-move-btn').forEach(button => {
        button.addEventListener('click', function() {
            const sampleId = this.dataset.sampleId;
            if (sampleId) {
                prepareMoveModal('table', sampleId);
            }
        });
    });
    
    // Set up event handlers for radio buttons in the move modal
    const moveToContainer = document.getElementById('moveToContainer');
    const moveToLocation = document.getElementById('moveToLocation');
    const containerSelectionGroup = document.getElementById('containerSelectionGroup');
    const locationSelectionGroup = document.getElementById('locationSelectionGroup');
    
    if (moveToContainer && moveToLocation) {
        moveToContainer.addEventListener('change', function() {
            containerSelectionGroup.style.display = this.checked ? 'block' : 'none';
            locationSelectionGroup.style.display = this.checked ? 'none' : 'block';
        });
        
        moveToLocation.addEventListener('change', function() {
            containerSelectionGroup.style.display = this.checked ? 'none' : 'block';
            locationSelectionGroup.style.display = this.checked ? 'block' : 'none';
        });
    }
    
    // Set up event handler for the confirm move button
    const confirmMoveBtn = document.getElementById('confirmMoveBtn');
    if (confirmMoveBtn) {
        confirmMoveBtn.addEventListener('click', function() {
            executeMoveSample();
        });
    }
});

// Function to prepare the move modal with sample data
function prepareMoveModal(source, sampleId) {
    const moveModal = document.getElementById('moveSampleModal');
    
    if (!moveModal) {
        console.error('Move sample modal not found');
        return;
    }
    
    if (source === 'modal') {
        // Called from sample details modal
        sampleId = document.getElementById('sample-id').textContent;
        if (sampleId.startsWith('SMP-')) {
            sampleId = sampleId.replace('SMP-', '');
        }
        
        // Set the sample name and info
        const sampleDescription = document.getElementById('sample-description').textContent;
        const samplePartNumber = document.getElementById('sample-part-number').textContent;
        const sampleAmount = document.getElementById('sample-amount').textContent;
        const sampleIdFormatted = document.getElementById('sample-id').textContent;
        
        document.getElementById('moveSampleName').textContent = `${sampleIdFormatted}: ${sampleDescription}`;
        document.getElementById('moveSampleInfo').textContent = `Part Number: ${samplePartNumber}, Quantity: ${sampleAmount}`;
        
        // Close the sample details modal
        const sampleDetailsModal = bootstrap.Modal.getInstance(document.getElementById('sampleDetailsModal'));
        if (sampleDetailsModal) {
            sampleDetailsModal.hide();
        }
    } else {
        // Called from table - need to fetch sample details first
        fetchSampleDataForMove(sampleId);
    }
    
    // Set the sample ID in the hidden input
    document.getElementById('moveSampleId').value = sampleId;
    
    // Fetch available containers and locations
    fetchContainersForMove();
    fetchLocationsForMove();
    
    // Show the move modal
    const modal = new bootstrap.Modal(moveModal);
    modal.show();
}

// Function to fetch sample data for the move modal
function fetchSampleDataForMove(sampleId) {
    fetch(`/api/samples/${sampleId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.sample) {
                const sample = data.sample;
                const sampleIdFormatted = `SMP-${sample.SampleID || sampleId}`;
                
                // Set the sample name and info
                document.getElementById('moveSampleName').textContent = `${sampleIdFormatted}: ${sample.Description || '-'}`;
                document.getElementById('moveSampleInfo').textContent = 
                    `Part Number: ${sample.PartNumber || '-'}, Quantity: ${sample.Amount || '-'} ${sample.Unit || 'pcs'}`;
            } else {
                document.getElementById('moveSampleName').textContent = `SMP-${sampleId}`;
                document.getElementById('moveSampleInfo').textContent = 'Details not available';
            }
        })
        .catch(error => {
            console.error('Error fetching sample data for move:', error);
            document.getElementById('moveSampleName').textContent = `SMP-${sampleId}`;
            document.getElementById('moveSampleInfo').textContent = 'Error loading details';
        });
}

// Function to fetch containers for the move modal
function fetchContainersForMove() {
    fetch('/api/containers/available')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.containers) {
                const containerSelect = document.getElementById('moveContainerSelect');
                containerSelect.innerHTML = '<option value="">-- Select Container --</option><option value="none">No Container</option>';
                
                data.containers.forEach(container => {
                    const option = document.createElement('option');
                    option.value = container.ContainerID;
                    option.textContent = `${container.ContainerID}: ${container.Description || 'Container'} - ${container.TypeName || 'Standard'}`;
                    containerSelect.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('Error fetching containers for move:', error);
            const containerSelect = document.getElementById('moveContainerSelect');
            containerSelect.innerHTML = '<option value="">Error loading containers</option>';
        });
}

// Function to fetch locations for the move modal
function fetchLocationsForMove() {
    fetch('/api/locations')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.locations) {
                const locationSelect = document.getElementById('moveLocationSelect');
                locationSelect.innerHTML = '<option value="">-- Select Location --</option>';
                
                data.locations.forEach(location => {
                    const option = document.createElement('option');
                    option.value = location.LocationID;
                    option.textContent = `${location.LocationName}: ${location.LabName || 'Lab'}`;
                    locationSelect.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('Error fetching locations for move:', error);
            const locationSelect = document.getElementById('moveLocationSelect');
            locationSelect.innerHTML = '<option value="">Error loading locations</option>';
            
            // Fallback: try to fetch minimal location data
            fetch('/api/basic-locations')
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.locations) {
                        locationSelect.innerHTML = '<option value="">-- Select Location --</option>';
                        data.locations.forEach(location => {
                            const option = document.createElement('option');
                            option.value = location.LocationID;
                            option.textContent = location.LocationName;
                            locationSelect.appendChild(option);
                        });
                    }
                })
                .catch(innerError => {
                    console.error('Error fetching basic locations:', innerError);
                });
        });
}

// Function to execute the sample move
function executeMoveSample() {
    const sampleId = document.getElementById('moveSampleId').value;
    const moveType = document.querySelector('input[name="moveType"]:checked').value;
    
    let requestData = {
        sampleId: sampleId
    };
    
    // Based on move type, prepare different request data
    if (moveType === 'container') {
        const containerId = document.getElementById('moveContainerSelect').value;
        const amount = document.getElementById('moveAmount').value;
        
        if (!containerId) {
            showErrorMessage('Please select a container');
            return;
        }
        
        if (amount < 1) {
            showErrorMessage('Amount must be at least 1');
            return;
        }
        
        if (containerId === 'none') {
            // Remove from container - special case
            requestData.removeFromContainer = true;
        } else {
            // Normal container move
            requestData.containerId = containerId;
            requestData.amount = amount;
        }
        
        // Send to container move endpoint
        moveToContainer(requestData);
    } else {
        // Location move
        const locationId = document.getElementById('moveLocationSelect').value;
        
        if (!locationId) {
            showErrorMessage('Please select a location');
            return;
        }
        
        requestData.locationId = locationId;
        
        // Send to location move endpoint
        moveToLocation(requestData);
    }
}

// Function to move a sample to a container
function moveToContainer(data) {
    let apiUrl = '/api/containers/add-sample';
    let requestMethod = 'POST';
    
    if (data.removeFromContainer) {
        // Use a different endpoint for removal
        apiUrl = `/api/samples/${data.sampleId}/remove-from-container`;
        requestMethod = 'POST';
        delete data.removeFromContainer; // Clean up request data
    }
    
    fetch(apiUrl, {
        method: requestMethod,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(responseData => {
        if (responseData.success) {
            showSuccessMessage('Sample moved successfully');
            
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('moveSampleModal'));
            if (modal) {
                modal.hide();
            }
            
            // Reload the page after a short delay
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showErrorMessage(`Error moving sample: ${responseData.error}`);
        }
    })
    .catch(error => {
        console.error('Error in move sample request:', error);
        showErrorMessage('An error occurred while moving the sample');
    });
}

// Function to move a sample to a location
function moveToLocation(data) {
    fetch(`/api/samples/${data.sampleId}/move-location`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(responseData => {
        if (responseData.success) {
            showSuccessMessage('Sample location updated successfully');
            
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('moveSampleModal'));
            if (modal) {
                modal.hide();
            }
            
            // Reload the page after a short delay
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showErrorMessage(`Error updating sample location: ${responseData.error}`);
        }
    })
    .catch(error => {
        console.error('Error in move location request:', error);
        showErrorMessage('An error occurred while updating the sample location');
    });
}

// Message functions for UI feedback
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