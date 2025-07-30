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
    document.getElementById('print-location').textContent = sampleData.LocationName || 'N/A';
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
    
    // Check if sample was created with containers - if so, print container labels instead
    const containerIds = window.registrationContainerIds;
    if (containerIds && containerIds.length > 0) {
        console.log('Sample was created with containers, printing container labels:', containerIds);
        
        // Print container labels instead of sample labels
        printContainerLabels(containerIds, printStatus);
    } else {
        console.log('Sample was created without containers, printing sample label');
        
        // Call the backend print API for sample
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
}

function printContainerLabels(containerIds, printStatus) {
    console.log('Printing container labels for containers:', containerIds);
    
    let printPromises = [];
    let printResults = [];
    
    // Print all containers
    for (let containerId of containerIds) {
        const printPromise = fetch(`/api/print/container/${containerId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ auto_print: true })
        })
        .then(response => response.json())
        .then(result => {
            printResults.push({
                containerId: containerId,
                result: result
            });
            return result;
        })
        .catch(error => {
            console.error(`Error printing container ${containerId}:`, error);
            printResults.push({
                containerId: containerId,
                result: { status: 'error', message: error.message }
            });
            return { status: 'error', message: error.message };
        });
        
        printPromises.push(printPromise);
    }
    
    // Wait for all print jobs to complete
    Promise.all(printPromises).then(results => {
        // Count successful prints
        const successCount = results.filter(r => r.status === 'success').length;
        const totalCount = results.length;
        
        // Add container print jobs to queue
        printResults.forEach(({ containerId, result }) => {
            let status = 'failed';
            if (result && result.status === 'success') {
                status = 'printed';
            } else if (result && result.status === 'warning') {
                status = 'queued';
            }
            
            // Add to print job queue
            if (typeof window.addPrintJob === 'function') {
                const containerData = {
                    type: 'container',
                    ContainerID: containerId,
                    ContainerIDFormatted: `CNT-${containerId}`,
                    Barcode: `CNT-${containerId}`,
                    Description: `Container ${containerId}`
                };
                console.log('Adding container print result to job queue:', containerData, status);
                window.addPrintJob(containerData, status);
            } else {
                // Store in localStorage for scanner page to pick up
                let queuedJobs = JSON.parse(localStorage.getItem('printJobs') || '[]');
                
                const printJob = {
                    id: Date.now() + containerId, // Make unique ID
                    timestamp: new Date().toISOString(),
                    containerId: containerId,
                    sampleIdFormatted: `CNT-${containerId}`,
                    barcode: `CNT-${containerId}`,
                    description: `Container ${containerId}`,
                    status: status,
                    type: 'container'
                };
                
                queuedJobs.unshift(printJob);
                
                // Keep only last 50 jobs
                if (queuedJobs.length > 50) {
                    queuedJobs = queuedJobs.slice(0, 50);
                }
                
                localStorage.setItem('printJobs', JSON.stringify(queuedJobs));
                console.log('Container print job added to queue:', printJob);
            }
        });
        
        // Show result to user
        if (successCount === totalCount) {
            printStatus.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check me-2"></i>
                    All ${totalCount} container label(s) sent to printer successfully!
                </div>
            `;
        } else if (successCount > 0) {
            printStatus.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${successCount} of ${totalCount} container labels printed successfully. Check print queue for failed jobs.
                </div>
            `;
        } else {
            printStatus.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Container label printing failed. Labels added to queue for retry.
                </div>
            `;
        }
        
        // After 3 seconds, finish the registration process
        setTimeout(function() {
            finishRegistration();
        }, 3000);
    });
}

function handleSkipPrint() {
    console.log('Skip print clicked');
    
    const printStatus = document.getElementById('printStatus');
    printStatus.classList.remove('d-none');
    printStatus.innerHTML = `
        <div class="alert alert-info">
            <i class="fas fa-info-circle me-2"></i>
            Print skipped. Label(s) added to print queue for later printing.
        </div>
    `;
    
    // Check if sample was created with containers - if so, add container labels to queue
    const containerIds = window.registrationContainerIds;
    if (containerIds && containerIds.length > 0) {
        console.log('Sample was created with containers, adding container labels to queue:', containerIds);
        
        // Add container labels to print queue
        containerIds.forEach(containerId => {
            if (typeof window.addPrintJob === 'function') {
                const containerData = {
                    type: 'container',
                    ContainerID: containerId,
                    ContainerIDFormatted: `CNT-${containerId}`,
                    Barcode: `CNT-${containerId}`,
                    Description: `Container ${containerId}`
                };
                console.log('Adding container to print job queue:', containerData);
                window.addPrintJob(containerData, 'queued');
            } else {
                // Store in localStorage for scanner page to pick up
                let queuedJobs = JSON.parse(localStorage.getItem('printJobs') || '[]');
                
                const printJob = {
                    id: Date.now() + containerId, // Make unique ID
                    timestamp: new Date().toISOString(),
                    containerId: containerId,
                    sampleIdFormatted: `CNT-${containerId}`,
                    barcode: `CNT-${containerId}`,
                    description: `Container ${containerId}`,
                    status: 'queued',
                    type: 'container'
                };
                
                queuedJobs.unshift(printJob);
                
                // Keep only last 50 jobs
                if (queuedJobs.length > 50) {
                    queuedJobs = queuedJobs.slice(0, 50);
                }
                
                localStorage.setItem('printJobs', JSON.stringify(queuedJobs));
                console.log('Container added to print queue:', printJob);
            }
        });
    } else {
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