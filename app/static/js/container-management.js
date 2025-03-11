// app/static/js/container-management.js
document.addEventListener('DOMContentLoaded', function() {
    console.log('Container management initialized');
    
    // Søgefunktionalitet til containertabellen
    const searchInput = document.getElementById('containerSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const tableRows = document.querySelectorAll('tbody tr');
            
            tableRows.forEach(row => {
                const rowText = row.textContent.toLowerCase();
                row.style.display = rowText.includes(searchTerm) ? '' : 'none';
            });
        });
    }
});

// Opret ny container
function createContainer() {
    const description = document.getElementById('containerDescription').value;
    const typeId = document.getElementById('containerType').value;
    const capacity = document.getElementById('containerCapacity').value;
    const isMixed = document.getElementById('containerIsMixed').checked;
    
    // Validering
    if (!description) {
        showErrorMessage('Indtast venligst en beskrivelse for containeren');
        return;
    }
    
    // Opret container-objekt
    const containerData = {
        description: description,
        containerTypeId: typeId || null,
        capacity: capacity || null,
        isMixed: isMixed
    };
    
    // Send til server
    fetch('/api/containers', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(containerData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage('Container oprettet succesfuldt!');
            
            // Luk modal og genindlæs siden
            const modal = bootstrap.Modal.getInstance(document.getElementById('createContainerModal'));
            modal.hide();
            
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showErrorMessage(`Fejl ved oprettelse: ${data.error}`);
        }
    })
    .catch(error => {
        showErrorMessage(`Der opstod en fejl: ${error}`);
    });
}

// Slet container
function deleteContainer(containerId) {
    if (confirm(`Er du sikker på at du vil slette container ${containerId}?`)) {
        fetch(`/api/containers/${containerId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSuccessMessage('Container slettet succesfuldt!');
                
                // Fjern række fra tabellen
                const row = document.querySelector(`tr[data-container-id="${containerId}"]`);
                if (row) {
                    row.remove();
                } else {
                    // Genindlæs siden hvis rækken ikke findes
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                }
            } else {
                showErrorMessage(`Fejl ved sletning: ${data.error}`);
            }
        })
        .catch(error => {
            showErrorMessage(`Der opstod en fejl: ${error}`);
        });
    }
}

// Beskedfunktioner
function showSuccessMessage(message) {
    // Genbruger eksisterende beskedfunktion fra test-functions.js
    if (typeof window.showSuccessMessage === 'function') {
        window.showSuccessMessage(message);
    } else {
        alert(message);
    }
}

function showErrorMessage(message) {
    // Genbruger eksisterende beskedfunktion fra test-functions.js
    if (typeof window.showErrorMessage === 'function') {
        window.showErrorMessage(message);
    } else {
        alert('Fejl: ' + message);
    }
}

// Tilføj event listeners til slet-knapper
document.querySelectorAll('.delete-container-btn').forEach(button => {
    button.addEventListener('click', function() {
        const containerId = this.getAttribute('data-container-id');
        deleteContainer(containerId);
    });
});