from datetime import datetime

class Sample:
    def __init__(self, id=None, description=None, barcode=None, part_number=None, is_unique=False, 
                 type='Standard', status="In Storage", amount=0, unit_id=None, 
                 owner_id=None, reception_id=None):
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
        return cls(
            id=row[0],
            barcode=row[1],
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