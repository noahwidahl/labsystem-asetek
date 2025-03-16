def validate_sample_data(data):
    """
    Validerer data for oprettelse af en prøve.
    """
    if not data.get('description'):
        return {
            'valid': False,
            'error': 'Beskrivelse er påkrævet',
            'field': 'description'
        }
    
    if not data.get('totalAmount') or int(data.get('totalAmount', 0)) <= 0:
        return {
            'valid': False,
            'error': 'Antal skal være større end 0',
            'field': 'totalAmount'
        }
    
    if not data.get('unit'):
        return {
            'valid': False,
            'error': 'Enhed skal vælges',
            'field': 'unit'
        }
    
    return {
        'valid': True
    }

def validate_container_data(data):
    """
    Validerer data for oprettelse af en container.
    """
    if not data.get('description'):
        return {
            'valid': False,
            'error': 'Beskrivelse er påkrævet',
            'field': 'description'
        }
    
    return {
        'valid': True
    }

def validate_test_data(data):
    """
    Validerer data for oprettelse af en test.
    """
    if not data.get('type'):
        return {
            'valid': False,
            'error': 'Testtype er påkrævet',
            'field': 'type'
        }
    
    if not data.get('samples') or len(data.get('samples', [])) == 0:
        return {
            'valid': False,
            'error': 'Mindst én prøve skal vælges',
            'field': 'samples'
        }
    
    return {
        'valid': True
    }