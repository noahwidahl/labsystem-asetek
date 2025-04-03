from datetime import datetime
from app.models.test import Test
from app.utils.db import DatabaseManager

class TestService:
    def __init__(self, mysql):
        self.mysql = mysql
        self.db = DatabaseManager(mysql)
    
    def get_active_tests(self):
        query = """
            SELECT 
                t.TestID, 
                t.TestNo, 
                t.TestName, 
                t.Description, 
                t.CreatedDate, 
                t.UserID,
                COUNT(ts.TestSampleID) as sample_count
            FROM Test t
            LEFT JOIN TestSample ts ON t.TestID = ts.TestID
            WHERE t.CreatedDate > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
            AND NOT EXISTS (
                SELECT 1 FROM History h 
                WHERE h.TestID = t.TestID AND h.ActionType = 'Test completed'
            )
            GROUP BY t.TestID
            ORDER BY t.CreatedDate DESC
        """
        
        result, _ = self.db.execute_query(query)
        
        tests = []
        for row in result:
            test = Test.from_db_row(row)
            test.sample_count = row[6] if len(row) > 6 else 0
            
            # Get username
            user_query = "SELECT Name FROM User WHERE UserID = %s"
            user_result, _ = self.db.execute_query(user_query, (test.user_id,))
            if user_result and len(user_result) > 0:
                test.user_name = user_result[0][0]
            else:
                test.user_name = "Unknown"
            
            tests.append(test)
        
        return tests
    
    def create_test(self, test_data, user_id):
        with self.db.transaction() as cursor:
            test = Test.from_dict(test_data)
            test.user_id = user_id
            
            # Create the test
            cursor.execute("""
                INSERT INTO Test (TestNo, TestName, Description, CreatedDate, UserID)
                VALUES (%s, %s, %s, NOW(), %s)
            """, (
                test.test_no,
                test.test_name,
                test.description,
                test.user_id
            ))
            
            test_id = cursor.lastrowid
            
            # Add samples to the test
            if test_data.get('samples'):
                samples_added = 0
                
                for sample_idx, sample_data in enumerate(test_data.get('samples')):
                    sample_id = sample_data.get('id')
                    amount = int(sample_data.get('amount', 1))
                    
                    for i in range(amount):
                        # Generate identification ID for test sample
                        base_identifier = f"{test.test_no}_{samples_added + 1}"
                        test_sample_id = base_identifier
                        
                        # Check if this identifier already exists
                        cursor.execute("""
                            SELECT COUNT(*) FROM TestSample 
                            WHERE GeneratedIdentifier = %s
                        """, (test_sample_id,))
                        
                        count = cursor.fetchone()[0]
                        
                        # If it already exists, add a unique suffix
                        if count > 0:
                            timestamp = int(datetime.now().timestamp() * 1000)
                            test_sample_id = f"{base_identifier}_{timestamp % 1000}"
                        
                        cursor.execute("""
                            INSERT INTO TestSample (SampleID, TestID, TestIteration, GeneratedIdentifier)
                            VALUES (%s, %s, %s, %s)
                        """, (
                            sample_id,
                            test_id,
                            samples_added + 1,
                            test_sample_id
                        ))
                        
                        # Reduce the amount in storage
                        cursor.execute("""
                            UPDATE SampleStorage 
                            SET AmountRemaining = AmountRemaining - 1
                            WHERE SampleID = %s AND AmountRemaining > 0
                            LIMIT 1
                        """, (sample_id,))
                        
                        samples_added += 1
            
            # Log the activity
            cursor.execute("""
                INSERT INTO History (Timestamp, ActionType, UserID, TestID, Notes)
                VALUES (NOW(), %s, %s, %s, %s)
            """, (
                'Test created',
                user_id,
                test_id,
                f"Test {test.test_no} created"
            ))
            
            return {
                'success': True, 
                'test_id': test.test_no
            }
    
    def complete_test(self, test_id, user_id):
        # Check if test_id is an integer or a string
        try:
            test_id_int = int(test_id)
            # If it's an integer, search by TestID
            query = "SELECT TestID, TestNo FROM Test WHERE TestID = %s"
            params = (test_id_int,)
        except ValueError:
            # If it's not an integer, search by TestNo
            query = "SELECT TestID, TestNo FROM Test WHERE TestNo = %s"
            params = (test_id,)
        
        result, _ = self.db.execute_query(query, params)
        
        if not result or len(result) == 0:
            raise ValueError('Test not found')
        
        actual_test_id = result[0][0]
        test_no = result[0][1]
        
        # Log test completion
        with self.db.transaction() as cursor:
            cursor.execute("""
                INSERT INTO History (Timestamp, ActionType, UserID, TestID, Notes)
                VALUES (NOW(), %s, %s, %s, %s)
            """, (
                'Test completed',
                user_id,
                actual_test_id,
                f"Test {test_no} completed"
            ))
            
            return {
                'success': True, 
                'test_id': test_no
            }