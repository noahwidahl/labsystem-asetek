from datetime import datetime

class Sample:
    def __init__(self, id=None, description=None, barcode=None, is_unique=False, 
                 type='Standard', status="På lager", amount=0, unit_id=None, 
                 owner_id=None, reception_id=None):
        self.id = id
        self.description = description
        self.barcode = barcode
        self.is_unique = is_unique
        self.type = type
        self.status = status
        self.amount = amount
        self.unit_id = unit_id
        self.owner_id = owner_id
        self.reception_id = reception_id
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            description=data.get('description'),
            barcode=data.get('barcode'),
            is_unique=data.get('hasSerialNumbers', False),
            type=data.get('sampleType', 'Standard'),
            status="På lager",
            amount=data.get('totalAmount', 0),
            unit_id=data.get('unit'),
            owner_id=data.get('owner')
        )
    
    @classmethod
    def from_db_row(cls, row):
        return cls(
            id=row[0],
            barcode=row[1],
            is_unique=bool(row[2]),
            type=row[3] if len(row) > 3 else 'Standard',
            description=row[4] if len(row) > 4 else None,
            status=row[5] if len(row) > 5 else "På lager",
            amount=row[6] if len(row) > 6 else 0,
            unit_id=row[7] if len(row) > 7 else None,
            owner_id=row[8] if len(row) > 8 else None,
            reception_id=row[9] if len(row) > 9 else None
        )
    
    def to_dict(self):
        return {
            'SampleID': self.id,
            'SampleIDFormatted': f"PRV-{self.id}" if self.id else None,
            'Description': self.description,
            'Barcode': self.barcode,
            'IsUnique': self.is_unique,
            'Type': self.type,
            'Status': self.status,
            'Amount': self.amount,
            'UnitID': self.unit_id,
            'OwnerID': self.owner_id,
            'ReceptionID': self.reception_id
        }