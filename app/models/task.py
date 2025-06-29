from datetime import datetime, date

class Task:
    def __init__(self, task_id=None, task_number=None, task_name=None, description=None,
                 project_code=None, status="Planning", priority="Medium", start_date=None,
                 end_date=None, estimated_duration=None, created_date=None, created_by=None,
                 assigned_to=None, team_members=None, notes=None):
        self.task_id = task_id
        self.task_number = task_number
        self.task_name = task_name
        self.description = description
        self.project_code = project_code
        self.status = status
        self.priority = priority
        self.start_date = start_date
        self.end_date = end_date
        self.estimated_duration = estimated_duration
        self.created_date = created_date or datetime.now()
        self.created_by = created_by
        self.assigned_to = assigned_to
        self.team_members = team_members or []
        self.notes = notes
    
    @classmethod
    def from_dict(cls, data):
        """
        Creates a Task object from dictionary data received from the API.
        """
        # Parse dates if provided
        start_date = None
        end_date = None
        
        if data.get('startDate'):
            try:
                start_date = datetime.strptime(data['startDate'], '%Y-%m-%d').date()
            except ValueError:
                pass
        
        if data.get('end_date'):
            try:
                end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            except ValueError:
                pass
        
        if data.get('start_date'):
            try:
                start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            except ValueError:
                pass
        
        return cls(
            task_number=data.get('task_number', ''),
            task_name=data.get('task_name', ''),
            description=data.get('description', ''),
            project_code=data.get('project_code', ''),
            status=data.get('status', 'Planning'),
            priority=data.get('priority', 'Medium'),
            start_date=start_date,
            end_date=end_date,
            estimated_duration=data.get('estimated_duration'),
            created_by=data.get('created_by'),
            assigned_to=data.get('assigned_to'),
            team_members=data.get('team_members', []),
            notes=data.get('notes', '')
        )
    
    @classmethod
    def from_db_row(cls, row):
        """
        Creates a Task object from database row data.
        """
        return cls(
            task_id=row[0],
            task_number=row[1],
            task_name=row[2],
            description=row[3],
            project_code=row[4],
            status=row[5],
            priority=row[6],
            start_date=row[7],
            end_date=row[8],
            estimated_duration=row[9],
            created_date=row[10],
            created_by=row[11],
            assigned_to=row[12],
            team_members=row[13],  # JSON field
            notes=row[14]
        )
    
    def to_dict(self):
        """
        Converts Task object to dictionary for API responses.
        """
        try:
            return {
                'task_id': self.task_id,
                'task_number': self.task_number,
                'task_name': self.task_name,
                'description': self.description,
                'project_code': self.project_code,
                'status': self.status,
                'priority': self.priority,
                'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
                'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
                'estimated_duration': self.estimated_duration,
                'created_date': self.created_date.strftime('%Y-%m-%d %H:%M:%S') if self.created_date else None,
                'created_by': self.created_by,
                'assigned_to': self.assigned_to,
                'assigned_to_name': getattr(self, 'assigned_to_name', None),
                'created_by_name': getattr(self, 'created_by_name', None),
                'team_members': self.team_members,
                'notes': self.notes,
                'completion_percentage': 0,  # Will be calculated by service
                'total_samples': 0,  # Will be calculated by service
                'total_tests': 0  # Will be calculated by service
            }
        except Exception as e:
            print(f"Error in Task.to_dict(): {e}")
            return {
                'task_id': self.task_id,
                'task_number': self.task_number,
                'task_name': self.task_name,
                'error': f"Failed to convert task to dictionary: {str(e)}"
            }
    
    def validate(self):
        """
        Validates task data before saving to database.
        """
        errors = []
        
        # Task number is not required as it can be auto-generated
        
        if not self.task_name or not self.task_name.strip():
            errors.append("Task name is required")
        
        if not self.created_by:
            errors.append("Created by user is required")
        
        if self.status not in ['Planning', 'Active', 'On Hold', 'Completed', 'Archived']:
            errors.append("Invalid status")
        
        if self.priority not in ['Low', 'Medium', 'High', 'Critical']:
            errors.append("Invalid priority")
        
        if self.start_date and self.end_date and self.start_date > self.end_date:
            errors.append("Start date cannot be after end date")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

class TaskSample:
    def __init__(self, task_sample_id=None, task_id=None, sample_id=None,
                 assigned_date=None, assigned_by=None, purpose=None, 
                 status="Assigned", notes=None):
        self.task_sample_id = task_sample_id
        self.task_id = task_id
        self.sample_id = sample_id
        self.assigned_date = assigned_date or datetime.now()
        self.assigned_by = assigned_by
        self.purpose = purpose
        self.status = status
        self.notes = notes
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            task_id=data.get('taskId'),
            sample_id=data.get('sampleId'),
            assigned_by=data.get('assignedBy'),
            purpose=data.get('purpose', ''),
            status=data.get('status', 'Assigned'),
            notes=data.get('notes', '')
        )
    
    @classmethod
    def from_db_row(cls, row):
        return cls(
            task_sample_id=row[0],
            task_id=row[1],
            sample_id=row[2],
            assigned_date=row[3],
            assigned_by=row[4],
            purpose=row[5],
            status=row[6],
            notes=row[7]
        )
    
    def to_dict(self):
        return {
            'TaskSampleID': self.task_sample_id,
            'TaskID': self.task_id,
            'SampleID': self.sample_id,
            'AssignedDate': self.assigned_date.strftime('%Y-%m-%d %H:%M:%S') if self.assigned_date else None,
            'AssignedBy': self.assigned_by,
            'Purpose': self.purpose,
            'Status': self.status,
            'Notes': self.notes
        }