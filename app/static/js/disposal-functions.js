// Funktioner til håndtering af kassation

// Vis kassationsmodal
function showDisposalModal(event) {
    // Forhindre standard link-handling
    if (event) event.preventDefault();
    
    // Tjek om Bootstrap er tilgængeligt
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap er ikke indlæst. Kan ikke vise modal.');
        alert('Der opstod en fejl. Prøv venligst at genindlæse siden.');
        return;
    }
    
    // Tjek om modal-elementet eksisterer
    const modalElement = document.getElementById('disposalModal');
    if (!modalElement) {
        console.error('Modal-element ikke fundet:', 'disposalModal');
        alert('Modal ikke fundet. Kontakt venligst administrator.');
        return;
    }
    
    // Forsøg at hente data
    try {
        // Hent tilgængelige prøver og seneste kassationer
        Promise.all([
            fetch('/api/activeSamples').then(response => response.json()),
            fetch('/api/recentDisposals').then(response => response.json())
        ])
        .then(([samplesData, disposalsData]) => {
            // Opdater dropdown med tilgængelige prøver
            populateDisposalSampleSelect(samplesData.samples || []);
            
            // Opdater tabel med seneste kassationer
            populateRecentDisposalsTable(disposalsData.disposals || []);
            
            // Vis modal
            try {
                const modal = new bootstrap.Modal(modalElement);
                modal.show();
            } catch (modalError) {
                console.error('Fejl ved visning af modal:', modalError);
                alert('Kunne ikke vise modal. Prøv venligst at genindlæse siden.');
            }
        })
        .catch(error => {
            console.error("Kunne ikke hente data:", error);
            alert("Kunne ikke hente data. Prøv venligst igen.");
        });
    } catch (error) {
        console.error('Fejl i showDisposalModal:', error);
        alert('Der opstod en fejl. Prøv venligst igen.');
    }
}

// Populer dropdown med tilgængelige prøver
function populateDisposalSampleSelect(samples) {
    const sampleSelect = document.getElementById('sampleSelect');
    if (!sampleSelect) return;
    
    // Ryd dropdown bortset fra den første tomme option
    while (sampleSelect.options.length > 1) {
        sampleSelect.remove(1);
    }
    
    // Tilføj prøver til dropdown
    samples.forEach(sample => {
        const option = document.createElement('option');
        option.value = sample.SampleID;
        option.textContent = `${sample.SampleIDFormatted} - ${sample.Description} (${sample.AmountRemaining} ${sample.Unit})`;
        sampleSelect.appendChild(option);
    });
}

// Populer tabel med seneste kassationer
function populateRecentDisposalsTable(disposals) {
    const tableBody = document.getElementById('disposalTableBody');
    if (!tableBody) return;
    
    // Ryd tabellen
    tableBody.innerHTML = '';
    
    if (disposals.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center">Ingen nylige kassationer</td></tr>';
        return;
    }
    
    // Populer tabellen med kassationer
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

// Formatter dato til dansk format
function formatDate(dateString) {
    if (!dateString) return 'Ukendt';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('da-DK', {
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

// Opret kassation
function createDisposal() {
    // Hent input-værdier
    const sampleId = document.getElementById('sampleSelect').value;
    const amount = parseInt(document.getElementById('disposalAmount').value) || 0;
    const disposalUser = document.getElementById('disposalUser').value;
    const notes = document.getElementById('disposalNotes').value;
    
    // Valider input
    if (!sampleId) {
        showErrorMessage("Vælg venligst en prøve");
        return;
    }
    
    if (amount <= 0) {
        showErrorMessage("Antal skal være større end 0");
        return;
    }
    
    if (!disposalUser) {
        showErrorMessage("Vælg venligst en bruger");
        return;
    }
    
    // Opret kassationsdata
    const disposalData = {
        sampleId: sampleId,
        amount: amount,
        userId: disposalUser,
        notes: notes || "Kasseret via systemet"
    };
    
    // Send til server
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
            showSuccessMessage("Kassation er registreret succesfuldt!");
            
            // Luk modal og genindlæs siden
            const modal = bootstrap.Modal.getInstance(document.getElementById('disposalModal'));
            if (modal) modal.hide();
            
            // Genindlæs siden efter kort pause
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showErrorMessage(`Fejl ved kassation: ${data.error}`);
        }
    })
    .catch(error => {
        showErrorMessage(`Der opstod en fejl: ${error}`);
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

// Funktioner til håndtering af test oprettelse
function showCreateTestModal() {
    // Hent de tilgængelige prøver før vi viser modal
    fetchAvailableSamples()
        .then(() => {
            const modal = new bootstrap.Modal(document.getElementById('createTestModal'));
            modal.show();
        })
        .catch(error => {
            showErrorMessage("Kunne ikke hente tilgængelige prøver: " + error);
        });
}

// Funktion til at hente tilgængelige prøver
function fetchAvailableSamples() {
    return fetch('/api/activeSamples')
        .then(response => response.json())
        .then(data => {
            if (data.samples) {
                populateSampleTable(data.samples);
            } else {
                throw new Error("Ingen prøver returneret");
            }
        });
}

// Funktion til at populere prøvetabellen
function populateSampleTable(samples) {
    const tableBody = document.querySelector('#createTestModal .available-samples tbody');
    if (!tableBody) return;
    
    // Ryd tabellen
    tableBody.innerHTML = '';
    
    if (samples.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" class="text-center">Ingen prøver tilgængelige</td></tr>';
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
        showErrorMessage("Vælg venligst en testtype");
        return;
    }
    
    // Hent valgte prøver
    const selectedSampleElements = document.querySelectorAll('input[name="selectedSamples"]:checked');
    if (selectedSampleElements.length === 0) {
        showErrorMessage("Vælg mindst én prøve");
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
            showErrorMessage(`Fejl ved oprettelse af test: ${data.error}`);
            // Genaktiver knappen
            if (createTestBtn) {
                createTestBtn.disabled = false;
                createTestBtn.innerHTML = 'Opret Test';
            }
        }
    })
    .catch(error => {
        showErrorMessage(`Der opstod en fejl: ${error}`);
        // Genaktiver knappen
        if (createTestBtn) {
            createTestBtn.disabled = false;
            createTestBtn.innerHTML = 'Opret Test';
        }
    });
}

// Beskedfunktioner til at vise fejl og succes
function showSuccessMessage(message) {
    const successToast = document.createElement('div');
    successToast.className = 'custom-toast success-toast';
    successToast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-check-circle"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">Succes</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    document.body.appendChild(successToast);

    // Tilføj 'show' klasse efter en kort forsinkelse (for animationseffekt)
    setTimeout(() => successToast.classList.add('show'), 10);

    // Fjern automatisk efter 3 sekunder
    setTimeout(() => {
        successToast.classList.remove('show');
        setTimeout(() => successToast.remove(), 300);
    }, 3000);
}

// Vis advarsel hvis man forsøger at bruge flere prøver end tilgængelig
function validateSampleAmount(input) {
    const max = parseInt(input.getAttribute('max')) || 0;
    const value = parseInt(input.value) || 0;
    
    if (value > max) {
        input.value = max;
        showWarningMessage(`Maksimalt ${max} enheder tilgængelige`);
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
            <div class="toast-title">Advarsel</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    document.body.appendChild(warningToast);

    // Tilføj 'show' klasse efter en kort forsinkelse (for animationseffekt)
    setTimeout(() => warningToast.classList.add('show'), 10);

    // Fjern automatisk efter 4 sekunder
    setTimeout(() => {
        warningToast.classList.remove('show');
        setTimeout(() => warningToast.remove(), 300);
    }, 4000);
}

// Hjælpefunktion til at vise velkomsttekst baseret på antal aktive tests
function updateWelcomeMessage(testCount) {
    const welcomeMessage = document.querySelector('.welcome-message');
    if (!welcomeMessage) return;
    
    if (testCount > 0) {
        welcomeMessage.innerHTML = `
            <h4>Velkommen til Test Administration</h4>
            <p>Du har <strong>${testCount}</strong> aktive tests i systemet.</p>
        `;
    } else {
        welcomeMessage.innerHTML = `
            <h4>Velkommen til Test Administration</h4>
            <p>Du har ingen aktive tests. Start en ny test ved at klikke på knappen ovenfor.</p>
        `;
    }
}

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
                <span class="visually-hidden">Indlæser...</span>
            </div>
            <div class="loading-text mt-2">Behandler...</div>
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

// Opdateret disposeAllTestSamples funktion
function disposeAllTestSamples(testId) {
    confirmAction(`Er du sikker på at du vil kassere ALLE prøver i test ${testId}?`, function() {
        // Vis indlæsningsindikator
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
            // Skjul indlæsningsindikator
            hideLoadingOverlay();
            
            if (data.success) {
                showSuccessMessage(`Alle prøver i test ${testId} er kasseret!`);
                
                // Genindlæs siden efter kort pause
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showErrorMessage(`Fejl ved kassation: ${data.error}`);
            }
        })
        .catch(error => {
            // Skjul indlæsningsindikator
            hideLoadingOverlay();
            showErrorMessage(`Der opstod en fejl: ${error}`);
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
                    <h5 class="modal-title">Bekræft handling</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Luk"></button>
                </div>
                <div class="modal-body">
                    <p>${message}</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuller</button>
                    <button type="button" class="btn btn-primary" id="confirmActionBtn">Bekræft</button>
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

function showErrorMessage(message) {
    const errorToast = document.createElement('div');
    errorToast.className = 'custom-toast error-toast';
    errorToast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-exclamation-circle"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">Fejl</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    document.body.appendChild(errorToast);

    // Tilføj 'show' klasse efter en kort forsinkelse (for animationseffekt)
    setTimeout(() => errorToast.classList.add('show'), 10);

    // Fjern automatisk efter 5 sekunder
    setTimeout(() => {
        errorToast.classList.remove('show');
        setTimeout(() => errorToast.remove(), 300);
    }, 5000);
}

// Funktion til at vise test detaljer
function showTestDetails(testId) {
    fetch(`/api/testDetails/${testId}`)
        .then(response => response.json())
        .then(data => {
            if (data.test) {
                populateTestDetailsModal(data.test);
                const modal = new bootstrap.Modal(document.getElementById('testDetailsModal'));
                modal.show();
            } else {
                throw new Error("Ingen testdata returneret");
            }
        })
        .catch(error => {
            showErrorMessage(`Kunne ikke hente testdetaljer: ${error}`);
        });
}

// Funktion til at populere test detaljer i modal
function populateTestDetailsModal(test) {
    const modal = document.getElementById('testDetailsModal');
    if (!modal) return;
    
    // Find elementer i modalen
    const titleEl = modal.querySelector('.modal-title');
    const testInfoEl = modal.querySelector('.test-info');
    const samplesTableEl = modal.querySelector('.test-samples-table');
    
    // Opdater titel
    if (titleEl) {
        titleEl.textContent = `Test Detaljer: ${test.TestNo || test.TestID}`;
    }
    
    // Opdater test info
    if (testInfoEl) {
        testInfoEl.innerHTML = `
            <div class="row mb-3">
                <div class="col-md-6">
                    <p><strong>Test Navn:</strong> ${test.TestName || 'Ikke angivet'}</p>
                    <p><strong>Test Nummer:</strong> ${test.TestNo || test.TestID}</p>
                    <p><strong>Oprettet:</strong> ${test.CreatedDate || 'Ukendt'}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>Ejer:</strong> ${test.UserName || 'Ukendt'}</p>
                    <p><strong>Status:</strong> <span class="badge bg-primary">Aktiv</span></p>
                    <p><strong>Antal Prøver:</strong> ${test.Samples ? test.Samples.length : 0}</p>
                </div>
            </div>
        `;
    }
    
    // Opdater prøvetabel
    if (samplesTableEl && test.Samples) {
        const tableBody = samplesTableEl.querySelector('tbody');
        if (tableBody) {
            tableBody.innerHTML = '';
            
            if (test.Samples.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="4" class="text-center">Ingen prøver i denne test</td></tr>';
            } else {
                test.Samples.forEach((sample, index) => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${sample.GeneratedIdentifier || `${test.TestNo}_${index + 1}`}</td>
                        <td>${sample.Description || 'Ikke angivet'}</td>
                        <td>${sample.OriginalSampleID || 'N/A'}</td>
                        <td>
                            <div class="btn-group">
                                <button class="btn btn-sm btn-outline-primary">Detaljer</button>
                                <button class="btn btn-sm btn-outline-danger" onclick="disposeSample('${sample.TestSampleID}')">Kassér</button>
                            </div>
                        </td>
                    `;
                    tableBody.appendChild(row);
                });
            }
        }
    }
}

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
    
    // Opdater velkomstbesked
    const activeTestsCount = document.querySelector('.active-tests-count');
    if (activeTestsCount) {
        updateWelcomeMessage(parseInt(activeTestsCount.textContent) || 0);
    }
});

// Initialiser funktioner når siden indlæses
document.addEventListener('DOMContentLoaded', function() {
    // Tilføj event listeners til kassationsmodal
    const disposalLink = document.querySelector('a[href="#"][onclick="showDisposalModal(event)"]');
    if (disposalLink) {
        disposalLink.addEventListener('click', function(e) {
            e.preventDefault();
            showDisposalModal();
        });
    }
    
    // Tilføj event listener til prøvevalg i kassationsmodal
    const sampleSelect = document.getElementById('sampleSelect');
    if (sampleSelect) {
        sampleSelect.addEventListener('change', updateDisposalAmount);
    }
});