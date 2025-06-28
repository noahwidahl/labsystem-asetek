// Functions for handling disposal

// Show disposal modal
function showDisposalModal(event) {
    console.log("disposal-functions.js: showDisposalModal called");
    
    // Prevent standard link handling
    if (event) event.preventDefault();
    
    // Check if Bootstrap is available
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap is not loaded. Cannot show modal.');
        alert('An error occurred. Please try reloading the page.');
        return;
    }
    
    // Check if modal element exists
    const modalElement = document.getElementById('disposalModal');
    if (!modalElement) {
        console.error('Modal element not found:', 'disposalModal');
        alert('Modal not found. Please contact the administrator.');
        return;
    }
    
    console.log("disposal-functions.js: Modal element found, proceeding with data load");
    
    // Attempt to fetch data
    try {
        // Get available samples and recent disposals
        Promise.all([
            fetch('/api/activeSamples')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (!data.success) {
                        throw new Error(data.error || "Failed to fetch samples");
                    }
                    return data;
                }),
            fetch('/api/recentDisposals')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (!data.success) {
                        throw new Error(data.error || "Failed to fetch disposal history");
                    }
                    return data;
                })
        ])
        .then(([samplesData, disposalsData]) => {
            console.log("Active samples data:", samplesData);
            
            // Update dropdown with available samples
            populateDisposalSampleSelect(samplesData.samples || []);
            
            // Update table with recent disposals
            populateRecentDisposalsTable(disposalsData.disposals || []);
            
            // Show modal
            try {
                const modal = new bootstrap.Modal(modalElement);
                modal.show();
            } catch (modalError) {
                console.error('Error showing modal:', modalError);
                alert('Could not show modal. Please try reloading the page.');
            }
        })
        .catch(error => {
            console.error("Could not fetch data:", error);
            showErrorMessageDisposal(`Could not fetch data: ${error.message || "Unknown error"}`);
        });
    } catch (error) {
        console.error('Error in showDisposalModal:', error);
        alert('An error occurred. Please try again.');
    }
}

// Populate dropdown with available samples
function populateDisposalSampleSelect(samples) {
    const sampleSelect = document.getElementById('sampleSelect');
    if (!sampleSelect) return;
    
    // Clear dropdown except for the first empty option
    while (sampleSelect.options.length > 1) {
        sampleSelect.remove(1);
    }
    
    // Check if there are any samples
    if (!samples || samples.length === 0) {
        const option = document.createElement('option');
        option.value = "";
        option.textContent = "No samples available for disposal";
        option.disabled = true;
        sampleSelect.appendChild(option);
        
        // Display a user-friendly message
        showWarningMessage("No samples available for disposal. Please register new samples first.");
        return;
    }
    
    // Add samples to dropdown
    samples.forEach(sample => {
        // Skip if essential data is missing
        if (!sample.SampleID || !sample.Description) return;
        
        const option = document.createElement('option');
        option.value = sample.SampleID;
        
        // Format the display text with available information
        let displayText = `${sample.SampleIDFormatted || `SMP-${sample.SampleID}`} - ${sample.Description}`;
        
        // Add amount and unit if available
        if (sample.AmountRemaining) {
            const unit = sample.Unit || 'pcs';
            displayText += ` (${sample.AmountRemaining} ${unit})`;
        }
        
        // Add location if available and not "Unknown"
        if (sample.LocationName && sample.LocationName !== "Unknown") {
            displayText += ` - ${sample.LocationName}`;
        }
        
        option.textContent = displayText;
        sampleSelect.appendChild(option);
    });
    
    console.log(`Populated disposal sample select with ${samples.length} samples`);
}

// Populate table with recent disposals
function populateRecentDisposalsTable(disposals) {
    const tableBody = document.getElementById('disposalTableBody');
    if (!tableBody) return;
    
    // Clear the table
    tableBody.innerHTML = '';
    
    if (disposals.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center">No recent disposals</td></tr>';
        return;
    }
    
    // Populate the table with disposals
    disposals.forEach(disposal => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${disposal.SampleID}</td>
            <td>${formatDate(disposal.DisposalDate)}</td>
            <td>${disposal.AmountDisposed}</td>
            <td>${disposal.DisposedBy}</td>
        `;
        tableBody.appendChild(row);
    });
}

// Format date to the international format
function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

// Add event listener to sample selection in disposal modal
function updateDisposalAmount() {
    const sampleSelect = document.getElementById('sampleSelect');
    const disposalAmount = document.getElementById('disposalAmount');
    
    if (!sampleSelect || !disposalAmount) return;
    
    // If no sample selected, disable amount field
    if (!sampleSelect.value) {
        disposalAmount.disabled = true;
        disposalAmount.value = '';
        return;
    }
    
    // Enable amount field
    disposalAmount.disabled = false;
    
    // Find selected sample from dropdown text
    const selectedOption = sampleSelect.options[sampleSelect.selectedIndex];
    const optionText = selectedOption.textContent;
    
    // Try to extract maximum amount from text with regex
    const match = optionText.match(/\((\d+)/);
    if (match && match[1]) {
        const maxAmount = parseInt(match[1]);
        disposalAmount.max = maxAmount;
        disposalAmount.value = 1;
        disposalAmount.placeholder = `Max: ${maxAmount}`;
    }
}

// Create disposal
function createDisposal() {
    // Get input values
    const sampleId = document.getElementById('sampleSelect').value;
    const amount = parseInt(document.getElementById('disposalAmount').value) || 0;
    const disposalUser = document.getElementById('disposalUser').value;
    const notes = document.getElementById('disposalNotes').value;
    
    // Validate input
    if (!sampleId) {
        showErrorMessageDisposal("Please select a sample");
        return;
    }
    
    if (amount <= 0) {
        showErrorMessageDisposal("Amount must be greater than 0");
        return;
    }
    
    if (!disposalUser) {
        showErrorMessageDisposal("Please select a user");
        return;
    }
    
    // Create disposal data
    const disposalData = {
        sampleId: sampleId,
        amount: amount,
        userId: disposalUser,
        notes: notes || "Disposed via system"
    };
    
    // Send to server
    fetch('/api/createDisposal', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(disposalData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage("Disposal has been registered successfully!");
            
            // Close modal and reload page
            const modal = bootstrap.Modal.getInstance(document.getElementById('disposalModal'));
            if (modal) modal.hide();
            
            // Reload page after short pause
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showErrorMessageDisposal(`Error during disposal: ${data.error}`);
        }
    })
    .catch(error => {
        showErrorMessageDisposal(`An error occurred: ${error}`);
    });
}

// Function to dispose a test sample
function disposeSample(testSampleId) {
    if (confirm("Are you sure you want to dispose this sample?")) {
        fetch('/api/disposeSample', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ testSampleId: testSampleId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSuccessMessage("Sample has been disposed successfully!");
                
                // Reload page after short pause
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showErrorMessage(`Error during disposal: ${data.error}`);
            }
        })
        .catch(error => {
            showErrorMessage(`An error occurred: ${error}`);
        });
    }
}

// Dispose all samples at once
function disposeAllTestSamples(testId) {
    if (confirm(`Are you sure you want to dispose ALL samples in test ${testId}?`)) {
        fetch('/api/disposeAllTestSamples', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ testId: testId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSuccessMessage(`All samples in test ${testId} have been disposed!`);
                
                // Reload page after short pause
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showErrorMessage(`Error during disposal: ${data.error}`);
            }
        })
        .catch(error => {
            showErrorMessage(`An error occurred: ${error}`);
        });
    }
}

// Functions for handling test creation - RENAMED to avoid conflicts
// This function should not be called from disposal page
function showCreateTestModalForDisposal() {
    // Fetch available samples before showing modal
    fetchAvailableSamplesForDisposal()
        .then(() => {
            const modal = new bootstrap.Modal(document.getElementById('createTestModal'));
            modal.show();
        })
        .catch(error => {
            showErrorMessageDisposal("Could not load available samples: " + error);
        });
}

// Funktion til at hente tilgængelige prøver
// This function is renamed to avoid conflict with test-functions.js
function fetchAvailableSamplesForDisposal() {
    return fetch('/api/activeSamples')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("API response for disposal:", data);
            
            if (data.success) {
                // Always pass a valid array to populateSampleTable
                const samples = Array.isArray(data.samples) ? data.samples : [];
                populateSampleTableForDisposal(samples);
                return; // Successful handling
            } 
            
            // If we get here, there was an error in the response
            throw new Error(data.error || "No samples available");
        });
}

// Funktion til at populere prøvetabellen
// This function is renamed to avoid conflict with test-functions.js
function populateSampleTableForDisposal(samples) {
    const tableBody = document.querySelector('#createTestModal .available-samples tbody');
    if (!tableBody) return;
    
    // Clear the table
    tableBody.innerHTML = '';
    
    if (samples.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" class="text-center">No samples available</td></tr>';
        return;
    }
    
    // Populer tabellen med prøver
    samples.forEach(sample => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <input type="checkbox" name="selectedSamples" value="${sample.SampleID}">
            </td>
            <td>${sample.SampleIDFormatted}</td>
            <td>${sample.Description}</td>
            <td>${sample.LocationName}</td>
            <td>
                <input type="number" class="form-control form-control-sm" name="sampleAmount" 
                       value="1" min="1" max="${sample.AmountRemaining}" data-id="${sample.SampleID}">
            </td>
        `;
        tableBody.appendChild(row);
    });
    
    // Tilføj event listener til "Vælg alle" checkbox
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

// Funktion til at oprette en test
function createTest() {
    // Hent testoplysninger
    const testType = document.querySelector('[name="testType"]').value;
    const testOwner = document.querySelector('[name="testOwner"]').value;
    
    // Valider input
    if (!testType) {
        showErrorMessageDisposal("Please select a test type");
        return;
    }
    
    // Hent valgte prøver
    const selectedSampleElements = document.querySelectorAll('input[name="selectedSamples"]:checked');
    if (selectedSampleElements.length === 0) {
        showErrorMessageDisposal("Select at least one sample");
        return;
    }
    
    // Opbyg array af valgte prøver med antal
    const selectedSamples = Array.from(selectedSampleElements).map(element => {
        const sampleId = element.value;
        const amountInput = document.querySelector(`input[name="sampleAmount"][data-id="${sampleId}"]`);
        const amount = amountInput ? parseInt(amountInput.value) || 1 : 1;
        
        return {
            id: sampleId,
            amount: amount
        };
    });
    
    // Opret testdata
    const testData = {
        type: testType,
        owner: testOwner,
        samples: selectedSamples,
        description: document.querySelector('[name="testDescription"]')?.value || ''
    };
    
    // Vis spinner under behandling
    const createTestBtn = document.querySelector('#createTestBtn');
    if (createTestBtn) {
        createTestBtn.disabled = true;
        createTestBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Opretter...';
    }
    
    // Send til server
    fetch('/api/createTest', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(testData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage(`Test ${data.test_id} er blevet oprettet succesfuldt!`);
            
            // Luk modal og genindlæs siden
            const modal = bootstrap.Modal.getInstance(document.getElementById('createTestModal'));
            if (modal) modal.hide();
            
            // Genindlæs siden efter kort pause
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showErrorMessageDisposal(`Error creating test: ${data.error}`);
            // Genaktiver knappen
            if (createTestBtn) {
                createTestBtn.disabled = false;
                createTestBtn.innerHTML = 'Create Test';
            }
        }
    })
    .catch(error => {
        showErrorMessageDisposal(`An error occurred: ${error}`);
        // Genaktiver knappen
        if (createTestBtn) {
            createTestBtn.disabled = false;
            createTestBtn.innerHTML = 'Create Test';
        }
    });
}

// Message functions for displaying errors and success
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

// Show warning if trying to use more samples than available
function validateSampleAmount(input) {
    const max = parseInt(input.getAttribute('max')) || 0;
    const value = parseInt(input.value) || 0;
    
    if (value > max) {
        input.value = max;
        showWarningMessage(`Maximum ${max} units available`);
    } else if (value < 1) {
        input.value = 1;
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

// Fjernet updateWelcomeMessage fra disposal-functions.js for at undgå konflikt
// Denne funktion er nu kun defineret i test-functions.js

function showLoadingOverlay() {
    // Tjek om overlay allerede eksisterer
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

// Skjul loading overlay
function hideLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.add('fade-out');
        setTimeout(() => {
            overlay.remove();
        }, 300);
    }
}

// Updated disposeAllTestSamples function
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
        .then(response => response.json())
        .then(data => {
            // Hide loading indicator
            hideLoadingOverlay();
            
            if (data.success) {
                showSuccessMessage(`All samples in test ${testId} have been disposed!`);
                
                // Reload page after short pause
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showErrorMessageDisposal(`Error during disposal: ${data.error}`);
            }
        })
        .catch(error => {
            // Hide loading indicator
            hideLoadingOverlay();
            showErrorMessageDisposal(`An error occurred: ${error}`);
        });
    });
}

function confirmAction(message, onConfirm) {
    // Opret elementer til modal
    const modalEl = document.createElement('div');
    modalEl.className = 'modal fade';
    modalEl.id = 'confirmActionModal';
    modalEl.tabIndex = '-1';
    modalEl.setAttribute('aria-hidden', 'true');
    
    modalEl.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header bg-warning">
                    <h5 class="modal-title">Confirm Action</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p>${message}</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="confirmActionBtn">Confirm</button>
                </div>
            </div>
        </div>
    `;
    
    // Tilføj modal til body
    document.body.appendChild(modalEl);
    
    // Initialiser Bootstrap modal
    const modal = new bootstrap.Modal(modalEl);
    
    // Tilføj event listener til konfirmationsknap
    document.getElementById('confirmActionBtn').addEventListener('click', function() {
        modal.hide();
        if (typeof onConfirm === 'function') {
            onConfirm();
        }
        
        // Fjern modal fra DOM efter brug
        modalEl.addEventListener('hidden.bs.modal', function(event) {
            modalEl.remove();
        });
    });
    
    // Vis modal
    modal.show();
}

// This is renamed to avoid conflict with the function in test-functions.js
function showErrorMessageDisposal(message) {
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

// This function will be handled by test-functions.js instead
// Removed to avoid conflict with the same function in test-functions.js

// This function will be handled by test-functions.js instead
// Removed to avoid conflict with the same function in test-functions.js

// Initialiser funktioner når siden indlæses
document.addEventListener('DOMContentLoaded', function() {
    // Tilføj event listeners til test knapper
    const createTestBtn = document.querySelector('button[onclick="showCreateTestModal()"]');
    if (createTestBtn) {
        createTestBtn.addEventListener('click', showCreateTestModal);
    }
    
    // Lyt efter ændringer i antal input
    document.addEventListener('change', function(e) {
        if (e.target && e.target.name === 'sampleAmount') {
            validateSampleAmount(e.target);
        }
    });
    
    // Lad være med at opdatere velkomstbesked fra denne fil
    // Det håndteres i test-functions.js
});

// Initialiser funktioner når siden indlæses
document.addEventListener('DOMContentLoaded', function() {
    // Tjek om siden er container-administration
    const isContainerPage = window.location.pathname.includes('/containers');
    
    // Hvis det er container-siden, lad container-management.js håndtere disposal-modalen
    if (!isContainerPage) {
        // Tilføj event listeners til kassationsmodal kun for ikke-container sider
        const disposalLink = document.querySelector('a[href="#"][onclick="showDisposalModal(event)"]');
        if (disposalLink) {
            // Fjern den oprindelige onclick for at undgå at den bliver kaldt to gange
            const originalOnClick = disposalLink.getAttribute('onclick');
            disposalLink.removeAttribute('onclick');
            
            disposalLink.addEventListener('click', function(e) {
                e.preventDefault();
                showDisposalModal();
            });
        }
    } else {
        console.log("Container side detekteret - disposal modal håndteres af container-management.js");
    }
    
    // Tilføj event listener til prøvevalg i kassationsmodal - dette er altid nødvendigt
    const sampleSelect = document.getElementById('sampleSelect');
    if (sampleSelect) {
        sampleSelect.addEventListener('change', updateDisposalAmount);
    }
});