// app/static/js/container-management.js
document.addEventListener('DOMContentLoaded', function() {
    console.log('Container management initialized');
    
    // Debug info
    const containers = document.querySelectorAll('table tbody tr[data-container-id]');
    console.log(`Fandt ${containers.length} container rækker i DOM`);
    
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
    
    // Filter knapper
    setupFilterButtons();
    
    // Tilføj event listener til slet-knapper
    document.querySelectorAll('.delete-container-btn').forEach(button => {
        button.addEventListener('click', function() {
            const containerId = this.getAttribute('data-container-id');
            deleteContainer(containerId);
        });
    });
});

function setupFilterButtons() {
    const filterAll = document.getElementById('filterAll');
    const filterEmpty = document.getElementById('filterEmpty');
    const filterFull = document.getElementById('filterFull');
    
    if (!filterAll || !filterEmpty || !filterFull) return;
    
    // Alle containere
    filterAll.addEventListener('click', function() {
        resetButtonStates([filterAll, filterEmpty, filterFull]);
        this.classList.add('active');
        filterContainers('all');
    });
    
    // Tomme containere
    filterEmpty.addEventListener('click', function() {
        resetButtonStates([filterAll, filterEmpty, filterFull]);
        this.classList.add('active');
        filterContainers('empty');
    });
    
    // Fyldte containere
    filterFull.addEventListener('click', function() {
        resetButtonStates([filterAll, filterEmpty, filterFull]);
        this.classList.add('active');
        filterContainers('full');
    });
    
    // Standard: Vis alle
    filterAll.classList.add('active');
}

function resetButtonStates(buttons) {
    buttons.forEach(button => {
        button.classList.remove('active');
    });
}

function filterContainers(filter) {
    const rows = document.querySelectorAll('tbody tr');
    
    rows.forEach(row => {
        const sampleCount = row.querySelector('td:nth-child(5)');
        
        if (!sampleCount) {
            row.style.display = '';
            return;
        }
        
        const countText = sampleCount.textContent;
        // Find første tal i teksten (prøver X / enheder Y)
        const firstNumber = parseInt(countText.match(/\d+/) || [0]);
        
        if (filter === 'all') {
            row.style.display = '';
        } else if (filter === 'empty') {
            row.style.display = firstNumber === 0 ? '' : 'none';
        } else if (filter === 'full') {
            row.style.display = firstNumber > 0 ? '' : 'none';
        }
    });
}

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
    
    // Debug log
    console.log('Creating container with data:', {
        description,
        typeId: typeId || 'null',
        capacity: capacity || 'null',
        isMixed
    });
    
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
    .then(response => {
        console.log('Server response status:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('Server response data:', data);
        if (data.success) {
            showSuccessMessage('Container oprettet succesfuldt!');
            
            // Luk modal og genindlæs siden
            const modal = bootstrap.Modal.getInstance(document.getElementById('createContainerModal'));
            if (modal) modal.hide();
            
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showErrorMessage(`Fejl ved oprettelse: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error creating container:', error);
        showErrorMessage(`Der opstod en fejl: ${error}`);
    });
}

// Slet container
function deleteContainer(containerId) {
    if (confirm(`Er du sikker på at du vil slette container ${containerId}?`)) {
        console.log('Deleting container:', containerId);
        
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
            console.error('Error deleting container:', error);
            showErrorMessage(`Der opstod en fejl: ${error}`);
        });
    }
}

// Beskedfunktioner
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