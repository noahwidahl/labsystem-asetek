from app.models.container import Container
from app.utils.db import DatabaseManager

class ContainerService:
    def __init__(self, mysql):
        self.mysql = mysql
        self.db = DatabaseManager(mysql)
    
    def get_all_containers(self):
        print("DEBUG: Fetching containers...")
        try:
            # Table name is already known to be 'container'
            cursor = self.mysql.connection.cursor()
            cursor.execute("SHOW TABLES LIKE 'container'")
            table_exists = cursor.fetchone() is not None
            
            print(f"DEBUG: container table exists: {table_exists}")
            
            if not table_exists:
                print("DEBUG: No container table exists!")
                cursor.close()
                return []
            
            table_name = "container"
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
    
    def get_available_containers(self):
        """Gets containers that are available for adding samples"""
        print("DEBUG: Getting available containers...")
        try:
            # Check table name
            query = """
                SELECT 
                    c.ContainerID,
                    c.Description,
                    IFNULL(
                        (SELECT COUNT(cs.ContainerSampleID) 
                        FROM ContainerSample cs 
                        WHERE cs.ContainerID = c.ContainerID), 
                        0
                    ) as sample_count,
                    c.ContainerCapacity,
                    sl.LocationName,
                    (
                        SELECT IFNULL(SUM(cs.Amount), 0) 
                        FROM containersample cs 
                        WHERE cs.ContainerID = c.ContainerID
                    ) as current_amount
                FROM container c
                LEFT JOIN storagelocation sl ON c.LocationID = sl.LocationID
                WHERE c.IsMixed = 1 OR (
                    SELECT IFNULL(SUM(cs.Amount), 0) 
                    FROM containersample cs 
                    WHERE cs.ContainerID = c.ContainerID
                ) < IFNULL(c.ContainerCapacity, 999999) OR c.ContainerCapacity IS NULL
                ORDER BY c.ContainerID DESC
            """
            
            result, _ = self.db.execute_query(query)
            containers = []
            
            if result:
                for row in result:
                    # Calculate available capacity
                    capacity = row[3] if row[3] is not None else 999999
                    current_amount = row[5] if len(row) > 5 else 0
                    available_capacity = capacity - current_amount
                    
                    containers.append({
                        'ContainerID': row[0],
                        'Description': row[1],
                        'sample_count': row[2],
                        'ContainerCapacity': row[3],
                        'available_capacity': available_capacity,
                        'LocationName': row[4] if len(row) > 4 else 'Unknown'
                    })
            
            print(f"DEBUG: Found {len(containers)} available containers")
            return containers
        except Exception as e:
            print(f"DEBUG: Error in get_available_containers: {e}")
            import traceback
            traceback.print_exc()
            return []

    def delete_container(self, container_id, user_id):
        print(f"DEBUG: delete_container called with container_id={container_id}, user_id={user_id}")
        try:
            with self.db.transaction() as cursor:
                # Table name is already known to be 'container'
                cursor.execute("SHOW TABLES LIKE 'container'")
                table_exists = cursor.fetchone() is not None
                
                if not table_exists:
                    print("DEBUG: No container table exists!")
                    return {
                        'success': False,
                        'error': 'Container table does not exist'
                    }
                
                table_name = "container"
                
                # Delete container's samples first if any
                # Instead of preventing deletion, we'll delete the container-sample links
                cursor.execute("""
                    DELETE FROM ContainerSample 
                    WHERE ContainerID = %s
                """, (container_id,))
                
                deleted_samples = cursor.rowcount
                print(f"DEBUG: Deleted {deleted_samples} sample links from container {container_id}")
                
                # Delete the container
                cursor.execute(f"""
                    DELETE FROM {table_name}
                    WHERE ContainerID = %s
                """, (container_id,))
                
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
                    'Container deleted',
                    user_id,
                    f"Container {container_id} deleted with {deleted_samples} sample links"
                ))
                
                return {
                    'success': True,
                    'container_id': container_id
                }
        except Exception as e:
            print(f"DEBUG: Error in delete_container: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def get_container_location(self, container_id):
        """Gets the location for a container"""
        print(f"DEBUG: Getting location for container {container_id}")
        try:
            # First check direct container.LocationID (new approach)
            query = """
                SELECT sl.LocationID, sl.LocationName
                FROM container c
                JOIN storagelocation sl ON c.LocationID = sl.LocationID
                WHERE c.ContainerID = %s
            """
            
            result, _ = self.db.execute_query(query, (container_id,))
            
            if result and len(result) > 0:
                return {
                    'LocationID': result[0][0],
                    'LocationName': result[0][1]
                }
            
            # Fallback: Find from contained samples (old approach)
            query = """
                SELECT DISTINCT ss.LocationID, sl.LocationName
                FROM containersample cs
                JOIN samplestorage ss ON cs.SampleStorageID = ss.StorageID
                JOIN storagelocation sl ON ss.LocationID = sl.LocationID
                WHERE cs.ContainerID = %s
                LIMIT 1
            """
            
            result, _ = self.db.execute_query(query, (container_id,))
            
            if result and len(result) > 0:
                # Update the container with this location for future use
                with self.db.transaction() as cursor:
                    cursor.execute("""
                        UPDATE container 
                        SET LocationID = %s 
                        WHERE ContainerID = %s
                    """, (result[0][0], container_id))
                
                return {
                    'LocationID': result[0][0],
                    'LocationName': result[0][1]
                }
            else:
                print(f"DEBUG: No location found for container {container_id}")
                return None
        except Exception as e:
            print(f"DEBUG: Error in get_container_location: {e}")
            import traceback
            traceback.print_exc()
            return None

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
            
            # Get container location
            try:
                # Get location information
                query = """
                    SELECT sl.LocationName 
                    FROM container c
                    LEFT JOIN storagelocation sl ON c.LocationID = sl.LocationID
                    WHERE c.ContainerID = %s
                """
                result, _ = self.db.execute_query(query, (container.id,))
                
                if result and len(result) > 0 and result[0][0]:
                    container.location_name = result[0][0]
                else:
                    container.location_name = 'Unknown'
            except Exception as e:
                print(f"DEBUG: Error getting container location: {e}")
                container.location_name = 'Unknown'
            
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
                # Use 'container' table
                table_name = "container"
                
                # Verify the table exists
                cursor.execute("SHOW TABLES LIKE 'container'")
                if cursor.fetchone() is None:
                    return {
                        'success': False,
                        'error': 'Container table does not exist'
                    }
                
                print(f"DEBUG: Using table name: {table_name}")
                container = Container.from_dict(container_data)
                
                # Print container object
                print(f"DEBUG: Container object created: {container.__dict__}")
                
                # Get a default location ID (1.1.1) if none provided
                location_id = container_data.get('locationId')
                if not location_id:
                    # Try to find the default location (1.1.1)
                    cursor.execute("""
                        SELECT LocationID FROM storagelocation 
                        WHERE LocationName = '1.1.1' 
                        LIMIT 1
                    """)
                    result = cursor.fetchone()
                    if result:
                        location_id = result[0]
                
                # Check if we need to create a new container type
                new_container_type = container_data.get('newContainerType')
                if new_container_type:
                    print(f"DEBUG: Creating new container type: {new_container_type}")
                    
                    # Insert the new container type
                    cursor.execute("""
                        INSERT INTO ContainerType (
                            TypeName,
                            Description,
                            DefaultCapacity
                        )
                        VALUES (%s, %s, %s)
                    """, (
                        new_container_type.get('typeName'),
                        new_container_type.get('description', ''),
                        new_container_type.get('capacity')
                    ))
                    
                    # Get the new container type ID
                    container_type_id = cursor.lastrowid
                    print(f"DEBUG: Created new container type with ID: {container_type_id}")
                    
                    # Update the container object with the new type ID
                    container.container_type_id = container_type_id
                    
                    # IMPORTANT: Always use the new container type's capacity for the container
                    # This fixes the issue where capacity validation was preventing progression
                    container.capacity = new_container_type.get('capacity')
                    print(f"DEBUG: Using capacity {container.capacity} from new container type")
                    
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
                        'Container type created',
                        user_id,
                        f"Container type '{new_container_type.get('typeName')}' created"
                    ))
                
                # Add the location_id to the insert query
                if container.container_type_id:
                    # If no capacity provided and we're not creating a new type, get default from existing container type
                    capacity = container.capacity
                    if not capacity and not new_container_type:
                        # Get default capacity from container type
                        cursor.execute("""
                            SELECT DefaultCapacity 
                            FROM ContainerType 
                            WHERE ContainerTypeID = %s
                        """, (container.container_type_id,))
                        
                        type_result = cursor.fetchone()
                        if type_result and type_result[0]:
                            capacity = type_result[0]
                            print(f"DEBUG: Using default capacity {capacity} from existing container type {container.container_type_id}")
                    
                    query = f"""
                        INSERT INTO {table_name} (
                            Description, 
                            ContainerTypeID,
                            IsMixed,
                            ContainerCapacity,
                            LocationID
                        )
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    
                    cursor.execute(query, (
                        container.description,
                        container.container_type_id,
                        1 if container.is_mixed else 0,
                        capacity,
                        location_id
                    ))
                else:
                    query = f"""
                        INSERT INTO {table_name} (
                            Description,
                            IsMixed,
                            ContainerCapacity,
                            LocationID
                        )
                        VALUES (%s, %s, %s, %s)
                    """
                    
                    cursor.execute(query, (
                        container.description,
                        1 if container.is_mixed else 0,
                        container.capacity,
                        location_id
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
            
    def add_sample_to_container(self, container_id, sample_id, amount=1, user_id=None, force_add=False):
        print(f"DEBUG: add_sample_to_container called with container_id={container_id}, sample_id={sample_id}, amount={amount}, force_add={force_add}")
        try:
            with self.db.transaction() as cursor:
                # Container table is just named 'container' in this database
                container_table = "container"
                
                # Check if container exists and get its capacity
                cursor.execute(f"""
                    SELECT c.ContainerID, c.ContainerCapacity, 
                           IFNULL((SELECT SUM(cs.Amount) FROM ContainerSample cs WHERE cs.ContainerID = c.ContainerID), 0) as CurrentAmount 
                    FROM {container_table} c
                    WHERE c.ContainerID = %s
                """, (container_id,))
                
                container_data = cursor.fetchone()
                if not container_data:
                    return {
                        'success': False,
                        'error': f'Container with ID {container_id} does not exist'
                    }
                
                container_capacity = container_data[1] 
                current_amount = container_data[2]
                
                # Check if adding this sample would exceed the container's capacity
                if container_capacity and not force_add:
                    new_total = current_amount + amount
                    if new_total > container_capacity:
                        return {
                            'success': False,
                            'warning': True,
                            'capacity_exceeded': True,
                            'error': f'Adding {amount} samples would exceed the container capacity of {container_capacity}. Current amount: {current_amount}',
                            'current_amount': current_amount,
                            'new_amount': new_total,
                            'capacity': container_capacity
                        }
                
                # Check if sample exists and is available
                cursor.execute("""
                    SELECT s.SampleID, ss.StorageID, ss.AmountRemaining, ss.LocationID
                    FROM Sample s
                    JOIN SampleStorage ss ON s.SampleID = ss.SampleID
                    WHERE s.SampleID = %s AND ss.AmountRemaining >= %s
                """, (sample_id, amount))
                
                sample_data = cursor.fetchone()
                if not sample_data:
                    return {
                        'success': False,
                        'error': f'Sample with ID {sample_id} does not exist or has insufficient quantity'
                    }
                
                storage_id = sample_data[1]
                sample_location_id = sample_data[3]
                
                # Update container's location to match the sample's location if not set
                cursor.execute("""
                    SELECT LocationID FROM container WHERE ContainerID = %s
                """, (container_id,))
                container_location = cursor.fetchone()
                
                if not container_location or not container_location[0]:
                    # Container has no location, set it to sample's location
                    cursor.execute("""
                        UPDATE container SET LocationID = %s WHERE ContainerID = %s
                    """, (sample_location_id, container_id))
                    print(f"DEBUG: Updated container {container_id} location to {sample_location_id}")
                
                # Check if ContainerSample table exists, create if it doesn't
                cursor.execute("SHOW TABLES LIKE 'ContainerSample'")
                if cursor.fetchone() is None:
                    print("DEBUG: Creating ContainerSample table")
                    cursor.execute("""
                        CREATE TABLE ContainerSample (
                            ContainerSampleID INT AUTO_INCREMENT PRIMARY KEY,
                            SampleStorageID INT NOT NULL,
                            ContainerID INT NOT NULL,
                            Amount INT NOT NULL DEFAULT 1
                        )
                    """)
                
                # Add the sample to the container
                cursor.execute("""
                    INSERT INTO ContainerSample (
                        SampleStorageID,
                        ContainerID,
                        Amount
                    )
                    VALUES (%s, %s, %s)
                """, (
                    storage_id,
                    container_id,
                    amount
                ))
                
                container_sample_id = cursor.lastrowid
                
                # Reduce the amount in storage
                cursor.execute("""
                    UPDATE SampleStorage 
                    SET AmountRemaining = AmountRemaining - %s
                    WHERE StorageID = %s AND AmountRemaining >= %s
                """, (amount, storage_id, amount))
                
                # Log the activity
                if user_id:
                    # Add a note if we're exceeding capacity
                    capacity_note = ""
                    if container_capacity and current_amount + amount > container_capacity:
                        capacity_note = f" (Container capacity exceeded: {current_amount + amount}/{container_capacity})"
                    
                    cursor.execute("""
                        INSERT INTO History (
                            Timestamp, 
                            ActionType, 
                            UserID, 
                            SampleID,
                            Notes
                        )
                        VALUES (NOW(), %s, %s, %s, %s)
                    """, (
                        'Sample added to container',
                        user_id,
                        sample_id,
                        f"Sample {sample_id} added to Container {container_id}, amount: {amount}{capacity_note}"
                    ))
                
                return {
                    'success': True,
                    'container_sample_id': container_sample_id,
                    'capacity_warning': container_capacity and current_amount + amount > container_capacity
                }
                
        except Exception as e:
            print(f"DEBUG: Error in add_sample_to_container: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }