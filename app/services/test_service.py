from datetime import datetime
from app.utils.db import DatabaseManager

class TestService:
    def __init__(self, mysql):
        self.mysql = mysql
        self.db = DatabaseManager(mysql)
    
    def get_active_tests(self, task_filter=None, user_filter=None):
        """Get all active tests with sample information, optionally filtered by task"""
        query = """
            SELECT 
                t.TestID,
                t.TestNo,
                t.TestName,
                t.TaskID,
                task.TaskNumber,
                task.TaskName as TaskName,
                t.Description,
                t.Status,
                t.CreatedDate,
                u.Name as UserName,
                COALESCE(sample_counts.total_samples, 0) as sample_count,
                COALESCE(sample_counts.active_samples, 0) as active_sample_count
            FROM test t
            LEFT JOIN user u ON t.UserID = u.UserID
            LEFT JOIN task task ON t.TaskID = task.TaskID
            LEFT JOIN (
                SELECT 
                    TestID,
                    COUNT(*) as total_samples,
                    SUM(CASE WHEN Status IN ('Allocated', 'Active') THEN 1 ELSE 0 END) as active_samples
                FROM testsampleusage 
                GROUP BY TestID
            ) sample_counts ON t.TestID = sample_counts.TestID
            WHERE t.Status IN ('Created', 'In Progress')
        """
        
        params = []
        if task_filter:
            query += " AND t.TaskID = %s"
            params.append(task_filter)
        
        if user_filter:
            query += " AND t.UserID = %s"
            params.append(user_filter)
        
        query += " ORDER BY t.CreatedDate DESC"
        
        result, _ = self.db.execute_query(query, params)
        
        tests = []
        for row in result:
            tests.append({
                'id': row[0],
                'test_no': row[1],
                'test_name': row[2],
                'task_id': row[3],
                'task_number': row[4],
                'task_name': row[5],
                'description': row[6],
                'status': row[7],
                'created_date': row[8],
                'user_name': row[9],
                'sample_count': row[10] or 0,
                'active_sample_count': row[11] or 0
            })
        
        return tests
    
    def create_test(self, test_data, user_id):
        """Create a new test, optionally linked to a task"""
        try:
            with self.db.transaction() as cursor:
                # Generate test number based on task or use general numbering
                task_id = test_data.get('task_id')
                
                if task_id:
                    # Use task-specific test numbering
                    cursor.execute("SELECT GetNextTaskTestNumber(%s)", (task_id,))
                    test_no_result = cursor.fetchone()
                    test_no = test_no_result[0] if test_no_result and test_no_result[0] else None
                    
                    if not test_no:
                        # Fallback to regular numbering if task function fails
                        cursor.execute("SELECT GetNextTestNumber()")
                        test_no = cursor.fetchone()[0]
                else:
                    # Use general test numbering
                    cursor.execute("SELECT GetNextTestNumber()")
                    test_no = cursor.fetchone()[0]
                
                # Insert test with optional task link
                cursor.execute("""
                    INSERT INTO test (TestNo, TestName, TaskID, Description, Status, CreatedDate, UserID)
                    VALUES (%s, %s, %s, %s, 'Created', %s, %s)
                """, (
                    test_no,
                    test_data.get('testName'),
                    task_id,
                    test_data.get('description', ''),
                    datetime.now(),
                    user_id
                ))
                
                test_id = cursor.lastrowid
                
                # Log task relationship if applicable
                log_message = f'Test {test_no} created successfully'
                if task_id:
                    log_message += f' (linked to Task ID {task_id})'
                
                return {
                    'success': True,
                    'test_id': test_id,
                    'test_no': test_no,
                    'task_id': task_id,
                    'message': log_message
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create test: {str(e)}'
            }
    
    def create_test_iteration(self, base_test_no, test_data, user_id):
        """Create a new iteration of an existing test"""
        try:
            with self.db.transaction() as cursor:
                # Generate iteration number
                cursor.execute("SELECT GetNextTestIteration(%s)", (base_test_no,))
                test_no = cursor.fetchone()[0]
                
                # Insert test
                cursor.execute("""
                    INSERT INTO test (TestNo, TestName, Description, Status, CreatedDate, UserID)
                    VALUES (%s, %s, %s, 'Created', %s, %s)
                """, (
                    test_no,
                    test_data.get('testName'),
                    test_data.get('description', ''),
                    datetime.now(),
                    user_id
                ))
                
                test_id = cursor.lastrowid
                
                return {
                    'success': True,
                    'test_id': test_id,
                    'test_no': test_no,
                    'message': f'Test iteration {test_no} created successfully'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create test iteration: {str(e)}'
            }
    
    def add_samples_to_test(self, test_id, sample_assignments, user_id):
        """Add samples to a test"""
        try:
            with self.db.transaction() as cursor:
                # Get test info
                cursor.execute("SELECT TestNo FROM test WHERE TestID = %s", (test_id,))
                test_result = cursor.fetchone()
                if not test_result:
                    return {'success': False, 'error': 'Test not found'}
                
                test_no = test_result[0]
                
                # Get existing sample count for identifier generation
                cursor.execute("""
                    SELECT COUNT(*) FROM testsampleusage WHERE TestID = %s
                """, (test_id,))
                existing_count = cursor.fetchone()[0] or 0
                
                added_samples = []
                
                for i, assignment in enumerate(sample_assignments):
                    sample_id = assignment['sample_id']
                    amount = assignment['amount']
                    notes = assignment.get('notes', '')
                    
                    # Generate sample identifier
                    sample_identifier = f"{test_no}_{existing_count + i + 1}"
                    
                    # Check available amount
                    cursor.execute("""
                        SELECT COALESCE(SUM(AmountRemaining), 0) 
                        FROM samplestorage 
                        WHERE SampleID = %s
                    """, (sample_id,))
                    available = cursor.fetchone()[0] or 0
                    
                    if available < amount:
                        # Enhanced error message with debugging info
                        cursor.execute("""
                            SELECT 
                                s.Status,
                                s.Amount as OriginalAmount,
                                COUNT(ss.StorageID) as StorageRecords,
                                COALESCE(SUM(ss.AmountRemaining), 0) as TotalRemaining,
                                COALESCE(SUM(CASE 
                                    WHEN tsu.Status IN ('Allocated', 'Active') 
                                    THEN tsu.AmountAllocated 
                                    ELSE 0 
                                END), 0) as AllocatedToTests
                            FROM sample s
                            LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
                            LEFT JOIN testsampleusage tsu ON s.SampleID = tsu.SampleID
                            WHERE s.SampleID = %s
                            GROUP BY s.SampleID, s.Status, s.Amount
                        """, (sample_id,))
                        
                        debug_info = cursor.fetchone()
                        
                        detailed_error = f'Insufficient amount for sample {sample_id}. '
                        detailed_error += f'Available: {available}, Requested: {amount}. '
                        
                        if debug_info:
                            status, original_amount, storage_records, total_remaining, allocated_to_tests = debug_info
                            detailed_error += f'Debug info - Status: {status}, '
                            detailed_error += f'Original Amount: {original_amount}, '
                            detailed_error += f'Storage Records: {storage_records}, '
                            detailed_error += f'Total Remaining: {total_remaining}, '
                            detailed_error += f'Allocated to Tests: {allocated_to_tests}'
                            
                            # Suggest specific solutions based on the debug info
                            if status != 'In Storage':
                                detailed_error += f'. ISSUE: Sample status is "{status}" instead of "In Storage"'
                            if storage_records == 0:
                                detailed_error += '. ISSUE: No storage records found for this sample'
                            if total_remaining == 0 and original_amount > 0:
                                detailed_error += '. ISSUE: Sample has 0 remaining amount but original amount was > 0'
                            if allocated_to_tests > 0:
                                detailed_error += f'. ISSUE: Sample has {allocated_to_tests} units allocated to other active tests'
                        
                        return {
                            'success': False,
                            'error': detailed_error
                        }
                    
                    # Add to test
                    cursor.execute("""
                        INSERT INTO testsampleusage 
                        (SampleID, TestID, SampleIdentifier, AmountAllocated, Status, Notes, CreatedDate, CreatedBy)
                        VALUES (%s, %s, %s, %s, 'Allocated', %s, %s, %s)
                    """, (
                        sample_id, test_id, sample_identifier, amount, 
                        notes, datetime.now(), user_id
                    ))
                    
                    # Reduce available amount in storage
                    cursor.execute("""
                        UPDATE samplestorage 
                        SET AmountRemaining = AmountRemaining - %s
                        WHERE SampleID = %s AND AmountRemaining >= %s
                        ORDER BY StorageID LIMIT 1
                    """, (amount, sample_id, amount))
                    
                    # Update sample status to 'In Test'
                    cursor.execute("""
                        UPDATE sample SET Status = 'In Test' WHERE SampleID = %s
                    """, (sample_id,))
                    
                    # Log history
                    cursor.execute("""
                        INSERT INTO History (SampleID, TestID, ActionType, UserID, Timestamp, Notes)
                        VALUES (%s, %s, 'Assigned to test', %s, %s, %s)
                    """, (
                        sample_id, test_id, user_id, datetime.now(),
                        f'Assigned {amount} units to test {test_no} as {sample_identifier}'
                    ))
                    
                    added_samples.append({
                        'sample_id': sample_id,
                        'identifier': sample_identifier,
                        'amount': amount
                    })
                
                return {
                    'success': True,
                    'added_samples': added_samples,
                    'message': f'Added {len(added_samples)} samples to test {test_no}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to add samples to test: {str(e)}'
            }
    
    def get_test_samples(self, test_id):
        """Get all samples in a test"""
        query = """
            SELECT 
                tsu.UsageID,
                tsu.SampleID,
                s.Description,
                s.PartNumber,
                tsu.SampleIdentifier,
                tsu.AmountAllocated,
                tsu.AmountUsed,
                tsu.AmountReturned,
                tsu.Status,
                tsu.Notes,
                tsu.CreatedDate
            FROM testsampleusage tsu
            JOIN sample s ON tsu.SampleID = s.SampleID
            WHERE tsu.TestID = %s
            ORDER BY tsu.CreatedDate
        """
        
        result, _ = self.db.execute_query(query, (test_id,))
        
        samples = []
        for row in result:
            samples.append({
                'usage_id': row[0],
                'sample_id': row[1],
                'description': row[2],
                'part_number': row[3],
                'identifier': row[4],
                'amount_allocated': row[5],
                'amount_used': row[6],
                'amount_returned': row[7],
                'status': row[8],
                'notes': row[9],
                'created_date': row[10]
            })
        
        return samples
    
    def remove_sample_from_test(self, usage_id, action, amount, user_id, target_test_id=None, notes=''):
        """Remove sample from test with various actions"""
        try:
            with self.db.transaction() as cursor:
                # Get usage info
                cursor.execute("""
                    SELECT tsu.SampleID, tsu.TestID, tsu.AmountAllocated, tsu.AmountUsed, 
                           tsu.SampleIdentifier, t.TestNo
                    FROM testsampleusage tsu
                    JOIN test t ON tsu.TestID = t.TestID
                    WHERE tsu.UsageID = %s
                """, (usage_id,))
                
                usage_result = cursor.fetchone()
                if not usage_result:
                    return {'success': False, 'error': 'Test sample usage not found'}
                
                sample_id, test_id, allocated, used, identifier, test_no = usage_result
                available_to_return = allocated - used
                
                if amount > available_to_return:
                    return {
                        'success': False, 
                        'error': f'Cannot return {amount}. Only {available_to_return} available.'
                    }
                
                if action == 'return':
                    # Return to storage
                    cursor.execute("""
                        UPDATE samplestorage 
                        SET AmountRemaining = AmountRemaining + %s
                        WHERE SampleID = %s
                        ORDER BY StorageID LIMIT 1
                    """, (amount, sample_id))
                    
                    # Update usage record
                    cursor.execute("""
                        UPDATE testsampleusage 
                        SET AmountReturned = AmountReturned + %s, Status = 'Returned'
                        WHERE UsageID = %s
                    """, (amount, usage_id))
                    
                    # Log history
                    cursor.execute("""
                        INSERT INTO History (SampleID, TestID, ActionType, UserID, Timestamp, Notes)
                        VALUES (%s, %s, 'Returned from test', %s, %s, %s)
                    """, (
                        sample_id, test_id, user_id, datetime.now(),
                        f'Returned {amount} units from test {test_no}. {notes}'
                    ))
                    
                elif action == 'transfer' and target_test_id:
                    # Transfer to another test
                    result = self.add_samples_to_test(
                        target_test_id, 
                        [{'sample_id': sample_id, 'amount': amount, 'notes': f'Transferred from {test_no}. {notes}'}],
                        user_id
                    )
                    
                    if not result['success']:
                        return result
                    
                    # Update original usage
                    cursor.execute("""
                        UPDATE testsampleusage 
                        SET Status = 'Transferred'
                        WHERE UsageID = %s
                    """, (usage_id,))
                
                # Check if sample should be removed from 'In Test' status
                cursor.execute("""
                    SELECT COUNT(*) FROM testsampleusage 
                    WHERE SampleID = %s AND Status IN ('Allocated', 'Active')
                """, (sample_id,))
                
                active_tests = cursor.fetchone()[0]
                if active_tests == 0:
                    cursor.execute("""
                        UPDATE sample SET Status = 'In Storage' WHERE SampleID = %s
                    """, (sample_id,))
                
                return {
                    'success': True,
                    'message': f'Successfully {action}ed {amount} units from test'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to {action} sample: {str(e)}'
            }
    
    def update_test_status(self, test_id, new_status, user_id):
        """Update test status"""
        try:
            with self.db.transaction() as cursor:
                cursor.execute("""
                    UPDATE test SET Status = %s WHERE TestID = %s
                """, (new_status, test_id))
                
                # Log in history
                cursor.execute("""
                    INSERT INTO History (TestID, ActionType, UserID, Timestamp, Notes)
                    VALUES (%s, 'Test status change', %s, %s, %s)
                """, (test_id, user_id, datetime.now(), f'Test status changed to {new_status}'))
                
                return {
                    'success': True,
                    'message': f'Test status updated to {new_status}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to update test status: {str(e)}'
            }
    
    def complete_test(self, test_id, sample_completions, user_id):
        """Complete test with detailed sample outcomes"""
        try:
            with self.db.transaction() as cursor:
                # Get test info
                cursor.execute("SELECT TestNo FROM test WHERE TestID = %s", (test_id,))
                test_result = cursor.fetchone()
                if not test_result:
                    return {'success': False, 'error': 'Test not found'}
                
                test_no = test_result[0]
                
                for completion in sample_completions:
                    usage_id = completion['usage_id']
                    amount_used = completion['amount_used']
                    amount_returned = completion.get('amount_returned', 0)
                    notes = completion.get('notes', '')
                    
                    # Update usage record
                    cursor.execute("""
                        UPDATE testsampleusage 
                        SET AmountUsed = %s, AmountReturned = %s, 
                            Status = CASE WHEN %s > 0 THEN 'Returned' ELSE 'Consumed' END,
                            CompletedDate = %s, Notes = CONCAT(COALESCE(Notes, ''), ' ', %s)
                        WHERE UsageID = %s
                    """, (
                        amount_used, amount_returned, amount_returned, 
                        datetime.now(), notes, usage_id
                    ))
                    
                    # Return amount to storage if applicable
                    if amount_returned > 0:
                        cursor.execute("""
                            SELECT SampleID FROM testsampleusage WHERE UsageID = %s
                        """, (usage_id,))
                        sample_id = cursor.fetchone()[0]
                        
                        cursor.execute("""
                            UPDATE samplestorage 
                            SET AmountRemaining = AmountRemaining + %s
                            WHERE SampleID = %s
                            ORDER BY StorageID LIMIT 1
                        """, (amount_returned, sample_id))
                
                # Update test status
                cursor.execute("""
                    UPDATE test SET Status = 'Completed' WHERE TestID = %s
                """, (test_id,))
                
                # Update sample statuses
                cursor.execute("""
                    UPDATE Sample s
                    SET Status = CASE 
                        WHEN EXISTS (
                            SELECT 1 FROM testsampleusage tsu 
                            WHERE tsu.SampleID = s.SampleID 
                            AND tsu.Status IN ('Allocated', 'Active')
                        ) THEN 'In Test'
                        WHEN EXISTS (
                            SELECT 1 FROM samplestorage ss 
                            WHERE ss.SampleID = s.SampleID 
                            AND ss.AmountRemaining > 0
                        ) THEN 'In Storage'
                        ELSE 'Consumed'
                    END
                    WHERE s.SampleID IN (
                        SELECT DISTINCT SampleID FROM testsampleusage WHERE TestID = %s
                    )
                """, (test_id,))
                
                return {
                    'success': True,
                    'message': f'Test {test_no} completed successfully'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to complete test: {str(e)}'
            }
    
    def get_sample_test_history(self, sample_id):
        """Get complete test history for a sample"""
        query = """
            SELECT 
                TestNo, TestName, SampleIdentifier, AmountAllocated,
                AmountUsed, AmountReturned, Status, CreatedDate, CompletedDate
            FROM sampletesthistoryview
            WHERE SampleID = %s
            ORDER BY CreatedDate
        """
        
        result, _ = self.db.execute_query(query, (sample_id,))
        
        history = []
        for row in result:
            history.append({
                'test_no': row[0],
                'test_name': row[1],
                'identifier': row[2],
                'allocated': row[3],
                'used': row[4],
                'returned': row[5],
                'status': row[6],
                'started': row[7],
                'completed': row[8]
            })
        
        return history
    
    def get_available_samples_for_task(self, task_id, search_term=None):
        """
        Get samples available for test assignment from a specific task.
        Only shows samples that are assigned to the task but not yet fully consumed in tests.
        """
        query = """
            SELECT 
                s.SampleID,
                s.Description,
                s.PartNumber,
                s.Barcode,
                ss.AmountRemaining,
                COALESCE(sl.LocationName, 'Unknown') as LocationName,
                CASE
                    WHEN un.UnitName IS NULL THEN 'pcs'
                    WHEN LOWER(un.UnitName) = 'stk' THEN 'pcs'
                    ELSE un.UnitName
                END as Unit,
                COALESCE(SUM(tsu.AmountAllocated), 0) as AllocatedToTests
            FROM sample s
            LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
            LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
            LEFT JOIN unit un ON s.UnitID = un.UnitID
            LEFT JOIN testsampleusage tsu ON s.SampleID = tsu.SampleID AND tsu.Status IN ('Allocated', 'Active')
            WHERE s.TaskID = %s
            AND s.Status = 'In Storage'
            AND (ss.AmountRemaining > 0 OR ss.AmountRemaining IS NULL)
        """
        
        params = [task_id]
        
        if search_term:
            query += """
                AND (s.Description LIKE %s 
                     OR s.Barcode LIKE %s 
                     OR s.PartNumber LIKE %s
                     OR CONCAT('SMP-', s.SampleID) LIKE %s)
            """
            search_param = f"%{search_term}%"
            params.extend([search_param, search_param, search_param, search_param])
        
        query += """
            GROUP BY s.SampleID, s.Description, s.PartNumber, s.Barcode, 
                     ss.AmountRemaining, sl.LocationName, un.UnitName
            HAVING (ss.AmountRemaining - COALESCE(AllocatedToTests, 0)) > 0
            ORDER BY s.SampleID DESC
            LIMIT 50
        """
        
        result, _ = self.db.execute_query(query, params)
        
        samples = []
        for row in result:
            available_amount = (row[4] or 0) - (row[7] or 0)
            sample = {
                'SampleID': row[0],
                'SampleIDFormatted': f'SMP-{row[0]}',
                'Description': row[1],
                'PartNumber': row[2] or '',
                'Barcode': row[3],
                'AmountRemaining': row[4] or 0,
                'LocationName': row[5],
                'Unit': row[6],
                'AllocatedToTests': row[7] or 0,
                'AvailableAmount': available_amount
            }
            samples.append(sample)
        
        return samples