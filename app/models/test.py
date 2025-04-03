from datetime import datetime

class Test:
    def __init__(self, id=None, test_no=None, test_name=None, description=None, 
                 created_date=None, user_id=None, samples=None, status="Active"):
        self.id = id
        self.test_no = test_no
        self.test_name = test_name
        self.description = description
        self.created_date = created_date or datetime.now()
        self.user_id = user_id
        self.samples = samples or []
        self.status = status   # "Active", "Completed", "Archived"
    
    @classmethod
    def from_dict(cls, data):
        test_type = data.get('type', '')
        test_number = f"T{test_type}"
        
        # Generate test name based on type
        test_name = ""
        if "1234.5" in test_type:
            test_name = "Pressure Test"
        elif "2345.6" in test_type:
            test_name = "Thermal Test"
        elif "3456.7" in test_type:
            test_name = "Durability Test"
        else:
            test_name = f"Test {test_type.upper()}"
        
        return cls(
            test_no=test_number,
            test_name=test_name,
            description=data.get('description', ''),
            user_id=data.get('owner')
        )
    
    @classmethod
    def from_db_row(cls, row):
        return cls(
            id=row[0],
            test_no=row[1],
            test_name=row[2],
            description=row[3] if len(row) > 3 else None,
            created_date=row[4] if len(row) > 4 else None,
            user_id=row[5] if len(row) > 5 else None,
            status=row[6] if len(row) > 6 else "Active"
        )
    
    def to_dict(self):
        return {
            'TestID': self.id,
            'TestNo': self.test_no,
            'TestName': self.test_name,
            'Description': self.description,
            'CreatedDate': self.created_date.strftime('%Y-%m-%d %H:%M:%S') if self.created_date else None,
            'UserID': self.user_id,
            'Status': self.status,
            'Samples': self.samples
        }