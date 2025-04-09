/**
 * Register Sample Types - Handling different sample types in the registration form
 */

// Initialize when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Sample types module loading...');
    
    // Set up sample type handling
    setupSampleTypeOptions();
    setupMultiSampleOptions();
    
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

// Setup sample type options (Single, Multiple, Bulk)
function setupSampleTypeOptions() {
    const singleSampleOption = document.getElementById('singleSampleOption');
    const multiSampleOption = document.getElementById('multiSampleOption');
    const bulkSampleOption = document.getElementById('bulkSampleOption');
    const multiSampleOptions = document.getElementById('multiSampleOptions');
    const multipleContainerOptions = document.getElementById('multipleContainerOptions');
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
        
        // Show/hide multiple sample options
        if (multiSampleOptions) {
            multiSampleOptions.classList.toggle('d-none', sampleType !== 'multiple');
        }
        
        // Update container options based on sample type
        const storageOption = document.querySelector('input[name="storageOption"]:checked')?.value;
        if (storageOption === 'container' && containerOptions && !containerOptions.classList.contains('d-none')) {
            if (multipleContainerOptions && singleContainerOptions) {
                const isMultiple = sampleType === 'multiple';
                multipleContainerOptions.classList.toggle('d-none', !isMultiple);
                singleContainerOptions.classList.toggle('d-none', isMultiple);
            }
        }
        
        // Update unit options based on sample type
        updateUnitOptions(sampleType === 'bulk');
        
        // Update total amount input based on sample type
        if (totalAmountInput) {
            if (sampleType === 'multiple') {
                // For multiple samples, total is calculated
                totalAmountInput.readOnly = true;
                updateTotalAmount();
            } else {
                // For single or bulk, total is manually entered
                totalAmountInput.readOnly = false;
            }
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

// Setup multi-sample options
function setupMultiSampleOptions() {
    const packageCountInput = document.querySelector('[name="packageCount"]');
    const amountPerPackageInput = document.querySelector('[name="amountPerPackage"]');
    const totalAmountInput = document.querySelector('[name="totalAmount"]');
    const calculatedTotal = document.getElementById('calculatedTotal');
    const totalCounter = document.getElementById('totalCount');
    const separateStorageCheckbox = document.getElementById('separateStorage');
    
    if (!packageCountInput || !amountPerPackageInput || !totalAmountInput) return;
    
    // Listen for changes in package fields
    packageCountInput.addEventListener('input', updateTotalAmount);
    amountPerPackageInput.addEventListener('input', updateTotalAmount);
    
    // Also listen for changes in totalAmount
    totalAmountInput.addEventListener('input', function() {
        if (totalCounter) {
            totalCounter.textContent = this.value || 0;
        }
    });
    
    // Handle separate storage checkbox
    if (separateStorageCheckbox) {
        separateStorageCheckbox.addEventListener('change', function() {
            // We'll handle this in step 4 when showing the grid
            updateStorageInstructions();
        });
    }
    
    // Initial update
    updateTotalAmount();
}

// Calculate total based on package count and amount per package
function updateTotalAmount() {
    const packageCountInput = document.querySelector('[name="packageCount"]');
    const amountPerPackageInput = document.querySelector('[name="amountPerPackage"]');
    const totalAmountInput = document.querySelector('[name="totalAmount"]');
    const calculatedTotal = document.getElementById('calculatedTotal');
    const totalCounter = document.getElementById('totalCount');
    
    if (!packageCountInput || !amountPerPackageInput || !totalAmountInput) return;
    
    const packageCount = parseInt(packageCountInput.value) || 0;
    const amountPerPackage = parseInt(amountPerPackageInput.value) || 0;
    const total = packageCount * amountPerPackage;
    
    totalAmountInput.value = total;
    if (calculatedTotal) {
        calculatedTotal.textContent = total;
    }
    
    // Also update totalCounter for scanning
    if (totalCounter) {
        totalCounter.textContent = total;
    }
}