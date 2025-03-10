/**
 * Package Locations modul til at håndtere forskellige lokationer for pakker
 */
const PackageLocations = (function() {
    // Private variabler
    let packageLocations = [];
    
    // Private methods
    function _generateLocationOptions() {
        const locationSelect = document.querySelector('[name="storageLocation"]');
        if (!locationSelect) return '';
        
        let options = '';
        Array.from(locationSelect.options).forEach(option => {
            if (option.value) {
                options += `<option value="${option.value}">${option.textContent}</option>`;
            }
        });
        
        return options;
    }
    
    function _updateLocationsSummary() {
        const summaryContainer = document.querySelector('.package-locations-list');
        if (!summaryContainer) return;
        
        if (packageLocations.length === 0) {
            summaryContainer.innerHTML = '<div class="text-muted">Ingen pakkeplaceringer konfigureret</div>';
            return;
        }
        
        let html = '<ul class="list-group list-group-flush">';
        
        // Sortér efter pakkenummer
        const sortedLocations = [...packageLocations].sort((a, b) => 
            parseInt(a.packageNumber) - parseInt(b.packageNumber));
        
        sortedLocations.forEach(pkg => {
            const locationSelect = document.querySelector(`[name="storageLocation"] option[value="${pkg.locationId}"]`);
            const locationName = locationSelect ? locationSelect.textContent : 'Ukendt placering';
            
            html += `
                <li class="list-group-item py-1 px-2 d-flex justify-content-between align-items-center">
                    <span>Pakke ${pkg.packageNumber}: ${locationName}</span>
                </li>
            `;
        });
        
        html += '</ul>';
        summaryContainer.innerHTML = html;
    }
    
    // Public API
    return {
        init: function() {
            console.log("Package Locations initialiseret");
            
            const differentLocationsCheckbox = document.getElementById('differentLocations');
            const packageCountInput = document.querySelector('[name="packageCount"]');
            const packageLocationsConfig = document.getElementById('packageLocationsConfig');
            const packageLocationsSummary = document.getElementById('packageLocationsSummary');
            const collapseLocationsBtn = document.getElementById('collapseLocationsBtn');
            
            // Håndter checkbox for forskellige lokationer
            if (differentLocationsCheckbox) {
                differentLocationsCheckbox.addEventListener('change', function() {
                    if (this.checked) {
                        packageLocationsConfig.classList.remove('d-none');
                        packageLocationsSummary.classList.remove('d-none');
                        PackageLocations.updateUI();
                    } else {
                        packageLocationsConfig.classList.add('d-none');
                        packageLocationsSummary.classList.add('d-none');
                        packageLocations = [];
                    }
                });
            }
            
            // Håndter klik på collapse-knap
            if (collapseLocationsBtn) {
                collapseLocationsBtn.addEventListener('click', function() {
                    const container = document.getElementById('packageLocationsContainer');
                    const isCollapsed = container.classList.contains('d-none');
                    
                    if (isCollapsed) {
                        container.classList.remove('d-none');
                        this.innerHTML = '<i class="fas fa-chevron-up"></i>';
                    } else {
                        container.classList.add('d-none');
                        this.innerHTML = '<i class="fas fa-chevron-down"></i>';
                    }
                });
            }
            
            // Opdater UI når antal pakker ændres
            if (packageCountInput) {
                packageCountInput.addEventListener('input', function() {
                    if (differentLocationsCheckbox.checked) {
                        PackageLocations.updateUI();
                    }
                });
            }
        },
        
        updateUI: function() {
            const packageCountInput = document.querySelector('[name="packageCount"]');
            const packageCount = parseInt(packageCountInput.value) || 1;
            const container = document.getElementById('packageLocationsContainer');
            
            if (!container) return;
            
            container.innerHTML = '';
            
            for (let i = 0; i < packageCount; i++) {
                const packageNumber = i + 1;
                const existingData = packageLocations.find(p => parseInt(p.packageNumber) === packageNumber);
                
                const row = document.createElement('div');
                row.className = 'mb-3 border-bottom pb-3';
                row.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <h6>Pakke ${packageNumber}</h6>
                    </div>
                    <div class="row">
                        <div class="col-md-12">
                            <div class="form-group">
                                <label>Vælg placering for pakke ${packageNumber}</label>
                                <select class="form-control package-location" data-package="${packageNumber}">
                                    <option value="">Vælg lagerplads</option>
                                    ${_generateLocationOptions()}
                                </select>
                            </div>
                        </div>
                    </div>
                `;
                
                container.appendChild(row);
            }
            
            // Tilføj event listeners til lokationsvalg
            document.querySelectorAll('.package-location').forEach(select => {
                select.addEventListener('change', function() {
                    const packageNumber = this.getAttribute('data-package');
                    const locationId = this.value;
                    
                    // Opdater eller tilføj pakkedata
                    const existingIndex = packageLocations.findIndex(p => p.packageNumber == packageNumber);
                    
                    if (existingIndex >= 0) {
                        packageLocations[existingIndex].locationId = locationId;
                    } else {
                        packageLocations.push({
                            packageNumber: packageNumber,
                            locationId: locationId
                        });
                    }
                    
                    // Opdater opsummering
                    _updateLocationsSummary();
                });
                
                // Genskab tidligere valg
                const packageNumber = select.getAttribute('data-package');
                const existingData = packageLocations.find(p => p.packageNumber == packageNumber);
                
                if (existingData && existingData.locationId) {
                    select.value = existingData.locationId;
                }
            });
            
            // Opdater opsummering
            _updateLocationsSummary();
        },
        
        getData: function() {
            const differentLocationsCheckbox = document.getElementById('differentLocations');
            
            return {
                differentLocations: differentLocationsCheckbox?.checked || false,
                packageLocations: packageLocations
            };
        },
        
        validate: function() {
            const differentLocationsCheckbox = document.getElementById('differentLocations');
            if (!differentLocationsCheckbox?.checked) return true;
            
            const packageCountInput = document.querySelector('[name="packageCount"]');
            const packageCount = parseInt(packageCountInput?.value) || 1;
            
            // Tjek at der er defineret placeringer for alle pakker
            if (packageLocations.length < packageCount) {
                if (typeof showErrorMessage === 'function') {
                    showErrorMessage('Du skal angive placering for alle pakker');
                } else {
                    alert('Du skal angive placering for alle pakker');
                }
                return false;
            }
            
            // Tjek at alle placeringer er valgt
            for (let i = 0; i < packageCount; i++) {
                const packageNumber = i + 1;
                const packageData = packageLocations.find(p => parseInt(p.packageNumber) === packageNumber);
                
                if (!packageData || !packageData.locationId) {
                    if (typeof showErrorMessage === 'function') {
                        showErrorMessage(`Du skal vælge placering for pakke ${packageNumber}`);
                    } else {
                        alert(`Du skal vælge placering for pakke ${packageNumber}`);
                    }
                    return false;
                }
            }
            
            return true;
        },
        
        reset: function() {
            packageLocations = [];
            
            const packageLocationsConfig = document.getElementById('packageLocationsConfig');
            if (packageLocationsConfig) {
                packageLocationsConfig.classList.add('d-none');
            }
            
            const packageLocationsSummary = document.getElementById('packageLocationsSummary');
            if (packageLocationsSummary) {
                packageLocationsSummary.classList.add('d-none');
            }
            
            const differentLocationsCheckbox = document.getElementById('differentLocations');
            if (differentLocationsCheckbox) {
                differentLocationsCheckbox.checked = false;
            }
            
            _updateLocationsSummary();
        }
    };
})();

// Initialisér når dokumentet er indlæst
document.addEventListener('DOMContentLoaded', function() {
    PackageLocations.init();
});