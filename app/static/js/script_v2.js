// Initialize when document loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('Script initialized');
    
    setupBasicEventListeners();
    
    // Check which page we're on
    const currentPath = window.location.pathname;
    if (currentPath === '/' || currentPath.includes('/dashboard')) {
        loadStorageLocations();
    } else if (currentPath.includes('/storage')) {
        setupSampleDeleteButtons();
    }
});

// Basic setup for all pages
function setupBasicEventListeners() {
    // Profile modal handler
    const profileBtn = document.querySelector('button[onclick="showProfileModal()"]');
    if (profileBtn) {
        profileBtn.addEventListener('click', showProfileModal);
    }
    
    // Disposal modal handler
    const disposalBtn = document.querySelector('a[onclick="showDisposalModal(event)"]');
    if (disposalBtn) {
        disposalBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showDisposalModal();
        });
    }
}

// Profile Modal function
function showProfileModal() {
    const profileModal = new bootstrap.Modal(document.getElementById('profileModal'));
    profileModal.show();
}

// Disposal Modal function
function showDisposalModal(event) {
    if (event) event.preventDefault();
    const disposalModal = new bootstrap.Modal(document.getElementById('disposalModal'));
    disposalModal.show();
}

// Load storage locations for dashboard
function loadStorageLocations() {
    fetch('/api/storage-locations')
        .then(response => response.json())
        .then(data => {
            if (data.locations) {
                updateStorageGrid(data.locations);
            }
        })
        .catch(error => {
            console.error('Error loading storage locations:', error);
            // Create dummy data as fallback
            createDummyStorageGrid();
        });
}

// Update storage grid with locations
function updateStorageGrid(locations) {
    const grids = document.querySelectorAll('.storage-grid');
    grids.forEach(grid => {
        grid.innerHTML = '';
        
        // Limit to first 12 locations for compact display
        const limitedLocations = locations.slice(0, 12);

        limitedLocations.forEach(location => {
            const cell = document.createElement('div');
            cell.className = 'storage-cell';
            if(location.status === 'occupied') {
                cell.classList.add('bg-light', 'border-primary');
            }

            const locationEl = document.createElement('div');
            locationEl.className = 'fw-bold';
            locationEl.textContent = location.LocationName;

            const capacity = document.createElement('div');
            capacity.className = 'small';
            capacity.textContent = location.status === 'occupied' ? `${location.count}` : 'Available';

            cell.appendChild(locationEl);
            cell.appendChild(capacity);
            grid.appendChild(cell);
        });
    });
}

// Create dummy storage grid as fallback
function createDummyStorageGrid() {
    const grids = document.querySelectorAll('.storage-grid');
    grids.forEach(grid => {
        grid.innerHTML = '';
        
        for (let i = 1; i <= 12; i++) {
            const cell = document.createElement('div');
            cell.className = 'storage-cell';
            if (i % 3 === 0) {
                cell.classList.add('bg-light', 'border-primary');
            }

            const locationEl = document.createElement('div');
            locationEl.className = 'fw-bold';
            locationEl.textContent = `A${Math.ceil(i/4)}.B${i % 4 || 4}`;

            const capacity = document.createElement('div');
            capacity.className = 'small';
            capacity.textContent = i % 3 === 0 ? 'Occupied' : 'Available';

            cell.appendChild(locationEl);
            cell.appendChild(capacity);
            grid.appendChild(cell);
        }
    });
}

// Expiring samples modal
function showExpiringDetails() {
    // This could fetch data from the API in a more complete implementation
    const expiringModal = new bootstrap.Modal(document.getElementById('expiringDetailsModal'));
    expiringModal.show();
}

// Setup delete buttons for samples
function setupSampleDeleteButtons() {
    const deleteButtons = document.querySelectorAll('.delete-sample-btn');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', function() {
            const sampleId = this.getAttribute('data-sample-id');
            deleteSample(sampleId);
        });
    });
}

// Delete sample function
function deleteSample(sampleId) {
    if (!sampleId) return;
    
    if (confirm(`Are you sure you want to delete sample ${sampleId}?`)) {
        fetch(`/api/samples/${sampleId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSuccessMessage('Sample deleted successfully!');
                
                // Remove the row from the table or refresh the page
                const row = this.closest('tr');
                if (row) {
                    row.remove();
                } else {
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                }
            } else {
                showErrorMessage(`Error deleting sample: ${data.error}`);
            }
        })
        .catch(error => {
            showErrorMessage(`An error occurred: ${error}`);
        });
    }
}

// Message display functions
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