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
            
            // Check search term - now searches in all relevant fields
            if (searchTerm) {
                const searchText = (item.dataset.searchtext || '').toLowerCase();
                const notes = (item.dataset.notes || '').toLowerCase();
                const actionType = (item.dataset.action || '').toLowerCase();
                
                const matchesSearch = searchText.includes(searchTerm) || 
                                    notes.includes(searchTerm) || 
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
        const modal = document.getElementById('historyDetailsModal');
        if (!modal) {
            console.error('History details modal not found');
            return;
        }

        // Show loading spinners
        this.showLoadingInModal();
        
        // Show the modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // Make AJAX request to get detailed information
        fetch(`/api/history/details/${logId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    this.populateModalWithData(data);
                } else {
                    this.showModalError(data.error || 'Failed to load details');
                }
            })
            .catch(error => {
                console.error('Error loading details:', error);
                this.showModalError(`Failed to load details: ${error.message}`);
            });
    }

    showLoadingInModal() {
        const loadingSpinner = '<div class="spinner-border spinner-border-sm" role="status" aria-label="Loading..."></div>';
        const elements = [
            'modal-action-type',
            'modal-timestamp', 
            'modal-user',
            'modal-notes',
            'modal-sample-id',
            'modal-sample-desc',
            'modal-sample-partnumber',
            'modal-sample-status',
            'modal-sample-location'
        ];

        elements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.innerHTML = loadingSpinner;
            }
        });

        // Note: History table loading removed
    }

    populateModalWithData(data) {
        // Fill modal with data - with fallbacks for missing data
        const elements = {
            'modal-action-type': data.details?.ActionType || 'Unknown Action',
            'modal-timestamp': data.details?.Timestamp || 'Unknown Time',
            'modal-user': data.details?.UserName || 'Unknown User',
            'modal-notes': data.details?.Notes || 'No notes available',
            'modal-sample-id': data.sample_info?.SampleID ? `SMP-${data.sample_info.SampleID}` : 'N/A',
            'modal-sample-desc': data.sample_info?.Description || 'No sample information available',
            'modal-sample-partnumber': data.sample_info?.PartNumber || 'No part number',
            'modal-sample-status': data.sample_info?.Status || 'N/A',
            'modal-sample-location': data.sample_info?.Location || 'N/A'
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });

        // Hide the View Sample button for now since the route doesn't exist
        const viewSampleBtn = document.getElementById('viewSampleBtn');
        if (viewSampleBtn) {
            viewSampleBtn.style.display = 'none';
        }

        // Note: Complete sample history section removed - users can search in main history page
    }

    // Method removed - complete sample history section no longer needed

    showModalError(message) {
        // Clear all fields and show error message
        const elements = {
            'modal-action-type': 'Error',
            'modal-timestamp': 'N/A',
            'modal-user': 'N/A',
            'modal-notes': message,
            'modal-sample-id': 'N/A',
            'modal-sample-desc': 'Error loading information',
            'modal-sample-partnumber': 'N/A',
            'modal-sample-status': 'N/A',
            'modal-sample-location': 'N/A'
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });

        // Hide the View Sample button
        const viewSampleBtn = document.getElementById('viewSampleBtn');
        if (viewSampleBtn) {
            viewSampleBtn.style.display = 'none';
        }

        // Note: History table section removed
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new HistoryManager();
});