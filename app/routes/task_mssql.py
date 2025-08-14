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
        
        # Build base query using only existing columns - simplified to avoid potential JOIN issues
        query = """
            SELECT 
                t.[TaskID],
                ISNULL(t.[TaskNumber], 'TASK' + CAST(t.[TaskID] AS NVARCHAR)) as TaskNumber,
                t.[TaskName],
                t.[Description],
                t.[Status],
                ISNULL(t.[Priority], 'Medium') as Priority,
                t.[CreatedDate],
                NULL as DueDate,
                NULL as CompletedDate,
                NULL as AssignedToUserID,
                'Unassigned' as AssignedToName,
                0 as SampleCount,
                0 as TestCount
            FROM [task] t
        """
        
        conditions = []
        params = []
        
        if status_filter:
            conditions.append("t.[Status] = ?")
            params.append(status_filter)
        
        if search_term:
            conditions.append("(t.[TaskName] LIKE ? OR t.[Description] LIKE ? OR t.[TaskNumber] LIKE ?)")
            search_param = f"%{search_term}%"
            params.extend([search_param, search_param, search_param])
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY t.[CreatedDate] DESC"
        
        print(f"DEBUG: Task query: {query}")
        print(f"DEBUG: Task params: {params}")
        
        tasks_results = mssql_db.execute_query(query, params, fetch_all=True)
        
        print(f"DEBUG: Found {len(tasks_results) if tasks_results else 0} tasks")
        if tasks_results:
            print(f"DEBUG: First task: {tasks_results[0] if tasks_results else 'None'}")
        
        tasks = []
        for row in tasks_results:
            task_id = row[0]
            
            # Get sample count for this task separately
            sample_count_result = mssql_db.execute_query("""
                SELECT COUNT(*) FROM [sample] WHERE [TaskID] = ?
            """, (task_id,), fetch_one=True)
            sample_count = sample_count_result[0] if sample_count_result else 0
            
            # Get test count for this task separately  
            test_count_result = mssql_db.execute_query("""
                SELECT COUNT(*) FROM [test] WHERE [TaskID] = ?
            """, (task_id,), fetch_one=True)
            test_count = test_count_result[0] if test_count_result else 0
            
            tasks.append({
                'task_id': task_id,
                'task_number': row[1],
                'task_name': row[2],
                'description': row[3],
                'status': row[4],
                'priority': row[5],
                'created_date': row[6].isoformat() if row[6] else None,
                'end_date': row[7].isoformat() if row[7] else None,  # DueDate mapped to end_date
                'completed_date': row[8].isoformat() if row[8] else None,
                'assigned_to_user_id': row[9],
                'assigned_to_name': row[10],
                'total_samples': sample_count,
                'total_tests': test_count
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

@task_mssql_bp.route('/api/tasks/debug', methods=['GET'])
def debug_tasks():
    """
    Debug endpoint to check raw task data.
    """
    try:
        # Get all tasks without JOINs first
        simple_tasks = mssql_db.execute_query("""
            SELECT [TaskID], [TaskName], [Status], [Description], [CreatedDate]
            FROM [task]
            ORDER BY [TaskID]
        """, fetch_all=True)
        
        print(f"DEBUG: Raw tasks from database: {simple_tasks}")
        
        tasks = []
        for row in simple_tasks:
            tasks.append({
                'task_id': row[0],
                'task_name': row[1], 
                'status': row[2],
                'description': row[3],
                'created_date': str(row[4]) if row[4] else None
            })
        
        return jsonify({
            'success': True, 
            'message': f'Found {len(tasks)} tasks',
            'tasks': tasks
        })
    except Exception as e:
        print(f"Error in debug tasks: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

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
        
        # Generate task number - use simpler format to match existing data
        task_no_result = mssql_db.execute_query("""
            SELECT MAX(CAST(SUBSTRING([TaskNumber], 5, LEN([TaskNumber]) - 4) AS INT)) + 1
            FROM [task] 
            WHERE [TaskNumber] LIKE 'TSK-%'
        """, fetch_one=True)
        
        next_number = task_no_result[0] if task_no_result and task_no_result[0] else 1
        task_number = f"TSK-{next_number:03d}"
        
        # Create task (include CreatedBy which is required)
        result = mssql_db.execute_query("""
            INSERT INTO [task] (
                [TaskNumber], 
                [TaskName], 
                [Description], 
                [Status], 
                [Priority], 
                [CreatedDate],
                [CreatedBy]
            ) 
            OUTPUT INSERTED.TaskID
            VALUES (?, ?, ?, ?, ?, GETDATE(), ?)
        """, (
            task_number,
            data.get('task_name'),
            data.get('description', ''),
            data.get('status', 'Planning'),
            data.get('priority', 'Medium'),
            user_id  # CreatedBy is required and cannot be NULL
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
        # Get task details (only use existing columns)
        task_result = mssql_db.execute_query("""
            SELECT 
                t.[TaskID],
                t.[TaskNumber],
                t.[TaskName],
                t.[Description],
                t.[Status],
                t.[Priority],
                t.[CreatedDate],
                NULL as DueDate,
                NULL as CompletedDate,
                NULL as AssignedToUserID,
                'Unassigned' as AssignedToName,
                'Unknown' as CreatedByName
            FROM [task] t
            WHERE t.[TaskID] = ?
        """, (task_id,), fetch_one=True)
        
        if not task_result:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        task = {
            'task_id': task_result[0],
            'task_number': task_result[1],
            'task_name': task_result[2],
            'description': task_result[3],
            'status': task_result[4],
            'priority': task_result[5],
            'created_date': task_result[6].isoformat() if task_result[6] else None,
            'end_date': task_result[7].isoformat() if task_result[7] else None,
            'completion_percentage': 0,
            'notes': task_result[3],
            'assigned_to_name': task_result[10]
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
                'SampleIDFormatted': f'SMP-{row[0]}',
                'Description': row[1],
                'PartNumber': row[2],
                'UsageStatus': row[3],
                'TestNo': None,
                'AmountRemaining': row[4],
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
                COUNT(tu.[UsageID]) as SampleCount
            FROM [test] t
            LEFT JOIN [user] u ON t.[UserID] = u.[UserID]
            LEFT JOIN [testsampleusage] tu ON t.[TestID] = tu.[TestID]
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
                'CreatedDate': row[5].isoformat() if row[5] else None,
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
        
        if 'priority' in data:
            update_fields.append("[Priority] = ?")
            params.append(data['priority'])
        
        # Skip due_date and assigned_to_user_id since these columns don't exist
        # if 'due_date' in data:
        #     update_fields.append("[DueDate] = ?")
        #     params.append(data['due_date'])
        # 
        # if 'assigned_to_user_id' in data:
        #     update_fields.append("[AssignedToUserID] = ?")
        #     params.append(data['assigned_to_user_id'])
        
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
            SET {', '.join(update_fields)}
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
                0 as overdue_tasks
            FROM [task]
        """, fetch_one=True)
        
        stats = {
            'total': stats_result[0] or 0,
            'planning': stats_result[1] or 0,
            'active': stats_result[2] or 0,
            'on_hold': stats_result[3] or 0,
            'completed': stats_result[4] or 0,
            'cancelled': stats_result[5] or 0,
            'overdue': stats_result[6] or 0
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
                NULL as DueDate,
                'Unassigned' as AssignedToName,
                COUNT(DISTINCT s.[SampleID]) as SampleCount,
                COUNT(DISTINCT te.[TestID]) as TestCount,
                0 as IsOverdue
            FROM [task] t
            LEFT JOIN [sample] s ON t.[TaskID] = s.[TaskID]
            LEFT JOIN [test] te ON t.[TaskID] = te.[TaskID]
            GROUP BY t.[TaskID], t.[TaskNumber], t.[TaskName], t.[Status], t.[Priority]
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
                COUNT(tu.[UsageID]) as SampleCount
            FROM [test] t
            LEFT JOIN [user] u ON t.[UserID] = u.[UserID]
            LEFT JOIN [testsampleusage] tu ON t.[TestID] = tu.[TestID]
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

@task_mssql_bp.route('/api/tasks/<int:task_id>/next-test-number', methods=['GET'])
def get_next_test_number(task_id):
    """
    Get the next test number for a task.
    """
    try:
        # Generate test number
        current_year = datetime.now().year
        test_no_result = mssql_db.execute_query("""
            SELECT MAX(CAST(SUBSTRING([TestNo], 6, LEN([TestNo]) - 5) AS INT)) + 1
            FROM [test] 
            WHERE [TestNo] LIKE ?
        """, (f"TST{current_year}%",), fetch_one=True)
        
        next_number = test_no_result[0] if test_no_result and test_no_result[0] else 1
        test_no = f"TST{current_year}{next_number:04d}"
        
        return jsonify({
            'success': True,
            'test_number': test_no
        })
        
    except Exception as e:
        print(f"Error getting next test number: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@task_mssql_bp.route('/api/tasks/<int:task_id>/available-samples', methods=['GET'])
def get_task_available_samples(task_id):
    """
    Get available samples for a task that can be assigned to tests.
    """
    try:
        # Get all available samples that can be assigned to tests
        # (Not limited to task-assigned samples for more flexibility)
        samples_results = mssql_db.execute_query("""
            SELECT 
                s.[SampleID],
                s.[Description], 
                s.[PartNumber],
                ISNULL(ss.[AmountRemaining], s.[Amount]) as AmountAvailable,
                CASE
                    WHEN u.[UnitName] IS NULL THEN 'pcs'
                    WHEN LOWER(u.[UnitName]) = 'stk' THEN 'pcs'
                    ELSE u.[UnitName]
                END as Unit,
                sl.[LocationName]
            FROM [sample] s
            LEFT JOIN [unit] u ON s.[UnitID] = u.[UnitID]
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            WHERE s.[Status] = 'In Storage'
            AND ISNULL(ss.[AmountRemaining], s.[Amount]) > 0
            ORDER BY s.[Description]
        """, fetch_all=True)
        
        samples = []
        for row in samples_results:
            samples.append({
                'SampleID': row[0],
                'SampleIDFormatted': f'SMP-{row[0]}',
                'Description': row[1],
                'PartNumber': row[2] or '',
                'AvailableAmount': row[3],
                'Unit': row[4],
                'LocationName': row[5] or 'Unknown'
            })
        
        return jsonify({
            'success': True,
            'samples': samples
        })
        
    except Exception as e:
        print(f"Error getting task available samples: {e}")
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
                SET [TaskID] = ?
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