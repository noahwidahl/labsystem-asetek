// app/static/js/container-details.js
document.addEventListener('DOMContentLoaded', function() {
    console.log('Container details initialized');
    
    // Initialiser sampleSelect med en søgefunktion
    setupSampleSelect();
});

function setupSampleSelect() {
    const sampleSelect = document.getElementById('sampleSelect');
    if (!sampleSelect) return;
    
    // Tilføj eventuelt en søgefunktion hvis der er mange prøver
    // Her kunne man bruge f.eks. select2 biblioteket
}

// Tilføj prøve til container
function addSampleToContainer() {
    const containerId = document.querySelector('[data-container-id]').getAttribute('data-container-id');
    const sampleId = document.getElementById('sampleSelect').value;
    const amount = parseInt(document.getElementById('sampleAmount').value) || 1;
    
    // Validering
    if (!sampleId) {
        showErrorMessage('Vælg venligst en prøve');
        return;
    }
    
    if (amount < 1) {
        showErrorMessage('Antal skal være mindst 1');
        return;
    }
    
    // Opret data-objekt
    const data = {
        containerId: containerId,
        sampleId: sampleId,
        amount: amount
    };
    
    // Send til server
    fetch('/api/containers/add-sample', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage('Prøve tilføjet til container!');
            
            // Luk modal og genindlæs siden
            const modal = bootstrap.Modal.getInstance(document.getElementById('addSampleToContainerModal'));
            modal.hide();
            
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showErrorMessage(`Fejl ved tilføjelse af prøve: ${data.error}`);
        }
    })
    .catch(error => {
        showErrorMessage(`Der opstod en fejl: ${error}`);
    });
}

// Fjern prøve fra container
function removeSampleFromContainer(containerId, sampleId, amount) {
    if (confirm('Er du sikker på at du vil fjerne denne prøve fra containeren?')) {
        // Opret data-objekt
        const data = {
            containerId: containerId,
            sampleId: sampleId,
            amount: amount
        };
        
        // Send til server
        fetch('/api/containers/remove-sample', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSuccessMessage('Prøve fjernet fra container!');
                
                // Genindlæs siden
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showErrorMessage(`Fejl ved fjernelse af prøve: ${data.error}`);
            }
        })
        .catch(error => {
            showErrorMessage(`Der opstod en fejl: ${error}`);
        });
    }
}

// Hjælpefunktioner til beskedvisning
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

// I container-details.js
document.querySelectorAll('.remove-sample-btn').forEach(button => {
    button.addEventListener('click', function() {
        const containerId = this.getAttribute('data-container-id');
        const sampleId = this.getAttribute('data-sample-id');
        removeSampleFromContainer(containerId, sampleId);
    });
});

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