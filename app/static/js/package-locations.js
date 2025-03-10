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
    
    // Public API
    return {
        init: function() {
            console.log("Package Locations initialiseret");
        },
        
        // Tilføj lokation for en bestemt pakke
        addLocation: function(packageNumber, locationId, locationName) {
            // Fjern eventuel eksisterende lokation for denne pakke
            this.removeLocation(packageNumber);
            
            // Tilføj den nye lokation
            packageLocations.push({
                packageNumber: packageNumber,
                locationId: locationId,
                locationName: locationName
            });
            
            console.log('Tilføjet lokation for pakke', packageNumber, ':', locationName);
        },
        
        // Fjern lokation baseret på pakkenummer
        removeLocation: function(packageNumber) {
            const index = packageLocations.findIndex(p => p.packageNumber == packageNumber);
            if (index >= 0) {
                packageLocations.splice(index, 1);
                console.log('Fjernet lokation for pakke', packageNumber);
            }
        },
        
        // Fjern lokation baseret på lokationsnavn
        removeLocationByName: function(locationName) {
            const index = packageLocations.findIndex(p => p.locationName === locationName);
            if (index >= 0) {
                packageLocations.splice(index, 1);
                console.log('Fjernet lokation:', locationName);
            }
        },
        
        // Hent alle valgte lokationer
        getSelectedLocations: function() {
            return packageLocations;
        },
        
        // Hent lokation for en bestemt pakke
        getLocationByPackage: function(packageNumber) {
            return packageLocations.find(p => p.packageNumber == packageNumber);
        },
        
        // Hent lokation med et bestemt lokationsnavn
        getLocationByName: function(locationName) {
            return packageLocations.find(p => p.locationName === locationName);
        },
        
        // Nulstil alle pakkelokationer
        reset: function() {
            packageLocations = [];
            console.log('Pakkelokationer nulstillet');
        },
        
        // Hent data til gemning i databasen
        getData: function() {
            return {
                differentLocations: true,
                packageLocations: packageLocations.map(p => ({
                    packageNumber: p.packageNumber,
                    locationId: p.locationId,
                    locationName: p.locationName
                }))
            };
        }
    };
})();

// Initialiser når dokumentet er indlæst
document.addEventListener('DOMContentLoaded', function() {
    PackageLocations.init();
});