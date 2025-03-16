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
                WHERE h.TestID = t.TestID AND h.ActionType = 'Test afsluttet'
            )
            GROUP BY t.TestID
            ORDER BY t.CreatedDate DESC
        """
        
        result, _ = self.db.execute_query(query)
        
        tests = []
        for row in result:
            test = Test.from_db_row(row)
            test.sample_count = row[6] if len(row) > 6 else 0
            
            # Hent brugernavn
            user_query = "SELECT Name FROM User WHERE UserID = %s"
            user_result, _ = self.db.execute_query(user_query, (test.user_id,))
            if user_result and len(user_result) > 0:
                test.user_name = user_result[0][0]
            else:
                test.user_name = "Ukendt"
            
            tests.append(test)
        
        return tests
    
    def create_test(self, test_data, user_id):
        with self.db.transaction() as cursor:
            test = Test.from_dict(test_data)
            test.user_id = user_id
            
            # Opret testen
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
            
            # Tilføj prøver til testen
            if test_data.get('samples'):
                samples_added = 0
                
                for sample_idx, sample_data in enumerate(test_data.get('samples')):
                    sample_id = sample_data.get('id')
                    amount = int(sample_data.get('amount', 1))
                    
                    for i in range(amount):
                        # Generer identifikations-id for test sample
                        base_identifier = f"{test.test_no}_{samples_added + 1}"
                        test_sample_id = base_identifier
                        
                        # Tjek om denne identifier allerede eksisterer
                        cursor.execute("""
                            SELECT COUNT(*) FROM TestSample 
                            WHERE GeneratedIdentifier = %s
                        """, (test_sample_id,))
                        
                        count = cursor.fetchone()[0]
                        
                        # Hvis den allerede eksisterer, tilføj et unikt suffix
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
                        
                        # Reducer mængden på lager
                        cursor.execute("""
                            UPDATE SampleStorage 
                            SET AmountRemaining = AmountRemaining - 1
                            WHERE SampleID = %s AND AmountRemaining > 0
                            LIMIT 1
                        """, (sample_id,))
                        
                        samples_added += 1
            
            # Log aktiviteten
            cursor.execute("""
                INSERT INTO History (Timestamp, ActionType, UserID, TestID, Notes)
                VALUES (NOW(), %s, %s, %s, %s)
            """, (
                'Test oprettet',
                user_id,
                test_id,
                f"Test {test.test_no} oprettet"
            ))
            
            return {
                'success': True, 
                'test_id': test.test_no
            }
    
    def complete_test(self, test_id, user_id):
        # Tjek om test_id er et heltal eller en streng
        try:
            test_id_int = int(test_id)
            # Hvis det er et heltal, søg på TestID
            query = "SELECT TestID, TestNo FROM Test WHERE TestID = %s"
            params = (test_id_int,)
        except ValueError:
            # Hvis det ikke er et heltal, søg på TestNo
            query = "SELECT TestID, TestNo FROM Test WHERE TestNo = %s"
            params = (test_id,)
        
        result, _ = self.db.execute_query(query, params)
        
        if not result or len(result) == 0:
            raise ValueError('Test ikke fundet')
        
        actual_test_id = result[0][0]
        test_no = result[0][1]
        
        # Log afslutning af test
        with self.db.transaction() as cursor:
            cursor.execute("""
                INSERT INTO History (Timestamp, ActionType, UserID, TestID, Notes)
                VALUES (NOW(), %s, %s, %s, %s)
            """, (
                'Test afsluttet',
                user_id,
                actual_test_id,
                f"Test {test_no} afsluttet"
            ))
            
            return {
                'success': True, 
                'test_id': test_no
            }