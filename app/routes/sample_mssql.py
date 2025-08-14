from flask import Blueprint, render_template, jsonify, request
from app.utils.mssql_db import mssql_db
from datetime import datetime, timedelta

sample_mssql_bp = Blueprint('sample_mssql', __name__)

@sample_mssql_bp.route('/register')
def register():
    try:
        # Get suppliers
        suppliers_results = mssql_db.execute_query("SELECT [SupplierID], [SupplierName] FROM [supplier]", fetch_all=True)
        suppliers = [{'SupplierID': row[0], 'SupplierName': row[1]} for row in suppliers_results]
        
        # Get users
        users_results = mssql_db.execute_query("SELECT [UserID], [Name] FROM [user]", fetch_all=True)
        users = [{'UserID': row[0], 'Name': row[1]} for row in users_results]
        
        # Get units (translate 'stk' to 'pcs')
        units_results = mssql_db.execute_query("SELECT [UnitID], [UnitName] FROM [unit] ORDER BY [UnitName]", fetch_all=True)
        units = []
        for row in units_results:
            unit_name = row[1]
            # Translate 'stk' to 'pcs' for consistency
            if unit_name.lower() == 'stk':
                unit_name = 'pcs'
            units.append({'UnitID': row[0], 'UnitName': unit_name})
        
        # Get locations
        locations_results = mssql_db.execute_query("""
            SELECT l.[LocationID], l.[LocationName], lb.[LabName]
            FROM [storagelocation] l
            JOIN [lab] lb ON l.[LabID] = lb.[LabID]
        """, fetch_all=True)
        locations = []
        for row in locations_results:
            locations.append({
                'LocationID': row[0],
                'LocationName': row[1],
                'LabName': row[2]
            })
        
        # Get container types
        container_types_results = mssql_db.execute_query("SELECT [ContainerTypeID], [TypeName], [Description], [DefaultCapacity] FROM [containertype]", fetch_all=True)
        container_types = []
        for row in container_types_results:
            container_types.append({
                'ContainerTypeID': row[0],
                'TypeName': row[1],
                'Description': row[2],
                'DefaultCapacity': row[3]
            })
        
        # Get active tasks
        tasks_results = mssql_db.execute_query("""
            SELECT [TaskID], [TaskNumber], [TaskName], [Status] 
            FROM [task] 
            WHERE [Status] IN ('Planning', 'Active', 'On Hold')
            ORDER BY [TaskNumber] DESC
        """, fetch_all=True)
        tasks = []
        for row in tasks_results:
            tasks.append({
                'TaskID': row[0],
                'TaskNumber': row[1],
                'TaskName': row[2],
                'Status': row[3]
            })
        
        return render_template('sections/register.html', 
                            suppliers=suppliers,
                            users=users,
                            units=units,
                            locations=locations,
                            container_types=container_types,
                            tasks=tasks)
    except Exception as e:
        print(f"Error loading register page: {e}")
        return render_template('sections/register.html', 
                            error="Error loading registration form")

@sample_mssql_bp.route('/samples')
def samples():
    try:
        # Initialize empty array for samples
        samples_for_template = []
        
        # Get filter parameters
        filter_criteria = {}
        search = request.args.get('search', '')
        location = request.args.get('location', '')
        status = request.args.get('status', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Tracking which filters are active
        if search:
            filter_criteria['search'] = search
        if location:
            filter_criteria['location'] = location
        if status:
            filter_criteria['status'] = status
        if date_from:
            filter_criteria['date_from'] = date_from
        if date_to:
            filter_criteria['date_to'] = date_to
        
        # Get sort parameters
        sort_by = request.args.get('sort_by', 'sample_id')
        sort_order = request.args.get('sort_order', 'DESC')
        
        # Get dropdown options for filters
        locations = mssql_db.execute_query("""
            SELECT [LocationID], [LocationName] FROM [storagelocation] ORDER BY [LocationName]
        """, fetch_all=True)
        locations = [{'LocationID': row[0], 'LocationName': row[1]} for row in locations or []]
        
        statuses = mssql_db.execute_query("""
            SELECT DISTINCT [Status] FROM [sample]
        """, fetch_all=True)
        statuses = [row[0] for row in statuses or []]
        
        # Build WHERE conditions for filtering
        where_conditions = []
        query_params = []
        
        # Add search filter
        if search:
            where_conditions.append("""
                (s.[Description] LIKE ? 
                 OR s.[PartNumber] LIKE ? 
                 OR ('SMP-' + CAST(s.[SampleID] AS NVARCHAR)) LIKE ?
                 OR CAST(s.[SampleID] AS NVARCHAR) LIKE ?)
            """)
            search_term = f"%{search}%"
            query_params.extend([search_term, search_term, search_term, search_term])
        
        # Add location filter
        if location:
            where_conditions.append("ss.[LocationID] = ?")
            query_params.append(location)
        
        # Add status filter
        if status:
            where_conditions.append("s.[Status] = ?")
            query_params.append(status)
        
        # Add date range filters
        if date_from:
            where_conditions.append("CAST(r.[ReceivedDate] AS DATE) >= ?")
            query_params.append(date_from)
        
        if date_to:
            where_conditions.append("CAST(r.[ReceivedDate] AS DATE) <= ?")
            query_params.append(date_to)
        
        # Build WHERE clause
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Count total filtered samples
        count_query = f"""
        SELECT COUNT(*) 
        FROM [sample] s
        JOIN [reception] r ON s.[ReceptionID] = r.[ReceptionID]
        LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
        LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
        LEFT JOIN [unit] u ON s.[UnitID] = u.[UnitID]
        {where_clause}
        """
        
        total_filtered_samples = mssql_db.execute_query(count_query, query_params, fetch_one=True)[0]
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = 20  # Show 20 samples per page
        offset = (page - 1) * per_page
        
        # Build ORDER BY clause
        order_by_clause = "ORDER BY "
        if sort_by == 'sample_id':
            order_by_clause += f"s.[SampleID] {sort_order}"
        elif sort_by == 'part_number':
            order_by_clause += f"s.[PartNumber] {sort_order}"
        elif sort_by == 'description':
            order_by_clause += f"s.[Description] {sort_order}"
        elif sort_by in ['registered_date', 'reception_date']:
            order_by_clause += f"r.[ReceivedDate] {sort_order}"
        elif sort_by == 'amount':
            order_by_clause += f"AmountRemaining {sort_order}"
        elif sort_by == 'location':
            order_by_clause += f"sl.[LocationName] {sort_order}"
        elif sort_by == 'status':
            order_by_clause += f"s.[Status] {sort_order}"
        else:
            order_by_clause += f"s.[SampleID] {sort_order}"  # Default sort
        
        # Get filtered and paginated samples
        query = f"""
        SELECT 
            s.[SampleID], 
            s.[PartNumber], 
            s.[Description], 
            CASE 
                WHEN s.[Status] = 'Disposed' THEN 0
                ELSE ISNULL(ss.[AmountRemaining], 0)
            END AS AmountRemaining, 
            CASE
                WHEN u.[UnitName] IS NULL THEN 'pcs'
                WHEN LOWER(u.[UnitName]) = 'stk' THEN 'pcs'
                ELSE u.[UnitName]
            END as Unit,
            ISNULL(sl.[LocationName], 'Disposed') as LocationName, 
            FORMAT(r.[ReceivedDate], 'dd-MM-yyyy HH:mm') AS Registered,
            s.[Status] 
        FROM [sample] s
        JOIN [reception] r ON s.[ReceptionID] = r.[ReceptionID]
        LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
        LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
        LEFT JOIN [unit] u ON s.[UnitID] = u.[UnitID]
        {where_clause}
        {order_by_clause}
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        
        query_params.extend([offset, per_page])
        db_results = mssql_db.execute_query(query, query_params, fetch_all=True)
        
        # Convert database results to template format
        samples_for_template = []
        
        for row in db_results or []:
            sample = {
                "ID": f"SMP-{row[0]}",
                "PartNumber": row[1] or "",
                "Description": row[2] or "",
                "Amount": f"{row[3]} {row[4]}",
                "Location": row[5] or "Unknown",
                "Registered": row[6] or "",
                "Status": row[7] or "Unknown"
            }
            samples_for_template.append(sample)
        
        # Calculate pagination info
        total_pages = (total_filtered_samples + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages
        
        pagination_info = {
            'page': page,
            'per_page': per_page,
            'total': total_filtered_samples,
            'pages': total_pages,
            'has_prev': has_prev,
            'has_next': has_next,
            'prev_num': page - 1 if has_prev else None,
            'next_num': page + 1 if has_next else None
        }
        
        return render_template('sections/storage.html', 
                            samples=samples_for_template,
                            locations=locations,
                            statuses=statuses,
                            filter_criteria=filter_criteria,
                            current_sort_by=sort_by,
                            current_sort_order=sort_order,
                            current_search=search,
                            page=pagination_info['page'],
                            per_page=pagination_info['per_page'],
                            total_samples=pagination_info['total'],
                            total_pages=pagination_info['pages'])
                            
    except Exception as e:
        print(f"Error loading samples page: {e}")
        import traceback
        traceback.print_exc()
        return render_template('sections/storage.html', 
                            samples=[],
                            locations=[],
                            statuses=[],
                            filter_criteria={},
                            page=1,
                            per_page=20,
                            total_samples=0,
                            total_pages=1,
                            sort_by='sample_id',
                            sort_order='DESC',
                            error="Error loading samples data")

@sample_mssql_bp.route('/storage')
def storage():
    try:
        # Get basic sample data for storage overview
        samples_results = mssql_db.execute_query("""
            SELECT TOP 100
                s.[SampleID], 
                s.[Barcode], 
                s.[PartNumber],
                s.[IsUnique],
                s.[Type],
                s.[Description], 
                s.[Status],
                s.[Amount], 
                s.[UnitID],
                s.[OwnerID],
                s.[ReceptionID],
                r.[ReceivedDate],
                CASE
                    WHEN u.[UnitName] IS NULL THEN 'pcs'
                    WHEN LOWER(u.[UnitName]) = 'stk' THEN 'pcs'
                    ELSE u.[UnitName]
                END as UnitName,
                ISNULL(sl.[LocationName], 'Unknown') as LocationName
            FROM [sample] s
            LEFT JOIN [reception] r ON s.[ReceptionID] = r.[ReceptionID]
            LEFT JOIN [unit] u ON s.[UnitID] = u.[UnitID]
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            WHERE s.[Status] = 'In Storage'
            ORDER BY s.[SampleID] DESC
        """, fetch_all=True)
        
        samples = []
        for row in samples_results or []:
            samples.append({
                'ID': f"SMP-{row[0]}",
                'PartNumber': row[2] or "",
                'Description': row[5] or "",
                'Amount': f"{row[7]} {row[12]}",
                'Location': row[13] or "Unknown",
                'Registered': row[11].strftime('%d-%m-%Y %H:%M') if row[11] else "",
                'Status': row[6] or "Unknown"
            })
        
        # Get locations for filter dropdown
        locations_results = mssql_db.execute_query("""
            SELECT DISTINCT sl.[LocationName]
            FROM [storagelocation] sl
            JOIN [samplestorage] ss ON sl.[LocationID] = ss.[LocationID]
            WHERE ss.[AmountRemaining] > 0
            ORDER BY sl.[LocationName]
        """, fetch_all=True)
        locations = [row[0] for row in locations_results]
        
        # Calculate pagination info for template
        page = 1  # Default page
        per_page = 20
        total_samples = len(samples)
        total_pages = max(1, (total_samples + per_page - 1) // per_page)
        
        return render_template('sections/storage.html', 
                            samples=samples,
                            locations=locations,
                            filter_criteria={},
                            page=page,
                            per_page=per_page,
                            total_samples=total_samples,
                            total_pages=total_pages)
    except Exception as e:
        print(f"Error loading storage page: {e}")
        return render_template('sections/storage.html', 
                            samples=[],
                            locations=[],
                            filter_criteria={},
                            page=1,
                            per_page=20,
                            total_samples=0,
                            total_pages=1,
                            error="Error loading storage data")

@sample_mssql_bp.route('/disposal')
def disposal_page():
    return render_template('sections/disposal.html')

@sample_mssql_bp.route('/expiry')
def expiry_page():
    try:
        # Get samples that are expiring or expired
        expiring_results = mssql_db.execute_query("""
            SELECT 
                s.[SampleID],
                s.[Barcode],
                s.[Description],
                s.[PartNumber],
                s.[Status],
                s.[Amount],
                s.[ExpireDate],
                u.[UnitName],
                sl.[LocationName],
                CASE 
                    WHEN s.[ExpireDate] < CAST(GETDATE() AS DATE) THEN 'Expired'
                    WHEN s.[ExpireDate] <= DATEADD(DAY, 14, CAST(GETDATE() AS DATE)) THEN 'Expiring Soon'
                    ELSE 'OK'
                END as ExpiryStatus,
                DATEDIFF(DAY, CAST(GETDATE() AS DATE), s.[ExpireDate]) as DaysToExpiry
            FROM [sample] s
            LEFT JOIN [unit] u ON s.[UnitID] = u.[UnitID]
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            WHERE s.[ExpireDate] IS NOT NULL 
            AND s.[Status] = 'In Storage'
            AND s.[ExpireDate] <= DATEADD(DAY, 30, CAST(GETDATE() AS DATE))
            ORDER BY s.[ExpireDate] ASC
        """, fetch_all=True)
        
        expiring_samples = []
        for row in expiring_results:
            expiring_samples.append({
                'SampleID': row[0],
                'Barcode': row[1],
                'Description': row[2],
                'PartNumber': row[3],
                'Status': row[4],
                'Amount': row[5],
                'ExpireDate': row[6],
                'UnitName': row[7] or 'pcs',
                'LocationName': row[8] or 'Unknown',
                'ExpiryStatus': row[9],
                'DaysToExpiry': row[10]
            })
        
        return render_template('sections/expiry.html', 
                            expiring_samples=expiring_samples)
    except Exception as e:
        print(f"Error loading expiry page: {e}")
        return render_template('sections/expiry.html', 
                            expiring_samples=[],
                            error="Error loading expiry data")

# ======================= API ENDPOINTS =======================

@sample_mssql_bp.route('/api/samples', methods=['POST'])
def create_sample():
    try:
        data = request.json
        user_id = 1  # TODO: Implement proper user authentication
        
        # Basic validation
        if not data.get('description'):
            return jsonify({
                'success': False, 
                'error': 'Description is required'
            }), 400
        
        # Create sample via database
        # Generate barcode if not provided
        barcode = data.get('barcode', f"BC{datetime.now().strftime('%Y%m%d%H%M%S')}")
        
        # Handle supplier ID - make sure it exists or use NULL
        supplier_id = data.get('supplier')
        print(f"DEBUG: Original supplier ID from request: {supplier_id} (type: {type(supplier_id)})")
        print(f"DEBUG: Full request data: {data}")
        
        # Also debug what suppliers exist in database
        try:
            all_suppliers = mssql_db.execute_query("""
                SELECT TOP 5 [SupplierID], [SupplierName] FROM [supplier] ORDER BY [SupplierID]
            """, fetch_all=True)
            print(f"DEBUG: Available suppliers: {all_suppliers}")
        except Exception as e:
            print(f"DEBUG: Error checking suppliers: {e}")
        
        # Clean up supplier ID - handle empty strings, None, 0, etc.
        if supplier_id in [None, '', '0', 0, 'null', 'undefined']:
            supplier_id = None
            print("DEBUG: Supplier ID set to None (empty/invalid)")
        else:
            try:
                supplier_id = int(supplier_id)
                # Verify supplier exists
                supplier_check = mssql_db.execute_query("""
                    SELECT [SupplierID] FROM [supplier] WHERE [SupplierID] = ?
                """, (supplier_id,), fetch_one=True)
                if not supplier_check:
                    print(f"DEBUG: Supplier ID {supplier_id} not found in database, setting to None")
                    supplier_id = None
                else:
                    print(f"DEBUG: Supplier ID {supplier_id} validated successfully")
            except (ValueError, TypeError):
                print(f"DEBUG: Invalid supplier ID format: {supplier_id}, setting to None")
                supplier_id = None
        
        # Use a single transaction for both reception and sample creation
        print(f"DEBUG: About to create reception and sample in transaction with supplier_id={supplier_id}, user_id={user_id}")
        
        # Create everything in a single transaction
        with mssql_db.transaction() as cursor:
            # Create reception first  
            source_type = 'External' if supplier_id else 'Internal'
            cursor.execute("""
                INSERT INTO [reception] ([SupplierID], [ReceivedDate], [UserID], [TrackingNumber], [SourceType], [Notes])
                OUTPUT INSERTED.ReceptionID
                VALUES (?, GETDATE(), ?, ?, ?, ?)
            """, (
                supplier_id,
                user_id,
                data.get('trackingNumber', ''),
                source_type,
                data.get('other', 'Registered via lab system')
            ))
            reception_result = cursor.fetchone()
            
            if not reception_result:
                raise Exception('Failed to create reception')
                
            reception_id = reception_result[0]
            
            # Create sample using the reception ID
            cursor.execute("""
                INSERT INTO [sample] ([Barcode], [PartNumber], [IsUnique], [Type], [Description], [Status], 
                                      [Amount], [UnitID], [OwnerID], [ReceptionID], [TaskID], [ExpireDate])
                OUTPUT INSERTED.SampleID
                VALUES (?, ?, ?, ?, ?, 'In Storage', ?, ?, ?, ?, ?, ?)
            """, (
                barcode,
                data.get('partNumber', ''),
                1 if data.get('hasSerialNumbers') else 0,
                data.get('sampleType', 'single').lower(),
                data.get('description'),
                int(data.get('totalAmount', 1)),
                data.get('unit'),
                data.get('owner'),
                reception_id,
                data.get('task'),
                data.get('expireDate')
            ))
            sample_result = cursor.fetchone()
            
            if not sample_result:
                raise Exception('Failed to create sample')
                
            sample_id = sample_result[0]
            print(f"DEBUG: Transaction completed - reception_id={reception_id}, sample_id={sample_id}")
        
        if sample_id:
            # Insert storage record
            mssql_db.execute_query("""
                INSERT INTO [samplestorage] ([SampleID], [LocationID], [AmountRemaining], [ExpireDate])
                VALUES (?, ?, ?, ?)
            """, (
                sample_id,
                data.get('storageLocation', 1),
                int(data.get('totalAmount', 1)),
                data.get('expireDate')
            ))
            
            # Log activity
            mssql_db.execute_query("""
                INSERT INTO [history] ([Timestamp], [ActionType], [UserID], [SampleID], [Notes])
                VALUES (GETDATE(), 'Sample registered', ?, ?, ?)
            """, (
                user_id,
                sample_id,
                f"Sample '{data.get('description')}' registered with {data.get('totalAmount', 1)} units"
            ))
            
            # Handle containers if requested
            container_ids = []
            create_containers = data.get('storageOption') == 'container'
            
            if create_containers:
                print(f"DEBUG: Processing container creation")
                
                # Check if using existing container
                if data.get('useExistingContainer') and data.get('existingContainerId'):
                    container_id = int(data.get('existingContainerId'))
                    print(f"DEBUG: Using existing container with ID: {container_id}")
                    
                    # Check if existing container has enough capacity
                    capacity_result = mssql_db.execute_query("""
                        SELECT 
                            c.[ContainerCapacity],
                            ISNULL(SUM(cs.[Amount]), 0) as CurrentAmount
                        FROM [container] c
                        LEFT JOIN [containersample] cs ON c.[ContainerID] = cs.[ContainerID]
                        WHERE c.[ContainerID] = ?
                        GROUP BY c.[ContainerID], c.[ContainerCapacity]
                    """, (container_id,), fetch_one=True)
                    
                    if capacity_result:
                        container_capacity = capacity_result[0]
                        current_amount = capacity_result[1] or 0
                        total_amount = int(data.get('totalAmount', 1))
                        
                        if container_capacity and (current_amount + total_amount > container_capacity):
                            return jsonify({
                                'success': False,
                                'error': f'Cannot add {total_amount} samples to container. Current: {current_amount}, Capacity: {container_capacity}, Available: {container_capacity - current_amount}'
                            }), 400
                    
                    container_ids.append(container_id)
                    
                    # Add sample to existing container
                    storage_result = mssql_db.execute_query("""
                        SELECT [StorageID] FROM [samplestorage] WHERE [SampleID] = ?
                    """, (sample_id,), fetch_one=True)
                    
                    if storage_result:
                        storage_id = storage_result[0]
                        mssql_db.execute_query("""
                            INSERT INTO [containersample] ([ContainerID], [SampleStorageID], [Amount])
                            VALUES (?, ?, ?)
                        """, (container_id, storage_id, int(data.get('totalAmount', 1))))
                
                else:
                    # Create new containers
                    print(f"DEBUG: Creating new containers")
                    container_count = int(data.get('containerCount', 1))
                    container_description = data.get('containerDescription', '')
                    
                    # Initialize container_type_id
                    container_type_id = data.get('containerTypeId')
                    
                    # Convert to int if it's a string
                    if container_type_id and str(container_type_id).isdigit():
                        container_type_id = int(container_type_id)
                    
                    # Only check if container type is required when not creating a new one
                    new_container_type = data.get('newContainerType')
                    if not container_type_id and not new_container_type:
                        return jsonify({'success': False, 'error': 'Container type is required'}), 400
                    
                    print(f"DEBUG: Starting container creation transaction with count={container_count}")
                    
                    # Use single database transaction for both container type and container creation
                    with mssql_db.get_connection() as conn:
                        cursor = conn.cursor()
                        try:
                            print(f"DEBUG: Transaction started successfully")
                            
                            # Create new container type if needed within this transaction
                            if new_container_type:
                                print(f"DEBUG: Creating new container type in transaction: {new_container_type}")
                                
                                cursor.execute("""
                                    INSERT INTO [containertype] ([TypeName], [Description], [DefaultCapacity])
                                    OUTPUT INSERTED.ContainerTypeID
                                    VALUES (?, ?, ?)
                                """, (
                                    new_container_type.get('typeName'),
                                    new_container_type.get('description', ''),
                                    int(new_container_type.get('capacity', 50))
                                ))
                                
                                type_result = cursor.fetchone()
                                if type_result:
                                    container_type_id = type_result[0]
                                    print(f"DEBUG: Created new container type with ID: {container_type_id}")
                                
                                    # Log the container type creation in same transaction
                                    cursor.execute("""
                                        INSERT INTO [history] ([ActionType], [UserID], [Notes], [Timestamp])
                                        VALUES (?, ?, ?, GETDATE())
                                    """, (
                                        'Container type created',
                                        user_id,
                                        f"Container type '{new_container_type.get('typeName')}' created"
                                    ))
                                else:
                                    raise Exception('Failed to create new container type')
                            
                            print(f"DEBUG: About to create container with final container_type_id={container_type_id}")
                            
                            for i in range(container_count):
                                print(f"DEBUG: Creating container {i+1} of {container_count}")
                                # Generate unique container barcode
                                container_barcode = f"CNT{datetime.now().strftime('%Y%m%d%H%M%S')}{str(i).zfill(3)}"
                                
                                # Get container capacity from container type
                                cursor.execute("""
                                    SELECT [DefaultCapacity] FROM [containertype] WHERE [ContainerTypeID] = ?
                                """, (container_type_id,))
                                capacity_result = cursor.fetchone()
                                container_capacity = capacity_result[0] if capacity_result else 50
                                
                                # Create container
                                print(f"DEBUG: Creating container with barcode={container_barcode}, type_id={container_type_id}, capacity={container_capacity}")
                                
                                cursor.execute("""
                                    INSERT INTO [container] (
                                        [Barcode], 
                                        [ContainerTypeID], 
                                        [Description], 
                                        [LocationID],
                                        [ContainerCapacity], 
                                        [IsMixed],
                                        [ContainerStatus]
                                    ) 
                                    OUTPUT INSERTED.ContainerID
                                    VALUES (?, ?, ?, ?, ?, ?, 'Active')
                                """, (
                                    container_barcode,
                                    container_type_id,
                                    container_description,
                                    data.get('storageLocation', 1),
                                    container_capacity,
                                    data.get('containerIsMixed', False)
                                ))
                                
                                container_result = cursor.fetchone()
                                if container_result:
                                    container_id = container_result[0]
                                    container_ids.append(container_id)
                                    print(f"DEBUG: Successfully created container with ID: {container_id}")
                                    
                                    # Add sample to new container in same transaction
                                    cursor.execute("""
                                        SELECT [StorageID] FROM [samplestorage] WHERE [SampleID] = ?
                                    """, (sample_id,))
                                    storage_result = cursor.fetchone()
                                    
                                    if storage_result:
                                        storage_id = storage_result[0]
                                        cursor.execute("""
                                            INSERT INTO [containersample] ([ContainerID], [SampleStorageID], [Amount])
                                            VALUES (?, ?, ?)
                                        """, (container_id, storage_id, int(data.get('totalAmount', 1)) // container_count))
                                        print(f"DEBUG: Added sample {sample_id} to container {container_id}")
                                    else:
                                        print(f"ERROR: Could not find storage record for sample {sample_id}")
                                else:
                                    print(f"ERROR: Container creation failed - no result returned")
                            
                            conn.commit()
                        except Exception as e:
                            conn.rollback()
                            print(f"ERROR: Container creation transaction failed: {e}")
                            raise
            
            # Get additional data for frontend
            location_name = 'Unknown'
            if data.get('storageLocation'):
                location_result = mssql_db.execute_query("""
                    SELECT [LocationName] FROM [storagelocation] WHERE [LocationID] = ?
                """, (data.get('storageLocation'),), fetch_one=True)
                if location_result:
                    location_name = location_result[0]
            
            # Get unit name
            unit_name = 'pcs'
            if data.get('unit'):
                unit_result = mssql_db.execute_query("""
                    SELECT [UnitName] FROM [unit] WHERE [UnitID] = ?
                """, (data.get('unit'),), fetch_one=True)
                if unit_result:
                    unit_name = unit_result[0]
            
            # Get task name if applicable
            task_name = None
            if data.get('task'):
                task_result = mssql_db.execute_query("""
                    SELECT [TaskName] FROM [task] WHERE [TaskID] = ?
                """, (data.get('task'),), fetch_one=True)
                if task_result:
                    task_name = task_result[0]
            
            response_data = {
                'success': True,
                'sample_id': sample_id,
                'reception_id': reception_id,
                'barcode': barcode,
                'sample_data': {
                    'SampleID': sample_id,
                    'SampleIDFormatted': f'SMP-{sample_id}',
                    'Description': data.get('description'),
                    'Barcode': barcode,
                    'PartNumber': data.get('partNumber', ''),
                    'Type': data.get('sampleType', 'single'),
                    'Amount': int(data.get('totalAmount', 1)),
                    'UnitName': unit_name,
                    'LocationName': location_name,
                    'ExpireDate': data.get('expireDate', ''),
                    'SerialNumbers': data.get('serialNumbers', []),
                    'HasSerialNumbers': bool(data.get('hasSerialNumbers')),
                    'TaskName': task_name
                }
            }
            
            # Add container information if containers were created
            if create_containers:
                if container_ids:
                    response_data['container_ids'] = container_ids
                    print(f"DEBUG: Added container_ids to response: {container_ids}")
                else:
                    print(f"DEBUG: Containers were requested but none were created successfully")
            
            return jsonify(response_data)
        else:
            return jsonify({'success': False, 'error': 'Failed to create sample'}), 500
            
    except Exception as e:
        print(f"API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@sample_mssql_bp.route('/api/samples/<int:sample_id>', methods=['DELETE'])
def delete_sample(sample_id):
    try:
        user_id = 1  # TODO: Implement proper user authentication
        
        # Delete related records first (foreign key constraints)
        mssql_db.execute_query("DELETE FROM [history] WHERE [SampleID] = ?", (sample_id,))
        mssql_db.execute_query("DELETE FROM [testsampleusage] WHERE [SampleID] = ?", (sample_id,))
        mssql_db.execute_query("DELETE FROM [containersample] WHERE [SampleStorageID] IN (SELECT [StorageID] FROM [samplestorage] WHERE [SampleID] = ?)", (sample_id,))
        mssql_db.execute_query("DELETE FROM [samplestorage] WHERE [SampleID] = ?", (sample_id,))
        mssql_db.execute_query("DELETE FROM [sampleserialnumber] WHERE [SampleID] = ?", (sample_id,))
        mssql_db.execute_query("DELETE FROM [sample] WHERE [SampleID] = ?", (sample_id,))
        
        # Log deletion
        mssql_db.execute_query("""
            INSERT INTO [history] ([Timestamp], [ActionType], [UserID], [Notes])
            VALUES (GETDATE(), 'Sample deleted', ?, ?)
        """, (user_id, f"Sample {sample_id} deleted"))
        
        return jsonify({
            'success': True,
            'sample_id': sample_id
        })
    except Exception as e:
        print(f"API error deleting sample: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@sample_mssql_bp.route('/api/activeSamples')
def get_active_samples():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        search = request.args.get('search', '')
        offset = (page - 1) * per_page
        
        # Build search conditions
        search_conditions = ""
        search_params = []
        if search:
            search_conditions = """
                AND (s.[Description] LIKE ? 
                     OR s.[Barcode] LIKE ? 
                     OR s.[PartNumber] LIKE ?
                     OR ('SMP-' + CAST(s.[SampleID] AS NVARCHAR)) LIKE ?)
            """
            search_term = f"%{search}%"
            search_params = [search_term, search_term, search_term, search_term]
        
        # Get total count
        count_query = f"""
            SELECT COUNT(DISTINCT s.[SampleID])
            FROM [sample] s
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            WHERE s.[Status] = 'In Storage' AND (ss.[AmountRemaining] > 0 OR ss.[AmountRemaining] IS NULL)
            {search_conditions}
        """
        total_count = mssql_db.execute_query(count_query, search_params, fetch_one=True)[0]
        
        # Get samples
        main_query = f"""
            SELECT 
                s.[SampleID], 
                s.[Description], 
                s.[Barcode],
                ISNULL(s.[PartNumber], '') as PartNumber,
                ss.[AmountRemaining],
                ISNULL(sl.[LocationName], 'Unknown') as LocationName,
                ISNULL(u.[Name], 'Unknown') as OwnerName,
                CASE
                    WHEN un.[UnitName] IS NULL THEN 'pcs'
                    WHEN LOWER(un.[UnitName]) = 'stk' THEN 'pcs'
                    ELSE un.[UnitName]
                END as Unit,
                CASE WHEN s.[IsUnique] = 1 THEN 1 ELSE 0 END as IsUnique
            FROM [sample] s
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            LEFT JOIN [user] u ON s.[OwnerID] = u.[UserID]
            LEFT JOIN [unit] un ON s.[UnitID] = un.[UnitID]
            WHERE s.[Status] = 'In Storage' AND (ss.[AmountRemaining] > 0 OR ss.[AmountRemaining] IS NULL)
            {search_conditions}
            ORDER BY s.[SampleID] DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        
        results = mssql_db.execute_query(main_query, search_params + [offset, per_page], fetch_all=True)
        
        samples = []
        for row in results or []:
            sample_dict = {
                'SampleID': row[0],
                'SampleIDFormatted': f"SMP-{row[0]}",
                'Description': row[1],
                'Barcode': row[2],
                'PartNumber': row[3],
                'AmountRemaining': row[4] or 1,
                'LocationName': row[5],
                'OwnerName': row[6],
                'Unit': row[7],
                'IsUnique': row[8]
            }
            
            # Get serial numbers for unique samples
            if sample_dict['IsUnique'] == 1:
                serials = mssql_db.execute_query("""
                    SELECT [SerialNumber] FROM [sampleserialnumber] 
                    WHERE [SampleID] = ? AND [IsActive] = 1
                """, (row[0],), fetch_all=True)
                sample_dict['SerialNumbers'] = [s[0] for s in serials or []]
                sample_dict['AmountRemaining'] = len(sample_dict['SerialNumbers'])
            
            samples.append(sample_dict)
        
        # Calculate pagination
        total_pages = (total_count + per_page - 1) // per_page
        
        return jsonify({
            'success': True,
            'samples': samples,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        })
    except Exception as e:
        print(f"API error getting active samples: {e}")
        return jsonify({
            'success': False,
            'samples': [],
            'error': str(e)
        }), 500

@sample_mssql_bp.route('/api/samples/<int:sample_id>', methods=['GET'])
def get_sample_details(sample_id):
    """
    Get detailed information about a specific sample - CRITICAL FOR DETAILS BUTTON!
    """
    try:
        # Get sample basic info
        sample_result = mssql_db.execute_query("""
            SELECT 
                s.[SampleID],
                s.[PartNumber],
                s.[Description],
                s.[Barcode],
                s.[Status],
                CASE
                    WHEN un.[UnitName] IS NULL THEN 'pcs'
                    WHEN LOWER(un.[UnitName]) = 'stk' THEN 'pcs'
                    ELSE un.[UnitName]
                END as Unit,
                r.[Notes] as Comments,
                FORMAT(r.[ReceivedDate], 'dd-MM-yyyy HH:mm') as RegisteredDate,
                owner.[Name] as RegisteredBy,
                ss.[AmountRemaining] as Amount,
                sl.[LocationName] as Location,
                c.[ContainerID],
                c.[Description] as ContainerName,
                r.[TrackingNumber],
                sp.[SupplierName],
                r.[SourceType],
                receiver.[Name] as ReceivedBy
            FROM [sample] s
            LEFT JOIN [reception] r ON s.[ReceptionID] = r.[ReceptionID]
            LEFT JOIN [user] owner ON s.[OwnerID] = owner.[UserID]
            LEFT JOIN [user] receiver ON r.[UserID] = receiver.[UserID]
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            LEFT JOIN [containersample] cs ON ss.[StorageID] = cs.[SampleStorageID]
            LEFT JOIN [container] c ON cs.[ContainerID] = c.[ContainerID]
            LEFT JOIN [unit] un ON s.[UnitID] = un.[UnitID]
            LEFT JOIN [supplier] sp ON r.[SupplierID] = sp.[SupplierID]
            WHERE s.[SampleID] = ?
        """, (sample_id,), fetch_one=True)
        
        if not sample_result:
            return jsonify({
                'success': False,
                'error': f'Sample with ID {sample_id} not found'
            }), 404
        
        sample = {
            'SampleID': str(sample_result[0]),
            'PartNumber': sample_result[1],
            'Description': sample_result[2],
            'Barcode': sample_result[3],
            'Status': sample_result[4],
            'Unit': sample_result[5],
            'Comments': sample_result[6],
            'RegisteredDate': sample_result[7],
            'RegisteredBy': sample_result[8],
            'Amount': float(sample_result[9]) if sample_result[9] else 0.0,
            'Location': sample_result[10],
            'ContainerID': int(sample_result[11]) if sample_result[11] else None,
            'ContainerName': sample_result[12] if sample_result[12] else None,
            'TrackingNumber': sample_result[13],
            'SupplierName': sample_result[14],
            'SourceType': sample_result[15],
            'ReceivedBy': sample_result[16]
        }
        
        # Get serial numbers
        serial_results = mssql_db.execute_query("""
            SELECT [SerialNumber] FROM [sampleserialnumber] 
            WHERE [SampleID] = ? AND [IsActive] = 1
            ORDER BY [CreatedDate]
        """, (sample_id,), fetch_all=True)
        serial_numbers = [row[0] for row in serial_results or []]
        
        # Get sample history
        history_results = mssql_db.execute_query("""
            SELECT 
                h.[LogID],
                FORMAT(h.[Timestamp], 'dd-MM-yyyy HH:mm') as Timestamp,
                h.[ActionType],
                u.[Name] as UserName,
                h.[Notes]
            FROM [history] h
            LEFT JOIN [user] u ON h.[UserID] = u.[UserID]
            WHERE h.[SampleID] = ?
            ORDER BY h.[Timestamp] DESC
        """, (sample_id,), fetch_all=True)
        
        history = []
        for row in history_results or []:
            history.append({
                'LogID': int(row[0]) if row[0] else None,
                'Timestamp': str(row[1]) if row[1] else None,
                'ActionType': row[2],
                'UserName': row[3],
                'Notes': row[4]
            })
        
        return jsonify({
            'success': True,
            'sample': sample,
            'history': history,
            'serial_numbers': serial_numbers
        })
    except Exception as e:
        print(f"API error getting sample details: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sample_mssql_bp.route('/api/samples/<int:sample_id>/move-location', methods=['POST'])
def move_sample_to_location(sample_id):
    """
    Move a sample to a direct storage location - CRITICAL FOR MOVE BUTTON!
    """
    try:
        data = request.json
        location_id = data.get('locationId')
        move_amount = int(data.get('amount', 0))
        user_id = 1  # TODO: Implement proper user authentication
        
        if not location_id:
            return jsonify({
                'success': False,
                'error': 'Location ID is required'
            }), 400
        
        # Check if sample exists
        sample_result = mssql_db.execute_query("""
            SELECT s.[SampleID], s.[Status], s.[Description]
            FROM [sample] s WHERE s.[SampleID] = ?
        """, (sample_id,), fetch_one=True)
        
        if not sample_result:
            return jsonify({
                'success': False,
                'error': f'Sample with ID {sample_id} not found'
            }), 404
        
        if sample_result[1] == 'Disposed':
            return jsonify({
                'success': False,
                'error': 'Cannot move a disposed sample'
            }), 400
        
        # Update storage location
        mssql_db.execute_query("""
            UPDATE [samplestorage] 
            SET [LocationID] = ?
            WHERE [SampleID] = ?
        """, (location_id, sample_id))
        
        # Get location name for logging
        location_result = mssql_db.execute_query("""
            SELECT [LocationName] FROM [storagelocation] WHERE [LocationID] = ?
        """, (location_id,), fetch_one=True)
        location_name = location_result[0] if location_result else f"Location {location_id}"
        
        # Log the move
        mssql_db.execute_query("""
            INSERT INTO [history] ([Timestamp], [ActionType], [UserID], [SampleID], [Notes])
            VALUES (GETDATE(), 'Sample moved', ?, ?, ?)
        """, (
            user_id,
            sample_id,
            f"Sample moved to {location_name}"
        ))
        
        return jsonify({
            'success': True,
            'message': f'Sample successfully moved to {location_name}'
        })
        
    except Exception as e:
        print(f"API error moving sample: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sample_mssql_bp.route('/api/createDisposal', methods=['POST'])
def create_disposal():
    """
    Create disposal record - CRITICAL FOR DISPOSAL FUNCTIONALITY!
    """
    try:
        data = request.json
        user_id = 1  # TODO: Implement proper user authentication
        
        # Validate required fields
        if not data.get('sampleId'):
            return jsonify({'success': False, 'error': 'Sample ID is required'}), 400
        
        if not data.get('amount') or int(data.get('amount', 0)) <= 0:
            return jsonify({'success': False, 'error': 'Valid amount is required'}), 400
        
        sample_id = data['sampleId']
        disposal_amount = int(data['amount'])
        
        # Get current amount from storage
        storage_result = mssql_db.execute_query("""
            SELECT [StorageID], [AmountRemaining] 
            FROM [samplestorage] 
            WHERE [SampleID] = ? AND [AmountRemaining] > 0
        """, (sample_id,), fetch_one=True)
        
        if not storage_result:
            return jsonify({
                'success': False,
                'error': 'No available storage for this sample'
            }), 400
        
        storage_id = storage_result[0]
        amount_remaining = storage_result[1]
        
        if disposal_amount > amount_remaining:
            return jsonify({
                'success': False,
                'error': f'Requested amount ({disposal_amount}) exceeds available amount ({amount_remaining})'
            }), 400
        
        # Update storage amount
        new_amount = amount_remaining - disposal_amount
        mssql_db.execute_query("""
            UPDATE [samplestorage] 
            SET [AmountRemaining] = ?
            WHERE [StorageID] = ?
        """, (new_amount, storage_id))
        
        # If all amount is disposed, update sample status
        if new_amount == 0:
            mssql_db.execute_query("""
                UPDATE [sample] 
                SET [Status] = 'Disposed' 
                WHERE [SampleID] = ?
            """, (sample_id,))
        
        # Log the disposal
        notes = data.get('notes') or "Disposed through system"
        notes = f"Amount: {disposal_amount} - {notes}"
        
        mssql_db.execute_query("""
            INSERT INTO [history] ([Timestamp], [ActionType], [UserID], [SampleID], [Notes])
            VALUES (GETDATE(), 'Disposed', ?, ?, ?)
        """, (user_id, sample_id, notes))
        
        return jsonify({
            'success': True,
            'message': f"Successfully disposed {disposal_amount} units of sample SMP-{sample_id}"
        })
        
    except Exception as e:
        print(f"API error creating disposal: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@sample_mssql_bp.route('/api/search', methods=['GET'])
def global_search():
    """
    Global search endpoint for the header search bar
    """
    try:
        search_term = request.args.get('q', '').strip()
        
        if not search_term or len(search_term) < 2:
            return jsonify({
                'success': False,
                'error': 'Search term must be at least 2 characters',
                'results': []
            })
        
        search_param = f"%{search_term}%"
        
        # Search samples
        sample_results = mssql_db.execute_query("""
            SELECT TOP 10
                'Sample' as result_type,
                'SMP-' + CAST(s.[SampleID] AS NVARCHAR) as id,
                s.[Description] as title,
                ISNULL(s.[PartNumber], 'No part number') as subtitle,
                s.[Status] as status,
                '/storage?search=' + ? as url
            FROM [sample] s
            WHERE s.[Description] LIKE ? OR s.[PartNumber] LIKE ? OR s.[Barcode] LIKE ?
        """, (search_term, search_param, search_param, search_param), fetch_all=True)
        
        # Search locations
        location_results = mssql_db.execute_query("""
            SELECT TOP 5
                'Location' as result_type,
                'LOC-' + CAST(sl.[LocationID] AS NVARCHAR) as id,
                sl.[LocationName] as title,
                l.[LabName] as subtitle,
                'Active' as status,
                '/storage?location=' + CAST(sl.[LocationID] AS NVARCHAR) as url
            FROM [storagelocation] sl
            JOIN [lab] l ON sl.[LabID] = l.[LabID]
            WHERE sl.[LocationName] LIKE ?
        """, (search_param,), fetch_all=True)
        
        # Search tests
        test_results = mssql_db.execute_query("""
            SELECT TOP 5
                'Test' as result_type,
                'TST-' + CAST(t.[TestID] AS NVARCHAR) as id,
                'Test #' + CAST(t.[TestID] AS NVARCHAR) as title,
                u.[Name] as subtitle,
                t.[Status] as status,
                '/testing' as url
            FROM [test] t
            JOIN [user] u ON t.[UserID] = u.[UserID]
            WHERE CAST(t.[TestID] AS NVARCHAR) LIKE ?
        """, (search_param,), fetch_all=True)
        
        # Combine results
        results = []
        for row in (sample_results or []) + (location_results or []) + (test_results or []):
            results.append({
                'result_type': row[0],
                'id': row[1],
                'title': row[2],
                'subtitle': row[3],
                'status': row[4],
                'url': row[5]
            })
        
        return jsonify({
            'success': True,
            'query': search_term,
            'results': results
        })
    except Exception as e:
        print(f"API error in global search: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'results': []
        }), 500

@sample_mssql_bp.route('/api/samples/by-task/<int:task_id>')
def get_samples_by_task(task_id):
    try:
        # Get samples assigned to task directly
        samples_results = mssql_db.execute_query("""
            SELECT 
                s.[SampleID],
                s.[Description],
                s.[PartNumber],
                s.[Barcode],
                s.[Status],
                ss.[AmountRemaining],
                sl.[LocationName],
                CASE
                    WHEN un.[UnitName] IS NULL THEN 'pcs'
                    WHEN LOWER(un.[UnitName]) = 'stk' THEN 'pcs'
                    ELSE un.[UnitName]
                END as Unit,
                'Registered to task' as Purpose,
                'Assigned' as AssignmentStatus,
                r.[ReceivedDate] as AssignedDate
            FROM [sample] s
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            LEFT JOIN [unit] un ON s.[UnitID] = un.[UnitID]
            LEFT JOIN [reception] r ON s.[ReceptionID] = r.[ReceptionID]
            WHERE s.[TaskID] = ? AND s.[Status] = 'In Storage'
            ORDER BY r.[ReceivedDate] DESC
        """, (task_id,), fetch_all=True)
        
        samples = []
        for row in samples_results or []:
            samples.append({
                'SampleID': row[0],
                'SampleIDFormatted': f"SMP-{row[0]}",
                'Description': row[1] or '',
                'PartNumber': row[2] or '',
                'Barcode': row[3] or '',
                'Status': row[4],
                'AmountRemaining': row[5] or 1,
                'LocationName': row[6] or 'Unknown',
                'Unit': row[7],
                'Purpose': row[8] or '',
                'AssignmentStatus': row[9],
                'AssignedDate': row[10].strftime('%Y-%m-%d %H:%M:%S') if row[10] else None
            })
        
        return jsonify({
            'success': True,
            'samples': samples,
            'count': len(samples)
        })
    except Exception as e:
        print(f"Error getting samples by task: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sample_mssql_bp.route('/api/recentDisposals')
def get_recent_disposals():
    try:
        disposals_results = mssql_db.execute_query("""
            SELECT TOP 10
                h.[LogID],
                FORMAT(h.[Timestamp], 'dd-MM-yyyy HH:mm') as DisposalDate,
                'SMP-' + CAST(h.[SampleID] AS NVARCHAR) as SampleID,
                h.[Notes] as AmountDisposed,
                u.[Name] as DisposedBy
            FROM [history] h
            JOIN [user] u ON h.[UserID] = u.[UserID]
            WHERE h.[ActionType] = 'Disposed'
            ORDER BY h.[Timestamp] DESC
        """, fetch_all=True)
        
        disposals = []
        for row in disposals_results or []:
            disposal_dict = {
                'LogID': row[0],
                'DisposalDate': row[1],
                'SampleID': row[2],
                'AmountDisposed': row[3],
                'DisposedBy': row[4]
            }
            
            # Clean up amount disposed - extract just the number if possible
            amount_str = disposal_dict.get('AmountDisposed', '')
            if 'Amount:' in amount_str:
                try:
                    import re
                    amount_match = re.search(r'Amount:\s*(\d+)', amount_str)
                    if amount_match:
                        disposal_dict['AmountDisposed'] = amount_match.group(1)
                except:
                    pass
            
            disposals.append(disposal_dict)
        
        return jsonify({
            'success': True,
            'disposals': disposals
        })
    except Exception as e:
        print(f"API error getting recent disposals: {e}")
        return jsonify({
            'success': False,
            'disposals': [],
            'error': str(e)
        }), 500

@sample_mssql_bp.route('/api/samples/<int:sample_id>/remove-from-container', methods=['POST'])
def remove_sample_from_container(sample_id):
    """
    Remove a sample from its current container - CRITICAL FOR MOVE FUNCTIONALITY!
    """
    try:
        user_id = 1  # TODO: Implement proper user authentication
        
        # Check if sample exists
        sample_result = mssql_db.execute_query("""
            SELECT s.[SampleID], s.[Status] FROM [sample] s WHERE s.[SampleID] = ?
        """, (sample_id,), fetch_one=True)
        
        if not sample_result:
            return jsonify({
                'success': False,
                'error': f'Sample with ID {sample_id} not found'
            }), 404
            
        if sample_result[1] == 'Disposed':
            return jsonify({
                'success': False,
                'error': 'Cannot move a disposed sample'
            }), 400
        
        # Remove from container by updating containersample table
        container_result = mssql_db.execute_query("""
            SELECT cs.[ContainerID], c.[Description] 
            FROM [containersample] cs
            JOIN [container] c ON cs.[ContainerID] = c.[ContainerID]
            JOIN [samplestorage] ss ON cs.[SampleStorageID] = ss.[StorageID]
            WHERE ss.[SampleID] = ?
        """, (sample_id,), fetch_one=True)
        
        if container_result:
            # Remove from container
            mssql_db.execute_query("""
                DELETE FROM [containersample] 
                WHERE [SampleStorageID] IN (
                    SELECT [StorageID] FROM [samplestorage] WHERE [SampleID] = ?
                )
            """, (sample_id,))
            
            container_name = container_result[1] or f"Container {container_result[0]}"
            
            # Log the action
            mssql_db.execute_query("""
                INSERT INTO [history] ([Timestamp], [ActionType], [UserID], [SampleID], [Notes])
                VALUES (GETDATE(), 'Sample moved', ?, ?, ?)
            """, (user_id, sample_id, f"Sample removed from container: {container_name}"))
            
            return jsonify({
                'success': True,
                'message': f'Sample removed from {container_name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Sample is not currently in a container'
            }), 400
            
    except Exception as e:
        print(f"API error removing sample from container: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sample_mssql_bp.route('/api/suppliers/search', methods=['GET'])
def search_suppliers():
    """Search suppliers by name - CRITICAL FOR SUPPLIER DROPDOWNS!"""
    try:
        search_query = request.args.get('q', '').strip()
        
        if not search_query:
            return jsonify({
                'success': True,
                'suppliers': []
            })
        
        # Search suppliers by name (case-insensitive partial match)
        suppliers_results = mssql_db.execute_query("""
            SELECT TOP 10 [SupplierID], [SupplierName] 
            FROM [supplier] 
            WHERE [SupplierName] LIKE ?
            ORDER BY [SupplierName]
        """, (f"%{search_query}%",), fetch_all=True)
        
        suppliers = []
        for row in suppliers_results or []:
            suppliers.append({
                'id': row[0],
                'name': row[1]
            })
        
        return jsonify({
            'success': True,
            'suppliers': suppliers
        })
        
    except Exception as e:
        print(f"API error searching suppliers: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'suppliers': []
        }), 500

@sample_mssql_bp.route('/api/notifications/create-test-data', methods=['POST'])
def create_test_notification_data():
    """Create test notification data for development"""
    try:
        user_id = 1  # TODO: Implement proper user authentication
        
        # Create some test notification entries
        test_notifications = [
            "Sample SMP-123 expires in 5 days",
            "Test T456 completed successfully", 
            "Container CNT-789 moved to new location"
        ]
        
        for note in test_notifications:
            mssql_db.execute_query("""
                INSERT INTO [history] ([Timestamp], [ActionType], [UserID], [Notes])
                VALUES (GETDATE(), 'System notification', ?, ?)
            """, (user_id, note))
        
        return jsonify({
            'success': True,
            'message': f'Created {len(test_notifications)} test notifications'
        })
    except Exception as e:
        print(f"API error creating test notifications: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sample_mssql_bp.route('/api/suppliers', methods=['POST'])
def create_supplier():
    """Create new supplier - CRITICAL FOR SUPPLIER MANAGEMENT!"""
    try:
        data = request.json
        user_id = 1  # TODO: Implement proper user authentication
        
        if not data.get('name'):
            return jsonify({
                'success': False,
                'error': 'Supplier name is required'
            }), 400
        
        # Check if supplier already exists
        existing = mssql_db.execute_query("""
            SELECT [SupplierID] FROM [supplier] WHERE [SupplierName] = ?
        """, (data['name'],), fetch_one=True)
        
        if existing:
            return jsonify({
                'success': False,
                'error': 'Supplier with this name already exists'
            }), 409
        
        # Create new supplier
        supplier_result = mssql_db.execute_query("""
            INSERT INTO [supplier] ([SupplierName])
            OUTPUT INSERTED.SupplierID
            VALUES (?)
        """, (data['name'],), fetch_one=True)
        
        supplier_id = supplier_result[0] if supplier_result else None
        
        if supplier_id:
            # Log the action
            mssql_db.execute_query("""
                INSERT INTO [history] ([Timestamp], [ActionType], [UserID], [Notes])
                VALUES (GETDATE(), 'Supplier created', ?, ?)
            """, (user_id, f"New supplier created: {data['name']}"))
            
            return jsonify({
                'success': True,
                'supplier_id': supplier_id,
                'name': data['name']
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create supplier'
            }), 500
    except Exception as e:
        print(f"API error creating supplier: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sample_mssql_bp.route('/api/validate-serial-numbers', methods=['POST'])
def validate_serial_numbers():
    """Validate serial numbers for unique samples - CRITICAL FOR SERIAL NUMBER VALIDATION!"""
    try:
        data = request.json
        sample_id = data.get('sample_id')
        serial_numbers = data.get('serial_numbers', [])
        
        if not sample_id or not serial_numbers:
            return jsonify({
                'success': False,
                'error': 'Sample ID and serial numbers are required'
            }), 400
        
        # Check if sample exists and is unique
        sample_result = mssql_db.execute_query("""
            SELECT [SampleID], [IsUnique], [Description] 
            FROM [sample] WHERE [SampleID] = ?
        """, (sample_id,), fetch_one=True)
        
        if not sample_result:
            return jsonify({
                'success': False,
                'error': f'Sample {sample_id} not found'
            }), 404
        
        if not sample_result[1]:  # IsUnique
            return jsonify({
                'success': False,
                'error': 'Sample is not marked as unique'
            }), 400
        
        validation_results = []
        duplicates = []
        
        for serial_num in serial_numbers:
            # Check if serial number already exists
            existing = mssql_db.execute_query("""
                SELECT sn.[SampleID], s.[Description]
                FROM [sampleserialnumber] sn
                JOIN [sample] s ON sn.[SampleID] = s.[SampleID]
                WHERE sn.[SerialNumber] = ? AND sn.[SampleID] != ? AND sn.[IsActive] = 1
            """, (serial_num, sample_id), fetch_one=True)
            
            if existing:
                validation_results.append({
                    'serial_number': serial_num,
                    'valid': False,
                    'error': f'Already used by sample {existing[0]}: {existing[1]}'
                })
                duplicates.append(serial_num)
            else:
                validation_results.append({
                    'serial_number': serial_num,
                    'valid': True,
                    'error': None
                })
        
        return jsonify({
            'success': True,
            'validation_results': validation_results,
            'all_valid': len(duplicates) == 0,
            'duplicate_count': len(duplicates),
            'duplicates': duplicates
        })
    except Exception as e:
        print(f"API error validating serial numbers: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@sample_mssql_bp.route('/api/samples/recent')
def get_recent_samples():
    """Get recently registered samples - CRITICAL FOR DASHBOARD!"""
    try:
        limit = request.args.get('limit', 10, type=int)
        limit = min(limit, 50)  # Cap at 50
        
        recent_results = mssql_db.execute_query("""
            SELECT TOP (?)
                s.[SampleID],
                s.[Description], 
                s.[PartNumber],
                s.[Barcode],
                s.[Status],
                FORMAT(r.[ReceivedDate], 'dd-MM-yyyy HH:mm') as RegisteredDate,
                u.[Name] as RegisteredBy,
                ss.[AmountRemaining]
            FROM [sample] s
            LEFT JOIN [reception] r ON s.[ReceptionID] = r.[ReceptionID]
            LEFT JOIN [user] u ON r.[UserID] = u.[UserID]
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            ORDER BY r.[ReceivedDate] DESC
        """, (limit,), fetch_all=True)
        
        samples = []
        for row in recent_results or []:
            samples.append({
                'SampleID': row[0],
                'SampleIDFormatted': f"SMP-{row[0]}",
                'Description': row[1],
                'PartNumber': row[2] or '',
                'Barcode': row[3] or '',
                'Status': row[4],
                'RegisteredDate': row[5],
                'RegisteredBy': row[6] or 'Unknown',
                'Amount': row[7] or 1
            })
        
        return jsonify({
            'success': True,
            'samples': samples,
            'count': len(samples)
        })
    except Exception as e:
        print(f"API error getting recent samples: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'samples': []
        }), 500

@sample_mssql_bp.route('/api/samples/last')
def get_last_sample():
    """Get the last registered sample - CRITICAL FOR SAMPLE REGISTRATION!"""
    try:
        last_result = mssql_db.execute_query("""
            SELECT TOP 1
                s.[SampleID],
                s.[Description], 
                s.[PartNumber],
                s.[Barcode],
                s.[Status],
                FORMAT(r.[ReceivedDate], 'dd-MM-yyyy HH:mm') as RegisteredDate,
                u.[Name] as RegisteredBy
            FROM [sample] s
            LEFT JOIN [reception] r ON s.[ReceptionID] = r.[ReceptionID]
            LEFT JOIN [user] u ON r.[UserID] = u.[UserID]
            ORDER BY s.[SampleID] DESC
        """, fetch_one=True)
        
        if last_result:
            sample = {
                'SampleID': last_result[0],
                'SampleIDFormatted': f"SMP-{last_result[0]}",
                'Description': last_result[1],
                'PartNumber': last_result[2] or '',
                'Barcode': last_result[3] or '',
                'Status': last_result[4],
                'RegisteredDate': last_result[5],
                'RegisteredBy': last_result[6] or 'Unknown'
            }
            
            return jsonify({
                'success': True,
                'sample': sample
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No samples found',
                'sample': None
            }), 404
    except Exception as e:
        print(f"API error getting last sample: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'sample': None
        }), 500

@sample_mssql_bp.route('/api/samples/available-for-task', methods=['GET'])
def get_samples_available_for_task():
    """Get samples available for assignment to tasks - CRITICAL FOR TASK MANAGEMENT!"""
    try:
        task_id = request.args.get('task_id', type=int)
        search = request.args.get('search', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        offset = (page - 1) * per_page
        
        # Build search condition
        search_condition = ""
        search_params = []
        if search:
            search_condition = """
                AND (s.[Description] LIKE ? 
                     OR s.[PartNumber] LIKE ?
                     OR s.[Barcode] LIKE ?)
            """
            search_term = f"%{search}%"
            search_params = [search_term, search_term, search_term]
        
        # Get count of available samples
        count_query = f"""
            SELECT COUNT(*)
            FROM [sample] s
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            WHERE s.[Status] = 'In Storage' 
            AND (ss.[AmountRemaining] > 0 OR ss.[AmountRemaining] IS NULL)
            AND (s.[TaskID] IS NULL OR s.[TaskID] != ?)
            {search_condition}
        """
        count_params = [task_id] + search_params if task_id else [0] + search_params
        total_count = mssql_db.execute_query(count_query, count_params, fetch_one=True)[0]
        
        # Get available samples
        main_query = f"""
            SELECT 
                s.[SampleID],
                s.[Description],
                s.[PartNumber],
                s.[Barcode],
                s.[Status],
                ss.[AmountRemaining],
                sl.[LocationName],
                CASE
                    WHEN un.[UnitName] IS NULL THEN 'pcs'
                    WHEN LOWER(un.[UnitName]) = 'stk' THEN 'pcs'
                    ELSE un.[UnitName]
                END as Unit,
                FORMAT(r.[ReceivedDate], 'dd-MM-yyyy') as RegisteredDate
            FROM [sample] s
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            LEFT JOIN [unit] un ON s.[UnitID] = un.[UnitID]
            LEFT JOIN [reception] r ON s.[ReceptionID] = r.[ReceptionID]
            WHERE s.[Status] = 'In Storage' 
            AND (ss.[AmountRemaining] > 0 OR ss.[AmountRemaining] IS NULL)
            AND (s.[TaskID] IS NULL OR s.[TaskID] != ?)
            {search_condition}
            ORDER BY s.[SampleID] DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        main_params = count_params + [offset, per_page]
        
        results = mssql_db.execute_query(main_query, main_params, fetch_all=True)
        
        samples = []
        for row in results or []:
            samples.append({
                'SampleID': row[0],
                'SampleIDFormatted': f"SMP-{row[0]}",
                'Description': row[1] or '',
                'PartNumber': row[2] or '',
                'Barcode': row[3] or '',
                'Status': row[4],
                'Amount': row[5] or 1,
                'LocationName': row[6] or 'Unknown',
                'Unit': row[7],
                'RegisteredDate': row[8]
            })
        
        # Calculate pagination
        total_pages = (total_count + per_page - 1) // per_page
        
        return jsonify({
            'success': True,
            'samples': samples,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        })
    except Exception as e:
        print(f"API error getting available samples for task: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'samples': []
        }), 500

# Print functionality for MSSQL
@sample_mssql_bp.route('/api/print/sample/<int:sample_id>', methods=['POST'])
def print_sample_label_endpoint(sample_id):
    """
    MSSQL version - Endpoint to print sample label for a specific sample.
    """
    try:
        data = request.get_json() or {}
        auto_print = data.get('auto_print', True)
        
        # Get sample details
        sample_result = mssql_db.execute_query("""
            SELECT 
                s.SampleID,
                s.Description,
                s.PartNumber,
                s.Barcode,
                s.Amount,
                s.Type,
                s.ExpireDate,
                u.UnitName,
                sl.LocationName,
                t.TaskName
            FROM [sample] s
            LEFT JOIN [unit] u ON s.UnitID = u.UnitID
            LEFT JOIN [samplestorage] ss ON s.SampleID = ss.SampleID
            LEFT JOIN [storagelocation] sl ON ss.LocationID = sl.LocationID
            LEFT JOIN [task] t ON s.TaskID = t.TaskID
            WHERE s.SampleID = ?
        """, (sample_id,), fetch_one=True)
        
        if not sample_result:
            return jsonify({
                'status': 'error',
                'message': f'Sample {sample_id} not found'
            }), 404
        
        # Prepare sample data for label
        sample_data = {
            'SampleID': sample_result[0],
            'SampleIDFormatted': f'SMP-{sample_result[0]}',
            'Description': sample_result[1] or '',
            'PartNumber': sample_result[2] or '',
            'Barcode': sample_result[3] or '',
            'Amount': sample_result[4] or 1,
            'Type': sample_result[5] or 'Standard',
            'ExpireDate': sample_result[6].strftime('%d-%m-%Y') if sample_result[6] else '',
            'UnitName': 'pcs' if (sample_result[7] or '').lower() == 'stk' else (sample_result[7] or 'pcs'),
            'LocationName': sample_result[8] or '',
            'TaskName': sample_result[9] or 'None'
        }
        
        # Import the actual print function from printer.py
        from app.routes.printer import print_sample_label
        result = print_sample_label(sample_data, auto_print)
        return jsonify(result)
        
    except Exception as e:
        print(f"Sample label print endpoint error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Sample label print error: {str(e)}'
        }), 500