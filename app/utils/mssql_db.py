"""
Microsoft SQL Server database utility module for LabSystem.
Provides connection and query execution functions for SQL Server.
"""
import pyodbc
import os
from contextlib import contextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MSSQLConnection:
    """Microsoft SQL Server connection handler"""
    
    def __init__(self):
        self.server = os.getenv('MSSQL_SERVER')
        self.database = os.getenv('MSSQL_DATABASE')
        self.username = os.getenv('MSSQL_USERNAME')
        self.password = os.getenv('MSSQL_PASSWORD')
        self.driver = os.getenv('MSSQL_DRIVER', 'ODBC Driver 18 for SQL Server')
        self.trust_cert = os.getenv('MSSQL_TRUST_CERT', 'yes')
        
    def get_connection_string(self):
        """Build SQL Server connection string"""
        if self.username and self.password:
            # SQL Server authentication
            conn_str = (
                f"DRIVER={{{self.driver}}};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
                f"TrustServerCertificate={self.trust_cert};"
            )
        else:
            # Windows/Trusted authentication
            conn_str = (
                f"DRIVER={{{self.driver}}};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"Trusted_Connection=yes;"
                f"TrustServerCertificate={self.trust_cert};"
            )
        
        return conn_str
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn_str = self.get_connection_string()
            conn = pyodbc.connect(conn_str)
            logger.debug("Connected to SQL Server successfully")
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
                logger.debug("Database connection closed")
    
    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        """Execute a query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()
                else:
                    conn.commit()
                    return cursor.rowcount
                    
            except Exception as e:
                logger.error(f"Query execution error: {e}")
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    def execute_many(self, query, params_list):
        """Execute a query multiple times with different parameters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount
            except Exception as e:
                logger.error(f"Batch execution error: {e}")
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                logger.error(f"Transaction error: {e}")
                conn.rollback()
                raise
            finally:
                cursor.close()

# Global instance
mssql_db = MSSQLConnection()

def get_current_user_mssql(user_login=None):
    """
    Gets or creates a user in SQL Server database based on Windows/domain authentication.
    Compatible with the existing get_current_user function.
    """
    # Default admin user as fallback
    default_user = {"UserID": 1, "Name": "System Admin", "WindowsLogin": "SYSTEM", "Role": "Admin"}
    
    if not user_login:
        # Get from environment or use default method
        import platform
        if platform.system() == 'Windows':
            userdomain = os.environ.get('USERDOMAIN', '')
            username = os.environ.get('USERNAME', '')
            user_login = f"{userdomain}\\{username}" if userdomain and username else username
        else:
            user_login = os.environ.get('USER', '')
    
    if not user_login:
        logger.warning("No user login found, using default admin")
        return default_user
    
    try:
        # First try to find user by WindowsLogin
        query = "SELECT TOP 1 [UserID], [Name], [WindowsLogin], [Role] FROM [user] WHERE [WindowsLogin] = ?"
        user = mssql_db.execute_query(query, (user_login,), fetch_one=True)
        
        if user:
            logger.info(f"Found existing user: {user[1]} ({user[2]})")
            return {
                "UserID": user[0], 
                "Name": user[1], 
                "WindowsLogin": user[2],
                "Role": user[3] or "Admin",
                "IsAdmin": True
            }
        
        # User doesn't exist, create them
        logger.info(f"Creating new user for login: {user_login}")
        
        # Extract display name from login
        display_name = user_login.split('\\')[-1].split('@')[0]
        
        # Insert new user
        insert_query = """
            INSERT INTO [user] ([Name], [WindowsLogin], [Role]) 
            VALUES (?, ?, ?)
        """
        mssql_db.execute_query(insert_query, (display_name, user_login, 'Admin'))
        
        # Get the new user
        user = mssql_db.execute_query(query, (user_login,), fetch_one=True)
        
        if user:
            logger.info(f"Created new user with ID: {user[0]}")
            return {
                "UserID": user[0],
                "Name": user[1],
                "WindowsLogin": user[2],
                "Role": user[3] or "Admin",
                "IsAdmin": True
            }
        else:
            logger.error("Failed to retrieve newly created user")
            return default_user
            
    except Exception as e:
        logger.error(f"Error in get_current_user_mssql: {e}")
        return default_user