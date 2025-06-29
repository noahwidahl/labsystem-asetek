// app/static/js/sample-details.js
document.addEventListener('DOMContentLoaded', function() {
    console.log('Sample details initialized');
    
    // Add event listeners for sample detail buttons
    setupSampleDetailButtons();
    
    // The move button event listener is now handled by move-sample.js
});

function setupSampleDetailButtons() {
    // Add event listener for the "Details" button on sample rows
    document.querySelectorAll('button.sample-details-btn').forEach(button => {
        button.addEventListener('click', function() {
            const sampleId = this.dataset.sampleId;
            if (sampleId) {
                loadSampleDetails(sampleId);
                const modal = new bootstrap.Modal(document.getElementById('sampleDetailsModal'));
                modal.show();
            }
        });
    });
}

// Make the function globally available
window.loadSampleDetails = function(sampleId) {
    // Clear previous content
    document.getElementById('sample-id').textContent = '-';
    document.getElementById('sample-barcode').textContent = '-';
    document.getElementById('sample-description').textContent = '-';
    document.getElementById('sample-part-number').textContent = '-';
    document.getElementById('sample-amount').textContent = '-';
    document.getElementById('sample-status').textContent = '-';
    document.getElementById('sample-registered-date').textContent = '-';
    document.getElementById('sample-registered-by').textContent = '-';
    document.getElementById('sample-location').textContent = '-';
    document.getElementById('sample-container').textContent = '-';
    document.getElementById('sample-tracking-number').textContent = '-';
    document.getElementById('sample-supplier').textContent = '-';
    document.getElementById('sample-units').textContent = '-';
    document.getElementById('sample-serial-numbers').textContent = '-';
    document.getElementById('sample-comments').textContent = '-';
    document.getElementById('sample-properties').innerHTML = '<p class="text-center text-muted">Loading properties...</p>';
    document.getElementById('sample-history-list').innerHTML = '<p class="text-center text-muted">Loading history...</p>';
    
    // Set the modal title
    document.getElementById('sampleDetailsModalLabel').textContent = `Sample ${sampleId} Details`;
    
    // Fetch sample details
    fetch(`/api/samples/${sampleId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.sample) {
                const sample = data.sample;
                
                // Update sample basic information
                // Handle and display sample data safely
                document.getElementById('sample-id').textContent = sample.SampleID ? `SMP-${sample.SampleID}` : `SMP-${sampleId}`;
                document.getElementById('sample-barcode').textContent = sample.Barcode || '-';
                document.getElementById('sample-description').textContent = sample.Description || '-';
                document.getElementById('sample-part-number').textContent = sample.PartNumber || '-';
                
                // Make sure amount is displayed correctly with unit
                let displayAmount = '-';
                if (sample.Amount !== null && sample.Amount !== undefined) {
                    // Try to format the amount, handle both string and number
                    try {
                        const amount = parseFloat(sample.Amount);
                        displayAmount = `${amount} ${sample.Unit || 'pcs'}`;
                    } catch (e) {
                        displayAmount = `${String(sample.Amount)} ${sample.Unit || 'pcs'}`;
                    }
                }
                document.getElementById('sample-amount').textContent = displayAmount;
                document.getElementById('sample-status').innerHTML = `<span class="badge ${sample.Status === 'Disposed' ? 'bg-danger' : 'bg-primary'}">${sample.Status || 'Active'}</span>`;
                document.getElementById('sample-registered-date').textContent = sample.RegisteredDate || '-';
                document.getElementById('sample-registered-by').textContent = sample.RegisteredBy || '-';
                
                // Update storage information
                document.getElementById('sample-location').textContent = sample.Location || '-';
                document.getElementById('sample-container').textContent = sample.ContainerID ? `Container ${sample.ContainerID}` : 'None';
                document.getElementById('sample-tracking-number').textContent = sample.TrackingNumber || '-';
                document.getElementById('sample-supplier').textContent = sample.SupplierName || '-';
                document.getElementById('sample-units').textContent = sample.Unit || '-';
                
                // Update serial numbers - handle multiple serial numbers
                let serialNumbersDisplay = 'No serial numbers';
                if (data.serial_numbers && data.serial_numbers.length > 0) {
                    serialNumbersDisplay = data.serial_numbers.join(', ');
                }
                document.getElementById('sample-serial-numbers').textContent = serialNumbersDisplay;
                
                // Update comments
                document.getElementById('sample-comments').textContent = sample.Comments || 'No comments';
                
                // Display properties
                if (data.properties && data.properties.length > 0) {
                    let propertiesHtml = '<div class="row">';
                    data.properties.forEach(prop => {
                        propertiesHtml += `
                            <div class="col-md-6 mb-2">
                                <div class="d-flex justify-content-between">
                                    <strong>${prop.PropertyName || 'Property'}:</strong>
                                    <span>${prop.PropertyValue || '-'}</span>
                                </div>
                            </div>
                        `;
                    });
                    propertiesHtml += '</div>';
                    document.getElementById('sample-properties').innerHTML = propertiesHtml;
                } else {
                    document.getElementById('sample-properties').innerHTML = 
                        '<p class="text-center text-muted">No properties for this sample</p>';
                }
                
                // Display history
                if (data.history && data.history.length > 0) {
                    let historyHtml = `
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead>
                                    <tr>
                                        <th>Date</th>
                                        <th>Action</th>
                                        <th>User</th>
                                        <th>Notes</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;
                    data.history.forEach(item => {
                        historyHtml += `
                            <tr>
                                <td>${item.Timestamp || '-'}</td>
                                <td>${item.ActionType || '-'}</td>
                                <td>${item.UserName || '-'}</td>
                                <td>${item.Notes || '-'}</td>
                            </tr>
                        `;
                    });
                    historyHtml += '</tbody></table></div>';
                    document.getElementById('sample-history-list').innerHTML = historyHtml;
                } else {
                    document.getElementById('sample-history-list').innerHTML = 
                        '<p class="text-center text-muted">No history found for this sample</p>';
                }
            } else {
                showErrorMessage(data.error || 'Error loading sample details');
            }
        })
        .catch(error => {
            console.error('Error fetching sample details:', error);
            showErrorMessage('An error occurred while loading sample details');
        });
}

// Helper functions for message display - copied from container-details.js for consistency
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