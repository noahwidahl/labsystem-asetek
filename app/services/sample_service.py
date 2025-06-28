from datetime import datetime
from app.models.sample import Sample
from app.utils.db import DatabaseManager

class SampleService:
    def __init__(self, mysql):
        self.mysql = mysql
        self.db = DatabaseManager(mysql)
    
    def get_all_samples(self, search_term=None, sort_by='s.SampleID', sort_order='DESC', filter_criteria=None):
        """
        Get all samples with support for searching, sorting and filtering
        
        Args:
            search_term (str): Optional search term to filter samples by
            sort_by (str): Field to sort by (default: SampleID)
            sort_order (str): Sort order (ASC or DESC)
            filter_criteria (dict): Optional dictionary with filter criteria
            
        Returns:
            list: List of Sample objects matching criteria
        """
        # Build base query with JOINs for efficient data retrieval
        query = """
            SELECT 
                s.SampleID, 
                s.Barcode, 
                s.PartNumber,
                s.IsUnique,
                s.Type,
                s.Description, 
                s.Status,
                s.Amount, 
                s.UnitID,
                s.OwnerID,
                s.ReceptionID,
                r.ReceivedDate,
                CASE
                    WHEN u.UnitName IS NULL THEN 'pcs'
                    WHEN LOWER(u.UnitName) = 'stk' THEN 'pcs'
                    ELSE u.UnitName
                END as UnitName,
                COALESCE(sl.LocationName, 'Unknown') as LocationName
            FROM Sample s
            LEFT JOIN Reception r ON s.ReceptionID = r.ReceptionID
            LEFT JOIN Unit u ON s.UnitID = u.UnitID
            LEFT JOIN SampleStorage ss ON s.SampleID = ss.SampleID
            LEFT JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
        """
        
        # Initialize conditions and parameters
        conditions = []
        params = []
        
        # Add search condition if search term is provided
        if search_term:
            # Full-text search across multiple fields using LIKE for better matching
            search_conditions = [
                "s.Description LIKE %s",
                "s.Barcode LIKE %s",
                "s.PartNumber LIKE %s",
                "sl.LocationName LIKE %s"
            ]
            search_term_param = f"%{search_term}%"
            params.extend([search_term_param] * len(search_conditions))
            conditions.append(f"({' OR '.join(search_conditions)})")
        
        # Add filter conditions if provided
        if filter_criteria:
            if filter_criteria.get('status'):
                conditions.append("s.Status = %s")
                params.append(filter_criteria['status'])
                
            if filter_criteria.get('location'):
                conditions.append("sl.LocationID = %s")
                params.append(filter_criteria['location'])
                
            if filter_criteria.get('date_from'):
                conditions.append("r.ReceivedDate >= %s")
                params.append(filter_criteria['date_from'])
                
            if filter_criteria.get('date_to'):
                conditions.append("r.ReceivedDate <= %s")
                params.append(filter_criteria['date_to'])
        
        # Add WHERE clause if we have conditions
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        # Add sorting - default to SampleID DESC
        # Validate sort_by to prevent SQL injection
        valid_sort_fields = {
            'sample_id': 's.SampleID',
            'barcode': 's.Barcode',
            'part_number': 's.PartNumber',
            'description': 's.Description',
            'reception_date': 'r.ReceivedDate',
            'amount': 'ss.AmountRemaining',
            'location': 'sl.LocationName',
            'status': 's.Status'
        }
        
        # Use validated sort field or default
        sort_field = valid_sort_fields.get(sort_by, 's.SampleID')
        
        # Validate sort order to prevent SQL injection
        sort_order = 'ASC' if sort_order.upper() == 'ASC' else 'DESC'
        
        query += f" ORDER BY {sort_field} {sort_order}"
        
        # Execute the query
        result, cursor = self.db.execute_query(query, params)
        
        # Convert to Sample objects
        samples = []
        columns = [col[0] for col in cursor.description]
        
        for row in result:
            # Create a dictionary from column names and row values
            row_dict = dict(zip(columns, row))
            
            # Map column names to the property names Sample expects
            sample_data = {
                'id': row_dict.get('SampleID'),
                'description': row_dict.get('Description'),
                'barcode': row_dict.get('Barcode'),
                'part_number': row_dict.get('PartNumber'),
                'is_unique': bool(row_dict.get('IsUnique', 0)),
                'type': row_dict.get('Type', 'Standard'),
                'status': row_dict.get('Status', 'In Storage'),
                'amount': row_dict.get('AmountRemaining', 0),
                'unit_id': row_dict.get('UnitID'),
                'owner_id': row_dict.get('OwnerID'),
                'reception_id': row_dict.get('ReceptionID'),
                'unit_name': row_dict.get('UnitName'),
                'location_name': row_dict.get('LocationName'),
                'received_date': row_dict.get('ReceivedDate')
            }
            
            # Create Sample object from data
            samples.append(Sample(**sample_data))
        
        return samples
    
    def get_sample_by_id(self, sample_id):
        query = """
            SELECT 
                s.SampleID, 
                s.Barcode, 
                s.PartNumber,
                s.IsUnique,
                s.Type,
                s.Description, 
                s.Status,
                ss.AmountRemaining, 
                s.UnitID,
                s.OwnerID,
                s.ReceptionID
            FROM Sample s
            JOIN SampleStorage ss ON s.SampleID = ss.SampleID
            WHERE s.SampleID = %s
        """
        
        result, _ = self.db.execute_query(query, (sample_id,))
        
        if not result or len(result) == 0:
            return None
        
        return Sample.from_db_row(result[0])
    
    def create_sample(self, sample_data, user_id):
        print(f"DEBUG: create_sample called with data: {sample_data}")
        with self.db.transaction(isolation_level="REPEATABLE READ") as cursor:
            # Handling supplier
            supplier_id = None
            if sample_data.get('supplier') and sample_data.get('supplier').strip():
                try:
                    supplier_id = int(sample_data.get('supplier'))
                except (ValueError, TypeError):
                    supplier_id = None
            
            # Ensure correct date formatting
            reception_date = datetime.now()
            if sample_data.get('receptionDate'):
                try:
                    reception_date = datetime.strptime(sample_data.get('receptionDate'), '%Y-%m-%d')
                except (ValueError, TypeError):
                    reception_date = datetime.now()
            
            # Insert reception record
            cursor.execute("""
                INSERT INTO Reception (
                    SupplierID, 
                    ReceivedDate, 
                    UserID, 
                    TrackingNumber,
                    SourceType,
                    Notes
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                supplier_id,
                reception_date,
                user_id,
                sample_data.get('trackingNumber', ''),
                'External' if supplier_id else 'Internal',
                sample_data.get('other', 'Registered via lab system')
            ))
            
            reception_id = cursor.lastrowid
            
            # This is now a simple single sample or bulk material system
            package_count = 1
            
            # Generate a unique barcode if not provided
            base_barcode = sample_data.get('barcode', '')
            if not base_barcode:
                base_barcode = f"BC{reception_id}-{int(datetime.now().timestamp())}"
            
            # Variables to keep track of sample_id and storage_id for the first sample
            first_sample_id = None
            first_storage_id = None
            
            # Use single storage location
            storage_location_id = sample_data.get('storageLocation')
            
            # Simplified single sample creation
            create_containers = sample_data.get('createContainers', False) or sample_data.get('storageOption') == 'container'
            container_ids = []
            
            # Generate barcode
            barcode = base_barcode
                
                # Calculate amount per package
                total_amount = int(sample_data.get('totalAmount', 0))
                
                # Handle amount differently based on registration type
                
                # Case 1: Multiple containers (one per package)
                if create_multi_containers:
                    # For multiple containers, each sample gets the amount per package directly
                    amount_per_package = int(sample_data.get('amountPerPackage', 1))
                    print(f"DEBUG: Package {i+1} of {package_count} with createMultipleContainers=True gets amount={amount_per_package}")
                
                # Case 2: Multiple identical samples - direct storage or single container
                elif is_multi_package:
                    # Get amount per package from form input
                    amount_per_package = int(sample_data.get('amountPerPackage', 1))
                    
                    # If original package count was modified for container handling,
                    # we need to keep the original amount per package from the form
                    if package_count != original_package_count:
                        print(f"DEBUG: Multiple identical samples using original amount per package: {amount_per_package}")
                    else:
                        print(f"DEBUG: Using standard amount per package: {amount_per_package}")
                
                # Case 3: Standard single sample
                else:
                    # Standard single sample handling
                    amount_per_package = total_amount
                    
                    # Adjust last package if there's a remainder
                    if i == package_count - 1 and total_amount % package_count != 0:
                        amount_per_package += total_amount % package_count
                        
                print(f"DEBUG: Using amount {amount_per_package} for package {i+1} of {package_count}")
                
                # Generate a good description for this package
                base_description = sample_data.get('description', '')
                package_suffix = ""
                
                # Add simple number suffix if we have multiple packages
                if package_count > 1:
                    package_suffix = f" {i+1}"
                
                # Full description combining base + package info
                full_description = base_description + package_suffix
                
                print(f"DEBUG: Using description '{full_description}' for package {i+1}")
                
                # Set the correct amount value for this sample/container
                # When using multiple containers (one per package), the amount should be
                # the value of amountPerPackage, not the total amount
                amount_value = amount_per_package
                
                print(f"DEBUG: Sample {i+1} of {package_count} with amount={amount_value}")
                
                # Handle expire date - use provided date or default to 2 months from now
                expire_date = None
                if sample_data.get('expireDate'):
                    try:
                        expire_date = datetime.strptime(sample_data.get('expireDate'), '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        pass
                
                if not expire_date:
                    # Default to 2 months from now
                    from datetime import timedelta
                    expire_date = (datetime.now() + timedelta(days=60)).date()
                
                # Insert the sample in Sample table
                cursor.execute("""
                    INSERT INTO Sample (
                        Barcode, 
                        PartNumber,
                        IsUnique, 
                        Type, 
                        Description, 
                        Status, 
                        Amount, 
                        UnitID, 
                        OwnerID, 
                        ReceptionID,
                        ExpireDate
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    barcode,
                    sample_data.get('partNumber', ''),
                    1 if sample_data.get('hasSerialNumbers') else 0,
                    sample_data.get('sampleType', 'Standard'),
                    full_description,
                    "In Storage",
                    amount_value,
                    sample_data.get('unit'),
                    sample_data.get('owner'),
                    reception_id,
                    expire_date
                ))
                
                sample_id = cursor.lastrowid
                
                # Save the first sample_id for later reference
                if first_sample_id is None:
                    first_sample_id = sample_id
                
                # Determine location for this package
                location_id = None
                
                # Check if we have multiple containers (one per package)
                create_multi_containers = sample_data.get('createMultipleContainers', False)
                
                # Try to get location from container locations first if creating one container per package
                if create_multi_containers and sample_data.get('containerLocations'):
                    container_locs = sample_data.get('containerLocations', [])
                    print(f"DEBUG: Available container locations: {container_locs}")
                    
                    # Find matching package
                    container_loc = next((loc for loc in container_locs if str(loc.get('packageNumber', '')) == str(i+1)), None)
                    
                    if container_loc and container_loc.get('locationId'):
                        location_id = container_loc.get('locationId')
                        print(f"DEBUG: Using container location {location_id} for package {i+1} from containerLocations array")
                    else:
                        print(f"WARNING: No matching container location found for package {i+1} in containerLocations array")
                
                # Fall back to package locations
                if not location_id and different_locations and package_locations:
                    # Find package data for this package number
                    package_data = next((p for p in package_locations if str(p.get('packageNumber', '')) == str(i+1)), None)
                    if package_data:
                        location_id = package_data.get('locationId')
                        print(f"DEBUG: Using location {location_id} for package {i+1} from packageLocations array")
                
                # Use default location if no specific one is found
                if not location_id:
                    location_id = sample_data.get('storageLocation')
                    print(f"DEBUG: Using default storageLocation {location_id} for package {i+1}")
                    
                # Safety check - set default location if still none
                if not location_id:
                    # Find a valid location ID from the database
                    cursor.execute("SELECT LocationID FROM StorageLocation ORDER BY LocationID LIMIT 1")
                    location_result = cursor.fetchone()
                    if location_result and location_result[0]:
                        location_id = location_result[0]
                    else:
                        # If no location found in the database, use 1 as a fallback
                        location_id = "1"
                        print(f"WARNING: Using default location ID 1, no locations found in database")
                
                # Insert to SampleStorage with the chosen location
                # Use the same amount value for consistency with the Sample table
                cursor.execute("""
                    INSERT INTO SampleStorage (
                        SampleID, 
                        LocationID, 
                        AmountRemaining, 
                        ExpireDate
                    )
                    VALUES (%s, %s, %s, %s)
                """, (
                    sample_id,
                    location_id,
                    amount_value,  # Use the same amount as in Sample table
                    sample_data.get('expiryDate')
                ))
                
                storage_id = cursor.lastrowid
                
                # Save the first storage_id for later reference
                if first_storage_id is None:
                    first_storage_id = storage_id
                
                # Handle container functionality
                if create_containers:
                    print(f"DEBUG: Processing container creation with data: containerTypeId={sample_data.get('containerTypeId')}, containerDescription={sample_data.get('containerDescription')}, containerLocationId={sample_data.get('containerLocationId')}")
                    
                    # Verify we have the minimum required data for container creation
                    if not sample_data.get('containerTypeId') and not sample_data.get('newContainerType'):
                        print("DEBUG: Cannot create container - missing containerTypeId or newContainerType")
                        # Try to find a default container type
                        cursor.execute("SELECT ContainerTypeID FROM ContainerType LIMIT 1")
                        result = cursor.fetchone()
                        if result:
                            sample_data['containerTypeId'] = result[0]
                            print(f"DEBUG: Using default container type: {result[0]}")
                        else:
                            print("DEBUG: No default container type found - creating basic container type")
                            # Create a basic container type
                            cursor.execute("""
                                INSERT INTO ContainerType (
                                    TypeName,
                                    Description,
                                    DefaultCapacity
                                )
                                VALUES (%s, %s, %s)
                            """, (
                                "Standard Box",
                                "Basic container type created automatically",
                                100
                            ))
                            sample_data['containerTypeId'] = cursor.lastrowid
                            print(f"DEBUG: Created basic container type: {sample_data['containerTypeId']}")
                    
                    # Ensure containerLocationId is set
                    if not sample_data.get('containerLocationId'):
                        if sample_data.get('storageLocation'):
                            sample_data['containerLocationId'] = sample_data.get('storageLocation')
                            print(f"DEBUG: Using storageLocation as containerLocationId: {sample_data['containerLocationId']}")
                        else:
                            # Get first available location
                            cursor.execute("SELECT LocationID FROM StorageLocation LIMIT 1")
                            result = cursor.fetchone()
                            if result:
                                sample_data['containerLocationId'] = result[0]
                                print(f"DEBUG: Using first available location: {sample_data['containerLocationId']}")
                            else:
                                raise Exception("No storage locations found in database. Cannot create container.")
                    
                    # Make sure we have a container description
                    # If not specified, first check if we're using an existing container
                    if sample_data.get('useExistingContainer') and sample_data.get('existingContainerId'):
                        print(f"DEBUG: Using existing container {sample_data.get('existingContainerId')}")
                    elif not sample_data.get('containerDescription'):
                        # If no container description provided, use the sample description as fallback
                        sample_data['containerDescription'] = sample_data.get('description', 'Container')
                        print(f"DEBUG: Using sample description as container name: {sample_data['containerDescription']}")
                    else:
                        # Make sure description is properly set and not empty
                        container_desc = sample_data.get('containerDescription', '').strip()
                        if not container_desc:
                            sample_data['containerDescription'] = sample_data.get('description', 'Container')
                            print(f"DEBUG: Container description was empty, using sample description instead: {sample_data['containerDescription']}")
                        else:
                            print(f"DEBUG: Using provided container description: {sample_data.get('containerDescription')}")
                    
                    try:
                        # Check if we should use existing container
                        if sample_data.get('useExistingContainer') and sample_data.get('existingContainerId'):
                            # Use existing container
                            container_id = sample_data.get('existingContainerId')
                            print(f"DEBUG: Using existing container with ID: {container_id}")
                            container_ids.append(container_id)
                        # Check if we're using one container for all samples and this is not the first sample
                        elif sample_data.get('useSingleContainerForAll') == True and i > 0 and len(container_ids) > 0:
                            # Use the first container we already created for all samples
                            container_id = container_ids[0]
                            print(f"DEBUG: Using single container for all samples - reusing container ID: {container_id}")
                        else:
                            # Create new container
                            print(f"DEBUG: Creating container for package {i+1}")
                            # Use container description if provided, or default to generic container name
                            container_desc = (sample_data.get('containerDescription') or '').strip()
                            if not container_desc:
                                container_desc = sample_data.get('description', 'Container')
                                print(f"DEBUG: Container description was empty, using sample description: {container_desc}")
                            if package_count > 1:
                                container_desc += f" {i+1}"
                            
                            # Use 'container' table directly
                            table_name = "container"
                            
                            # Check if we need to create a new container type first
                            # For clarity, we'll set a created container type ID variable if we create a new type
                            created_container_type_id = None
                            
                            if sample_data.get('newContainerType'):
                                print(f"DEBUG: Creating new container type from sample registration")
                                new_type = sample_data.get('newContainerType')
                                
                                # Check if this is the first container in a multi-container scenario
                                # If we already have a created container type, use that instead of creating a new one
                                if i == 0 or len(container_ids) == 0:
                                    # First container in a batch - create the new container type
                                    # Insert the new container type
                                    cursor.execute("""
                                        INSERT INTO ContainerType (
                                            TypeName,
                                            Description,
                                            DefaultCapacity
                                        )
                                        VALUES (%s, %s, %s)
                                    """, (
                                        new_type.get('typeName'),
                                        new_type.get('description', ''),
                                        new_type.get('capacity')
                                    ))
                                    
                                    # Get the new container type ID
                                    container_type_id = cursor.lastrowid
                                    created_container_type_id = container_type_id
                                    # Store the container type ID in sample_data so it can be reused for other containers
                                    sample_data['createdContainerTypeId'] = container_type_id
                                    print(f"DEBUG: Created new container type with ID: {container_type_id} for first container")
                                    
                                    # IMPORTANT: Get the capacity from the new container type
                                    # This ensures that when creating a new container type, we use its capacity
                                    capacity = new_type.get('capacity')
                                    print(f"DEBUG: Using capacity {capacity} from new container type {container_type_id}")
                                    
                                    # Log the container type creation
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
                                        f"Container type '{new_type.get('typeName')}' created during sample registration"
                                    ))
                                else:
                                    # For subsequent containers, reuse the previously created container type
                                    container_type_id = sample_data.get('createdContainerTypeId')
                                    capacity = new_type.get('capacity')
                                    print(f"DEBUG: Reusing container type ID {container_type_id} for container {i+1}")
                            elif sample_data.get('createdContainerTypeId'):
                                # This is a subsequent container in a batch and we have a previously created container type
                                container_type_id = sample_data.get('createdContainerTypeId')
                                print(f"DEBUG: Using previously created container type ID {container_type_id} for container {i+1}")
                            elif sample_data.get('containerTypeId'):
                                # Use the supplied container type ID
                                container_type_id = sample_data.get('containerTypeId')
                            else:
                                # Try to find a default container type (using first one in the database)
                                container_type_id = None
                                cursor.execute("SELECT ContainerTypeID FROM ContainerType LIMIT 1")
                                default_type_result = cursor.fetchone()
                                if default_type_result:
                                    container_type_id = default_type_result[0]
                            
                            # Prioritized logic for determining container capacity
                            # 1. First check if we have a new container type with capacity
                            if sample_data.get('newContainerType') and sample_data.get('newContainerType').get('capacity'):
                                capacity = int(sample_data.get('newContainerType').get('capacity'))
                                print(f"DEBUG: Using capacity {capacity} from new container type for container #{i+1}")
                            # 2. If user explicitly specified container capacity
                            elif sample_data.get('containerCapacity'):
                                capacity = int(sample_data.get('containerCapacity'))
                                print(f"DEBUG: Using user-specified capacity {capacity} for container #{i+1}")
                            # 3. If we have a container type ID, get its default capacity from the database
                            elif container_type_id:
                                # Query the container type's default capacity
                                cursor.execute("""
                                    SELECT DefaultCapacity, TypeName
                                    FROM ContainerType 
                                    WHERE ContainerTypeID = %s
                                """, (container_type_id,))
                                type_result = cursor.fetchone()
                                if type_result and type_result[0]:
                                    capacity = int(type_result[0])
                                    type_name = type_result[1]
                                    print(f"DEBUG: Using DefaultCapacity {capacity} from container type '{type_name}' (ID: {container_type_id}) for container #{i+1}")
                                else:
                                    # Fallback if no default capacity
                                    capacity = 100  # Default to 100 units as a reasonable fallback
                                    print(f"DEBUG: No DefaultCapacity found for container type {container_type_id}, using default value {capacity} for container #{i+1}")
                            # 4. Fallbacks in priority order
                            else:
                                # If all else fails, determine a capacity based on the context
                                if sample_data.get('useSingleContainerForAll', False):
                                    # For "one container for all" mode, suggest a larger capacity
                                    capacity = max(100, int(sample_data.get('totalAmount', 0)) * 2)
                                    print(f"DEBUG: No capacity specified for single container for all samples, using {capacity} (2x total amount) for container #{i+1}")
                                elif sample_data.get('createMultipleContainers', False):
                                    # For "one container per package", suggest a reasonable multiple of amount per package
                                    capacity = max(50, int(sample_data.get('amountPerPackage', 1)) * 5)
                                    print(f"DEBUG: No capacity specified for container in multiple containers mode, using {capacity} (5x amount per package) for container #{i+1}")
                                else:
                                    # Default reasonable capacity
                                    capacity = 100
                                    print(f"DEBUG: No capacity information available, using default capacity {capacity} for container #{i+1}")
                            
                            print(f"CONTAINER CREATION: Container #{i+1}/{package_count}, Type ID: {container_type_id}, Capacity: {capacity}, Description: '{container_desc}'")
                            
                            # Get location from parameters or use the one already determined
                            # Check for multiple container locations
                            container_location_id = None
                            
                            # First check if we have "one container per package" mode
                            if sample_data.get('createMultipleContainers', False):
                                # In "one container per package" mode, we need to use the specific location for each package
                                container_locations = sample_data.get('containerLocations', [])
                                
                                if container_locations and len(container_locations) > 0:
                                    # Try to find location for this package
                                    matching_location = next((cl for cl in container_locations if str(cl.get('packageNumber', '')) == str(i+1)), None)
                                    if matching_location:
                                        container_location_id = matching_location.get('locationId')
                                        print(f"DEBUG: Using special container location {container_location_id} for package {i+1} (multiple containers mode)")
                            
                            # If no location found yet, try packageLocations as fallback
                            if not container_location_id and sample_data.get('packageLocations'):
                                package_locations = sample_data.get('packageLocations', [])
                                matching_package = next((p for p in package_locations if str(p.get('packageNumber', '')) == str(i+1)), None)
                                if matching_package:
                                    container_location_id = matching_package.get('locationId')
                                    print(f"DEBUG: Using package location {container_location_id} for container of package {i+1}")
                            
                            # Fallback to main container location
                            if not container_location_id and sample_data.get('containerLocationId'):
                                container_location_id = sample_data.get('containerLocationId')
                                print(f"DEBUG: Using main containerLocationId {container_location_id} for container of package {i+1}")
                            
                            # Last resort: use sample storage location
                            if not container_location_id:
                                container_location_id = location_id
                                print(f"DEBUG: Using storage location {container_location_id} as fallback for container of package {i+1}")
                            
                            # Create container with location and container type
                            # Check if container_location_id is a string in format "x.x.x"
                            location_id_to_use = container_location_id
                            
                            # If container_location_id is a string in format "x.x.x", try to find or create the location
                            if isinstance(container_location_id, str) and container_location_id.count('.') == 2:
                                try:
                                    location_name = container_location_id
                                    print(f"DEBUG: Looking up location by name: {location_name}")
                                    
                                    # Try to find the location by name
                                    cursor.execute("""
                                        SELECT LocationID FROM StorageLocation WHERE LocationName = %s
                                    """, (location_name,))
                                    
                                    location_result = cursor.fetchone()
                                    if location_result:
                                        # Found existing location
                                        location_id_to_use = location_result[0]
                                        print(f"DEBUG: Found existing location with ID: {location_id_to_use}")
                                    else:
                                        # Parse rack, section, shelf from the format x.x.x
                                        parts = location_name.split('.')
                                        if len(parts) == 3:
                                            rack = parts[0]
                                            section = parts[1]
                                            shelf = parts[2]
                                            
                                            # Create a new location
                                            print(f"DEBUG: Creating new location: Rack={rack}, Section={section}, Shelf={shelf}")
                                            
                                            # Get lab ID (use first available lab)
                                            cursor.execute("SELECT LabID FROM Lab LIMIT 1")
                                            lab_result = cursor.fetchone()
                                            lab_id = lab_result[0] if lab_result else 1
                                            
                                            # Insert the new location
                                            cursor.execute("""
                                                INSERT INTO StorageLocation (
                                                    LocationName, 
                                                    Rack, 
                                                    Section, 
                                                    Shelf, 
                                                    LabID
                                                )
                                                VALUES (%s, %s, %s, %s, %s)
                                            """, (
                                                location_name,
                                                rack,
                                                section,
                                                shelf,
                                                lab_id
                                            ))
                                            
                                            location_id_to_use = cursor.lastrowid
                                            print(f"DEBUG: Created new location with ID: {location_id_to_use}")
                                        else:
                                            # Fall back to default location if format is invalid
                                            cursor.execute("SELECT LocationID FROM StorageLocation LIMIT 1")
                                            location_result = cursor.fetchone()
                                            location_id_to_use = location_result[0] if location_result else 1
                                            print(f"DEBUG: Using default location ID: {location_id_to_use}")
                                except Exception as loc_error:
                                    print(f"DEBUG: Error processing location: {loc_error}")
                                    # Fall back to using a default location
                                    cursor.execute("SELECT LocationID FROM StorageLocation LIMIT 1")
                                    location_result = cursor.fetchone()
                                    location_id_to_use = location_result[0] if location_result else 1
                                    print(f"DEBUG: Using fallback location ID after error: {location_id_to_use}")
                            
                            print(f"DEBUG: Using location ID for container: {location_id_to_use}")
                            
                            # Create container with the determined location ID and container type
                            if container_type_id:
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
                                    container_desc,
                                    container_type_id,
                                    1 if sample_data.get('containerIsMixed', False) else 0,
                                    capacity,  # Use supplied capacity or default to amount_per_package
                                    location_id_to_use  # Use container-specific location if specified
                                ))
                            else:
                                # No container type found, create without it
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
                                    container_desc,
                                    1 if sample_data.get('containerIsMixed', False) else 0,
                                    capacity,  # Use supplied capacity or default to amount_per_package
                                    location_id_to_use  # Use container-specific location if specified
                                ))
                            
                            container_id = cursor.lastrowid
                            print(f"DEBUG: Created container with ID: {container_id}")
                            container_ids.append(container_id)
                        
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
                        
                        # Connect samples to the container
                        # Ensure that we're using the exact amount provided by the user
                        # Use amount_per_package for the current package/container
                        
                        # When using one container per package, use the same amount value for consistency
                        container_amount = amount_value
                        
                        # Debug output
                        print(f"DEBUG: Adding sample {sample_id} to container {container_id} with amount {container_amount}")
                        
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
                            container_amount  # Use amount for this specific package/container
                        ))
                        
                        # Log container creation
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
                            'Container created',
                            user_id,
                            sample_id,
                            f"Container {container_id} created for sample {sample_id}"
                        ))
                    except Exception as e:
                        print(f"DEBUG: Error creating container: {e}")
                        import traceback
                        traceback.print_exc()
                        
                        # Important: Re-raise exception to indicate failure
                        # This will trigger transaction rollback
                        raise Exception(f"Failed to create container: {e}")
            
            # Handle serial numbers if relevant
            if sample_data.get('hasSerialNumbers') and sample_data.get('serialNumbers'):
                serial_numbers = sample_data.get('serialNumbers')
                for i, serial_number in enumerate(serial_numbers):
                    cursor.execute("""
                        INSERT INTO SampleSerialNumber (
                            SampleID, 
                            SerialNumber
                        )
                        VALUES (%s, %s)
                    """, (
                        first_sample_id,
                        serial_number
                    ))
            
            # Log the activity in the History table
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
                'Received',
                user_id,
                first_sample_id,
                f"Sample(s) registered: {package_count} package(s) - total amount: {sample_data.get('totalAmount')}"
            ))
            
            # Return relevant data
            response_data = {
                'success': True, 
                'sample_id': f"SMP-{first_sample_id}", 
                'reception_id': reception_id,
                'package_count': package_count
            }
            
            if create_containers and container_ids:
                response_data['container_ids'] = container_ids
                
            return response_data