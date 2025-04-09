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

// Global variables to ensure we only initialize once
window._REGISTER_INITIALIZED = window._REGISTER_INITIALIZED || false;
window._REGISTER_INIT_TIMER = null;

// Add a handler to clear the state when leaving the page
window.addEventListener('beforeunload', function() {
    // Clear session storage keys related to the form
    sessionStorage.removeItem('currentFormStep');
    sessionStorage.removeItem('hasVisitedStep2');
    
    // Reset package locations if available
    if (typeof window.PackageLocations !== 'undefined' && typeof window.PackageLocations.reset === 'function') {
        window.PackageLocations.reset();
    }
    
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