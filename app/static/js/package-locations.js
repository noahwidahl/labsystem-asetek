/**
 * Package Locations module to handle different locations for packages
 */
const PackageLocations = (function() {
    // Private variables
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
            console.log("Package Locations initialized");
        },
        
        // Add location for a specific package
        addLocation: function(packageNumber, locationId, locationName) {
            // Remove any existing location for this package
            this.removeLocation(packageNumber);
            
            // Add the new location
            packageLocations.push({
                packageNumber: packageNumber,
                locationId: locationId,
                locationName: locationName
            });
            
            console.log('Added location for package', packageNumber, ':', locationName);
        },
        
        // Remove location based on package number
        removeLocation: function(packageNumber) {
            const index = packageLocations.findIndex(p => p.packageNumber == packageNumber);
            if (index >= 0) {
                packageLocations.splice(index, 1);
                console.log('Removed location for package', packageNumber);
            }
        },
        
        // Remove location based on location name
        removeLocationByName: function(locationName) {
            const index = packageLocations.findIndex(p => p.locationName === locationName);
            if (index >= 0) {
                packageLocations.splice(index, 1);
                console.log('Removed location:', locationName);
            }
        },
        
        // Get all selected locations
        getSelectedLocations: function() {
            return packageLocations;
        },
        
        // Get location for a specific package
        getLocationByPackage: function(packageNumber) {
            return packageLocations.find(p => p.packageNumber == packageNumber);
        },
        
        // Get location with a specific location name
        getLocationByName: function(locationName) {
            return packageLocations.find(p => p.locationName === locationName);
        },
        
        // Reset all package locations
        reset: function() {
            packageLocations = [];
            console.log('Package locations reset');
        },
        
        // Get data for saving to database
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

// Initialize when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    PackageLocations.init();
});