/**
 * Scanner and Printer integration functions for Lab System
 */

document.addEventListener('DOMContentLoaded', function() {
    // Opdater server IP
    if (document.getElementById('serverIp')) {
        fetch('/api/system/info')
            .then(response => response.json())
            .then(data => {
                document.getElementById('serverIp').textContent = data.server_ip || 'Konfiguration nødvendig';
                if (document.getElementById('serverIpConfig')) {
                    document.getElementById('serverIpConfig').textContent = data.server_ip || 'SERVER_IP';
                }
            })
            .catch(error => {
                console.error('Fejl ved hentning af serverinfo:', error);
                document.getElementById('serverIp').textContent = 'Fejl ved hentning';
            });
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
            updateScannerStatus('Stregkode fundet!', 'success');
            displayScanResults(data.sample);
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
        statusDiv.textContent = message;
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
        statusDiv.textContent = message;
        statusDiv.className = `alert alert-${type}`;
    }
}

/**
 * Viser scanningsresultater på siden
 * @param {Object} sample - Prøveobjekt med data
 */
function displayScanResults(sample) {
    document.getElementById('sampleId').textContent = sample.SampleIDFormatted || '';
    document.getElementById('sampleDescription').textContent = sample.Description || '';
    document.getElementById('sampleBarcode').textContent = sample.Barcode || '';
    document.getElementById('samplePartNumber').textContent = sample.PartNumber || '';
    document.getElementById('sampleType').textContent = sample.Type || '';
    document.getElementById('sampleStatus').textContent = sample.Status || '';
    document.getElementById('sampleAmount').textContent = sample.Amount || '';
    document.getElementById('sampleUnit').textContent = sample.UnitName || '';
    document.getElementById('sampleLocation').textContent = sample.LocationName || '';
    
    document.getElementById('scanResults').classList.remove('d-none');
    document.getElementById('noResults').classList.add('d-none');
}

/**
 * Skjuler scanningsresultater på siden
 */
function hideScanResults() {
    document.getElementById('scanResults').classList.add('d-none');
    document.getElementById('noResults').classList.remove('d-none');
}