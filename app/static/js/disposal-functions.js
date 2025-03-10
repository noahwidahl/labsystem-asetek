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

// Opdater max antal baseret på valgt prøve
function updateDisposalAmount() {
    const sampleSelect = document.getElementById('sampleSelect');
    const disposalAmount = document.getElementById('disposalAmount');
    
    if (!sampleSelect || !disposalAmount) return;
    
    // Hvis ingen prøve er valgt, deaktiver antal-feltet
    if (!sampleSelect.value) {
        disposalAmount.disabled = true;
        disposalAmount.value = '';
        return;
    }
    
    // Aktiver antal-feltet
    disposalAmount.disabled = false;
    
    // Find den valgte prøve fra dropdown-teksten
    const selectedOption = sampleSelect.options[sampleSelect.selectedIndex];
    const optionText = selectedOption.textContent;
    
    // Forsøg at udtrække det maksimale antal fra teksten med regex
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

// Funktion til at kassere en testprøve
function disposeSample(testSampleId) {
    if (confirm("Er du sikker på at du vil kassere denne prøve?")) {
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
                showSuccessMessage("Prøve er kasseret succesfuldt!");
                
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
}

// Kassér alle prøver på én gang
function disposeAllTestSamples(testId) {
    if (confirm(`Er du sikker på at du vil kassere ALLE prøver i test ${testId}?`)) {
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
            showErrorMessage(`Der opstod en fejl: ${error}`);
        });
    }
}

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