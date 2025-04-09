/**
 * Register Identification - Serial number handling for the registration form
 */

// Initialize when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Identification module loading...');
    
    // Setup scanner functionality
    setupScannerListeners();
    
    // Mark this module as loaded in the global state
    if (window.registerApp) {
        window.registerApp.modulesLoaded.identification = true;
        console.log('Identification module loaded');
    } else {
        console.error('registerApp not found - identification module cannot register');
    }
});

// Scanner functionality
function setupScannerListeners() {
    const scannerInput = document.getElementById('barcodeInput');
    const addManualBtn = document.getElementById('addManualBtn');
    const scanButton = document.getElementById('scanButton');
    const bulkEntryButton = document.getElementById('bulkEntryButton');
    const bulkEntrySection = document.querySelector('.bulk-entry');
    const addBulkBtn = document.getElementById('addBulkBtn');
    const clearAllScannedBtn = document.getElementById('clearAllScannedBtn');
    
    if (scannerInput && addManualBtn) {
        // Scanner input handling
        scannerInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                const barcode = event.target.value.trim();
                if (barcode) {
                    processScan(barcode);
                    event.target.value = '';
                }
            }
        });
        
        // Manual addition
        addManualBtn.addEventListener('click', function() {
            const barcode = scannerInput.value.trim();
            if (barcode) {
                processScan(barcode);
                scannerInput.value = '';
            }
            scannerInput.focus();
        });
    }
    
    // Toggle scanning state
    if (scanButton) {
        scanButton.addEventListener('click', function() {
            const isActive = this.classList.contains('btn-primary');
            
            if (isActive) {
                // Deactivate scanning
                this.classList.remove('btn-primary');
                this.classList.add('btn-outline-primary');
                this.innerHTML = '<i class="fas fa-barcode"></i> Start Scanning';
                if (scannerInput) {
                    scannerInput.disabled = true;
                    scannerInput.placeholder = "Scanning deaktiveret";
                }
            } else {
                // Activate scanning
                this.classList.remove('btn-outline-primary');
                this.classList.add('btn-primary');
                this.innerHTML = '<i class="fas fa-barcode"></i> Scanning Aktiv';
                if (scannerInput) {
                    scannerInput.disabled = false;
                    scannerInput.placeholder = "Scan eller indtast serienummer";
                    scannerInput.focus();
                }
            }
        });
    }
    
    // Show/hide bulk entry
    if (bulkEntryButton && bulkEntrySection) {
        bulkEntryButton.addEventListener('click', function() {
            bulkEntrySection.classList.toggle('d-none');
            
            if (!bulkEntrySection.classList.contains('d-none')) {
                document.getElementById('bulkBarcodes').focus();
            }
        });
    }
    
    // Add bulk serial numbers
    if (addBulkBtn) {
        addBulkBtn.addEventListener('click', function() {
            const bulkBarcodes = document.getElementById('bulkBarcodes');
            if (bulkBarcodes) {
                const barcodes = bulkBarcodes.value.split('\n')
                    .map(code => code.trim())
                    .filter(code => code.length > 0);
                
                const totalExpected = parseInt(document.querySelector('[name="totalAmount"]')?.value) || 0;
                const currentCount = registerApp.scannedItems.length;
                
                if (currentCount + barcodes.length > totalExpected) {
                    showErrorMessage(`Kan ikke tilføje ${barcodes.length} stregkoder. Maksimalt antal er ${totalExpected} (${currentCount} allerede scannet)`);
                    return;
                }
                
                barcodes.forEach(barcode => {
                    processScan(barcode);
                });
                
                bulkBarcodes.value = '';
                showSuccessMessage(`${barcodes.length} stregkoder tilføjet succesfuldt`);
                
                // Hide bulk entry after addition
                bulkEntrySection.classList.add('d-none');
            }
        });
    }
    
    // Clear all scanned items
    if (clearAllScannedBtn) {
        clearAllScannedBtn.addEventListener('click', function() {
            if (confirm('Er du sikker på, at du vil fjerne alle scannede prøver?')) {
                registerApp.scannedItems = [];
                updateScanUI();
                showSuccessMessage('Alle scannede prøver er blevet fjernet');
            }
        });
    }
}

// Handle scanning a barcode
function processScan(barcode) {
    if (!barcode) return;

    const totalExpected = parseInt(document.querySelector('[name="totalAmount"]')?.value) || 0;
    
    // Check for duplicates
    if (registerApp.scannedItems.includes(barcode)) {
        showWarningMessage(`Stregkode "${barcode}" er allerede scannet`);
        return;
    }

    if (registerApp.scannedItems.length < totalExpected) {
        registerApp.scannedItems.push(barcode);
        updateScanUI();
        // Play a sound to indicate successful scanning
        playSuccessSound();
    } else {
        showErrorMessage('Maksimalt antal prøver nået');
    }
}

// Update UI with scanned items
function updateScanUI() {
    const counter = document.getElementById('scannedCount');
    const totalCounter = document.getElementById('totalCount');
    const total = document.querySelector('[name="totalAmount"]')?.value || 0;
    const emptyMessage = document.querySelector('.empty-scanned-message');

    if (counter) counter.textContent = registerApp.scannedItems.length;
    if (totalCounter) totalCounter.textContent = total;

    const container = document.querySelector('.scanned-items');
    if (container) {
        // Remove empty message if there are scanned items
        if (emptyMessage) {
            emptyMessage.style.display = registerApp.scannedItems.length > 0 ? 'none' : 'block';
        }
        
        // If no scanned items, show empty message and return
        if (registerApp.scannedItems.length === 0) {
            container.innerHTML = `<div class="empty-scanned-message text-center p-3 text-muted">
                Ingen prøver scannet endnu. Brug scanneren eller indtast serienumre manuelt ovenfor.
            </div>`;
            return;
        }
        
        // Build list of scanned items
        let html = '<div class="list-group">';
        
        registerApp.scannedItems.forEach((code, index) => {
            html += `
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <span class="badge bg-primary rounded-pill me-3">${index + 1}</span>
                        <span>${code}</span>
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-danger remove-item" data-index="${index}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        });
        
        html += '</div>';
        container.innerHTML = html;
        
        // Add event listeners to remove buttons
        container.querySelectorAll('.remove-item').forEach(button => {
            button.addEventListener('click', function() {
                const index = parseInt(this.getAttribute('data-index'));
                removeScannedItem(index);
            });
        });
    }
}

// Remove a scanned item
function removeScannedItem(index) {
    registerApp.scannedItems.splice(index, 1);
    updateScanUI();
}

// Play a success sound when scanning
function playSuccessSound() {
    try {
        // Create a simple sound
        const context = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = context.createOscillator();
        const gainNode = context.createGain();
        
        oscillator.type = 'sine';
        oscillator.frequency.value = 1000;
        oscillator.connect(gainNode);
        gainNode.connect(context.destination);
        
        gainNode.gain.value = 0.1;
        oscillator.start(0);
        
        setTimeout(function() {
            oscillator.stop();
        }, 100);
    } catch (e) {
        // Sound effects are not crucial, so we ignore errors
        console.log('Sound effects not supported');
    }
}

// Focus on barcode input
function setupBarcodeInput() {
    const barcodeInput = document.getElementById('barcodeInput');
    if (barcodeInput) {
        barcodeInput.focus();
    }
}