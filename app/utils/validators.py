def validate_sample_data(data):
    """
    Validates data for creating a sample.
    """
    if not data.get('description'):
        return {
            'valid': False,
            'error': 'Description is required',
            'field': 'description'
        }
    
    if not data.get('totalAmount') or int(data.get('totalAmount', 0)) <= 0:
        return {
            'valid': False,
            'error': 'Amount must be greater than 0',
            'field': 'totalAmount'
        }
    
    if not data.get('unit'):
        return {
            'valid': False,
            'error': 'Unit must be selected',
            'field': 'unit'
        }
    
    return {
        'valid': True
    }

def validate_container_data(data):
    """
    Validates data for creating a container.
    """
    if not data.get('description'):
        return {
            'valid': False,
            'error': 'Description is required',
            'field': 'description'
        }
    
    # Location is required
    if not data.get('locationId'):
        return {
            'valid': False,
            'error': 'Storage location is required',
            'field': 'containerLocation'
        }
    
    # Validate location format
    if not str(data.get('locationId')).isdigit():
        return {
            'valid': False,
            'error': 'Location must be a valid location ID',
            'field': 'containerLocation'
        }
    
    # Container type is required - either an existing one or creating a new one
    if not data.get('containerTypeId') and not data.get('newContainerType'):
        return {
            'valid': False,
            'error': 'Container type is required',
            'field': 'containerType'
        }
    
    # Capacity is not required, but if provided it must be a number
    if data.get('capacity') and not str(data.get('capacity')).isdigit():
        return {
            'valid': False, 
            'error': 'Capacity must be a number',
            'field': 'containerCapacity'
        }
        
    # If creating a new container type, capacity is not required for the container
    # as it will use the new type's capacity
    
    # Validate new container type if provided
    if data.get('newContainerType'):
        new_type = data.get('newContainerType')
        
        if not new_type.get('typeName'):
            return {
                'valid': False,
                'error': 'Container type name is required',
                'field': 'newContainerTypeName'
            }
        
        # Validate capacity if provided in new container type
        if new_type.get('capacity') and not str(new_type.get('capacity')).isdigit():
            return {
                'valid': False,
                'error': 'Container type capacity must be a number',
                'field': 'newContainerTypeCapacity'
            }
            
        # If capacity is not provided for the container type, set a default
        if not new_type.get('capacity'):
            new_type['capacity'] = 10  # Default capacity
    
    return {
        'valid': True
    }

def validate_test_data(data):
    """
    Validates data for creating a test.
    """
    if not data.get('type'):
        return {
            'valid': False,
            'error': 'Test type is required',
            'field': 'type'
        }
    
    if not data.get('samples') or len(data.get('samples', [])) == 0:
        return {
            'valid': False,
            'error': 'At least one sample must be selected',
            'field': 'samples'
        }
    
    return {
        'valid': True
    }