/**
 * Container modul til at håndtere container-funktionalitet på registreringssiden
 */
const ContainerModule = (function() {
    // Private variabler
    let containersEnabled = false;
    
    // Private metoder
    function _updateContainerOptions() {
        const createContainersCheckbox = document.getElementById('createContainers');
        if (!createContainersCheckbox) return;
        
        containersEnabled = createContainersCheckbox.checked;
        
        // Vis eller skjul container-relaterede felter baseret på valget
        const containerFields = document.querySelectorAll('.container-related');
        containerFields.forEach(field => {
            field.classList.toggle('d-none', !containersEnabled);
        });
        
        console.log('Container creation is now:', containersEnabled ? 'enabled' : 'disabled');
    }
    
    // Public API
    return {
        init: function() {
            console.log("Container modul initialiseret");
            
            // Initialiser status baseret på nuværende checkbox-tilstand
            const createContainersCheckbox = document.getElementById('createContainers');
            if (createContainersCheckbox) {
                containersEnabled = createContainersCheckbox.checked;
                
                // Lyt efter ændringer i container-checkboxen
                createContainersCheckbox.addEventListener('change', _updateContainerOptions);
                
                // Kør opdatering første gang for at sætte initial tilstand
                _updateContainerOptions();
            }
        },
        
        // Returner om container-oprettelse er aktiveret
        isEnabled: function() {
            return containersEnabled;
        },
        
        // Tilføj til form data inden indsendelse
        addToFormData: function(formData) {
            if (!formData) return formData;
            
            formData.createContainers = containersEnabled;
            
            // Tilføj eventuelle andre container-relaterede felter her hvis nødvendigt
            
            return formData;
        }
    };
})();