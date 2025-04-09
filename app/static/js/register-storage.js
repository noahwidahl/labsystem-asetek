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
    const containerLocationSelect = document.getElementById('containerLocation');
    let selectedLocationId = null;
    
    // Reset the saved rack number
    window.selectedRackNum = null;
    window.allRacksCollapsed = true;
    
    // Update storage instructions based on current selections
    updateStorageInstructions();
    
    // First check if we have a selected container location from existing container
    if (registerApp.selectedContainerLocation && registerApp.selectedContainerLocation.LocationID) {
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
    // Otherwise use the selected container location from the new container form
    else if (containerLocationSelect && containerLocationSelect.value) {
        selectedLocationId = containerLocationSelect.value;
        
        // Try to extract rack number
        if (containerLocationSelect.selectedOptions && containerLocationSelect.selectedOptions[0]) {
            const locationText = containerLocationSelect.selectedOptions[0].textContent;
            const match = locationText.match(/(\d+)\.(\d+)\.(\d+)/);
            if (match) {
                window.selectedRackNum = match[1];
            }
        }
        
        console.log("Using pre-selected location from container form:", selectedLocationId, "Rack:", window.selectedRackNum);
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
    
    // Add fixed button bar at the bottom for navigation and hide the original buttons
    const originalPrevButton = document.getElementById('prevButton');
    const originalNextButton = document.getElementById('nextButton');
    
    // Get text from original next button (could be "Next" or "Save")
    const nextButtonText = originalNextButton ? originalNextButton.textContent.trim() : "Save";
    const isLastStep = nextButtonText.toLowerCase().includes('save');
    
    // Hide original navigation buttons if they exist
    if (originalPrevButton) originalPrevButton.style.display = 'none';
    if (originalNextButton) originalNextButton.style.display = 'none';
    
    // Find the form navigation container and hide it
    const formNavigation = document.querySelector('.form-navigation');
    if (formNavigation) formNavigation.style.display = 'none';
    
    // Create fixed button bar
    let buttonBar = document.querySelector('.fixed-button-bar');
    if (!buttonBar) {
        buttonBar = document.createElement('div');
        buttonBar.className = 'fixed-button-bar position-sticky bottom-0 bg-white border-top py-3 px-4 d-flex justify-content-between';
        buttonBar.style.zIndex = '1000';
        buttonBar.style.marginTop = 'auto';
        buttonBar.innerHTML = `
            <button type="button" class="btn btn-secondary" id="fixedPrevButton">
                <i class="fas fa-arrow-left me-2"></i>Back
            </button>
            <button type="button" class="btn btn-primary" id="fixedNextButton">
                ${isLastStep ? 'Save' : 'Next'} ${isLastStep ? '' : '<i class="fas fa-arrow-right ms-2"></i>'}
            </button>
        `;
        
        // Find the parent to attach the button bar to
        const storageSelector = document.querySelector('.storage-selector');
        if (storageSelector) {
            storageSelector.style.paddingBottom = '70px'; // Make room for the fixed bar
            storageSelector.appendChild(buttonBar);
            
            // Add event listeners to buttons
            buttonBar.querySelector('#fixedPrevButton').addEventListener('click', function() {
                if (originalPrevButton) originalPrevButton.click();
            });
            
            buttonBar.querySelector('#fixedNextButton').addEventListener('click', function() {
                console.log('Fixed next button clicked, current step:', registerApp.currentStep);
                
                // Very simple approach: if on last step, submit directly from the backup function
                if (registerApp.currentStep === registerApp.totalSteps) {
                    console.log('Final step, calling handleFormSubmission');
                    
                    // Check if the function exists before calling it
                    if (typeof window.handleFormSubmission === 'function') {
                        window.handleFormSubmission();
                    } else {
                        console.error("handleFormSubmission not found in register-storage.js - using fallback");
                        
                        // Fallback - use form submission via direct API call
                        const formData = {
                            // Use the form data directly
                            description: document.querySelector('[name="description"]')?.value || '',
                            totalAmount: parseInt(document.querySelector('[name="totalAmount"]')?.value) || 1,
                            unit: document.querySelector('[name="unit"]')?.value || '',
                            storageLocation: registerApp.selectedLocation || '',
                            storageOption: document.querySelector('input[name="storageOption"]:checked')?.value || 'direct',
                            createContainers: document.querySelector('input[name="storageOption"]:checked')?.value === 'container'
                        };
                        
                        // If containers are used, add container info
                        if (formData.createContainers) {
                            // API expects this format
                            formData.containerDescription = document.getElementById('containerDescription')?.value || '';
                            // Ensure containerTypeId is a number
                            const typeId = document.getElementById('containerType')?.value;
                            formData.containerTypeId = typeId ? parseInt(typeId) : null;
                            // Ensure capacity is a number
                            const capacity = document.getElementById('containerCapacity')?.value;
                            formData.containerCapacity = capacity ? parseInt(capacity) : null;
                            formData.containerIsMixed = document.getElementById('containerIsMixed')?.checked || false;
                            
                            // Container location - use either the specific select or the general location
                            const containerLocationSelect = document.getElementById('containerLocation');
                            if (containerLocationSelect && containerLocationSelect.value) {
                                // Ensure locationId is a number
                                formData.containerLocationId = parseInt(containerLocationSelect.value);
                            } else if (registerApp.selectedLocation) {
                                // Ensure locationId is a number
                                formData.containerLocationId = typeof registerApp.selectedLocation === 'string' ? 
                                    parseInt(registerApp.selectedLocation) : registerApp.selectedLocation;
                            }
                            
                            // For debugging
                            console.log('Container data being sent:', {
                                createContainers: formData.createContainers,
                                containerDescription: formData.containerDescription,
                                containerTypeId: formData.containerTypeId,
                                containerIsMixed: formData.containerIsMixed,
                                containerCapacity: formData.containerCapacity,
                                containerLocationId: formData.containerLocationId
                            });
                        }
                        
                        // Show processing message
                        alert('Submitting registration...');
                        
                        // Send data directly
                        fetch('/api/samples', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(formData)
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                alert(`Success! Sample ${data.sample_id} has been registered.`);
                                window.location.href = '/dashboard';
                            } else {
                                alert(`Error: ${data.error || 'Unknown error'}`);
                            }
                        })
                        .catch(error => {
                            alert(`Error: ${error.message || 'Unknown error'}`);
                        });
                    }
                } else {
                    // For other steps, use the original button which has the nextStep logic
                    if (originalNextButton) originalNextButton.click();
                }
            });
        }
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
                
                // Determine if we need multi-select mode
                const sampleType = document.querySelector('input[name="sampleTypeOption"]:checked')?.value || 'single';
                const storageOption = document.querySelector('input[name="storageOption"]:checked')?.value || 'direct';
                const separateStorage = document.getElementById('separateStorage')?.checked || false;
                const oneContainerPerPackage = storageOption === 'container' && sampleType === 'multiple' && document.getElementById('oneContainerPerPackage')?.checked;
                
                // Add visual indicator for multi-package selection
                if ((sampleType === 'multiple' && separateStorage) || oneContainerPerPackage) {
                    cell.setAttribute('data-toggle', 'tooltip');
                    cell.setAttribute('title', 'Click to select for a package');
                    cell.classList.add('multi-selectable-cell');
                }
                
                // Use multi-select if either separate storage OR one container per package is active
                if ((sampleType === 'multiple' && separateStorage) || oneContainerPerPackage) {
                    // In multi-selection mode, mark cells as available for selection
                    cell.classList.add('multi-package-available');
                    
                    // Use the multi-package selection handler
                    cell.addEventListener('click', () => {
                        handleMultiPackageSelection(cell);
                        updateLocationSummary();
                    });
                } else {
                    // For normal selection mode, use standard selection
                    cell.addEventListener('click', () => {
                        selectStorageCell(cell);
                        updateLocationSummary();
                    });
                }
                
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
function handleMultiPackageSelection(cell) {
    // Get required count based on selection
    const sampleType = document.querySelector('input[name="sampleTypeOption"]:checked')?.value || 'single';
    const storageOption = document.querySelector('input[name="storageOption"]:checked')?.value || 'direct';
    
    let packageCount = 1;
    
    // For multiple samples with separate storage
    if (sampleType === 'multiple' && document.getElementById('separateStorage')?.checked) {
        packageCount = parseInt(document.querySelector('[name="packageCount"]')?.value) || 1;
    }
    // For multiple samples with one container per package
    else if (sampleType === 'multiple' && storageOption === 'container' && document.getElementById('oneContainerPerPackage')?.checked) {
        packageCount = parseInt(document.querySelector('[name="packageCount"]')?.value) || 1;
    }
    
    const selectedCellsCount = document.querySelectorAll('.storage-cell.multi-package-selected').length;
    
    // Ensure PackageLocations is available
    if (typeof window.PackageLocations === 'undefined') {
        console.error("PackageLocations module not available");
        alert("Error: Package location tracking is not available. Please refresh the page and try again.");
        return;
    }
    
    // Check if cell is already selected
    if (cell.classList.contains('multi-package-selected')) {
        // Find the package number associated with this cell
        const packageNumber = getPackageNumberForCell(cell);
        
        // Deselect cell
        cell.classList.remove('multi-package-selected');
        cell.classList.add('multi-package-available');
        
        // Find location and remove it from package-locations list
        const locationText = cell.querySelector('.location').textContent;
        
        // Debug log
        console.log("Removing location from cell:", locationText, "with package number:", packageNumber);
        
        if (packageNumber) {
            // If we know the package number, use it
            window.PackageLocations.removeLocation(packageNumber);
        } else {
            // Otherwise remove by name
            window.PackageLocations.removeLocationByName(locationText);
        }
        
        // Always update the summary when removing a location
        updatePackageSelectionSummary();
        
        // Debug: dump state
        console.log("After removal, package locations:", window.PackageLocations.dumpState());
    } else {
        // Check if we already selected maximum number of locations
        if (selectedCellsCount < packageCount) {
            // Select cell
            cell.classList.add('multi-package-selected');
            cell.classList.remove('multi-package-available');
            
            // Get location info from cell
            const locationText = cell.querySelector('.location').textContent;
            const locationId = cell.dataset.locationId;
            
            // Find the next available package number
            let nextPackageNumber = 1;
            
            // Get all currently selected packages
            const selectedPackages = [];
            window.PackageLocations.getSelectedLocations().forEach(loc => {
                selectedPackages.push(parseInt(loc.packageNumber));
            });
            
            // If there are packages already selected, find the next available
            if (selectedPackages.length > 0) {
                selectedPackages.sort((a, b) => a - b);
                
                // Find first gap in sequence or use next number
                for (let i = 1; i <= packageCount; i++) {
                    if (!selectedPackages.includes(i)) {
                        nextPackageNumber = i;
                        break;
                    }
                }
            }
            
            // Debug log
            console.log("Adding location from cell:", locationText, "with ID:", locationId, "as package:", nextPackageNumber);
            
            // Store the package number in a data attribute on the cell for later reference
            cell.dataset.packageNumber = nextPackageNumber;
            
            // Add location with the determined package number
            window.PackageLocations.addLocation(nextPackageNumber, locationId, locationText);
            
            // Always update the summary when adding a location
            updatePackageSelectionSummary();
            
            // Debug: dump state
            console.log("After addition, package locations:", window.PackageLocations.dumpState());
        } else {
            // We already selected max count - show error
            alert(`You can only select ${packageCount} locations. Remove a location before adding a new one.`);
        }
    }
}

// Helper function to get the package number stored on a cell
function getPackageNumberForCell(cell) {
    // If we have package number stored directly on the cell, use it
    if (cell.dataset.packageNumber) {
        return parseInt(cell.dataset.packageNumber);
    }
    
    // Otherwise try to find it by location name
    const locationText = cell.querySelector('.location').textContent;
    const location = window.PackageLocations.getLocationByName(locationText);
    
    return location ? location.packageNumber : null;
}

// Update the location summary based on selected options
function updateLocationSummary() {
    const locationSummary = document.getElementById('locationSummary');
    const locationSummaryContent = document.getElementById('locationSummaryContent');
    
    if (!locationSummary || !locationSummaryContent) return;
    
    // Get relevant selection data
    const sampleType = document.querySelector('input[name="sampleTypeOption"]:checked')?.value || 'single';
    const storageOption = document.querySelector('input[name="storageOption"]:checked')?.value || 'direct';
    const separateStorage = document.getElementById('separateStorage')?.checked || false;
    const useExistingContainer = storageOption === 'container' && document.getElementById('existingContainerOption')?.checked;
    const oneContainerPerPackage = storageOption === 'container' && sampleType === 'multiple' && document.getElementById('oneContainerPerPackage')?.checked;
    
    // Check if we should use multi-select mode
    const useMultiSelect = (sampleType === 'multiple' && separateStorage) || (oneContainerPerPackage);
    
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
    // If using multi-select mode for packages or containers
    else if (useMultiSelect) {
        // Ensure PackageLocations is available
        if (typeof window.PackageLocations === 'undefined') {
            window.PackageLocations = {
                _locations: [],
                getSelectedLocations: function() { return this._locations; }
            };
        }
        
        const selectedLocations = PackageLocations.getSelectedLocations() || [];
        const packageCount = parseInt(document.querySelector('[name="packageCount"]')?.value) || 1;
        
        // Determine if this is for containers or multiple packages
        const oneContainerPerPackage = document.getElementById('oneContainerPerPackage')?.checked || false;
        
        // Show progress and remaining count with appropriate message
        summaryHtml += `
            <div class="alert ${selectedLocations.length === packageCount ? 'alert-success' : 'alert-warning'} mb-2">
                <i class="fas fa-${selectedLocations.length === packageCount ? 'check-circle' : 'exclamation-triangle'}"></i>
                ${oneContainerPerPackage ? 
                  `Selected ${selectedLocations.length} of ${packageCount} container locations (one per package)` : 
                  `Selected ${selectedLocations.length} of ${packageCount} required package locations`}
            </div>
        `;
        
        // If we have selected locations, show them
        if (selectedLocations.length > 0) {
            summaryHtml += '<div class="selected-locations-list mt-2">';
            
            // Sort by package number
            const sortedLocations = [...selectedLocations].sort((a, b) => parseInt(a.packageNumber) - parseInt(b.packageNumber));
            
            sortedLocations.forEach(loc => {
                summaryHtml += `
                    <div class="selected-location-item mb-1">
                        <span class="badge bg-primary me-2">Package ${loc.packageNumber}</span>
                        <span class="location-name">${loc.locationName}</span>
                    </div>
                `;
            });
            
            summaryHtml += '</div>';
        }
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

// Update display of selected packages and locations
function updatePackageSelectionSummary() {
    // Get sample type and determine if we need to show package locations
    const sampleType = document.querySelector('input[name="sampleTypeOption"]:checked')?.value || 'single';
    const storageOption = document.querySelector('input[name="storageOption"]:checked')?.value || 'direct';
    const separateStorage = document.getElementById('separateStorage')?.checked || false;
    const oneContainerPerPackage = storageOption === 'container' && sampleType === 'multiple' && document.getElementById('oneContainerPerPackage')?.checked;
    
    // Only show summary for multi-package with separate storage or one container per package
    const useMultiSelect = (sampleType === 'multiple' && separateStorage) || oneContainerPerPackage;
    if (!useMultiSelect) return;
    
    const packageCount = parseInt(document.querySelector('[name="packageCount"]')?.value) || 1;
    
    // Find or create summary container
    let summaryContainer = document.querySelector('.package-selection-summary');
    if (!summaryContainer) {
        summaryContainer = document.createElement('div');
        summaryContainer.className = 'package-selection-summary mt-4';
        
        const storageSelector = document.querySelector('.storage-selector');
        if (storageSelector) {
            storageSelector.appendChild(summaryContainer);
        }
    }
    
    // Get selected package locations
    if (typeof window.PackageLocations === 'undefined') {
        console.error("PackageLocations module not available");
        return;
    }
    
    // Debug - log the current state
    console.log("DEBUG: Update summary - current package locations:", window.PackageLocations.dumpState());
    
    const selectedLocations = window.PackageLocations.getSelectedLocations();
    
    // Update summary
    if (selectedLocations.length === 0) {
        summaryContainer.innerHTML = '';
        summaryContainer.classList.add('d-none');
        return;
    }
    
    summaryContainer.classList.remove('d-none');
    
    // Sort by package number
    const sortedLocations = [...selectedLocations].sort((a, b) => 
        parseInt(a.packageNumber) - parseInt(b.packageNumber));
    
    let html = `
        <div class="card">
            <div class="card-header bg-light">
                <h5 class="mb-0">Selected Package Locations</h5>
            </div>
            <div class="card-body">
                <ul class="list-group list-group-flush">
    `;
    
    sortedLocations.forEach(pkg => {
        html += `
            <li class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <span class="badge bg-primary me-2">Package ${pkg.packageNumber}</span>
                    <span>${pkg.locationName} (ID: ${pkg.locationId})</span>
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger remove-location" data-package="${pkg.packageNumber}">
                    <i class="fas fa-times"></i>
                </button>
            </li>
        `;
    });
    
    html += `
                </ul>
            </div>
            <div class="card-footer">
                <div class="d-flex justify-content-between align-items-center">
                    <span>${selectedLocations.length} of ${packageCount} locations selected</span>
                    <button type="button" class="btn btn-sm btn-outline-secondary" id="clearAllLocations">
                        Clear all
                    </button>
                </div>
            </div>
        </div>
    `;
    
    summaryContainer.innerHTML = html;
    
    // Add event listeners to remove buttons
    summaryContainer.querySelectorAll('.remove-location').forEach(button => {
        button.addEventListener('click', function() {
            const packageNumber = this.getAttribute('data-package');
            const locationData = window.PackageLocations.getLocationByPackage(packageNumber);
            
            if (locationData) {
                // Find and update the corresponding grid cell
                const gridCells = document.querySelectorAll('.storage-cell');
                gridCells.forEach(cell => {
                    const locationText = cell.querySelector('.location')?.textContent;
                    if (locationText === locationData.locationName) {
                        cell.classList.remove('multi-package-selected');
                        cell.classList.add('multi-package-available');
                        // Also remove package number from cell
                        delete cell.dataset.packageNumber;
                    }
                });
                
                // Remove from package locations
                window.PackageLocations.removeLocation(packageNumber);
                
                // Debug - log after removal
                console.log(`DEBUG: Removed package ${packageNumber}, remaining locations:`, window.PackageLocations.dumpState());
                
                // Update summary
                updatePackageSelectionSummary();
                updateLocationSummary();
            }
        });
    });
    
    // Add event listener to "clear all" button
    const clearAllBtn = document.getElementById('clearAllLocations');
    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', function() {
            // Remove all selected locations
            window.PackageLocations.reset();
            
            // Reset grid cells
            const gridCells = document.querySelectorAll('.storage-cell.multi-package-selected');
            gridCells.forEach(cell => {
                cell.classList.remove('multi-package-selected');
                cell.classList.add('multi-package-available');
                // Also remove package number from cell
                delete cell.dataset.packageNumber;
            });
            
            // Debug - log after reset
            console.log("DEBUG: Reset all locations:", window.PackageLocations.dumpState());
            
            // Update summary
            updatePackageSelectionSummary();
            updateLocationSummary();
        });
    }
    
    // Update location summary to show status
    updateLocationSummary();
}

// Update storage instructions based on selected options
function updateStorageInstructions() {
    const storageInstructions = document.getElementById('storageInstructions');
    const storageInstructionsText = document.getElementById('storageInstructionsText');
    
    if (!storageInstructions || !storageInstructionsText) return;
    
    const sampleType = document.querySelector('input[name="sampleTypeOption"]:checked')?.value || 'single';
    const storageOption = document.querySelector('input[name="storageOption"]:checked')?.value || 'direct';
    const separateStorage = document.getElementById('separateStorage')?.checked || false;
    const multiContainerOption = document.querySelector('input[name="multiContainerOption"]:checked')?.value || 'single';
    
    let instructionText = '';
    
    // Generate appropriate instructions based on selections
    if (sampleType === 'multiple' && separateStorage) {
        instructionText = 'Select multiple locations by clicking on available spaces in the grid. You need to select one location for each package.';
    } else if (sampleType === 'multiple' && storageOption === 'container' && multiContainerOption === 'multiple') {
        instructionText = 'MULTIPLE CONTAINER MODE: Select one location for each container. You need to select exactly ' + 
                         (document.querySelector('[name="packageCount"]')?.value || '1') + 
                         ' locations (one for each package). Each container will be created at its own location.';
    } else if (storageOption === 'container' && document.getElementById('existingContainerOption')?.checked) {
        instructionText = 'Using the location of the selected existing container. You can still choose a different location if needed.';
    } else {
        instructionText = 'Select a storage location by clicking on an available space in the grid below.';
    }
    
    storageInstructionsText.textContent = instructionText;
}