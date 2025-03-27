// Function to update the storage overview on dashboard
function updateStorageOverview(locations) {
    const storageContainer = document.querySelector('.storage-grid');
    if (!storageContainer) return;
    
    storageContainer.innerHTML = '';
    
    // Group locations by rack
    const locationsByRack = {};
    locations.forEach(location => {
        // Extract rack number from location name (format: rack.section.shelf)
        let rackNum;
        if (location.Reol !== undefined) {
            rackNum = location.Reol;
        } else {
            const parts = location.LocationName.split('.');
            rackNum = parts[0];
        }
        
        if (!locationsByRack[rackNum]) {
            locationsByRack[rackNum] = [];
        }
        
        locationsByRack[rackNum].push(location);
    });
    
    // Create rack sections in order
    Object.keys(locationsByRack).sort((a, b) => parseInt(a) - parseInt(b)).forEach(rackNum => {
        const rackLocations = locationsByRack[rackNum];
        
        const rackSection = document.createElement('div');
        rackSection.className = 'rack-section card mb-3';
        
        const rackHeader = document.createElement('div');
        rackHeader.className = 'card-header';
        rackHeader.innerHTML = `<h5 class="mb-0">Rack ${rackNum}</h5>`;
        rackSection.appendChild(rackHeader);
        
        const rackBody = document.createElement('div');
        rackBody.className = 'card-body p-2';
        
        const locationList = document.createElement('div');
        locationList.className = 'location-list';
        
        // Sort locations by section and shelf
        rackLocations.sort((a, b) => {
            const partsA = a.LocationName.split('.');
            const partsB = b.LocationName.split('.');
            
            // Compare section first
            const sectionA = parseInt(partsA[1]);
            const sectionB = parseInt(partsB[1]);
            if (sectionA !== sectionB) return sectionA - sectionB;
            
            // Then compare shelf
            return parseInt(partsA[2]) - parseInt(partsB[2]);
        });
        
        // Create location items
        rackLocations.forEach(location => {
            const locationItem = document.createElement('div');
            locationItem.className = 'location-item d-flex justify-content-between align-items-center p-2 border-bottom';
            
            const locationName = document.createElement('div');
            locationName.className = 'fw-bold';
            locationName.textContent = location.LocationName;
            
            const sampleCount = document.createElement('div');
            sampleCount.className = location.count > 0 ? 'badge bg-primary' : 'badge bg-light text-dark';
            sampleCount.textContent = location.count > 0 ? `${location.count} samples` : 'Empty';
            
            locationItem.appendChild(locationName);
            locationItem.appendChild(sampleCount);
            locationList.appendChild(locationItem);
        });
        
        rackBody.appendChild(locationList);
        rackSection.appendChild(rackBody);
        storageContainer.appendChild(rackSection);
    });
}

// Function to initialize the dashboard with the correct number of racks
function initializeStorageDashboard() {
    // Based on the images, we can see racks numbered 5-14 (compact shelving)
    // plus additional regular shelving units
    
    fetch('/api/storage-locations')
        .then(response => response.json())
        .then(data => {
            if (data.locations) {
                updateStorageOverview(data.locations);
            } else {
                // Create default data for demonstration
                createDefaultStorageOverview();
            }
        })
        .catch(error => {
            console.error('Failed to load storage locations:', error);
            createDefaultStorageOverview();
        });
}

// Create default storage overview based on the images
function createDefaultStorageOverview() {
    const storageContainer = document.querySelector('.storage-grid');
    if (!storageContainer) return;
    
    storageContainer.innerHTML = '';
    
    // Create racks based on the images (compact shelving 5-14)
    for (let rack = 5; rack <= 14; rack++) {
        const rackSection = document.createElement('div');
        rackSection.className = 'rack-section card mb-3';
        
        const rackHeader = document.createElement('div');
        rackHeader.className = 'card-header';
        rackHeader.innerHTML = `<h5 class="mb-0">Rack ${rack}</h5>`;
        rackSection.appendChild(rackHeader);
        
        const rackBody = document.createElement('div');
        rackBody.className = 'card-body p-2';
        
        const locationList = document.createElement('div');
        locationList.className = 'location-list';
        
        // Each rack has 5 sections with 5 shelves each
        for (let section = 1; section <= 5; section++) {
            for (let shelf = 1; shelf <= 5; shelf++) {
                const locationItem = document.createElement('div');
                locationItem.className = 'location-item d-flex justify-content-between align-items-center p-2 border-bottom';
                
                const locationName = document.createElement('div');
                locationName.className = 'fw-bold';
                locationName.textContent = `${rack}.${section}.${shelf}`;
                
                const sampleCount = document.createElement('div');
                // Randomly assign some samples for demonstration
                const count = Math.floor(Math.random() * 5);
                sampleCount.className = count > 0 ? 'badge bg-primary' : 'badge bg-light text-dark';
                sampleCount.textContent = count > 0 ? `${count} samples` : 'Empty';
                
                locationItem.appendChild(locationName);
                locationItem.appendChild(sampleCount);
                locationList.appendChild(locationItem);
            }
        }
        
        rackBody.appendChild(locationList);
        rackSection.appendChild(rackBody);
        storageContainer.appendChild(rackSection);
    }
    
    // Add regular shelving units (seen in images 3, 6, 7)
    for (let rack = 1; rack <= 4; rack++) {
        const rackSection = document.createElement('div');
        rackSection.className = 'rack-section card mb-3';
        
        const rackHeader = document.createElement('div');
        rackHeader.className = 'card-header';
        rackHeader.innerHTML = `<h5 class="mb-0">Shelf Unit ${rack}</h5>`;
        rackSection.appendChild(rackHeader);
        
        const rackBody = document.createElement('div');
        rackBody.className = 'card-body p-2';
        
        const locationList = document.createElement('div');
        locationList.className = 'location-list';
        
        // Each regular shelf unit has 3 sections with 4 shelves each
        for (let section = 1; section <= 3; section++) {
            for (let shelf = 1; shelf <= 4; shelf++) {
                const locationItem = document.createElement('div');
                locationItem.className = 'location-item d-flex justify-content-between align-items-center p-2 border-bottom';
                
                const locationName = document.createElement('div');
                locationName.className = 'fw-bold';
                locationName.textContent = `${rack}.${section}.${shelf}`;
                
                const sampleCount = document.createElement('div');
                // Randomly assign some samples for demonstration
                const count = Math.floor(Math.random() * 5);
                sampleCount.className = count > 0 ? 'badge bg-primary' : 'badge bg-light text-dark';
                sampleCount.textContent = count > 0 ? `${count} samples` : 'Empty';
                
                locationItem.appendChild(locationName);
                locationItem.appendChild(sampleCount);
                locationList.appendChild(locationItem);
            }
        }
        
        rackBody.appendChild(locationList);
        rackSection.appendChild(rackBody);
        storageContainer.appendChild(rackSection);
    }
}

// Call this function when the dashboard page loads
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname === '/' || window.location.pathname.includes('/dashboard')) {
        initializeStorageDashboard();
    }
});