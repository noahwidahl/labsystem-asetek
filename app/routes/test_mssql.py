from flask import Blueprint, render_template, jsonify, request
from app.utils.mssql_db import mssql_db
from datetime import datetime

test_mssql_bp = Blueprint('test_mssql', __name__)

@test_mssql_bp.route('/testing')
def testing():
    try:
        # Get current user (simplified for now)
        user_id = 1  # TODO: Implement proper user authentication
        
        # Get active tests (only for current user)
        active_tests_results = mssql_db.execute_query("""
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
            WHERE t.[UserID] = ? AND t.[Status] IN ('Created', 'In Progress', 'Active')
            GROUP BY t.[TestID], t.[TestNo], t.[TestName], t.[Description], t.[Status], t.[CreatedDate], u.[Name]
            ORDER BY t.[CreatedDate] DESC
        """, (user_id,), fetch_all=True)
        
        active_tests = []
        for row in active_tests_results:
            active_tests.append({
                'TestID': row[0],
                'TestNo': row[1],
                'TestName': row[2],
                'Description': row[3],
                'Status': row[4],
                'CreatedDate': row[5],
                'UserName': row[6],
                'SampleCount': row[7]
            })
        
        # Get available samples for test creation
        samples_results = mssql_db.execute_query("""
            SELECT 
                s.[SampleID], 
                s.[Description], 
                s.[PartNumber],
                ISNULL(ss.[AmountRemaining], s.[Amount]) as AmountAvailable,
                sl.[LocationName],
                s.[Status]
            FROM [sample] s
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            WHERE s.[Status] = 'In Storage'
            AND ISNULL(ss.[AmountRemaining], s.[Amount]) > 0
            ORDER BY s.[Description]
        """, fetch_all=True)
        
        samples = []
        for row in samples_results:
            samples.append({
                "SampleID": row[0],
                "SampleIDFormatted": f"SMP-{row[0]}",
                "Description": row[1],
                "PartNumber": row[2] or "",
                "AmountAvailable": row[3],
                "LocationName": row[4] or "Unknown",
                "Status": row[5]
            })
        
        # Get users
        users_results = mssql_db.execute_query("""
            SELECT [UserID], [Name] FROM [user] ORDER BY [Name]
        """, fetch_all=True)
        users = [{'UserID': row[0], 'Name': row[1]} for row in users_results]
        
        # Get active tasks for test creation
        tasks_results = mssql_db.execute_query("""
            SELECT [TaskID], [TaskNumber], [TaskName], [Status] 
            FROM [task] 
            WHERE [Status] IN ('Planning', 'Active', 'On Hold')
            ORDER BY [TaskNumber] DESC
        """, fetch_all=True)
        tasks = [{'TaskID': row[0], 'TaskNumber': row[1], 'TaskName': row[2], 'Status': row[3]} for row in tasks_results]
        
        return render_template('sections/testing.html', 
                            active_tests=active_tests, 
                            samples=samples,
                            users=users,
                            tasks=tasks)
    except Exception as e:
        print(f"Error loading testing: {e}")
        import traceback
        traceback.print_exc()
        return render_template('sections/testing.html', 
                            error="Error loading test administration")

@test_mssql_bp.route('/api/tests', methods=['GET'])
def get_tests():
    """
    Get tests with optional task filtering.
    """
    try:
        task_filter = request.args.get('task_id')
        user_id = 1  # TODO: Implement proper user authentication
        
        query = """
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
            WHERE t.[UserID] = ?
        """
        params = [user_id]
        
        if task_filter:
            query += " AND t.[TaskID] = ?"
            params.append(int(task_filter))
        
        query += """
            GROUP BY t.[TestID], t.[TestNo], t.[TestName], t.[Description], t.[Status], t.[CreatedDate], u.[Name]
            ORDER BY t.[CreatedDate] DESC
        """
        
        tests_results = mssql_db.execute_query(query, params, fetch_all=True)
        
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
        print(f"Error getting tests: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@test_mssql_bp.route('/api/tests/create', methods=['POST'])
def create_test():
    try:
        data = request.json
        user_id = 1  # TODO: Implement proper user authentication
        
        # Generate test number
        current_year = datetime.now().year
        test_no_result = mssql_db.execute_query("""
            SELECT MAX(CAST(SUBSTRING([TestNo], 6, LEN([TestNo]) - 5) AS INT)) + 1
            FROM [test] 
            WHERE [TestNo] LIKE ?
        """, (f"TST{current_year}%",), fetch_one=True)
        
        next_number = test_no_result[0] if test_no_result and test_no_result[0] else 1
        test_no = f"TST{current_year}{next_number:04d}"
        
        # Create test
        result = mssql_db.execute_query("""
            INSERT INTO [test] (
                [TestNo], 
                [TestName], 
                [Description], 
                [Status], 
                [CreatedDate], 
                [UserID],
                [TaskID]
            ) 
            OUTPUT INSERTED.TestID
            VALUES (?, ?, ?, 'Created', GETDATE(), ?, ?)
        """, (
            test_no,
            data.get('test_name'),
            data.get('description', ''),
            user_id,
            data.get('task_id')
        ), fetch_one=True)
        
        if result:
            test_id = result[0]
            
            # Log activity
            mssql_db.execute_query("""
                INSERT INTO [history] (
                    [Timestamp], 
                    [ActionType], 
                    [UserID], 
                    [Notes]
                )
                VALUES (GETDATE(), 'Test created', ?, ?)
            """, (
                user_id,
                f"Test '{data.get('test_name')}' created with number {test_no}"
            ))
            
            return jsonify({
                'success': True,
                'test_id': test_id,
                'test_no': test_no,
                'message': 'Test created successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create test'}), 500
        
    except Exception as e:
        print(f"Error creating test: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to create test: {str(e)}'
        }), 500

@test_mssql_bp.route('/api/tests/<int:test_id>/add-samples', methods=['POST'])
def add_samples_to_test(test_id):
    try:
        data = request.json
        user_id = 1  # TODO: Implement proper user authentication
        sample_assignments = data.get('samples', [])
        
        added_samples = []
        
        for assignment in sample_assignments:
            sample_id = assignment.get('sample_id')
            amount = assignment.get('amount', 1)
            notes = assignment.get('notes', '')
            
            # Check sample availability
            available_result = mssql_db.execute_query("""
                SELECT ISNULL(ss.[AmountRemaining], s.[Amount]) as Available
                FROM [sample] s
                LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
                WHERE s.[SampleID] = ?
            """, (sample_id,), fetch_one=True)
            
            if not available_result or available_result[0] < amount:
                return jsonify({
                    'success': False,
                    'error': f'Insufficient amount available for sample {sample_id}'
                }), 400
            
            # Create test usage record
            usage_result = mssql_db.execute_query("""
                INSERT INTO [testusage] (
                    [TestID], 
                    [SampleID], 
                    [AmountUsed], 
                    [Status], 
                    [AssignedDate], 
                    [Notes]
                ) 
                OUTPUT INSERTED.TestUsageID
                VALUES (?, ?, ?, 'Active', GETDATE(), ?)
            """, (test_id, sample_id, amount, notes), fetch_one=True)
            
            if usage_result:
                usage_id = usage_result[0]
                
                # Update sample storage
                mssql_db.execute_query("""
                    UPDATE [samplestorage] 
                    SET [AmountRemaining] = [AmountRemaining] - ?
                    WHERE [SampleID] = ?
                """, (amount, sample_id))
                
                # Generate identifier
                identifier = f"TST{test_id}SMP{sample_id}{usage_id}"
                
                added_samples.append({
                    'usage_id': usage_id,
                    'sample_id': sample_id,
                    'amount': amount,
                    'identifier': identifier
                })
                
                # Log activity
                mssql_db.execute_query("""
                    INSERT INTO [history] (
                        [Timestamp], 
                        [ActionType], 
                        [UserID], 
                        [SampleID],
                        [Notes]
                    )
                    VALUES (GETDATE(), 'Sample added to test', ?, ?, ?)
                """, (
                    user_id,
                    sample_id,
                    f"Sample {sample_id} added to test {test_id} with amount {amount}"
                ))
        
        return jsonify({
            'success': True,
            'added_samples': added_samples,
            'message': f'{len(added_samples)} samples added to test successfully'
        })
        
    except Exception as e:
        print(f"Error adding samples to test: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to add samples to test: {str(e)}'
        }), 500

@test_mssql_bp.route('/api/tests/<int:test_id>/samples', methods=['GET'])
def get_test_samples(test_id):
    try:
        samples_results = mssql_db.execute_query("""
            SELECT 
                tu.[TestUsageID],
                tu.[SampleID],
                s.[Description],
                s.[PartNumber],
                tu.[AmountUsed],
                tu.[Status],
                tu.[AssignedDate],
                tu.[CompletedDate],
                tu.[Notes],
                u.[UnitName],
                sl.[LocationName]
            FROM [testusage] tu
            JOIN [sample] s ON tu.[SampleID] = s.[SampleID]
            LEFT JOIN [unit] u ON s.[UnitID] = u.[UnitID]
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            WHERE tu.[TestID] = ?
            ORDER BY tu.[AssignedDate] DESC
        """, (test_id,), fetch_all=True)
        
        samples = []
        for row in samples_results:
            samples.append({
                'TestUsageID': row[0],
                'SampleID': row[1],
                'Description': row[2],
                'PartNumber': row[3],
                'AmountUsed': row[4],
                'Status': row[5],
                'AssignedDate': row[6],
                'CompletedDate': row[7],
                'Notes': row[8],
                'UnitName': row[9] or 'pcs',
                'LocationName': row[10] or 'Unknown'
            })
        
        return jsonify({
            'success': True,
            'samples': samples
        })
        
    except Exception as e:
        print(f"Error getting test samples: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get test samples: {str(e)}'
        }), 500

@test_mssql_bp.route('/api/tests/<int:test_id>/status', methods=['PUT'])
def update_test_status(test_id):
    try:
        data = request.json
        user_id = 1  # TODO: Implement proper user authentication
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({
                'success': False,
                'error': 'Status is required'
            }), 400
        
        valid_statuses = ['Created', 'In Progress', 'Completed', 'Archived']
        if new_status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }), 400
        
        # Update test status
        mssql_db.execute_query("""
            UPDATE [test] 
            SET [Status] = ?, [LastModified] = GETDATE()
            WHERE [TestID] = ?
        """, (new_status, test_id))
        
        # Log activity
        mssql_db.execute_query("""
            INSERT INTO [history] (
                [Timestamp], 
                [ActionType], 
                [UserID], 
                [Notes]
            )
            VALUES (GETDATE(), 'Test status updated', ?, ?)
        """, (
            user_id,
            f"Test {test_id} status changed to {new_status}"
        ))
        
        return jsonify({
            'success': True,
            'message': f'Test status updated to {new_status}'
        })
        
    except Exception as e:
        print(f"Error updating test status: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to update test status: {str(e)}'
        }), 500

@test_mssql_bp.route('/api/tests/<int:test_id>/complete', methods=['POST'])
def complete_test(test_id):
    try:
        data = request.json
        user_id = 1  # TODO: Implement proper user authentication
        sample_completions = data.get('sample_completions', [])
        
        # Update test status to completed
        mssql_db.execute_query("""
            UPDATE [test] 
            SET [Status] = 'Completed', [CompletedDate] = GETDATE()
            WHERE [TestID] = ?
        """, (test_id,))
        
        # Process sample completions
        for completion in sample_completions:
            usage_id = completion.get('usage_id')
            status = completion.get('status', 'Completed')
            notes = completion.get('notes', '')
            
            # Update test usage
            mssql_db.execute_query("""
                UPDATE [testusage] 
                SET [Status] = ?, [CompletedDate] = GETDATE(), [Notes] = ?
                WHERE [TestUsageID] = ?
            """, (status, notes, usage_id))
        
        # Log activity
        mssql_db.execute_query("""
            INSERT INTO [history] (
                [Timestamp], 
                [ActionType], 
                [UserID], 
                [Notes]
            )
            VALUES (GETDATE(), 'Test completed', ?, ?)
        """, (
            user_id,
            f"Test {test_id} completed with {len(sample_completions)} sample completions"
        ))
        
        return jsonify({
            'success': True,
            'message': 'Test completed successfully'
        })
        
    except Exception as e:
        print(f"Error completing test: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to complete test: {str(e)}'
        }), 500

@test_mssql_bp.route('/api/tests/<int:test_id>/details', methods=['GET'])
def get_test_details(test_id):
    try:
        # Get test info
        test_result = mssql_db.execute_query("""
            SELECT 
                t.[TestID], 
                t.[TestNo], 
                t.[TestName], 
                t.[Description], 
                t.[Status], 
                t.[CreatedDate], 
                t.[UserID],
                u.[Name] as UserName
            FROM [test] t
            LEFT JOIN [user] u ON t.[UserID] = u.[UserID]
            WHERE t.[TestID] = ?
        """, (test_id,), fetch_one=True)
        
        if not test_result:
            return jsonify({
                'success': False,
                'error': 'Test not found'
            }), 404
        
        test_info = {
            'test_id': test_result[0],
            'test_no': test_result[1],
            'test_name': test_result[2],
            'description': test_result[3],
            'status': test_result[4],
            'created_date': test_result[5],
            'user_name': test_result[7] or 'Unknown'
        }
        
        # Get samples
        samples_results = mssql_db.execute_query("""
            SELECT 
                tu.[TestUsageID],
                tu.[SampleID],
                s.[Description],
                s.[PartNumber],
                tu.[AmountUsed],
                tu.[Status],
                tu.[AssignedDate],
                tu.[CompletedDate],
                tu.[Notes],
                CASE
                    WHEN u.[UnitName] IS NULL THEN 'pcs'
                    WHEN LOWER(u.[UnitName]) = 'stk' THEN 'pcs'
                    ELSE u.[UnitName]
                END as UnitName,
                sl.[LocationName]
            FROM [testusage] tu
            JOIN [sample] s ON tu.[SampleID] = s.[SampleID]
            LEFT JOIN [unit] u ON s.[UnitID] = u.[UnitID]
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            WHERE tu.[TestID] = ?
            ORDER BY tu.[AssignedDate] DESC
        """, (test_id,), fetch_all=True)
        
        samples = []
        for row in samples_results:
            samples.append({
                'TestUsageID': row[0],
                'SampleID': row[1],
                'Description': row[2],
                'PartNumber': row[3],
                'AmountUsed': row[4],
                'Status': row[5],
                'AssignedDate': row[6],
                'CompletedDate': row[7],
                'Notes': row[8],
                'UnitName': row[9],
                'LocationName': row[10] or 'Unknown'
            })
        
        return jsonify({
            'success': True,
            'test': test_info,
            'samples': samples
        })
        
    except Exception as e:
        print(f"Error getting test details: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get test details: {str(e)}'
        }), 500

@test_mssql_bp.route('/api/tests/<int:test_id>/assign-task', methods=['PUT'])
def assign_test_to_task(test_id):
    """
    Assign a test to a task.
    """
    try:
        data = request.get_json()
        
        if not data or 'task_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Task ID is required'
            }), 400
        
        task_id = data['task_id']
        user_id = 1  # TODO: Implement proper user authentication
        
        # Check if test exists
        test_result = mssql_db.execute_query("""
            SELECT [TestID], [TestName] FROM [test] WHERE [TestID] = ?
        """, (test_id,), fetch_one=True)
        
        if not test_result:
            return jsonify({
                'success': False,
                'error': 'Test not found'
            }), 404
        
        # Check if task exists
        task_result = mssql_db.execute_query("""
            SELECT [TaskID], [TaskName] FROM [task] WHERE [TaskID] = ?
        """, (task_id,), fetch_one=True)
        
        if not task_result:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        # Update test to assign it to task
        mssql_db.execute_query("""
            UPDATE [test] 
            SET [TaskID] = ?
            WHERE [TestID] = ?
        """, (task_id, test_id))
        
        return jsonify({
            'success': True,
            'message': f'Test {test_result[1]} assigned to task {task_result[1]}'
        })
        
    except Exception as e:
        print(f"Error assigning test to task: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@test_mssql_bp.route('/api/samples/<int:sample_id>/move-to-test', methods=['POST'])
def move_sample_to_test(sample_id):
    """
    Move a sample from storage to a test.
    Used by the barcode scanner functionality.
    """
    try:
        data = request.json
        test_id = data.get('test_id')
        amount = data.get('amount', 1)
        notes = data.get('notes', '')
        user_id = 1  # TODO: Implement proper user authentication
        
        if not test_id:
            return jsonify({
                'success': False,
                'error': 'Test ID is required'
            }), 400
        
        # Check sample availability
        available_result = mssql_db.execute_query("""
            SELECT ISNULL(ss.[AmountRemaining], s.[Amount]) as Available
            FROM [sample] s
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            WHERE s.[SampleID] = ?
        """, (sample_id,), fetch_one=True)
        
        if not available_result or available_result[0] < amount:
            return jsonify({
                'success': False,
                'error': f'Insufficient amount available for sample {sample_id}'
            }), 400
        
        # Create test usage record
        usage_result = mssql_db.execute_query("""
            INSERT INTO [testusage] (
                [TestID], 
                [SampleID], 
                [AmountUsed], 
                [Status], 
                [AssignedDate], 
                [Notes]
            ) 
            OUTPUT INSERTED.TestUsageID
            VALUES (?, ?, ?, 'Active', GETDATE(), ?)
        """, (test_id, sample_id, amount, f'Moved via scanner. {notes}'.strip()), fetch_one=True)
        
        if usage_result:
            usage_id = usage_result[0]
            
            # Update sample storage
            mssql_db.execute_query("""
                UPDATE [samplestorage] 
                SET [AmountRemaining] = [AmountRemaining] - ?
                WHERE [SampleID] = ?
            """, (amount, sample_id))
            
            # Generate identifier
            identifier = f"TST{test_id}SMP{sample_id}{usage_id}"
            
            # Get sample and test details for response
            sample_result = mssql_db.execute_query("""
                SELECT [SampleID], [Barcode], [Description], [PartNumber], [Amount], [UnitID]
                FROM [sample] 
                WHERE [SampleID] = ?
            """, (sample_id,), fetch_one=True)
            
            test_result = mssql_db.execute_query("""
                SELECT [TestID], [TestNo], [TestName]
                FROM [test] 
                WHERE [TestID] = ?
            """, (test_id,), fetch_one=True)
            
            # Get unit name
            unit_name = 'pcs'
            if sample_result and sample_result[5]:
                unit_result = mssql_db.execute_query("""
                    SELECT [UnitName] FROM [unit] WHERE [UnitID] = ?
                """, (sample_result[5],), fetch_one=True)
                if unit_result:
                    unit_name = unit_result[0]
            
            # Generate test sample barcode for printing
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            test_barcode = f"TST{sample_result[0]}{test_result[0]}{timestamp[-4:]}"
            
            response_data = {
                'success': True,
                'message': 'Sample moved to test successfully',
                'added_samples': [{
                    'usage_id': usage_id,
                    'sample_id': sample_id,
                    'amount': amount,
                    'identifier': identifier
                }],
                'test_sample_data': {
                    'SampleID': sample_result[0],
                    'SampleIDFormatted': f'SMP-{sample_result[0]}',
                    'Barcode': sample_result[1],
                    'Description': sample_result[2],
                    'PartNumber': sample_result[3],
                    'Amount': amount,
                    'UnitName': unit_name,
                    'TestID': test_result[0],
                    'TestNo': test_result[1],
                    'TestName': test_result[2],
                    'TestBarcode': test_barcode,
                    'SampleIdentifier': identifier,
                    'show_test_print_confirmation': False
                }
            }
            
            # Log activity
            mssql_db.execute_query("""
                INSERT INTO [history] (
                    [Timestamp], 
                    [ActionType], 
                    [UserID], 
                    [SampleID],
                    [Notes]
                )
                VALUES (GETDATE(), 'Sample moved to test', ?, ?, ?)
            """, (
                user_id,
                sample_id,
                f"Sample {sample_id} moved to test {test_id} via scanner with amount {amount}"
            ))
            
            return jsonify(response_data)
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create test usage record'
            }), 500
        
    except Exception as e:
        print(f"Error moving sample to test: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to move sample to test: {str(e)}'
        }), 500