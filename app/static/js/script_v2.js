// Initialize when document loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('Script initialized');
    
    setupBasicEventListeners();
    
    // Check which page we're on
    const currentPath = window.location.pathname;
    if (currentPath === '/' || currentPath.includes('/dashboard')) {
        loadStorageLocations();
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
            capacity.textContent = location.status === 'occupied' ? `${location.count}` : 'Ledig';

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
            capacity.textContent = i % 3 === 0 ? 'Optaget' : 'Ledig';

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