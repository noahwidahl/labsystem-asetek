/**
 * Register Print - Handles the print step (step 5) in registration process
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Print module loading...');
    
    // Setup print step handlers
    setupPrintStep();
    
    // Mark this module as loaded in the global state
    if (window.registerApp) {
        window.registerApp.modulesLoaded.print = true;
        console.log('Print module loaded');
    } else {
        console.error('registerApp not found - print module cannot register');
    }
});

function setupPrintStep() {
    // Handle print now button
    const printNowBtn = document.getElementById('printNowBtn');
    if (printNowBtn) {
        printNowBtn.addEventListener('click', function() {
            handlePrintNow();
        });
    }
    
    // Handle skip print button
    const skipPrintBtn = document.getElementById('skipPrintBtn');
    if (skipPrintBtn) {
        skipPrintBtn.addEventListener('click', function() {
            handleSkipPrint();
        });
    }
}

// Global function to populate print step with sample data
window.populatePrintStep = function(sampleData) {
    console.log('Populating print step with sample data:', sampleData);
    
    // Update the sample details in print step
    document.getElementById('print-sample-id').textContent = sampleData.SampleIDFormatted || 'N/A';
    document.getElementById('print-description').textContent = sampleData.Description || 'N/A';
    document.getElementById('print-barcode').textContent = sampleData.Barcode || 'N/A';
    document.getElementById('print-amount').textContent = `${sampleData.Amount || 0} ${sampleData.UnitName || 'pcs'}`;
    document.getElementById('print-location').textContent = registerApp.selectedLocationName || 'N/A';
    // Handle multiple serial numbers
    let serialDisplay = 'None';
    if (sampleData.SerialNumbers && sampleData.SerialNumbers.length > 0) {
        serialDisplay = sampleData.SerialNumbers.join(', ');
    }
    document.getElementById('print-serial').textContent = serialDisplay;
    
    // Store sample data for later use
    window.currentSampleData = sampleData;
};

function handlePrintNow() {
    console.log('Print now clicked');
    
    const printStatus = document.getElementById('printStatus');
    printStatus.classList.remove('d-none');
    printStatus.innerHTML = `
        <div class="alert alert-info">
            <i class="fas fa-spinner fa-spin me-2"></i>
            Sending to printer...
        </div>
    `;
    
    // Use the sample data stored when we populated the print step
    const sampleData = window.currentSampleData;
    if (!sampleData) {
        printStatus.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Error: Sample data not available for printing
            </div>
        `;
        return;
    }
    
    // Call the backend print API
    fetch(`/api/print/sample/${sampleData.SampleID}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(sampleData)
    })
    .then(response => response.json())
    .then(printResult => {
        // Add to print job queue regardless of result
        const sampleData = window.currentSampleData;
        if (sampleData) {
            let status = 'failed';
            if (printResult && printResult.status === 'success') {
                status = 'printed';
            } else if (printResult && printResult.status === 'warning') {
                status = 'queued'; // Printer not available, but can retry later
            }
            
            // Add to print job queue
            if (typeof window.addPrintJob === 'function') {
                console.log('Adding print result to job queue:', sampleData, status);
                window.addPrintJob(sampleData, status);
            } else {
                // Store in localStorage for scanner page to pick up
                let queuedJobs = JSON.parse(localStorage.getItem('printJobs') || '[]');
                
                const printJob = {
                    id: Date.now(),
                    timestamp: new Date().toISOString(),
                    sampleId: sampleData.SampleID,
                    sampleIdFormatted: sampleData.SampleIDFormatted || `SMP-${sampleData.SampleID}`,
                    barcode: sampleData.Barcode,
                    description: sampleData.Description,
                    status: status
                };
                
                queuedJobs.unshift(printJob);
                
                // Keep only last 50 jobs
                if (queuedJobs.length > 50) {
                    queuedJobs = queuedJobs.slice(0, 50);
                }
                
                localStorage.setItem('printJobs', JSON.stringify(queuedJobs));
                console.log('Print job added to queue:', printJob);
            }
        }
        
        // Show result to user
        if (printResult && printResult.status === 'success') {
            printStatus.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check me-2"></i>
                    Label sent to printer successfully!
                </div>
            `;
        } else if (printResult && printResult.status === 'warning') {
            printStatus.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${printResult.message || 'Print job queued. Please check printer configuration.'}
                </div>
            `;
        } else {
            printStatus.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${printResult?.message || 'Print job failed. Added to queue for retry.'}
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('Print error:', error);
        printStatus.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Print error: ${error.message || 'Network error'}
            </div>
        `;
    });
    
    // After 3 seconds, finish the registration process
    setTimeout(function() {
        finishRegistration();
    }, 3000);
}

function handleSkipPrint() {
    console.log('Skip print clicked');
    
    const printStatus = document.getElementById('printStatus');
    printStatus.classList.remove('d-none');
    printStatus.innerHTML = `
        <div class="alert alert-info">
            <i class="fas fa-info-circle me-2"></i>
            Print skipped. Label added to print queue for later printing.
        </div>
    `;
    
    // Add sample to print job queue on scanner page
    const sampleData = window.currentSampleData;
    if (sampleData) {
        // Call the addPrintJob function if it exists (from scanner page)
        if (typeof window.addPrintJob === 'function') {
            console.log('Adding sample to print job queue:', sampleData);
            window.addPrintJob(sampleData, 'queued');
        } else {
            // Store in localStorage for scanner page to pick up
            console.log('addPrintJob not available, storing in localStorage');
            let queuedJobs = JSON.parse(localStorage.getItem('printJobs') || '[]');
            
            const printJob = {
                id: Date.now(),
                timestamp: new Date().toISOString(),
                sampleId: sampleData.SampleID,
                sampleIdFormatted: sampleData.SampleIDFormatted || `SMP-${sampleData.SampleID}`,
                barcode: sampleData.Barcode,
                description: sampleData.Description,
                status: 'queued'
            };
            
            queuedJobs.unshift(printJob);
            
            // Keep only last 50 jobs
            if (queuedJobs.length > 50) {
                queuedJobs = queuedJobs.slice(0, 50);
            }
            
            localStorage.setItem('printJobs', JSON.stringify(queuedJobs));
            console.log('Sample added to print queue:', printJob);
        }
    }
    
    // Finish registration immediately
    setTimeout(function() {
        finishRegistration();
    }, 1500);
}

function finishRegistration() {
    console.log('Finishing registration process');
    
    // Show success message (use stored message from registration)
    const successMessage = window.registrationSuccessMessage || 'Sample registration complete!';
    const printStatus = document.getElementById('printStatus');
    printStatus.innerHTML = `
        <div class="alert alert-success">
            <i class="fas fa-check me-2"></i>
            ${successMessage} Redirecting to dashboard...
        </div>
    `;
    
    // Clear the stored message
    window.registrationSuccessMessage = null;
    
    // Redirect to dashboard after 3 seconds
    setTimeout(function() {
        window.location.href = '/dashboard';
    }, 3000);
}