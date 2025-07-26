/**
 * Zebra Scanner Integration for LabSystem
 * Handles both manual input and automatic scanner integration
 */

class ZebraScanner {
    constructor() {
        this.scannerInput = null;
        this.lastScanTime = 0;
        this.scanBuffer = '';
        this.scannerPaused = false;
        this.init();
    }

    init() {
        // Create hidden input for scanner data
        this.createScannerInput();
        
        // Listen for barcode scans
        this.setupScanListener();
        
        // Setup focus management to pause scanner when user is typing in forms
        this.setupFocusManagement();
        
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
        
        // Keep input focused for scanner data - but only when not paused
        this.scannerInput.focus();
        
        // Only refocus on specific non-form clicks
        document.addEventListener('click', (e) => {
            // Only refocus if clicking on body, div, span, or other non-interactive elements
            if (!this.scannerPaused && e.target && 
                e.target.matches('body, div, span, p, h1, h2, h3, h4, h5, h6, img, .content-section')) {
                setTimeout(() => {
                    if (!this.scannerPaused) {
                        this.scannerInput.focus();
                    }
                }, 100);
            }
        });
    }

    setupScanListener() {
        let scanTimeout;
        
        this.scannerInput.addEventListener('input', (e) => {
            // If scanner is paused, ignore input
            if (this.scannerPaused) {
                e.target.value = '';
                return;
            }
            
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
                if (this.scanBuffer.trim().length > 0 && !this.scannerPaused) {
                    this.processScan(this.scanBuffer.trim());
                    this.scanBuffer = '';
                    e.target.value = '';
                }
            }, 50);
        });

        // Handle Enter key (common scanner suffix)
        this.scannerInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !this.scannerPaused) {
                clearTimeout(scanTimeout);
                if (this.scanBuffer.trim().length > 0) {
                    this.processScan(this.scanBuffer.trim());
                    this.scanBuffer = '';
                    e.target.value = '';
                }
            }
        });
    }


    async processScan(barcode) {
        console.log('Scanner detected barcode:', barcode);
        
        
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
            
            
            // Handle successful scan result
            if (result.status === 'success') {
                this.handleSuccessfulScan(result);
            } else {
                this.handleFailedScan(result);
            }
            
        } catch (error) {
            console.error('Scanner API error:', error);
        }
    }

    setupFocusManagement() {
        // Pause scanner when user focuses on form elements
        document.addEventListener('focusin', (e) => {
            const target = e.target;
            
            // Check if the focused element is a form input (but not our scanner input)
            if (target !== this.scannerInput && 
                target.matches('input, textarea, select, [contenteditable]')) {
                
                this.scannerPaused = true;
                console.log('Scanner paused - user is typing in form field:', target.name || target.id);
                
                // Clear scanner buffer when pausing
                this.scanBuffer = '';
                this.scannerInput.value = '';
            }
        });
        
        // Resume scanner when user leaves form elements
        document.addEventListener('focusout', (e) => {
            const target = e.target;
            
            // If leaving a form element, check if we should resume
            if (target !== this.scannerInput && 
                target.matches('input, textarea, select, [contenteditable]')) {
                
                setTimeout(() => {
                    // Only resume if no other form element has focus
                    const activeElement = document.activeElement;
                    if (!activeElement || 
                        activeElement === document.body ||
                        activeElement === this.scannerInput ||
                        !activeElement.matches('input, textarea, select, [contenteditable]')) {
                        
                        this.scannerPaused = false;
                        console.log('Scanner resumed - user left form field');
                        // Only refocus if user isn't actively using another form element
                        if (activeElement !== this.scannerInput && 
                            !activeElement.matches('input, textarea, select, [contenteditable]')) {
                            this.scannerInput.focus();
                        }
                    }
                }, 200); // Longer delay to ensure focus has settled
            }
        });
        
        // Pause during form submission
        document.addEventListener('submit', (e) => {
            this.scannerPaused = true;
            console.log('Scanner paused during form submission');
            setTimeout(() => {
                // Only resume if not in a form field
                const activeElement = document.activeElement;
                if (!activeElement.matches('input, textarea, select, [contenteditable]')) {
                    this.scannerPaused = false;
                    this.scannerInput.focus();
                    console.log('Scanner resumed after form submission');
                }
            }, 1000);
        });
    }

    // Public methods to control scanner
    enableScanner() {
        this.scannerPaused = false;
        this.scannerInput.focus();
        console.log('Scanner manually enabled');
    }
    
    disableScanner() {
        this.scannerPaused = true;
        console.log('Scanner manually disabled');
    }
    
    isEnabled() {
        return !this.scannerPaused;
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

}

// Initialize scanner when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.zebraScanner = new ZebraScanner();
    console.log('Zebra Scanner initialized');
});