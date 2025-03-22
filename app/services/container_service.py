from app.models.container import Container
from app.utils.db import DatabaseManager

class ContainerService:
    def __init__(self, mysql):
        self.mysql = mysql
        self.db = DatabaseManager(mysql)
    
    def get_all_containers(self):
        print("DEBUG: Fetching containers...")
        try:
            # First: Check both possible table names (container and Container)
            cursor = self.mysql.connection.cursor()
            cursor.execute("SHOW TABLES LIKE 'container'")
            lowercase_exists = cursor.fetchone() is not None
            
            cursor.execute("SHOW TABLES LIKE 'Container'")
            uppercase_exists = cursor.fetchone() is not None
            
            print(f"DEBUG: lowercase container table exists: {lowercase_exists}")
            print(f"DEBUG: uppercase Container table exists: {uppercase_exists}")
            
            if not lowercase_exists and not uppercase_exists:
                print("DEBUG: No container table exists!")
                cursor.close()
                return []
            
            # Use the table name that exists
            table_name = "container" if lowercase_exists else "Container"
            cursor.close()
            
            # If table exists, continue fetching data
            query = f"""
                SELECT 
                    c.ContainerID,
                    c.Description,
                    c.ContainerTypeID,
                    c.IsMixed,
                    c.ContainerCapacity,
                    'Active' as Status
                FROM {table_name} c
                ORDER BY c.ContainerID DESC
            """
            
            result, _ = self.db.execute_query(query)
            print(f"DEBUG: Container query returned {len(result) if result else 0} rows")
            
            # If no results, return empty list
            if not result:
                print("DEBUG: No containers found in database")
                return []
            
            containers = []
            for row in result:
                try:
                    print(f"DEBUG: Processing container row: {row}")
                    container = Container.from_db_row(row)
                    
                    # Fetch extra information
                    container_with_info = self._add_container_info(container)
                    containers.append(container_with_info)
                except Exception as e:
                    print(f"DEBUG: Error processing container row: {e}")
            
            print(f"DEBUG: Returning {len(containers)} containers")
            return containers
        except Exception as e:
            print(f"DEBUG: General error in get_all_containers: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _add_container_info(self, container):
        try:
            # Add type name
            if container.container_type_id:
                query = "SELECT TypeName FROM ContainerType WHERE ContainerTypeID = %s"
                result, _ = self.db.execute_query(query, (container.container_type_id,))
                if result and len(result) > 0:
                    container.type_name = result[0][0]
            else:
                container.type_name = 'Standard'
            
            # Count number of samples - check both table names
            try:
                cursor = self.mysql.connection.cursor()
                cursor.execute("SHOW TABLES LIKE 'ContainerSample'")
                sample_table_exists = cursor.fetchone() is not None
                cursor.close()
                
                if sample_table_exists:
                    query = """
                        SELECT COUNT(ContainerSampleID) as SampleCount, IFNULL(SUM(Amount), 0) as TotalItems 
                        FROM ContainerSample 
                        WHERE ContainerID = %s
                    """
                    result, _ = self.db.execute_query(query, (container.id,))
                    
                    if result and len(result) > 0:
                        container.sample_count = result[0][0] or 0
                        container.total_items = result[0][1] or 0
                    else:
                        container.sample_count = 0
                        container.total_items = 0
                else:
                    print("DEBUG: ContainerSample table not found")
                    container.sample_count = 0
                    container.total_items = 0
            except Exception as e:
                print(f"DEBUG: Error attempting to count samples: {e}")
                container.sample_count = 0
                container.total_items = 0
            
            return container
        except Exception as e:
            print(f"DEBUG: Error in _add_container_info: {e}")
            # Make sure we still return the container object even with errors
            container.type_name = 'Standard'
            container.sample_count = 0
            container.total_items = 0
            return container
    
    def create_container(self, container_data, user_id):
        print(f"DEBUG: create_container called with data: {container_data}")
        try:
            with self.db.transaction() as cursor:
                # Check both possible table names
                cursor.execute("SHOW TABLES LIKE 'container'")
                lowercase_exists = cursor.fetchone() is not None
                
                cursor.execute("SHOW TABLES LIKE 'Container'")
                uppercase_exists = cursor.fetchone() is not None
                
                if not lowercase_exists and not uppercase_exists:
                    # No container table exists - create it
                    print("DEBUG: Creating container table")
                    cursor.execute("""
                        CREATE TABLE container (
                            ContainerID INT AUTO_INCREMENT PRIMARY KEY,
                            Description VARCHAR(255) NOT NULL,
                            ContainerTypeID INT NULL,
                            IsMixed TINYINT(1) DEFAULT 0,
                            ContainerCapacity INT NULL
                        )
                    """)
                    table_name = "container"
                else:
                    # Use the table name that exists
                    table_name = "container" if lowercase_exists else "Container"
                
                print(f"DEBUG: Using table name: {table_name}")
                container = Container.from_dict(container_data)
                
                # Print container object
                print(f"DEBUG: Container object created: {container.__dict__}")
                
                if container.container_type_id:
                    query = f"""
                        INSERT INTO {table_name} (
                            Description, 
                            ContainerTypeID,
                            IsMixed,
                            ContainerCapacity
                        )
                        VALUES (%s, %s, %s, %s)
                    """
                    
                    cursor.execute(query, (
                        container.description,
                        container.container_type_id,
                        1 if container.is_mixed else 0,
                        container.capacity
                    ))
                else:
                    query = f"""
                        INSERT INTO {table_name} (
                            Description,
                            IsMixed,
                            ContainerCapacity
                        )
                        VALUES (%s, %s, %s)
                    """
                    
                    cursor.execute(query, (
                        container.description,
                        1 if container.is_mixed else 0,
                        container.capacity
                    ))
                
                container_id = cursor.lastrowid
                print(f"DEBUG: Container created with ID: {container_id}")
                
                # Log the activity
                cursor.execute("""
                    INSERT INTO History (
                        Timestamp, 
                        ActionType, 
                        UserID, 
                        Notes
                    )
                    VALUES (NOW(), %s, %s, %s)
                """, (
                    'Container created',
                    user_id,
                    f"Container {container_id} created: {container.description}"
                ))
                
                return {
                    'success': True,
                    'container_id': container_id
                }
        except Exception as e:
            print(f"DEBUG: Error in create_container: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }