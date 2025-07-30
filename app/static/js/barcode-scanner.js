/**
 * Global Barcode Scanner Handler
 * Handles wireless Zebra scanner input across all pages
 */

class BarcodeScanner {
    constructor() {
        console.log('🚀 DEBUG: BarcodeScanner constructor called');
        this.scanBuffer = '';
        this.scanTimeout = null;
        this.scanTimeoutDuration = 100; // ms between characters from scanner
        this.minBarcodeLength = 5;
        this.maxBarcodeLength = 50;
        
        this.barcodePatterns = {
            container: /^CNT-\d+$/,
            sample: /^(BC\d+-.*|SMP-\d+|BC\d+.*-.*)$/
        };
        console.log('🔍 DEBUG: Barcode patterns:', this.barcodePatterns);
        
        // Scan history storage
        this.scanHistory = JSON.parse(localStorage.getItem('scanHistory') || '[]');
        this.currentFilter = 'all';
        console.log('📚 DEBUG: Loaded scan history:', this.scanHistory.length, 'items');
        
        this.init();
        console.log('✅ DEBUG: BarcodeScanner constructor completed');
    }
    
    init() {
        console.log('🔧 DEBUG: BarcodeScanner init() called');
        // Listen for keydown events globally
        document.addEventListener('keydown', (event) => this.handleKeyInput(event));
        console.log('⌨️ DEBUG: Global keydown listener added');
        
        // Prevent scanner input from interfering with forms when modal is closed
        this.isModalOpen = false;
        
        console.log('✅ DEBUG: BarcodeScanner initialized successfully');
    }
    
    handleKeyInput(event) {
        // Only process if no input fields are focused (unless scanner modal is open)
        const activeElement = document.activeElement;
        const isInputFocused = activeElement && 
            (activeElement.tagName === 'INPUT' || 
             activeElement.tagName === 'TEXTAREA' || 
             activeElement.tagName === 'SELECT' ||
             activeElement.contentEditable === 'true');
        
        // If modal is open, always process scanner input
        // If modal is closed, only process if no input is focused
        if (!this.isModalOpen && isInputFocused) {
            return;
        }
        
        // Handle Enter key - indicates end of barcode scan
        if (event.key === 'Enter') {
            event.preventDefault();
            this.processScan();
            return;
        }
        
        // Handle printable characters
        if (event.key.length === 1) {
            event.preventDefault();
            this.addCharacterToBuffer(event.key);
        }
    }
    
    addCharacterToBuffer(char) {
        // Clear existing timeout
        if (this.scanTimeout) {
            clearTimeout(this.scanTimeout);
        }
        
        // Add character to buffer
        this.scanBuffer += char;
        
        // Set timeout to auto-process if no more characters come
        this.scanTimeout = setTimeout(() => {
            if (this.scanBuffer.length >= this.minBarcodeLength) {
                this.processScan();
            } else {
                this.clearBuffer();
            }
        }, this.scanTimeoutDuration);
        
        // Prevent buffer overflow
        if (this.scanBuffer.length > this.maxBarcodeLength) {
            this.clearBuffer();
        }
    }
    
    processScan() {
        const barcode = this.scanBuffer.trim().toUpperCase();
        this.clearBuffer();
        
        if (barcode.length < this.minBarcodeLength) {
            return;
        }
        
        console.log('Barcode scanned:', barcode);
        
        // Determine barcode type
        const barcodeType = this.determineBarcodeType(barcode);
        
        if (barcodeType) {
            this.handleBarcodeScan(barcode, barcodeType);
        } else {
            this.showError(`Unknown barcode format: ${barcode}`);
        }
    }
    
    determineBarcodeType(barcode) {
        for (const [type, pattern] of Object.entries(this.barcodePatterns)) {
            if (pattern.test(barcode)) {
                return type;
            }
        }
        return null;
    }
    
    async handleBarcodeScan(barcode, type) {
        console.log('🔄 DEBUG: handleBarcodeScan() called with:', barcode, type);
        try {
            // Show loading toast instead of modal
            console.log('📡 DEBUG: Showing loading toast');
            this.showLoadingToast(barcode);
            
            // Lookup barcode in database
            const apiUrl = `/api/barcode/${encodeURIComponent(barcode)}`;
            console.log('🌐 DEBUG: Making API call to:', apiUrl);
            const response = await fetch(apiUrl);
            console.log('📥 DEBUG: API response status:', response.status, response.statusText);
            
            const data = await response.json();
            console.log('📊 DEBUG: API response data:', data);
            
            // Hide loading toast
            this.hideLoadingToast();
            
            if (data.success) {
                console.log('✅ DEBUG: Barcode found, showing modal');
                // Add to scan history
                this.addToScanHistory(barcode, type, data, true);
                this.showScanModal(barcode, type, data);
            } else {
                console.log('❌ DEBUG: Barcode not found');
                // Add failed scan to history
                this.addToScanHistory(barcode, type, null, false);
                this.showError(`Barcode not found: ${barcode}`);
            }
        } catch (error) {
            console.error('💥 DEBUG: Error looking up barcode:', error);
            // Hide loading toast
            this.hideLoadingToast();
            // Add failed scan to history
            this.addToScanHistory(barcode, type, null, false);
            this.showError(`Error scanning barcode: ${barcode}`);
        }
    }
    
    showScanModal(barcode, type, data) {
        this.isModalOpen = true;
        
        // Store scan data for use in print functions
        this.lastScanData = data;
        
        // Remove any existing modal to prevent conflicts
        const existingModal = document.getElementById('barcodeModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Create new modal
        const modal = this.createScanModal();
        document.body.appendChild(modal);
        
        // Update modal content
        this.updateModalContent(modal, barcode, type, data);
        
        // Show modal
        const bsModal = new bootstrap.Modal(modal, {
            backdrop: true,
            keyboard: true,
            focus: true
        });
        bsModal.show();
        
        // Handle modal close
        modal.addEventListener('hidden.bs.modal', () => {
            this.isModalOpen = false;
            // Ensure modal is completely removed from DOM
            modal.remove();
            // Remove any leftover backdrops
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());
            // Restore body classes
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        }, { once: true });
    }
    
    createScanModal() {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'barcodeModal';
        modal.tabIndex = -1;
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-barcode me-2"></i>Barcode Scan Result
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="barcodeModalBody">
                        <!-- Content will be populated -->
                    </div>
                    <div class="modal-footer" id="barcodeModalFooter">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        return modal;
    }
    
    updateModalContent(modal, barcode, type, data) {
        const body = modal.querySelector('#barcodeModalBody');
        const footer = modal.querySelector('#barcodeModalFooter');
        
        // Generate content based on barcode type
        switch (type) {
            case 'container':
                this.renderContainerContent(body, footer, barcode, data);
                break;
            case 'sample':
                this.renderSampleContent(body, footer, barcode, data);
                break;
            default:
                body.innerHTML = `<p>Unknown barcode type: ${type}</p>`;
        }
    }
    
    renderContainerContent(body, footer, barcode, data) {
        const container = data.container;
        const samples = data.samples || [];
        
        body.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6><i class="fas fa-box me-2"></i>Container Information</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Container ID:</strong></td><td>${container.ContainerID}</td></tr>
                        <tr><td><strong>Barcode:</strong></td><td><code>${barcode}</code></td></tr>
                        <tr><td><strong>Description:</strong></td><td>${container.Description}</td></tr>
                        <tr><td><strong>Type:</strong></td><td>${container.TypeName}</td></tr>
                        <tr><td><strong>Location:</strong></td><td>${container.LocationName}</td></tr>
                        <tr><td><strong>Task:</strong></td><td>${container.TaskName || 'None'}</td></tr>
                        <tr><td><strong>Capacity:</strong></td><td>${container.ContainerCapacity}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6><i class="fas fa-vials me-2"></i>Samples in Container (${samples.length})</h6>
                    ${samples.length > 0 ? `
                        <div class="table-responsive" style="max-height: 200px; overflow-y: auto;">
                            <table class="table table-sm">
                                <thead><tr><th>Sample</th><th>Description</th><th>Amount</th></tr></thead>
                                <tbody>
                                    ${samples.map(s => `
                                        <tr>
                                            <td><a href="#" onclick="window.barcodeScanner.scanBarcode('${s.Barcode}')">${s.SampleIDFormatted}</a></td>
                                            <td>${s.Description}</td>
                                            <td>${s.Amount}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    ` : '<p class="text-muted">No samples in this container</p>'}
                </div>
            </div>
        `;
        
        // Add action buttons - show direct print option on scanner page
        const isOnScannerPage = window.location.pathname === '/scanner';
        let printButton = '';
        
        if (isOnScannerPage && typeof window.showPrintConfirmation === 'function') {
            // Direct print button for scanner page
            printButton = `
                <button type="button" class="btn btn-primary" onclick="window.barcodeScanner.showContainerPrintConfirmationWithContext(${container.ContainerID}, '${container.ContainerIDFormatted || 'CNT-' + container.ContainerID}', '${barcode}', '${container.Description || ''}')">
                    <i class="fas fa-print me-1"></i>Print Label
                </button>
            `;
        } else {
            // Print queue button for other pages
            printButton = `
                <button type="button" class="btn btn-outline-primary" onclick="window.barcodeScanner.addContainerToPrintQueue(${container.ContainerID}, '${container.ContainerIDFormatted || 'CNT-' + container.ContainerID}', '${barcode}', '${container.Description || ''}')">
                    <i class="fas fa-print me-1"></i>Add to Print Queue
                </button>
            `;
        }
        
        footer.innerHTML = `
            ${printButton}
            <button type="button" class="btn btn-outline-secondary" onclick="window.location.href='/containers'">
                <i class="fas fa-box me-1"></i>View All Containers
            </button>
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
        `;
    }
    
    renderSampleContent(body, footer, barcode, data) {
        const sample = data.sample;
        const storage = data.storage || {};
        const history = data.history || [];
        
        body.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6><i class="fas fa-vial me-2"></i>Sample Information</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Sample ID:</strong></td><td>${sample.SampleIDFormatted}</td></tr>
                        <tr><td><strong>Barcode:</strong></td><td><code>${barcode}</code></td></tr>
                        <tr><td><strong>Description:</strong></td><td>${sample.Description}</td></tr>
                        <tr><td><strong>Part Number:</strong></td><td>${sample.PartNumber || '-'}</td></tr>
                        <tr><td><strong>Status:</strong></td><td><span class="badge bg-primary">${sample.Status}</span></td></tr>
                        <tr><td><strong>Amount:</strong></td><td>${sample.Amount} ${sample.UnitName || 'pcs'}</td></tr>
                        <tr><td><strong>Task:</strong></td><td>${sample.TaskName || 'None'}</td></tr>
                        <tr><td><strong>Expire Date:</strong></td><td>${sample.ExpireDate || '-'}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6><i class="fas fa-map-marker-alt me-2"></i>Storage Information</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Location:</strong></td><td>${storage.LocationName || 'Unknown'}</td></tr>
                        <tr><td><strong>Amount Remaining:</strong></td><td>${storage.AmountRemaining || 0}</td></tr>
                        <tr><td><strong>Container:</strong></td><td>${storage.ContainerDescription || 'Direct storage'}</td></tr>
                    </table>
                    
                    ${history.length > 0 ? `
                        <h6 class="mt-3"><i class="fas fa-history me-2"></i>Recent Activity</h6>
                        <div style="max-height: 120px; overflow-y: auto;">
                            ${history.slice(0, 3).map(h => `
                                <small class="d-block mb-1">
                                    <strong>${h.ActionType}</strong> - ${new Date(h.Timestamp).toLocaleDateString()}
                                </small>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
        
        // Add action buttons - show direct print option on scanner page
        const isOnScannerPage = window.location.pathname === '/scanner';
        let printButton = '';
        
        if (isOnScannerPage && typeof window.showPrintConfirmation === 'function') {
            // Direct print button for scanner page
            printButton = `
                <button type="button" class="btn btn-primary" onclick="window.barcodeScanner.showSamplePrintConfirmation(${sample.SampleID}, '${sample.SampleIDFormatted}', '${barcode}', '${sample.Description || ''}')">
                    <i class="fas fa-print me-1"></i>Print Label
                </button>
            `;
        } else {
            // Print queue button for other pages
            printButton = `
                <button type="button" class="btn btn-outline-primary" onclick="window.barcodeScanner.addSampleToPrintQueue(${sample.SampleID}, '${sample.SampleIDFormatted}', '${barcode}', '${sample.Description || ''}')">
                    <i class="fas fa-print me-1"></i>Add to Print Queue
                </button>
            `;
        }
        
        footer.innerHTML = `
            ${printButton}
            <button type="button" class="btn btn-outline-success" onclick="window.barcodeScanner.showMoveToTestModal(${sample.SampleID}, '${sample.SampleIDFormatted}')">
                <i class="fas fa-flask me-1"></i>Move to Test
            </button>
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
        `;
    }
    
    
    showLoadingToast(barcode) {
        // Remove existing loading toast
        this.hideLoadingToast();
        
        const toast = document.createElement('div');
        toast.className = 'toast position-fixed top-0 end-0 m-3';
        toast.id = 'loadingToast';
        toast.style.zIndex = '9999';
        toast.innerHTML = `
            <div class="toast-header bg-primary text-white">
                <div class="spinner-border spinner-border-sm me-2" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <strong class="me-auto">Scanning...</strong>
            </div>
            <div class="toast-body">
                Looking up: <strong>${barcode}</strong>
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { autohide: false });
        bsToast.show();
    }
    
    hideLoadingToast() {
        const loadingToast = document.getElementById('loadingToast');
        if (loadingToast) {
            const bsToast = bootstrap.Toast.getInstance(loadingToast);
            if (bsToast) {
                bsToast.hide();
            }
            loadingToast.remove();
        }
    }
    
    showError(message) {
        // Create simple error toast
        const toast = document.createElement('div');
        toast.className = 'toast position-fixed top-0 end-0 m-3';
        toast.style.zIndex = '9999';
        toast.innerHTML = `
            <div class="toast-header bg-danger text-white">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong class="me-auto">Scanner Error</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove after toast is hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
    
    clearBuffer() {
        this.scanBuffer = '';
        if (this.scanTimeout) {
            clearTimeout(this.scanTimeout);
            this.scanTimeout = null;
        }
    }
    
    // Public method to manually trigger a scan (for testing)
    scanBarcode(barcode) {
        console.log('🎯 DEBUG: scanBarcode() called with:', barcode);
        const type = this.determineBarcodeType(barcode);
        console.log('🔍 DEBUG: Determined barcode type:', type);
        if (type) {
            console.log('✅ DEBUG: Valid barcode type, calling handleBarcodeScan');
            this.handleBarcodeScan(barcode, type);
        } else {
            console.log('❌ DEBUG: Invalid barcode format');
            this.showError(`Invalid barcode format: ${barcode}`);
        }
    }
    
    async showMoveToTestModal(sampleId, sampleIdFormatted) {
        try {
            // Hide and clean up the current modal
            const currentModal = document.getElementById('barcodeModal');
            if (currentModal) {
                const currentBsModal = bootstrap.Modal.getInstance(currentModal);
                if (currentBsModal) {
                    currentBsModal.hide();
                }
                currentModal.remove();
            }
            
            // Clean up any modal backdrops
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());
            
            // Fetch available tests
            const response = await fetch('/api/tests');
            const data = await response.json();
            
            if (!data.success) {
                this.showError('Failed to load available tests');
                return;
            }
            
            const tests = data.tests || [];
            
            // Create move to test modal
            this.createMoveToTestModal(sampleId, sampleIdFormatted, tests);
            
        } catch (error) {
            console.error('Error showing move to test modal:', error);
            this.showError('Error loading tests');
        }
    }
    
    createMoveToTestModal(sampleId, sampleIdFormatted, tests) {
        // Remove existing modal if it exists
        const existingModal = document.getElementById('moveToTestModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'moveToTestModal';
        modal.tabIndex = -1;
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-flask me-2"></i>Move Sample to Test
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label"><strong>Sample:</strong> ${sampleIdFormatted}</label>
                        </div>
                        
                        <div class="mb-3">
                            <label for="testSelect" class="form-label">Select Test</label>
                            <select class="form-select" id="testSelect" required>
                                <option value="">Choose a test...</option>
                                ${tests.map(test => `
                                    <option value="${test.id}">
                                        ${test.test_no} - ${test.test_name} 
                                        ${test.task_name ? '(Task: ' + test.task_name + ')' : ''}
                                    </option>
                                `).join('')}
                            </select>
                            ${tests.length === 0 ? '<small class="text-muted">No active tests available</small>' : ''}
                        </div>
                        
                        <div class="mb-3">
                            <label for="amountInput" class="form-label">Amount</label>
                            <input type="number" class="form-control" id="amountInput" value="1" min="1" step="1">
                        </div>
                        
                        <div class="mb-3">
                            <label for="notesInput" class="form-label">Notes (optional)</label>
                            <textarea class="form-control" id="notesInput" rows="2" placeholder="Optional notes..."></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="confirmMoveBtn" ${tests.length === 0 ? 'disabled' : ''}>
                            <i class="fas fa-flask me-1"></i>Move to Test
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Show the modal
        const bsModal = new bootstrap.Modal(modal, {
            backdrop: true,
            keyboard: true,
            focus: true
        });
        bsModal.show();
        
        // Handle modal close cleanup
        modal.addEventListener('hidden.bs.modal', () => {
            this.isModalOpen = false;
            modal.remove();
            // Clean up any leftover backdrops
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());
            // Restore body classes
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        }, { once: true });
        
        // Handle confirm button
        const confirmBtn = modal.querySelector('#confirmMoveBtn');
        confirmBtn.addEventListener('click', () => {
            this.handleMoveToTest(sampleId, sampleIdFormatted, modal, bsModal);
        });
    }
    
    async handleMoveToTest(sampleId, sampleIdFormatted, modal, bsModal) {
        const testSelect = modal.querySelector('#testSelect');
        const amountInput = modal.querySelector('#amountInput');
        const notesInput = modal.querySelector('#notesInput');
        const confirmBtn = modal.querySelector('#confirmMoveBtn');
        
        const testId = testSelect.value;
        const amount = parseInt(amountInput.value) || 1;
        const notes = notesInput.value.trim();
        
        if (!testId) {
            this.showError('Please select a test');
            return;
        }
        
        if (amount < 1) {
            this.showError('Amount must be at least 1');
            return;
        }
        
        // Disable button and show loading
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Moving...';
        
        try {
            const response = await fetch(`/api/samples/${sampleId}/move-to-test`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    test_id: testId,
                    amount: amount,
                    notes: notes
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Close modal
                bsModal.hide();
                
                // Show success message (no print prompt for test samples)
                this.showSuccess(`Sample ${sampleIdFormatted} moved to test successfully!`);
            } else {
                this.showError(result.error || 'Failed to move sample to test');
            }
            
        } catch (error) {
            console.error('Error moving sample to test:', error);
            this.showError('Error moving sample to test');
        } finally {
            // Re-enable button
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = '<i class="fas fa-flask me-1"></i>Move to Test';
        }
    }
    
    showSuccess(message) {
        // Create success toast
        const toast = document.createElement('div');
        toast.className = 'toast position-fixed top-0 end-0 m-3';
        toast.style.zIndex = '9999';
        toast.innerHTML = `
            <div class="toast-header bg-success text-white">
                <i class="fas fa-check-circle me-2"></i>
                <strong class="me-auto">Success</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove after toast is hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
    
    addToScanHistory(barcode, type, data, success) {
        const historyItem = {
            barcode: barcode,
            type: type,
            success: success,
            timestamp: new Date().toISOString(),
            description: success && data ? this.getDescriptionFromData(data, type) : 'Not found'
        };
        
        // Add to beginning of array
        this.scanHistory.unshift(historyItem);
        
        // Keep only last 50 scans
        if (this.scanHistory.length > 50) {
            this.scanHistory = this.scanHistory.slice(0, 50);
        }
        
        // Save to localStorage
        localStorage.setItem('scanHistory', JSON.stringify(this.scanHistory));
        
        // Update display if on scanner page
        this.updateScanHistoryDisplay();
    }
    
    getDescriptionFromData(data, type) {
        switch (type) {
            case 'container':
                return data.container ? data.container.Description : 'Container';
            case 'sample':
                return data.sample ? data.sample.Description : 'Sample';
            default:
                return 'Unknown';
        }
    }
    
    updateScanHistoryDisplay() {
        const historyTable = document.getElementById('scanHistoryBody');
        if (!historyTable) return; // Not on scanner page
        
        // Filter history based on current filter
        let filteredHistory = this.scanHistory;
        if (this.currentFilter !== 'all') {
            filteredHistory = this.scanHistory.filter(item => item.type === this.currentFilter);
        }
        
        if (filteredHistory.length === 0) {
            const message = this.currentFilter === 'all' ? 
                'No scans yet. Start scanning to see results here.' :
                `No ${this.getTypeDisplayName(this.currentFilter).toLowerCase()}s scanned yet.`;
            
            historyTable.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted py-4">
                        <i class="fas fa-barcode fa-2x mb-2"></i>
                        <br>${message}
                    </td>
                </tr>
            `;
            return;
        }
        
        // Limit to last 5 scans
        const limitedHistory = filteredHistory.slice(0, 5);
        
        historyTable.innerHTML = limitedHistory.map(item => {
            const time = new Date(item.timestamp).toLocaleTimeString();
            const statusBadge = item.success ? 
                '<span class="badge bg-success">Found</span>' : 
                '<span class="badge bg-danger">Not Found</span>';
            const typeDisplay = this.getTypeDisplayName(item.type);
            
            return `
                <tr class="scan-history-row ${item.success ? '' : 'table-warning'}" style="cursor: pointer;" onclick="window.barcodeScanner.rescanBarcode('${item.barcode}')">
                    <td>${time}</td>
                    <td><code>${item.barcode}</code></td>
                    <td>${typeDisplay}</td>
                    <td>${item.description}</td>
                    <td>${statusBadge}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); window.barcodeScanner.rescanBarcode('${item.barcode}')">
                            <i class="fas fa-search"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
        
        // Update filter button states
        this.updateFilterButtons();
    }
    
    getTypeDisplayName(type) {
        switch (type) {
            case 'container': return 'Container';
            case 'sample': return 'Sample';
            default: return 'Unknown';
        }
    }
    
    rescanBarcode(barcode) {
        this.scanBarcode(barcode);
    }
    
    clearScanHistory() {
        this.scanHistory = [];
        localStorage.removeItem('scanHistory');
        this.updateScanHistoryDisplay();
    }
    
    filterScans(type) {
        this.currentFilter = type;
        this.updateScanHistoryDisplay();
    }
    
    updateFilterButtons() {
        const filterButtons = ['filterAll', 'filterContainer', 'filterSample'];
        const filterMappings = {
            'filterAll': 'all',
            'filterContainer': 'container', 
            'filterSample': 'sample'
        };
        
        filterButtons.forEach(buttonId => {
            const button = document.getElementById(buttonId);
            if (button) {
                const filterType = filterMappings[buttonId];
                if (filterType === this.currentFilter) {
                    button.classList.remove('btn-outline-secondary');
                    button.classList.add('btn-secondary');
                } else {
                    button.classList.remove('btn-secondary');
                    button.classList.add('btn-outline-secondary');
                }
            }
        });
    }
    
    addSampleToPrintQueue(sampleId, sampleIdFormatted, barcode, description) {
        try {
            let printJobs = JSON.parse(localStorage.getItem('printJobs') || '[]');
            
            const printJob = {
                id: Date.now(),
                timestamp: new Date().toISOString(),
                sampleId: sampleId,
                sampleIdFormatted: sampleIdFormatted,
                barcode: barcode,
                description: description,
                type: 'sample',
                status: 'queued'
            };
            
            printJobs.unshift(printJob); // Add to beginning
            
            // Keep only last 50 jobs
            if (printJobs.length > 50) {
                printJobs = printJobs.slice(0, 50);
            }
            
            localStorage.setItem('printJobs', JSON.stringify(printJobs));
            console.log('Sample added to print queue:', printJob);
            
            // Show success message
            this.showSuccess(`Sample ${sampleIdFormatted} added to print queue!`);
            
            // Trigger print queue refresh if on scanner page
            if (typeof loadPrintJobs === 'function') {
                loadPrintJobs();
            }
            
            // Close the current modal
            const currentModal = document.getElementById('barcodeModal');
            if (currentModal) {
                const currentBsModal = bootstrap.Modal.getInstance(currentModal);
                if (currentBsModal) {
                    currentBsModal.hide();
                }
            }
            
        } catch (error) {
            console.error('Error adding sample to print queue:', error);
            this.showError('Error adding sample to print queue');
        }
    }
    
    addContainerToPrintQueue(containerId, containerIdFormatted, barcode, description) {
        try {
            let printJobs = JSON.parse(localStorage.getItem('printJobs') || '[]');
            
            const printJob = {
                id: Date.now(),
                timestamp: new Date().toISOString(),
                containerId: containerId,
                containerIdFormatted: containerIdFormatted,
                // For compatibility with scanner page - use container data as sample data
                sampleId: containerId,
                sampleIdFormatted: containerIdFormatted,
                barcode: barcode,
                description: description,
                type: 'container',
                status: 'queued'
            };
            
            printJobs.unshift(printJob); // Add to beginning
            
            // Keep only last 50 jobs
            if (printJobs.length > 50) {
                printJobs = printJobs.slice(0, 50);
            }
            
            localStorage.setItem('printJobs', JSON.stringify(printJobs));
            console.log('Container added to print queue:', printJob);
            
            // Show success message
            this.showSuccess(`Container ${containerIdFormatted} added to print queue!`);
            
            // Trigger print queue refresh if on scanner page
            if (typeof loadPrintJobs === 'function') {
                loadPrintJobs();
            }
            
            // Close the current modal
            const currentModal = document.getElementById('barcodeModal');
            if (currentModal) {
                const currentBsModal = bootstrap.Modal.getInstance(currentModal);
                if (currentBsModal) {
                    currentBsModal.hide();
                }
            }
            
        } catch (error) {
            console.error('Error adding container to print queue:', error);
            this.showError('Error adding container to print queue');
        }
    }
    
    showContainerPrintConfirmation(containerId, containerIdFormatted, barcode, description, sampleCount) {
        // Close the scanner modal first
        const scannerModal = document.getElementById('barcodeModal');
        if (scannerModal) {
            const bsModal = bootstrap.Modal.getInstance(scannerModal);
            if (bsModal) {
                bsModal.hide();
            }
        }
        
        // Create container data object for print confirmation
        const containerData = {
            type: 'container',
            ContainerID: containerId,
            ContainerIDFormatted: containerIdFormatted,
            Barcode: barcode,
            Description: description,
            SampleCount: sampleCount
        };
        
        // Call the scanner page print confirmation function
        if (typeof window.showPrintConfirmation === 'function') {
            window.showPrintConfirmation(containerData);
        } else {
            console.error('showPrintConfirmation function not available');
            this.showError('Print confirmation not available on this page');
        }
    }
    
    showContainerPrintConfirmationWithContext(containerId, containerIdFormatted, barcode, description) {
        // Find the current scan data to get correct sample count
        let sampleCount = 0;
        
        // Look for the most recent scan data in our scan history
        if (this.lastScanData && this.lastScanData.samples) {
            sampleCount = this.lastScanData.samples.length;
        } else if (this.lastScanData && this.lastScanData.container && this.lastScanData.container.SampleCount) {
            sampleCount = this.lastScanData.container.SampleCount;
        }
        
        // Call the original function with correct sample count
        this.showContainerPrintConfirmation(containerId, containerIdFormatted, barcode, description, sampleCount);
    }
    
    showSamplePrintConfirmation(sampleId, sampleIdFormatted, barcode, description) {
        // Close the scanner modal first
        const scannerModal = document.getElementById('barcodeModal');
        if (scannerModal) {
            const bsModal = bootstrap.Modal.getInstance(scannerModal);
            if (bsModal) {
                bsModal.hide();
            }
        }
        
        // Create sample data object for print confirmation
        const sampleData = {
            type: 'sample',
            SampleID: sampleId,
            SampleIDFormatted: sampleIdFormatted,
            Barcode: barcode,
            Description: description
        };
        
        // Call the scanner page print confirmation function
        if (typeof window.showPrintConfirmation === 'function') {
            window.showPrintConfirmation(sampleData);
        } else {
            console.error('showPrintConfirmation function not available');
            this.showError('Print confirmation not available on this page');
        }
    }
}

// Initialize global scanner when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🌟 DEBUG: DOM loaded, initializing global barcode scanner');
    try {
        window.barcodeScanner = new BarcodeScanner();
        console.log('🎉 DEBUG: Global barcode scanner initialized successfully');
        console.log('🔗 DEBUG: window.barcodeScanner:', window.barcodeScanner);
        
        // Test if scanner is accessible
        if (typeof window.barcodeScanner.scanBarcode === 'function') {
            console.log('✅ DEBUG: scanBarcode method is accessible');
        } else {
            console.error('❌ DEBUG: scanBarcode method NOT accessible');
        }
    } catch (error) {
        console.error('💥 DEBUG: Failed to initialize barcode scanner:', error);
    }
});