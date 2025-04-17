class Container:
    def __init__(self, id=None, description=None, container_type_id=None, 
                 is_mixed=False, capacity=None, status='Active', location_id=None):
        self.id = id
        self.description = description
        self.container_type_id = container_type_id
        self.is_mixed = is_mixed
        self.capacity = capacity
        self.status = status
        self.location_id = location_id
    
    @classmethod
    def from_dict(cls, data):
        # Debug data to track what values are being provided
        print(f"DEBUG: Container.from_dict() called with: {data}")
        
        # Check for possible location ID field names
        location_id = data.get('locationId') or data.get('containerLocationId') or data.get('storageLocation')
        
        # Log what location ID was found
        print(f"DEBUG: Using location_id: {location_id}")
        
        return cls(
            description=data.get('description'),
            container_type_id=data.get('containerTypeId'),
            is_mixed=data.get('isMixed', False),
            capacity=data.get('capacity'),
            location_id=location_id
        )
    
    @classmethod
    def from_db_row(cls, row):
        return cls(
            id=row[0],
            description=row[1],
            container_type_id=row[2] if len(row) > 2 else None,
            is_mixed=bool(row[3]) if len(row) > 3 else False,
            capacity=row[4] if len(row) > 4 else None,
            status=row[5] if len(row) > 5 else 'Active',
            location_id=row[6] if len(row) > 6 else None
        )
    
    def to_dict(self):
        return {
            'ContainerID': self.id,
            'Description': self.description,
            'ContainerTypeID': self.container_type_id,
            'IsMixed': self.is_mixed,
            'Capacity': self.capacity,
            'Status': self.status,
            'LocationID': self.location_id
        }