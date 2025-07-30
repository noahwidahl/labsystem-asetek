/**
 * Scanner and Printer integration functions for Lab System
 * 
 * HARDWARE CONFIGURATION:
 * ======================
 * 
 * Scanner: Zebra MC330M with DataWedge
 * - API Endpoint: POST /api/scanner/data
 * - DataWedge Configuration:
 *   - Intent Action: none
 *   - Intent Category: none  
 *   - Intent Delivery: HTTP POST
 *   - URL: http://SERVER_IP:5000/api/scanner/data
 *   - Headers: Content-Type=application/json
 *   - JSON Format: {"barcode": "%SCAN"}
 * 
 * Printer: Brother QL-810W Label Printer
 * - API Endpoints: 
 *   - Test: POST /api/print/test
 *   - Print: POST /api/print/label
 * - Supported Label Types: Sample labels, Container labels
 * 
 * API ENDPOINTS:
 * =============
 * - POST /api/scanner/data - Receive barcode from DataWedge
 * - POST /api/scanner/test - Manual barcode lookup
 * - POST /api/print/test - Print test label
 * - POST /api/print/label - Print sample/container label
 * - GET /api/system/info - Get server IP and configuration
 */

document.addEventListener('DOMContentLoaded', function() {
    // Focus on barcode input field for immediate scanning
    const barcodeInput = document.getElementById('manualBarcode');
    if (barcodeInput) {
        barcodeInput.focus();
    }
    
    // Manual scan button event
    const scanButton = document.getElementById('scanButton');
    if (scanButton) {
        scanButton.addEventListener('click', function() {
            const barcode = document.getElementById('manualBarcode').value.trim();
            if (barcode) {
                performScan(barcode);
            } else {
                updateScannerStatus('Indtast en stregkode først', 'warning');
            }
        });
    }
    
    // Barcode input field event
    const barcodeInput = document.getElementById('manualBarcode');
    if (barcodeInput) {
        barcodeInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const barcode = this.value.trim();
                if (barcode) {
                    performScan(barcode);
                } else {
                    updateScannerStatus('Indtast en stregkode først', 'warning');
                }
            }
        });
    }
    
    // Test print button event
    const printTestButton = document.getElementById('printTestButton');
    if (printTestButton) {
        printTestButton.addEventListener('click', function() {
            updatePrinterStatus('Sender testudskrivning...', 'info');
            
            fetch('/api/print/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    updatePrinterStatus('Testlabel udskrevet succesfuldt!', 'success');
                } else {
                    updatePrinterStatus(`Fejl: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Fejl ved printer test:', error);
                updatePrinterStatus('Fejl ved kommunikation med serveren', 'danger');
            });
        });
    }
    
    // Print sample label button event
    const printSampleButton = document.getElementById('printSampleButton');
    if (printSampleButton) {
        printSampleButton.addEventListener('click', function() {
            const sampleId = document.getElementById('sampleId').textContent;
            const sampleDesc = document.getElementById('sampleDescription').textContent;
            const sampleBarcode = document.getElementById('sampleBarcode').textContent;
            const samplePartNumber = document.getElementById('samplePartNumber').textContent;
            const sampleType = document.getElementById('sampleType').textContent;
            const sampleAmount = document.getElementById('sampleAmount').textContent;
            const sampleUnit = document.getElementById('sampleUnit').textContent;
            
            updatePrinterStatus('Sender udskrivningsanmodning...', 'info');
            
            fetch('/api/print/label', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    label_type: 'sample',
                    data: {
                        SampleIDFormatted: sampleId,
                        Description: sampleDesc,
                        Barcode: sampleBarcode,
                        PartNumber: samplePartNumber,
                        Type: sampleType,
                        Amount: sampleAmount,
                        UnitName: sampleUnit
                    }
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    updatePrinterStatus('Prøvelabel udskrevet succesfuldt!', 'success');
                } else {
                    updatePrinterStatus(`Fejl: ${data.message}`, 'danger');
                }
            })
            .catch(error => {
                console.error('Fejl ved udskrivning af prøvelabel:', error);
                updatePrinterStatus('Fejl ved kommunikation med serveren', 'danger');
            });
        });
    }
});

/**
 * Udfører scanning af en stregkode
 * @param {string} barcode - Stregkoden, der skal scannes
 */
function performScan(barcode) {
    updateScannerStatus('Scanner stregkode...', 'info');
    
    fetch('/api/scanner/test', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            barcode: barcode
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            const resultType = data.result_type || 'sample';
            const lookupType = data.lookup_type || 'barcode';
            
            // Display appropriate success message based on result type and lookup method
            let message = 'Stregkode fundet!';
            if (resultType === 'container') {
                message = 'Container fundet!';
            } else if (resultType === 'test_sample') {
                message = 'Test prøve fundet!';
            } else if (lookupType === 'serial_number') {
                message = 'Prøve fundet via serienummer!';
            }
            
            updateScannerStatus(message, 'success');
            displayScanResults(data);
            
            // Check if response includes print confirmation trigger
            if (data.show_print_confirmation && data.sample_data) {
                // Trigger print confirmation after a short delay
                setTimeout(() => {
                    if (typeof window.showPrintConfirmation === 'function') {
                        window.showPrintConfirmation(data.sample_data);
                    }
                }, 1000); // 1 second delay to allow success message to be seen
            }
        } else if (data.status === 'not_found') {
            updateScannerStatus(`Stregkode ikke fundet: ${barcode}`, 'warning');
            hideScanResults();
        } else {
            updateScannerStatus(`Fejl: ${data.message}`, 'danger');
            hideScanResults();
        }
    })
    .catch(error => {
        console.error('Fejl ved scanning:', error);
        updateScannerStatus('Fejl ved kommunikation med serveren', 'danger');
        hideScanResults();
    });
}

/**
 * Opdaterer status for scanneren
 * @param {string} message - Statusbesked
 * @param {string} type - Type af status (success, warning, danger, info)
 */
function updateScannerStatus(message, type) {
    const statusDiv = document.getElementById('scannerStatus');
    if (statusDiv) {
        const iconMap = {
            'success': 'fas fa-check-circle',
            'warning': 'fas fa-exclamation-triangle', 
            'danger': 'fas fa-exclamation-circle',
            'info': 'fas fa-info-circle'
        };
        const icon = iconMap[type] || 'fas fa-info-circle';
        statusDiv.innerHTML = `<i class="${icon}"></i> ${message}`;
        statusDiv.className = `alert alert-${type}`;
    }
}

/**
 * Opdaterer status for printeren
 * @param {string} message - Statusbesked
 * @param {string} type - Type af status (success, warning, danger, info)
 */
function updatePrinterStatus(message, type) {
    const statusDiv = document.getElementById('printerStatus');
    if (statusDiv) {
        const iconMap = {
            'success': 'fas fa-check-circle',
            'warning': 'fas fa-exclamation-triangle',
            'danger': 'fas fa-exclamation-circle', 
            'info': 'fas fa-info-circle',
            'secondary': 'fas fa-check-circle'
        };
        const icon = iconMap[type] || 'fas fa-check-circle';
        statusDiv.innerHTML = `<i class="${icon}"></i> ${message}`;
        statusDiv.className = `alert alert-${type} mb-0`;
    }
}

/**
 * Viser scanningsresultater på siden
 * @param {Object} data - Data fra scanner API
 */
function displayScanResults(data) {
    const resultType = data.result_type || 'sample';
    const result = data.sample || data.container || data.test_sample || {};
    
    // Clear previous results
    clearScanResults();
    
    if (resultType === 'sample') {
        displaySampleResults(result, data.lookup_type);
    } else if (resultType === 'container') {
        displayContainerResults(result);
    } else if (resultType === 'test_sample') {
        displayTestSampleResults(result);
    }
    
    document.getElementById('scanResults').classList.remove('d-none');
    document.getElementById('noResults').classList.add('d-none');
}

/**
 * Viser sample scanningsresultater
 * @param {Object} sample - Sample data
 * @param {string} lookupType - Type of lookup performed
 */
function displaySampleResults(sample, lookupType) {
    document.getElementById('sampleId').textContent = sample.SampleIDFormatted || '';
    document.getElementById('sampleDescription').textContent = sample.Description || '';
    document.getElementById('sampleBarcode').textContent = sample.Barcode || '';
    document.getElementById('samplePartNumber').textContent = sample.PartNumber || '';
    document.getElementById('sampleType').textContent = sample.Type || '';
    document.getElementById('sampleStatus').textContent = sample.Status || '';
    document.getElementById('sampleAmount').textContent = sample.Amount || '';
    document.getElementById('sampleUnit').textContent = sample.UnitName || '';
    document.getElementById('sampleLocation').textContent = sample.LocationName || '';
    document.getElementById('sampleTask').textContent = sample.TaskName || 'None';
    
    // Add lookup type indicator
    if (lookupType === 'serial_number') {
        const serialIndicator = document.createElement('div');
        serialIndicator.className = 'alert alert-info mt-2';
        serialIndicator.innerHTML = `<i class="fas fa-barcode"></i> Found by serial number: ${sample.SerialNumber}`;
        document.getElementById('scanResults').appendChild(serialIndicator);
    }
    
    // Update print button to include all sample data
    const printButton = document.getElementById('printSampleButton');
    if (printButton) {
        printButton.onclick = () => printSampleLabel(sample);
    }
}

/**
 * Viser container scanningsresultater
 * @param {Object} container - Container data
 */
function displayContainerResults(container) {
    // Modify the display to show container information
    const resultsDiv = document.getElementById('scanResults');
    resultsDiv.innerHTML = `
        <div class="alert alert-success">
            <h5><i class="fas fa-box"></i> Container Found</h5>
        </div>
        <div class="table-responsive">
            <table class="table table-sm table-striped">
                <tbody>
                    <tr>
                        <td><strong>Container ID:</strong></td>
                        <td>${container.ContainerIDFormatted || ''}</td>
                    </tr>
                    <tr>
                        <td><strong>Description:</strong></td>
                        <td>${container.Description || ''}</td>
                    </tr>
                    <tr>
                        <td><strong>Barcode:</strong></td>
                        <td class="font-monospace">${container.Barcode || ''}</td>
                    </tr>
                    <tr>
                        <td><strong>Type:</strong></td>
                        <td>${container.ContainerType || ''}</td>
                    </tr>
                    <tr>
                        <td><strong>Location:</strong></td>
                        <td>${container.LocationName || ''}</td>
                    </tr>
                    <tr>
                        <td><strong>Sample Count:</strong></td>
                        <td>${container.SampleCount || 0} samples</td>
                    </tr>
                    <tr>
                        <td><strong>Task:</strong></td>
                        <td>${container.TaskName || 'None'}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="d-grid gap-2 mt-3">
            <button class="btn btn-success btn-lg" onclick="printContainerLabel(${JSON.stringify(container).replace(/"/g, '&quot;')})">
                <i class="fas fa-print"></i> Print Container Label
            </button>
        </div>
    `;
}

/**
 * Viser test sample scanningsresultater
 * @param {Object} testSample - Test sample data
 */
function displayTestSampleResults(testSample) {
    const resultsDiv = document.getElementById('scanResults');
    resultsDiv.innerHTML = `
        <div class="alert alert-warning">
            <h5><i class="fas fa-flask"></i> Test Sample Found</h5>
        </div>
        <div class="table-responsive">
            <table class="table table-sm table-striped">
                <tbody>
                    <tr>
                        <td><strong>Test ID:</strong></td>
                        <td>${testSample.GeneratedIdentifier || ''}</td>
                    </tr>
                    <tr>
                        <td><strong>Test Number:</strong></td>
                        <td>${testSample.TestNo || ''}</td>
                    </tr>
                    <tr>
                        <td><strong>Test Name:</strong></td>
                        <td>${testSample.TestName || ''}</td>
                    </tr>
                    <tr>
                        <td><strong>Original Sample:</strong></td>
                        <td>SMP-${testSample.SampleID}</td>
                    </tr>
                    <tr>
                        <td><strong>Description:</strong></td>
                        <td>${testSample.SampleDescription || ''}</td>
                    </tr>
                    <tr>
                        <td><strong>Part Number:</strong></td>
                        <td>${testSample.PartNumber || ''}</td>
                    </tr>
                    <tr>
                        <td><strong>Status:</strong></td>
                        <td>${testSample.Status || ''}</td>
                    </tr>
                    <tr>
                        <td><strong>Location:</strong></td>
                        <td>${testSample.LocationName || ''}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="d-grid gap-2 mt-3">
            <button class="btn btn-info btn-lg" onclick="viewTestDetails(${testSample.TestID})">
                <i class="fas fa-eye"></i> View Test Details
            </button>
        </div>
    `;
}

/**
 * Rydder scanningsresultater
 */
function clearScanResults() {
    const resultsDiv = document.getElementById('scanResults');
    resultsDiv.innerHTML = `
        <div class="table-responsive">
            <table class="table table-sm table-striped">
                <tbody>
                    <tr>
                        <td><strong>ID:</strong></td>
                        <td id="sampleId"></td>
                    </tr>
                    <tr>
                        <td><strong>Beskrivelse:</strong></td>
                        <td id="sampleDescription"></td>
                    </tr>
                    <tr>
                        <td><strong>Stregkode:</strong></td>
                        <td id="sampleBarcode" class="font-monospace"></td>
                    </tr>
                    <tr>
                        <td><strong>Varenummer:</strong></td>
                        <td id="samplePartNumber"></td>
                    </tr>
                    <tr>
                        <td><strong>Type:</strong></td>
                        <td id="sampleType"></td>
                    </tr>
                    <tr>
                        <td><strong>Status:</strong></td>
                        <td id="sampleStatus"></td>
                    </tr>
                    <tr>
                        <td><strong>Mængde:</strong></td>
                        <td><span id="sampleAmount"></span> <span id="sampleUnit"></span></td>
                    </tr>
                    <tr>
                        <td><strong>Lokation:</strong></td>
                        <td id="sampleLocation"></td>
                    </tr>
                    <tr>
                        <td><strong>Task:</strong></td>
                        <td id="sampleTask"></td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div class="d-grid gap-2 mt-3">
            <button class="btn btn-success btn-lg" id="printSampleButton">
                <i class="fas fa-print"></i> Udskriv Prøve Label
            </button>
        </div>
    `;
}

/**
 * Print sample label with enhanced data
 * @param {Object} sample - Sample data to print
 */
function printSampleLabel(sample) {
    updatePrinterStatus('Sender udskrivningsanmodning...', 'info');
    
    fetch('/api/print/label', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            label_type: 'sample',
            data: sample
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updatePrinterStatus(data.message, 'success');
        } else {
            updatePrinterStatus(`Fejl: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Fejl ved udskrivning af prøvelabel:', error);
        updatePrinterStatus('Fejl ved kommunikation med serveren', 'danger');
    });
}

/**
 * Print container label
 * @param {Object} container - Container data to print
 */
function printContainerLabel(container) {
    updatePrinterStatus('Sender container label udskrivning...', 'info');
    
    fetch('/api/print/label', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            label_type: 'container',
            data: container
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updatePrinterStatus(data.message, 'success');
        } else {
            updatePrinterStatus(`Fejl: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Fejl ved udskrivning af container label:', error);
        updatePrinterStatus('Fejl ved kommunikation med serveren', 'danger');
    });
}

/**
 * View test details (placeholder - should integrate with existing test details functionality)
 * @param {number} testId - Test ID to view
 */
function viewTestDetails(testId) {
    // This should integrate with existing test management functionality
    alert(`View test details for Test ID: ${testId}\n\nThis would open the test details modal.`);
}

/**
 * Skjuler scanningsresultater på siden
 */
function hideScanResults() {
    document.getElementById('scanResults').classList.add('d-none');
    document.getElementById('noResults').classList.remove('d-none');
}

/**
 * Hook for sample registration completion to trigger print confirmation
 * This function is called when sample location is saved successfully
 */
function handleSampleRegistrationComplete(sampleData) {
    // Check if we're on scanner page and print confirmation is available
    if (typeof window.showPrintConfirmation === 'function') {
        // Show print confirmation dialog
        setTimeout(() => {
            window.showPrintConfirmation(sampleData);
        }, 500); // Small delay to allow registration success message to show
    }
}

// Make function globally available
window.handleSampleRegistrationComplete = handleSampleRegistrationComplete;