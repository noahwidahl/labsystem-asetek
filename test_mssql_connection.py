#!/usr/bin/env python3
"""
Test script for SQL Server connection
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.mssql_db import mssql_db, get_current_user_mssql

def test_connection():
    """Test basic SQL Server connection"""
    print("Testing SQL Server connection...")
    
    try:
        result = mssql_db.execute_query("SELECT @@VERSION", fetch_one=True)
        print(f"✅ Connection successful!")
        print(f"SQL Server version: {result[0][:50]}...")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_database():
    """Test database and tables"""
    print("\nTesting database structure...")
    
    try:
        # Test if our tables exist
        tables_query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE' 
        ORDER BY TABLE_NAME
        """
        tables = mssql_db.execute_query(tables_query, fetch_all=True)
        
        print(f"✅ Found {len(tables)} tables:")
        for table in tables:
            print(f"   - {table[0]}")
        
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_data():
    """Test basic data queries"""
    print("\nTesting data access...")
    
    try:
        # Test users
        users = mssql_db.execute_query("SELECT COUNT(*) FROM [user]", fetch_one=True)
        print(f"✅ Users in database: {users[0]}")
        
        # Test samples
        samples = mssql_db.execute_query("SELECT COUNT(*) FROM [sample]", fetch_one=True)
        print(f"✅ Samples in database: {samples[0]}")
        
        # Test current user function
        current_user = get_current_user_mssql()
        print(f"✅ Current user function works: {current_user['Name']}")
        
        return True
    except Exception as e:
        print(f"❌ Data test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("SQL SERVER CONNECTION TEST")
    print("=" * 50)
    
    success = True
    
    # Test connection
    if not test_connection():
        success = False
    
    # Test database structure
    if success and not test_database():
        success = False
    
    # Test data access
    if success and not test_data():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ALL TESTS PASSED! SQL Server is ready.")
    else:
        print("❌ Some tests failed. Check your configuration.")
    print("=" * 50)
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)