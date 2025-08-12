from flask import Blueprint, render_template, jsonify, request
from app.utils.mssql_db import mssql_db
from datetime import datetime

task_mssql_bp = Blueprint('task_mssql', __name__)

@task_mssql_bp.route('/tasks')
def tasks_page():
    """
    Render the task management page.
    """
    try:
        # Get users for assignment dropdowns
        users_results = mssql_db.execute_query("""
            SELECT [UserID], [Name] FROM [user] ORDER BY [Name]
        """, fetch_all=True)
        users = [{'UserID': row[0], 'Name': row[1]} for row in users_results]
        
        return render_template('sections/tasks.html', users=users)
    except Exception as e:
        print(f"Error loading tasks page: {e}")
        return render_template('sections/tasks.html', error="Error loading task management page")

@task_mssql_bp.route('/api/tasks', methods=['GET'])
def get_tasks():
    """
    Get all tasks with optional filtering.
    """
    try:
        status_filter = request.args.get('status')
        assigned_filter = request.args.get('assigned_to')
        search_term = request.args.get('search')
        
        # Build base query
        query = """
            SELECT 
                t.[TaskID],
                t.[TaskNumber],
                t.[TaskName],
                t.[Description],
                t.[Status],
                t.[Priority],
                t.[CreatedDate],
                t.[DueDate],
                t.[CompletedDate],
                t.[AssignedToUserID],
                u.[Name] as AssignedToName,
                COUNT(DISTINCT s.[SampleID]) as SampleCount,
                COUNT(DISTINCT te.[TestID]) as TestCount
            FROM [task] t
            LEFT JOIN [user] u ON t.[AssignedToUserID] = u.[UserID]
            LEFT JOIN [sample] s ON t.[TaskID] = s.[TaskID]
            LEFT JOIN [test] te ON t.[TaskID] = te.[TaskID]
        """
        
        conditions = []
        params = []
        
        if status_filter:
            conditions.append("t.[Status] = ?")
            params.append(status_filter)
        
        if assigned_filter:
            conditions.append("t.[AssignedToUserID] = ?")
            params.append(int(assigned_filter))
        
        if search_term:
            conditions.append("(t.[TaskName] LIKE ? OR t.[Description] LIKE ? OR t.[TaskNumber] LIKE ?)")
            search_param = f"%{search_term}%"
            params.extend([search_param, search_param, search_param])
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += """
            GROUP BY t.[TaskID], t.[TaskNumber], t.[TaskName], t.[Description], t.[Status], 
                     t.[Priority], t.[CreatedDate], t.[DueDate], t.[CompletedDate], 
                     t.[AssignedToUserID], u.[Name]
            ORDER BY t.[CreatedDate] DESC
        """
        
        tasks_results = mssql_db.execute_query(query, params, fetch_all=True)
        
        tasks = []
        for row in tasks_results:
            tasks.append({
                'TaskID': row[0],
                'TaskNumber': row[1],
                'TaskName': row[2],
                'Description': row[3],
                'Status': row[4],
                'Priority': row[5],
                'CreatedDate': row[6],
                'DueDate': row[7],
                'CompletedDate': row[8],
                'AssignedToUserID': row[9],
                'AssignedToName': row[10],
                'SampleCount': row[11],
                'TestCount': row[12]
            })
        
        return jsonify({
            'success': True,
            'tasks': tasks,
            'count': len(tasks)
        })
        
    except Exception as e:
        print(f"Error getting tasks: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_mssql_bp.route('/api/tasks', methods=['POST'])
def create_task():
    """
    Create a new task.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        user_id = 1  # TODO: Implement proper user authentication
        
        # Generate task number
        current_year = datetime.now().year
        task_no_result = mssql_db.execute_query("""
            SELECT MAX(CAST(SUBSTRING([TaskNumber], 6, LEN([TaskNumber]) - 5) AS INT)) + 1
            FROM [task] 
            WHERE [TaskNumber] LIKE ?
        """, (f"TASK{current_year}%",), fetch_one=True)
        
        next_number = task_no_result[0] if task_no_result and task_no_result[0] else 1
        task_number = f"TASK{current_year}{next_number:04d}"
        
        # Create task
        result = mssql_db.execute_query("""
            INSERT INTO [task] (
                [TaskNumber], 
                [TaskName], 
                [Description], 
                [Status], 
                [Priority], 
                [CreatedDate], 
                [DueDate], 
                [AssignedToUserID],
                [CreatedByUserID]
            ) 
            OUTPUT INSERTED.TaskID
            VALUES (?, ?, ?, ?, ?, GETDATE(), ?, ?, ?)
        """, (
            task_number,
            data.get('task_name'),
            data.get('description', ''),
            data.get('status', 'Planning'),
            data.get('priority', 'Medium'),
            data.get('due_date'),
            data.get('assigned_to_user_id'),
            user_id
        ), fetch_one=True)
        
        if result:
            task_id = result[0]
            
            # Log activity
            mssql_db.execute_query("""
                INSERT INTO [history] (
                    [Timestamp], 
                    [ActionType], 
                    [UserID], 
                    [Notes]
                )
                VALUES (GETDATE(), 'Task created', ?, ?)
            """, (
                user_id,
                f"Task '{data.get('task_name')}' created with number {task_number}"
            ))
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'task_number': task_number,
                'message': 'Task created successfully'
            }), 201
        else:
            return jsonify({'success': False, 'error': 'Failed to create task'}), 500
        
    except Exception as e:
        print(f"Error creating task: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_mssql_bp.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """
    Get a specific task by ID with samples and tests.
    """
    try:
        # Get task details
        task_result = mssql_db.execute_query("""
            SELECT 
                t.[TaskID],
                t.[TaskNumber],
                t.[TaskName],
                t.[Description],
                t.[Status],
                t.[Priority],
                t.[CreatedDate],
                t.[DueDate],
                t.[CompletedDate],
                t.[AssignedToUserID],
                u.[Name] as AssignedToName,
                cb.[Name] as CreatedByName
            FROM [task] t
            LEFT JOIN [user] u ON t.[AssignedToUserID] = u.[UserID]
            LEFT JOIN [user] cb ON t.[CreatedByUserID] = cb.[UserID]
            WHERE t.[TaskID] = ?
        """, (task_id,), fetch_one=True)
        
        if not task_result:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        task = {
            'TaskID': task_result[0],
            'TaskNumber': task_result[1],
            'TaskName': task_result[2],
            'Description': task_result[3],
            'Status': task_result[4],
            'Priority': task_result[5],
            'CreatedDate': task_result[6],
            'DueDate': task_result[7],
            'CompletedDate': task_result[8],
            'AssignedToUserID': task_result[9],
            'AssignedToName': task_result[10],
            'CreatedByName': task_result[11]
        }
        
        # Get task samples
        samples_results = mssql_db.execute_query("""
            SELECT 
                s.[SampleID],
                s.[Description],
                s.[PartNumber],
                s.[Status],
                s.[Amount],
                CASE
                    WHEN u.[UnitName] IS NULL THEN 'pcs'
                    WHEN LOWER(u.[UnitName]) = 'stk' THEN 'pcs'
                    ELSE u.[UnitName]
                END as UnitName,
                sl.[LocationName]
            FROM [sample] s
            LEFT JOIN [unit] u ON s.[UnitID] = u.[UnitID]
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            WHERE s.[TaskID] = ?
            ORDER BY s.[SampleID]
        """, (task_id,), fetch_all=True)
        
        samples = []
        for row in samples_results:
            samples.append({
                'SampleID': row[0],
                'Description': row[1],
                'PartNumber': row[2],
                'Status': row[3],
                'Amount': row[4],
                'UnitName': row[5],
                'LocationName': row[6] or 'Unknown'
            })
        
        # Get task tests
        tests_results = mssql_db.execute_query("""
            SELECT 
                t.[TestID],
                t.[TestNo],
                t.[TestName],
                t.[Description],
                t.[Status],
                t.[CreatedDate],
                u.[Name] as UserName,
                COUNT(tu.[TestUsageID]) as SampleCount
            FROM [test] t
            LEFT JOIN [user] u ON t.[UserID] = u.[UserID]
            LEFT JOIN [testusage] tu ON t.[TestID] = tu.[TestID]
            WHERE t.[TaskID] = ?
            GROUP BY t.[TestID], t.[TestNo], t.[TestName], t.[Description], t.[Status], t.[CreatedDate], u.[Name]
            ORDER BY t.[CreatedDate] DESC
        """, (task_id,), fetch_all=True)
        
        tests = []
        for row in tests_results:
            tests.append({
                'TestID': row[0],
                'TestNo': row[1],
                'TestName': row[2],
                'Description': row[3],
                'Status': row[4],
                'CreatedDate': row[5],
                'UserName': row[6],
                'SampleCount': row[7]
            })
        
        return jsonify({
            'success': True,
            'task': task,
            'samples': samples,
            'tests': tests
        })
        
    except Exception as e:
        print(f"Error getting task: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_mssql_bp.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """
    Update a task.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        user_id = 1  # TODO: Implement proper user authentication
        
        # Build update query dynamically
        update_fields = []
        params = []
        
        if 'task_name' in data:
            update_fields.append("[TaskName] = ?")
            params.append(data['task_name'])
        
        if 'description' in data:
            update_fields.append("[Description] = ?")
            params.append(data['description'])
        
        if 'status' in data:
            update_fields.append("[Status] = ?")
            params.append(data['status'])
            
            # If completing task, set completion date
            if data['status'] == 'Completed':
                update_fields.append("[CompletedDate] = GETDATE()")
        
        if 'priority' in data:
            update_fields.append("[Priority] = ?")
            params.append(data['priority'])
        
        if 'due_date' in data:
            update_fields.append("[DueDate] = ?")
            params.append(data['due_date'])
        
        if 'assigned_to_user_id' in data:
            update_fields.append("[AssignedToUserID] = ?")
            params.append(data['assigned_to_user_id'])
        
        if not update_fields:
            return jsonify({
                'success': False,
                'error': 'No fields to update'
            }), 400
        
        # Add task_id to params
        params.append(task_id)
        
        # Update task
        update_query = f"""
            UPDATE [task] 
            SET {', '.join(update_fields)}, [LastModified] = GETDATE()
            WHERE [TaskID] = ?
        """
        
        mssql_db.execute_query(update_query, params)
        
        # Log activity
        mssql_db.execute_query("""
            INSERT INTO [history] (
                [Timestamp], 
                [ActionType], 
                [UserID], 
                [Notes]
            )
            VALUES (GETDATE(), 'Task updated', ?, ?)
        """, (
            user_id,
            f"Task {task_id} updated"
        ))
        
        return jsonify({
            'success': True,
            'message': 'Task updated successfully'
        })
        
    except Exception as e:
        print(f"Error updating task: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_mssql_bp.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """
    Delete a task.
    """
    try:
        user_id = 1  # TODO: Implement proper user authentication
        
        # Check if task has samples or tests
        samples_count = mssql_db.execute_query("""
            SELECT COUNT(*) FROM [sample] WHERE [TaskID] = ?
        """, (task_id,), fetch_one=True)
        
        tests_count = mssql_db.execute_query("""
            SELECT COUNT(*) FROM [test] WHERE [TaskID] = ?
        """, (task_id,), fetch_one=True)
        
        if (samples_count and samples_count[0] > 0) or (tests_count and tests_count[0] > 0):
            return jsonify({
                'success': False,
                'error': 'Cannot delete task that has assigned samples or tests'
            }), 400
        
        # Delete task
        mssql_db.execute_query("""
            DELETE FROM [task] WHERE [TaskID] = ?
        """, (task_id,))
        
        # Log activity
        mssql_db.execute_query("""
            INSERT INTO [history] (
                [Timestamp], 
                [ActionType], 
                [UserID], 
                [Notes]
            )
            VALUES (GETDATE(), 'Task deleted', ?, ?)
        """, (
            user_id,
            f"Task {task_id} deleted"
        ))
        
        return jsonify({
            'success': True,
            'message': 'Task deleted successfully'
        })
        
    except Exception as e:
        print(f"Error deleting task: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_mssql_bp.route('/api/tasks/stats')
def get_task_stats():
    """
    Get task statistics for dashboard.
    """
    try:
        stats_result = mssql_db.execute_query("""
            SELECT 
                COUNT(*) as total_tasks,
                SUM(CASE WHEN [Status] = 'Planning' THEN 1 ELSE 0 END) as planning_tasks,
                SUM(CASE WHEN [Status] = 'Active' THEN 1 ELSE 0 END) as active_tasks,
                SUM(CASE WHEN [Status] = 'On Hold' THEN 1 ELSE 0 END) as on_hold_tasks,
                SUM(CASE WHEN [Status] = 'Completed' THEN 1 ELSE 0 END) as completed_tasks,
                SUM(CASE WHEN [Status] = 'Cancelled' THEN 1 ELSE 0 END) as cancelled_tasks,
                SUM(CASE WHEN [DueDate] < CAST(GETDATE() AS DATE) AND [Status] NOT IN ('Completed', 'Cancelled') THEN 1 ELSE 0 END) as overdue_tasks
            FROM [task]
        """, fetch_one=True)
        
        stats = {
            'total_tasks': stats_result[0] or 0,
            'planning_tasks': stats_result[1] or 0,
            'active_tasks': stats_result[2] or 0,
            'on_hold_tasks': stats_result[3] or 0,
            'completed_tasks': stats_result[4] or 0,
            'cancelled_tasks': stats_result[5] or 0,
            'overdue_tasks': stats_result[6] or 0
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        print(f"Error getting task statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_mssql_bp.route('/api/tasks/overview')
def get_tasks_overview():
    """
    Get task overview with statistics.
    """
    try:
        overview_results = mssql_db.execute_query("""
            SELECT 
                t.[TaskID],
                t.[TaskNumber],
                t.[TaskName],
                t.[Status],
                t.[Priority],
                t.[DueDate],
                u.[Name] as AssignedToName,
                COUNT(DISTINCT s.[SampleID]) as SampleCount,
                COUNT(DISTINCT te.[TestID]) as TestCount,
                CASE WHEN t.[DueDate] < CAST(GETDATE() AS DATE) AND t.[Status] NOT IN ('Completed', 'Cancelled') THEN 1 ELSE 0 END as IsOverdue
            FROM [task] t
            LEFT JOIN [user] u ON t.[AssignedToUserID] = u.[UserID]
            LEFT JOIN [sample] s ON t.[TaskID] = s.[TaskID]
            LEFT JOIN [test] te ON t.[TaskID] = te.[TaskID]
            GROUP BY t.[TaskID], t.[TaskNumber], t.[TaskName], t.[Status], t.[Priority], t.[DueDate], u.[Name]
            ORDER BY t.[CreatedDate] DESC
        """, fetch_all=True)
        
        overviews = []
        for row in overview_results:
            overviews.append({
                'TaskID': row[0],
                'TaskNumber': row[1],
                'TaskName': row[2],
                'Status': row[3],
                'Priority': row[4],
                'DueDate': row[5],
                'AssignedToName': row[6],
                'SampleCount': row[7],
                'TestCount': row[8],
                'IsOverdue': row[9] == 1
            })
        
        return jsonify({
            'success': True,
            'tasks': overviews
        })
        
    except Exception as e:
        print(f"Error getting task overview: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_mssql_bp.route('/api/tasks/<int:task_id>/tests')
def get_task_tests(task_id):
    """
    Get all tests assigned to a task.
    """
    try:
        tests_results = mssql_db.execute_query("""
            SELECT 
                t.[TestID],
                t.[TestNo],
                t.[TestName],
                t.[Description],
                t.[Status],
                t.[CreatedDate],
                u.[Name] as UserName,
                COUNT(tu.[TestUsageID]) as SampleCount
            FROM [test] t
            LEFT JOIN [user] u ON t.[UserID] = u.[UserID]
            LEFT JOIN [testusage] tu ON t.[TestID] = tu.[TestID]
            WHERE t.[TaskID] = ?
            GROUP BY t.[TestID], t.[TestNo], t.[TestName], t.[Description], t.[Status], t.[CreatedDate], u.[Name]
            ORDER BY t.[CreatedDate] DESC
        """, (task_id,), fetch_all=True)
        
        tests = []
        for row in tests_results:
            tests.append({
                'TestID': row[0],
                'TestNo': row[1],
                'TestName': row[2],
                'Description': row[3],
                'Status': row[4],
                'CreatedDate': row[5],
                'UserName': row[6],
                'SampleCount': row[7]
            })
        
        return jsonify({
            'success': True,
            'tests': tests,
            'count': len(tests)
        })
        
    except Exception as e:
        print(f"Error getting task tests: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_mssql_bp.route('/api/tasks/<int:task_id>/samples')
def get_task_samples(task_id):
    """
    Get all samples assigned to a task.
    """
    try:
        samples_results = mssql_db.execute_query("""
            SELECT 
                s.[SampleID],
                s.[Description],
                s.[PartNumber],
                s.[Status],
                s.[Amount],
                CASE
                    WHEN u.[UnitName] IS NULL THEN 'pcs'
                    WHEN LOWER(u.[UnitName]) = 'stk' THEN 'pcs'
                    ELSE u.[UnitName]
                END as UnitName,
                sl.[LocationName],
                FORMAT(r.[ReceivedDate], 'dd-MM-yyyy') as ReceivedDate
            FROM [sample] s
            LEFT JOIN [unit] u ON s.[UnitID] = u.[UnitID]
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            LEFT JOIN [reception] r ON s.[ReceptionID] = r.[ReceptionID]
            WHERE s.[TaskID] = ?
            ORDER BY s.[SampleID]
        """, (task_id,), fetch_all=True)
        
        samples = []
        for row in samples_results:
            samples.append({
                'SampleID': row[0],
                'Description': row[1],
                'PartNumber': row[2],
                'Status': row[3],
                'Amount': row[4],
                'UnitName': row[5],
                'LocationName': row[6] or 'Unknown',
                'ReceivedDate': row[7]
            })
        
        return jsonify({
            'success': True,
            'samples': samples,
            'count': len(samples)
        })
        
    except Exception as e:
        print(f"Error getting task samples: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_mssql_bp.route('/api/tasks/<int:task_id>/assign-samples', methods=['POST'])
def assign_samples_to_task(task_id):
    """
    Assign samples to a task.
    """
    try:
        data = request.get_json()
        sample_ids = data.get('sample_ids', [])
        purpose = data.get('purpose', '')
        
        if not sample_ids:
            return jsonify({
                'success': False,
                'error': 'No samples provided'
            }), 400
        
        user_id = 1  # TODO: Implement proper user authentication
        
        # Assign samples to task
        assigned_count = 0
        for sample_id in sample_ids:
            # Update sample with task assignment
            mssql_db.execute_query("""
                UPDATE [sample] 
                SET [TaskID] = ?, [LastModified] = GETDATE()
                WHERE [SampleID] = ?
            """, (task_id, sample_id))
            
            assigned_count += 1
            
            # Log activity
            mssql_db.execute_query("""
                INSERT INTO [history] (
                    [Timestamp], 
                    [ActionType], 
                    [UserID], 
                    [SampleID],
                    [Notes]
                )
                VALUES (GETDATE(), 'Sample assigned to task', ?, ?, ?)
            """, (
                user_id,
                sample_id,
                f"Sample {sample_id} assigned to task {task_id}. Purpose: {purpose}"
            ))
        
        return jsonify({
            'success': True,
            'message': f'Successfully assigned {assigned_count} sample(s) to task'
        })
        
    except Exception as e:
        print(f"Error assigning samples to task: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500