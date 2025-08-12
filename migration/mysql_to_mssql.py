#!/usr/bin/env python3
"""
Migration script to transfer data from MySQL to Microsoft SQL Server.
Handles data type conversion and maintains referential integrity.
"""

import os
import sys
import json
from datetime import datetime
import logging
from dotenv import load_dotenv

# Add app to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MySQL imports
try:
    import MySQLdb
    from MySQLdb import cursors
except ImportError:
    print("MySQLdb not found, trying mysql.connector")
    import mysql.connector as MySQLdb
    cursors = None

# SQL Server imports
import pyodbc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # MySQL connection details
        self.mysql_config = {
            'host': os.getenv('MYSQL_HOST'),
            'user': os.getenv('MYSQL_USER'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DB')
        }
        
        # SQL Server connection details
        self.mssql_server = os.getenv('MSSQL_SERVER')
        self.mssql_database = os.getenv('MSSQL_DATABASE')
        self.mssql_username = os.getenv('MSSQL_USERNAME')
        self.mssql_password = os.getenv('MSSQL_PASSWORD')
        self.mssql_driver = os.getenv('MSSQL_DRIVER', 'ODBC Driver 18 for SQL Server')
        
        # Table migration order (respecting foreign keys)
        self.migration_order = [
            'lab',
            'user',
            'unit', 
            'containertype',
            'storagelocation',
            'supplier',
            'task',
            'reception',
            'sample',
            'sampleserialnumber',
            'samplestorage',
            'container',
            'containersample',
            'test',
            'testsampleusage',
            'tasksample',
            'expirationnotification',
            'history'
        ]
        
    def get_mysql_connection(self):
        """Get MySQL database connection"""
        try:
            if cursors:
                conn = MySQLdb.connect(
                    host=self.mysql_config['host'],
                    user=self.mysql_config['user'],
                    password=self.mysql_config['password'],
                    database=self.mysql_config['database'],
                    cursorclass=cursors.DictCursor
                )
            else:
                conn = MySQLdb.connect(**self.mysql_config)
            logger.info("Connected to MySQL successfully")
            return conn
        except Exception as e:
            logger.error(f"MySQL connection failed: {e}")
            raise
    
    def get_mssql_connection(self):
        """Get SQL Server database connection"""
        try:
            if self.mssql_username and self.mssql_password:
                conn_str = (
                    f"DRIVER={{{self.mssql_driver}}};"
                    f"SERVER={self.mssql_server};"
                    f"DATABASE={self.mssql_database};"
                    f"UID={self.mssql_username};"
                    f"PWD={self.mssql_password};"
                    f"TrustServerCertificate=yes;"
                )
            else:
                conn_str = (
                    f"DRIVER={{{self.mssql_driver}}};"
                    f"SERVER={self.mssql_server};"
                    f"DATABASE={self.mssql_database};"
                    f"Trusted_Connection=yes;"
                    f"TrustServerCertificate=yes;"
                )
            
            conn = pyodbc.connect(conn_str)
            logger.info("Connected to SQL Server successfully")
            return conn
        except Exception as e:
            logger.error(f"SQL Server connection failed: {e}")
            raise
    
    def convert_value(self, value, column_name, table_name):
        """Convert MySQL values to SQL Server compatible values"""
        if value is None:
            return None
            
        # Handle JSON columns (TeamMembers in task table)
        if table_name == 'task' and column_name == 'TeamMembers':
            if isinstance(value, str):
                try:
                    # Verify it's valid JSON
                    json.loads(value)
                    return value
                except:
                    return None
            elif isinstance(value, (list, dict)):
                return json.dumps(value)
        
        # Handle boolean values (MySQL tinyint to SQL Server bit)
        boolean_columns = {
            'sample': ['IsUnique'],
            'container': ['IsMixed'],
            'sampleserialnumber': ['IsActive'],
            'expirationnotification': ['IsRead']
        }
        
        if table_name in boolean_columns and column_name in boolean_columns[table_name]:
            return 1 if value else 0
        
        # Handle datetime values
        if isinstance(value, datetime):
            return value
            
        return value
    
    def get_table_data(self, mysql_conn, table_name):
        """Get all data from MySQL table"""
        try:
            cursor = mysql_conn.cursor()
            cursor.execute(f"SELECT * FROM `{table_name}`")
            
            if cursors:
                # If using DictCursor
                rows = cursor.fetchall()
                columns = list(rows[0].keys()) if rows else []
            else:
                # If using regular cursor
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
            
            cursor.close()
            logger.info(f"Retrieved {len(rows)} rows from {table_name}")
            return columns, rows
            
        except Exception as e:
            logger.error(f"Error reading from {table_name}: {e}")
            raise
    
    def insert_table_data(self, mssql_conn, table_name, columns, rows):
        """Insert data into SQL Server table"""
        if not rows:
            logger.info(f"No data to insert into {table_name}")
            return
            
        try:
            cursor = mssql_conn.cursor()
            
            # Build INSERT statement
            columns_str = ', '.join([f'[{col}]' for col in columns])
            placeholders = ', '.join(['?' for _ in columns])
            
            # Handle IDENTITY columns
            identity_tables = {
                'lab': 'LabID',
                'user': 'UserID', 
                'unit': 'UnitID',
                'containertype': 'ContainerTypeID',
                'storagelocation': 'LocationID',
                'supplier': 'SupplierID',
                'task': 'TaskID',
                'reception': 'ReceptionID',
                'sample': 'SampleID',
                'sampleserialnumber': 'SerialNumberID',
                'samplestorage': 'StorageID',
                'container': 'ContainerID',
                'containersample': 'ContainerSampleID',
                'test': 'TestID',
                'testsampleusage': 'UsageID',
                'tasksample': 'TaskSampleID',
                'expirationnotification': 'NotificationID',
                'history': 'LogID'
            }
            
            if table_name in identity_tables:
                cursor.execute(f"SET IDENTITY_INSERT [{table_name}] ON")
            
            insert_sql = f"INSERT INTO [{table_name}] ({columns_str}) VALUES ({placeholders})"
            
            # Convert and insert data
            converted_rows = []
            for row in rows:
                if cursors:
                    # DictCursor - row is a dictionary
                    converted_row = [self.convert_value(row[col], col, table_name) for col in columns]
                else:
                    # Regular cursor - row is a tuple
                    converted_row = [self.convert_value(row[i], columns[i], table_name) for i in range(len(columns))]
                converted_rows.append(tuple(converted_row))
            
            cursor.executemany(insert_sql, converted_rows)
            
            if table_name in identity_tables:
                cursor.execute(f"SET IDENTITY_INSERT [{table_name}] OFF")
            
            mssql_conn.commit()
            logger.info(f"Successfully inserted {len(converted_rows)} rows into {table_name}")
            
        except Exception as e:
            logger.error(f"Error inserting into {table_name}: {e}")
            mssql_conn.rollback()
            raise
        finally:
            cursor.close()
    
    def clear_table_data(self, mssql_conn, table_name):
        """Clear existing data from SQL Server table"""
        try:
            cursor = mssql_conn.cursor()
            cursor.execute(f"DELETE FROM [{table_name}]")
            mssql_conn.commit()
            cursor.close()
            logger.info(f"Cleared existing data from {table_name}")
        except Exception as e:
            logger.warning(f"Could not clear {table_name}: {e}")
    
    def migrate_table(self, table_name):
        """Migrate a single table"""
        logger.info(f"Starting migration of table: {table_name}")
        
        mysql_conn = None
        mssql_conn = None
        
        try:
            # Get connections
            mysql_conn = self.get_mysql_connection()
            mssql_conn = self.get_mssql_connection()
            
            # Get data from MySQL
            columns, rows = self.get_table_data(mysql_conn, table_name)
            
            if not rows:
                logger.info(f"Table {table_name} is empty, skipping")
                return True
            
            # Clear existing data in SQL Server (optional)
            # self.clear_table_data(mssql_conn, table_name)
            
            # Insert data into SQL Server
            self.insert_table_data(mssql_conn, table_name, columns, rows)
            
            logger.info(f"Successfully migrated table: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate table {table_name}: {e}")
            return False
            
        finally:
            if mysql_conn:
                mysql_conn.close()
            if mssql_conn:
                mssql_conn.close()
    
    def run_migration(self, clear_target=False):
        """Run the complete migration"""
        logger.info("Starting MySQL to SQL Server migration")
        start_time = datetime.now()
        
        successful_tables = []
        failed_tables = []
        
        for table_name in self.migration_order:
            logger.info(f"Migrating table {table_name}...")
            try:
                success = self.migrate_table(table_name)
                if success:
                    successful_tables.append(table_name)
                else:
                    failed_tables.append(table_name)
            except Exception as e:
                logger.error(f"Migration failed for {table_name}: {e}")
                failed_tables.append(table_name)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Summary
        logger.info("=" * 60)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Start time: {start_time}")
        logger.info(f"End time: {end_time}")
        logger.info(f"Duration: {duration}")
        logger.info(f"Successful tables ({len(successful_tables)}): {', '.join(successful_tables)}")
        
        if failed_tables:
            logger.error(f"Failed tables ({len(failed_tables)}): {', '.join(failed_tables)}")
            return False
        else:
            logger.info("All tables migrated successfully!")
            return True

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("""
MySQL to SQL Server Migration Tool

Usage: python mysql_to_mssql.py [options]

Options:
  --help          Show this help message
  --clear-target  Clear target tables before migration (DESTRUCTIVE!)

Environment variables required:
  MySQL: MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
  SQL Server: MSSQL_SERVER, MSSQL_DATABASE, MSSQL_USERNAME, MSSQL_PASSWORD
        """)
        return
    
    clear_target = '--clear-target' in sys.argv
    
    if clear_target:
        response = input("WARNING: This will DELETE all existing data in SQL Server tables. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled.")
            return
    
    # Run migration
    migrator = DatabaseMigrator()
    success = migrator.run_migration(clear_target=clear_target)
    
    if success:
        print("\nMigration completed successfully!")
        sys.exit(0)
    else:
        print("\nMigration completed with errors. Check migration.log for details.")
        sys.exit(1)

if __name__ == '__main__':
    main()