/**
 * History page functionality
 */

class HistoryManager {
    constructor() {
        this.currentPage = 1;
        this.itemsPerPage = 20;
        this.allItems = [];
        this.filteredItems = [];
        this.searchInput = null;
        this.actionFilter = null;
        this.clearFiltersBtn = null;
        this.resultsInfo = null;
        
        this.init();
    }

    init() {
        // Initialize elements
        this.searchInput = document.getElementById('searchInput');
        this.actionFilter = document.getElementById('actionFilter');
        this.clearFiltersBtn = document.getElementById('clearFilters');
        this.resultsInfo = document.getElementById('resultsInfo');
        
        // Get all custody items
        this.allItems = Array.from(document.querySelectorAll('.custody-item'));
        this.filteredItems = [...this.allItems];
        
        // Initialize tooltips
        this.initTooltips();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Set up pagination
        this.setupPagination();
        
        // Initial pagination display
        this.updatePagination();
        
        console.log(`History manager initialized with ${this.allItems.length} items`);
    }

    initTooltips() {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    setupEventListeners() {
        // Search and filter functionality
        if (this.searchInput) {
            this.searchInput.addEventListener('input', () => this.filterItems());
        }
        
        if (this.actionFilter) {
            this.actionFilter.addEventListener('change', () => this.filterItems());
        }
        
        if (this.clearFiltersBtn) {
            this.clearFiltersBtn.addEventListener('click', () => this.clearFilters());
        }

        // Details modal functionality
        this.setupDetailsModal();

        // Export functionality
        this.setupExport();
    }

    setupDetailsModal() {
        document.querySelectorAll('.btn-details').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const logId = e.currentTarget.getAttribute('data-log-id');
                this.loadHistoryDetails(logId);
            });
        });
    }

    setupExport() {
        const exportBtn = document.getElementById('exportCsv');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                // Get current filter state
                const searchTerm = this.searchInput ? this.searchInput.value : '';
                const actionType = this.actionFilter ? this.actionFilter.value : '';
                
                // Build query parameters for export
                const params = new URLSearchParams();
                if (searchTerm) params.append('search', searchTerm);
                if (actionType) params.append('action', actionType);
                
                // Redirect to export endpoint with current filters
                window.location.href = `/api/history/export?${params.toString()}`;
            });
        }
    }

    filterItems() {
        const searchTerm = this.searchInput ? this.searchInput.value.toLowerCase().trim() : '';
        const selectedAction = this.actionFilter ? this.actionFilter.value : '';
        
        this.filteredItems = this.allItems.filter(item => {
            let showItem = true;
            
            // Check search term
            if (searchTerm) {
                const sampleDesc = (item.dataset.sample || '').toLowerCase();
                const notes = (item.dataset.notes || '').toLowerCase();
                const description = (item.dataset.description || '').toLowerCase();
                const partNumber = (item.dataset.partnumber || '').toLowerCase();
                const actionType = (item.dataset.action || '').toLowerCase();
                
                const matchesSearch = sampleDesc.includes(searchTerm) || 
                                    notes.includes(searchTerm) || 
                                    description.includes(searchTerm) || 
                                    partNumber.includes(searchTerm) ||
                                    actionType.includes(searchTerm);
                
                if (!matchesSearch) {
                    showItem = false;
                }
            }
            
            // Check action filter
            if (selectedAction && item.dataset.action !== selectedAction) {
                showItem = false;
            }
            
            return showItem;
        });
        
        // Reset to first page when filtering
        this.currentPage = 1;
        this.updatePagination();
        this.updateResultsInfo(searchTerm, selectedAction);
    }

    updateResultsInfo(searchTerm, selectedAction) {
        if (!this.resultsInfo) return;
        
        const totalItems = this.allItems.length;
        const filteredCount = this.filteredItems.length;
        const currentPageItems = Math.min(this.itemsPerPage, filteredCount);
        
        if (searchTerm || selectedAction) {
            let filterText = '';
            if (searchTerm) filterText += ` search: "${searchTerm}"`;
            if (selectedAction) filterText += ` action: "${selectedAction}"`;
            this.resultsInfo.innerHTML = `Found ${filteredCount} of ${totalItems} records${filterText}`;
        } else {
            this.resultsInfo.innerHTML = `Showing ${currentPageItems} of ${totalItems} most recent history records (page ${this.currentPage}). Use search and filter to narrow results.`;
        }
    }

    clearFilters() {
        if (this.searchInput) this.searchInput.value = '';
        if (this.actionFilter) this.actionFilter.value = '';
        this.filterItems();
    }

    setupPagination() {
        // Create pagination controls
        const paginationContainer = document.createElement('div');
        paginationContainer.className = 'history-pagination';
        paginationContainer.innerHTML = `
            <div class="pagination-info">
                <span id="paginationInfo"></span>
            </div>
            <div class="pagination-controls">
                <button id="prevPageBtn" class="btn btn-outline-secondary btn-sm" disabled>
                    <i class="fas fa-chevron-left"></i> Previous
                </button>
                <button id="nextPageBtn" class="btn btn-outline-secondary btn-sm">
                    Next <i class="fas fa-chevron-right"></i>
                </button>
            </div>
        `;
        
        // Insert pagination after the chain of custody container
        const chainContainer = document.querySelector('.chain-of-custody-container');
        if (chainContainer) {
            chainContainer.parentNode.insertBefore(paginationContainer, chainContainer.nextSibling);
            
            // Set up pagination event listeners
            const prevBtn = document.getElementById('prevPageBtn');
            const nextBtn = document.getElementById('nextPageBtn');
            
            if (prevBtn) {
                prevBtn.addEventListener('click', () => {
                    if (this.currentPage > 1) {
                        this.currentPage--;
                        this.updatePagination();
                    }
                });
            }
            
            if (nextBtn) {
                nextBtn.addEventListener('click', () => {
                    const totalPages = Math.ceil(this.filteredItems.length / this.itemsPerPage);
                    if (this.currentPage < totalPages) {
                        this.currentPage++;
                        this.updatePagination();
                    }
                });
            }
        }
    }

    updatePagination() {
        const totalItems = this.filteredItems.length;
        const totalPages = Math.ceil(totalItems / this.itemsPerPage);
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = Math.min(startIndex + this.itemsPerPage, totalItems);
        
        // Hide all items first
        this.allItems.forEach(item => {
            item.style.display = 'none';
        });
        
        // Show only items for current page
        const itemsToShow = this.filteredItems.slice(startIndex, endIndex);
        itemsToShow.forEach(item => {
            item.style.display = 'flex'; // Use flex to maintain layout
        });
        
        // Update pagination info
        const paginationInfo = document.getElementById('paginationInfo');
        if (paginationInfo) {
            if (totalItems === 0) {
                paginationInfo.textContent = 'No records found';
            } else {
                paginationInfo.textContent = `Showing ${startIndex + 1}-${endIndex} of ${totalItems} records (Page ${this.currentPage} of ${totalPages})`;
            }
        }
        
        // Update pagination buttons
        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');
        
        if (prevBtn) {
            prevBtn.disabled = this.currentPage <= 1;
        }
        
        if (nextBtn) {
            nextBtn.disabled = this.currentPage >= totalPages;
        }
        
        // Hide pagination if no items or only one page
        const paginationContainer = document.querySelector('.history-pagination');
        if (paginationContainer) {
            if (totalPages <= 1) {
                paginationContainer.style.display = 'none';
            } else {
                paginationContainer.style.display = 'flex';
            }
        }
    }

    loadHistoryDetails(logId) {
        // Show spinner in modal while loading
        const modal = document.getElementById('historyDetailsModal');
        const modalActionType = document.getElementById('modal-action-type');
        const modalTimestamp = document.getElementById('modal-timestamp');
        
        if (modalActionType) {
            modalActionType.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div>';
        }
        if (modalTimestamp) {
            modalTimestamp.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div>';
        }
        
        // Show the modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // Make AJAX request to get detailed information
        fetch(`/api/history/details/${logId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.populateModalWithData(data);
                } else {
                    this.showModalError(data.error || 'Failed to load details');
                }
            })
            .catch(error => {
                console.error('Error loading details:', error);
                this.showModalError('Failed to load details');
            });
    }

    populateModalWithData(data) {
        // Fill modal with data
        const elements = {
            'modal-action-type': data.details.ActionType,
            'modal-timestamp': data.details.Timestamp,
            'modal-user': data.details.UserName,
            'modal-notes': data.details.Notes,
            'modal-sample-id': data.details.SampleDesc,
            'modal-sample-desc': data.sample_info?.Description || 'N/A',
            'modal-sample-status': data.sample_info?.Status || 'N/A',
            'modal-sample-location': data.sample_info?.Location || 'N/A'
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });

        // Update the View Sample button
        const viewSampleBtn = document.getElementById('viewSampleBtn');
        if (viewSampleBtn) {
            if (data.sample_info?.SampleID) {
                viewSampleBtn.style.display = '';
                viewSampleBtn.onclick = () => {
                    window.location.href = `/samples/${data.sample_info.SampleID}`;
                };
            } else {
                viewSampleBtn.style.display = 'none';
            }
        }

        // Fill sample history table
        this.populateHistoryTable(data.sample_history);
    }

    populateHistoryTable(sampleHistory) {
        const historyTable = document.getElementById('modal-sample-history');
        if (!historyTable) return;
        
        historyTable.innerHTML = '';
        
        if (sampleHistory && sampleHistory.length > 0) {
            sampleHistory.forEach(historyItem => {
                const row = document.createElement('tr');
                
                const cells = [
                    historyItem.Timestamp,
                    `<span class="badge ${historyItem.ActionType.toLowerCase()}">${historyItem.ActionType}</span>`,
                    historyItem.UserName,
                    historyItem.Notes
                ];
                
                cells.forEach((cellContent, index) => {
                    const cell = document.createElement('td');
                    if (index === 1) { // Action type cell with badge
                        cell.innerHTML = cellContent;
                    } else {
                        cell.textContent = cellContent;
                    }
                    row.appendChild(cell);
                });
                
                historyTable.appendChild(row);
            });
        } else {
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 4;
            cell.textContent = 'No history available for this sample';
            cell.className = 'text-center';
            row.appendChild(cell);
            historyTable.appendChild(row);
        }
    }

    showModalError(message) {
        const modalActionType = document.getElementById('modal-action-type');
        const modalNotes = document.getElementById('modal-notes');
        
        if (modalActionType) modalActionType.textContent = 'Error';
        if (modalNotes) modalNotes.textContent = message;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new HistoryManager();
});