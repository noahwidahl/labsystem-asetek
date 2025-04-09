/**
 * Register Form - Core functionality for registration form navigation
 */

// Initialize when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Form module loading...');
    
    // Set default expiry date to 2 months ahead
    setDefaultExpiryDate();
    
    // Setup registration form steps
    setupRegistrationSteps();
    
    // Add a simple mechanism to prevent the unexpected navigation issue
    // This is the simplest possible fix: If we've already been to step 2 in this session,
    // don't let the form jump back to step 1 unexpectedly
    window.addEventListener('focusin', function(e) {
        if (registerApp.currentStep === 2 && sessionStorage.getItem('focusedInStep2')) {
            // If we try to focus on a field in step 2 but the form has moved back to step 1,
            // forcibly go back to step 2
            if (document.querySelector('#step1.active') && e.target.closest('#step2')) {
                console.log('Detected unexpected jump to step 1, forcing back to step 2');
                showStep(2);
            }
        }
    });
    
    // Mark this module as loaded in the global state
    if (window.registerApp) {
        window.registerApp.modulesLoaded.form = true;
        console.log('Form module loaded');
    } else {
        console.error('registerApp not found - form module cannot register');
    }
});

// Set default expiry date
function setDefaultExpiryDate() {
    const expiryInput = document.querySelector('input[name="expiryDate"]');
    if (expiryInput) {
        const defaultDate = new Date();
        defaultDate.setMonth(defaultDate.getMonth() + registerApp.REGISTRATION_EXPIRY_MONTHS);
        const dateString = defaultDate.toISOString().split('T')[0];
        expiryInput.value = dateString;
    }
}

// Cache for current step to detect unexpected navigation
let _previousRenderStep = null;

// Show a specific step in the form
function showStep(step) {
    // If we've already shown this step in last 500ms, avoid double-render
    if (_previousRenderStep === step) {
        console.log(`Ignoring duplicate render of step ${step}`);
        return;
    }
    _previousRenderStep = step;
    setTimeout(() => { _previousRenderStep = null; }, 500);
    
    console.log(`Showing step ${step} (current: ${registerApp.currentStep})`);
    
    // Ensure step is a valid integer
    step = parseInt(step) || 1;
    
    // STRONGEST PROTECTION: If user has already visited step 2 and page tries to go back to step 1,
    // force the flow to step 2 instead
    if (step === 1 && sessionStorage.getItem('hasVisitedStep2') && registerApp.currentStep !== 1) {
        console.log("⚠️ BLOCKED unexpected navigation back to step 1");
        step = parseInt(sessionStorage.getItem('currentFormStep')) || 2;
    }
    
    // Ensure step is within valid range
    if (step < 1) step = 1;
    if (step > registerApp.totalSteps) step = registerApp.totalSteps;
    
    const formSteps = document.querySelectorAll('.form-step');
    formSteps.forEach(el => {
        el.classList.remove('active');
    });

    const currentStepElement = document.querySelector(`#step${step}`);
    if (currentStepElement) {
        currentStepElement.classList.add('active');
        updateProgress(step);
        updateNavigationButtons(step);

        // Initialize the current page
        if (step === 1) {
            initReceptionDate();
        } else if (step === 3 && document.getElementById('hasSerialNumbers')?.checked) {
            setupBarcodeInput();
        } else if (step === 4) {
            if (typeof setupStorageGrid === 'function') {
                setupStorageGrid();
            } else {
                console.error("setupStorageGrid function not found");
            }
        }
        
        // Scroll to top of the form
        const formContainer = document.querySelector('.registration-form');
        if (formContainer) {
            formContainer.scrollTop = 0;
        }
        
        // CRITICAL STATE TRACKING: Always save the current step in sessionStorage
        // This ensures we can restore to the correct step if there's a reset
        sessionStorage.setItem('currentFormStep', step.toString());
        
        // When changing from step 1 to step 2, add special handling to fix the bug
        // where the form jumps back to step 1 the first time you enter information
        if (registerApp.currentStep === 1 && step === 2) {
            console.log('First navigation to step 2 detected');
            // Push a new browser history state
            try {
                window.history.pushState({step: 2}, '');
            } catch(e) {
                console.warn('History API not available:', e);
            }
            
            // Ensure we record this state transition
            sessionStorage.setItem('hasVisitedStep2', 'true');
        }
        
        // Update current step global variable
        registerApp.currentStep = step;
        
        // Make sure navigation buttons are visible
        const nextButton = document.getElementById('nextButton');
        const prevButton = document.getElementById('prevButton');
        
        if (nextButton) {
            nextButton.style.display = 'block';
            nextButton.textContent = step === registerApp.totalSteps ? 'Save' : 'Next';
        }
        
        if (prevButton) {
            prevButton.style.display = step > 1 ? 'block' : 'none';
        }
    } else {
        console.error(`Step element #step${step} not found`);
    }
}

// Update progress bar
function updateProgress(step) {
    const progress = ((step - 1) / (registerApp.totalSteps - 1)) * 100;
    
    // Update all progress bars on the page
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        bar.style.width = `${progress}%`;
    });
    
    // Update steps display
    const steps = document.querySelectorAll('.step');
    steps.forEach((el, index) => {
        el.classList.remove('active', 'completed');
        
        if (index + 1 < step) {
            el.classList.add('completed');
        } else if (index + 1 === step) {
            el.classList.add('active');
        }
    });
}

// Update navigation buttons
function updateNavigationButtons(step) {
    const prevButton = document.getElementById('prevButton');
    const nextButton = document.getElementById('nextButton');

    if (prevButton) {
        prevButton.style.display = step === 1 ? 'none' : 'block';
    }

    if (nextButton) {
        nextButton.textContent = step === registerApp.totalSteps ? 'Save' : 'Next';
    }
}

// Setup registration form navigation
function setupRegistrationSteps() {
    const nextButton = document.getElementById('nextButton');
    const prevButton = document.getElementById('prevButton');
    
    if (nextButton) {
        nextButton.addEventListener('click', function() {
            console.log('Next button clicked, current step:', registerApp.currentStep);
            
            if (registerApp.currentStep === registerApp.totalSteps) {
                console.log('Final step, calling handleFormSubmission directly');
                
                // Check if the function exists before calling it
                if (typeof window.handleFormSubmission === 'function') {
                    window.handleFormSubmission();
                } else {
                    console.error("handleFormSubmission not found in register-form.js - using fallback");
                    
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
                nextStep();
            }
        });
    }
    
    if (prevButton) {
        prevButton.addEventListener('click', function() {
            previousStep();
        });
    }
}

// Go to next step
function nextStep() {
    console.log("Next Step function called. Current step:", registerApp.currentStep);
    
    // Ensure the validation function exists
    if (typeof window.validateCurrentStep !== 'function') {
        console.error("validateCurrentStep function not found! Checking if module is loaded:", 
            registerApp.modulesLoaded.validation);
        
        // Check for delayed initialization - retry with a short delay
        if (!registerApp.validationCheckAttempted) {
            registerApp.validationCheckAttempted = true;
            console.log("First validation check attempt - retrying in 500ms");
            
            setTimeout(function() {
                console.log("Retrying nextStep after delay");
                nextStep();
            }, 500);
            return;
        }
        
        // Fallback - proceed without validation
        console.warn("Proceeding without validation");
        proceedToNextStep(true);
        return;
    }
    
    // Function exists, try to validate
    try {
        if (validateCurrentStep()) {
            proceedToNextStep(true);
        }
    } catch (error) {
        console.error("Error during validation:", error);
        showErrorMessage("An error occurred. Please try again.");
    }
    
    // Helper function to proceed to next step
    function proceedToNextStep(validationPassed) {
        const hasSerialNumbers = document.getElementById('hasSerialNumbers')?.checked || false;
        
        // Check if this is the last step and we need to show summary
        if (registerApp.currentStep === registerApp.totalSteps) {
            // Show registration summary before submission
            const registrationSummary = document.getElementById('registrationSummary');
            if (registrationSummary) {
                registrationSummary.classList.remove('d-none');
                
                // Try to update the summary
                if (typeof updateRegistrationSummary === 'function') {
                    try {
                        updateRegistrationSummary();
                    } catch (error) {
                        console.error("Error updating summary:", error);
                    }
                }
                
                // Change next button text to "Confirm and Save"
                const nextButton = document.getElementById('nextButton');
                if (nextButton) {
                    nextButton.textContent = 'Confirm and Save';
                }
                
                // If we have fixed navigation, update that too
                const fixedNextButton = document.getElementById('fixedNextButton');
                if (fixedNextButton) {
                    fixedNextButton.textContent = 'Confirm and Save';
                }
                
                // We don't actually advance to the next step here
                return;
            }
        }
        
        // Always increment to next step first
        registerApp.currentStep += 1;
        
        // If we land on identification step (step 3) and there are no serial numbers, skip to step 4
        if (registerApp.currentStep === 3 && !hasSerialNumbers) {
            registerApp.currentStep = 4;
        }
        
        // Make sure we don't go beyond the maximum number of steps
        registerApp.currentStep = Math.min(registerApp.currentStep, registerApp.totalSteps);
        
        console.log("Moving to step:", registerApp.currentStep);
        showStep(registerApp.currentStep);
    }
}

// Go to previous step
function previousStep() {
    const hasSerialNumbers = document.getElementById('hasSerialNumbers')?.checked || false;
    
    // Always decrement to previous step first
    registerApp.currentStep -= 1;
    
    // If we land on identification step (step 3) and there are no serial numbers, skip to step 2
    if (registerApp.currentStep === 3 && !hasSerialNumbers) {
        registerApp.currentStep = 2;
    }
    
    // Make sure we don't go below the first step
    registerApp.currentStep = Math.max(registerApp.currentStep, 1);
    
    showStep(registerApp.currentStep);
}

// UI Message functions
function showSuccessMessage(message) {
    // Remove existing error messages
    clearValidationErrors();
    
    const successToast = document.createElement('div');
    successToast.className = 'custom-toast success-toast';
    successToast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-check-circle"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">Success</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    document.body.appendChild(successToast);

    // Add 'show' class after a short delay (for animation effect)
    setTimeout(() => successToast.classList.add('show'), 10);

    // Remove automatically after 3 seconds
    setTimeout(() => {
        successToast.classList.remove('show');
        setTimeout(() => successToast.remove(), 300);
    }, 3000);
}

function showErrorMessage(message, field = null) {
    const errorToast = document.createElement('div');
    errorToast.className = 'custom-toast error-toast';
    errorToast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-exclamation-circle"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">Error</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    document.body.appendChild(errorToast);

    // Add 'show' class after a short delay (for animation effect)
    setTimeout(() => errorToast.classList.add('show'), 10);

    // Remove automatically after 5 seconds
    setTimeout(() => {
        errorToast.classList.remove('show');
        setTimeout(() => errorToast.remove(), 300);
    }, 5000);
    
    // If a specific field is specified, mark it with an error
    if (field) {
        const fieldElement = document.querySelector(`[name="${field}"]`);
        if (fieldElement) {
            fieldElement.classList.add('field-error');
            
            // Add error message below the field
            const fieldContainer = fieldElement.closest('.form-group');
            if (fieldContainer) {
                // Remove any existing error messages
                const existingError = fieldContainer.querySelector('.field-error-message');
                if (existingError) existingError.remove();
                
                // Add new error message
                const errorMsg = document.createElement('div');
                errorMsg.className = 'field-error-message';
                errorMsg.textContent = message;
                fieldContainer.appendChild(errorMsg);
                
                // Add listeners to remove error marking on input
                fieldElement.addEventListener('input', function() {
                    this.classList.remove('field-error');
                    const errorMsg = fieldContainer.querySelector('.field-error-message');
                    if (errorMsg) errorMsg.remove();
                });
            }
        }
    }
}

function showWarningMessage(message) {
    const warningToast = document.createElement('div');
    warningToast.className = 'custom-toast warning-toast';
    warningToast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-exclamation-triangle"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">Warning</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    document.body.appendChild(warningToast);

    // Add 'show' class after a short delay (for animation effect)
    setTimeout(() => warningToast.classList.add('show'), 10);

    // Remove automatically after 4 seconds
    setTimeout(() => {
        warningToast.classList.remove('show');
        setTimeout(() => warningToast.remove(), 300);
    }, 4000);
}

// Helper function to remove all validation errors
function clearValidationErrors() {
    // Remove error classes from all fields
    document.querySelectorAll('.field-error').forEach(field => {
        field.classList.remove('field-error');
    });
    
    // Remove all error messages
    document.querySelectorAll('.field-error-message').forEach(msg => {
        msg.remove();
    });
}

// Initialize reception date
function initReceptionDate() {
    // Nothing to do here in this implementation
}

// Reset form
function resetForm() {
    registerApp.currentStep = 1;
    registerApp.scannedItems = [];
    
    document.querySelectorAll('input:not([type="radio"]):not([type="checkbox"])').forEach(input => {
        input.value = '';
        input.classList.remove('invalid');
    });
    
    document.querySelectorAll('select').forEach(select => {
        select.selectedIndex = 0;
        select.classList.remove('invalid');
    });
    
    // Reset checkboxes
    if (document.getElementById('hasSerialNumbers')) {
        document.getElementById('hasSerialNumbers').checked = false;
    }
    
    setDefaultExpiryDate();
    showStep(1);
}