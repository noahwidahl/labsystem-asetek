// Message functions for displaying success and errors
function showSuccessMessage(message) {
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

function showErrorMessage(message) {
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

// Function to show the dedicated test iteration modal
function showCreateTestIterationModal(testId, testNo, testName) {
    console.log(`DEBUG: showCreateTestIterationModal called with testId=${testId}, testNo=${testNo}, testName=${testName}`);
    
    // Get the dedicated test iteration modal
    const modal = new bootstrap.Modal(document.getElementById('createTestIterationModal'));
    
    // Fill in test information
    document.getElementById('iterationTestType').value = testName || "Unknown";
    document.getElementById('iterationTestDescription').value = `Iteration of test ${testNo}`;
    
    // Set hidden fields
    document.getElementById('originalTestId').value = testId;
    document.getElementById('originalTestNo').value = testNo;
    
    // Show iteration information in the banner
    // Parse the test number to show next iteration
    const match = testNo.match(/T(\d+)\.(\d+)/);
    let nextIterationNo = testNo;
    
    if (match) {
        const baseNum = match[1];
        const iterNum = parseInt(match[2]);
        nextIterationNo = `T${baseNum}.${iterNum + 1}`;
    }
    
    document.getElementById('iterationOriginalTest').textContent = `Original test: ${testNo}`;
    document.getElementById('iterationNewNumber').textContent = `New iteration: ${nextIterationNo}`;
    
    // Log debug information
    console.log(`Preparing iteration of test ${testNo} (ID: ${testId})`);
    console.log(`Next iteration number will be: ${nextIterationNo}`);
    
    // Show the modal
    modal.show();
    
    // Show loading state in table
    const tableBody = document.querySelector('#createTestIterationModal .iteration-available-samples tbody');
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center">
                    <div class="d-flex justify-content-center my-3">
                        <div class="spinner-border text-success" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                    <p>Loading available samples...</p>
                </td>
            </tr>
        `;
    }
    
    // Fetch available samples
    fetchAvailableSamplesForIteration()
        .catch(error => {
            console.error("Error fetching samples for iteration:", error);
            
            if (tableBody) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center">
                            <div class="alert alert-warning mb-0">
                                <i class="fas fa-exclamation-triangle me-2"></i>
                                Could not load samples. Please make sure you have samples registered and stored in the system.
                            </div>
                        </td>
                    </tr>
                `;
            }
            
            // Disable the create button
            const createBtn = document.getElementById('createIterationBtn');
            if (createBtn) {
                createBtn.disabled = true;
                createBtn.title = 'No samples available for testing';
            }
        });
}

// Function to fetch available samples for iteration, using the same API endpoint
function fetchAvailableSamplesForIteration() {
    return fetch('/api/activeSamples')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Always pass a valid array to populateIterationSampleTable
                const samples = Array.isArray(data.samples) ? data.samples : [];
                populateIterationSampleTable(samples);
                return;
            }
            
            // If we get here, there was an error in the response
            throw new Error(data.error || "Unknown error");
        });
}

// Function to populate the iteration sample table
function populateIterationSampleTable(samples) {
    const tableBody = document.querySelector('#createTestIterationModal .iteration-available-samples tbody');
    if (!tableBody) return;
    
    // Clear the table
    tableBody.innerHTML = '';
    
    // Set create button state
    const createBtn = document.getElementById('createIterationBtn');
    if (createBtn) {
        if (samples.length === 0) {
            createBtn.disabled = true;
            createBtn.title = 'No samples available for testing';
        } else {
            createBtn.disabled = false;
            createBtn.title = '';
        }
    }
    
    // Show message if no samples
    if (samples.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center p-3">
                    <div class="alert alert-info mb-0">
                        <i class="fas fa-info-circle me-2"></i>
                        No samples available for testing. Please register and store samples first.
                    </div>
                </td>
            </tr>`;
        return;
    }
    
    // Populate the table with samples
    samples.forEach(sample => {
        const row = document.createElement('tr');
        
        // Determine if this is a unique sample with serial numbers
        const isUnique = sample.IsUnique === 1;
        const hasSerialNumbers = sample.SerialNumbersList && sample.SerialNumbersList.length > 0;
        
        // Create base row HTML
        let rowHtml = `
            <td>
                <input type="checkbox" name="selectedSamples" value="${sample.SampleID}" data-unique="${isUnique ? 1 : 0}">
            </td>
            <td>${sample.SampleIDFormatted}</td>
            <td>${sample.PartNumber || '-'}</td>
            <td>
                ${sample.Description}
                ${sample.Status === 'In Test' ? 
                    '<span class="badge bg-warning text-dark ms-2">In Test</span>' : ''}
            </td>
            <td>${sample.LocationName || 'Unknown'}</td>
        `;
        
        // Different input for amount based on sample type
        if (isUnique && hasSerialNumbers) {
            // For unique samples with serial numbers, offer dropdowns instead of amount
            rowHtml += `
                <td>
                    <div class="d-flex align-items-center mb-2">
                        <span class="badge bg-success me-2">${sample.AmountRemaining} Available</span>
                    </div>
                    <div class="serial-number-selector" data-id="${sample.SampleID}" style="display: none;">
                        <select class="form-select form-select-sm" multiple size="3">
                            ${sample.SerialNumbersList.map(sn => `<option value="${sn}">${sn}</option>`).join('')}
                        </select>
                        <small class="form-text text-muted">Select serial numbers</small>
                    </div>
                    <div class="amount-selector">
                        <div class="input-group input-group-sm">
                            <span class="input-group-text">Use:</span>
                            <input type="number" class="form-control form-control-sm" name="sampleAmount" 
                                   value="1" min="1" max="${sample.AmountRemaining}" data-id="${sample.SampleID}">
                        </div>
                    </div>
                </td>
            `;
        } else {
            // For standard samples, just show amount selector
            rowHtml += `
                <td>
                    <div class="d-flex align-items-center mb-2">
                        <span class="badge bg-success me-2">${sample.AmountRemaining} Available</span>
                    </div>
                    <div class="input-group input-group-sm">
                        <span class="input-group-text">Use:</span>
                        <input type="number" class="form-control form-control-sm" name="sampleAmount" 
                               value="1" min="1" max="${sample.AmountRemaining}" data-id="${sample.SampleID}">
                    </div>
                </td>
            `;
        }
        
        row.innerHTML = rowHtml;
        
        // Add amount tooltip to the description cell for visibility
        const descCell = row.querySelector('td:nth-child(4)');
        if (descCell) {
            descCell.title = `Available quantity: ${sample.AmountRemaining || 0} ${sample.Unit || 'pcs'}`;
            descCell.style.cursor = 'help';
        }
        
        tableBody.appendChild(row);
        
        // Add event listeners for unique sample checkboxes
        if (isUnique && hasSerialNumbers) {
            const checkbox = row.querySelector('input[name="selectedSamples"]');
            checkbox.addEventListener('change', function() {
                const serialSelector = row.querySelector('.serial-number-selector');
                const amountSelector = row.querySelector('.amount-selector');
                
                if (this.checked) {
                    serialSelector.style.display = 'block';
                    amountSelector.style.display = 'none';
                } else {
                    serialSelector.style.display = 'none';
                    amountSelector.style.display = 'block';
                }
            });
        }
    });
}

// Function specifically for creating a test iteration
function createTestIteration() {
    // Get test information
    const testType = document.getElementById('iterationTestType').value;
    const testOwner = document.querySelector('[name="iterationTestOwner"]').value;
    const testDescription = document.getElementById('iterationTestDescription').value;
    
    // Get critical iteration information
    const originalTestId = document.getElementById('originalTestId').value;
    const originalTestNo = document.getElementById('originalTestNo').value;
    
    // Validate input
    if (!testType) {
        showErrorMessage("Test type is missing");
        return;
    }
    
    if (!originalTestId || !originalTestNo) {
        showErrorMessage("Original test information is missing");
        return;
    }
    
    // Get selected samples
    const selectedSampleElements = document.querySelectorAll('#createTestIterationModal input[name="selectedSamples"]:checked');
    if (selectedSampleElements.length === 0) {
        showErrorMessage("Select at least one sample");
        return;
    }
    
    // Build array of selected samples with amount and serial numbers if applicable
    const selectedSamples = Array.from(selectedSampleElements).map(element => {
        const sampleId = element.value;
        const isUnique = element.dataset.unique === "1";
        let amount = 1;
        let serialNumbers = [];
        
        // Handle unique samples differently
        if (isUnique) {
            // Look for serial number selector
            const serialSelector = element.closest('tr').querySelector('.serial-number-selector select');
            if (serialSelector) {
                // Get selected serial numbers
                serialNumbers = Array.from(serialSelector.selectedOptions).map(opt => opt.value);
                
                // If serial numbers are selected, set amount to match
                if (serialNumbers.length > 0) {
                    amount = serialNumbers.length;
                } else {
                    // Otherwise get the amount from input
                    const amountInput = document.querySelector(`#createTestIterationModal input[name="sampleAmount"][data-id="${sampleId}"]`);
                    amount = amountInput ? parseInt(amountInput.value) || 1 : 1;
                }
            }
        } else {
            // Standard samples just use amount
            const amountInput = document.querySelector(`#createTestIterationModal input[name="sampleAmount"][data-id="${sampleId}"]`);
            amount = amountInput ? parseInt(amountInput.value) || 1 : 1;
        }
        
        const sampleData = {
            id: sampleId,
            amount: amount
        };
        
        // Add serial numbers if any were selected
        if (serialNumbers.length > 0) {
            sampleData.serialNumbers = serialNumbers;
        }
        
        return sampleData;
    });
    
    // Complete test data with both original test info AND iteration flag
    const testData = {
        type: testType,
        owner: testOwner,
        samples: selectedSamples,
        description: testDescription,
        original_test_id: originalTestId,
        original_test_no: originalTestNo,
        is_iteration: true
    };
    
    // Debug log
    console.log("===== CREATING TEST ITERATION =====");
    console.log(`Original Test ID: ${originalTestId}`);
    console.log(`Original Test No: ${originalTestNo}`);
    console.log(`Test Type: ${testType}`);
    console.log(`Samples: ${selectedSamples.length}`);
    console.log("Test Data:", testData);
    
    // IMPORTANT: Always use the dedicated endpoint for iterations
    const endpoint = '/api/createTestIteration';
    
    // Show loading indicator
    showLoadingOverlay();
    
    // Send to server
    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(testData)
    })
    .then(response => response.json())
    .then(data => {
        // Hide loading indicator
        hideLoadingOverlay();
        
        if (data.success) {
            showSuccessMessage(`Test iteration ${data.test_id} has been created successfully!`);
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('createTestIterationModal'));
            if (modal) modal.hide();
            
            // Reload page after short delay
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showErrorMessage(`Error creating test iteration: ${data.error}`);
        }
    })
    .catch(error => {
        // Hide loading indicator
        hideLoadingOverlay();
        showErrorMessage(`An error occurred: ${error}`);
    });
}

// Functions for handling test creation
function showCreateTestModal() {
    // Reset modal title and remove any existing info boxes
    document.querySelector('#createTestModal .modal-title').textContent = 'Create New Test';
    const existingInfoBox = document.querySelector('#createTestModal .alert');
    if (existingInfoBox) {
        existingInfoBox.remove();
    }
    
    // Reset the create button text and style
    document.getElementById('testMode').value = "regular";
    
    // Reset button styling
    const createTestBtn = document.getElementById('createTestBtn');
    if (createTestBtn) {
        createTestBtn.classList.remove('btn-success');
        createTestBtn.classList.add('btn-primary');
        createTestBtn.title = '';
    }
    
    // Clear any existing values
    const testTypeInput = document.querySelector('[name="testType"]');
    if (testTypeInput) {
        testTypeInput.value = '';
    }
    
    const testDescriptionInput = document.querySelector('[name="testDescription"]');
    if (testDescriptionInput) {
        testDescriptionInput.value = '';
    }
    
    // Show modal first to improve user experience
    const modal = new bootstrap.Modal(document.getElementById('createTestModal'));
    modal.show();
    
    // Show loading state in table
    const tableBody = document.querySelector('#createTestModal .available-samples tbody');
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center">
                    <div class="d-flex justify-content-center my-3">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                    <p>Loading available samples...</p>
                </td>
            </tr>
        `;
    }
    
    // Fetch available samples
    fetchAvailableSamples()
        .catch(error => {
            console.error("Error fetching samples:", error);
            
            if (tableBody) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center">
                            <div class="alert alert-warning mb-0">
                                <i class="fas fa-exclamation-triangle me-2"></i>
                                Could not load samples. Please make sure you have samples registered and stored in the system.
                            </div>
                        </td>
                    </tr>
                `;
            }
            
            // Disable the create test button
            const createTestBtn = document.getElementById('createTestBtn');
            if (createTestBtn) {
                createTestBtn.disabled = true;
                createTestBtn.title = 'No samples available for testing';
            }
            
            // Don't show error toast since we're already showing it in the table
            // This prevents duplicate error messages
        });
}

// Function to fetch available samples
function fetchAvailableSamples() {
    return fetch('/api/activeSamples')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("API response:", data); // Debug log
            
            if (data.success) {
                // Always pass a valid array to populateSampleTable
                const samples = Array.isArray(data.samples) ? data.samples : [];
                populateSampleTable(samples);
                return; // Successful handling
            } 
            
            // If we get here, there was an error in the response
            throw new Error(data.error || "Unknown error");
        });
}

// Function to populate the sample table
function populateSampleTable(samples) {
    const tableBody = document.querySelector('#createTestModal .available-samples tbody');
    if (!tableBody) return;
    
    // Clear the table
    tableBody.innerHTML = '';
    
    // Set create test button state
    const createTestBtn = document.getElementById('createTestBtn');
    if (createTestBtn) {
        if (samples.length === 0) {
            createTestBtn.disabled = true;
            createTestBtn.title = 'No samples available for testing';
        } else {
            createTestBtn.disabled = false;
            createTestBtn.title = '';
        }
    }
    
    // Show message if no samples
    if (samples.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center p-3">
                    <div class="alert alert-info mb-0">
                        <i class="fas fa-info-circle me-2"></i>
                        No samples available for testing. Please register and store samples first.
                    </div>
                </td>
            </tr>`;
        return;
    }
    
    // Populate the table with samples
    samples.forEach(sample => {
        const row = document.createElement('tr');
        
        // Determine if this is a unique sample with serial numbers
        const isUnique = sample.IsUnique === 1;
        const hasSerialNumbers = sample.SerialNumbersList && sample.SerialNumbersList.length > 0;
        
        // Create base row HTML
        let rowHtml = `
            <td>
                <input type="checkbox" name="selectedSamples" value="${sample.SampleID}" data-unique="${isUnique ? 1 : 0}">
            </td>
            <td>${sample.SampleIDFormatted}</td>
            <td>${sample.PartNumber || '-'}</td>
            <td>
                ${sample.Description}
                ${sample.Status === 'In Test' ? 
                    '<span class="badge bg-warning text-dark ms-2">In Test</span>' : ''}
            </td>
            <td>${sample.LocationName || 'Unknown'}</td>
        `;
        
        // Different input for amount based on sample type
        if (isUnique && hasSerialNumbers) {
            // For unique samples with serial numbers, offer dropdowns instead of amount
            rowHtml += `
                <td>
                    <div class="d-flex align-items-center mb-2">
                        <span class="badge bg-success me-2">${sample.AmountRemaining} Available</span>
                    </div>
                    <div class="serial-number-selector" data-id="${sample.SampleID}" style="display: none;">
                        <select class="form-select form-select-sm" multiple size="3">
                            ${sample.SerialNumbersList.map(sn => `<option value="${sn}">${sn}</option>`).join('')}
                        </select>
                        <small class="form-text text-muted">Select serial numbers</small>
                    </div>
                    <div class="amount-selector">
                        <div class="input-group input-group-sm">
                            <span class="input-group-text">Use:</span>
                            <input type="number" class="form-control form-control-sm" name="sampleAmount" 
                                   value="1" min="1" max="${sample.AmountRemaining}" data-id="${sample.SampleID}">
                        </div>
                    </div>
                </td>
            `;
        } else {
            // For standard samples, just show amount selector
            rowHtml += `
                <td>
                    <div class="d-flex align-items-center mb-2">
                        <span class="badge bg-success me-2">${sample.AmountRemaining} Available</span>
                    </div>
                    <div class="input-group input-group-sm">
                        <span class="input-group-text">Use:</span>
                        <input type="number" class="form-control form-control-sm" name="sampleAmount" 
                               value="1" min="1" max="${sample.AmountRemaining}" data-id="${sample.SampleID}">
                    </div>
                </td>
            `;
        }
        
        row.innerHTML = rowHtml;
        
        // Add amount tooltip to the description cell for visibility
        const descCell = row.querySelector('td:nth-child(4)');
        if (descCell) {
            descCell.title = `Available quantity: ${sample.AmountRemaining || 0} ${sample.Unit || 'pcs'}`;
            descCell.style.cursor = 'help';
        }
        
        tableBody.appendChild(row);
        
        // Add event listeners for unique sample checkboxes
        if (isUnique && hasSerialNumbers) {
            const checkbox = row.querySelector('input[name="selectedSamples"]');
            checkbox.addEventListener('change', function() {
                const serialSelector = row.querySelector('.serial-number-selector');
                const amountSelector = row.querySelector('.amount-selector');
                
                if (this.checked) {
                    serialSelector.style.display = 'block';
                    amountSelector.style.display = 'none';
                } else {
                    serialSelector.style.display = 'none';
                    amountSelector.style.display = 'block';
                }
            });
        }
    });
    
    // Add event listener to "Select all" checkbox
    const selectAllCheckbox = document.getElementById('selectAll');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            const checkboxes = document.querySelectorAll('input[name="selectedSamples"]');
            checkboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
        });
    }
}

// Function to create a new test
function createTest() {
    // Get test information
    const testType = document.querySelector('[name="testType"]').value;
    const testOwner = document.querySelector('[name="testOwner"]').value;
    
    // Validate input
    if (!testType) {
        showErrorMessage("Please select a test type");
        return;
    }
    
    // Get selected samples
    const selectedSampleElements = document.querySelectorAll('input[name="selectedSamples"]:checked');
    if (selectedSampleElements.length === 0) {
        showErrorMessage("Select at least one sample");
        return;
    }
    
    // Build array of selected samples with amount and serial numbers if applicable
    const selectedSamples = Array.from(selectedSampleElements).map(element => {
        const sampleId = element.value;
        const isUnique = element.dataset.unique === "1";
        let amount = 1;
        let serialNumbers = [];
        
        // Handle unique samples differently
        if (isUnique) {
            // Look for serial number selector
            const serialSelector = element.closest('tr').querySelector('.serial-number-selector select');
            if (serialSelector) {
                // Get selected serial numbers
                serialNumbers = Array.from(serialSelector.selectedOptions).map(opt => opt.value);
                
                // If serial numbers are selected, set amount to match
                if (serialNumbers.length > 0) {
                    amount = serialNumbers.length;
                } else {
                    // Otherwise get the amount from input
                    const amountInput = document.querySelector(`input[name="sampleAmount"][data-id="${sampleId}"]`);
                    amount = amountInput ? parseInt(amountInput.value) || 1 : 1;
                }
            }
        } else {
            // Standard samples just use amount
            const amountInput = document.querySelector(`input[name="sampleAmount"][data-id="${sampleId}"]`);
            amount = amountInput ? parseInt(amountInput.value) || 1 : 1;
        }
        
        const sampleData = {
            id: sampleId,
            amount: amount
        };
        
        // Add serial numbers if any were selected
        if (serialNumbers.length > 0) {
            sampleData.serialNumbers = serialNumbers;
        }
        
        return sampleData;
    });
    
    // Get the description field value
    let description = document.querySelector('[name="testDescription"]')?.value || '';
    
    // Create test data - NO ITERATION INFO, this is for regular tests only!
    const testData = {
        type: testType,
        owner: testOwner,
        samples: selectedSamples,
        description: description
    };
    
    console.log("DEBUG: Test Data:", testData);
    
    // Regular tests always use the standard endpoint
    const endpoint = '/api/createTest';
    
    console.log(`Using endpoint: ${endpoint}`);
    
    // Send to server
    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(testData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage(`Test ${data.test_id} has been created successfully!`);
            
            // Close modal and reload page
            const modal = bootstrap.Modal.getInstance(document.getElementById('createTestModal'));
            if (modal) modal.hide();
            
            // Reload page after short delay
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showErrorMessage(`Error creating test: ${data.error}`);
        }
    })
    .catch(error => {
        showErrorMessage(`An error occurred: ${error}`);
    });
}

// CompleteTest function
function completeTest(testId, testNo) {
    // Use testNo for display if available, otherwise fallback to testId
    const displayId = testNo || testId;
    
    confirmAction(`Are you sure you want to complete test ${displayId}?`, function() {
        // Show loading indicator
        showLoadingOverlay();
        
        fetch(`/api/completeTest/${testId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ testId: testId })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server answered with status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Hide loading indicator
            hideLoadingOverlay();
            
            if (data.success) {
                // Test completed successfully
                showSuccessMessage(`Test ${data.test_id || displayId} has been completed!`);
                
                // Close test details modal
                const testDetailsModal = bootstrap.Modal.getInstance(document.getElementById('testDetailsModal'));
                if (testDetailsModal) {
                    testDetailsModal.hide();
                }
                
                // Store test ID for disposition and show the disposition modal
                // This is critical - we need to make sure this happens
                console.log("Preparing to show sample disposition modal for test", testId);
                document.getElementById('completedTestId').value = testId;
                
                // Wait a moment for the first modal to close, then show disposition modal
                setTimeout(() => {
                    console.log("Showing sample disposition modal now");
                    const dispositionModal = new bootstrap.Modal(document.getElementById('sampleDispositionModal'));
                    dispositionModal.show();
                    
                    // Setup event handlers for the buttons
                    setupDispositionHandlers(testId, data.test_id || displayId);
                }, 300);
            } else {
                showErrorMessage(`Error while finishing test: ${data.error}`);
            }
        })
        .catch(error => {
            // Hide loading indicator
            hideLoadingOverlay();
            showErrorMessage(`An error has occurred: ${error}`);
            console.error("Error while finishing test:", error);
        });
    });
}

function removeTestCardFromDOM(testId) {
    // Find alle test-kort
    const testCards = document.querySelectorAll('.test-card');
    let foundCard = false;
    
    testCards.forEach(card => {
        // Tjek først om kortet har et data-attribut
        let cardTestId = card.getAttribute('data-test-id');
        
        // Hvis ikke, prøv at finde badge-elementet
        if (!cardTestId) {
            const badge = card.querySelector('.badge');
            if (badge) {
                cardTestId = badge.textContent.trim();
            }
        }
        
        // Hvis stadig ikke, prøv at finde TestNo i et andet element
        if (!cardTestId) {
            const cardContent = card.textContent;
            if (cardContent && cardContent.includes(testId)) {
                cardTestId = testId;
            }
        }
        
        if (cardTestId === testId) {
            foundCard = true;
            // Få fat i forældreelementet (kolonnen) for at fjerne hele kortet
            const column = card.closest('.col-md-6, .col-lg-4');
            if (column) {
                // Fade-out animation før vi fjerner kortet
                column.style.transition = 'all 0.5s ease';
                column.style.opacity = '0';
                column.style.transform = 'scale(0.8)';
                
                setTimeout(() => {
                    column.remove();
                    
                    // Opdater antal aktive tests i velkomstbeskeden
                    const remainingCards = document.querySelectorAll('.test-card').length;
                    updateWelcomeMessage(remainingCards);
                }, 500);
            }
        }
    });
    
    if (!foundCard) {
        console.warn(`Could not find test card for test ${testId}`);
    }
}

function showLoadingOverlay() {
    // Check if overlay already exists
    if (document.getElementById('loadingOverlay')) {
        return;
    }
    
    const overlay = document.createElement('div');
    overlay.id = 'loadingOverlay';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="loading-spinner">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <div class="loading-text mt-2">Processing...</div>
        </div>
    `;
    
    document.body.appendChild(overlay);
}

// Hide loading overlay
function hideLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.add('fade-out');
        setTimeout(() => {
            overlay.remove();
        }, 300);
    }
}

function showTestDetails(testId) {
    currentTestId = testId;
    console.log(`Showing test details for ID: ${testId}`);  // Debug output
    
    // Show loading indicator
    const modal = new bootstrap.Modal(document.getElementById('testDetailsModal'));
    modal.show();
    
    // Show loading indicator in the modal
    document.querySelector('.test-info').innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Loading test details...</p></div>';
    document.querySelector('.test-samples-table tbody').innerHTML = '<tr><td colspan="4" class="text-center">Loading...</td></tr>';
    
    // Fetch test details from server
    fetch(`/api/testDetails/${testId}`)
        .then(response => {
            console.log(`Response status: ${response.status}`); // Debug output
            if (response.status === 404) {
                // If test is not found (maybe it has been completed)
                throw new Error("The test was not found. It may have been completed.");
            }
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("API response data:", data);  // Debug output
            if (data.test) {
                // Store the test number globally for use with other functions
                currentTestNo = data.test.TestNo;
                console.log(`Set currentTestNo: ${currentTestNo}`);
                
                // Update the "Complete Test" button to use the test number
                const completeBtn = document.getElementById('completeTestBtn');
                if (completeBtn) {
                    completeBtn.setAttribute('onclick', `completeTest('${testId}', '${currentTestNo}')`);
                }
                
                populateTestDetailsModal(data.test);
            } else {
                throw new Error("No test data returned");
            }
        })
        .catch(error => {
            document.querySelector('.test-info').innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
            document.querySelector('.test-samples-table tbody').innerHTML = '<tr><td colspan="4" class="text-center">Could not load data</td></tr>';
            console.error("Error fetching test details:", error);
        });
}

// Function to dispose all samples in a test at once
function disposeAllTestSamples(testId) {
    confirmAction(`Are you sure you want to dispose ALL samples in test ${testId}?`, function() {
        // Show loading indicator
        showLoadingOverlay();
        
        fetch('/api/disposeAllTestSamples', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ testId: testId })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Hide loading indicator
            hideLoadingOverlay();
            
            if (data.success) {
                showSuccessMessage(`All samples in test ${testId} have been disposed successfully!`);
                
                // Close modal if open
                const modal = bootstrap.Modal.getInstance(document.getElementById('testDetailsModal'));
                if (modal) modal.hide();
                
                // Remove test card and reload page after short delay
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showErrorMessage(`Error during disposal: ${data.error}`);
            }
        })
        .catch(error => {
            // Hide loading indicator
            hideLoadingOverlay();
            showErrorMessage(`An error occurred: ${error}`);
            console.error("Error disposing all samples:", error);
        });
    });
}

function populateTestDetailsModal(test) {
    const testInfoEl = document.querySelector('.test-info');
    const samplesTableEl = document.querySelector('.test-samples-table tbody');
    const relatedTestsSection = document.querySelector('.related-tests');
    const relatedTestsTableEl = document.querySelector('.related-tests-table tbody');
    
    console.log("Test data received:", test);  // Debug output
    
    // Update title
    document.querySelector('#testDetailsModal .modal-title').textContent = `Test Details: ${test.TestNo || test.TestID}`;
    
    // Update test information
    testInfoEl.innerHTML = `
        <div class="row mb-3">
            <div class="col-md-6">
                <p><strong>Test Type:</strong> ${test.TestName || 'Not specified'}</p>
                <p><strong>Test Number:</strong> ${test.TestNo || test.TestID}</p>
                <p><strong>Created:</strong> ${test.CreatedDate || 'Unknown'}</p>
            </div>
            <div class="col-md-6">
                <p><strong>Owner:</strong> ${test.UserName || 'Unknown'}</p>
                <p><strong>Status:</strong> <span class="badge bg-primary">Active</span></p>
                <p><strong>Sample Count:</strong> ${test.Samples ? test.Samples.length : 0}</p>
            </div>
        </div>
        ${test.Description ? `<p><strong>Description:</strong> ${test.Description}</p>` : ''}
    `;
    
    // Show related tests if available
    if (test.related_tests && test.related_tests.length > 1) {  // More than 1 means there are other iterations
        relatedTestsSection.style.display = 'block';
        relatedTestsTableEl.innerHTML = '';
        
        test.related_tests.forEach(relatedTest => {
            const row = document.createElement('tr');
            
            // Highlight the current test
            if (relatedTest.IsCurrent) {
                row.classList.add('table-primary');
            }
            
            // Extract sample count if available
            const sampleCount = relatedTest.Samples ? relatedTest.Samples.length : '-';
            
            row.innerHTML = `
                <td>${relatedTest.TestNo}</td>
                <td>${relatedTest.TestName || 'Not specified'}</td>
                <td>${relatedTest.CreatedDate || 'Unknown'}</td>
                <td>${sampleCount}</td>
                <td>
                    ${relatedTest.IsCurrent ? 
                        '<span class="badge bg-primary">Current</span>' : 
                        `<button class="btn btn-sm btn-outline-primary" onclick="showTestDetails('${relatedTest.TestID}')">
                            <i class="fas fa-eye"></i> View
                        </button>`
                    }
                </td>
            `;
            relatedTestsTableEl.appendChild(row);
        });
    } else {
        relatedTestsSection.style.display = 'none';
    }
    
    // Update sample table
    if (test.Samples && test.Samples.length > 0) {
        samplesTableEl.innerHTML = '';
        
        test.Samples.forEach((sample, index) => {
            const row = document.createElement('tr');
            const partInfo = sample.PartNumber ? `(${sample.PartNumber})` : '';
            row.innerHTML = `
                <td>${sample.GeneratedIdentifier || `${test.TestNo}_${index + 1}`}</td>
                <td>
                    ${sample.Description || 'Not specified'} ${partInfo}
                    <span class="badge bg-warning text-dark ms-2">In Test</span>
                </td>
                <td>SMP-${sample.OriginalSampleID || 'N/A'}</td>
                <td>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline-primary" onclick="showChainOfCustody('${sample.GeneratedIdentifier}')">
                            <i class="fas fa-history"></i> History
                        </button>
                        <button class="btn btn-sm btn-outline-success" onclick="returnSampleToStorage('${sample.TestSampleID}')">
                            <i class="fas fa-archive"></i> Return
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="disposeSample('${sample.TestSampleID}')">
                            <i class="fas fa-trash-alt"></i> Dispose
                        </button>
                    </div>
                </td>
            `;
            samplesTableEl.appendChild(row);
        });
    } else {
        samplesTableEl.innerHTML = '<tr><td colspan="4" class="text-center">No samples in this test</td></tr>';
    }
}

// Helper function to display welcome text based on number of active tests
function updateWelcomeMessage(testCount) {
    const welcomeMessage = document.querySelector('.welcome-message');
    if (!welcomeMessage) return;
    
    if (testCount > 0) {
        welcomeMessage.innerHTML = `
            <h4>Welcome to Test Administration</h4>
            <p>You have <strong>${testCount}</strong> active tests in the system!</p>
        `;
    } else {
        welcomeMessage.innerHTML = `
            <h4>Welcome to Test Administration</h4>
            <p>You have no active tests. Start a new test by clicking the button above.</p>
        `;
    }
}

// Function to dispose a single sample
function disposeSample(testSampleId) {
    if (!testSampleId) return;
    
    confirmAction(`Are you sure you want to dispose this test sample?`, function() {
        // Show loading indicator
        showLoadingOverlay();
        
        fetch(`/api/disposeSample/${testSampleId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading indicator
            hideLoadingOverlay();
            
            if (data.success) {
                showSuccessMessage(`Sample disposed successfully!`);
                
                // Remove this sample from the UI
                const row = document.querySelector(`button[onclick*="${testSampleId}"]`).closest('tr');
                if (row) {
                    row.classList.add('table-danger');
                    setTimeout(() => {
                        row.remove();
                    }, 500);
                }
            } else {
                showErrorMessage(`Error disposing sample: ${data.error}`);
            }
        })
        .catch(error => {
            hideLoadingOverlay();
            showErrorMessage(`An error occurred: ${error}`);
        });
    });
}

// Function to return a sample to storage
function returnSampleToStorage(testSampleId) {
    if (!testSampleId) return;
    
    confirmAction(`Are you sure you want to return this sample to storage?`, function() {
        // Show loading indicator
        showLoadingOverlay();
        
        fetch(`/api/returnSampleToStorage/${testSampleId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading indicator
            hideLoadingOverlay();
            
            if (data.success) {
                showSuccessMessage(`Sample successfully returned to storage!`);
                
                // Update this sample in the UI to indicate it was returned
                const row = document.querySelector(`button[onclick*="${testSampleId}"]`).closest('tr');
                if (row) {
                    row.classList.add('table-success');
                    setTimeout(() => {
                        row.remove();
                    }, 500);
                }
            } else {
                showErrorMessage(`Error returning sample to storage: ${data.error}`);
            }
        })
        .catch(error => {
            hideLoadingOverlay();
            showErrorMessage(`An error occurred: ${error}`);
        });
    });
}

// Function to show chain of custody for a test sample
function showChainOfCustody(identifier) {
    if (!identifier) return;
    
    // Show loading indicator
    showLoadingOverlay();
    
    fetch(`/api/chainOfCustody/${identifier}`)
        .then(response => response.json())
        .then(data => {
            hideLoadingOverlay();
            
            if (data.success && data.chain_of_custody) {
                // Create a modal to display chain of custody
                const modal = document.createElement('div');
                modal.className = 'modal fade';
                modal.id = 'chainOfCustodyModal';
                modal.tabIndex = '-1';
                
                let historyHtml = '<div class="list-group mt-3">';
                
                // Build history timeline
                if (data.chain_of_custody.History && data.chain_of_custody.History.length > 0) {
                    data.chain_of_custody.History.forEach(item => {
                        // Style based on action type
                        let iconClass = 'fas fa-info-circle text-info';
                        
                        if (item.ActionType === 'Sample added to test') {
                            iconClass = 'fas fa-flask text-primary';
                        } else if (item.ActionType === 'Sample disposed') {
                            iconClass = 'fas fa-trash-alt text-danger';
                        } else if (item.ActionType === 'Sample returned to storage') {
                            iconClass = 'fas fa-archive text-success';
                        } else if (item.ActionType === 'Test completed') {
                            iconClass = 'fas fa-check-circle text-success';
                        } else if (item.ActionType === 'Test created') {
                            iconClass = 'fas fa-plus-circle text-primary';
                        }
                        
                        historyHtml += `
                            <div class="list-group-item">
                                <div class="d-flex w-100 justify-content-between">
                                    <h6 class="mb-1">
                                        <i class="${iconClass} me-2"></i>
                                        ${item.ActionType}
                                    </h6>
                                    <small>${item.Timestamp}</small>
                                </div>
                                <p class="mb-1">${item.Notes}</p>
                                <small>by ${item.UserName}</small>
                            </div>
                        `;
                    });
                } else {
                    historyHtml += '<div class="list-group-item">No history records found</div>';
                }
                
                historyHtml += '</div>';
                
                modal.innerHTML = `
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Chain of Custody: ${identifier}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div class="chain-of-custody-timeline">
                                    ${historyHtml}
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                `;
                
                // Remove existing modal if any
                const existingModal = document.getElementById('chainOfCustodyModal');
                if (existingModal) {
                    existingModal.remove();
                }
                
                // Add to document and show
                document.body.appendChild(modal);
                const bsModal = new bootstrap.Modal(modal);
                bsModal.show();
            } else {
                showErrorMessage(`Error fetching chain of custody: ${data.error || 'Unknown error'}`);
            }
        })
        .catch(error => {
            hideLoadingOverlay();
            showErrorMessage(`An error occurred: ${error}`);
        });
}

// Helper function for confirmations
function confirmAction(message, callback) {
    // Create a modal for confirmation
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'confirmActionModal';
    modal.tabIndex = '-1';
    
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Confirm Action</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p>${message}</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-danger" id="confirmActionBtn">Confirm</button>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('confirmActionModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add to document
    document.body.appendChild(modal);
    
    // Initialize Bootstrap modal
    const bsModal = new bootstrap.Modal(modal);
    
    // Add event listener to confirm button
    const confirmBtn = modal.querySelector('#confirmActionBtn');
    confirmBtn.addEventListener('click', function() {
        bsModal.hide();
        if (typeof callback === 'function') {
            callback();
        }
    });
    
    // Show the modal
    bsModal.show();
}

// Function to setup event handlers for the disposition buttons
function setupDispositionHandlers(testId, displayId) {
    console.log("Setting up disposition handlers for test", testId);
    
    // Setup event handlers for disposition buttons
    const disposeAllBtn = document.getElementById('disposeAllSamplesBtn');
    const returnAllBtn = document.getElementById('returnAllSamplesBtn');
    const decideIndividuallyBtn = document.getElementById('decideIndividuallyBtn');
    
    if (!disposeAllBtn || !returnAllBtn || !decideIndividuallyBtn) {
        console.error("Could not find disposition buttons");
        return;
    }
    
    // Remove any existing event listeners
    disposeAllBtn.replaceWith(disposeAllBtn.cloneNode(true));
    returnAllBtn.replaceWith(returnAllBtn.cloneNode(true));
    decideIndividuallyBtn.replaceWith(decideIndividuallyBtn.cloneNode(true));
    
    // Re-get the buttons after replacing
    const newDisposeAllBtn = document.getElementById('disposeAllSamplesBtn');
    const newReturnAllBtn = document.getElementById('returnAllSamplesBtn');
    const newDecideIndividuallyBtn = document.getElementById('decideIndividuallyBtn');
    
    // Add event listeners
    newDisposeAllBtn.addEventListener('click', function() {
        console.log("Dispose all samples button clicked for test", testId);
        disposeAllTestSamples(testId);
        
        // Close the modal
        const dispositionModal = bootstrap.Modal.getInstance(document.getElementById('sampleDispositionModal'));
        if (dispositionModal) {
            dispositionModal.hide();
        }
    });
    
    newReturnAllBtn.addEventListener('click', function() {
        console.log("Return all samples button clicked for test", testId);
        returnAllSamplesToStorage(testId);
        
        // Close the modal
        const dispositionModal = bootstrap.Modal.getInstance(document.getElementById('sampleDispositionModal'));
        if (dispositionModal) {
            dispositionModal.hide();
        }
    });
    
    newDecideIndividuallyBtn.addEventListener('click', function() {
        console.log("Decide individually button clicked for test", testId);
        // Close disposition modal
        const dispositionModal = bootstrap.Modal.getInstance(document.getElementById('sampleDispositionModal'));
        if (dispositionModal) {
            dispositionModal.hide();
        }
        
        // Show test details modal again
        setTimeout(() => {
            showTestDetails(testId);
        }, 300);
    });
}

// Function to return all samples to storage
function returnAllSamplesToStorage(testId) {
    // Show loading indicator
    showLoadingOverlay();
    
    fetch('/api/returnAllTestSamples', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ testId: testId })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // Hide loading indicator
        hideLoadingOverlay();
        
        if (data.success) {
            showSuccessMessage(`All samples returned to storage successfully!`);
            
            // Reload the page after a short delay
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showErrorMessage(`Error returning samples: ${data.error}`);
        }
    })
    .catch(error => {
        // Hide loading indicator
        hideLoadingOverlay();
        showErrorMessage(`An error occurred: ${error}`);
        console.error("Error returning samples to storage:", error);
    });
}

// Initialiser funktioner når siden indlæses
document.addEventListener('DOMContentLoaded', function() {
    // Opdater velkomstbesked
    const activeTestsCount = document.querySelector('.active-tests-count');
    if (activeTestsCount) {
        updateWelcomeMessage(parseInt(activeTestsCount.textContent) || 0);
    }
});