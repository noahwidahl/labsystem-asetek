from datetime import datetime
from app.utils.db import DatabaseManager

class TestService:
    def __init__(self, mysql):
        self.mysql = mysql
        self.db = DatabaseManager(mysql)
    
    def get_active_tests(self):
        """Get all active tests with sample information"""
        query = """
            SELECT 
                t.TestID,
                t.TestNo,
                t.TestName,
                t.Description,
                t.Status,
                t.CreatedDate,
                u.Name as UserName,
                COALESCE(sample_counts.total_samples, 0) as sample_count,
                COALESCE(sample_counts.active_samples, 0) as active_sample_count
            FROM Test t
            LEFT JOIN User u ON t.UserID = u.UserID
            LEFT JOIN (
                SELECT 
                    TestID,
                    COUNT(*) as total_samples,
                    SUM(CASE WHEN Status IN ('Allocated', 'Active') THEN 1 ELSE 0 END) as active_samples
                FROM TestSampleUsage 
                GROUP BY TestID
            ) sample_counts ON t.TestID = sample_counts.TestID
            WHERE t.Status IN ('Created', 'In Progress')
            ORDER BY t.CreatedDate DESC
        """
        
        result, _ = self.db.execute_query(query, ())
        
        tests = []
        for row in result:
            tests.append({
                'id': row[0],
                'test_no': row[1],
                'test_name': row[2],
                'description': row[3],
                'status': row[4],
                'created_date': row[5],
                'user_name': row[6],
                'sample_count': row[7] or 0,
                'active_sample_count': row[8] or 0
            })
        
        return tests
    
    def create_test(self, test_data, user_id):
        """Create a new test"""
        try:
            with self.db.transaction() as cursor:
                # Generate test number
                cursor.execute("SELECT GetNextTestNumber()")
                test_no = cursor.fetchone()[0]
                
                # Insert test
                cursor.execute("""
                    INSERT INTO Test (TestNo, TestName, Description, Status, CreatedDate, UserID)
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
                    'message': f'Test {test_no} created successfully'
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
                    INSERT INTO Test (TestNo, TestName, Description, Status, CreatedDate, UserID)
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
                cursor.execute("SELECT TestNo FROM Test WHERE TestID = %s", (test_id,))
                test_result = cursor.fetchone()
                if not test_result:
                    return {'success': False, 'error': 'Test not found'}
                
                test_no = test_result[0]
                
                # Get existing sample count for identifier generation
                cursor.execute("""
                    SELECT COUNT(*) FROM TestSampleUsage WHERE TestID = %s
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
                        FROM SampleStorage 
                        WHERE SampleID = %s
                    """, (sample_id,))
                    available = cursor.fetchone()[0] or 0
                    
                    if available < amount:
                        return {
                            'success': False,
                            'error': f'Insufficient amount for sample {sample_id}. Available: {available}, Requested: {amount}'
                        }
                    
                    # Add to test
                    cursor.execute("""
                        INSERT INTO TestSampleUsage 
                        (SampleID, TestID, SampleIdentifier, AmountAllocated, Status, Notes, CreatedDate, CreatedBy)
                        VALUES (%s, %s, %s, %s, 'Allocated', %s, %s, %s)
                    """, (
                        sample_id, test_id, sample_identifier, amount, 
                        notes, datetime.now(), user_id
                    ))
                    
                    # Reduce available amount in storage
                    cursor.execute("""
                        UPDATE SampleStorage 
                        SET AmountRemaining = AmountRemaining - %s
                        WHERE SampleID = %s AND AmountRemaining >= %s
                        ORDER BY StorageID LIMIT 1
                    """, (amount, sample_id, amount))
                    
                    # Update sample status to 'In Test'
                    cursor.execute("""
                        UPDATE Sample SET Status = 'In Test' WHERE SampleID = %s
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
            FROM TestSampleUsage tsu
            JOIN Sample s ON tsu.SampleID = s.SampleID
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
                    FROM TestSampleUsage tsu
                    JOIN Test t ON tsu.TestID = t.TestID
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
                        UPDATE SampleStorage 
                        SET AmountRemaining = AmountRemaining + %s
                        WHERE SampleID = %s
                        ORDER BY StorageID LIMIT 1
                    """, (amount, sample_id))
                    
                    # Update usage record
                    cursor.execute("""
                        UPDATE TestSampleUsage 
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
                        UPDATE TestSampleUsage 
                        SET Status = 'Transferred'
                        WHERE UsageID = %s
                    """, (usage_id,))
                
                # Check if sample should be removed from 'In Test' status
                cursor.execute("""
                    SELECT COUNT(*) FROM TestSampleUsage 
                    WHERE SampleID = %s AND Status IN ('Allocated', 'Active')
                """, (sample_id,))
                
                active_tests = cursor.fetchone()[0]
                if active_tests == 0:
                    cursor.execute("""
                        UPDATE Sample SET Status = 'In Storage' WHERE SampleID = %s
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
                    UPDATE Test SET Status = %s WHERE TestID = %s
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
                cursor.execute("SELECT TestNo FROM Test WHERE TestID = %s", (test_id,))
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
                        UPDATE TestSampleUsage 
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
                            SELECT SampleID FROM TestSampleUsage WHERE UsageID = %s
                        """, (usage_id,))
                        sample_id = cursor.fetchone()[0]
                        
                        cursor.execute("""
                            UPDATE SampleStorage 
                            SET AmountRemaining = AmountRemaining + %s
                            WHERE SampleID = %s
                            ORDER BY StorageID LIMIT 1
                        """, (amount_returned, sample_id))
                
                # Update test status
                cursor.execute("""
                    UPDATE Test SET Status = 'Completed' WHERE TestID = %s
                """, (test_id,))
                
                # Update sample statuses
                cursor.execute("""
                    UPDATE Sample s
                    SET Status = CASE 
                        WHEN EXISTS (
                            SELECT 1 FROM TestSampleUsage tsu 
                            WHERE tsu.SampleID = s.SampleID 
                            AND tsu.Status IN ('Allocated', 'Active')
                        ) THEN 'In Test'
                        WHEN EXISTS (
                            SELECT 1 FROM SampleStorage ss 
                            WHERE ss.SampleID = s.SampleID 
                            AND ss.AmountRemaining > 0
                        ) THEN 'In Storage'
                        ELSE 'Consumed'
                    END
                    WHERE s.SampleID IN (
                        SELECT DISTINCT SampleID FROM TestSampleUsage WHERE TestID = %s
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
            FROM SampleTestHistoryView
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