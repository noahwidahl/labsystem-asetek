from contextlib import contextmanager
from flask import current_app

# Global variable to store the DB manager instance
_db_manager = None

def get_db_manager():
    """
    Singleton pattern to get database manager instance.
    This helps avoid circular imports when db access is needed from models.
    """
    global _db_manager
    
    if _db_manager is None:
        try:
            # Get MySQL instance from app context - this can fail if called outside Flask context
            from app import mysql
            _db_manager = DatabaseManager(mysql)
        except Exception as e:
            # This is a fallback for when this is called outside Flask context
            # It's not ideal but prevents complete failure
            print(f"Error creating DB manager: {e}")
            # Return a simple object with execute_query method
            class DummyManager:
                def execute_query(self, query, params=None):
                    print(f"DUMMY DB MANAGER: Would execute {query} with {params}")
                    return [], None
            _db_manager = DummyManager()
    
    return _db_manager

class DatabaseManager:
    def __init__(self, mysql):
        self.mysql = mysql
    
    @contextmanager
    def transaction(self, isolation_level=None):
        """
        Context manager for handling database transactions.
        
        Usage:
            with db_manager.transaction():
                # database operations here
        """
        cursor = self.mysql.connection.cursor()
        try:
            # Set isolation level if specified
            if isolation_level:
                cursor.execute(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")
                
            cursor.execute("START TRANSACTION")
            yield cursor
            self.mysql.connection.commit()
        except Exception as e:
            self.mysql.connection.rollback()
            raise e
        finally:
            cursor.close()
    
    def execute_query(self, query, params=None, commit=False):
        cursor = self.mysql.connection.cursor()
        try:
            # Add enhanced debugging for string format issues
            if '%' in query:
                print(f"DEBUG DB: Query contains % character: {query}")
                if params is None or len(params) == 0:
                    print("DEBUG DB: WARNING - Query contains % but has no parameters!")
                    # Try to escape % characters in the query
                    modified_query = query.replace('%', '%%')
                    print(f"DEBUG DB: Modified query: {modified_query}")
                    query = modified_query

            # Execute the query
            result = cursor.execute(query, params or ())
            rows = cursor.fetchall() if cursor.description else []
            
            print(f"DEBUG DB: Executed query: {query}")
            print(f"DEBUG DB: Params: {params}")
            print(f"DEBUG DB: Result rows: {len(rows)}")
            
            if commit:
                self.mysql.connection.commit()
                print(f"DEBUG DB: Changes committed")
            
            return rows, cursor.lastrowid
        except Exception as e:
            if commit:
                self.mysql.connection.rollback()
                print(f"DEBUG DB: Error, rolled back changes: {e}")
            print(f"DEBUG DB: Query error: {e}")
            
            # Enhanced error reporting for format string errors
            if "not enough arguments for format string" in str(e):
                print(f"DEBUG DB: FORMAT ERROR - Query: {query}")
                print(f"DEBUG DB: FORMAT ERROR - Params: {params}")
                print("DEBUG DB: This is likely caused by unescaped % characters in the query")
                if "LIKE" in query and "%" in query:
                    print("DEBUG DB: Query contains LIKE and %. Try escaping % with %%")
            
            raise e
        finally:
            cursor.close()