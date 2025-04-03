from datetime import datetime
from app.models.sample import Sample
from app.utils.db import DatabaseManager

class SampleService:
    def __init__(self, mysql):
        self.mysql = mysql
        self.db = DatabaseManager(mysql)
    
    def get_all_samples(self):
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
            WHERE ss.AmountRemaining > 0
            ORDER BY s.SampleID DESC
        """
        
        result, _ = self.db.execute_query(query)
        
        samples = []
        for row in result:
            samples.append(Sample.from_db_row(row))
        
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
            container_ids = []  # List to keep track of created containers
            
            print(f"DEBUG: Creating {package_count} packages, create_containers={create_containers}")
            
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
                    location_id = "1"
                
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
                            container_desc = sample_data.get('containerDescription', 'Container')
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
                            container_location_id = sample_data.get('containerLocationId') or location_id
                            
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
                            amount_per_package
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