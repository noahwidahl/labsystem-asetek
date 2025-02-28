// Constants
const DEFAULT_EXPIRY_MONTHS = 2;
const NOTIFICATION_THRESHOLDS = {
    WARNING: 14, // days
    CRITICAL: 7  // days
};
let currentStep = 1;
const totalSteps = 3;
let scannedItems = [];
let selectedLocation = null;

// Initialize when document loads
document.addEventListener('DOMContentLoaded', () => {
    initializeApplication();
});

// Initialization
function initializeApplication() {
    // Generelle initialiseringer
    initializeUserProfile();
    setupFormListeners();
    setupScannerListeners();
    setupStorageGridListeners();
    
    // Initialiser funktioner baseret på den aktuelle sti
    const currentPath = window.location.pathname;
    
    if (currentPath === '/' || currentPath.includes('/dashboard')) {
        loadDashboardData();
    } else if (currentPath.includes('/register')) {
        setDefaultExpiryDate();
        setupRegistrationSteps();
        setupSerialNumberToggle();
        showStep(1);
    } else if (currentPath.includes('/storage')) {
        // Lager-specifikke initialiseringer
    } else if (currentPath.includes('/testing')) {
        // Test-specifikke initialiseringer
    }
    
    // Mock domain user info
    const domainUser = {
        username: 'BWM',
        domain: 'ASETEK',
        roles: ['Admin']
    };

    // Update UI with domain user
    updateUIWithDomainUser(domainUser);
}

// Load Storage Locations
function loadStorageLocations() {
    fetch('/api/storage-locations')
        .then(response => response.json())
        .then(data => {
            if (data.locations) {
                updateStorageGrid(data.locations);
            }
        })
        .catch(error => console.error('Error loading storage locations:', error));
}

function updateStorageGrid(locations) {
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '';

    locations.forEach(location => {
        const cell = document.createElement('div');
        cell.className = 'storage-cell';
        if(location.status === 'occupied') {
            cell.classList.add('occupied');
        }

        const locationEl = document.createElement('div');
        locationEl.className = 'location';
        locationEl.textContent = location.LocationName;

        const capacity = document.createElement('div');
        capacity.className = 'capacity';
        capacity.textContent = location.status === 'occupied' ? `${location.count} prøver` : 'Ledig';

        cell.appendChild(locationEl);
        cell.appendChild(capacity);
        grid.appendChild(cell);

        if (location.status !== 'occupied') {
            cell.addEventListener('click', () => selectStorageCell(cell));
        }
    });
}

// Profile Management Functions
function showProfileModal() {
    const modal = new bootstrap.Modal(document.getElementById('profileModal'));
    modal.show();
}

function saveProfiles() {
    const profiles = {
        admin: document.getElementById('adminProfile').checked,
        user: document.getElementById('userProfile').checked,
        guest: document.getElementById('guestProfile').checked
    };

    updateUIForProfiles(profiles);
    saveProfilesToLocalStorage(profiles);

    const modal = bootstrap.Modal.getInstance(document.getElementById('profileModal'));
    modal.hide();
}

function updateUIForProfiles(profiles) {
    const userRoles = document.querySelector('.user-roles');
    userRoles.innerHTML = '';

    if (profiles.admin) {
        userRoles.innerHTML += '<span class="role-badge admin">Admin</span>';
        enableAdminFeatures();
    }
    if (profiles.user) {
        userRoles.innerHTML += '<span class="role-badge user">Bruger</span>';
    }
    if (profiles.guest) {
        userRoles.innerHTML += '<span class="role-badge guest">Gæst</span>';
        disableEditingFeatures();
    }
}

function updateUIWithDomainUser(userInfo) {
    document.querySelector('.user-name').textContent = userInfo.username;

    const userRoles = document.querySelector('.user-roles');
    userRoles.innerHTML = '';

    userInfo.roles.forEach(role => {
        userRoles.innerHTML += `<span class="role-badge ${role.toLowerCase()}">${role}</span>`;
    });
}

// Registration Steps Functions
function updateProgress(step) {
    const hasSerialNumbers = document.getElementById('hasSerialNumbers');
    if (!hasSerialNumbers) return; // Afbryd hvis elementet ikke findes
    
    const isChecked = hasSerialNumbers.checked;
    const totalSteps = isChecked ? 3 : 2;
    
    // Beregn progress baseret på antal steps
    const progress = ((step - 1) / (totalSteps - 1)) * 100;
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
    }

    // Opdater steps visning
    const steps = document.querySelectorAll('.step');
    if (steps.length === 0) return;
    
    steps.forEach((el, index) => {
        el.classList.remove('active', 'completed');
        
        // Hvis vi ikke har serienumre og er på step 2, skip denne iteration
        if (!isChecked && index === 1) {
            return;
        }

        if (index + 1 < step) {
            el.classList.add('completed');
        } else if (index + 1 === step) {
            el.classList.add('active');
        }
    });
}

function setupSerialNumberToggle() {
    const checkbox = document.getElementById('hasSerialNumbers');
    if (checkbox) {
        checkbox.addEventListener('change', () => {
            const currentStep = document.querySelector('.form-step.active').id.replace('step', '');
            updateProgress(parseInt(currentStep));
        });
    }
}

function showStep(step) {
    const formSteps = document.querySelectorAll('.form-step');
    if (formSteps.length === 0) {
        console.warn("No form steps found");
        return; // Afbryd hvis der ikke er nogen form-trin
    }
    
    formSteps.forEach(el => {
        el.classList.remove('active');
    });

    const currentStep = document.querySelector(`.form-step:nth-child(${step})`);
    if (currentStep) {
        currentStep.classList.add('active');
        updateProgress(step);
        updateNavigationButtons(step);

        if (step === 3) {
            setupStorageGrid();
        }
    } else {
        console.warn(`Step ${step} not found`);
    }
}

function updateNavigationButtons(step) {
    const prevButton = document.querySelector('#prevButton');
    const nextButton = document.querySelector('#nextButton');

    if (prevButton) {
        prevButton.style.display = step === 1 ? 'none' : 'block';
    }

    if (nextButton) {
        if (step === totalSteps) {
            nextButton.textContent = 'Afslut';
            nextButton.onclick = handleFormSubmission;
        } else {
            nextButton.textContent = 'Næste';
            nextButton.onclick = nextStep;
        }
    }
}

function nextStep() {
    if (validateCurrentStep()) {
        const hasSerialNumbers = document.getElementById('hasSerialNumbers').checked;
        
        // Hvis vi er på step 1 og der ikke er serienumre, spring til step 3
        if (currentStep === 1 && !hasSerialNumbers) {
            currentStep = 3;
        } else {
            currentStep = Math.min(currentStep + 1, totalSteps);
        }
        
        showStep(currentStep);
    }
}

function previousStep() {
    const hasSerialNumbers = document.getElementById('hasSerialNumbers').checked;
    
    if (currentStep === 3 && !hasSerialNumbers) {
        currentStep = 1;
    } else {
        currentStep = Math.max(currentStep - 1, 1);
    }
    
    showStep(currentStep);
    
    // Aktivér/deaktivér tilbage-knappen
    const prevButton = document.querySelector('#prevButton');
    if (prevButton) {
        prevButton.disabled = currentStep === 1;
    }
}

// Form Validation and Submission
async function handleFormSubmission() {
    if (!validateCurrentStep()) return;
    
    const formData = {
        description: document.querySelector('[name="description"]').value,
        totalAmount: parseInt(document.querySelector('[name="totalAmount"]').value),
        unit: document.querySelector('[name="unit"]').value,
        owner: document.querySelector('[name="owner"]').value,
        supplier: document.querySelector('[name="supplier"]').value,
        expiryDate: document.querySelector('[name="expiryDate"]').value,
        hasSerialNumbers: document.getElementById('hasSerialNumbers').checked,
        other: document.querySelector('[name="other"]').value,
        serialNumbers: scannedItems,
        storageLocation: document.querySelector('[name="storageLocation"]').value || selectedLocation
    };
    
    try {
        const response = await fetch('/api/samples', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccessMessage(`Prøve ${result.sample_id} er blevet registreret succesfuldt`);
            
            setTimeout(() => {
                resetForm();
                showContent('storage');
            }, 1500);
        } else {
            showErrorMessage(`Fejl ved registrering: ${result.error}`);
        }
    } catch (error) {
        console.error('Error submitting form:', error);
        showErrorMessage('Der opstod en fejl ved registrering. Prøv igen senere.');
    }
}
    
function validateCurrentStep() {
    switch (currentStep) {
        case 1:
            // Valider den grundlæggende information
            const requiredFields = [
                'description',
                'totalAmount',
                'unit',
                'owner',
                'supplier',
                'expiryDate'
            ];
            
            let isValid = true;
            
            requiredFields.forEach(field => {
                const input = document.querySelector(`[name="${field}"]`);
                if (!input || !input.value.trim()) {
                    markInvalid(input);
                    isValid = false;
                } else {
                    markValid(input);
                }
            });
            
            return isValid;
            
        case 2:
            // Validering af serienumre, hvis de er påkrævet
            const hasSerialNumbers = document.getElementById('hasSerialNumbers').checked;
            const totalAmount = parseInt(document.querySelector('[name="totalAmount"]').value) || 0;
            
            if (hasSerialNumbers && scannedItems.length < totalAmount) {
                showErrorMessage(`Der mangler at blive scannet ${totalAmount - scannedItems.length} prøver`);
                return false;
            }
            
            return true;
            
        case 3:
            // Validering af lagerplacering
            const locationSelect = document.querySelector('[name="storageLocation"]');
            
            if ((!locationSelect || !locationSelect.value) && !selectedLocation) {
                showErrorMessage('Vælg venligst en lagerplacering');
                return false;
            }
            
            return true;
            
        default:
            return true;
    }
}
    
// Storage Grid Functions
function setupStorageGrid() {
    // Hent lagerplaceringer fra API'en
    fetch('/api/storage-locations')
        .then(response => response.json())
        .then(data => {
            if (data.locations) {
                updateStorageGrid(data.locations);
            }
        })
        .catch(error => {
            console.error('Error loading storage locations:', error);
            // Fallback til dummy data hvis API-kaldet fejler
            createDummyStorageGrid();
        });
}
    
function createDummyStorageGrid() {
    const grid = document.querySelector('.storage-grid');
    if (!grid) return;

    grid.innerHTML = '';

    for (let i = 1; i <= 12; i++) {
        const cell = document.createElement('div');
        cell.className = 'storage-cell';
        if (Math.random() > 0.7) cell.classList.add('occupied');

        const location = document.createElement('div');
        location.className = 'location';
        location.textContent = `A${Math.ceil(i/4)}.B${i % 4 || 4}`;

        const capacity = document.createElement('div');
        capacity.className = 'capacity';
        capacity.textContent = cell.classList.contains('occupied') ? 'Optaget' : 'Ledig';

        cell.appendChild(location);
        cell.appendChild(capacity);
        grid.appendChild(cell);

        if (!cell.classList.contains('occupied')) {
            cell.addEventListener('click', () => selectStorageCell(cell));
        }
    }
}
    
function setupStorageGridListeners() {
    document.querySelectorAll('.storage-cell').forEach(cell => {
        if (!cell.classList.contains('occupied')) {
            cell.addEventListener('click', () => selectStorageCell(cell));
        }
    });
}
    
function selectStorageCell(cell) {
    document.querySelectorAll('.storage-cell').forEach(c => c.classList.remove('selected'));
    cell.classList.add('selected');
    selectedLocation = cell.querySelector('.location').textContent;
}
    
// Scanner Functions
function setupScannerListeners() {
    const scannerInput = document.getElementById('barcodeInput');
    if (scannerInput) {
        scannerInput.addEventListener('keypress', handleScan);
    }
}
    
function handleScan(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        processScan(event.target.value);
        event.target.value = '';
    }
}
    
function processScan(barcode) {
    if (!barcode) return;

    const totalExpected = parseInt(document.querySelector('[name="amount"]')?.value) || 0;

    if (scannedItems.length < totalExpected) {
        scannedItems.push(barcode);
        updateScanUI();
    } else {
        showErrorMessage('Maksimalt antal prøver er nået');
    }
}
    
function updateScanUI() {
    const counter = document.getElementById('scannedCount');
    const totalCounter = document.getElementById('totalCount');
    const total = document.querySelector('[name="amount"]')?.value || 0;

    if (counter) counter.textContent = scannedItems.length;
    if (totalCounter) totalCounter.textContent = total;

    const container = document.querySelector('.scanned-items');
    if (container) {
        container.innerHTML = scannedItems.map((code, index) => `
            <div class="scanned-item">
                <span>${code}</span>
                <button onclick="removeScannedItem(${index})" class="btn btn-sm btn-danger">
                    Fjern
                </button>
            </div>
        `).join('');
    }
}
    
// Setup Event Listeners
function setupFormListeners() {
    document.querySelectorAll('input, select').forEach(input => {
        input.addEventListener('input', () => {
            if (input.classList.contains('invalid')) {
                validateField(input);
            }
        });
    });
}
    
function setupRegistrationSteps() {
    // Implementering kan tilpasses efter behov
    console.log('Setting up registration steps');
}
    
// Test Creation Functions
function showCreateTestModal() {
    const modal = new bootstrap.Modal(document.getElementById('createTestModal'));
    modal.show();
}
    
function createTest() {
    // Valider inputs
    const testType = document.querySelector('[name="testType"]');
    const testOwner = document.querySelector('[name="testOwner"]');
    
    if (!testType.value) {
        testType.classList.add('invalid');
        return;
    }
    
    if (!testOwner.value) {
        testOwner.classList.add('invalid');
        return;
    }
    
    const selectedSamples = getSelectedSamples();
    if (selectedSamples.length === 0) {
        showErrorMessage('Vælg mindst én prøve til testen');
        return;
    }
    
    const testData = {
        type: testType.value,
        owner: testOwner.value,
        testName: `${testType.options[testType.selectedIndex].text} Test`,
        description: `Test oprettet ${new Date().toLocaleDateString('da-DK')}`,
        samples: selectedSamples
    };

    // Send til API
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
            showSuccessMessage(`Test ${data.test_id} oprettet succesfuldt`);
            
            const modal = bootstrap.Modal.getInstance(document.getElementById('createTestModal'));
            modal.hide();
            
            // Reload testing page efter kortere delay
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            showErrorMessage(`Fejl ved oprettelse af test: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error creating test:', error);
        showErrorMessage('Der opstod en fejl ved oprettelse af test. Prøv igen senere.');
    });
}
    
function getSelectedSamples() {
    const selectedSamples = [];
    document.querySelectorAll('[name="selectedSamples"]:checked').forEach(checkbox => {
        const row = checkbox.closest('tr');
        const amountInput = row.querySelector('input[type="number"]');
        
        // Kontroller at mængden er gyldig
        if (amountInput && parseInt(amountInput.value) > 0) {
            selectedSamples.push({
                id: row.querySelector('td:nth-child(2)').textContent,
                amount: parseInt(amountInput.value)
            });
        } else if (amountInput) {
            amountInput.classList.add('invalid');
        }
    });
    return selectedSamples;
}
    
function updateTestOverview() {
    // Implementation would update the test overview UI
    console.log('Updating test overview');
}
    
// Expiry Check Functions
function showExpiringDetails() {
    // Indlæs udløbende prøver fra API
    fetch('/api/expiring-samples')
        .then(response => response.json())
        .then(data => {
            if (data.samples && data.samples.length > 0) {
                updateExpiringModal(data.samples);
            } else {
                updateExpiringModal([]);
            }
            const modal = new bootstrap.Modal(document.getElementById('expiringDetailsModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error loading expiring samples:', error);
            showErrorMessage('Kunne ikke indlæse udløbende prøver. Prøv igen senere.');
        });
}
    
function updateExpiringModal(samples) {
    const modalBody = document.querySelector('#expiringDetailsModal .modal-body');
    
    if (samples.length === 0) {
        modalBody.innerHTML = '<div class="alert alert-info">Ingen prøver der udløber inden for de næste 14 dage.</div>';
        return;
    }
    
    let tableContent = `
        <div class="table-responsive">
            <table class="table">
                <thead>
                    <tr>
                        <th>Prøve ID</th>
                        <th>Beskrivelse</th>
                        <th>Udløbsdato</th>
                        <th>Dage til udløb</th>
                        <th>Placering</th>
                        <th>Handling</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    samples.forEach(sample => {
        const warningClass = sample.days_until_expiry <= 7 ? 'danger' : 'warning';
        const formattedDate = new Date(sample.ExpireDate).toLocaleDateString('da-DK');
        
        tableContent += `
            <tr class="${warningClass}">
                <td>${sample.SampleID}</td>
                <td>${sample.Description}</td>
                <td>${formattedDate}</td>
                <td>${sample.days_until_expiry}</td>
                <td>${sample.LocationName}</td>
                <td>
                    <button class="btn btn-sm btn-warning" onclick="extendExpiryDate('${sample.SampleID}')">
                        Forlæng
                    </button>
                </td>
            </tr>
        `;
    });
    
    tableContent += `
                </tbody>
            </table>
        </div>
    `;
    
    modalBody.innerHTML = tableContent;
}
    
function extendExpiryDate(sampleId) {
    // Dette skal implementeres senere med et API-kald
    console.log(`Extending expiry date for sample: ${sampleId}`);
    showSuccessMessage(`Udløbsdato forlænget med 30 dage for ${sampleId}`);
}
    
function checkForExpiringSamples() {
    fetch('/api/expiring-samples')
        .then(response => response.json())
        .then(data => {
            if (data.samples && data.samples.length > 0) {
                // Vis notifikation
                showWarningMessage(`${data.samples.length} prøver udløber snart. Klik for detaljer.`, () => showExpiringDetails());
            }
        })
        .catch(error => console.error('Error checking expiring samples:', error));
}

// Container Functions
function showContainerModal(event) {
    if (event) event.preventDefault();
    
    // Hent container data via API
    fetch('/api/containers')
        .then(response => response.json())
        .then(data => {
            updateContainerTable(data.containers);
            
            // Vis modal
            const modal = new bootstrap.Modal(document.getElementById('containerModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error loading containers:', error);
            showErrorMessage('Kunne ikke indlæse container data. Prøv igen senere.');
        });
}

function updateContainerTable(containers) {
    const tableBody = document.getElementById('containerTableBody');
    
    if (!tableBody) return;
    
    if (!containers || containers.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center">Ingen containere fundet</td></tr>';
        return;
    }
    
    let html = '';
    containers.forEach(container => {
        html += `
            <tr>
                <td>${container.ContainerID}</td>
                <td>${container.Description}</td>
                <td>${container.IsMixed ? 'Ja' : 'Nej'}</td>
                <td>${container.sample_count || 0}</td>
            </tr>
        `;
    });
    
    tableBody.innerHTML = html;
}

function createContainer() {
    const description = document.getElementById('containerDescription').value;
    const isMixed = document.getElementById('isMixed').checked;
    
    if (!description) {
        showErrorMessage('Indtast venligst en beskrivelse');
        return;
    }
    
    const containerData = {
        description: description,
        isMixed: isMixed
    };
    
    fetch('/api/createContainer', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(containerData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage(`Container ${data.container_id} er oprettet`);
            
            // Nulstil form
            document.getElementById('containerDescription').value = '';
            document.getElementById('isMixed').checked = false;
            
            // Opdater container tabel
            fetch('/api/containers')
                .then(response => response.json())
                .then(data => {
                    updateContainerTable(data.containers);
                });
        } else {
            showErrorMessage(`Fejl ved oprettelse af container: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error creating container:', error);
        showErrorMessage('Der opstod en fejl ved oprettelse af container. Prøv igen senere.');
    });
}

// Disposal Functions
function showDisposalModal(event) {
    if (event) event.preventDefault();
    
    // Hent aktive prøver til dropdown
    fetch('/api/activeSamples')
        .then(response => response.json())
        .then(data => {
            updateSampleSelect(data.samples);
            
            // Hent seneste kassationer
            fetch('/api/recentDisposals')
                .then(response => response.json())
                .then(data => {
                    updateDisposalTable(data.disposals);
                    
                    // Vis modal
                    const modal = new bootstrap.Modal(document.getElementById('disposalModal'));
                    modal.show();
                });
        })
        .catch(error => {
            console.error('Error loading active samples:', error);
            showErrorMessage('Kunne ikke indlæse prøve data. Prøv igen senere.');
        });
}

function updateSampleSelect(samples) {
    const sampleSelect = document.getElementById('sampleSelect');
    
    if (!sampleSelect) return;
    
    // Behold den første option (Vælg prøve)
    sampleSelect.innerHTML = '<option value="">Vælg prøve</option>';
    
    if (!samples || samples.length === 0) {
        sampleSelect.innerHTML += '<option disabled>Ingen prøver tilgængelige</option>';
        return;
    }
    
    samples.forEach(sample => {
        sampleSelect.innerHTML += `
            <option value="${sample.SampleID}">${sample.SampleIDFormatted} - ${sample.Description} (${sample.AmountRemaining} ${sample.Unit})</option>
        `;
    });
}

function updateDisposalTable(disposals) {
    const tableBody = document.getElementById('disposalTableBody');
    
    if (!tableBody) return;
    
    if (!disposals || disposals.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center">Ingen kassationer fundet</td></tr>';
        return;
    }
    
    let html = '';
    disposals.forEach(disposal => {
        html += `
            <tr>
                <td>${disposal.SampleID}</td>
                <td>${disposal.DisposalDate}</td>
                <td>${disposal.AmountDisposed}</td>
                <td>${disposal.DisposedBy}</td>
            </tr>
        `;
    });
    
    tableBody.innerHTML = html;
}

function createDisposal() {
    const sampleId = document.getElementById('sampleSelect').value;
    const amount = document.getElementById('disposalAmount').value;
    const userId = document.getElementById('disposalUser').value;
    const notes = document.getElementById('disposalNotes').value;
    
    if (!sampleId) {
        showErrorMessage('Vælg venligst en prøve');
        return;
    }
    
    if (!amount || amount <= 0) {
        showErrorMessage('Indtast venligst et gyldigt antal');
        return;
    }
    
    if (!userId) {
        showErrorMessage('Vælg venligst en bruger');
        return;
    }
    
    const disposalData = {
        sampleId: sampleId,
        amount: amount,
        userId: userId,
        notes: notes
    };
    
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
            showSuccessMessage(`Kassation ${data.disposal_id} er registreret`);
            
            // Nulstil form
            document.getElementById('sampleSelect').selectedIndex = 0;
            document.getElementById('disposalAmount').value = '';
            document.getElementById('disposalNotes').value = '';
            
            // Opdater prøver og kassationstabel
            fetch('/api/activeSamples')
                .then(response => response.json())
                .then(data => {
                    updateSampleSelect(data.samples);
                });
                
            fetch('/api/recentDisposals')
                .then(response => response.json())
                .then(data => {
                    updateDisposalTable(data.disposals);
                });
        } else {
            showErrorMessage(`Fejl ved registrering af kassation: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error creating disposal:', error);
        showErrorMessage('Der opstod en fejl ved registrering af kassation. Prøv igen senere.');
    });
}
    
// Utility Functions
function showSuccessMessage(message) {
    const successToast = document.createElement('div');
    successToast.className = 'toast show';
    successToast.role = 'alert';
    successToast.ariaLive = 'assertive';
    successToast.style.position = 'fixed';
    successToast.style.top = '20px';
    successToast.style.right = '20px';
    successToast.style.zIndex = '1050';
    successToast.innerHTML = `
        <div class="toast-header bg-success text-white">
            <strong class="me-auto">Succes</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;
    document.body.appendChild(successToast);

    setTimeout(() => {
        successToast.remove();
    }, 3000);
}
    
function showErrorMessage(message) {
    const errorToast = document.createElement('div');
    errorToast.className = 'toast show';
    errorToast.role = 'alert';
    errorToast.ariaLive = 'assertive';
    errorToast.style.position = 'fixed';
    errorToast.style.top = '20px';
    errorToast.style.right = '20px';
    errorToast.style.zIndex = '1050';
    errorToast.innerHTML = `
        <div class="toast-header bg-danger text-white">
            <strong class="me-auto">Fejl</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;
    document.body.appendChild(errorToast);

    setTimeout(() => {
        errorToast.remove();
    }, 3000);
}
    
function showWarningMessage(message, clickCallback = null) {
    const warningToast = document.createElement('div');
    warningToast.className = 'toast show';
    warningToast.role = 'alert';
    warningToast.ariaLive = 'assertive';
    warningToast.style.position = 'fixed';
    warningToast.style.top = '20px';
    warningToast.style.right = '20px';
    warningToast.style.zIndex = '1050';
    warningToast.style.cursor = clickCallback ? 'pointer' : 'default';
    
    if (clickCallback) {
        warningToast.addEventListener('click', clickCallback);
    }
    
    warningToast.innerHTML = `
        <div class="toast-header bg-warning text-dark">
            <strong class="me-auto">Advarsel</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;
    document.body.appendChild(warningToast);

    setTimeout(() => {
        warningToast.remove();
    }, 5000);
}
    
function resetForm() {
    currentStep = 1;
    scannedItems = [];
    selectedLocation = null;

    document.querySelectorySelectorAll('input:not([type="radio"]):not([type="checkbox"])').forEach(input => {
        input.value = '';
        input.classList.remove('invalid');
    });
    document.querySelectorAll('select').forEach(select => {
        select.selectedIndex = 0;
        select.classList.remove('invalid');
    });
    
    // Reset checkbox
    if (document.getElementById('hasSerialNumbers')) {
        document.getElementById('hasSerialNumbers').checked = false;
    }
    
    // Clear scanned items container
    const scannedItemsContainer = document.querySelector('.scanned-items');
    if (scannedItemsContainer) {
        scannedItemsContainer.innerHTML = '';
    }

    setDefaultExpiryDate();
    showStep(1);
}
    
// Helper Functions
function validateField(input) {
    if (!input.value) {
        markInvalid(input);
    } else {
        markValid(input);
    }
}
    
function markInvalid(element) {
    element.classList.add('invalid');
}
    
function markValid(element) {
    element.classList.remove('invalid');
}
    
function setDefaultExpiryDate() {
    const expiryInput = document.querySelector('input[name="expiryDate"]');
    if (expiryInput) {
        const defaultDate = new Date();
        defaultDate.setMonth(defaultDate.getMonth() + DEFAULT_EXPIRY_MONTHS);
        expiryInput.valueAsDate = defaultDate;
    }
}
    
function validateForm() {
    let isValid = true;
    document.querySelectorAll('[required]').forEach(input => {
        if (!input.value) {
            isValid = false;
            markInvalid(input);
        } else {
            markValid(input);
        }
    });
    return isValid;
}
    
function saveRegistrationData(formData) {
    localStorage.setItem('registeredSamples', JSON.stringify(formData));
}
    
function saveProfilesToLocalStorage(profiles) {
    localStorage.setItem('userProfiles', JSON.stringify(profiles));
}
    
function initializeUserProfile() {
    const savedProfiles = localStorage.getItem('userProfiles');
    if (savedProfiles) {
        updateUIForProfiles(JSON.parse(savedProfiles));
    }
}
    
function loadDashboardData() {
    // Hent udløbende prøver
    checkForExpiringSamples();
    
    // Hent lagerpladser
    loadStorageLocations();
    
    // Andre dashboard data kunne hentes her
}
    
function enableAdminFeatures() {
    // Implementation af admin features
    console.log('Admin features enabled');
}
    
function disableEditingFeatures() {
    // Implementation af read-only mode
    console.log('Editing features disabled');
}
    
function removeScannedItem(index) {
    scannedItems.splice(index, 1);
    updateScanUI();
}

// For at håndtere navigation mellem sider
function showContent(section) {
    // Hvis det er en faktisk URL, så navigér til den
    if (section.startsWith('/')) {
        window.location.href = section;
        return;
    }
    
    // Ellers skjul alle sektioner og vis den forespurgte
    document.querySelectorAll('.content-section').forEach(el => {
        el.classList.remove('active');
    });
    
    const targetSection = document.getElementById(section);
    if (targetSection) {
        targetSection.classList.add('active');
        // Opdater også aktiv klassen i navigationen
        document.querySelectorAll('.nav-item').forEach(el => {
            el.classList.remove('active');
        });
        document.querySelector(`.nav-item[href*="${section}"]`)?.classList.add('active');
    }
}
    
// Export necessary functions for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        validateForm,
        handleScan,
        showContent,
        updateUIForProfiles,
        showContainerModal,
        showDisposalModal,
        createContainer,
        createDisposal
    };
}