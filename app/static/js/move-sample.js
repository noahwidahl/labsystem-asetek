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
                
                // Sort containers by ID (descending to show newest first)
                const sortedContainers = [...data.containers].sort((a, b) => b.ContainerID - a.ContainerID);
                
                sortedContainers.forEach(container => {
                    const option = document.createElement('option');
                    option.value = container.ContainerID;
                    
                    // Create a more informative description
                    let containerDesc = `${container.ContainerID}: ${container.Description || 'Container'}`;
                    
                    // Add type and capacity info if available
                    if (container.TypeName) {
                        containerDesc += ` (${container.TypeName})`;
                    }
                    
                    // Add location if available
                    if (container.LocationName) {
                        containerDesc += ` - Location: ${container.LocationName}`;
                    }
                    
                    // Add capacity information if available
                    if (container.ContainerCapacity) {
                        const currentAmount = container.CurrentAmount || 0;
                        containerDesc += ` - ${currentAmount}/${container.ContainerCapacity}`;
                    }
                    
                    option.textContent = containerDesc;
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
    fetch('/api/basic-locations')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.locations) {
                const locationSelect = document.getElementById('moveLocationSelect');
                locationSelect.innerHTML = '<option value="">-- Select Location --</option>';
                
                // Sort locations by name (assuming format like 1.1.1)
                const sortedLocations = [...data.locations].sort((a, b) => {
                    // Parse location names into components
                    const partsA = a.LocationName.split('.').map(Number);
                    const partsB = b.LocationName.split('.').map(Number);
                    
                    // Compare each component
                    for (let i = 0; i < Math.min(partsA.length, partsB.length); i++) {
                        if (partsA[i] !== partsB[i]) {
                            return partsA[i] - partsB[i];
                        }
                    }
                    return partsA.length - partsB.length;
                });
                
                sortedLocations.forEach(location => {
                    const option = document.createElement('option');
                    option.value = location.LocationID;
                    option.textContent = location.LocationName;
                    locationSelect.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('Error fetching locations for move:', error);
            const locationSelect = document.getElementById('moveLocationSelect');
            locationSelect.innerHTML = '<option value="">Error loading locations</option>';
        });
}

// Function to execute the sample move
function executeMoveSample() {
    const sampleId = document.getElementById('moveSampleId').value;
    const moveType = document.querySelector('input[name="moveType"]:checked').value;
    
    let requestData = {
        sampleId: sampleId
    };
    
    // Get amount to move (used for both container and location)
    const amount = parseInt(document.getElementById('moveAmount').value, 10);
    if (isNaN(amount) || amount < 1) {
        showErrorMessage('Amount must be at least 1');
        return;
    }
    
    // Based on move type, prepare different request data
    if (moveType === 'container') {
        const containerId = document.getElementById('moveContainerSelect').value;
        
        if (!containerId) {
            showErrorMessage('Please select a container');
            return;
        }
        
        if (containerId === 'none') {
            // Remove from container - special case
            requestData.removeFromContainer = true;
        } else {
            // Normal container move
            requestData.containerId = parseInt(containerId, 10);
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
        
        requestData.locationId = parseInt(locationId, 10);
        requestData.amount = amount; // Also send amount for location moves
        
        // Send to location move endpoint
        moveToLocation(requestData);
    }
}

// Function to move a sample to a container
function moveToContainer(data) {
    // First validate unit type compatibility if moving to a container with existing samples
    if (!data.removeFromContainer && data.containerId) {
        validateUnitTypeForContainerMove(data.sampleId, data.containerId, () => {
            executeContainerMove(data);
        });
    } else {
        executeContainerMove(data);
    }
}

// Function to validate unit type compatibility
function validateUnitTypeForContainerMove(sampleId, containerId, callback) {
    // First get the sample's unit type
    fetch(`/api/samples/${sampleId}`)
        .then(response => response.json())
        .then(sampleData => {
            if (!sampleData.success) {
                throw new Error('Could not fetch sample data');
            }
            
            const sampleUnit = sampleData.sample.Unit || 'pcs';
            
            // Then get container's existing samples and their unit types
            fetch(`/api/containers/${containerId}`)
                .then(response => response.json())
                .then(containerData => {
                    if (!containerData.success) {
                        throw new Error('Could not fetch container data');
                    }
                    
                    // Check if container has existing samples with different unit types
                    const existingSamples = containerData.samples || [];
                    const incompatibleUnits = existingSamples.filter(sample => 
                        sample.Unit && sample.Unit !== sampleUnit
                    );
                    
                    if (incompatibleUnits.length > 0) {
                        const existingUnits = [...new Set(incompatibleUnits.map(s => s.Unit))];
                        showErrorMessage(`Cannot move sample with unit "${sampleUnit}" to container with existing samples using units: ${existingUnits.join(', ')}. All samples in a container must use the same unit type.`);
                        return;
                    }
                    
                    // If validation passed, execute the move
                    callback();
                })
                .catch(error => {
                    console.error('Error validating container units:', error);
                    showErrorMessage('Error validating unit compatibility. Please try again.');
                });
        })
        .catch(error => {
            console.error('Error validating sample unit:', error);
            showErrorMessage('Error validating sample unit. Please try again.');
        });
}

// Actual function to execute container move
function executeContainerMove(data) {
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
        console.log('🖨️ Move response received:', responseData);
        if (responseData.success) {
            showSuccessMessage('Sample moved successfully');
            
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('moveSampleModal'));
            if (modal) {
                modal.hide();
            }
            
            // Handle printing based on move type
            const originalContainerId = responseData.original_container_id;
            const newContainerId = data.containerId;
            console.log('🖨️ Container IDs - Original:', originalContainerId, 'New:', newContainerId, 'Original has samples:', responseData.original_container_has_samples);
            
            // Show print prompts for affected containers
            if (originalContainerId && newContainerId && originalContainerId !== newContainerId) {
                // Sample moved from one container to another - show combined prompt for both
                console.log('🖨️ Container-to-container move detected:', {originalContainerId, newContainerId, original_has_samples: responseData.original_container_has_samples});
                
                // Show combined prompt for both containers
                if (typeof showCombinedContainerPrintPrompt === 'function') {
                    const originalStatus = responseData.original_container_has_samples ? 'updated' : 'now empty';
                    showCombinedContainerPrintPrompt({
                        sourceContainerId: originalContainerId,
                        sourceStatus: originalStatus,
                        destinationContainerId: newContainerId,
                        destinationStatus: 'updated',
                        sampleId: data.sampleId
                    });
                } else {
                    // Fallback to old approach
                    const printQueue = [];
                    
                    printQueue.push(() => {
                        console.log('🖨️ Showing new container prompt for', newContainerId);
                        showContainerUpdatePrintPrompt(newContainerId, {
                            description: `New container after adding sample`,
                            action: 'Sample added to container'
                        });
                    });
                    
                    if (originalContainerId) {
                        printQueue.push(() => {
                            console.log('🖨️ Showing original container prompt for', originalContainerId);
                            const containerStatus = responseData.original_container_has_samples ? 'updated' : 'now empty';
                            showContainerUpdatePrintPrompt(originalContainerId, {
                                description: `Original container after sample removal (${containerStatus})`,
                                action: 'Sample removed from container'
                            });
                        });
                    }
                    
                    executePrintQueue(printQueue);
                }
            } else if (newContainerId && !data.removeFromContainer) {
                // Sample moved to container from direct storage - show new container prompt
                if (typeof showContainerUpdatePrintPrompt === 'function') {
                    showContainerUpdatePrintPrompt(newContainerId, {
                        description: `Container after moving sample`,
                        action: 'Sample moved to container'
                    });
                } else {
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                }
            } else if (originalContainerId && data.removeFromContainer) {
                // Sample removed from container to direct storage - show both container and sample prompts
                if (typeof showContainerUpdatePrintPrompt === 'function') {
                    // Create a queue of print prompts to show in sequence
                    const printQueue = [];
                    
                    // Always show container prompt (whether empty or not)
                    if (originalContainerId) {
                        printQueue.push(() => {
                            const containerStatus = responseData.original_container_has_samples ? 'updated' : 'now empty';
                            showContainerUpdatePrintPrompt(originalContainerId, {
                                description: `Container after sample removal (${containerStatus})`,
                                action: 'Sample removed from container'
                            });
                        });
                    }
                    
                    // Then show sample prompt for the moved sample (now in direct storage)
                    printQueue.push(() => {
                        if (typeof showSampleLocationPrintPrompt === 'function') {
                            showSampleLocationPrintPrompt(data.sampleId, {
                                description: `Sample moved to direct storage`,
                                action: 'Sample moved to location'
                            });
                        }
                    });
                    
                    // Execute print queue with proper delays
                    executePrintQueue(printQueue);
                } else {
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                }
            } else {
                // Direct location move - just reload
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            }
        } else {
            showErrorMessage(`Error moving sample: ${responseData.error}`);
        }
    })
    .catch(error => {
        console.error('Error in move sample request:', error);
        showErrorMessage('An error occurred while moving the sample');
    });
}

// Function to execute print prompts in sequence, avoiding modal conflicts
function executePrintQueue(printQueue) {
    console.log('🖨️ executePrintQueue called with', printQueue.length, 'items');
    if (printQueue.length === 0) {
        return;
    }
    
    let currentIndex = 0;
    
    function showNextPrompt() {
        if (currentIndex >= printQueue.length) {
            return;
        }
        
        const currentPrompt = printQueue[currentIndex];
        currentIndex++;
        
        // Execute the current prompt
        console.log('🖨️ Executing prompt', currentIndex, 'of', printQueue.length);
        currentPrompt();
        
        // Wait for modal to appear then listen for its close event
        setTimeout(() => {
            const printModals = document.querySelectorAll('#containerUpdatePrintModal, #sampleLocationPrintModal, #containerPrintConfirmModal, [id*="Print"]');
            console.log('🖨️ Found print modals:', Array.from(printModals).map(m => m.id));
            
            if (printModals.length > 0) {
                // Listen for any of the print modals to close
                printModals.forEach(modal => {
                    const handleModalClose = (event) => {
                        console.log('🖨️ Modal closed:', modal.id);
                        modal.removeEventListener('hidden.bs.modal', handleModalClose);
                        
                        // Wait a bit then show next prompt
                        setTimeout(() => {
                            showNextPrompt();
                        }, 500);
                    };
                    
                    modal.addEventListener('hidden.bs.modal', handleModalClose, { once: true });
                });
            } else {
                // No modal found, continue immediately
                console.log('🖨️ No modal found, continuing immediately');
                setTimeout(() => {
                    showNextPrompt();
                }, 500);
            }
        }, 200);
    }
    
    // Start showing prompts
    showNextPrompt();
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
            
            // Show sample print prompt for location move
            showSampleLocationPrintPrompt(data.sampleId, {
                description: `Sample moved to new location`,
                action: 'Location updated'
            });
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

// Print functionality is now handled by global print-functions.js
// Functions showSampleLocationPrintPrompt, addSamplePrintJob, etc. are available globally