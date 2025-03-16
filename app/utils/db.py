from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, mysql):
        self.mysql = mysql
    
    @contextmanager
    def transaction(self, isolation_level=None):
        """
        Context manager til håndtering af database-transaktioner.
        
        Usage:
            with db_manager.transaction():
                # database operationer her
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
            raise e
        finally:
            cursor.close()