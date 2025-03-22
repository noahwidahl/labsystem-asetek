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
        if (containerDetailsSection) {
            containerDetailsSection.classList.toggle('d-none', !containersEnabled);
        }
        
        console.log('Container creation is now:', containersEnabled ? 'enabled' : 'disabled');
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
                
                // Run update first time to set initial state
                _updateContainerOptions();
            }
        },
        
        // Return if container creation is enabled
        isEnabled: function() {
            return containersEnabled;
        },
        
        // Add to form data before submission
        addToFormData: function(formData) {
            if (!formData) return formData;
            
            formData.createContainers = containersEnabled;
            
            // Add any other container-related fields if needed
            if (containersEnabled) {
                formData.containerDescription = document.getElementById('containerDescription')?.value || '';
                formData.containerIsMixed = document.getElementById('containerIsMixed')?.checked || false;
            }
            
            return formData;
        }
    };
})();