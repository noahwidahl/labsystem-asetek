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
        # Generate a timestamp-based test number if not using the predefined ones
        current_time = datetime.now().strftime("%y%m%d%H%M")
        test_number = f"T{current_time}"
        
        # Use the input directly as the test name
        test_name = f"{test_type} Test"
        
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
        try:
            # Handle potential None values safely
            date_str = None
            if self.created_date:
                try:
                    date_str = self.created_date.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    print(f"Date formatting error: {e}, using string representation instead")
                    date_str = str(self.created_date)
            
            # Print debug info about samples
            print(f"Samples type: {type(self.samples)}, value: {self.samples}")
            
            return {
                'TestID': self.id,
                'TestNo': self.test_no,
                'TestName': self.test_name,
                'Description': self.description,
                'CreatedDate': date_str,
                'UserID': self.user_id,
                'Status': self.status,
                'Samples': self.samples or []  # Ensure samples is never None
            }
        except Exception as e:
            print(f"Error in Test.to_dict(): {e}")
            # Return minimal dict if conversion fails
            return {
                'TestID': str(self.id) if self.id else None,
                'TestNo': str(self.test_no) if self.test_no else None,
                'Error': f"Failed to convert test to dictionary: {str(e)}"
            }