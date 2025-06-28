/**
 * Register - Main registration script
 * 
 * This file serves as the entry point for the sample registration system.
 * It defines the global registerApp object to share state between modules.
 */

// Create a global object to share state and functions
window.registerApp = {
    // Basic variables
    currentStep: 1,
    totalSteps: 4,
    scannedItems: [],
    selectedLocation: null,
    selectedContainerLocation: null,
    skipLocationSelection: false,
    REGISTRATION_EXPIRY_MONTHS: 2,
    // Container-related state
    containerIds: [],
    oneContainerPerPackage: false,
    
    // Store module states
    modulesLoaded: {
        validation: false,
        form: false,
        sampleTypes: false,
        storage: false,
        containers: false,
        identification: false
    },
    
    // Global functions that must be available
    requiredGlobalFunctions: [
        'validateCurrentStep',
        'updateRegistrationSummary',
        'handleFormSubmission'
    ],
    
    // Function to check if all required modules are loaded
    allModulesLoaded: function() {
        return this.modulesLoaded.validation && 
               this.modulesLoaded.form;
    },
    
    // Function to check if all required global functions are available
    checkGlobalFunctions: function() {
        const missing = [];
        
        this.requiredGlobalFunctions.forEach(funcName => {
            if (typeof window[funcName] !== 'function') {
                missing.push(funcName);
                console.error(`Required global function missing: ${funcName}`);
            }
        });
        
        return missing.length === 0 ? true : missing;
    },
    
    // SAFE GLOBAL VARIABLE to prevent duplicate init
    _initCount: 0,
    
    // Initialize the registration system when all modules are loaded
    init: function() {
        // GLOBAL LOCK on multiple initializations
        this._initCount++;
        console.log(`Running main registration initialization (call #${this._initCount})`);
        
        // STRONG GUARD: Never allow more than one initialization per page load
        if (this._initCount > 1) {
            console.warn(`BLOCKED initialization attempt #${this._initCount}`);
            return;
        }
        
        // MOST IMPORTANT PROTECTION: If we're already on step 2+, never reset to step 1
        // This uses sessionStorage which persists across the whole session
        if (sessionStorage.getItem('currentFormStep') && parseInt(sessionStorage.getItem('currentFormStep')) > 1) {
            // Get the saved step
            const savedStep = parseInt(sessionStorage.getItem('currentFormStep'));
            console.log(`CRITICAL: Restoring form to saved step ${savedStep} from storage, preventing reset`);
            this.currentStep = savedStep;
            
            // Immediately render the correct step
            if (typeof showStep === 'function') {
                setTimeout(function() {
                    showStep(savedStep);
                }, 0);
            }
            return;
        }
        
        // Check if all required global functions are available
        const functionsCheck = this.checkGlobalFunctions();
        if (functionsCheck !== true) {
            console.error('Missing required global functions:', functionsCheck);
            // We'll still proceed, but log a warning
            console.warn('Registration system may not work correctly due to missing functions');
        } else {
            console.log('All required global functions are available');
        }
        
        // Reset all global state
        this.currentStep = 1;
        this.scannedItems = [];
        this.selectedLocation = null;
        this.selectedContainerLocation = null;
        this.skipLocationSelection = false;
        
        // Initialize the first step
        if (typeof showStep === 'function') {
            showStep(1);
        }
        
        console.log('Registration system initialized');
    }
};

// Helper function to populate form fields from sample data
function populateFormWithSampleData(sampleData) {
    console.log("Populating form with sample data:", sampleData);
    
    try {
        // Populate Step 1: Reception Details
        // Handle supplier - try multiple ways as the field might be differently implemented
        if (sampleData.SupplierID) {
            // First try the newer search interface
            const supplierIdInput = document.getElementById('supplierIdInput');
            const selectedSupplierDisplay = document.getElementById('selectedSupplierDisplay');
            const selectedSupplierName = document.getElementById('selectedSupplierName');
            
            if (supplierIdInput && selectedSupplierDisplay && selectedSupplierName) {
                // New supplier search interface
                supplierIdInput.value = sampleData.SupplierID;
                
                // Update the display with supplier name if available
                if (sampleData.SupplierName) {
                    selectedSupplierName.textContent = sampleData.SupplierName;
                } else {
                    // Use the supplier name from the data if available
                    const allSuppliers = window.suppliers || [];
                    const supplier = allSuppliers.find(s => s.SupplierID == sampleData.SupplierID);
                    if (supplier) {
                        selectedSupplierName.textContent = supplier.SupplierName;
                    } else {
                        selectedSupplierName.textContent = "Supplier #" + sampleData.SupplierID;
                    }
                }
                
                selectedSupplierDisplay.classList.remove('d-none');
                
                // Update search input placeholder
                const supplierSearchInput = document.getElementById('supplierSearchInput');
                if (supplierSearchInput) {
                    supplierSearchInput.placeholder = "Supplier selected";
                }
            }
            
            // Then try the traditional dropdown as a fallback
            const supplierSelect = document.getElementById('supplier');
            if (supplierSelect) {
                for (let i = 0; i < supplierSelect.options.length; i++) {
                    if (supplierSelect.options[i].value == sampleData.SupplierID) {
                        supplierSelect.selectedIndex = i;
                        break;
                    }
                }
            }
        }
        
        // Populate Step 2: Sample Information
        // Part Number
        const partNumberField = document.querySelector('input[name="partNumber"]');
        if (partNumberField && sampleData.PartNumber) {
            partNumberField.value = sampleData.PartNumber;
        }
        
        // Description/Sample Name
        const descriptionField = document.querySelector('input[name="description"]');
        if (descriptionField && sampleData.Description) {
            descriptionField.value = sampleData.Description;
        }
        
        // Units
        if (sampleData.UnitID) {
            const unitSelect = document.querySelector('select[name="unit"], #unit');
            if (unitSelect) {
                for (let i = 0; i < unitSelect.options.length; i++) {
                    if (unitSelect.options[i].value == sampleData.UnitID) {
                        unitSelect.selectedIndex = i;
                        break;
                    }
                }
            }
        }
        
        // Handle all radio buttons 
        if (sampleData.SampleTypeID) {
            const sampleTypeRadios = document.querySelectorAll('input[name="sampleType"]');
            for (let i = 0; i < sampleTypeRadios.length; i++) {
                if (sampleTypeRadios[i].value == sampleData.SampleTypeID) {
                    sampleTypeRadios[i].checked = true;
                    // Trigger change event to update UI if needed
                    sampleTypeRadios[i].dispatchEvent(new Event('change'));
                    break;
                }
            }
        }
        
        // Handle all checkboxes (for multi-select options)
        if (sampleData.Options) {
            let options = [];
            
            // Try to parse options if it's a string
            if (typeof sampleData.Options === 'string') {
                try {
                    options = JSON.parse(sampleData.Options);
                } catch (e) {
                    // If it's a comma-separated string
                    options = sampleData.Options.split(',').map(opt => opt.trim());
                }
            } else if (Array.isArray(sampleData.Options)) {
                options = sampleData.Options;
            }
            
            // Check all checkboxes that match the options
            if (options.length > 0) {
                const checkboxes = document.querySelectorAll('input[type="checkbox"]');
                checkboxes.forEach(checkbox => {
                    if (options.includes(checkbox.value) || 
                        options.includes(checkbox.name) || 
                        options.includes(checkbox.id)) {
                        checkbox.checked = true;
                        checkbox.dispatchEvent(new Event('change'));
                    }
                });
            }
        }
        
        // Handle dropdown selects (for single-select options)
        document.querySelectorAll('select').forEach(select => {
            // Skip the unit select which is already handled
            if (select.id === 'unit' || select.name === 'unit') return;
            
            // Try to find a matching field in sample data based on select name
            const fieldName = select.name || select.id;
            if (fieldName && sampleData[fieldName]) {
                for (let i = 0; i < select.options.length; i++) {
                    if (select.options[i].value == sampleData[fieldName]) {
                        select.selectedIndex = i;
                        select.dispatchEvent(new Event('change'));
                        break;
                    }
                }
            }
        });
        
        // Handle custom fields based on sample type
        if (sampleData.CustomFields) {
            try {
                let customFields = {};
                
                // Allow for different formats of custom fields
                if (typeof sampleData.CustomFields === 'string') {
                    customFields = JSON.parse(sampleData.CustomFields);
                } else if (typeof sampleData.CustomFields === 'object') {
                    customFields = sampleData.CustomFields;
                }
                
                for (const fieldName in customFields) {
                    const field = document.querySelector(`[name="${fieldName}"]`);
                    if (field) {
                        field.value = customFields[fieldName];
                        // Trigger change event
                        field.dispatchEvent(new Event('change'));
                    }
                }
            } catch (e) {
                console.warn("Could not parse custom fields:", e);
            }
        }
        
        // Show success message
        const dataCopiedAlert = document.getElementById('dataCopiedAlert');
        const dataCopiedMessage = document.getElementById('dataCopiedMessage');
        if (dataCopiedAlert && dataCopiedMessage) {
            dataCopiedMessage.textContent = `Sample data copied from ${sampleData.SampleIDFormatted || 'previous sample'}`;
            dataCopiedAlert.classList.remove('d-none');
            
            // Auto-hide the alert after 5 seconds
            setTimeout(() => {
                dataCopiedAlert.classList.add('d-none');
            }, 5000);
        }
        
        // Validate the form if possible
        if (typeof validateIdentificationSection === 'function') {
            validateIdentificationSection();
        }
        
        // Try to move to next step if we're on step 1
        if (registerApp && registerApp.currentStep === 1) {
            // Only move to step 2 if we have the necessary fields
            if (typeof showStep === 'function') {
                showStep(2);
            }
        }
        
        return true;
    } catch (error) {
        console.error("Error populating form:", error);
        return false;
    }
}

// Copy registration from modal to form
function copyRegistration() {
    console.log("Copying registration data...");
    
    // Get the selected sample from the dropdown
    const dropdown = document.getElementById('existingRegistrations');
    
    if (!dropdown || dropdown.selectedIndex < 0) {
        alert("Please select a sample first");
        return;
    }
    
    const selectedOption = dropdown.options[dropdown.selectedIndex];
    
    if (!selectedOption || !selectedOption.dataset.sample) {
        alert("Error: No sample data available");
        return;
    }
    
    try {
        // Parse the sample data
        const sampleData = JSON.parse(selectedOption.dataset.sample);
        
        // Populate form with the data
        const success = populateFormWithSampleData(sampleData);
        
        if (success) {
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('copyRegistrationModal'));
            if (modal) {
                modal.hide();
            }
        } else {
            alert("There was a problem copying the sample data");
        }
    } catch (error) {
        console.error("Error copying registration:", error);
        alert("An error occurred while copying the registration data");
    }
}

// Load and copy the last registered sample
function copyLastRegisteredSample() {
    console.log("Copying last registered sample...");
    
    // Show loading spinner on the button
    const copyLastButton = document.getElementById('copyLastButton');
    if (copyLastButton) {
        const originalText = copyLastButton.innerHTML;
        copyLastButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Loading...';
        copyLastButton.disabled = true;
        
        // Fetch the most recent sample
        fetch('/api/samples/recent?limit=1')
        .then(response => response.json())
        .then(data => {
            copyLastButton.innerHTML = originalText;
            copyLastButton.disabled = false;
            
            if (data.success && data.samples && data.samples.length > 0) {
                const lastSample = data.samples[0];
                
                // Populate form with the last sample data
                const success = populateFormWithSampleData(lastSample);
                
                if (!success) {
                    alert("There was a problem copying the last sample data");
                }
            } else {
                alert("No previous samples found to copy");
            }
        })
        .catch(error => {
            copyLastButton.innerHTML = originalText;
            copyLastButton.disabled = false;
            console.error("Error fetching last sample:", error);
            alert("Error loading last sample: " + error.message);
        });
    }
}

// Global variables to ensure we only initialize once
window._REGISTER_INITIALIZED = window._REGISTER_INITIALIZED || false;
window._REGISTER_INIT_TIMER = null;

// Add a handler to clear the state when leaving the page
window.addEventListener('beforeunload', function() {
    // Clear session storage keys related to the form
    sessionStorage.removeItem('currentFormStep');
    sessionStorage.removeItem('hasVisitedStep2');
    
    
    // If we're in the register page, reset the form
    if (window.location.pathname.includes('/register')) {
        console.log('Leaving register page - resetting form state');
        if (typeof resetForm === 'function') {
            resetForm();
        }
    }
});

// Initialize when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Registration system loading...');
    
    // Reset the form if this is a fresh load of the register page
    if (window.location.pathname.includes('/register')) {
        // Clear any saved step information
        sessionStorage.removeItem('currentFormStep');
        sessionStorage.removeItem('hasVisitedStep2');
    }
    
    // CRITICAL: Block runtime.lastError double initialization issue
    if (window._REGISTER_INITIALIZED) {
        console.log('PREVENTED: Blocking duplicate DOMContentLoaded initialization');
        return;
    }
    window._REGISTER_INITIALIZED = true;
    
    // Clear any previously scheduled initialization
    if (window._REGISTER_INIT_TIMER) {
        clearTimeout(window._REGISTER_INIT_TIMER);
    }
    
    // Always work with a single timer for initialization
    window._REGISTER_INIT_TIMER = setTimeout(function() {
        console.log('Initializing form system...');
        registerApp.init();
        
        // Add event listener for the "Use last registered sample" button
        const copyLastButton = document.getElementById('copyLastButton');
        if (copyLastButton) {
            copyLastButton.addEventListener('click', function() {
                copyLastRegisteredSample();
            });
        }
    }, 500);
});

// Add extra protection against Chrome extension issues that trigger multiple init events
window.addEventListener('load', function() {
    // If we detect the error signature in the console logs, force restore the step
    if (window._ALREADY_LOADED) {
        console.log('PREVENTED: Blocking duplicate window.load event');
        
        // Check if we need to restore step
        if (sessionStorage.getItem('currentFormStep') && 
            parseInt(sessionStorage.getItem('currentFormStep')) > 1) {
            
            const savedStep = parseInt(sessionStorage.getItem('currentFormStep'));
            console.log(`Load event - restoring to step ${savedStep}`);
            
            // Small delay to ensure DOM is ready
            setTimeout(function() {
                if (typeof showStep === 'function') {
                    showStep(savedStep);
                }
            }, 200);
        }
        return;
    }
    window._ALREADY_LOADED = true;
});