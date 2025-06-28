/**
 * Register Sample Types - Handling different sample types in the registration form
 */

// Initialize when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Sample types module loading...');
    
    // Set up sample type handling
    setupSampleTypeOptions();
    
    // Mark this module as loaded in the global state
    if (window.registerApp) {
        window.registerApp.modulesLoaded.sampleTypes = true;
        console.log('Sample types module loaded');
    } else {
        console.error('registerApp not found - sample types module cannot register');
    }
});

// Variables for sample handling
let scannedItems = [];

// Setup sample type options (Single, Bulk)
function setupSampleTypeOptions() {
    const singleSampleOption = document.getElementById('singleSampleOption');
    const bulkSampleOption = document.getElementById('bulkSampleOption');
    const singleContainerOptions = document.getElementById('singleContainerOptions');
    const totalAmountInput = document.querySelector('[name="totalAmount"]');
    const unitSelect = document.querySelector('[name="unit"]');
    
    if (!unitSelect) return; // Exit early if unit select doesn't exist
    
    // Get container options sections
    const containerOptions = document.getElementById('containerOptions');
    
    // Save all original unit options for later use
    const allUnitOptions = Array.from(unitSelect.options);
    
    // Find pcs/stk option
    const pcsOption = allUnitOptions.find(opt => 
        opt.textContent.trim().toLowerCase() === 'stk' || 
        opt.textContent.trim().toLowerCase() === 'pcs');
        
    // Rename any "stk" options to "pcs" for consistency
    allUnitOptions.forEach(option => {
        if (option.textContent.trim().toLowerCase() === 'stk') {
            option.textContent = 'pcs';
        }
    });
    
    // Function to update UI based on sample type
    function updateSampleTypeUI(sampleType) {
        console.log('Updating sample type UI for:', sampleType);
        
        // Update unit options based on sample type
        updateUnitOptions(sampleType === 'bulk');
        
        // Update total amount input based on sample type
        if (totalAmountInput) {
            // For single or bulk, total is manually entered
            totalAmountInput.readOnly = false;
        }
    }
    
    // Helper function to update unit options
    function updateUnitOptions(isBulk) {
        // Save the current selection
        const currentValue = unitSelect.value;
        
        // Clear all options
        unitSelect.innerHTML = '';
        
        // Add empty option
        const emptyOption = document.createElement('option');
        emptyOption.value = '';
        emptyOption.textContent = 'Select unit';
        unitSelect.appendChild(emptyOption);
        
        if (isBulk) {
            // For bulk quantity: Add all units except pcs
            allUnitOptions.forEach(option => {
                if (option.value && option.textContent.trim().toLowerCase() !== 'pcs') {
                    unitSelect.appendChild(option.cloneNode(true));
                }
            });
            
            // Reset value (forces the user to select a unit)
            unitSelect.value = '';
        } else {
            // For pieces: Only pcs is available
            if (pcsOption) {
                // Make a clone of the pcs option
                const pcsOptionClone = pcsOption.cloneNode(true);
                // Ensure it says "pcs" not "stk"
                pcsOptionClone.textContent = 'pcs';
                unitSelect.appendChild(pcsOptionClone);
                unitSelect.value = pcsOption.value;
            } else {
                // Fallback if we didn't find pcs option
                const newPcsOption = document.createElement('option');
                newPcsOption.value = "1"; // Assuming pcs has ID=1
                newPcsOption.textContent = 'pcs';
                unitSelect.appendChild(newPcsOption);
                unitSelect.value = "1";
            }
        }
        
        // Update the helper text
        const unitHelper = document.querySelector('.unit-helper');
        if (unitHelper) {
            unitHelper.textContent = isBulk ? 
                'Select appropriate unit for bulk material (weight, length, volume)' : 
                'Number of individual pieces';
        }
    }
    
    // Handle sample type changes
    const sampleTypeOptions = document.querySelectorAll('input[name="sampleTypeOption"]');
    sampleTypeOptions.forEach(option => {
        option.addEventListener('change', function() {
            updateSampleTypeUI(this.value);
        });
    });
    
    // Initial update of UI based on default selection
    const initialSelectedType = document.querySelector('input[name="sampleTypeOption"]:checked');
    if (initialSelectedType) {
        updateSampleTypeUI(initialSelectedType.value);
    }
    
    // Make sure single sample option is checked by default if nothing is selected
    if (!initialSelectedType && singleSampleOption) {
        singleSampleOption.checked = true;
        updateSampleTypeUI('single');
    }
}