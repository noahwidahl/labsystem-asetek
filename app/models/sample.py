from datetime import datetime

class Sample:
    def __init__(self, id=None, description=None, barcode=None, part_number=None, is_unique=False, 
                 type='Standard', status="In Storage", amount=0, unit_id=None, 
                 owner_id=None, reception_id=None, **kwargs):
        self.id = id
        self.description = description
        self.barcode = barcode
        self.part_number = part_number
        self.is_unique = is_unique
        self.type = type
        self.status = status
        self.amount = amount
        self.unit_id = unit_id
        self.owner_id = owner_id
        self.reception_id = reception_id
        
        # Additional fields that might come from joined tables
        self.unit_name = kwargs.get('unit_name')
        self.location_name = kwargs.get('location_name')
        self.received_date = kwargs.get('received_date')
        self.owner_name = kwargs.get('owner_name')
        
        # Add any additional attributes dynamically
        for key, value in kwargs.items():
            if not hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            description=data.get('description'),
            barcode=data.get('barcode'),
            part_number=data.get('partNumber', ''),
            is_unique=data.get('hasSerialNumbers', False),
            type=data.get('sampleType', 'Standard'),
            status="In Storage",
            amount=data.get('totalAmount', 0),
            unit_id=data.get('unit'),
            owner_id=data.get('owner')
        )
    
    @classmethod
    def from_db_row(cls, row):
        # Convert row to dict if we have column names
        if hasattr(row, 'keys'):
            # This is already a dict-like object
            return cls(**row)
            
        # Handle different result formats
        if isinstance(row, dict):
            # Dict format
            return cls(**row)
        elif hasattr(row, '_mapping') or hasattr(row, 'items'):
            # Row proxy or similar
            return cls(**dict(row))
        else:
            # Tuple format - use positional args
            sample = cls(
                id=row[0],
                barcode=row[1] if len(row) > 1 else None,
                part_number=row[2] if len(row) > 2 else None,
                is_unique=bool(row[3]) if len(row) > 3 else False,
                type=row[4] if len(row) > 4 else 'Standard',
                description=row[5] if len(row) > 5 else None,
                status=row[6] if len(row) > 6 else "In Storage",
                amount=row[7] if len(row) > 7 else 0,
                unit_id=row[8] if len(row) > 8 else None,
                owner_id=row[9] if len(row) > 9 else None,
                reception_id=row[10] if len(row) > 10 else None
            )
            
            # Attempt to add joined fields if present
            if len(row) > 11:
                sample.received_date = row[11]
            if len(row) > 12:
                sample.unit_name = row[12]
            if len(row) > 13:
                sample.location_name = row[13]
                
            return sample
    
    def to_dict(self):
        return {
            'SampleID': self.id,
            'SampleIDFormatted': f"SMP-{self.id}" if self.id else None,
            'Description': self.description,
            'Barcode': self.barcode,
            'PartNumber': self.part_number,
            'IsUnique': self.is_unique,
            'Type': self.type,
            'Status': self.status,
            'Amount': self.amount,
            'UnitID': self.unit_id,
            'OwnerID': self.owner_id,
            'ReceptionID': self.reception_id
        }