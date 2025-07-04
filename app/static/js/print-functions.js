/**
 * Global Print Functions for Laboratory System
 * Handles printing of containers and samples across all pages
 */

// Global variables for print functionality
let globalCurrentPrintContainer = null;
let globalCurrentPrintSample = null;

// =============================================================================
// CONTAINER PRINT FUNCTIONS
// =============================================================================

/**
 * Show print prompt for new container creation
 */
function showContainerPrintPrompt(containerId, containerData) {
    console.log('🖨️ Container print prompt called with:', { containerId, containerData });
    
    // Store container info for printing
    globalCurrentPrintContainer = {
        id: containerId,
        data: containerData
    };
    
    // Create modal if it doesn't exist
    let modal = document.getElementById('containerPrintConfirmModal');
    if (!modal) {
        modal = createContainerPrintModal();
        document.body.appendChild(modal);
    }
    
    // Update modal content
    document.getElementById('printContainerId').textContent = `CNT-${containerId}`;
    document.getElementById('printContainerDescription').textContent = containerData?.description || 'Container';
    
    // Show modal
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

/**
 * Show print prompt for container updates (when samples are added/removed)
 */
function showContainerUpdatePrintPrompt(containerId, updateInfo) {
    console.log('🖨️ Container update print prompt called with:', { containerId, updateInfo });
    
    // Store container info for printing
    globalCurrentPrintContainer = {
        id: containerId,
        data: updateInfo
    };
    
    // Create modal if it doesn't exist
    let modal = document.getElementById('containerUpdatePrintModal');
    if (!modal) {
        modal = createContainerUpdatePrintModal();
        document.body.appendChild(modal);
    }
    
    // Update modal content
    document.getElementById('updateContainerId').textContent = `CNT-${containerId}`;
    document.getElementById('updateContainerAction').textContent = updateInfo?.action || 'Container updated';
    
    // Show modal
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

function createContainerPrintModal() {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'containerPrintConfirmModal';
    modal.tabIndex = -1;
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Print Container Label</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>Would you like to print the label for this container now?</p>
                    <div class="alert alert-info">
                        <strong>Container:</strong> <span id="printContainerId"></span><br>
                        <strong>Description:</strong> <span id="printContainerDescription"></span>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="skipContainerPrint()">
                        <i class="fas fa-times me-1"></i>Skip
                    </button>
                    <button type="button" class="btn btn-primary" onclick="printContainerNow()">
                        <i class="fas fa-print me-1"></i>Print Now
                    </button>
                </div>
            </div>
        </div>
    `;
    return modal;
}

function createContainerUpdatePrintModal() {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'containerUpdatePrintModal';
    modal.tabIndex = -1;
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Container Updated - Print Label?</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>Container has been updated. Would you like to print an updated label with current contents?</p>
                    <div class="alert alert-info">
                        <strong>Container:</strong> <span id="updateContainerId"></span><br>
                        <strong>Change:</strong> <span id="updateContainerAction"></span>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="skipContainerUpdatePrint()">
                        <i class="fas fa-times me-1"></i>Skip
                    </button>
                    <button type="button" class="btn btn-primary" onclick="printContainerUpdateNow()">
                        <i class="fas fa-print me-1"></i>Print Updated Label
                    </button>
                </div>
            </div>
        </div>
    `;
    return modal;
}

async function printContainerNow() {
    if (!globalCurrentPrintContainer) return;
    
    try {
        const response = await fetch(`/api/print/container/${globalCurrentPrintContainer.id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                auto_print: true
            })
        });
        
        const result = await response.json();
        
        // Add to print job queue regardless of result
        const containerData = {
            id: globalCurrentPrintContainer.id,
            description: globalCurrentPrintContainer.data?.description || `Container CNT-${globalCurrentPrintContainer.id}`,
            type: 'container'
        };
        
        let status = 'failed';
        if (result && result.status === 'success') {
            status = 'printed';
            showGlobalSuccessMessage('Container label printed successfully!');
        } else if (result && result.status === 'warning') {
            status = 'queued'; // Printer not available, but can retry later
            showGlobalSuccessMessage('Container label queued for printing.');
        } else {
            status = 'queued'; // Failed but can retry
            showGlobalSuccessMessage('Container label added to print queue.');
        }
        
        // Add to print job queue
        addContainerPrintJob(containerData, status);
        
        // Hide modal and reload page
        bootstrap.Modal.getInstance(document.getElementById('containerPrintConfirmModal')).hide();
        globalCurrentPrintContainer = null;
        
        // Reload page to show the new container
        setTimeout(() => {
            window.location.reload();
        }, 1000);
        
    } catch (error) {
        console.error('Print error:', error);
        
        // Add to print job queue as failed/queued
        const containerData = {
            id: globalCurrentPrintContainer.id,
            description: globalCurrentPrintContainer.data?.description || `Container CNT-${globalCurrentPrintContainer.id}`,
            type: 'container'
        };
        addContainerPrintJob(containerData, 'queued');
        
        showGlobalSuccessMessage('Container label added to print queue due to printer issues.');
        
        // Hide modal and reload page
        bootstrap.Modal.getInstance(document.getElementById('containerPrintConfirmModal')).hide();
        globalCurrentPrintContainer = null;
        
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }
}

async function printContainerUpdateNow() {
    if (!globalCurrentPrintContainer) return;
    
    try {
        const response = await fetch(`/api/print/container/${globalCurrentPrintContainer.id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                auto_print: true
            })
        });
        
        const result = await response.json();
        
        // Add to print job queue regardless of result
        const containerData = {
            id: globalCurrentPrintContainer.id,
            description: `Container CNT-${globalCurrentPrintContainer.id} (${globalCurrentPrintContainer.data?.action || 'Updated'})`,
            type: 'container'
        };
        
        let status = 'failed';
        if (result && result.status === 'success') {
            status = 'printed';
            showGlobalSuccessMessage('Container label printed successfully!');
        } else if (result && result.status === 'warning') {
            status = 'queued'; // Printer not available, but can retry later
            showGlobalSuccessMessage('Container label queued for printing.');
        } else {
            status = 'queued'; // Failed but can retry
            showGlobalSuccessMessage('Container label added to print queue.');
        }
        
        // Add to print job queue
        addContainerPrintJob(containerData, status);
        
        // Hide modal and reload page
        bootstrap.Modal.getInstance(document.getElementById('containerUpdatePrintModal')).hide();
        globalCurrentPrintContainer = null;
        
        // Reload page to show updated container
        setTimeout(() => {
            window.location.reload();
        }, 1000);
        
    } catch (error) {
        console.error('Print error:', error);
        
        // Add to print job queue as failed/queued
        const containerData = {
            id: globalCurrentPrintContainer.id,
            description: `Container CNT-${globalCurrentPrintContainer.id} (${globalCurrentPrintContainer.data?.action || 'Updated'})`,
            type: 'container'
        };
        addContainerPrintJob(containerData, 'queued');
        
        showGlobalSuccessMessage('Container label added to print queue due to printer issues.');
        
        // Hide modal and reload page
        bootstrap.Modal.getInstance(document.getElementById('containerUpdatePrintModal')).hide();
        globalCurrentPrintContainer = null;
        
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }
}

function skipContainerPrint() {
    // Add to print job queue when skipping
    if (globalCurrentPrintContainer) {
        const containerData = {
            id: globalCurrentPrintContainer.id,
            description: globalCurrentPrintContainer.data?.description || `Container CNT-${globalCurrentPrintContainer.id}`,
            type: 'container'
        };
        addContainerPrintJob(containerData, 'queued');
        showGlobalSuccessMessage('Container label added to print queue.');
    }
    
    // Hide modal and reload page
    bootstrap.Modal.getInstance(document.getElementById('containerPrintConfirmModal')).hide();
    globalCurrentPrintContainer = null;
    
    // Reload page to show the new container
    setTimeout(() => {
        window.location.reload();
    }, 1000);
}

function skipContainerUpdatePrint() {
    // Add to print job queue when skipping
    if (globalCurrentPrintContainer) {
        const containerData = {
            id: globalCurrentPrintContainer.id,
            description: `Container CNT-${globalCurrentPrintContainer.id} (${globalCurrentPrintContainer.data?.action || 'Updated'})`,
            type: 'container'
        };
        addContainerPrintJob(containerData, 'queued');
        showGlobalSuccessMessage('Container label added to print queue.');
    }
    
    // Hide modal and reload page
    bootstrap.Modal.getInstance(document.getElementById('containerUpdatePrintModal')).hide();
    globalCurrentPrintContainer = null;
    
    // Reload page to show updated container
    setTimeout(() => {
        window.location.reload();
    }, 1000);
}

// =============================================================================
// SAMPLE PRINT FUNCTIONS
// =============================================================================

/**
 * Show print prompt for sample location updates
 */
function showSampleLocationPrintPrompt(sampleId, updateInfo) {
    console.log('🖨️ Sample location print prompt called with:', { sampleId, updateInfo });
    
    // First fetch sample data
    fetch(`/api/samples/${sampleId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.sample) {
                const sampleData = data.sample;
                
                // Store sample info for printing
                globalCurrentPrintSample = {
                    id: sampleId,
                    data: sampleData,
                    updateInfo: updateInfo
                };
                
                // Create modal if it doesn't exist
                let modal = document.getElementById('sampleLocationPrintModal');
                if (!modal) {
                    modal = createSampleLocationPrintModal();
                    document.body.appendChild(modal);
                }
                
                // Update modal content
                document.getElementById('printMovedSampleId').textContent = sampleData.SampleIDFormatted || `SMP-${sampleId}`;
                document.getElementById('printMovedSampleBarcode').textContent = sampleData.Barcode || `SMP-${sampleId}`;
                document.getElementById('printMovedSampleAction').textContent = updateInfo?.action || 'Sample updated';
                
                // Show modal
                const bootstrapModal = new bootstrap.Modal(modal);
                bootstrapModal.show();
            } else {
                console.error('Failed to fetch sample data for print prompt');
                // Fallback - just reload page
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            }
        })
        .catch(error => {
            console.error('Error fetching sample data for print prompt:', error);
            // Fallback - just reload page
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        });
}

function createSampleLocationPrintModal() {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'sampleLocationPrintModal';
    modal.tabIndex = -1;
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Sample Updated - Print Label?</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>Sample has been updated. Would you like to print an updated label?</p>
                    <div class="alert alert-info">
                        <strong>Sample:</strong> <span id="printMovedSampleId"></span><br>
                        <strong>Barcode:</strong> <span id="printMovedSampleBarcode"></span><br>
                        <strong>Change:</strong> <span id="printMovedSampleAction"></span>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="skipSampleLocationPrint()">
                        <i class="fas fa-times me-1"></i>Skip
                    </button>
                    <button type="button" class="btn btn-primary" onclick="printSampleLocationNow()">
                        <i class="fas fa-print me-1"></i>Print Updated Label
                    </button>
                </div>
            </div>
        </div>
    `;
    return modal;
}

async function printSampleLocationNow() {
    if (!globalCurrentPrintSample) return;
    
    try {
        const response = await fetch(`/api/print/sample/${globalCurrentPrintSample.id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                auto_print: true
            })
        });
        
        const result = await response.json();
        
        // Add to print job queue regardless of result
        const sampleData = globalCurrentPrintSample.data;
        
        let status = 'failed';
        if (result && result.status === 'success') {
            status = 'printed';
            showGlobalSuccessMessage('Sample label printed successfully!');
        } else if (result && result.status === 'warning') {
            status = 'queued'; // Printer not available, but can retry later
            showGlobalSuccessMessage('Sample label queued for printing.');
        } else {
            status = 'queued'; // Failed but can retry
            showGlobalSuccessMessage('Sample label added to print queue.');
        }
        
        // Add to print job queue
        addSamplePrintJob(sampleData, status);
        
        // Hide modal and reload page
        bootstrap.Modal.getInstance(document.getElementById('sampleLocationPrintModal')).hide();
        globalCurrentPrintSample = null;
        
        // Reload page to show updated sample
        setTimeout(() => {
            window.location.reload();
        }, 1000);
        
    } catch (error) {
        console.error('Print error:', error);
        
        // Add to print job queue as failed/queued
        const sampleData = globalCurrentPrintSample.data;
        addSamplePrintJob(sampleData, 'queued');
        
        showGlobalSuccessMessage('Sample label added to print queue due to printer issues.');
        
        // Hide modal and reload page
        bootstrap.Modal.getInstance(document.getElementById('sampleLocationPrintModal')).hide();
        globalCurrentPrintSample = null;
        
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }
}

function skipSampleLocationPrint() {
    // Add to print job queue when skipping
    if (globalCurrentPrintSample) {
        const sampleData = globalCurrentPrintSample.data;
        addSamplePrintJob(sampleData, 'queued');
        showGlobalSuccessMessage('Sample label added to print queue.');
    }
    
    // Hide modal and reload page
    bootstrap.Modal.getInstance(document.getElementById('sampleLocationPrintModal')).hide();
    globalCurrentPrintSample = null;
    
    // Reload page to show updated sample
    setTimeout(() => {
        window.location.reload();
    }, 1000);
}

// =============================================================================
// TEST SAMPLE PRINT FUNCTIONS
// =============================================================================

/**
 * Show print prompt for test sample labels (when samples are moved to tests)
 */
function showTestSamplePrintPrompt(testSampleData) {
    console.log('🖨️ Test sample print prompt called with:', testSampleData);
    
    // Store test sample info for printing
    globalCurrentPrintSample = {
        id: testSampleData.SampleID,
        data: testSampleData,
        type: 'test_sample'
    };
    
    // Create modal if it doesn't exist
    let modal = document.getElementById('testSamplePrintModal');
    if (!modal) {
        modal = createTestSamplePrintModal();
        document.body.appendChild(modal);
    }
    
    // Update modal content
    document.getElementById('printTestSampleId').textContent = testSampleData.SampleIDFormatted || `SMP-${testSampleData.SampleID}`;
    document.getElementById('printTestBarcode').textContent = testSampleData.TestBarcode;
    document.getElementById('printTestName').textContent = testSampleData.TestName || 'Unknown Test';
    document.getElementById('printTestIdentifier').textContent = testSampleData.SampleIdentifier;
    
    // Show modal
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

function createTestSamplePrintModal() {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'testSamplePrintModal';
    modal.tabIndex = -1;
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Test Sample - Print Label?</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>Sample has been added to test. Would you like to print a test sample label?</p>
                    <div class="alert alert-info">
                        <strong>Sample:</strong> <span id="printTestSampleId"></span><br>
                        <strong>Test Barcode:</strong> <span id="printTestBarcode"></span><br>
                        <strong>Test:</strong> <span id="printTestName"></span><br>
                        <strong>Test ID:</strong> <span id="printTestIdentifier"></span>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="skipTestSamplePrint()">
                        <i class="fas fa-times me-1"></i>Skip
                    </button>
                    <button type="button" class="btn btn-primary" onclick="printTestSampleNow()">
                        <i class="fas fa-print me-1"></i>Print Test Label
                    </button>
                </div>
            </div>
        </div>
    `;
    return modal;
}

async function printTestSampleNow() {
    if (!globalCurrentPrintSample) return;
    
    try {
        const testSampleData = globalCurrentPrintSample.data;
        
        const response = await fetch('/api/print/test-sample', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                SampleID: testSampleData.SampleID,
                TestID: testSampleData.TestID,
                TestBarcode: testSampleData.TestBarcode,
                SampleIdentifier: testSampleData.SampleIdentifier,
                PartNumber: testSampleData.PartNumber,
                Description: testSampleData.Description,
                TestName: testSampleData.TestName,
                auto_print: true
            })
        });
        
        const result = await response.json();
        
        let status = 'failed';
        if (result && result.status === 'success') {
            status = 'printed';
            showGlobalSuccessMessage('Test sample label printed successfully!');
        } else if (result && result.status === 'warning') {
            status = 'queued'; // Printer not available, but can retry later
            showGlobalSuccessMessage('Test sample label queued for printing.');
        } else {
            status = 'queued'; // Failed but can retry
            showGlobalSuccessMessage('Test sample label added to print queue.');
        }
        
        // Add to print job queue
        addTestSamplePrintJob(testSampleData, status);
        
        // Hide modal and close without reload (we're in scanner context)
        bootstrap.Modal.getInstance(document.getElementById('testSamplePrintModal')).hide();
        globalCurrentPrintSample = null;
        
    } catch (error) {
        console.error('Test sample print error:', error);
        
        // Add to print job queue as failed/queued
        const testSampleData = globalCurrentPrintSample.data;
        addTestSamplePrintJob(testSampleData, 'queued');
        
        showGlobalSuccessMessage('Test sample label added to print queue due to printer issues.');
        
        // Hide modal
        bootstrap.Modal.getInstance(document.getElementById('testSamplePrintModal')).hide();
        globalCurrentPrintSample = null;
    }
}

function skipTestSamplePrint() {
    // Add to print job queue when skipping
    if (globalCurrentPrintSample) {
        const testSampleData = globalCurrentPrintSample.data;
        addTestSamplePrintJob(testSampleData, 'queued');
        showGlobalSuccessMessage('Test sample label added to print queue.');
    }
    
    // Hide modal
    bootstrap.Modal.getInstance(document.getElementById('testSamplePrintModal')).hide();
    globalCurrentPrintSample = null;
}

// =============================================================================
// PRINT QUEUE FUNCTIONS
// =============================================================================

/**
 * Add container print job to queue
 */
function addContainerPrintJob(containerData, status) {
    try {
        let printJobs = JSON.parse(localStorage.getItem('printJobs') || '[]');
        
        const printJob = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            containerId: containerData.id,
            containerIdFormatted: `CNT-${containerData.id}`,
            // For compatibility with scanner page - use container data as sample data
            sampleId: containerData.id,
            sampleIdFormatted: `CNT-${containerData.id}`,
            barcode: `CNT-${containerData.id}`,
            description: containerData.description,
            type: 'container',
            status: status // 'queued', 'printed', 'failed'
        };
        
        printJobs.unshift(printJob); // Add to beginning
        
        // Keep only last 50 jobs
        if (printJobs.length > 50) {
            printJobs = printJobs.slice(0, 50);
        }
        
        localStorage.setItem('printJobs', JSON.stringify(printJobs));
        console.log('✅ Container print job added to queue:', printJob);
        
    } catch (error) {
        console.error('❌ Error adding container print job to queue:', error);
    }
}

/**
 * Add sample print job to queue
 */
function addSamplePrintJob(sampleData, status) {
    try {
        let printJobs = JSON.parse(localStorage.getItem('printJobs') || '[]');
        
        const printJob = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            sampleId: sampleData.SampleID,
            sampleIdFormatted: sampleData.SampleIDFormatted || `SMP-${sampleData.SampleID}`,
            barcode: sampleData.Barcode || `SMP-${sampleData.SampleID}`,
            description: sampleData.Description || `Sample ${sampleData.SampleID}`,
            type: 'sample',
            status: status // 'queued', 'printed', 'failed'
        };
        
        printJobs.unshift(printJob); // Add to beginning
        
        // Keep only last 50 jobs
        if (printJobs.length > 50) {
            printJobs = printJobs.slice(0, 50);
        }
        
        localStorage.setItem('printJobs', JSON.stringify(printJobs));
        console.log('✅ Sample print job added to queue:', printJob);
        
    } catch (error) {
        console.error('❌ Error adding sample print job to queue:', error);
    }
}

/**
 * Add test sample print job to queue
 */
function addTestSamplePrintJob(testSampleData, status) {
    try {
        let printJobs = JSON.parse(localStorage.getItem('printJobs') || '[]');
        
        const printJob = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            sampleId: testSampleData.SampleID,
            sampleIdFormatted: testSampleData.SampleIDFormatted || `SMP-${testSampleData.SampleID}`,
            barcode: testSampleData.TestBarcode || `TST${testSampleData.SampleID}`,
            description: `Test Sample: ${testSampleData.Description || ''} (${testSampleData.TestName || 'Test'})`,
            type: 'test_sample',
            testId: testSampleData.TestID,
            testIdentifier: testSampleData.SampleIdentifier,
            status: status // 'queued', 'printed', 'failed'
        };
        
        printJobs.unshift(printJob); // Add to beginning
        
        // Keep only last 50 jobs
        if (printJobs.length > 50) {
            printJobs = printJobs.slice(0, 50);
        }
        
        localStorage.setItem('printJobs', JSON.stringify(printJobs));
        console.log('✅ Test sample print job added to queue:', printJob);
        
    } catch (error) {
        console.error('❌ Error adding test sample print job to queue:', error);
    }
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Show global success message
 */
function showGlobalSuccessMessage(message) {
    // Try different success message functions depending on what's available
    if (typeof showSuccessMessage === 'function') {
        showSuccessMessage(message);
    } else if (typeof showAlert === 'function') {
        showAlert('success', message);
    } else {
        // Fallback to simple alert
        console.log('✅ SUCCESS:', message);
        // Create a simple toast notification
        const toast = document.createElement('div');
        toast.className = 'alert alert-success position-fixed';
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `${message} <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>`;
        document.body.appendChild(toast);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 3000);
    }
}

// =============================================================================
// GLOBAL EXPORTS
// =============================================================================

// Make all functions globally available
window.showContainerPrintPrompt = showContainerPrintPrompt;
window.showContainerUpdatePrintPrompt = showContainerUpdatePrintPrompt;
window.showSampleLocationPrintPrompt = showSampleLocationPrintPrompt;
window.showTestSamplePrintPrompt = showTestSamplePrintPrompt;
window.addContainerPrintJob = addContainerPrintJob;
window.addSamplePrintJob = addSamplePrintJob;
window.addTestSamplePrintJob = addTestSamplePrintJob;
window.showGlobalSuccessMessage = showGlobalSuccessMessage;

// Print modal functions
window.printContainerNow = printContainerNow;
window.printContainerUpdateNow = printContainerUpdateNow;
window.skipContainerPrint = skipContainerPrint;
window.skipContainerUpdatePrint = skipContainerUpdatePrint;
window.printSampleLocationNow = printSampleLocationNow;
window.skipSampleLocationPrint = skipSampleLocationPrint;
window.printTestSampleNow = printTestSampleNow;
window.skipTestSamplePrint = skipTestSamplePrint;

console.log('🖨️ Global print functions loaded successfully!');