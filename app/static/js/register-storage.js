/**
 * Register Storage - Location handling for the registration form
 */

// Initialize when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Storage module loading...');
    
    // Mark this module as loaded in the global state
    if (window.registerApp) {
        window.registerApp.modulesLoaded.storage = true;
        console.log('Storage module loaded');
    } else {
        console.error('registerApp not found - storage module cannot register');
    }
});

// Set up the storage grid
function setupStorageGrid() {
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '<div class="text-center p-3"><div class="spinner-border"></div><p>Loading storage locations...</p></div>';

    // Check if there's a pre-selected location from container details
    let selectedLocationId = null;
    
    // Reset the saved rack number
    window.selectedRackNum = null;
    window.allRacksCollapsed = true;
    
    // Update storage instructions based on current selections
    updateStorageInstructions();
    
    // First check if we have a selected container location from existing container
    // Only use it if "existing container" option is actually selected
    const existingContainerOption = document.getElementById('existingContainerOption');
    const containerStorageOption = document.getElementById('containerStorageOption');
    
    if (containerStorageOption && containerStorageOption.checked && 
        existingContainerOption && existingContainerOption.checked && 
        registerApp.selectedContainerLocation && registerApp.selectedContainerLocation.LocationID) {
        
        selectedLocationId = registerApp.selectedContainerLocation.LocationID;
        
        // Parse the location name to get the rack number
        if (registerApp.selectedContainerLocation.LocationName) {
            const parts = registerApp.selectedContainerLocation.LocationName.split('.');
            if (parts.length >= 1) {
                window.selectedRackNum = parts[0];
            }
        }
        
        console.log("Using location from existing container:", selectedLocationId, registerApp.selectedContainerLocation.LocationName, "Rack:", window.selectedRackNum);
    }

    // Fetch storage locations from API
    fetch('/api/storage-locations')
        .then(response => response.json())
        .then(data => {
            console.log("Received storage location data:", data);
            if (data.locations) {
                createGridFromLocations(data.locations, selectedLocationId);
            } else {
                console.error("No locations in response");
                // Fallback to rack.section.shelf format
                createDefaultStorageGrid(selectedLocationId);
            }
            
            // Show the location summary
            updateLocationSummary();
        })
        .catch(error => {
            console.error('Error fetching storage locations:', error);
            // Fallback to rack.section.shelf format
            createDefaultStorageGrid(selectedLocationId);
            
            // Show the location summary
            updateLocationSummary();
        });
}

// Create grid from fetched location data
function createGridFromLocations(locations, preSelectedLocationId = null) {
    console.log("createGridFromLocations with", locations.length, "locations", preSelectedLocationId ? `and pre-selected location ${preSelectedLocationId}` : "");
    
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '';
    
    // Organize locations by rack, section, shelf
    const organizedLocations = organizeLocationsByStructure(locations);
    
    // Keep track of the cell for pre-selected location
    let preSelectedCell = null;
    
    // Remove any existing fixed button bar to prevent duplicates
    const existingButtonBar = document.querySelector('.fixed-button-bar');
    if (existingButtonBar) {
        existingButtonBar.remove();
    }
    
    // Create rack sections
    Object.keys(organizedLocations).sort((a, b) => parseInt(a) - parseInt(b)).forEach(reolNum => {
        const reolSection = document.createElement('div');
        reolSection.className = 'reol-section mb-4';
        
        // Determine if this rack should be expanded
        const isSelectedRack = (window.selectedRackNum === reolNum) || (preSelectedLocationId && preSelectedLocationId.toString().startsWith(reolNum));
        
        const reolHeader = document.createElement('div');
        reolHeader.className = 'mb-2 d-flex justify-content-between align-items-center bg-light p-2 rounded';
        
        // Create clickable header with toggle functionality
        const titleSpan = document.createElement('h5');
        titleSpan.textContent = `Rack ${reolNum}`;
        titleSpan.className = 'mb-0';
        titleSpan.style.cursor = 'pointer';
        
        // Add rack header elements
        reolHeader.appendChild(titleSpan);
        reolSection.appendChild(reolHeader);
        
        // Create container for sections
        const sektionsContainer = document.createElement('div');
        sektionsContainer.className = 'd-flex flex-wrap';
        sektionsContainer.style.display = isSelectedRack ? 'flex' : 'none';
        
        // Add toggle functionality to header
        reolHeader.addEventListener('click', () => {
            if (sektionsContainer.style.display === 'none') {
                // Collapse all other racks first
                if (!event.ctrlKey) { // Unless ctrl key is pressed (for multiple expanding)
                    const allSektionsContainers = document.querySelectorAll('.reol-section .d-flex.flex-wrap');
                    
                    allSektionsContainers.forEach(container => {
                        if (container !== sektionsContainer) {
                            container.style.display = 'none';
                        }
                    });
                }
                
                // Now expand this rack
                sektionsContainer.style.display = 'flex';
                reolHeader.classList.add('bg-primary', 'text-white');
            } else {
                sektionsContainer.style.display = 'none';
                reolHeader.classList.remove('bg-primary', 'text-white');
            }
        });
        
        // For each section in the rack
        Object.keys(organizedLocations[reolNum]).sort((a, b) => parseInt(a) - parseInt(b)).forEach(sektionNum => {
            const sektionDiv = document.createElement('div');
            sektionDiv.className = 'sektion-container me-3 mb-3';
            
            const sektionHeader = document.createElement('div');
            sektionHeader.textContent = `Section ${sektionNum}`;
            sektionHeader.className = 'sektion-header small text-muted mb-1';
            sektionDiv.appendChild(sektionHeader);
            
            const hyldeContainer = document.createElement('div');
            hyldeContainer.className = 'd-flex flex-column';
            
            // For each shelf in the section
            Object.keys(organizedLocations[reolNum][sektionNum]).sort((a, b) => parseInt(a) - parseInt(b)).forEach(hyldeNum => {
                const location = organizedLocations[reolNum][sektionNum][hyldeNum];
                const locationName = `${reolNum}.${sektionNum}.${hyldeNum}`;
                
                // Create shelf cell
                const cell = document.createElement('div');
                cell.className = 'storage-cell mb-1';
                cell.dataset.locationId = location.LocationID;
                cell.dataset.locationName = locationName;
                
                // Show number of samples on the shelf instead of "occupied"
                const count = location.count || 0;
                
                const locationEl = document.createElement('div');
                locationEl.className = 'location fw-bold';
                locationEl.textContent = locationName;
                
                const capacity = document.createElement('div');
                capacity.className = 'capacity small';
                capacity.textContent = count > 0 ? `${count} sample(s)` : 'Available';
                
                cell.appendChild(locationEl);
                cell.appendChild(capacity);
                hyldeContainer.appendChild(cell);
                
                // Standard single selection mode
                cell.addEventListener('click', () => {
                    selectStorageCell(cell);
                    updateLocationSummary();
                });
                
                // If this is the pre-selected location, save the cell reference
                if (preSelectedLocationId && location.LocationID == preSelectedLocationId) {
                    preSelectedCell = cell;
                }
            });
            
            sektionDiv.appendChild(hyldeContainer);
            sektionsContainer.appendChild(sektionDiv);
        });
        
        reolSection.appendChild(sektionsContainer);
        grid.appendChild(reolSection);
    });
    
    // After the grid is created, auto-select the pre-selected location if any
    if (preSelectedCell) {
        console.log("Auto-selecting pre-selected location");
        
        // Scroll to make the location visible (with some delay to ensure DOM is ready)
        setTimeout(() => {
            preSelectedCell.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Select the cell
            selectStorageCell(preSelectedCell);
            
            // Add a highlight animation
            preSelectedCell.classList.add('highlight-animation');
            setTimeout(() => {
                preSelectedCell.classList.remove('highlight-animation');
            }, 1500);
            
            // If using container location, show a message
            if (registerApp.selectedContainerLocation) {
                showSuccessMessage(`Using container location: ${registerApp.selectedContainerLocation.LocationName}`);
            }
            
            // Update the location summary
            updateLocationSummary();
        }, 200);
    } 
    // If we have container location but couldn't find the cell, still store the ID
    else if (registerApp.selectedContainerLocation && registerApp.selectedContainerLocation.LocationID) {
        console.log("Container location exists but cell not found in grid. Using location ID:", registerApp.selectedContainerLocation.LocationID);
        registerApp.selectedLocation = registerApp.selectedContainerLocation.LocationID;
        
        // Show a location indicator even without a cell
        let locationIndicator = document.querySelector('.selected-location-indicator');
        if (!locationIndicator) {
            locationIndicator = document.createElement('div');
            locationIndicator.className = 'selected-location-indicator mt-3 p-2 bg-light rounded';
            document.querySelector('.storage-selector').appendChild(locationIndicator);
        }
        
        locationIndicator.innerHTML = `<strong>Selected location:</strong> ${registerApp.selectedContainerLocation.LocationName} <span class="badge bg-info">Container Location</span>`;
        
        // Create hidden input
        let locationInput = document.getElementById('selectedLocationInput');
        if (!locationInput) {
            locationInput = document.createElement('input');
            locationInput.type = 'hidden';
            locationInput.name = 'storageLocation';
            locationInput.id = 'selectedLocationInput';
            document.querySelector('.storage-selector').appendChild(locationInput);
        }
        
        locationInput.value = registerApp.selectedContainerLocation.LocationID;
        
        // Update the location summary
        updateLocationSummary();
    }
}

// We maintain our grid creation function with updated format
function createDefaultStorageGrid(preSelectedLocationId = null) {
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '';
    
    // Keep track of the cell for pre-selected location
    let preSelectedCell = null;
    
    // Create default storage grid with rack.section.shelf format
    for (let rack = 1; rack <= 3; rack++) {
        const reolSection = document.createElement('div');
        reolSection.className = 'reol-section mb-4';
        
        const reolHeader = document.createElement('h5');
        reolHeader.textContent = `Rack ${rack}`;
        reolHeader.className = 'mb-2';
        reolSection.appendChild(reolHeader);
        
        const sektionsContainer = document.createElement('div');
        sektionsContainer.className = 'd-flex flex-wrap';
        
        for (let section = 1; section <= 2; section++) {
            const sektionDiv = document.createElement('div');
            sektionDiv.className = 'sektion-container me-3 mb-3';
            
            const sektionHeader = document.createElement('div');
            sektionHeader.textContent = `Section ${section}`;
            sektionHeader.className = 'sektion-header small text-muted mb-1';
            sektionDiv.appendChild(sektionHeader);
            
            const hyldeContainer = document.createElement('div');
            hyldeContainer.className = 'd-flex flex-column';
            
            for (let shelf = 1; shelf <= 5; shelf++) {
                const cell = document.createElement('div');
                cell.className = 'storage-cell mb-1';
                
                const locationName = `${rack}.${section}.${shelf}`;
                cell.dataset.locationName = locationName;
                
                // Generate a simulated ID matching format in DB (LocationID)
                const simulatedId = `${rack}${section}${shelf}`;
                cell.dataset.locationId = simulatedId;
                
                const locationEl = document.createElement('div');
                locationEl.className = 'location fw-bold';
                locationEl.textContent = locationName;
                
                const capacity = document.createElement('div');
                capacity.className = 'capacity small';
                capacity.textContent = 'Available';
                
                cell.appendChild(locationEl);
                cell.appendChild(capacity);
                hyldeContainer.appendChild(cell);
                
                // Add click event to the cell
                cell.addEventListener('click', () => {
                    selectStorageCell(cell);
                    updateLocationSummary();
                });
                
                // If this is the pre-selected location, save the cell reference
                if (preSelectedLocationId && simulatedId == preSelectedLocationId) {
                    preSelectedCell = cell;
                }
            }
            
            sektionDiv.appendChild(hyldeContainer);
            sektionsContainer.appendChild(sektionDiv);
        }
        
        reolSection.appendChild(sektionsContainer);
        grid.appendChild(reolSection);
    }
    
    // After the grid is created, auto-select the pre-selected location if any
    if (preSelectedCell) {
        console.log("Auto-selecting pre-selected location in default grid");
        
        // Scroll to make the location visible (with some delay to ensure DOM is ready)
        setTimeout(() => {
            preSelectedCell.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Select the cell
            selectStorageCell(preSelectedCell);
            
            // Add a highlight animation
            preSelectedCell.classList.add('highlight-animation');
            setTimeout(() => {
                preSelectedCell.classList.remove('highlight-animation');
            }, 1500);
        }, 200);
    }
}

// Organize locations by structure
function organizeLocationsByStructure(locations) {
    const organized = {};
    let selectedRackNum = null;
    
    locations.forEach(location => {
        let reolNum, sektionNum, hyldeNum;
        
        // If we have Rack, Section, Shelf columns directly
        if (location.Rack !== undefined && location.Section !== undefined && location.Shelf !== undefined) {
            reolNum = location.Rack;
            sektionNum = location.Section;
            hyldeNum = location.Shelf;
        } else {
            // Parse LocationName (assumes format rack.section.shelf)
            const parts = location.LocationName.split('.');
            if (parts.length === 3) {
                [reolNum, sektionNum, hyldeNum] = parts;
            } else if (parts.length === 2) {
                // Handle older A1.B1 format
                reolNum = location.LocationName.substring(1, 2);
                sektionNum = "1";
                hyldeNum = location.LocationName.substring(4);
            } else {
                console.log("Unknown format:", location.LocationName);
                return; // Skip if format not recognized
            }
        }
        
        // Create necessary objects if they don't exist
        if (!organized[reolNum]) organized[reolNum] = {};
        if (!organized[reolNum][sektionNum]) organized[reolNum][sektionNum] = {};
        
        // Store location in organizational structure
        organized[reolNum][sektionNum][hyldeNum] = location;
        
        // Check if this is the selected location
        if (registerApp.selectedContainerLocation && registerApp.selectedContainerLocation.LocationID == location.LocationID) {
            selectedRackNum = reolNum;
        }
    });
    
    // Store the selected rack number for later use
    if (selectedRackNum) {
        window.selectedRackNum = selectedRackNum;
    }
    
    return organized;
}

// Updated selectStorageCell function - with direct saving of location without dropdown
function selectStorageCell(cell) {
    // All cells are clickable, regardless of how many samples are on a shelf
    
    // Remove marking from all cells
    document.querySelectorAll('.storage-cell').forEach(c => c.classList.remove('selected'));
    
    // Mark the selected cell
    cell.classList.add('selected');
    
    // Get location ID and name
    const locationId = cell.dataset.locationId;
    const locationName = cell.dataset.locationName;
    
    // Save the location for form submission
    registerApp.selectedLocation = locationId;
    
    // Display selected location
    let locationIndicator = document.querySelector('.selected-location-indicator');
    if (!locationIndicator) {
        locationIndicator = document.createElement('div');
        locationIndicator.className = 'selected-location-indicator mt-3 p-2 bg-light rounded';
        document.querySelector('.storage-selector').appendChild(locationIndicator);
    }
    
    locationIndicator.innerHTML = `<strong>Selected location:</strong> ${locationName}`;
    
    // Update hidden input fields
    let locationInput = document.getElementById('selectedLocationInput');
    if (!locationInput) {
        locationInput = document.createElement('input');
        locationInput.type = 'hidden';
        locationInput.name = 'storageLocation';
        locationInput.id = 'selectedLocationInput';
        document.querySelector('.storage-selector').appendChild(locationInput);
    }
    
    locationInput.value = locationId;
}

// Function to handle multi-package selection


// Update the location summary based on selected options
function updateLocationSummary() {
    const locationSummary = document.getElementById('locationSummary');
    const locationSummaryContent = document.getElementById('locationSummaryContent');
    
    if (!locationSummary || !locationSummaryContent) return;
    
    // Get relevant selection data
    const storageOption = document.querySelector('input[name="storageOption"]:checked')?.value || 'direct';
    const useExistingContainer = storageOption === 'container' && document.getElementById('existingContainerOption')?.checked;
    
    let summaryHtml = '';
    
    // If using existing container location
    if (useExistingContainer && registerApp.selectedContainerLocation) {
        summaryHtml += `
            <div class="alert alert-info mb-2">
                <i class="fas fa-info-circle"></i>
                Using container location: <strong>${registerApp.selectedContainerLocation.LocationName}</strong>
            </div>
        `;
    }
    // Standard single location selection
    else {
        const selectedCell = document.querySelector('.storage-cell.selected');
        if (selectedCell) {
            const locationName = selectedCell.dataset.locationName;
            
            summaryHtml += `
                <div class="alert alert-success mb-2">
                    <i class="fas fa-check-circle"></i>
                    Selected location: <strong>${locationName}</strong>
                </div>
            `;
        } else {
            summaryHtml += `
                <div class="alert alert-warning mb-2">
                    <i class="fas fa-exclamation-triangle"></i>
                    No location selected. Please click on an available space in the grid.
                </div>
            `;
        }
    }
    
    // Update the summary content
    locationSummaryContent.innerHTML = summaryHtml;
    
    // Show the summary
    locationSummary.classList.remove('d-none');
}


// Update storage instructions based on selected options
function updateStorageInstructions() {
    const storageInstructions = document.getElementById('storageInstructions');
    const storageInstructionsText = document.getElementById('storageInstructionsText');
    
    if (!storageInstructions || !storageInstructionsText) return;
    
    const storageOption = document.querySelector('input[name="storageOption"]:checked')?.value || 'direct';
    
    let instructionText = '';
    
    // Generate appropriate instructions based on selections
    if (storageOption === 'container' && document.getElementById('existingContainerOption')?.checked) {
        instructionText = 'Using the location of the selected existing container. You can still choose a different location if needed.';
    } else {
        instructionText = 'Select a storage location by clicking on an available space in the grid below.';
    }
    
    storageInstructionsText.textContent = instructionText;
}