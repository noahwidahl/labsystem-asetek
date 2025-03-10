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
        }
    })
    .catch(error => {
        showErrorMessage(`Der opstod en fejl: ${error}`);
    });
}

// CompleteTest funktion
function completeTest(testId) {
    if (confirm(`Er du sikker på at du vil afslutte test ${testId}?`)) {
        fetch(`/api/completeTest/${testId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ testId: testId })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server svarede med status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                alert(`Test ${testId} er blevet afsluttet`);
                setTimeout(() => {
                    window.location.reload();
                }, 500);
            } else {
                alert(`Fejl ved afslutning af test: ${data.error}`);
            }
        })
        .catch(error => {
            console.error("Fejl ved afslutning af test:", error);
            alert(`Der opstod en fejl: ${error}`);
        });
    }
}

// ShowTestDetails funktion
function showTestDetails(testId) {
    fetch(`/api/testDetails/${testId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server svarede med status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data && data.test) {
                alert(`Test detaljer for: ${data.test.TestName}`);
                // Her kan vi tilføje kode til at vise en modal med detaljer
            } else {
                alert("Ingen testdata returneret");
            }
        })
        .catch(error => {
            console.error("Fejl ved hentning af testdetaljer:", error);
            alert(`Kunne ikke hente testdetaljer: ${error}`);
        });
}

// Funktion til at kassere alle prøver i en test
function disposeAllTestSamples(testId) {
    if (!testId) {
        alert("Fejl: Mangler test ID");
        return;
    }
    
    if (confirm(`Er du sikker på at du vil kassere ALLE prøver i test ${testId}?`)) {
        fetch('/api/disposeAllTestSamples', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ testId: testId })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server svarede med status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                alert(`Alle prøver i test ${testId} er kasseret!`);
                setTimeout(() => {
                    window.location.reload();
                }, 500);
            } else {
                alert(`Fejl ved kassation: ${data.error}`);
            }
        })
        .catch(error => {
            console.error("Fejl ved kassation:", error);
            alert(`Der opstod en fejl: ${error}`);
        });
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