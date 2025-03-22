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
        body: JSON.stringify(data)
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
    const description = document.getElementById('containerDescription').value;
    const typeId = document.getElementById('containerType').value;
    const capacity = document.getElementById('containerCapacity').value;
    const isMixed = document.getElementById('containerIsMixed').checked;
    
    // Validation
    if (!description) {
        showErrorMessage('Please enter a description for the container');
        return;
    }
    
    // Debug log
    console.log('Creating container with data:', {
        description,
        typeId: typeId || 'null',
        capacity: capacity || 'null',
        isMixed
    });
    
    // Create container object
    const containerData = {
        description: description,
        containerTypeId: typeId || null,
        capacity: capacity || null,
        isMixed: isMixed
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
            showErrorMessage(`Error during creation: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error creating container:', error);
        showErrorMessage(`An error occurred: ${error}`);
    });
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