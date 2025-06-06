/**
 * Register Containers - Container handling for the registration form
 */

// Initialize when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Containers module loading...');
    
    // Setup container options
    setupStorageOptions();
    setupContainerOptions();
    setupContainerTypeCreation();
    setupLocationValidation();
    
    // Mark this module as loaded in the global state
    if (window.registerApp) {
        window.registerApp.modulesLoaded.containers = true;
        console.log('Containers module loaded');
    } else {
        console.error('registerApp not found - containers module cannot register');
    }
});

// Setup location validation for text input
function setupLocationValidation() {
    const locationInput = document.getElementById('containerLocation');
    if (!locationInput) return;
    
    console.log('Setting up location validation');
    
    // Function to validate location format (x.x.x)
    function validateLocationFormat(value) {
        if (!value) return false;
        
        // Check format with regex - allows for 1.1.1, 10.5.3, etc.
        // Format is x.x.x where x is one or more digits
        const locationRegex = /^\d+\.\d+\.\d+$/;
        return locationRegex.test(value);
    }
    
    // Add input event listener to validate on typing
    locationInput.addEventListener('input', function() {
        const value = this.value.trim();
        const isValid = validateLocationFormat(value);
        
        // Show/hide error message
        if (value && !isValid) {
            this.classList.add('is-invalid');
            this.setCustomValidity('Please enter a valid location in format "x.x.x" (e.g. 1.1.1)');
        } else {
            this.classList.remove('is-invalid');
            this.setCustomValidity('');
        }
    });
    
    // Add blur event to validate on focus loss
    locationInput.addEventListener('blur', function() {
        const value = this.value.trim();
        if (value && !validateLocationFormat(value)) {
            this.classList.add('is-invalid');
            this.setCustomValidity('Please enter a valid location in format "x.x.x" (e.g. 1.1.1)');
        }
    });
}

// Setup storage options (Direct vs Container)
function setupStorageOptions() {
    const directStorageOption = document.getElementById('directStorageOption');
    const containerStorageOption = document.getElementById('containerStorageOption');
    const containerOptions = document.getElementById('containerOptions');
    const multipleContainerOptions = document.getElementById('multipleContainerOptions');
    const singleContainerOptions = document.getElementById('singleContainerOptions');
    
    if (!directStorageOption || !containerStorageOption || !containerOptions) return;
    
    // Initialize container options based on sample type
    function updateContainerOptions() {
        // First check if container option is selected
        const useContainer = containerStorageOption && containerStorageOption.checked;
        
        // Then check sample type
        const sampleType = document.querySelector('input[name="sampleTypeOption"]:checked')?.value || 'single';
        const isMultiple = sampleType === 'multiple';
        
        // Show container options if container storage is selected
        containerOptions.classList.toggle('d-none', !useContainer);
        
        // Update multiple/single container options based on sample type
        if (useContainer && multipleContainerOptions && singleContainerOptions) {
            multipleContainerOptions.classList.toggle('d-none', !isMultiple);
            singleContainerOptions.classList.toggle('d-none', isMultiple);
            
            // Make sure the right option is selected
            if (isMultiple) {
                // Select "One container per package" by default
                const oneContainerPerPackage = document.getElementById('oneContainerPerPackage');
                if (oneContainerPerPackage) oneContainerPerPackage.checked = true;
                
                // Make sure "one container for all" is NOT selected
                const oneContainerForAll = document.getElementById('oneContainerForAll');
                if (oneContainerForAll) oneContainerForAll.checked = false;
            } else {
                // Select "New container" by default
                const newContainerOption = document.getElementById('newContainerOption');
                if (newContainerOption) newContainerOption.checked = true;
            }
            
            // Hide or show container details based on selection
            const existingContainerOption = document.getElementById('existingContainerOption');
            const existingContainerSelectArea = document.getElementById('existingContainerSelectArea');
            const containerDetailsSection = document.getElementById('containerDetailsSection');
            
            if (existingContainerOption && existingContainerOption.checked) {
                if (existingContainerSelectArea) existingContainerSelectArea.classList.remove('d-none');
                if (containerDetailsSection) containerDetailsSection.classList.add('d-none');
            } else {
                if (existingContainerSelectArea) existingContainerSelectArea.classList.add('d-none');
                if (containerDetailsSection) containerDetailsSection.classList.remove('d-none');
            }
        }
        
        // Update storage instructions
        updateStorageInstructions();
    }
    
    // Handle storage option changes
    const storageOptions = document.querySelectorAll('input[name="storageOption"]');
    storageOptions.forEach(option => {
        option.addEventListener('change', updateContainerOptions);
    });
    
    // Also listen for sample type changes to update container options
    const sampleTypeOptions = document.querySelectorAll('input[name="sampleTypeOption"]');
    sampleTypeOptions.forEach(option => {
        option.addEventListener('change', updateContainerOptions);
    });
    
    // Initial update
    updateContainerOptions();
}

// Setup container options
function setupContainerOptions() {
    // Single container options
    const newContainerOption = document.getElementById('newContainerOption');
    const existingContainerOption = document.getElementById('existingContainerOption');
    const existingContainerSelectArea = document.getElementById('existingContainerSelectArea');
    const containerDetailsSection = document.getElementById('containerDetailsSection');
    
    // Multiple container options
    const oneContainerForAll = document.getElementById('oneContainerForAll');
    const oneContainerPerPackage = document.getElementById('oneContainerPerPackage');
    
    // Handle single container options
    if (newContainerOption && existingContainerOption) {
        newContainerOption.addEventListener('change', function() {
            if (this.checked) {
                if (existingContainerSelectArea) existingContainerSelectArea.classList.add('d-none');
                if (containerDetailsSection) containerDetailsSection.classList.remove('d-none');
            }
        });
        
        existingContainerOption.addEventListener('change', function() {
            if (this.checked) {
                if (existingContainerSelectArea) existingContainerSelectArea.classList.remove('d-none');
                if (containerDetailsSection) containerDetailsSection.classList.add('d-none');
                
                fetchExistingContainers();
            }
        });
    }
    
    // Handle multiple container options
    if (oneContainerForAll && oneContainerPerPackage) {
        oneContainerForAll.addEventListener('change', function() {
            // When "one container for all" is selected, auto-select "No" for separate storage
            if (this.checked) {
                // With radio buttons, we just need to select the "No" option
                const separateStorageNo = document.getElementById('separateStorageNo');
                if (separateStorageNo) {
                    separateStorageNo.checked = true;
                    
                    // Trigger change event to ensure UI updates
                    const event = new Event('change');
                    separateStorageNo.dispatchEvent(event);
                }
            }
            
            // Update container location visibility if function is available
            if (typeof updateContainerLocationVisibility === 'function') {
                updateContainerLocationVisibility();
            }
            
            // Always update storage instructions
            updateStorageInstructions();
        });
        
        oneContainerPerPackage.addEventListener('change', function() {
            // Update container location visibility if function is available
            if (typeof updateContainerLocationVisibility === 'function') {
                updateContainerLocationVisibility();
            }
            
            // Ensure package count and amount per package are properly filled in
            const packageCountInput = document.querySelector('[name="packageCount"]');
            const amountPerPackageInput = document.querySelector('[name="amountPerPackage"]');
            
            if (packageCountInput && amountPerPackageInput) {
                // Ensure we have valid values
                if (!packageCountInput.value || parseInt(packageCountInput.value) < 1) {
                    packageCountInput.value = 1;
                }
                
                if (!amountPerPackageInput.value || parseInt(amountPerPackageInput.value) < 1) {
                    amountPerPackageInput.value = 1;
                }
                
                // Update the total amount calculation
                if (typeof updateTotalAmount === 'function') {
                    updateTotalAmount();
                }
            }
            
            // Check if we need to auto-enable separate storage
            if (this.checked) {
                const separateStorage = document.getElementById('separateStorage');
                if (separateStorage) {
                    // Enable separate storage by default for better UX, but don't force it
                    // Separage storage is now optional for one container per package
                    console.log("One container per package selected - enabling separate storage checkbox");
                }
            }
            
            // Clear any existing PackageLocations when changing container options
            if (window.PackageLocations && typeof window.PackageLocations.reset === 'function') {
                window.PackageLocations.reset();
                console.log("Reset package locations due to container option change");
            }
            
            // Always update storage instructions
            updateStorageInstructions();
        });
    }
    
    // Listen for container selection to get its location
    const existingContainerSelect = document.getElementById('existingContainerSelect');
    if (existingContainerSelect) {
        existingContainerSelect.addEventListener('change', function() {
            fetchContainerLocation(this.value);
        });
    }
    
    // Initial state
    if (newContainerOption && newContainerOption.checked) {
        if (existingContainerSelectArea) existingContainerSelectArea.classList.add('d-none');
        if (containerDetailsSection) containerDetailsSection.classList.remove('d-none');
    } else if (existingContainerOption && existingContainerOption.checked) {
        if (existingContainerSelectArea) existingContainerSelectArea.classList.remove('d-none');
        if (containerDetailsSection) containerDetailsSection.classList.add('d-none');
        
        fetchExistingContainers();
    }
}

// Setup container type creation
function setupContainerTypeCreation() {
    const useExistingTypeOption = document.getElementById('useExistingTypeOption');
    const createNewTypeOption = document.getElementById('createNewTypeOption');
    const existingTypeSection = document.getElementById('existingContainerTypeSection');
    const newContainerTypeSection = document.getElementById('newContainerTypeSection');
    
    if (!useExistingTypeOption || !createNewTypeOption) {
        console.log("Container type radio buttons not found, skipping setup");
        return;
    }
    
    console.log("Setting up container type radio buttons");
    
    // Function to handle container type option change
    function handleContainerTypeOptionChange() {
        const containerTypeSelect = document.getElementById('containerType');
        const containerCapacityInput = document.getElementById('containerCapacity');
        const newTypeNameInput = document.getElementById('newContainerTypeName');
        const newTypeCapacityInput = document.getElementById('newContainerTypeCapacity');
        
        // Check which option is selected
        const createNew = createNewTypeOption.checked;
        
        console.log(`Container type option changed: ${createNew ? 'Create new' : 'Use existing'}`);
        
        // Show/hide appropriate sections
        if (existingTypeSection) existingTypeSection.classList.toggle('d-none', createNew);
        if (newContainerTypeSection) newContainerTypeSection.classList.toggle('d-none', !createNew);
        
        // Manage required fields
        if (containerTypeSelect) {
            containerTypeSelect.required = !createNew;
            containerTypeSelect.disabled = createNew;
            // Clear the selection when switching to new container type creation
            if (createNew) {
                containerTypeSelect.value = '';
                // Important: Remove validation errors if we're creating a new type
                containerTypeSelect.setCustomValidity('');
            }
        }
        
        if (containerCapacityInput) {
            containerCapacityInput.disabled = createNew;
            // Clear capacity when switching to new container type creation
            if (createNew) containerCapacityInput.value = '';
        }
        
        // Handle required fields for new container type
        if (newTypeNameInput) newTypeNameInput.required = createNew;
        if (newTypeCapacityInput) newTypeCapacityInput.required = createNew;
        
        // Store the container type creation state in the global app state
        // This ensures it's preserved for all form submissions including multiple containers
        if (window.registerApp) {
            window.registerApp.createNewContainerType = createNew;
            console.log("Container type creation state stored in global state:", createNew);
        }
    }
    
    // Add event listeners to both radio buttons
    useExistingTypeOption.addEventListener('change', handleContainerTypeOptionChange);
    createNewTypeOption.addEventListener('change', handleContainerTypeOptionChange);
    
    // Call the function initially to set the correct state
    handleContainerTypeOptionChange();
    
    // Initialize global state with the current selection
    if (window.registerApp) {
        window.registerApp.createNewContainerType = createNewTypeOption.checked;
        console.log("Initial container type creation state set in global app:", createNewTypeOption.checked);
    }
}

// Function to fetch existing containers
function fetchExistingContainers() {
    const existingContainerSelect = document.getElementById('existingContainerSelect');
    if (!existingContainerSelect) {
        console.error("existingContainerSelect element not found!");
        return;
    }
    
    console.log("DEBUG: Fetching existing containers...");
    
    // Clear existing options except the first one
    while (existingContainerSelect.options.length > 1) {
        existingContainerSelect.remove(1);
    }
    
    // Add a "loading..." option
    const loadingOption = document.createElement('option');
    loadingOption.textContent = 'Loading containers...';
    loadingOption.disabled = true;
    existingContainerSelect.appendChild(loadingOption);
    
    // Fetch containers from server with cache-busting query parameter
    // This ensures we get fresh data every time, not cached results
    const timestamp = new Date().getTime();
    fetch(`/api/containers/available?_=${timestamp}`)
        .then(response => {
            console.log("DEBUG: Got response from /api/containers/available, status:", response.status);
            return response.json();
        })
        .then(data => {
            // Remove "loading..." option
            existingContainerSelect.remove(existingContainerSelect.options.length - 1);
            
            console.log("DEBUG: /api/containers/available API response:", data);
            
            if (data.containers && data.containers.length > 0) {
                data.containers.forEach(container => {
                    const option = document.createElement('option');
                    option.value = container.ContainerID;
                    
                    // Debug logging for container data
                    console.log("DEBUG: Container data:", container);
                    
                    // Include location information in the dropdown for better identification
                    const locationInfo = container.LocationName ? ` - Location: ${container.LocationName}` : '';
                    
                    // Add capacity information if available
                    let capacityInfo = '';
                    if (container.ContainerCapacity !== null) {
                        const availableCapacity = container.available_capacity !== undefined 
                            ? container.available_capacity 
                            : (container.ContainerCapacity - (container.sample_count || 0));
                        capacityInfo = ` (${container.sample_count || 0} samples, ${availableCapacity}/${container.ContainerCapacity} available)`;
                    } else {
                        capacityInfo = ` (${container.sample_count || 0} samples)`;
                    }
                    
                    option.textContent = `${container.ContainerID}: ${container.Description}${locationInfo}${capacityInfo}`;
                    existingContainerSelect.appendChild(option);
                });
                
                console.log(`DEBUG: Loaded ${data.containers.length} available containers`);
                
                // Enable the dropdown and select the first container by default
                if (data.containers.length > 0) {
                    existingContainerSelect.disabled = false;
                    // If there's a container, select the first one to fetch its location 
                    existingContainerSelect.selectedIndex = 1;
                    
                    // Trigger the change event to load the container's location
                    const event = new Event('change');
                    existingContainerSelect.dispatchEvent(event);
                }
            } else {
                const noContainersOption = document.createElement('option');
                noContainersOption.textContent = 'No available containers found';
                noContainersOption.disabled = true;
                existingContainerSelect.appendChild(noContainersOption);
                
                console.log('DEBUG: No available containers found');
            }
        })
        .catch(error => {
            console.error('ERROR: Error fetching containers:', error);
            const errorOption = document.createElement('option');
            errorOption.textContent = 'Error fetching containers';
            errorOption.disabled = true;
            existingContainerSelect.appendChild(errorOption);
        });
}

// Function to fetch container location
function fetchContainerLocation(containerId) {
    if (!containerId) {
        console.error("DEBUG: fetchContainerLocation called with no containerId");
        return;
    }
    
    console.log(`DEBUG: Fetching location for container ${containerId}`);
    
    fetch(`/api/containers/${containerId}/location`)
        .then(response => {
            console.log(`DEBUG: Got response from container location API, status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            console.log(`DEBUG: Container location API response:`, data);
            
            if (data.success && data.location) {
                console.log("DEBUG: Container location:", data.location);
                
                // Save container's location for later use in the global state
                registerApp.selectedContainerLocation = data.location;
                
                // Store the location ID in all possible field names for maximum compatibility
                if (data.location.LocationID) {
                    registerApp.containerLocationId = data.location.LocationID;
                    registerApp.locationId = data.location.LocationID;
                    registerApp.storageLocation = data.location.LocationID;
                    
                    console.log(`DEBUG: Stored container location IDs: 
                        locationId=${registerApp.locationId}, 
                        containerLocationId=${registerApp.containerLocationId},
                        storageLocation=${registerApp.storageLocation}`);
                }
                
                // Set skipLocationSelection to true since we'll use container's location
                // This will make the location grid auto-select this location in step 4
                registerApp.skipLocationSelection = true;
                console.log(`DEBUG: Setting skipLocationSelection=true, will use container location: ${data.location.LocationName}`);
            } else {
                console.error("DEBUG: No location data received for container or request failed");
            }
        })
        .catch(error => console.error("ERROR: Failed to fetch container location:", error));
}

// Define a new globally-accessible function that will override any existing implementations
window.updateContainerLocationVisibility = function() {
    console.log("FIXED implementation of updateContainerLocationVisibility called");
    const oneContainerPerPackage = document.getElementById('oneContainerPerPackage');
    const containerLocationSection = document.getElementById('containerLocationSelectSection');
    const multiLocationInfo = document.getElementById('multiLocationInfo');
    
    if (oneContainerPerPackage && containerLocationSection) {
        // Hide location dropdown when "one container per package" is selected
        if (oneContainerPerPackage.checked) {
            // Hide location dropdown
            containerLocationSection.classList.add('d-none');
            // Remove required attribute when hidden
            const containerLocationSelect = document.getElementById('containerLocation');
            if (containerLocationSelect) {
                containerLocationSelect.removeAttribute('required');
                // Clear any selected value to prevent it from being submitted
                containerLocationSelect.value = '';
            }
            
            // Show the multi-location info alert
            if (multiLocationInfo) {
                multiLocationInfo.style.display = 'block';
            }
            
            // CRITICAL FIX: Do *not* automatically check or disable "separate storage" checkbox
            // Let users explicitly decide if they want separate storage or not
            const separateStorage = document.getElementById('separateStorage');
            if (separateStorage) {
                // Do nothing with the checked state - leave it as the user set it
                // Make sure it's enabled so user can change it
                separateStorage.disabled = false;
                
                // Just trigger associated events to update the UI
                separateStorage.dispatchEvent(new Event('change'));
            }
        } else {
            // Show location dropdown
            containerLocationSection.classList.remove('d-none');
            // Add required attribute when visible
            const containerLocationSelect = document.getElementById('containerLocation');
            if (containerLocationSelect) {
                containerLocationSelect.setAttribute('required', 'required');
            }
            
            // Hide the multi-location info alert
            if (multiLocationInfo) {
                multiLocationInfo.style.display = 'none';
            }
            
            // Re-enable the separate storage checkbox
            const separateStorage = document.getElementById('separateStorage');
            if (separateStorage) {
                separateStorage.disabled = false;
            }
        }
    }
};