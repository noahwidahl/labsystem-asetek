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
                    'Active' as Status,
                    c.LocationID
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
                    container = Container.from_db_row(row)
                    
                    # Add additional calculated fields using additional query
                    container = self._add_container_info(container)
                    
                    containers.append(container)
                except Exception as e:
                    print(f"DEBUG: Error creating container object: {e}")
                    continue
            
            return containers
        except Exception as e:
            print(f"DEBUG: Error in get_all_containers: {e}")
            import traceback
            traceback.print_exc()
            return []
            
    def get_container_by_id(self, container_id):
        print(f"DEBUG: Getting container with ID {container_id}")
        try:
            query = f"""
                SELECT 
                    c.ContainerID,
                    c.Description,
                    c.ContainerTypeID,
                    c.IsMixed,
                    c.ContainerCapacity,
                    'Active' as Status,
                    c.LocationID
                FROM container c
                WHERE c.ContainerID = %s
            """
            
            result, _ = self.db.execute_query(query, (container_id,))
            
            if not result or len(result) == 0:
                print(f"DEBUG: No container found with ID {container_id}")
                return None
            
            container = Container.from_db_row(result[0])
            
            # Add additional calculated fields
            container = self._add_container_info(container)
            
            return container
        except Exception as e:
            print(f"DEBUG: Error in get_container_by_id: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_container_location(self, container_id):
        try:
            query = """
                SELECT 
                    l.LocationID,
                    l.LocationName,
                    l.Rack,
                    l.Section,
                    l.Shelf
                FROM container c
                JOIN StorageLocation l ON c.LocationID = l.LocationID
                WHERE c.ContainerID = %s
            """
            
            result, cursor = self.db.execute_query(query, (container_id,))
            
            if not result or len(result) == 0:
                return None
            
            columns = [col[0] for col in cursor.description]
            location = dict(zip(columns, result[0]))
            
            return location
        except Exception as e:
            print(f"DEBUG: Error in get_container_location: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_available_containers(self):
        try:
            # Dette er en mere robust version, der også beregner tilgængelig kapacitet
            query = f"""
                SELECT 
                    c.ContainerID,
                    c.Description,
                    ct.TypeName,
                    c.ContainerCapacity,
                    IFNULL(SUM(cs.Amount), 0) as CurrentAmount,
                    l.LocationName
                FROM container c
                LEFT JOIN ContainerType ct ON c.ContainerTypeID = ct.ContainerTypeID
                LEFT JOIN ContainerSample cs ON c.ContainerID = cs.ContainerID
                LEFT JOIN StorageLocation l ON c.LocationID = l.LocationID
                GROUP BY c.ContainerID
                HAVING CurrentAmount < c.ContainerCapacity OR c.ContainerCapacity IS NULL
            """
            
            # Direkte brug af MySQL cursor i stedet for db utils
            cursor = self.mysql.connection.cursor()
            cursor.execute(query)
            
            # Konverterer rå resultater til dict
            columns = [col[0] for col in cursor.description]
            containers = []
            
            for row in cursor.fetchall():
                container_dict = dict(zip(columns, row))
                
                # Beregn tilgængelig kapacitet
                container_capacity = container_dict.get('ContainerCapacity')
                current_amount = container_dict.get('CurrentAmount', 0)
                
                # Tilføj beregnede felter som frontend forventer
                if container_capacity is not None:
                    container_dict['available_capacity'] = container_capacity - current_amount
                
                # Tilføj sample_count for kompatibilitet med frontend
                container_dict['sample_count'] = current_amount
                
                containers.append(container_dict)
            
            cursor.close()
            print(f"DEBUG: Returning {len(containers)} available containers")
            
            return containers
        except Exception as e:
            print(f"DEBUG: Error in get_available_containers: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _add_container_info(self, container):
        try:
            # Get container type name
            cursor = self.mysql.connection.cursor()
            
            # Get type info
            cursor.execute("""
                SELECT TypeName 
                FROM containertype 
                WHERE ContainerTypeID = %s
            """, (container.container_type_id,))
            
            type_result = cursor.fetchone()
            if type_result:
                container.type_name = type_result[0]
            else:
                container.type_name = 'Unknown'
                
            # Get location name
            if hasattr(container, 'location_id') and container.location_id:
                cursor.execute("""
                    SELECT LocationName 
                    FROM storagelocation 
                    WHERE LocationID = %s
                """, (container.location_id,))
                
                location_result = cursor.fetchone()
                if location_result:
                    container.location_name = location_result[0]
                else:
                    container.location_name = 'Unknown'
            else:
                container.location_name = 'Not assigned'
                
            # Get count of samples in container
            cursor.execute("""
                SELECT 
                    COUNT(*) as SampleCount,
                    IFNULL(SUM(Amount), 0) as TotalItems
                FROM containersample 
                WHERE ContainerID = %s
            """, (container.id,))
            
            count_result = cursor.fetchone()
            cursor.close()
            
            if count_result:
                container.sample_count = count_result[0]
                container.total_items = count_result[1]
            else:
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
    
    def _generate_unique_container_barcode(self, cursor):
        """
        Generate a unique container barcode that doesn't already exist in the database
        """
        attempt = 1
        max_attempts = 1000  # Prevent infinite loop
        
        while attempt <= max_attempts:
            # First try with the AUTO_INCREMENT value
            if attempt == 1:
                cursor.execute("SELECT AUTO_INCREMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'container'")
                auto_increment_result = cursor.fetchone()
                candidate_id = auto_increment_result[0] if auto_increment_result else 1
            else:
                # If AUTO_INCREMENT failed, find the highest existing ID and increment
                cursor.execute("SELECT MAX(ContainerID) FROM container")
                max_id_result = cursor.fetchone()
                max_id = max_id_result[0] if max_id_result and max_id_result[0] else 0
                candidate_id = max_id + attempt
            
            candidate_barcode = f"CNT-{candidate_id}"
            
            # Check if this barcode already exists
            cursor.execute("SELECT COUNT(*) FROM container WHERE Barcode = %s", (candidate_barcode,))
            exists = cursor.fetchone()[0] > 0
            
            if not exists:
                print(f"DEBUG: Generated unique container barcode: {candidate_barcode}")
                return candidate_barcode
            
            print(f"DEBUG: Barcode {candidate_barcode} already exists, trying next candidate")
            attempt += 1
        
        # If we couldn't find a unique barcode after max_attempts, use timestamp fallback
        import time
        timestamp_barcode = f"CNT-{int(time.time())}"
        print(f"DEBUG: Using timestamp-based barcode as fallback: {timestamp_barcode}")
        return timestamp_barcode
    
    def create_container(self, container_data, user_id):
        print(f"DEBUG: create_container called with data: {container_data}")
        # Extract key data for debugging
        debug_info = {
            'description': container_data.get('description'),
            'locationId': container_data.get('locationId'),
            'containerLocationId': container_data.get('containerLocationId'),
            'storageLocation': container_data.get('storageLocation'),
            'containerTypeId': container_data.get('containerTypeId'),
            'newContainerType': container_data.get('newContainerType')
        }
        print(f"DEBUG: Key container data: {debug_info}")
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
                
                # Get a location ID from various potential field names
                location_id = container_data.get('locationId') or container_data.get('containerLocationId') or container_data.get('storageLocation')
                print(f"DEBUG: Looking for location ID in data: {location_id}")
                
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
                        print(f"DEBUG: Using default location ID: {location_id}")
                    else:
                        print("DEBUG: No default location found. This might cause container creation to fail.")
                
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
                    # Improved logic for container capacity determination
                    # Priority: 1. Explicit capacity, 2. Default from type, 3. Reasonable fallback
                    
                    # Start with the explicitly provided capacity if any
                    capacity = container.capacity
                    
                    # If no explicit capacity and not creating a new type, get default from container type
                    if (capacity is None or capacity == 0) and not new_container_type:
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
                        else:
                            # If no default capacity is found, use a reasonable default
                            capacity = 100
                            print(f"DEBUG: No DefaultCapacity found for container type {container.container_type_id}, using standard default {capacity}")
                    
                    # Verify capacity is a valid number and greater than zero
                    try:
                        if capacity is not None:
                            capacity = int(capacity)
                            if capacity <= 0:
                                capacity = 100
                                print(f"DEBUG: Invalid capacity value ({capacity}), using standard default 100")
                        else:
                            capacity = 100
                            print(f"DEBUG: No capacity specified, using standard default 100")
                    except (ValueError, TypeError):
                        capacity = 100
                        print(f"DEBUG: Non-numeric capacity value, using standard default 100")
                    
                    # Generate unique container barcode
                    container_barcode = self._generate_unique_container_barcode(cursor)
                    
                    query = f"""
                        INSERT INTO {table_name} (
                            Barcode,
                            Description, 
                            ContainerTypeID,
                            IsMixed,
                            ContainerCapacity,
                            LocationID
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    
                    # Handle isMixed parameter from container_data
                    is_mixed = container_data.get('isMixed', container.is_mixed)
                    
                    cursor.execute(query, (
                        container_barcode,
                        container.description,
                        container.container_type_id,
                        1 if is_mixed else 0,
                        capacity,
                        location_id
                    ))
                else:
                    # Even when container type is not specified, we should properly handle capacity
                    capacity = container.capacity
                    
                    # If no capacity is specified, use a reasonable default
                    if capacity is None or capacity == 0:
                        capacity = 100
                        print(f"DEBUG: No container type or capacity specified, using standard default capacity {capacity}")
                    
                    # Verify capacity is a valid number and greater than zero
                    try:
                        capacity = int(capacity)
                        if capacity <= 0:
                            capacity = 100
                            print(f"DEBUG: Invalid capacity value ({capacity}), using standard default 100")
                    except (ValueError, TypeError):
                        capacity = 100
                        print(f"DEBUG: Non-numeric capacity value, using standard default 100")
                    
                    # Generate unique container barcode
                    container_barcode = self._generate_unique_container_barcode(cursor)
                    
                    query = f"""
                        INSERT INTO {table_name} (
                            Barcode,
                            Description,
                            IsMixed,
                            ContainerCapacity,
                            LocationID
                        )
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    
                    # Handle isMixed parameter from container_data
                    is_mixed = container_data.get('isMixed', container.is_mixed)
                    
                    cursor.execute(query, (
                        container_barcode,
                        container.description,
                        1 if is_mixed else 0,
                        capacity,
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
                
                # Automatic printing is disabled - all printing handled by frontend
                print(f"DEBUG: Container {container_id} created, automatic printing disabled")
                
                result = {
                    'success': True,
                    'container_id': container_id
                }
                
                return result
        except Exception as e:
            print(f"DEBUG: Error in create_container: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
            
    def add_sample_to_container(self, container_id, sample_id, amount=1, user_id=None, force_add=False, source=''):
        print(f"DEBUG: add_sample_to_container called with container_id={container_id}, sample_id={sample_id}, amount={amount}, force_add={force_add}")
        # Note: This function now MOVES samples to containers rather than adding them
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
                        available_space = container_capacity - current_amount
                        return {
                            'success': False,
                            'warning': True,
                            'capacity_exceeded': True,
                            'error': f'Cannot add {amount} samples to container. Container has {available_space} of {container_capacity} units available (current: {current_amount})',
                            'current_amount': current_amount,
                            'new_amount': new_total,
                            'capacity': container_capacity,
                            'available_space': available_space
                        }
                
                # Check if sample exists and is available, and if it's currently in a container
                cursor.execute("""
                    SELECT 
                        s.SampleID, 
                        ss.StorageID, 
                        ss.AmountRemaining, 
                        ss.LocationID,
                        s.Description,
                        s.PartNumber,
                        s.Barcode,
                        s.UnitID,
                        s.ReceptionID,
                        s.OwnerID,
                        s.Amount,
                        s.Type,
                        s.IsUnique,
                        cs.ContainerID as CurrentContainerID
                    FROM sample s
                    JOIN samplestorage ss ON s.SampleID = ss.SampleID
                    LEFT JOIN containersample cs ON ss.StorageID = cs.SampleStorageID
                    WHERE s.SampleID = %s AND ss.AmountRemaining >= %s
                """, (sample_id, amount))
                
                sample_data = cursor.fetchone()
                if not sample_data:
                    return {
                        'success': False,
                        'error': f'Sample with ID {sample_id} does not exist or has insufficient quantity'
                    }
                
                storage_id = sample_data[1]
                sample_amount_remaining = sample_data[2]
                sample_location_id = sample_data[3]
                
                # Extract all sample data for potential new sample creation
                sample_description = sample_data[4]
                sample_part_number = sample_data[5]
                sample_barcode = sample_data[6]
                sample_unit_id = sample_data[7]
                sample_reception_id = sample_data[8]
                sample_owner_id = sample_data[9]
                sample_original_amount = sample_data[10] if sample_data[10] is not None else 0
                sample_type = sample_data[11] or 'single'
                sample_is_unique = sample_data[12] or 0
                original_container_id = sample_data[13]  # Current container ID (if any)
                
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
                
                # For container details "add" functionality, prevent moving between containers
                # Only allow adding samples from direct storage
                if source == 'container_details' and original_container_id and original_container_id != container_id:
                    return {
                        'success': False,
                        'error': 'This sample is already in another container. Please use the Move functionality in Sample Overview to move samples between containers.'
                    }
                
                # Remove sample from original container if it exists (for Sample Overview moves)
                if original_container_id and original_container_id != container_id:
                    cursor.execute("""
                        DELETE FROM containersample 
                        WHERE SampleStorageID = %s AND ContainerID = %s
                    """, (storage_id, original_container_id))
                    print(f"DEBUG: Removed sample from original container {original_container_id}")
                
                # Check if containersample table exists, create if it doesn't
                cursor.execute("SHOW TABLES LIKE 'containersample'")
                if cursor.fetchone() is None:
                    print("DEBUG: Creating containersample table")
                    cursor.execute("""
                        CREATE TABLE containersample (
                            ContainerSampleID INT AUTO_INCREMENT PRIMARY KEY,
                            SampleStorageID INT NOT NULL,
                            ContainerID INT NOT NULL,
                            Amount INT NOT NULL DEFAULT 1
                        )
                    """)
                
                # Add the sample to the container
                cursor.execute("""
                    INSERT INTO containersample (
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
                
                # Check if we are moving all items or just some
                # If moving all items, just update the location
                # If moving some items, create a new sample record and reduce the original
                
                if amount >= sample_amount_remaining:
                    # Moving ALL items - just update the location
                    cursor.execute("""
                        UPDATE samplestorage 
                        SET LocationID = (SELECT LocationID FROM container WHERE ContainerID = %s)
                        WHERE StorageID = %s
                    """, (container_id, storage_id))
                    
                    print(f"DEBUG: Sample moved to container {container_id} (all units). Updated location to match container.")
                else:
                    # Moving SOME items - create a new sample and reduce the original
                    # First, reduce the amount in both sample and samplestorage tables
                    new_amount = sample_amount_remaining - amount
                    
                    # Update samplestorage.AmountRemaining
                    cursor.execute("""
                        UPDATE samplestorage 
                        SET AmountRemaining = %s 
                        WHERE StorageID = %s
                    """, (new_amount, storage_id))
                    
                    # Also update sample.Amount for consistency
                    cursor.execute("""
                        UPDATE sample 
                        SET Amount = %s 
                        WHERE SampleID = %s
                    """, (new_amount, sample_id))
                    
                    # Create timestamp for unique barcode
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    new_barcode = f"{sample_barcode}-{timestamp}" if sample_barcode else f"MOVED-{sample_id}-{timestamp}"
                    
                    # Now create a new sample record for the moved portion
                    cursor.execute("""
                        INSERT INTO sample (
                            PartNumber,
                            Description,
                            Barcode,
                            Status,
                            Amount,
                            UnitID,
                            OwnerID,
                            ReceptionID,
                            Type,
                            IsUnique
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        sample_part_number,
                        sample_description,
                        new_barcode,  # Create a unique barcode with timestamp
                        'In Storage',
                        amount,  # Set the correct amount for the new sample
                        sample_unit_id,
                        sample_owner_id,
                        sample_reception_id,
                        sample_type,
                        sample_is_unique
                    ))
                    
                    new_sample_id = cursor.lastrowid
                    
                    # Get container's location
                    cursor.execute("SELECT LocationID FROM container WHERE ContainerID = %s", (container_id,))
                    container_location_result = cursor.fetchone()
                    container_location_id = container_location_result[0] if container_location_result else None
                    
                    # Create storage record for the new sample
                    cursor.execute("""
                        INSERT INTO samplestorage (
                            SampleID,
                            LocationID,
                            AmountRemaining
                        ) VALUES (%s, %s, %s)
                    """, (
                        new_sample_id,
                        container_location_id,
                        amount
                    ))
                    
                    # Get the new storage ID
                    new_storage_id = cursor.lastrowid
                    
                    # Update containersample to point to the new storage record
                    cursor.execute("""
                        UPDATE containersample
                        SET SampleStorageID = %s
                        WHERE ContainerSampleID = %s
                    """, (new_storage_id, container_sample_id))
                    
                    print(f"DEBUG: Created new sample {new_sample_id} for {amount} units moved to container {container_id}")
                    
                # Legacy comment for context:
                # IMPORTANT: We now DO reduce the sample amount when splitting. This ensures accurate tracking
                # in both SampleStorage.AmountRemaining and Sample.Amount tables
                
                # Log the activity
                if user_id:
                    # Add a note if we're exceeding capacity
                    capacity_note = ""
                    if container_capacity and current_amount + amount > container_capacity:
                        capacity_note = f" (Container capacity exceeded: {current_amount + amount}/{container_capacity})"
                    
                    cursor.execute("""
                        INSERT INTO history (
                            Timestamp, 
                            ActionType, 
                            UserID, 
                            SampleID,
                            Notes
                        )
                        VALUES (NOW(), %s, %s, %s, %s)
                    """, (
                        'Sample moved to container',
                        user_id,
                        sample_id,
                        f"Sample {sample_id} moved to Container {container_id}, amount: {amount}{capacity_note}"
                    ))
                
                # Check if original container still has samples
                original_container_has_samples = False
                if original_container_id and original_container_id != container_id:
                    cursor.execute("""
                        SELECT COUNT(*) FROM containersample WHERE ContainerID = %s
                    """, (original_container_id,))
                    remaining_samples = cursor.fetchone()[0]
                    original_container_has_samples = remaining_samples > 0
                    print(f"DEBUG: Original container {original_container_id} has {remaining_samples} samples remaining, has_samples={original_container_has_samples}")
                else:
                    print(f"DEBUG: No original container or same container (original={original_container_id}, new={container_id})")
                
                # Note: Container label printing is now handled by frontend prompt
                # This allows user to choose whether to print or skip
                
                result = {
                    'success': True,
                    'container_sample_id': container_sample_id,
                    'capacity_warning': container_capacity and current_amount + amount > container_capacity,
                    'original_container_id': original_container_id,
                    'original_container_has_samples': original_container_has_samples
                }
                print(f"DEBUG: Returning move result: {result}")
                return result
                
        except Exception as e:
            print(f"DEBUG: Error in add_sample_to_container: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
            
    def delete_container(self, container_id, user_id):
        try:
            print(f"DEBUG: Deleting container {container_id}")
            
            # Check if the container exists
            cursor = self.mysql.connection.cursor()
            cursor.execute("""
                SELECT ContainerID, Description
                FROM container
                WHERE ContainerID = %s
            """, (container_id,))
            
            container_data = cursor.fetchone()
            if not container_data:
                cursor.close()
                return {
                    'success': False,
                    'error': 'Container not found'
                }
                
            container_description = container_data[1]
            
            # Check if the container has samples - don't allow deletion if it does
            cursor.execute("""
                SELECT COUNT(*) 
                FROM ContainerSample
                WHERE ContainerID = %s
            """, (container_id,))
            
            sample_count = cursor.fetchone()[0]
            if sample_count > 0:
                cursor.close()
                return {
                    'success': False,
                    'error': f'Container still has {sample_count} samples. Remove all samples first.'
                }
            
            # Delete the container
            with self.db.transaction() as tx_cursor:
                tx_cursor.execute("""
                    DELETE FROM container
                    WHERE ContainerID = %s
                """, (container_id,))
                
                # Log the deletion
                tx_cursor.execute("""
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
                    f'Container {container_id} ({container_description}) was deleted'
                ))
                
            cursor.close()
            return {
                'success': True,
                'message': f'Container {container_id} deleted successfully'
            }
        except Exception as e:
            print(f"DEBUG: Error in delete_container: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
            
    def delete_container_type(self, container_type_id, user_id):
        try:
            print(f"DEBUG: Deleting container type {container_type_id}")
            
            # First check if the container type exists
            cursor = self.mysql.connection.cursor()
            cursor.execute("""
                SELECT TypeName
                FROM containertype
                WHERE ContainerTypeID = %s
            """, (container_type_id,))
            
            result = cursor.fetchone()
            if not result:
                cursor.close()
                return {
                    'success': False,
                    'error': 'Container type not found'
                }
                
            type_name = result[0]
            
            # Check if any active containers use this type
            cursor.execute("""
                SELECT COUNT(*) 
                FROM container
                WHERE ContainerTypeID = %s
            """, (container_type_id,))
            
            active_containers = cursor.fetchone()[0]
            if active_containers > 0:
                cursor.close()
                return {
                    'success': False,
                    'error': f'This container type is used by {active_containers} active containers and cannot be deleted. Remove all containers of this type first.'
                }
                
            # Check if any samples are in containers of this type
            cursor.execute("""
                SELECT COUNT(*) 
                FROM container c
                JOIN containersample cs ON c.ContainerID = cs.ContainerID
                WHERE c.ContainerTypeID = %s
            """, (container_type_id,))
            
            active_samples = cursor.fetchone()[0]
            if active_samples > 0:
                cursor.close()
                return {
                    'success': False,
                    'error': f'This container type is used by containers that contain {active_samples} samples and cannot be deleted. Remove all samples from containers of this type first.'
                }
                
            # Check if any tests use this container type
            # Simplify the test query since we may not have all the tables referenced in the original query
            cursor.execute("""
                SELECT COUNT(*) 
                FROM test t
                JOIN testsampleusage ts ON t.TestID = ts.TestID
                JOIN sample s ON ts.SampleID = s.SampleID
                JOIN samplestorage ss ON s.SampleID = ss.SampleID
                JOIN containersample cs ON ss.StorageID = cs.SampleStorageID
                JOIN container c ON cs.ContainerID = c.ContainerID
                WHERE c.ContainerTypeID = %s
            """, (container_type_id,))
            
            active_tests = cursor.fetchone()[0]
            if active_tests > 0:
                cursor.close()
                return {
                    'success': False,
                    'error': f'This container type is used in {active_tests} tests and cannot be deleted. Complete all tests using this container type first.'
                }
                
            # After all checks, delete the container type
            with self.db.transaction() as tx_cursor:
                tx_cursor.execute("""
                    DELETE FROM containertype
                    WHERE ContainerTypeID = %s
                """, (container_type_id,))
                
                # Log the deletion
                tx_cursor.execute("""
                    INSERT INTO history (
                        Timestamp,
                        ActionType,
                        UserID,
                        Notes
                    )
                    VALUES (NOW(), %s, %s, %s)
                """, (
                    'Container type deleted',
                    user_id,
                    f'Container type "{type_name}" (ID: {container_type_id}) was deleted'
                ))
                
            cursor.close()
            return {
                'success': True,
                'message': f'Container type "{type_name}" deleted successfully'
            }
        except Exception as e:
            print(f"DEBUG: Error in delete_container_type: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f'Database error: {str(e)}'
            }