#!/usr/bin/env python

"""
This script creates a test directly in the database without going through the API.
It helps debug issues with test creation.
"""

import os
import sys
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection info
DB_HOST = os.getenv('MYSQL_HOST', 'localhost')
DB_USER = os.getenv('MYSQL_USER', 'root')
DB_PASS = os.getenv('MYSQL_PASSWORD', '')
DB_NAME = os.getenv('MYSQL_DB', 'lab_system')

try:
    # Connect to database
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )
    cursor = conn.cursor()
    
    # Generate test number
    test_no = "T1000.1"
    test_name = "Test Fixture"
    description = "Created by test fixture script"
    user_id = 1  # Assuming user ID 1 exists
    
    # Create test
    cursor.execute("""
        INSERT INTO Test (TestNo, TestName, Description, CreatedDate, UserID)
        VALUES (%s, %s, %s, NOW(), %s)
    """, (test_no, test_name, description, user_id))
    
    test_id = cursor.lastrowid
    print(f"Created test with ID {test_id} and TestNo {test_no}")
    
    # Get a sample to add to test
    cursor.execute("""
        SELECT SampleID FROM Sample LIMIT 1
    """)
    
    sample_result = cursor.fetchone()
    if sample_result:
        sample_id = sample_result[0]
        
        # Add sample to test
        test_sample_id = f"{test_no}_1"
        cursor.execute("""
            INSERT INTO TestSample (SampleID, TestID, TestIteration, GeneratedIdentifier)
            VALUES (%s, %s, %s, %s)
        """, (sample_id, test_id, 1, test_sample_id))
        
        # Add history entry
        cursor.execute("""
            INSERT INTO History (Timestamp, ActionType, UserID, SampleID, TestID, Notes)
            VALUES (NOW(), %s, %s, %s, %s, %s)
        """, (
            'Sample added to test',
            user_id,
            sample_id,
            test_id,
            f"Sample added to test {test_no} as {test_sample_id}"
        ))
        
        print(f"Added sample {sample_id} to test with identifier {test_sample_id}")
    
    # Commit changes
    conn.commit()
    print("Test creation successful")
    
except Exception as e:
    print(f"Error: {e}")
    if 'conn' in locals() and conn.is_connected():
        conn.rollback()
finally:
    if 'cursor' in locals() and cursor:
        cursor.close()
    if 'conn' in locals() and conn.is_connected():
        conn.close()