/**
 * Zebra Scanner Integration for LabSystem
 * Handles both manual input and automatic scanner integration
 */

class ZebraScanner {
    constructor() {
        this.scannerInput = null;
        this.lastScanTime = 0;
        this.scanBuffer = '';
        this.init();
    }

    init() {
        // Create hidden input for scanner data
        this.createScannerInput();
        
        // Listen for barcode scans
        this.setupScanListener();
        
        // Add manual test interface
        this.createTestInterface();
    }

    createScannerInput() {
        // Create hidden input that captures scanner data
        this.scannerInput = document.createElement('input');
        this.scannerInput.id = 'zebra-scanner-input';
        this.scannerInput.style.position = 'absolute';
        this.scannerInput.style.left = '-9999px';
        this.scannerInput.style.opacity = '0';
        this.scannerInput.setAttribute('autocomplete', 'off');
        
        document.body.appendChild(this.scannerInput);
        
        // Keep input focused for scanner data
        this.scannerInput.focus();
        
        // Refocus if lost
        document.addEventListener('click', () => {
            setTimeout(() => this.scannerInput.focus(), 100);
        });
    }

    setupScanListener() {
        let scanTimeout;
        
        this.scannerInput.addEventListener('input', (e) => {
            const currentTime = Date.now();
            const inputValue = e.target.value;
            
            // Clear previous timeout
            clearTimeout(scanTimeout);
            
            // If this is a rapid input (typical of scanner), accumulate
            if (currentTime - this.lastScanTime < 100) {
                this.scanBuffer += inputValue;
            } else {
                this.scanBuffer = inputValue;
            }
            
            this.lastScanTime = currentTime;
            
            // Wait for end of scan (50ms after last input)
            scanTimeout = setTimeout(() => {
                if (this.scanBuffer.trim().length > 0) {
                    this.processScan(this.scanBuffer.trim());
                    this.scanBuffer = '';
                    e.target.value = '';
                }
            }, 50);
        });

        // Handle Enter key (common scanner suffix)
        this.scannerInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                clearTimeout(scanTimeout);
                if (this.scanBuffer.trim().length > 0) {
                    this.processScan(this.scanBuffer.trim());
                    this.scanBuffer = '';
                    e.target.value = '';
                }
            }
        });
    }

    createTestInterface() {
        // Create test panel for manual barcode entry
        const testPanel = document.createElement('div');
        testPanel.innerHTML = `
            <div id="scanner-test-panel" style="
                position: fixed;
                top: 10px;
                right: 10px;
                background: white;
                border: 2px solid #007bff;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                z-index: 1000;
                font-family: Arial, sans-serif;
                max-width: 300px;
            ">
                <h4 style="margin: 0 0 10px 0; color: #007bff;">🔍 Scanner Test</h4>
                <input type="text" id="manual-barcode" placeholder="Enter barcode to test" style="
                    width: 100%;
                    padding: 8px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    margin-bottom: 10px;
                    font-size: 14px;
                ">
                <button id="test-scan-btn" style="
                    width: 100%;
                    padding: 8px;
                    background: #007bff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 14px;
                ">Test Scan</button>
                <div id="scan-result" style="
                    margin-top: 10px;
                    padding: 8px;
                    background: #f8f9fa;
                    border-radius: 4px;
                    font-size: 12px;
                    max-height: 150px;
                    overflow-y: auto;
                "></div>
                <button id="toggle-panel-btn" style="
                    position: absolute;
                    top: 5px;
                    right: 5px;
                    background: none;
                    border: none;
                    font-size: 16px;
                    cursor: pointer;
                ">−</button>
            </div>
        `;
        
        document.body.appendChild(testPanel);
        
        // Setup test interface events
        this.setupTestInterface();
    }

    setupTestInterface() {
        const manualInput = document.getElementById('manual-barcode');
        const testBtn = document.getElementById('test-scan-btn');
        const toggleBtn = document.getElementById('toggle-panel-btn');
        const panel = document.getElementById('scanner-test-panel');
        
        // Manual test scan
        testBtn.addEventListener('click', () => {
            const barcode = manualInput.value.trim();
            if (barcode) {
                this.processScan(barcode);
                manualInput.value = '';
            }
        });
        
        // Enter key in manual input
        manualInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                testBtn.click();
            }
        });
        
        // Toggle panel
        let isMinimized = false;
        toggleBtn.addEventListener('click', () => {
            isMinimized = !isMinimized;
            const content = panel.children;
            for (let i = 1; i < content.length - 1; i++) {
                content[i].style.display = isMinimized ? 'none' : 'block';
            }
            toggleBtn.textContent = isMinimized ? '+' : '−';
            panel.style.height = isMinimized ? 'auto' : 'auto';
        });
    }

    async processScan(barcode) {
        console.log('Scanner detected barcode:', barcode);
        
        // Update test interface
        this.updateTestResult(`🔍 Scanning: ${barcode}...`);
        
        try {
            // Send to your LabSystem API
            const response = await fetch('/api/scanner/data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    barcode: barcode,
                    timestamp: new Date().toISOString(),
                    device: 'Zebra Scanner'
                })
            });
            
            const result = await response.json();
            
            // Update test interface
            this.updateTestResult(`✅ Result: ${result.message}`, result);
            
            // Handle successful scan result
            if (result.status === 'success') {
                this.handleSuccessfulScan(result);
            } else {
                this.handleFailedScan(result);
            }
            
        } catch (error) {
            console.error('Scanner API error:', error);
            this.updateTestResult(`❌ Error: ${error.message}`);
        }
    }

    updateTestResult(message, data = null) {
        const resultDiv = document.getElementById('scan-result');
        if (resultDiv) {
            const timestamp = new Date().toLocaleTimeString();
            const resultHtml = `
                <div style="border-bottom: 1px solid #dee2e6; padding: 5px 0;">
                    <strong>${timestamp}:</strong> ${message}
                    ${data ? `<br><small><pre>${JSON.stringify(data, null, 2)}</pre></small>` : ''}
                </div>
            `;
            resultDiv.innerHTML = resultHtml + resultDiv.innerHTML;
        }
    }

    handleSuccessfulScan(result) {
        // Handle different types of scan results
        switch (result.result_type) {
            case 'sample':
                console.log('Sample found:', result.sample);
                this.showSampleDetails(result.sample);
                break;
            case 'container':
                console.log('Container found:', result.container);
                this.showContainerDetails(result.container);
                break;
            case 'test_sample':
                console.log('Test sample found:', result.test_sample);
                this.showTestSampleDetails(result.test_sample);
                break;
            default:
                console.log('Unknown scan result type');
        }
    }

    handleFailedScan(result) {
        console.log('Scan failed:', result.message);
        // You could show a popup or notification here
        alert(`Barcode not found: ${result.message}`);
    }

    showSampleDetails(sample) {
        // Create or update sample details modal/panel
        console.log('Showing sample details:', sample);
        
        // Example: Show in alert (you would implement a proper modal)
        const details = `
Sample Found!
ID: ${sample.SampleIDFormatted}
Description: ${sample.Description}
Part Number: ${sample.PartNumber}
Location: ${sample.LocationName}
Amount: ${sample.Amount} ${sample.UnitName}
        `.trim();
        
        alert(details);
    }

    showContainerDetails(container) {
        console.log('Showing container details:', container);
        alert(`Container Found: ${container.ContainerIDFormatted} with ${container.SampleCount} samples`);
    }

    showTestSampleDetails(testSample) {
        console.log('Showing test sample details:', testSample);
        alert(`Test Sample Found: ${testSample.GeneratedIdentifier} for test ${testSample.TestNo}`);
    }

    // Public method to manually trigger a scan (for testing)
    testScan(barcode) {
        this.processScan(barcode);
    }
}

// Initialize scanner when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.zebraScanner = new ZebraScanner();
    console.log('Zebra Scanner initialized');
});