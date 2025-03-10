/**
 * Container-håndtering for laboratoriesystem
 * Modul der håndterer container-funktionalitet og placering af multiple pakker
 */

// Container-modul med namespace for at undgå konflikter med global scope
const ContainerModule = (function() {
    // Private variabler
    let containers = [];
    let locations = [];
    
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
    
    function _loadExistingContainers(packageNumber) {
        const containerSelect = document.querySelector(`.existing-container-id[data-package="${packageNumber}"]`);
        if (!containerSelect) return;
        
        // Sæt "loading" tilstand
        containerSelect.innerHTML = '<option value="">Indlæser containere...</option>';
        
        // Hent containere fra API
        fetch('/api/containers/available')
            .then(response => response.json())
            .then(data => {
                if (data.containers && data.containers.length > 0) {
                    containers = data.containers;
                    containerSelect.innerHTML = '<option value="">Vælg container</option>';
                    
                    data.containers.forEach(container => {
                        const option = document.createElement('option');
                        option.value = container.ContainerID;
                        option.textContent = `Container ${container.ContainerID}: ${container.Description}`;
                        containerSelect.appendChild(option);
                    });
                } else {
                    containerSelect.innerHTML = '<option value="">Ingen containere tilgængelige</option>';
                }
            })
            .catch(error => {
                console.error('Error loading containers:', error);
                containerSelect.innerHTML = '<option value="">Fejl ved indlæsning af containere</option>';
            });
    }
    
    // Public API
    return {
        /**
         * Initialiserer multi-pakke container håndtering
         * @param {Object} config Konfiguration for container-modulet
         */
        init: function(config = {}) {
            console.log('Container-modul initialiseret');
            
            const differentLocationsCheckbox = document.getElementById('differentLocations');
            const packageLocationsContainer = document.getElementById('packageLocations');
            const packageCountInput = document.querySelector('[name="packageCount"]');
            
            // Håndter forskellige lokationer checkbox
            if (differentLocationsCheckbox && packageLocationsContainer) {
                differentLocationsCheckbox.addEventListener('change', function() {
                    packageLocationsContainer.classList.toggle('d-none', !this.checked);
                    
                    // Opdater pakkelokationer hvis checkboxen er markeret
                    if (this.checked) {
                        ContainerModule.updatePackageLocations();
                    }
                });
            }
            
            // Opdater pakkelokations UI ved ændring af antal pakker
            if (packageCountInput) {
                packageCountInput.addEventListener('input', function() {
                    if (differentLocationsCheckbox && differentLocationsCheckbox.checked) {
                        ContainerModule.updatePackageLocations();
                    }
                });
            }
        },
        
        /**
         * Opdaterer UI for pakkelokationer baseret på aktuelt antal pakker
         */
        updatePackageLocations: function() {
            const packageCountInput = document.querySelector('[name="packageCount"]');
            const packageCount = parseInt(packageCountInput.value) || 0;
            const locationsContainer = document.querySelector('.package-locations-container');
            
            if (!locationsContainer) return;
            
            locationsContainer.innerHTML = '';
            
            // Opret en lokalitetsvælger for hver pakke
            for (let i = 0; i < packageCount; i++) {
                const packageNumber = i + 1;
                
                const packageLocationDiv = document.createElement('div');
                packageLocationDiv.className = 'card mb-2';
                
                packageLocationDiv.innerHTML = `
                    <div class="card-body">
                        <h6 class="card-title">Pakke ${packageNumber}</h6>
                        <div class="form-group">
                            <label>Vælg placering for pakke ${packageNumber}</label>
                            <select class="form-control package-location" data-package="${packageNumber}">
                                <option value="">Vælg lagerplads</option>
                                ${_generateLocationOptions()}
                            </select>
                        </div>
                        <div class="mt-2">
                            <div class="form-check">
                                <input class="form-check-input package-has-container" type="checkbox" id="package${packageNumber}HasContainer" data-package="${packageNumber}">
                                <label class="form-check-label" for="package${packageNumber}HasContainer">
                                    Tilføj denne pakke til en container
                                </label>
                            </div>
                            <div class="container-options d-none" id="package${packageNumber}ContainerOptions">
                                <div class="card-body bg-light mt-2">
                                    <div class="form-group">
                                        <select class="form-control container-selection" data-package="${packageNumber}">
                                            <option value="new">Opret ny container</option>
                                            <option value="existing">Vælg eksisterende container</option>
                                        </select>
                                    </div>
                                    <div class="new-container-fields" data-package="${packageNumber}">
                                        <div class="form-group mt-2">
                                            <label>Container type</label>
                                            <input type="text" class="form-control new-container-description" placeholder="f.eks. 'Rød plastboks'" data-package="${packageNumber}">
                                        </div>
                                    </div>
                                    <div class="existing-container-fields d-none" data-package="${packageNumber}">
                                        <div class="form-group mt-2">
                                            <label>Vælg eksisterende container</label>
                                            <select class="form-control existing-container-id" data-package="${packageNumber}">
                                                <option value="">Indlæser containere...</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                locationsContainer.appendChild(packageLocationDiv);
            }
            
            // Tilføj event listeners til container checkboxes
            document.querySelectorAll('.package-has-container').forEach(checkbox => {
                checkbox.addEventListener('change', function() {
                    const packageNumber = this.getAttribute('data-package');
                    const containerOptions = document.getElementById(`package${packageNumber}ContainerOptions`);
                    
                    if (containerOptions) {
                        containerOptions.classList.toggle('d-none', !this.checked);
                    }
                    
                    // Hvis markeret, indlæs eksisterende containere
                    if (this.checked) {
                        _loadExistingContainers(packageNumber);
                    }
                });
            });
            
            // Tilføj event listeners til container type selectors
            document.querySelectorAll('.container-selection').forEach(select => {
                select.addEventListener('change', function() {
                    const packageNumber = this.getAttribute('data-package');
                    const newFields = document.querySelector(`.new-container-fields[data-package="${packageNumber}"]`);
                    const existingFields = document.querySelector(`.existing-container-fields[data-package="${packageNumber}"]`);
                    
                    if (this.value === 'new') {
                        if (newFields) newFields.classList.remove('d-none');
                        if (existingFields) existingFields.classList.add('d-none');
                    } else {
                        if (newFields) newFields.classList.add('d-none');
                        if (existingFields) existingFields.classList.remove('d-none');
                    }
                });
            });
        },
        
        /**
         * Indsamler container- og lokationsdata fra UI
         * @returns {Object} Indsamlede data om pakker, lokationer og containere
         */
        collectPackageData: function() {
            const differentLocations = document.getElementById('differentLocations')?.checked || false;
            let packageData = {
                differentLocations: differentLocations,
                packageLocations: []
            };
            
            // Hvis multiple lokationer er markeret, indsaml data fra hver pakkelokation
            if (differentLocations) {
                document.querySelectorAll('.package-location').forEach(locationSelect => {
                    const packageNumber = locationSelect.getAttribute('data-package');
                    const locationId = locationSelect.value;
                    
                    // Find ud af om denne pakke har en container
                    const hasContainer = document.querySelector(`.package-has-container[data-package="${packageNumber}"]`)?.checked || false;
                    
                    let containerData = null;
                    if (hasContainer) {
                        const containerType = document.querySelector(`.container-selection[data-package="${packageNumber}"]`).value;
                        
                        if (containerType === 'new') {
                            containerData = {
                                type: 'new',
                                description: document.querySelector(`.new-container-description[data-package="${packageNumber}"]`).value
                            };
                        } else {
                            containerData = {
                                type: 'existing',
                                containerId: document.querySelector(`.existing-container-id[data-package="${packageNumber}"]`).value
                            };
                        }
                    }
                    
                    packageData.packageLocations.push({
                        packageNumber: packageNumber,
                        locationId: locationId,
                        hasContainer: hasContainer,
                        containerData: containerData
                    });
                });
            }
            
            return packageData;
        },
        
        /**
         * Validerer container- og lokationsdata
         * @returns {boolean} True hvis alle data er gyldige
         */
        validatePackageData: function() {
            const differentLocations = document.getElementById('differentLocations')?.checked || false;
            
            if (!differentLocations) return true;
            
            let isValid = true;
            
            document.querySelectorAll('.package-location').forEach(locationSelect => {
                if (!locationSelect.value) {
                    locationSelect.classList.add('field-error');
                    isValid = false;
                } else {
                    locationSelect.classList.remove('field-error');
                }
            });
            
            // Valider containerdata for pakker med containere
            document.querySelectorAll('.package-has-container:checked').forEach(checkbox => {
                const packageNumber = checkbox.getAttribute('data-package');
                const containerType = document.querySelector(`.container-selection[data-package="${packageNumber}"]`).value;
                
                if (containerType === 'new') {
                    const description = document.querySelector(`.new-container-description[data-package="${packageNumber}"]`);
                    if (!description.value.trim()) {
                        description.classList.add('field-error');
                        isValid = false;
                    } else {
                        description.classList.remove('field-error');
                    }
                } else {
                    const containerId = document.querySelector(`.existing-container-id[data-package="${packageNumber}"]`);
                    if (!containerId.value) {
                        containerId.classList.add('field-error');
                        isValid = false;
                    } else {
                        containerId.classList.remove('field-error');
                    }
                }
            });
            
            if (!isValid) {
                showErrorMessage('Udfyld alle felter for pakkelokationer og containere');
            }
            
            return isValid;
        },
        
        /**
         * Nulstiller container-modul data og UI
         */
        reset: function() {
            const packageLocationsContainer = document.querySelector('.package-locations-container');
            if (packageLocationsContainer) {
                packageLocationsContainer.innerHTML = '';
            }
            
            const differentLocationsCheckbox = document.getElementById('differentLocations');
            if (differentLocationsCheckbox) {
                differentLocationsCheckbox.checked = false;
            }
            
            const packageLocations = document.getElementById('packageLocations');
            if (packageLocations) {
                packageLocations.classList.add('d-none');
            }
        }
    };
})();