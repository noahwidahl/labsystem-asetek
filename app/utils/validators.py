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