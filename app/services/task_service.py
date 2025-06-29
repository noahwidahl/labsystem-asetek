from datetime import datetime
from app.models.task import Task, TaskSample
from app.utils.db import DatabaseManager
import json

class TaskService:
    def __init__(self, mysql):
        self.mysql = mysql
        self.db = DatabaseManager(mysql)
    
    def get_all_tasks(self, status_filter=None, assigned_filter=None, search_term=None):
        """
        Get all tasks with optional filtering.
        """
        query = """
            SELECT 
                t.TaskID, t.TaskNumber, t.TaskName, t.Description, t.ProjectCode,
                t.Status, t.Priority, t.StartDate, t.EndDate, t.EstimatedDuration,
                t.CreatedDate, t.CreatedBy, t.AssignedTo, t.TeamMembers, t.Notes,
                creator.Name as CreatedByName,
                assignee.Name as AssignedToName,
                COALESCE(sample_counts.total_samples, 0) as total_samples,
                COALESCE(test_counts.total_tests, 0) as total_tests
            FROM task t
            LEFT JOIN user creator ON t.CreatedBy = creator.UserID
            LEFT JOIN user assignee ON t.AssignedTo = assignee.UserID
            LEFT JOIN (
                SELECT TaskID, COUNT(DISTINCT SampleID) as total_samples
                FROM (
                    SELECT TaskID, SampleID FROM sample WHERE TaskID IS NOT NULL
                    UNION
                    SELECT TaskID, SampleID FROM tasksample
                ) all_task_samples
                GROUP BY TaskID
            ) sample_counts ON t.TaskID = sample_counts.TaskID
            LEFT JOIN (
                SELECT TaskID, COUNT(*) as total_tests
                FROM test 
                WHERE TaskID IS NOT NULL
                GROUP BY TaskID
            ) test_counts ON t.TaskID = test_counts.TaskID
        """
        
        conditions = []
        params = []
        
        if status_filter:
            conditions.append("t.Status = %s")
            params.append(status_filter)
        
        if assigned_filter:
            conditions.append("t.AssignedTo = %s")
            params.append(assigned_filter)
        
        if search_term:
            conditions.append("""
                (t.TaskNumber LIKE %s OR t.TaskName LIKE %s OR t.Description LIKE %s)
            """)
            search_param = f"%{search_term}%"
            params.extend([search_param, search_param, search_param])
        
        # Always exclude completed tasks unless specifically requested
        if not status_filter or status_filter != 'Completed':
            conditions.append("t.Status != 'Completed'")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY t.CreatedDate DESC"
        
        result, _ = self.db.execute_query(query, params)
        
        print(f"DEBUG: Query returned {len(result)} tasks")
        for i, row in enumerate(result):
            print(f"DEBUG: Task {i+1} - ID: {row[0]}, Samples: {row[17] if len(row) > 17 else 'N/A'}, Tests: {row[18] if len(row) > 18 else 'N/A'}")
        
        tasks = []
        for row in result:
            # Parse team members JSON
            team_members = []
            if row[13]:  # TeamMembers field
                try:
                    team_members = json.loads(row[13])
                except:
                    team_members = []
            
            # Create task with basic data (first 15 columns)
            row_with_parsed_json = list(row[:15])
            row_with_parsed_json[13] = team_members
            
            task = Task.from_db_row(row_with_parsed_json)
            
            # Add user names and counts from extended query
            task.created_by_name = row[15] if len(row) > 15 else None
            task.assigned_to_name = row[16] if len(row) > 16 else None
            task.total_samples = row[17] if len(row) > 17 else 0
            task.total_tests = row[18] if len(row) > 18 else 0
            
            tasks.append(task)
        
        return tasks
    
    def get_task_by_id(self, task_id):
        """
        Get a specific task by ID.
        """
        query = """
            SELECT 
                t.TaskID, t.TaskNumber, t.TaskName, t.Description, t.ProjectCode,
                t.Status, t.Priority, t.StartDate, t.EndDate, t.EstimatedDuration,
                t.CreatedDate, t.CreatedBy, t.AssignedTo, t.TeamMembers, t.Notes,
                creator.Name as CreatedByName,
                assignee.Name as AssignedToName,
                COALESCE(sample_counts.total_samples, 0) as total_samples,
                COALESCE(test_counts.total_tests, 0) as total_tests
            FROM task t
            LEFT JOIN user creator ON t.CreatedBy = creator.UserID
            LEFT JOIN user assignee ON t.AssignedTo = assignee.UserID
            LEFT JOIN (
                SELECT TaskID, COUNT(DISTINCT SampleID) as total_samples
                FROM (
                    SELECT TaskID, SampleID FROM sample WHERE TaskID IS NOT NULL
                    UNION
                    SELECT TaskID, SampleID FROM tasksample
                ) all_task_samples
                GROUP BY TaskID
            ) sample_counts ON t.TaskID = sample_counts.TaskID
            LEFT JOIN (
                SELECT TaskID, COUNT(*) as total_tests
                FROM test 
                WHERE TaskID IS NOT NULL
                GROUP BY TaskID
            ) test_counts ON t.TaskID = test_counts.TaskID
            WHERE t.TaskID = %s
        """
        
        result, _ = self.db.execute_query(query, (task_id,))
        
        if not result:
            return None
        
        row = result[0]
        # Parse team members JSON
        team_members = []
        if row[13]:
            try:
                team_members = json.loads(row[13])
            except:
                team_members = []
        
        # Create task with basic data (first 15 columns)
        row_with_parsed_json = list(row[:15])
        row_with_parsed_json[13] = team_members
        
        task = Task.from_db_row(row_with_parsed_json)
        
        # Add user names and counts from extended query
        task.created_by_name = row[15] if len(row) > 15 else None
        task.assigned_to_name = row[16] if len(row) > 16 else None
        task.total_samples = row[17] if len(row) > 17 else 0
        task.total_tests = row[18] if len(row) > 18 else 0
        
        return task
    
    def get_task_statistics(self):
        """
        Get task statistics for dashboard.
        """
        query = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN Status = 'Planning' THEN 1 ELSE 0 END) as planning,
                SUM(CASE WHEN Status = 'Active' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN Status = 'On Hold' THEN 1 ELSE 0 END) as on_hold,
                SUM(CASE WHEN Status = 'Completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN Status = 'Cancelled' THEN 1 ELSE 0 END) as cancelled
            FROM task
        """
        
        result, _ = self.db.execute_query(query)
        
        if result:
            row = result[0]
            return {
                'total': row[0] or 0,
                'planning': row[1] or 0,
                'active': row[2] or 0,
                'on_hold': row[3] or 0,
                'completed': row[4] or 0,
                'cancelled': row[5] or 0
            }
        
        return {
            'total': 0,
            'planning': 0,
            'active': 0,
            'on_hold': 0,
            'completed': 0,
            'cancelled': 0
        }
    
    def create_task(self, task_data, user_id):
        """
        Create a new task.
        """
        task = Task.from_dict(task_data)
        task.created_by = user_id
        
        # Generate task number if not provided
        if not task.task_number or not task.task_number.strip():
            task.task_number = self._generate_task_number()
        
        # Validate task data
        validation = task.validate()
        if not validation['valid']:
            return {
                'success': False,
                'errors': validation['errors']
            }
        
        try:
            # Check if task number already exists
            existing_query = "SELECT TaskID FROM task WHERE TaskNumber = %s"
            existing_result, _ = self.db.execute_query(existing_query, (task.task_number,))
            
            if existing_result:
                return {
                    'success': False,
                    'error': f'Task number {task.task_number} already exists'
                }
            
            # Insert new task
            insert_query = """
                INSERT INTO task (
                    TaskNumber, TaskName, Description, ProjectCode, Status, Priority,
                    StartDate, EndDate, EstimatedDuration, CreatedBy, AssignedTo, TeamMembers, Notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Convert team members to JSON
            team_members_json = json.dumps(task.team_members) if task.team_members else None
            
            params = (
                task.task_number, task.task_name, task.description, task.project_code,
                task.status, task.priority, task.start_date, task.end_date,
                task.estimated_duration, task.created_by, task.assigned_to,
                team_members_json, task.notes
            )
            
            result, cursor = self.db.execute_query(insert_query, params, commit=True)
            task_id = cursor
            
            # Log the activity
            self._log_task_activity(task_id, 'Task created', f"Task '{task.task_name}' created", user_id)
            
            return {
                'success': True,
                'task_id': task_id,
                'task_number': task.task_number
            }
            
        except Exception as e:
            print(f"Error creating task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_task(self, task_id, task_data, user_id):
        """
        Update an existing task.
        """
        try:
            # Get existing task
            existing_task = self.get_task_by_id(task_id)
            if not existing_task:
                return {
                    'success': False,
                    'error': 'Task not found'
                }
            
            # For partial updates (like status/priority), update only the provided fields
            # without full validation
            update_fields = []
            update_values = []
            
            allowed_fields = {
                'task_number': 'TaskNumber',
                'task_name': 'TaskName', 
                'description': 'Description',
                'project_code': 'ProjectCode',
                'status': 'Status',
                'priority': 'Priority',
                'start_date': 'StartDate',
                'end_date': 'EndDate',
                'estimated_duration': 'EstimatedDuration',
                'assigned_to': 'AssignedTo',
                'notes': 'Notes'
            }
            
            for field_key, db_column in allowed_fields.items():
                if field_key in task_data:
                    update_fields.append(f"{db_column} = %s")
                    update_values.append(task_data[field_key])
            
            if not update_fields:
                return {
                    'success': False,
                    'error': 'No valid fields to update'
                }
            
            # Check if task number conflicts with other tasks (only if task_number is being updated)
            if 'task_number' in task_data and task_data['task_number'] != existing_task.task_number:
                existing_query = "SELECT TaskID FROM task WHERE TaskNumber = %s AND TaskID != %s"
                existing_result, _ = self.db.execute_query(existing_query, (task_data['task_number'], task_id))
                
                if existing_result:
                    return {
                        'success': False,
                        'error': f'Task number {task_data["task_number"]} already exists'
                    }
            
            # Update task with only the provided fields
            update_query = f"UPDATE task SET {', '.join(update_fields)} WHERE TaskID = %s"
            update_values.append(task_id)
            
            self.db.execute_query(update_query, update_values, commit=True)
            
            # Log the activity with specific attention to status changes
            updated_fields = list(task_data.keys())
            
            # Special handling for status changes
            if 'status' in task_data:
                old_status = existing_task.status
                new_status = task_data['status']
                
                if new_status == 'Completed' and old_status != 'Completed':
                    # Log task completion specifically
                    self._log_task_activity(task_id, 'Task completed', f"Task '{existing_task.task_name}' marked as completed", user_id)
                elif old_status != new_status:
                    # Log status change
                    self._log_task_activity(task_id, 'Task status change', f"Status changed from '{old_status}' to '{new_status}'", user_id)
                
                # If other fields were also updated, log them separately
                other_fields = [f for f in updated_fields if f != 'status']
                if other_fields:
                    self._log_task_activity(task_id, 'Task updated', f"Task fields updated: {', '.join(other_fields)}", user_id)
            else:
                # Regular update log
                self._log_task_activity(task_id, 'Task updated', f"Task fields updated: {', '.join(updated_fields)}", user_id)
            
            return {
                'success': True,
                'task_id': task_id
            }
            
        except Exception as e:
            print(f"Error updating task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_task(self, task_id, user_id):
        """
        Delete a task (only if no tests or samples are assigned).
        """
        try:
            # Check if task has associated tests
            test_query = "SELECT COUNT(*) FROM test WHERE TaskID = %s"
            test_result, _ = self.db.execute_query(test_query, (task_id,))
            test_count = test_result[0][0] if test_result else 0
            
            if test_count > 0:
                return {
                    'success': False,
                    'error': f'Cannot delete task: {test_count} tests are assigned to this task'
                }
            
            # Check if task has assigned samples
            sample_query = "SELECT COUNT(*) FROM tasksample WHERE TaskID = %s"
            sample_result, _ = self.db.execute_query(sample_query, (task_id,))
            sample_count = sample_result[0][0] if sample_result else 0
            
            if sample_count > 0:
                return {
                    'success': False,
                    'error': f'Cannot delete task: {sample_count} samples are assigned to this task'
                }
            
            # Get task name for logging
            task = self.get_task_by_id(task_id)
            task_name = task.task_name if task else f"Task {task_id}"
            
            # Delete task
            delete_query = "DELETE FROM task WHERE TaskID = %s"
            self.db.execute_query(delete_query, (task_id,), commit=True)
            
            # Log the activity
            self._log_task_activity(task_id, 'Task deleted', f"Task '{task_name}' deleted", user_id)
            
            return {
                'success': True,
                'message': f'Task {task_name} deleted successfully'
            }
            
        except Exception as e:
            print(f"Error deleting task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_task_overview(self, task_id=None):
        """
        Get task overview with statistics from the view.
        """
        query = """
            SELECT 
                TaskID, TaskNumber, TaskName, Description, Status, Priority,
                StartDate, EndDate, CreatedDate, CreatedBy, AssignedTo,
                total_tests, active_tests, completed_tests,
                total_samples, assigned_samples, consumed_samples,
                progress_percent
            FROM TaskOverviewView
        """
        
        params = []
        if task_id:
            query += " WHERE TaskID = %s"
            params.append(task_id)
        else:
            query += " ORDER BY CreatedDate DESC"
        
        result, _ = self.db.execute_query(query, params)
        
        overviews = []
        for row in result:
            overview = {
                'TaskID': row[0],
                'TaskNumber': row[1],
                'TaskName': row[2],
                'Description': row[3],
                'Status': row[4],
                'Priority': row[5],
                'StartDate': row[6].strftime('%Y-%m-%d') if row[6] else None,
                'EndDate': row[7].strftime('%Y-%m-%d') if row[7] else None,
                'CreatedDate': row[8].strftime('%Y-%m-%d %H:%M:%S') if row[8] else None,
                'CreatedBy': row[9],
                'AssignedTo': row[10],
                'Statistics': {
                    'total_tests': row[11] or 0,
                    'active_tests': row[12] or 0,
                    'completed_tests': row[13] or 0,
                    'total_samples': row[14] or 0,
                    'assigned_samples': row[15] or 0,
                    'consumed_samples': row[16] or 0,
                    'progress_percent': row[17] or 0
                }
            }
            overviews.append(overview)
        
        return overviews[0] if task_id and overviews else overviews
    
    def get_task_tests(self, task_id):
        """
        Get all tests assigned to a task.
        """
        query = """
            SELECT 
                t.TestID, t.TestNo, t.TestName, t.Description as TestDescription, t.Status as TestStatus,
                t.CreatedDate, u.Name as CreatedBy, 
                COALESCE(sample_counts.total_samples, 0) as sample_count
            FROM test t
            LEFT JOIN user u ON t.UserID = u.UserID
            LEFT JOIN (
                SELECT 
                    TestID,
                    COUNT(*) as total_samples
                FROM testsampleusage
                GROUP BY TestID
            ) sample_counts ON t.TestID = sample_counts.TestID
            WHERE t.TaskID = %s
            ORDER BY t.TestNo
        """
        
        result, _ = self.db.execute_query(query, (task_id,))
        
        tests = []
        for row in result:
            test = {
                'TestID': row[0],
                'TestNo': row[1],
                'TestName': row[2],
                'Description': row[3],
                'Status': row[4],
                'CreatedDate': row[5].strftime('%Y-%m-%d %H:%M:%S') if row[5] else None,
                'CreatedBy': row[6],
                'SampleCount': row[7] or 0
            }
            tests.append(test)
        
        return tests
    
    def get_task_samples(self, task_id):
        """
        Get all samples assigned to this task.
        Includes both samples assigned directly during registration (Sample.TaskID) 
        and samples currently being used in tests that belong to this task.
        """
        query = """
            SELECT DISTINCT
                s.SampleID,
                s.Description,
                s.PartNumber,
                s.Status as SampleStatus,
                CASE 
                    WHEN tsu.SampleID IS NOT NULL THEN tsu.Status
                    ELSE 'Available for Task'
                END as UsageStatus,
                COALESCE(tsu.CreatedDate, r.ReceivedDate) as AssignedDate,
                CASE 
                    WHEN tsu.SampleID IS NOT NULL THEN CONCAT('Used in test ', t.TestNo)
                    ELSE 'Available for task assignment'
                END as Purpose,
                COALESCE(tsu.Notes, '') as Notes,
                COALESCE(test_user.Name, owner.Name) as AssignedBy,
                t.TestNo,
                t.TestName,
                tsu.SampleIdentifier,
                tsu.AmountAllocated,
                ss.AmountRemaining
            FROM sample s
            LEFT JOIN reception r ON s.ReceptionID = r.ReceptionID
            LEFT JOIN user owner ON s.OwnerID = owner.UserID
            LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
            LEFT JOIN testsampleusage tsu ON s.SampleID = tsu.SampleID
            LEFT JOIN test t ON tsu.TestID = t.TestID AND t.TaskID = %s
            LEFT JOIN user test_user ON t.UserID = test_user.UserID
            WHERE s.TaskID = %s
            ORDER BY AssignedDate DESC
        """
        
        result, _ = self.db.execute_query(query, (task_id, task_id))
        
        samples = []
        for row in result:
            sample = {
                'SampleID': row[0],
                'SampleIDFormatted': f'SMP-{row[0]}',
                'Description': row[1],
                'PartNumber': row[2] or '',
                'SampleStatus': row[3],
                'UsageStatus': row[4],
                'AssignedDate': row[5].strftime('%Y-%m-%d %H:%M:%S') if row[5] else None,
                'Purpose': row[6] or '',
                'Notes': row[7] or '',
                'AssignedBy': row[8],
                'TestNo': row[9] or '',
                'TestName': row[10] or '',
                'SampleIdentifier': row[11] or '',
                'AmountAllocated': row[12] or 0,
                'AmountRemaining': row[13] or 0
            }
            samples.append(sample)
        
        return samples
    
    def generate_next_test_number(self, task_id):
        """
        Generate the next test number for a task.
        """
        try:
            cursor = self.mysql.connection.cursor()
            cursor.execute("SELECT GetNextTaskTestNumber(%s)", (task_id,))
            result = cursor.fetchone()
            cursor.close()
            
            if result and result[0]:
                return result[0]
            else:
                # Fallback method
                return f"T{task_id}00.1"
                
        except Exception as e:
            print(f"Error generating test number: {e}")
            return f"T{task_id}00.1"
    
    def _generate_task_number(self):
        """
        Generate next available task number in format TSK-XXX.
        """
        query = """
            SELECT TaskNumber FROM task 
            WHERE TaskNumber LIKE 'TSK-%' 
            ORDER BY CAST(SUBSTRING(TaskNumber, 5) AS UNSIGNED) DESC 
            LIMIT 1
        """
        
        result, _ = self.db.execute_query(query)
        
        if result and result[0][0]:
            # Extract number from TSK-XXX format
            last_number = result[0][0]
            try:
                num_part = int(last_number.split('-')[1])
                next_num = num_part + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
        
        return f"TSK-{next_num:03d}"
    
    def _log_task_activity(self, task_id, action_type, notes, user_id):
        """
        Log task activity to history table.
        """
        try:
            log_query = """
                INSERT INTO History (ActionType, Notes, UserID, Timestamp)
                VALUES (%s, %s, %s, %s)
            """
            
            full_notes = f"Task ID {task_id}: {notes}"
            self.db.execute_query(log_query, (action_type, full_notes, user_id, datetime.now()), commit=True)
            
        except Exception as e:
            print(f"Error logging task activity: {e}")