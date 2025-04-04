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
                'Active' as Status,
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
        
        result, _ = self.db.execute_query(query, ())
        
        tests = []
        for row in result:
            test = Test.from_db_row(row)
            # Æen
            test.sample_count = row[7] if len(row) > 7 else 0
            
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
        """Create a new test with samples"""
        samples_added = 0
        db_test_id = None
        test_no = None
        
        try:
            # Step 1: Get the next test number - do this outside of the main transaction
            # Using parameter for LIKE to avoid % escaping issues
            query = """
                SELECT TestNo FROM Test 
                WHERE TestNo LIKE ? 
                ORDER BY TestID DESC LIMIT 1
            """
            # MySQLdb uses %s not ? for placeholders, so replace it
            query = query.replace("?", "%s")
            result, _ = self.db.execute_query(query, ('T%',))
            
            # Process test number logic to match documentation format T1234.5
            # According to documentation:
            # - T1234 is the test number (sequential)
            # - .5 is the iteration number
            
            # First, check if there are any existing tests
            if result and len(result) > 0 and result[0][0]:
                last_test_no = result[0][0]
                print(f"Last test number: {last_test_no}")
                
                try:
                    # Extract the base test number and iteration
                    import re
                    # Pattern to match T1234.5 format
                    match = re.search(r'T(\d+)\.(\d+)', last_test_no)
                    
                    if match:
                        # We found a properly formatted test number
                        base_number = int(match.group(1))
                        iteration = int(match.group(2))
                        
                        # Get the test type - this determines if it's a new test or iteration
                        test_type = test_data.get('type', '')
                        test_description = test_data.get('description', '')
                        
                        # Create a new test number by default
                        test_number = base_number + 1
                        iteration = 1
                        
                        # Check if the user explicitly requested a new iteration of an existing test
                        # Check if this is explicitly marked as an iteration
                        is_iteration = test_data.get('is_iteration', False)
                        
                        # Check if an original test ID was provided
                        original_test_id = test_data.get('original_test_id')
                        
                        # Also check for keywords in the description
                        has_iteration_keywords = test_description and ('iteration' in test_description.lower() or 
                                               'fortsættelse' in test_description.lower() or
                                               'fortsaettelse' in test_description.lower() or
                                               'iter.' in test_description.lower())
                        
                        # If original_test_id is provided, use that directly
                        if original_test_id:
                            # Get the original test information
                            original_query = "SELECT TestNo, TestName FROM Test WHERE TestID = %s"
                            original_result, _ = self.db.execute_query(original_query, (original_test_id,))
                            
                            if original_result and len(original_result) > 0:
                                original_test_no = original_result[0][0]
                                
                                # Extract test number and iteration from the original
                                original_match = re.search(r'T(\d+)\.(\d+)', original_test_no)
                                if original_match:
                                    # Use the same test number but increment the iteration
                                    test_number = int(original_match.group(1))
                                    last_iter_query = """
                                        SELECT MAX(CAST(SUBSTRING_INDEX(TestNo, '.', -1) AS UNSIGNED))
                                        FROM Test
                                        WHERE TestNo LIKE 'T%s.%%'
                                    """
                                    last_iter_result, _ = self.db.execute_query(last_iter_query, (test_number,))
                                    
                                    if last_iter_result and last_iter_result[0][0]:
                                        iteration = int(last_iter_result[0][0]) + 1
                                    else:
                                        iteration = 1
                                    
                                    print(f"Creating iteration {iteration} of test T{test_number} from original test {original_test_no}")
                        
                        # If either condition is true and we don't have an original_test_id, treat as iteration
                        elif is_iteration or has_iteration_keywords:
                            # User wants to create a new iteration of an existing test
                            # Get the original test's information
                            iteration_query = """
                                SELECT TestID, TestNo, TestName FROM Test 
                                WHERE TestNo LIKE %s
                                ORDER BY TestID DESC
                            """
                            # Look for tests with same base number (T1234.%)
                            iteration_pattern = f"T{base_number}.%"
                            iteration_result, _ = self.db.execute_query(iteration_query, (iteration_pattern,))
                            
                            if iteration_result and len(iteration_result) > 0:
                                # Found the original test, make a new iteration
                                test_number = base_number
                                iteration = iteration + 1
                                print(f"Creating new iteration {iteration} of test T{test_number}")
                        else:
                            # No iterations found (shouldn't happen), use next number
                            test_number = base_number + 1
                            iteration = 1
                    else:
                        # Non-standard format, use a new sequential number
                        # Extract numeric part (any number after T)
                        basic_match = re.search(r'T(\d+)', last_test_no)
                        if basic_match:
                            number = int(basic_match.group(1))
                            # If it's a large timestamp-like number, reset to proper sequence
                            if number > 10000:
                                test_number = 1  # Start with 1 for new format
                            else:
                                test_number = number + 1
                        else:
                            test_number = 1  # Start with 1 for new format
                        
                        iteration = 1  # Start with iteration 1
                except Exception as e:
                    print(f"Error parsing last test number: {e}")
                    test_number = 1  # Start with 1 for new format
                    iteration = 1  # Start with iteration 1
            else:
                # No existing tests, start with 1
                test_number = 1
                iteration = 1
            
            # Format according to documentation: T1234.5 
            # Where 1234 is sequential test number and .5 is iteration
            test_no = f"T{test_number}.{iteration}"
            print(f"Generated test number: {test_no}")
            
            # Step 2: Create the Test object
            test = Test.from_dict(test_data)
            test.test_no = test_no  # Set the generated test_no
            test.user_id = user_id
            
            print(f"Creating test with test_no: {test_no}, user_id: {user_id}")
            print(f"Test data: {test_data}")
            
            # Step 3: Insert the test record
            with self.db.transaction() as cursor:
                cursor.execute("""
                    INSERT INTO Test (TestNo, TestName, Description, CreatedDate, UserID)
                    VALUES (%s, %s, %s, NOW(), %s)
                """, (
                    test.test_no,
                    test.test_name,
                    test.description,
                    test.user_id
                ))
                
                # Get the database ID of the created test
                db_test_id = cursor.lastrowid
                print(f"Created test with DB ID: {db_test_id}")
            
            # Step 4: Process samples if there are any
            if test_data.get('samples'):
                for sample_idx, sample_data in enumerate(test_data.get('samples')):
                    sample_id = sample_data.get('id')
                    amount = int(sample_data.get('amount', 1))
                    
                    # Get sample info in a separate query
                    sample_query = """
                        SELECT s.IsUnique, s.PartNumber, s.Description
                        FROM Sample s
                        WHERE s.SampleID = %s
                    """
                    sample_result, _ = self.db.execute_query(sample_query, (sample_id,))
                    
                    is_unique = sample_result[0][0] if sample_result and len(sample_result) > 0 else 0
                    part_number = sample_result[0][1] if sample_result and len(sample_result) > 0 and len(sample_result[0]) > 1 else None
                    description = sample_result[0][2] if sample_result and len(sample_result) > 0 and len(sample_result[0]) > 2 else None
                    
                    # Handle unique samples differently if required
                    if is_unique:
                        # Generate placeholder serial numbers
                        current_time = datetime.now().strftime("%Y%m%d%H%M%S")
                        serial_numbers = [f"SN-{sample_id}-{current_time}-{i+1}" for i in range(amount)]
                        
                        # If serial numbers are provided in the request, use them
                        selected_serials = sample_data.get('serialNumbers', [])
                        serials_to_use = selected_serials if selected_serials else serial_numbers[:amount]
                        
                        for serial_idx, serial_number in enumerate(serials_to_use[:amount]):
                            # Process each unique sample in its own transaction
                            with self.db.transaction() as cursor:
                                # Generate identification ID according to documentation format: "T1234.5_1"
                                # The format is TestID_SequentialNumber where sequential number is unique per test
                                base_identifier = f"{test_no}_{samples_added + 1}"
                                test_sample_id = base_identifier
                                
                                # Add the sample to the test
                                try:
                                    cursor.execute("""
                                        INSERT INTO TestSample (SampleID, TestID, TestIteration, GeneratedIdentifier, SerialNumber)
                                        VALUES (%s, %s, %s, %s, %s)
                                    """, (
                                        sample_id,
                                        db_test_id,
                                        samples_added + 1,
                                        test_sample_id,
                                        serial_number
                                    ))
                                except Exception as e:
                                    # If SerialNumber column doesn't exist, try without it
                                    if "Unknown column 'SerialNumber'" in str(e):
                                        cursor.execute("""
                                            INSERT INTO TestSample (SampleID, TestID, TestIteration, GeneratedIdentifier)
                                            VALUES (%s, %s, %s, %s)
                                        """, (
                                            sample_id,
                                            db_test_id,
                                            samples_added + 1,
                                            test_sample_id
                                        ))
                                    else:
                                        # Re-raise if it's a different error
                                        raise
                                
                                # Log in history that this specific unit was used in test
                                cursor.execute("""
                                    INSERT INTO History (Timestamp, ActionType, UserID, SampleID, TestID, Notes)
                                    VALUES (NOW(), %s, %s, %s, %s, %s)
                                """, (
                                    'Sample added to test',
                                    user_id,
                                    sample_id,
                                    db_test_id,
                                    # Double %% to escape % in format strings when using periods
                                    f"Sample with S/N {serial_number} added to test T{test_number}.1 as {test_sample_id}"
                                ))
                            
                            samples_added += 1
                    else:
                        # For generic samples (like O-rings), process each in its own small transaction
                        for i in range(amount):
                            with self.db.transaction() as cursor:
                                # Generate identification ID according to documentation format: "T1234.5_1"
                                # The format is TestID_SequentialNumber where sequential number is unique per test
                                base_identifier = f"{test_no}_{samples_added + 1}"
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
                                    db_test_id,
                                    samples_added + 1,
                                    test_sample_id
                                ))
                                
                                # Log in history
                                cursor.execute("""
                                    INSERT INTO History (Timestamp, ActionType, UserID, SampleID, TestID, Notes)
                                    VALUES (NOW(), %s, %s, %s, %s, %s)
                                """, (
                                    'Sample added to test',
                                    user_id,
                                    sample_id,
                                    db_test_id,
                                    # Double %% to escape % in format strings when using periods
                                    f"{description if description else 'Sample'} added to test T{test_number}.1 as {test_sample_id}"
                                ))
                            
                            samples_added += 1
                        
                        # Update storage amount in a separate transaction
                        with self.db.transaction() as cursor:
                            cursor.execute("""
                                UPDATE SampleStorage 
                                SET AmountRemaining = AmountRemaining - %s
                                WHERE SampleID = %s AND AmountRemaining >= %s
                                LIMIT 1
                            """, (amount, sample_id, amount))
            
            # Step 5: Log the test creation in a final transaction
            with self.db.transaction() as cursor:
                cursor.execute("""
                    INSERT INTO History (Timestamp, ActionType, UserID, TestID, Notes)
                    VALUES (NOW(), %s, %s, %s, %s)
                """, (
                    'Test created',
                    user_id,
                    db_test_id,
                    # Double %% to escape % in format strings when using periods
                    f"Test T{test_number}.1 created with {samples_added} samples"
                ))
            
            return {
                'success': True, 
                'test_id': test_no,
                'test_db_id': db_test_id,
                'sample_count': samples_added
            }
        except Exception as e:
            print(f"Error in create_test: {e}")
            import traceback
            traceback.print_exc()
            raise e
    
    def complete_test(self, test_id, user_id, disposition_data=None):
        """
        Complete a test and handle sample disposition:
        - disposition_data: Dictionary with sample disposition options:
            - 'action': 'dispose' or 'return' (what to do with samples)
            - 'samples': List of sample IDs to handle specifically
            - 'notes': Optional notes about disposition
        """
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
        
        # Process test completion including sample disposition
        with self.db.transaction() as cursor:
            # Default disposition is to dispose all samples if not specified
            disposition_action = 'dispose'
            disposition_notes = 'Standard disposal after test completion'
            
            if disposition_data:
                disposition_action = disposition_data.get('action', 'dispose')
                disposition_notes = disposition_data.get('notes', 'Sample disposition after test')
            
            # Get all test samples
            cursor.execute("""
                SELECT ts.TestSampleID, ts.SampleID, ts.GeneratedIdentifier, s.IsUnique, s.PartNumber, s.Description
                FROM TestSample ts
                JOIN Sample s ON ts.SampleID = s.SampleID
                WHERE ts.TestID = %s
            """, (actual_test_id,))
            
            test_samples = cursor.fetchall()
            
            handled_samples = 0
            
            # Process each test sample
            for sample in test_samples:
                test_sample_id = sample[0]
                original_sample_id = sample[1]
                generated_identifier = sample[2]
                is_unique = sample[3]
                part_number = sample[4]
                description = sample[5]
                
                # Handle according to disposition
                if disposition_action == 'dispose':
                    # Record disposal
                    cursor.execute("""
                        INSERT INTO Disposal (SampleID, UserID, DisposalDate, AmountDisposed, Notes)
                        VALUES (%s, %s, NOW(), %s, %s)
                    """, (
                        original_sample_id,
                        user_id,
                        1,  # Each test sample is one unit
                        f"Disposed after test {test_no}, identifier: {generated_identifier}"
                    ))
                    
                    # Log in history
                    cursor.execute("""
                        INSERT INTO History (Timestamp, ActionType, UserID, SampleID, TestID, Notes)
                        VALUES (NOW(), %s, %s, %s, %s, %s)
                    """, (
                        'Sample disposed',
                        user_id,
                        original_sample_id,
                        actual_test_id,
                        f"Test sample {generated_identifier} disposed after test completion"
                    ))
                    
                elif disposition_action == 'return':
                    # Return to storage
                    # Add a new entry in SampleStorage
                    cursor.execute("""
                        SELECT LocationID, ExpireDate FROM SampleStorage
                        WHERE SampleID = %s
                        LIMIT 1
                    """, (original_sample_id,))
                    
                    storage_info = cursor.fetchone()
                    location_id = storage_info[0] if storage_info else 1  # Default location
                    expire_date = storage_info[1] if storage_info and len(storage_info) > 1 else None
                    
                    # Add back to sample storage
                    cursor.execute("""
                        UPDATE SampleStorage 
                        SET AmountRemaining = AmountRemaining + 1
                        WHERE SampleID = %s AND LocationID = %s
                        LIMIT 1
                    """, (original_sample_id, location_id))
                    
                    # Check if update affected any rows
                    if cursor.rowcount == 0:
                        # Need to insert a new storage record
                        cursor.execute("""
                            INSERT INTO SampleStorage (SampleID, LocationID, AmountRemaining, ExpireDate)
                            VALUES (%s, %s, %s, %s)
                        """, (
                            original_sample_id,
                            location_id,
                            1,  # Amount
                            expire_date
                        ))
                    
                    # Log in history
                    cursor.execute("""
                        INSERT INTO History (Timestamp, ActionType, UserID, SampleID, TestID, LocationID, Notes)
                        VALUES (NOW(), %s, %s, %s, %s, %s, %s)
                    """, (
                        'Sample returned to storage',
                        user_id,
                        original_sample_id,
                        actual_test_id,
                        location_id,
                        f"Test sample {generated_identifier} returned to storage after test completion"
                    ))
                
                handled_samples += 1
            
            # Log test completion
            cursor.execute("""
                INSERT INTO History (Timestamp, ActionType, UserID, TestID, Notes)
                VALUES (NOW(), %s, %s, %s, %s)
            """, (
                'Test completed',
                user_id,
                actual_test_id,
                f"Test {test_no} completed, {handled_samples} samples {disposition_action}d"
            ))
            
            return {
                'success': True, 
                'test_id': test_no,
                'handled_samples': handled_samples,
                'disposition': disposition_action
            }
            
    def get_test_details(self, test_id):
        """Get detailed information about a test including all test samples"""
        # Add debug output
        print(f"Service: Getting test details for test_id: {test_id} (type: {type(test_id)})")
        
        # Get all tests first to debug
        debug_query = "SELECT TestID, TestNo FROM Test"
        debug_result, _ = self.db.execute_query(debug_query, ())
        print(f"Service: All tests in database: {debug_result}")
        
        # Check if test_id is an integer or a string
        try:
            test_id_int = int(test_id)
            # If it's an integer, search by TestID
            print(f"Service: Parsed test_id as integer: {test_id_int}")
            query = "SELECT TestID, TestNo FROM Test WHERE TestID = %s"
            params = (test_id_int,)
        except ValueError:
            # If it's not an integer, search by TestNo
            print(f"Service: Using test_id as string: {test_id}")
            query = "SELECT TestID, TestNo FROM Test WHERE TestNo = %s"
            params = (test_id,)
        
        result, _ = self.db.execute_query(query, params)
        
        if not result or len(result) == 0:
            raise ValueError('Test not found')
        
        actual_test_id = result[0][0]
        current_test_no = result[0][1]
        
        # Check if this is part of a test series (has same base number)
        import re
        test_match = re.search(r'T(\d+)\.(\d+)', current_test_no)
        related_tests = []
        
        if test_match:
            base_number = test_match.group(1)
            # Find all tests with the same base number
            related_query = """
                SELECT TestID, TestNo, TestName, Description, CreatedDate, UserID
                FROM Test
                WHERE TestNo LIKE 'T%s.%%'
                ORDER BY CAST(SUBSTRING_INDEX(TestNo, '.', -1) AS UNSIGNED)
            """
            related_result, _ = self.db.execute_query(related_query, (base_number,))
            
            if related_result and len(related_result) > 0:
                for row in related_result:
                    related_tests.append({
                        'TestID': row[0],
                        'TestNo': row[1],
                        'TestName': row[2],
                        'Description': row[3],
                        'CreatedDate': row[4].strftime('%Y-%m-%d %H:%M:%S') if row[4] else None,
                        'UserID': row[5],
                        'IsCurrent': row[0] == actual_test_id
                    })
        
        # Get basic test information
        query = """
            SELECT 
                t.TestID, 
                t.TestNo, 
                t.TestName, 
                t.Description, 
                t.CreatedDate, 
                t.UserID,
                'Active' as Status
            FROM Test t
            WHERE t.TestID = %s
        """
        
        result, _ = self.db.execute_query(query, (actual_test_id,))
        
        if not result or len(result) == 0:
            raise ValueError('Test not found')
        
        test = Test.from_db_row(result[0])
        
        # Get username
        user_query = "SELECT Name FROM User WHERE UserID = %s"
        user_result, _ = self.db.execute_query(user_query, (test.user_id,))
        if user_result and len(user_result) > 0:
            test.user_name = user_result[0][0]
        else:
            test.user_name = "Unknown"
        
        # Get all samples in the test - without SerialNumber field that doesn't exist
        samples_query = """
            SELECT 
                ts.TestSampleID,
                ts.SampleID,
                ts.TestIteration,
                ts.GeneratedIdentifier,
                s.Description,
                s.PartNumber
            FROM TestSample ts
            JOIN Sample s ON ts.SampleID = s.SampleID
            WHERE ts.TestID = %s
            ORDER BY ts.TestIteration
        """
        
        samples_result, _ = self.db.execute_query(samples_query, (actual_test_id,))
        
        samples = []
        for row in samples_result:
            samples.append({
                'TestSampleID': row[0],
                'OriginalSampleID': row[1],
                'TestIteration': row[2],
                'GeneratedIdentifier': row[3],
                'Description': row[4] if len(row) > 4 else "Unknown",
                'PartNumber': row[5] if len(row) > 5 else None
            })
        
        test.samples = samples
        
        # Get history for this test
        history_query = """
            SELECT 
                h.Timestamp,
                h.ActionType,
                h.UserID,
                h.SampleID,
                h.TestID,
                h.LocationID,
                h.Notes,
                u.Name as UserName
            FROM History h
            LEFT JOIN User u ON h.UserID = u.UserID
            WHERE h.TestID = %s
            ORDER BY h.Timestamp DESC
        """
        
        history_result, _ = self.db.execute_query(history_query, (actual_test_id,))
        
        history = []
        for row in history_result:
            history.append({
                'Timestamp': row[0].strftime('%Y-%m-%d %H:%M:%S') if row[0] else None,
                'ActionType': row[1],
                'UserID': row[2],
                'SampleID': row[3],
                'TestID': row[4],
                'LocationID': row[5],
                'Notes': row[6],
                'UserName': row[7] if len(row) > 7 else "Unknown"
            })
        
        test.history = history
        test.related_tests = related_tests
        
        return test
    
    def dispose_test_sample(self, test_sample_id, user_id):
        """Dispose of a single test sample"""
        with self.db.transaction() as cursor:
            # Get test sample information
            cursor.execute("""
                SELECT ts.SampleID, ts.TestID, ts.GeneratedIdentifier, t.TestNo
                FROM TestSample ts
                JOIN Test t ON ts.TestID = t.TestID
                WHERE ts.TestSampleID = %s
            """, (test_sample_id,))
            
            result = cursor.fetchone()
            if not result:
                raise ValueError('Test sample not found')
            
            sample_id = result[0]
            test_id = result[1]
            generated_identifier = result[2]
            test_no = result[3]
            
            # Record disposal
            cursor.execute("""
                INSERT INTO Disposal (SampleID, UserID, DisposalDate, AmountDisposed, Notes)
                VALUES (%s, %s, NOW(), %s, %s)
            """, (
                sample_id,
                user_id,
                1,  # Each test sample is one unit
                f"Disposed from test {test_no}, identifier: {generated_identifier}"
            ))
            
            # Log in history
            cursor.execute("""
                INSERT INTO History (Timestamp, ActionType, UserID, SampleID, TestID, Notes)
                VALUES (NOW(), %s, %s, %s, %s, %s)
            """, (
                'Sample disposed',
                user_id,
                sample_id,
                test_id,
                f"Test sample {generated_identifier} disposed"
            ))
            
            return {
                'success': True,
                'sample_id': sample_id,
                'test_sample_id': test_sample_id,
                'test_id': test_id
            }
            
    def return_test_sample_to_storage(self, test_sample_id, user_id):
        """Return a single test sample to storage"""
        with self.db.transaction() as cursor:
            # Get test sample information
            cursor.execute("""
                SELECT ts.SampleID, ts.TestID, ts.GeneratedIdentifier, t.TestNo, s.Description
                FROM TestSample ts
                JOIN Test t ON ts.TestID = t.TestID
                JOIN Sample s ON ts.SampleID = s.SampleID
                WHERE ts.TestSampleID = %s
            """, (test_sample_id,))
            
            result = cursor.fetchone()
            if not result:
                raise ValueError('Test sample not found')
            
            sample_id = result[0]
            test_id = result[1]
            generated_identifier = result[2]
            test_no = result[3]
            description = result[4]
            
            # Get the default storage location for this sample
            cursor.execute("""
                SELECT LocationID, ExpireDate FROM SampleStorage
                WHERE SampleID = %s
                LIMIT 1
            """, (sample_id,))
            
            storage_info = cursor.fetchone()
            location_id = storage_info[0] if storage_info else 1  # Default location
            expire_date = storage_info[1] if storage_info and len(storage_info) > 1 else None
            
            # Add back to sample storage
            cursor.execute("""
                UPDATE SampleStorage 
                SET AmountRemaining = AmountRemaining + 1
                WHERE SampleID = %s AND LocationID = %s
                LIMIT 1
            """, (sample_id, location_id))
            
            # Check if update affected any rows
            if cursor.rowcount == 0:
                # Need to insert a new storage record
                cursor.execute("""
                    INSERT INTO SampleStorage (SampleID, LocationID, AmountRemaining, ExpireDate)
                    VALUES (%s, %s, %s, %s)
                """, (
                    sample_id,
                    location_id,
                    1,  # Amount
                    expire_date
                ))
            
            # Log in history
            cursor.execute("""
                INSERT INTO History (Timestamp, ActionType, UserID, SampleID, TestID, LocationID, Notes)
                VALUES (NOW(), %s, %s, %s, %s, %s, %s)
            """, (
                'Sample returned to storage',
                user_id,
                sample_id,
                test_id,
                location_id,
                f"Test sample {generated_identifier} returned to storage from test {test_no}"
            ))
            
            return {
                'success': True,
                'sample_id': sample_id,
                'test_sample_id': test_sample_id,
                'test_id': test_id,
                'location_id': location_id
            }
    
    def get_chain_of_custody(self, identifier):
        """Get the chain of custody for a test sample based on its identifier"""
        # First find the test sample
        query = """
            SELECT ts.TestSampleID, ts.SampleID, ts.TestID
            FROM TestSample ts
            WHERE ts.GeneratedIdentifier = %s
        """
        
        result, _ = self.db.execute_query(query, (identifier,))
        
        if not result or len(result) == 0:
            raise ValueError('Test sample not found')
        
        test_sample_id = result[0][0]
        sample_id = result[0][1]
        test_id = result[0][2]
        
        # Get all history related to this sample
        history_query = """
            SELECT 
                h.Timestamp,
                h.ActionType,
                h.UserID,
                h.SampleID,
                h.TestID,
                h.LocationID,
                h.Notes,
                u.Name as UserName
            FROM History h
            LEFT JOIN User u ON h.UserID = u.UserID
            WHERE (h.SampleID = %s OR h.TestID = %s)
            ORDER BY h.Timestamp
        """
        
        history_result, _ = self.db.execute_query(history_query, (sample_id, test_id))
        
        history = []
        for row in history_result:
            history.append({
                'Timestamp': row[0].strftime('%Y-%m-%d %H:%M:%S') if row[0] else None,
                'ActionType': row[1],
                'UserID': row[2],
                'UserName': row[7] if len(row) > 7 else "Unknown",
                'Notes': row[6],
            })
        
        return {
            'TestSampleID': test_sample_id,
            'SampleID': sample_id,
            'TestID': test_id,
            'Identifier': identifier,
            'History': history
        }
        
    def dispose_all_test_samples(self, test_id, user_id):
        """Dispose of all samples in a test at once"""
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
        
        # Process disposal of all test samples
        with self.db.transaction() as cursor:
            # Get all test samples
            cursor.execute("""
                SELECT ts.TestSampleID, ts.SampleID, ts.GeneratedIdentifier, s.Description
                FROM TestSample ts
                JOIN Sample s ON ts.SampleID = s.SampleID
                WHERE ts.TestID = %s
            """, (actual_test_id,))
            
            test_samples = cursor.fetchall()
            
            if not test_samples or len(test_samples) == 0:
                raise ValueError('No samples found in this test')
            
            disposed_samples = 0
            
            # Process each test sample
            for sample in test_samples:
                test_sample_id = sample[0]
                sample_id = sample[1]
                generated_identifier = sample[2]
                description = sample[3]
                
                # Record disposal
                cursor.execute("""
                    INSERT INTO Disposal (SampleID, UserID, DisposalDate, AmountDisposed, Notes)
                    VALUES (%s, %s, NOW(), %s, %s)
                """, (
                    sample_id,
                    user_id,
                    1,  # Each test sample is one unit
                    f"Bulk disposal from test {test_no}, identifier: {generated_identifier}"
                ))
                
                # Log in history
                cursor.execute("""
                    INSERT INTO History (Timestamp, ActionType, UserID, SampleID, TestID, Notes)
                    VALUES (NOW(), %s, %s, %s, %s, %s)
                """, (
                    'Sample disposed',
                    user_id,
                    sample_id,
                    actual_test_id,
                    f"Test sample {generated_identifier} disposed during bulk disposal"
                ))
                
                disposed_samples += 1
            
            # Log bulk disposal
            cursor.execute("""
                INSERT INTO History (Timestamp, ActionType, UserID, TestID, Notes)
                VALUES (NOW(), %s, %s, %s, %s)
            """, (
                'Bulk sample disposal',
                user_id,
                actual_test_id,
                f"Bulk disposal of {disposed_samples} samples from test {test_no}"
            ))
            
            return {
                'success': True, 
                'test_id': test_no,
                'disposed_samples': disposed_samples
            }