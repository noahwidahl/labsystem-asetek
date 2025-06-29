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
            
            # Generate a unique barcode if not provided
            base_barcode = sample_data.get('barcode', '')
            if not base_barcode:
                base_barcode = f"BC{reception_id}-{int(datetime.now().timestamp())}"
            
            # Get sample data
            total_amount = int(sample_data.get('totalAmount', 0))
            description = sample_data.get('description', '')
            sample_type = sample_data.get('sampleType', 'single')
            
            # Handle expire date - use provided date or default to 2 months from now
            expire_date = None
            expire_date_input = sample_data.get('expireDate')
            if expire_date_input and expire_date_input.strip():
                try:
                    expire_date = datetime.strptime(expire_date_input, '%Y-%m-%d').date()
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
                base_barcode,
                sample_data.get('partNumber', ''),
                1 if sample_data.get('hasSerialNumbers') else 0,
                sample_type,
                description,
                "In Storage",
                total_amount,
                sample_data.get('unit'),
                sample_data.get('owner'),
                reception_id,
                expire_date
            ))
            
            sample_id = cursor.lastrowid
            
            # Determine storage location
            location_id = sample_data.get('storageLocation')
            if not location_id:
                # Find a valid location ID from the database
                cursor.execute("SELECT LocationID FROM StorageLocation ORDER BY LocationID LIMIT 1")
                location_result = cursor.fetchone()
                if location_result and location_result[0]:
                    location_id = location_result[0]
                else:
                    location_id = "1"
                    print(f"WARNING: Using default location ID 1, no locations found in database")
            
            # Insert to SampleStorage
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
                total_amount,
                expire_date
            ))
            
            storage_id = cursor.lastrowid
            
            # Handle containers if requested
            container_ids = []
            create_containers = sample_data.get('storageOption') == 'container'
            
            if create_containers:
                print(f"DEBUG: Processing container creation")
                
                # Check if using existing container
                if sample_data.get('useExistingContainer') and sample_data.get('existingContainerId'):
                    container_id = sample_data.get('existingContainerId')
                    print(f"DEBUG: Using existing container with ID: {container_id}")
                    
                    # First check if existing container has enough capacity
                    cursor.execute("""
                        SELECT 
                            c.ContainerCapacity,
                            IFNULL(SUM(cs.Amount), 0) as CurrentAmount
                        FROM container c
                        LEFT JOIN ContainerSample cs ON c.ContainerID = cs.ContainerID
                        WHERE c.ContainerID = %s
                        GROUP BY c.ContainerID, c.ContainerCapacity
                    """, (container_id,))
                    
                    capacity_check = cursor.fetchone()
                    if capacity_check:
                        container_capacity = capacity_check[0]
                        current_amount = capacity_check[1] or 0
                        
                        if container_capacity and (current_amount + total_amount > container_capacity):
                            return {
                                'success': False,
                                'error': f'Cannot add {total_amount} samples to container. Current: {current_amount}, Capacity: {container_capacity}, Available: {container_capacity - current_amount}'
                            }
                    
                    container_ids.append(container_id)
                    
                    # Add sample to existing container
                    from app.services.container_service import ContainerService
                    container_service = ContainerService(self.mysql)
                    result = container_service.add_sample_to_container(
                        container_id, 
                        sample_id, 
                        total_amount, 
                        user_id
                    )
                    
                    if not result.get('success'):
                        error_msg = result.get('error', 'Unknown error')
                        print(f"ERROR: Failed to add sample to existing container: {error_msg}")
                        return {
                            'success': False,
                            'error': f'Failed to add sample to existing container: {error_msg}'
                        }
                
                else:
                    # Create new container
                    from app.services.container_service import ContainerService
                    container_service = ContainerService(self.mysql)
                    
                    # Handle container location - convert text to LocationID if needed
                    container_location_id = sample_data.get('containerLocationId')
                    if not container_location_id and sample_data.get('containerLocationText'):
                        # Try to find location by name
                        location_text = sample_data.get('containerLocationText')
                        cursor.execute(
                            "SELECT LocationID FROM StorageLocation WHERE LocationName = %s LIMIT 1",
                            (location_text,)
                        )
                        location_result = cursor.fetchone()
                        if location_result:
                            container_location_id = location_result[0]
                            print(f"DEBUG: Found location ID {container_location_id} for location text '{location_text}'")
                        else:
                            print(f"WARNING: Could not find location for text '{location_text}', using default")
                            container_location_id = location_id
                    elif not container_location_id:
                        container_location_id = location_id
                    
                    container_data = {
                        'description': sample_data.get('containerDescription') or description,
                        'containerTypeId': sample_data.get('containerTypeId'),
                        'newContainerType': sample_data.get('newContainerType'),
                        'locationId': container_location_id,
                        'capacity': sample_data.get('containerCapacity'),
                        'isMixed': sample_data.get('containerIsMixed', False)
                    }
                    
                    # First check if the container will have enough capacity for the sample
                    container_capacity = container_data.get('capacity')
                    if not container_capacity and container_data.get('containerTypeId'):
                        # Get capacity from container type
                        cursor.execute("""
                            SELECT DefaultCapacity 
                            FROM ContainerType 
                            WHERE ContainerTypeID = %s
                        """, (container_data.get('containerTypeId'),))
                        capacity_result = cursor.fetchone()
                        if capacity_result:
                            container_capacity = capacity_result[0]
                    elif not container_capacity and container_data.get('newContainerType'):
                        container_capacity = container_data.get('newContainerType', {}).get('capacity')
                    
                    # Validate capacity before creating container
                    if container_capacity:
                        try:
                            capacity = int(container_capacity)
                            if total_amount > capacity:
                                return {
                                    'success': False,
                                    'error': f'Sample amount ({total_amount}) exceeds container capacity ({capacity}). Please choose a larger container type or reduce the sample amount.'
                                }
                        except (ValueError, TypeError):
                            print(f"WARNING: Invalid container capacity: {container_capacity}")
                    
                    result = container_service.create_container(container_data, user_id)
                    
                    if result.get('success'):
                        container_id = result.get('container_id')
                        container_ids.append(container_id)
                        print(f"DEBUG: Created new container with ID: {container_id}")
                        
                        # Add sample to new container (this will also check capacity again)
                        add_result = container_service.add_sample_to_container(
                            container_id, 
                            sample_id, 
                            total_amount, 
                            user_id
                        )
                        
                        if not add_result.get('success'):
                            error_msg = add_result.get('error', 'Unknown error')
                            print(f"ERROR: Failed to add sample to new container: {error_msg}")
                            return {
                                'success': False,
                                'error': f'Container created but failed to add sample: {error_msg}'
                            }
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        print(f"ERROR: Failed to create container: {error_msg}")
                        return {
                            'success': False,
                            'error': f'Failed to create container: {error_msg}'
                        }
            
            # Add serial numbers if provided
            if sample_data.get('hasSerialNumbers') and sample_data.get('serialNumbers'):
                for serial_number in sample_data.get('serialNumbers', []):
                    cursor.execute("""
                        INSERT INTO SampleSerial (
                            SampleID,
                            SerialNumber
                        )
                        VALUES (%s, %s)
                    """, (
                        sample_id,
                        serial_number
                    ))
            
            # Log the activity
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
                'Sample registered',
                user_id,
                sample_id,
                f"Sample '{description}' registered with {total_amount} units"
            ))
            
            response_data = {
                'success': True,
                'sample_id': sample_id,
                'storage_id': storage_id,
                'reception_id': reception_id
            }
            
            if create_containers and container_ids:
                response_data['container_ids'] = container_ids
                
            return response_data
