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
    
    // Mark this module as loaded in the global state
    if (window.registerApp) {
        window.registerApp.modulesLoaded.containers = true;
        console.log('Containers module loaded');
    } else {
        console.error('registerApp not found - containers module cannot register');
    }
});

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
                // Select "One container for all" by default
                const oneContainerForAll = document.getElementById('oneContainerForAll');
                if (oneContainerForAll) oneContainerForAll.checked = true;
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
            updateStorageInstructions();
        });
        
        oneContainerPerPackage.addEventListener('change', function() {
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
    const createContainerTypeCheckbox = document.getElementById('createContainerType');
    const newContainerTypeSection = document.getElementById('newContainerTypeSection');
    const containerTypeSelect = document.getElementById('containerType');
    const containerCapacityInput = document.getElementById('containerCapacity');
    
    if (!createContainerTypeCheckbox || !newContainerTypeSection) return;
    
    createContainerTypeCheckbox.addEventListener('change', function() {
        newContainerTypeSection.classList.toggle('d-none', !this.checked);
        
        // Disable existing type fields when creating new type
        if (containerTypeSelect) containerTypeSelect.disabled = this.checked;
        if (containerCapacityInput) containerCapacityInput.disabled = this.checked;
    });
    
    // Initial state
    newContainerTypeSection.classList.toggle('d-none', !createContainerTypeCheckbox.checked);
    if (containerTypeSelect) containerTypeSelect.disabled = createContainerTypeCheckbox.checked;
    if (containerCapacityInput) containerCapacityInput.disabled = createContainerTypeCheckbox.checked;
}

// Function to fetch existing containers
function fetchExistingContainers() {
    const existingContainerSelect = document.getElementById('existingContainerSelect');
    if (!existingContainerSelect) return;
    
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
        .then(response => response.json())
        .then(data => {
            // Remove "loading..." option
            existingContainerSelect.remove(existingContainerSelect.options.length - 1);
            
            if (data.containers && data.containers.length > 0) {
                data.containers.forEach(container => {
                    const option = document.createElement('option');
                    option.value = container.ContainerID;
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
                
                console.log(`Loaded ${data.containers.length} available containers`);
                
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
                
                console.log('No available containers found');
            }
        })
        .catch(error => {
            console.error('Error fetching containers:', error);
            const errorOption = document.createElement('option');
            errorOption.textContent = 'Error fetching containers';
            errorOption.disabled = true;
            existingContainerSelect.appendChild(errorOption);
        });
}

// Function to fetch container location
function fetchContainerLocation(containerId) {
    if (!containerId) return;
    
    fetch(`/api/containers/${containerId}/location`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.location) {
                console.log("Container placering:", data.location);
                // Save container's location for later use in the global state
                registerApp.selectedContainerLocation = data.location;
                
                // Set skipLocationSelection to true since we'll use container's location
                // This will make the location grid auto-select this location in step 4
                registerApp.skipLocationSelection = true;
                console.log("Setting skipLocationSelection=true, will use container location:", data.location.LocationName);
            }
        })
        .catch(error => console.error("Fejl ved hentning af containerplacering:", error));
}