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
        # EMERGENCY FIX: Create a direct connection to MySQL to display all samples
        # This bypasses any potential issues with the service layer
        try:
            cursor = self.mysql.connection.cursor()
            print("*** EMERGENCY FIX: Direct query to get all samples ***")

            # Super simple query to grab all samples 
            cursor.execute("""
                SELECT 
                    SampleID, Barcode, PartNumber, IsUnique, Type, Description, 
                    Status, Amount, UnitID, OwnerID, ReceptionID
                FROM Sample 
                ORDER BY SampleID DESC
            """)
            
            results = cursor.fetchall()
            print(f"Found {len(results)} samples via direct query")
            
            # Convert to Sample objects
            samples = []
            for row in results:
                sample = Sample(
                    id=row[0],
                    barcode=row[1],
                    part_number=row[2],
                    is_unique=bool(row[3]) if row[3] is not None else False,
                    type=row[4] if row[4] is not None else 'Standard',
                    description=row[5],
                    status=row[6] if row[6] is not None else "In Storage",
                    amount=row[7] if row[7] is not None else 0,
                    unit_id=row[8],
                    owner_id=row[9],
                    reception_id=row[10]
                )
                samples.append(sample)
            
            # Try to get additional information for each sample
            for sample in samples:
                try:
                    # Get reception date
                    cursor.execute("SELECT ReceivedDate FROM Reception WHERE ReceptionID = %s", (sample.reception_id,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        sample.received_date = result[0]
                    
                    # Get unit name
                    cursor.execute("SELECT UnitName FROM Unit WHERE UnitID = %s", (sample.unit_id,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        sample.unit_name = result[0]
                    
                    # Get location name if a SampleStorage entry exists
                    cursor.execute("""
                        SELECT sl.LocationName 
                        FROM SampleStorage ss 
                        JOIN StorageLocation sl ON ss.LocationID = sl.LocationID 
                        WHERE ss.SampleID = %s
                    """, (sample.id,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        sample.location_name = result[0]
                    else:
                        # If no location exists, try to get a default location
                        cursor.execute("SELECT LocationName FROM StorageLocation LIMIT 1")
                        result = cursor.fetchone()
                        sample.location_name = result[0] if result and result[0] else "Unknown"
                except Exception as e:
                    print(f"Error getting additional info for sample {sample.id}: {e}")
            
            cursor.close()
            return samples
            
        except Exception as direct_error:
            print(f"*** DIRECT QUERY FAILED: {direct_error} ***")
            print("Falling back to regular query method")
            
            # Original query as backup
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
                    s.ReceptionID
                FROM Sample s
                ORDER BY s.SampleID DESC
            """
            
            # No WHERE conditions - get all samples
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
            
            # Determine if it's a multi-package or single sample
            is_multi_package = sample_data.get('isMultiPackage', False)
            # Ensure package_count is 1 when using containers
            if sample_data.get('useExistingContainer', False) or (sample_data.get('createContainers', False) and not is_multi_package):
                # For container operations, always use 1 package
                package_count = 1
            else:
                package_count = int(sample_data.get('packageCount', 1)) if is_multi_package else 1
            
            print(f"DEBUG: is_multi_package={is_multi_package}, package_count={package_count}, useExistingContainer={sample_data.get('useExistingContainer', False)}")
            
            # Generate a unique barcode if not provided
            base_barcode = sample_data.get('barcode', '')
            if not base_barcode:
                base_barcode = f"BC{reception_id}-{int(datetime.now().timestamp())}"
            
            # Variables to keep track of sample_id and storage_id for the first sample
            first_sample_id = None
            first_storage_id = None
            
            # Determine if packages have different locations
            different_locations = sample_data.get('differentLocations', False)
            package_locations = sample_data.get('packageLocations', [])
            
            # Flag for container creation
            create_containers = sample_data.get('createContainers', False)
            # Check for alternate naming
            if not create_containers and sample_data.get('storageOption') == 'container':
                create_containers = True
                sample_data['createContainers'] = True
                print("DEBUG: Setting createContainers=True based on storageOption")
                
            container_ids = []  # List to keep track of created containers
            
            print(f"DEBUG: Creating {package_count} packages, create_containers={create_containers}")
            print(f"DEBUG: Full sample_data for container creation: {sample_data}")
            
            # Iterate through the number of packages
            for i in range(package_count):
                # Generate barcode for each package
                barcode = f"{base_barcode}-{i+1}" if package_count > 1 else base_barcode
                
                # Calculate amount per package
                total_amount = int(sample_data.get('totalAmount', 0))
                amount_per_package = int(sample_data.get('amountPerPackage', total_amount // package_count)) if is_multi_package else total_amount
                
                # Adjust last package if there's a remainder
                if i == package_count - 1 and not is_multi_package and total_amount % package_count != 0:
                    amount_per_package += total_amount % package_count
                
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
                        ReceptionID
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    barcode,
                    sample_data.get('partNumber', ''),
                    1 if sample_data.get('hasSerialNumbers') else 0,
                    sample_data.get('sampleType', 'Standard'),
                    sample_data.get('description') + (f" (Package {i+1})" if is_multi_package and package_count > 1 else ""),
                    "In Storage",
                    amount_per_package,
                    sample_data.get('unit'),
                    sample_data.get('owner'),
                    reception_id
                ))
                
                sample_id = cursor.lastrowid
                
                # Save the first sample_id for later reference
                if first_sample_id is None:
                    first_sample_id = sample_id
                
                # Determine location for this package
                location_id = None
                if different_locations and package_locations:
                    # Find package data for this package number
                    package_data = next((p for p in package_locations if str(p.get('packageNumber', '')) == str(i+1)), None)
                    if package_data:
                        location_id = package_data.get('locationId')
                
                # Use default location if no specific one is found
                if not location_id:
                    location_id = sample_data.get('storageLocation')
                    
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
                    amount_per_package,
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
                        else:
                            # Create new container
                            print(f"DEBUG: Creating container for package {i+1}")
                            # Use container description if provided, or default to generic container name
                            container_desc = (sample_data.get('containerDescription') or '').strip()
                            if not container_desc:
                                container_desc = sample_data.get('description', 'Container')
                                print(f"DEBUG: Container description was empty, using sample description: {container_desc}")
                            if package_count > 1:
                                container_desc += f" (Package {i+1})"
                            
                            # Use 'container' table directly
                            table_name = "container"
                            
                            # Check if we need to create a new container type first
                            if sample_data.get('newContainerType'):
                                print(f"DEBUG: Creating new container type from sample registration")
                                new_type = sample_data.get('newContainerType')
                                
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
                                print(f"DEBUG: Created new container type with ID: {container_type_id}")
                                
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
                            
                            # Get capacity from parameters or default to amount_per_package
                            # If creating a new container type, use its capacity value instead
                            if sample_data.get('newContainerType'):
                                capacity = sample_data.get('newContainerType').get('capacity') or amount_per_package
                                print(f"DEBUG: Using capacity {capacity} from new container type for container")
                            else:
                                capacity = sample_data.get('containerCapacity') or amount_per_package
                            
                            # Get location from parameters or use the one already determined
                            # Check for multiple container locations
                            container_location_id = None
                            container_locations = sample_data.get('containerLocations', [])
                            
                            # If we have specific container locations for multiple packages
                            if container_locations and len(container_locations) > 0:
                                # Try to find location for this package
                                for cl in container_locations:
                                    if str(cl.get('packageNumber', '')) == str(i+1):
                                        container_location_id = cl.get('locationId')
                                        print(f"DEBUG: Using special container location {container_location_id} for package {i+1}")
                                        break
                                
                            # Fallback to main container location or storage location
                            if not container_location_id:
                                container_location_id = sample_data.get('containerLocationId') or location_id
                                print(f"DEBUG: Using fallback container location {container_location_id} for package {i+1}")
                            
                            # Create container with location and container type
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
                                    container_location_id  # Use container-specific location if specified
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
                                    container_location_id  # Use container-specific location if specified
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
                            amount_per_package  # Use amount for this specific package/container
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