/**
 * Container module to handle container functionality on the registration page
 */
const ContainerModule = (function() {
    // Private variables
    let containersEnabled = false;
    
    // Private methods
    function _updateContainerOptions() {
        const createContainersCheckbox = document.getElementById('createContainers');
        if (!createContainersCheckbox) return;
        
        containersEnabled = createContainersCheckbox.checked;
        
        // Container-specific section to show/hide based on checkbox
        const containerDetailsSection = document.getElementById('containerDetailsSection');
        const existingContainerSection = document.getElementById('existingContainerSection');
        
        if (containerDetailsSection) {
            containerDetailsSection.classList.toggle('d-none', !containersEnabled);
        }
        
        if (existingContainerSection) {
            existingContainerSection.classList.toggle('d-none', !containersEnabled);
        }
        
        // DO NOT pre-fill container description with sample name, as these serve different purposes
        
        if (containersEnabled) {
            // Fetch container types
            _fetchContainerTypes();
        }
        
        console.log('Container creation is now:', containersEnabled ? 'enabled' : 'disabled');
    }
    
    // Fetch container types from server (NOTE: Now rendered server-side)
    function _fetchContainerTypes() {
        // Now using server-side rendering from register.py
        // This function is kept for backwards compatibility
        
        // We don't auto-populate container description from sample name anymore
        // as requested, as they serve different purposes
    }
    
    // Set up container type toggle
    function _setupContainerTypeToggle() {
        const createTypeCheckbox = document.getElementById('createContainerType');
        const containerTypeSelect = document.getElementById('containerType');
        const newTypeSection = document.getElementById('newContainerTypeSection');
        const capacityInput = document.getElementById('containerCapacity');
        
        if (!createTypeCheckbox || !containerTypeSelect || !newTypeSection) return;
        
        // Toggle between container type dropdown and create new section
        createTypeCheckbox.addEventListener('change', function() {
            const createNew = this.checked;
            
            // Disable both container type dropdown and capacity input when creating new type
            containerTypeSelect.disabled = createNew;
            capacityInput.disabled = createNew; // Disable capacity input as we'll use the new type's capacity instead
            
            newTypeSection.classList.toggle('d-none', !createNew);
            
            // Clear validation errors on toggle
            if (createNew) {
                // We're creating a new type, clear validation on select and capacity
                containerTypeSelect.classList.remove('is-invalid');
                capacityInput.classList.remove('is-invalid');
                
                const selectFeedback = containerTypeSelect.nextElementSibling;
                if (selectFeedback && selectFeedback.classList.contains('invalid-feedback')) {
                    selectFeedback.remove();
                }
                
                const capacityFeedback = capacityInput.nextElementSibling;
                if (capacityFeedback && capacityFeedback.classList.contains('invalid-feedback')) {
                    capacityFeedback.remove();
                }
                
                // Clear container type selection and capacity
                containerTypeSelect.value = '';
                capacityInput.value = ''; // Clear capacity as it will come from the new type
                
                // Focus on new type name field
                setTimeout(() => {
                    document.getElementById('newContainerTypeName').focus();
                }, 100);
            } else {
                // We're using existing type, clear validation on new type fields
                document.getElementById('newContainerTypeName').classList.remove('is-invalid');
                const typeFeedback = document.getElementById('newContainerTypeName').nextElementSibling;
                if (typeFeedback && typeFeedback.classList.contains('invalid-feedback')) {
                    typeFeedback.remove();
                }
                
                // Enable capacity input again
                capacityInput.disabled = false;
                
                // If container type is already selected, update the capacity
                if (containerTypeSelect.value) {
                    const selectedOption = containerTypeSelect.options[containerTypeSelect.selectedIndex];
                    const typeData = selectedOption.dataset;
                    
                    if (typeData.capacity && !capacityInput.value) {
                        capacityInput.value = typeData.capacity;
                    }
                }
                
                // Focus on container type select
                setTimeout(() => {
                    containerTypeSelect.focus();
                }, 100);
            }
        });
    }
    
    // Setup container type selection
    function _setupContainerTypeSelection() {
        const containerTypeSelect = document.getElementById('containerType');
        const capacityInput = document.getElementById('containerCapacity');
        
        if (!containerTypeSelect || !capacityInput) return;
        
        // Lookup capacity when type changes
        containerTypeSelect.addEventListener('change', function() {
            const typeId = this.value;
            if (!typeId) {
                capacityInput.value = '';
                capacityInput.placeholder = 'Capacity (required)';
                return;
            }
            
            // Find the selected option
            const selectedOption = this.options[this.selectedIndex];
            const typeData = selectedOption.dataset;
            
            // Set default capacity if available
            if (typeData.capacity) {
                capacityInput.value = typeData.capacity;
                capacityInput.placeholder = `Default: ${typeData.capacity}`;
            }
            
            // Remove any validation error on container type
            containerTypeSelect.classList.remove('is-invalid');
            const feedback = containerTypeSelect.nextElementSibling;
            if (feedback && feedback.classList.contains('invalid-feedback')) {
                feedback.remove();
            }
        });
        
        // Initial setup - populate capacity if a type is already selected
        if (containerTypeSelect.value) {
            const selectedOption = containerTypeSelect.options[containerTypeSelect.selectedIndex];
            const typeData = selectedOption.dataset;
            
            if (typeData.capacity && !capacityInput.value) {
                capacityInput.value = typeData.capacity;
                capacityInput.placeholder = `Default: ${typeData.capacity}`;
            }
        }
    }
    
    // Setup radio toggle between existing and new container
    function _setupContainerOptionToggle() {
        const newContainerOption = document.getElementById('newContainerOption');
        const existingContainerOption = document.getElementById('existingContainerOption');
        const containerDetailsSection = document.getElementById('containerDetailsSection');
        const existingContainerSelectArea = document.getElementById('existingContainerSelectArea');
        
        if (!newContainerOption || !existingContainerOption) return;
        
        // Handle radio button selection
        newContainerOption.addEventListener('change', function() {
            if (this.checked) {
                containerDetailsSection.classList.remove('d-none');
                existingContainerSelectArea.classList.add('d-none');
            }
        });
        
        existingContainerOption.addEventListener('change', function() {
            if (this.checked) {
                containerDetailsSection.classList.add('d-none');
                existingContainerSelectArea.classList.remove('d-none');
                _fetchExistingContainers();
            }
        });
    }
    
    // Fetch existing containers
    function _fetchExistingContainers() {
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
        
        // Fetch containers from server
        fetch('/api/containers/available')
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
                        option.textContent = `${container.ContainerID}: ${container.Description}${locationInfo} (${container.sample_count || 0} samples)`;
                        existingContainerSelect.appendChild(option);
                    });
                } else {
                    const noContainersOption = document.createElement('option');
                    noContainersOption.textContent = 'No available containers found';
                    noContainersOption.disabled = true;
                    existingContainerSelect.appendChild(noContainersOption);
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
    
    // Validate container data - this is now a helper function only used externally
    function _validateContainerData() {
        // This function is deprecated - validation is done directly in the validate method
        return ContainerModule.validate();
    }
    
    // Show field-specific errors
    function _showFieldError(field, message) {
        if (!field) return;
        
        // Add invalid class to the field
        field.classList.add('is-invalid');
        
        // Create feedback element if it doesn't exist
        let feedback = field.nextElementSibling;
        if (!feedback || !feedback.classList.contains('invalid-feedback')) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            field.parentNode.insertBefore(feedback, field.nextSibling);
        }
        
        // Set error message
        feedback.textContent = message;
    }
    
    // Clear validation errors
    function _clearValidationErrors() {
        // Remove is-invalid class from all inputs
        document.querySelectorAll('.is-invalid').forEach(element => {
            element.classList.remove('is-invalid');
        });
        
        // Remove all validation feedback elements
        document.querySelectorAll('.invalid-feedback').forEach(element => {
            element.remove();
        });
    }
    
    // Public API
    return {
        init: function() {
            console.log("Container module initialized");
            
            // Initialize status based on current checkbox state
            const createContainersCheckbox = document.getElementById('createContainers');
            if (createContainersCheckbox) {
                containersEnabled = createContainersCheckbox.checked;
                
                // Listen for changes on the container checkbox
                createContainersCheckbox.addEventListener('change', _updateContainerOptions);
                
                // Set up container type functionality
                _setupContainerTypeToggle();
                _setupContainerTypeSelection();
                _setupContainerOptionToggle();
                
                // Create route to handle container type API requests if not available
                // This is typically done on the server side, but we mock it here
                if (!window.containerTypesAPIAvailable) {
                    // Mock route - this would be handled by the server in a real implementation
                    console.log("Setting up mock container types API");
                    
                    // This is just for future expansion - implemented on server side
                }
                
                // Run update first time to set initial state
                _updateContainerOptions();
            }
        },
        
        // Return if container creation is enabled
        isEnabled: function() {
            return containersEnabled;
        },
        
        // Validate container data
        validate: function() {
            if (!containersEnabled) return true;
            
            // Use the existing container if that option is selected
            const existingContainerOption = document.getElementById('existingContainerOption');
            if (existingContainerOption && existingContainerOption.checked) {
                const existingContainerId = document.getElementById('existingContainerSelect').value;
                if (!existingContainerId) {
                    alert('Please select an existing container');
                    return false;
                }
                return true;
            }

            // Clear previous validation errors
            _clearValidationErrors();
            
            // Validate new container fields
            const description = document.getElementById('containerDescription');
            if (!description.value) {
                _showFieldError(description, 'Container description is required');
                return false;
            }
            
            const createNewType = document.getElementById('createContainerType').checked;
            let isValid = true;
            
            if (createNewType) {
                // Validate new container type
                const typeName = document.getElementById('newContainerTypeName');
                if (!typeName.value) {
                    _showFieldError(typeName, 'Container type name is required');
                    isValid = false;
                }
                
                const typeCapacity = document.getElementById('newContainerTypeCapacity');
                if (!typeCapacity.value) {
                    _showFieldError(typeCapacity, 'Container type capacity is required');
                    isValid = false;
                }
                
                // When creating a new type, capacity validation is not needed for the container
                // as it will use the new type's capacity
            } else {
                // Validate container type selection
                const containerType = document.getElementById('containerType');
                if (!containerType.value) {
                    _showFieldError(containerType, 'Please select a container type');
                    isValid = false;
                }
                
                // Only validate capacity if not creating a new type
                const capacity = document.getElementById('containerCapacity');
                if (!capacity.value) {
                    _showFieldError(capacity, 'Container capacity is required');
                    isValid = false;
                }
            }
            
            // Validate location
            const location = document.getElementById('containerLocation');
            if (!location.value) {
                _showFieldError(location, 'Storage location is required');
                isValid = false;
            }
            
            return isValid;
        },
        
        // Add to form data before submission
        addToFormData: function(formData) {
            if (!formData) return formData;
            
            formData.createContainers = containersEnabled;
            
            if (containersEnabled) {
                // Check if using existing container
                const existingContainerOption = document.getElementById('existingContainerOption');
                if (existingContainerOption && existingContainerOption.checked) {
                    formData.useExistingContainer = true;
                    formData.existingContainerId = document.getElementById('existingContainerSelect').value;
                } else {
                    // Add new container data
                    formData.containerDescription = document.getElementById('containerDescription').value;
                    formData.containerIsMixed = document.getElementById('containerIsMixed').checked;
                    formData.containerCapacity = document.getElementById('containerCapacity').value;
                    formData.containerLocationId = document.getElementById('containerLocation').value;
                    
                    // Check if creating new container type
                    const createContainerType = document.getElementById('createContainerType').checked;
                    if (createContainerType) {
                        formData.newContainerType = {
                            typeName: document.getElementById('newContainerTypeName').value,
                            capacity: document.getElementById('newContainerTypeCapacity').value,
                            description: document.getElementById('newContainerTypeDescription').value || ''
                        };
                    } else {
                        formData.containerTypeId = document.getElementById('containerType').value;
                    }
                }
            }
            
            return formData;
        }
    };
})();