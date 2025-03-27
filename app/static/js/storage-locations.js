// Function to update the storage overview on dashboard
function updateStorageOverview(locations) {
    const storageContainer = document.querySelector('.storage-grid');
    if (!storageContainer) return;
    
    storageContainer.innerHTML = '';
    
    // Group locations by rack and section
    const rackSectionMap = {};
    
    locations.forEach(location => {
        let rackNum, sectionNum, shelfNum;
        
        // Extract rack, section, shelf numbers
        if (location.Reol !== undefined && location.Sektion !== undefined && location.Hylde !== undefined) {
            rackNum = location.Reol;
            sectionNum = location.Sektion;
            shelfNum = location.Hylde;
        } else {
            const parts = location.LocationName.split('.');
            if (parts.length === 3) {
                [rackNum, sectionNum, shelfNum] = parts;
            } else {
                console.warn("Unknown location format:", location.LocationName);
                return;
            }
        }
        
        // Create rack entry if it doesn't exist
        if (!rackSectionMap[rackNum]) {
            rackSectionMap[rackNum] = {};
        }
        
        // Create section entry if it doesn't exist
        if (!rackSectionMap[rackNum][sectionNum]) {
            rackSectionMap[rackNum][sectionNum] = [];
        }
        
        // Add location to its section
        rackSectionMap[rackNum][sectionNum].push({
            ...location,
            shelfNum: parseInt(shelfNum)
        });
    });
    
    // Create rack sections in order
    Object.keys(rackSectionMap).sort((a, b) => parseInt(a) - parseInt(b)).forEach(rackNum => {
        const rackDiv = document.createElement('div');
        rackDiv.className = 'rack-container card mb-4';
        
        const rackHeader = document.createElement('div');
        rackHeader.className = 'card-header d-flex justify-content-between align-items-center';
        rackHeader.innerHTML = `
            <h5 class="mb-0">Rack ${rackNum}</h5>
            <div class="rack-controls">
                <button class="btn btn-sm btn-outline-secondary me-2" onclick="toggleRackView(${rackNum})">
                    <i class="fas fa-chevron-down" id="rack-toggle-${rackNum}"></i>
                </button>
                <button class="btn btn-sm btn-outline-primary" onclick="addSection(${rackNum})">
                    <i class="fas fa-plus"></i> Add Section
                </button>
            </div>
        `;
        rackDiv.appendChild(rackHeader);
        
        const rackBody = document.createElement('div');
        rackBody.className = 'card-body p-3';
        rackBody.id = `rack-body-${rackNum}`;
        
        const sectionsContainer = document.createElement('div');
        sectionsContainer.className = 'sections-container row g-3';
        
        // Get sections for this rack
        const sections = rackSectionMap[rackNum];
        
        // Create section cards in order
        Object.keys(sections).sort((a, b) => parseInt(a) - parseInt(b)).forEach(sectionNum => {
            const sectionCol = document.createElement('div');
            sectionCol.className = 'col-md-6 col-lg-4';
            sectionCol.id = `section-${rackNum}-${sectionNum}`;
            
            const sectionCard = document.createElement('div');
            sectionCard.className = 'section-card card h-100';
            
            const sectionHeader = document.createElement('div');
            sectionHeader.className = 'card-header d-flex justify-content-between align-items-center py-2';
            sectionHeader.innerHTML = `
                <h6 class="mb-0">Section ${sectionNum}</h6>
                <div class="section-controls">
                    <button class="btn btn-sm btn-outline-danger" onclick="removeSection(${rackNum}, ${sectionNum})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            sectionCard.appendChild(sectionHeader);
            
            const sectionBody = document.createElement('div');
            sectionBody.className = 'card-body p-0';
            
            const shelvesList = document.createElement('ul');
            shelvesList.className = 'list-group list-group-flush';
            
            // Sort locations by shelf number
            const sortedLocations = sections[sectionNum].sort((a, b) => a.shelfNum - b.shelfNum);
            
            // Create shelf items (always 5 shelves per section)
            for (let shelf = 1; shelf <= 5; shelf++) {
                const shelfLocation = sortedLocations.find(loc => loc.shelfNum === shelf);
                
                const shelfItem = document.createElement('li');
                shelfItem.className = 'list-group-item d-flex justify-content-between align-items-center py-2';
                
                const locationName = document.createElement('div');
                locationName.className = 'fw-bold';
                locationName.textContent = `${rackNum}.${sectionNum}.${shelf}`;
                
                const sampleCount = document.createElement('div');
                
                if (shelfLocation) {
                    const count = shelfLocation.count || 0;
                    sampleCount.className = count > 0 ? 'badge bg-primary' : 'badge bg-light text-dark';
                    sampleCount.textContent = count > 0 ? `${count} samples` : 'Empty';
                } else {
                    sampleCount.className = 'badge bg-light text-dark';
                    sampleCount.textContent = 'Empty';
                }
                
                shelfItem.appendChild(locationName);
                shelfItem.appendChild(sampleCount);
                shelvesList.appendChild(shelfItem);
            }
            
            sectionBody.appendChild(shelvesList);
            sectionCard.appendChild(sectionBody);
            sectionCol.appendChild(sectionCard);
            sectionsContainer.appendChild(sectionCol);
        });
        
        rackBody.appendChild(sectionsContainer);
        rackDiv.appendChild(rackBody);
        storageContainer.appendChild(rackDiv);
    });
    
    // Add admin controls if user is admin
    addAdminControls();
}

// Toggle rack view (expand/collapse)
function toggleRackView(rackNum) {
    const rackBody = document.getElementById(`rack-body-${rackNum}`);
    const toggleIcon = document.getElementById(`rack-toggle-${rackNum}`);
    
    if (rackBody.style.display === 'none') {
        rackBody.style.display = 'block';
        toggleIcon.className = 'fas fa-chevron-down';
    } else {
        rackBody.style.display = 'none';
        toggleIcon.className = 'fas fa-chevron-right';
    }
}

// Admin function to add section to a rack
function addSection(rackNum) {
    // Check if user is admin
    if (!isUserAdmin()) {
        showErrorMessage('Only administrators can add rack sections');
        return;
    }
    
    // Get existing sections for this rack
    const existingSections = document.querySelectorAll(`[id^="section-${rackNum}-"]`);
    const sectionNumbers = Array.from(existingSections).map(section => {
        const id = section.id;
        const parts = id.split('-');
        return parseInt(parts[2]);
    });
    
    // Find next available section number
    let newSectionNum = 1;
    while (sectionNumbers.includes(newSectionNum)) {
        newSectionNum++;
    }
    
    // Check if we've reached the maximum number of sections (6)
    if (newSectionNum > 6) {
        showErrorMessage('Maximum number of sections (6) reached for this rack');
        return;
    }
    
    // Call API to add section
    fetch('/api/storage/add-section', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            rackNum: rackNum,
            sectionNum: newSectionNum
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage(`Section ${newSectionNum} added to Rack ${rackNum}`);
            
            // Refresh the storage display
            loadStorageLocations();
        } else {
            showErrorMessage(`Failed to add section: ${data.error}`);
        }
    })
    .catch(error => {
        showErrorMessage(`Error: ${error.message}`);
    });
}

// Admin function to remove section from a rack
function removeSection(rackNum, sectionNum) {
    // Check if user is admin
    if (!isUserAdmin()) {
        showErrorMessage('Only administrators can remove rack sections');
        return;
    }
    
    // Confirm deletion
    if (!confirm(`Are you sure you want to remove Section ${sectionNum} from Rack ${rackNum}? This will delete all shelf locations in this section.`)) {
        return;
    }
    
    // Check if section has samples
    const section = document.getElementById(`section-${rackNum}-${sectionNum}`);
    const sampleBadges = section.querySelectorAll('.badge.bg-primary');
    
    if (sampleBadges.length > 0) {
        if (!confirm(`Warning: This section contains samples. Removing it will make these samples inaccessible. Continue?`)) {
            return;
        }
    }
    
    // Call API to remove section
    fetch('/api/storage/remove-section', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            rackNum: rackNum,
            sectionNum: sectionNum
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage(`Section ${sectionNum} removed from Rack ${rackNum}`);
            
            // Remove the section from the UI
            section.remove();
        } else {
            showErrorMessage(`Failed to remove section: ${data.error}`);
        }
    })
    .catch(error => {
        showErrorMessage(`Error: ${error.message}`);
    });
}

// Check if current user is admin
function isUserAdmin() {
    // This would normally check the user's role from the session
    // For this example, we'll return true
    return true;
}

// Add admin controls if user is admin
function addAdminControls() {
    if (!isUserAdmin()) return;
    
    const storageContainer = document.querySelector('.storage-grid');
    if (!storageContainer) return;
    
    // Check if admin controls already exist
    if (document.getElementById('storage-admin-controls')) return;
    
    // Create admin controls
    const adminControls = document.createElement('div');
    adminControls.id = 'storage-admin-controls';
    adminControls.className = 'admin-controls card mb-4';
    
    adminControls.innerHTML = `
        <div class="card-header bg-dark text-white">
            <h5 class="mb-0">Administrator Controls</h5>
        </div>
        <div class="card-body">
            <div class="row">
                <div class="col-md-6">
                    <div class="form-group mb-3">
                        <label for="new-rack-number">New Rack Number</label>
                        <input type="number" id="new-rack-number" class="form-control" min="1" max="50">
                    </div>
                </div>
                <div class="col-md-6 d-flex align-items-end">
                    <button class="btn btn-primary" onclick="addRack()">
                        <i class="fas fa-plus"></i> Add New Rack
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Insert at the beginning of the container
    storageContainer.insertBefore(adminControls, storageContainer.firstChild);
}

// Admin function to add a new rack
function addRack() {
    const rackNumberInput = document.getElementById('new-rack-number');
    const rackNum = parseInt(rackNumberInput.value);
    
    if (!rackNum || rackNum < 1) {
        showErrorMessage('Please enter a valid rack number');
        return;
    }
    
    // Check if rack already exists
    if (document.querySelector(`.rack-container:has(h5:contains("Rack ${rackNum}"))`)) {
        showErrorMessage(`Rack ${rackNum} already exists`);
        return;
    }
    
    // Call API to add rack
    fetch('/api/storage/add-rack', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            rackNum: rackNum
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage(`Rack ${rackNum} added successfully`);
            
            // Refresh the storage display
            loadStorageLocations();
            
            // Clear input
            rackNumberInput.value = '';
        } else {
            showErrorMessage(`Failed to add rack: ${data.error}`);
        }
    })
    .catch(error => {
        showErrorMessage(`Error: ${error.message}`);
    });
}

// Load storage locations from API
function loadStorageLocations() {
    fetch('/api/storage-locations')
        .then(response => response.json())
        .then(data => {
            if (data.locations) {
                updateStorageOverview(data.locations);
            } else {
                showErrorMessage('No location data received from server');
                createDefaultStorageStructure();
            }
        })
        .catch(error => {
            console.error('Failed to load storage locations:', error);
            showErrorMessage(`Error loading storage data: ${error.message}`);
            createDefaultStorageStructure();
        });
}

// Create default storage structure for demo
function createDefaultStorageStructure() {
    // Create sample data for 14 racks with varying number of sections
    const defaultLocations = [];
    
    // Create 14 racks
    for (let rack = 1; rack <= 14; rack++) {
        // Each rack has 1-6 sections (random for demo)
        const sectionCount = Math.min(6, Math.max(1, Math.floor(Math.random() * 6) + 1));
        
        for (let section = 1; section <= sectionCount; section++) {
            // Each section has exactly 5 shelves
            for (let shelf = 1; shelf <= 5; shelf++) {
                // Random number of samples (0-10)
                const sampleCount = Math.floor(Math.random() * 11);
                
                defaultLocations.push({
                    LocationID: `${rack}${section}${shelf}`,
                    LocationName: `${rack}.${section}.${shelf}`,
                    Reol: rack,
                    Sektion: section,
                    Hylde: shelf,
                    count: sampleCount
                });
            }
        }
    }
    
    updateStorageOverview(defaultLocations);
}

// Toast message functions
function showSuccessMessage(message) {
    showToast(message, 'success');
}

function showErrorMessage(message) {
    showToast(message, 'danger');
}

function showToast(message, type) {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0 position-fixed top-0 end-0 m-3`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast, {
        delay: 5000
    });
    
    bsToast.show();
    
    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        document.body.removeChild(toast);
    });
}

// Initialize when the dashboard page loads
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname === '/' || window.location.pathname.includes('/dashboard')) {
        loadStorageLocations();
    }
});