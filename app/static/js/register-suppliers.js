/**
 * Register Suppliers - Supplier search and management functionality
 */

// Initialize supplier functionality when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Supplier module loading...');
    
    // Make functions globally available
    window.createNewSupplier = createNewSupplier;
    window.updateSupplierDisplay = updateSupplierDisplay;
    
    // Initialize supplier search
    initializeSupplierSearch();
    initializeSupplierModal();
    initializeCopyRegistrationModal();
    
    // Mark this module as loaded
    if (window.registerApp) {
        window.registerApp.modulesLoaded.suppliers = true;
        console.log('Supplier module loaded');
    }
});

function initializeSupplierSearch() {
    const supplierSearchInput = document.getElementById('supplierSearchInput');
    const supplierResults = document.getElementById('supplierResults');
    const supplierIdInput = document.getElementById('supplierIdInput');
    const selectedSupplierDisplay = document.getElementById('selectedSupplierDisplay');
    const clearSupplierBtn = document.getElementById('clearSupplierBtn');
    
    if (!supplierSearchInput) return;
    
    let searchTimeout;
    let currentFocus = -1;
    
    // Supplier search functionality - Improved responsiveness
    supplierSearchInput.addEventListener('input', function() {
        const query = this.value.trim();
        currentFocus = -1;
        
        clearTimeout(searchTimeout);
        
        if (query.length < 1) {
            supplierResults.classList.add('d-none');
            return;
        }
        
        // Immediate search for better responsiveness - no delay
        searchSuppliers(query);
    });
    
    // Keyboard navigation
    supplierSearchInput.addEventListener('keydown', function(e) {
        const items = supplierResults.querySelectorAll('.supplier-search-item');
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            currentFocus++;
            addActive(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            currentFocus--;
            addActive(items);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (currentFocus > -1 && items[currentFocus]) {
                items[currentFocus].click();
            }
        } else if (e.key === 'Escape') {
            supplierResults.classList.add('d-none');
            currentFocus = -1;
        }
    });
    
    // Clear supplier selection
    if (clearSupplierBtn) {
        clearSupplierBtn.addEventListener('click', function() {
            clearSupplierSelection();
        });
    }
    
    // Hide results when clicking outside
    document.addEventListener('click', function(e) {
        if (!supplierSearchInput.contains(e.target) && !supplierResults.contains(e.target)) {
            supplierResults.classList.add('d-none');
        }
    });
    
    function addActive(items) {
        removeActive(items);
        if (currentFocus >= items.length) currentFocus = 0;
        if (currentFocus < 0) currentFocus = items.length - 1;
        if (items[currentFocus]) {
            items[currentFocus].classList.add('active');
        }
    }
    
    function removeActive(items) {
        items.forEach(item => item.classList.remove('active'));
    }
    
    function searchSuppliers(query) {
        fetch(`/api/suppliers/search?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                displaySupplierResults(data);
            })
            .catch(error => {
                console.error('Error searching suppliers:', error);
                supplierResults.innerHTML = '<div class="supplier-search-empty">Error searching suppliers</div>';
                supplierResults.classList.remove('d-none');
            });
    }
    
    function displaySupplierResults(suppliers) {
        supplierResults.innerHTML = '';
        
        if (suppliers.length === 0) {
            supplierResults.innerHTML = '<div class="supplier-search-empty">No suppliers found</div>';
        } else {
            suppliers.forEach(supplier => {
                const item = document.createElement('div');
                item.className = 'supplier-search-item';
                item.textContent = supplier.name;
                item.addEventListener('click', () => selectSupplier(supplier.id, supplier.name));
                supplierResults.appendChild(item);
            });
        }
        
        supplierResults.classList.remove('d-none');
        currentFocus = -1;
    }
    
    function selectSupplier(id, name) {
        supplierIdInput.value = id;
        updateSupplierDisplay(name);
        supplierResults.classList.add('d-none');
        supplierSearchInput.value = '';
    }
    
    function updateSupplierDisplay(name) {
        const selectedSupplierName = document.getElementById('selectedSupplierName');
        if (name && selectedSupplierName) {
            selectedSupplierName.textContent = name;
            selectedSupplierDisplay.classList.remove('d-none');
            supplierSearchInput.placeholder = "Supplier selected";
        } else {
            selectedSupplierName.textContent = "No supplier selected";
            selectedSupplierDisplay.classList.add('d-none');
            supplierSearchInput.placeholder = "Search for supplier...";
        }
    }
    
    function clearSupplierSelection() {
        supplierIdInput.value = '';
        updateSupplierDisplay('');
    }
}

function initializeSupplierModal() {
    // New supplier modal functionality
    const createSupplierBtn = document.getElementById('createSupplierBtn');
    if (createSupplierBtn) {
        createSupplierBtn.addEventListener('click', createNewSupplier);
    }
}

function createNewSupplier() {
    const supplierName = document.getElementById('newSupplierName').value.trim();
    
    if (!supplierName) {
        const nameInput = document.getElementById('newSupplierName');
        nameInput.classList.add('is-invalid');
        nameInput.focus();
        return;
    }
    
    const saveButton = document.getElementById('createSupplierBtn');
    const originalText = saveButton.textContent;
    saveButton.textContent = 'Creating...';
    saveButton.disabled = true;
    
    fetch('/api/suppliers', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            name: supplierName
        })
    })
    .then(response => response.json())
    .then(data => {
        saveButton.textContent = originalText;
        saveButton.disabled = false;
        
        if (data.success) {
            // Update supplier selection
            const supplierIdInput = document.getElementById('supplierIdInput');
            if (supplierIdInput) {
                supplierIdInput.value = data.supplier_id;
                updateSupplierDisplay(supplierName);
            }
            
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('newSupplierModal'));
            if (modal) modal.hide();
            
            // Clear form
            document.getElementById('newSupplierName').value = '';
            
            showSuccessToast('Supplier created successfully');
        } else {
            console.log('🔴 REGISTER DEBUG: About to show error toast');
            console.log('🔴 REGISTER DEBUG: Error data:', data);
            console.log('🔴 REGISTER DEBUG: showErrorToast function exists?', typeof showErrorToast);
            showErrorToast('Error creating supplier: ' + (data.error || 'Unknown error'));
            console.log('🔴 REGISTER DEBUG: Error toast call completed');
        }
    })
    .catch(error => {
        console.log('🔴 REGISTER DEBUG: Catch block - About to show error toast');
        console.log('🔴 REGISTER DEBUG: Catch error:', error);
        saveButton.textContent = originalText;
        saveButton.disabled = false;
        showErrorToast('Error creating supplier: ' + error.message);
        console.log('🔴 REGISTER DEBUG: Catch error toast call completed');
    });
}

function initializeCopyRegistrationModal() {
    // Copy registration modal functionality
    const copyRegistrationModal = document.getElementById('copyRegistrationModal');
    if (copyRegistrationModal) {
        copyRegistrationModal.addEventListener('show.bs.modal', loadPreviousRegistrations);
    }
    
    const copyRegistrationBtn = document.getElementById('copyRegistrationBtn');
    if (copyRegistrationBtn) {
        copyRegistrationBtn.addEventListener('click', copySelectedRegistration);
    }
}

function loadPreviousRegistrations() {
    const dropdown = document.getElementById('existingRegistrations');
    if (!dropdown) return;
    
    // Clear existing options
    dropdown.innerHTML = '<option>Loading samples...</option>';
    
    fetch('/api/samples/recent')
        .then(response => response.json())
        .then(data => {
            dropdown.innerHTML = '<option value="">Select a sample to copy...</option>';
            
            if (data.samples && data.samples.length > 0) {
                data.samples.forEach(sample => {
                    const option = document.createElement('option');
                    option.value = sample.sample_id;
                    option.textContent = `${sample.description} (${sample.barcode || sample.sample_id})`;
                    dropdown.appendChild(option);
                });
            } else {
                dropdown.innerHTML = '<option value="">No recent samples found</option>';
            }
        })
        .catch(error => {
            console.error('Error loading recent samples:', error);
            dropdown.innerHTML = '<option value="">Error loading samples</option>';
        });
}

function copySelectedRegistration() {
    const dropdown = document.getElementById('existingRegistrations');
    const selectedSampleId = dropdown.value;
    
    if (!selectedSampleId) {
        showWarningToast('Please select a sample to copy');
        return;
    }
    
    fetch(`/api/samples/${selectedSampleId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                populateFormWithSampleData(data.sample);
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('copyRegistrationModal'));
                if (modal) modal.hide();
                
                showSuccessToast('Sample data copied successfully');
            } else {
                showErrorToast('Error loading sample data: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error copying registration:', error);
            showErrorToast('Error copying registration: ' + error.message);
        });
}

function populateFormWithSampleData(sample) {
    // Populate form fields with sample data
    const fields = {
        'description': sample.description,
        'partNumber': sample.part_number,
        'totalAmount': sample.amount,
        'unit': sample.unit_id,
        'owner': sample.owner_id
    };
    
    Object.keys(fields).forEach(fieldName => {
        const field = document.querySelector(`[name="${fieldName}"]`);
        if (field && fields[fieldName]) {
            field.value = fields[fieldName];
        }
    });
}

// Helper function to update supplier display (used by other functions)
function updateSupplierDisplay(name) {
    const selectedSupplierName = document.getElementById('selectedSupplierName');
    const selectedSupplierDisplay = document.getElementById('selectedSupplierDisplay');
    const supplierSearchInput = document.getElementById('supplierSearchInput');
    
    if (name && selectedSupplierName) {
        selectedSupplierName.textContent = name;
        selectedSupplierDisplay.classList.remove('d-none');
        supplierSearchInput.placeholder = "Supplier selected";
    } else {
        selectedSupplierName.textContent = "No supplier selected";
        selectedSupplierDisplay.classList.add('d-none');
        supplierSearchInput.placeholder = "Search for supplier...";
    }
}