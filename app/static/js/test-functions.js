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
// Funktion til at oprette en test
function createTest() {
    // Hent testoplysninger
    const testType = document.querySelector('[name="testType"]').value;
    const testOwner = document.querySelector('[name="testOwner"]').value;
    
    // Valider input
    if (!testType) {
        showErrorMessage("Please select a test type");
        return;
    }
    
    // Hent valgte prøver
    const selectedSampleElements = document.querySelectorAll('input[name="selectedSamples"]:checked');
    if (selectedSampleElements.length === 0) {
        showErrorMessage("Select at least one sample");
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
        samples: selectedSamples
    };
    
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
            showSuccessMessage(`Test ${data.test_id} has been created successfully!`);
            
            // Luk modal og genindlæs siden
            const modal = bootstrap.Modal.getInstance(document.getElementById('createTestModal'));
            if (modal) modal.hide();
            
            // Genindlæs siden efter kort pause
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

// CompleteTest funktion
function completeTest(testId) {
    confirmAction(`Are you sure you want to finish test ${testId}?`, function() {
        // Vis indlæsningsindikator
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
            // Skjul indlæsningsindikator
            hideLoadingOverlay();
            
            if (data.success) {
                showSuccessMessage(`Test ${testId} has been finished!`);
                
                // Luk modal hvis åben
                const modal = bootstrap.Modal.getInstance(document.getElementById('testDetailsModal'));
                if (modal) modal.hide();
                
                // Fjern test-kortet manuelt (klientsiden)
                removeTestCardFromDOM(testId);
            } else {
                showErrorMessage(`Error while finishing test: ${data.error}`);
            }
        })
        .catch(error => {
            // Skjul indlæsningsindikator
            hideLoadingOverlay();
            showErrorMessage(`An error has occured: ${error}`);
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

function showTestDetails(testId) {
    currentTestId = testId;
    // Vis loading indikator
    const modal = new bootstrap.Modal(document.getElementById('testDetailsModal'));
    modal.show();
    
    // Vis indlæsningsindikator i modalen
    document.querySelector('.test-info').innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Loading test details...</p></div>';
    document.querySelector('.test-samples-table tbody').innerHTML = '<tr><td colspan="4" class="text-center">Loading...</td></tr>';
    
    // Hent testdetaljer fra serveren
    fetch(`/api/testDetails/${testId}`)
        .then(response => {
            if (response.status === 404) {
                // Hvis testen ikke findes (måske er den blevet afsluttet)
                throw new Error("The test was not found. It may have been completed.");
            }
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.test) {
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

// Funktion til at kassere alle prøver på én gang
function disposeAllTestSamples(testId) {
    confirmAction(`Are you sure you want to dispose ALL samples in test ${testId}?`, function() {
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
                showSuccessMessage(`All samples in test ${testId} have been disposed!`);
                
                // Genindlæs siden efter kort pause
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showErrorMessage(`Error during disposal: ${data.error}`);
            }
        })
        .catch(error => {
            // Skjul indlæsningsindikator
            hideLoadingOverlay();
            showErrorMessage(`An error occurred: ${error}`);
        });
    });
}

function populateTestDetailsModal(test) {
    const testInfoEl = document.querySelector('.test-info');
    const samplesTableEl = document.querySelector('.test-samples-table tbody');
    
    // Opdater titel
    document.querySelector('#testDetailsModal .modal-title').textContent = `Test Detaljer: ${test.TestNo || test.TestID}`;
    
    // Opdater test information
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
        ${test.Description ? `<p><strong>Beskrivelse:</strong> ${test.Description}</p>` : ''}
    `;
    
    // Opdater prøvetabel
    if (test.Samples && test.Samples.length > 0) {
        samplesTableEl.innerHTML = '';
        
        test.Samples.forEach((sample, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${sample.GeneratedIdentifier || `${test.TestNo}_${index + 1}`}</td>
                <td>${sample.Description || 'Ikke angivet'}</td>
                <td>PRV-${sample.OriginalSampleID || 'N/A'}</td>
                <td>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-outline-primary">Detaljer</button>
                        <button class="btn btn-sm btn-outline-danger" onclick="disposeSample('${sample.TestSampleID}')">Kassér</button>
                    </div>
                </td>
            `;
            samplesTableEl.appendChild(row);
        });
    } else {
        samplesTableEl.innerHTML = '<tr><td colspan="4" class="text-center">Ingen prøver i denne test</td></tr>';
    }
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

// Initialiser funktioner når siden indlæses
document.addEventListener('DOMContentLoaded', function() {
    // Opdater velkomstbesked
    const activeTestsCount = document.querySelector('.active-tests-count');
    if (activeTestsCount) {
        updateWelcomeMessage(parseInt(activeTestsCount.textContent) || 0);
    }
});
