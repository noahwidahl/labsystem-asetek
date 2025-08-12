from flask import Blueprint, render_template, jsonify, request
from app.utils.mssql_db import mssql_db
from datetime import datetime

container_mssql_bp = Blueprint('container_mssql', __name__)

@container_mssql_bp.route('/containers')
def containers():
    try:
        # Get containers with details
        containers_results = mssql_db.execute_query("""
            SELECT 
                c.[ContainerID],
                c.[Description],
                c.[ContainerTypeID],
                c.[IsMixed],
                c.[ContainerCapacity],
                ct.[TypeName],
                ISNULL(c.[ContainerStatus], 'Active') as Status,
                c.[LocationID],
                sl.[LocationName],
                COUNT(cs.[ContainerSampleID]) as SampleCount,
                ISNULL(SUM(cs.[Amount]), 0) as TotalItems
            FROM [container] c
            LEFT JOIN [containertype] ct ON c.[ContainerTypeID] = ct.[ContainerTypeID]
            LEFT JOIN [storagelocation] sl ON c.[LocationID] = sl.[LocationID]
            LEFT JOIN [containersample] cs ON c.[ContainerID] = cs.[ContainerID]
            GROUP BY c.[ContainerID], c.[Description], c.[ContainerTypeID], c.[IsMixed], 
                     c.[ContainerCapacity], ct.[TypeName], c.[ContainerStatus], 
                     c.[LocationID], sl.[LocationName]
            ORDER BY c.[ContainerID] DESC
        """, fetch_all=True)
        
        containers_for_template = []
        for row in containers_results:
            containers_for_template.append({
                'ContainerID': row[0],
                'Description': row[1],
                'ContainerTypeID': row[2],
                'IsMixed': row[3],
                'ContainerCapacity': row[4],
                'TypeName': row[5] or 'Standard',
                'Status': row[6],
                'LocationID': row[7],
                'LocationName': row[8] or 'Unknown',
                'SampleCount': row[9],
                'TotalItems': row[10]
            })
        
        # Get container types
        container_types_results = mssql_db.execute_query("""
            SELECT [ContainerTypeID], [TypeName], [Description], [DefaultCapacity] 
            FROM [containertype]
        """, fetch_all=True)
        container_types = []
        for row in container_types_results:
            container_types.append({
                'ContainerTypeID': row[0],
                'TypeName': row[1],
                'Description': row[2],
                'DefaultCapacity': row[3]
            })
        
        # Get storage locations
        locations_results = mssql_db.execute_query("""
            SELECT [LocationID], [LocationName], [Rack], [Section], [Shelf]
            FROM [storagelocation]
            ORDER BY [Rack], [Section], [Shelf]
        """, fetch_all=True)
        locations = []
        for row in locations_results:
            locations.append({
                'LocationID': row[0],
                'LocationName': row[1],
                'Rack': row[2],
                'Section': row[3],
                'Shelf': row[4]
            })
        
        # Get available samples (not in containers)
        available_samples_results = mssql_db.execute_query("""
            SELECT 
                s.[SampleID],
                'SMP-' + CAST(s.[SampleID] AS NVARCHAR) as SampleIDFormatted,
                s.[Description],
                ss.[AmountRemaining],
                CASE
                    WHEN u.[UnitName] IS NULL THEN 'pcs'
                    WHEN LOWER(u.[UnitName]) = 'stk' THEN 'pcs'
                    ELSE u.[UnitName]
                END as Unit
            FROM [sample] s
            JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [unit] u ON s.[UnitID] = u.[UnitID]
            LEFT JOIN [containersample] cs ON ss.[StorageID] = cs.[SampleStorageID]
            WHERE ss.[AmountRemaining] > 0
            AND s.[Status] = 'In Storage'
            AND cs.[ContainerSampleID] IS NULL
            ORDER BY s.[SampleID] DESC
        """, fetch_all=True)
        available_samples = []
        for row in available_samples_results:
            available_samples.append({
                'SampleID': row[0],
                'SampleIDFormatted': row[1],
                'Description': row[2],
                'AmountRemaining': row[3],
                'Unit': row[4]
            })
        
        return render_template('sections/containers.html', 
                            containers=containers_for_template,
                            container_types=container_types,
                            available_samples=available_samples,
                            locations=locations)
    except Exception as e:
        print(f"Error loading containers: {e}")
        import traceback
        traceback.print_exc()
        return render_template('sections/containers.html', 
                            error=f"Error loading containers: {str(e)}",
                            containers=[],
                            container_types=[],
                            available_samples=[],
                            locations=[])

@container_mssql_bp.route('/api/containers/<int:container_id>/location')
def get_container_location(container_id):
    try:
        location_result = mssql_db.execute_query("""
            SELECT 
                sl.[LocationID],
                sl.[LocationName],
                sl.[Rack],
                sl.[Section],
                sl.[Shelf],
                l.[LabName]
            FROM [container] c
            JOIN [storagelocation] sl ON c.[LocationID] = sl.[LocationID]
            JOIN [lab] l ON sl.[LabID] = l.[LabID]
            WHERE c.[ContainerID] = ?
        """, (container_id,), fetch_one=True)
        
        if not location_result:
            return jsonify({'success': False, 'error': 'Location not found'}), 404
        
        location = {
            'LocationID': location_result[0],
            'LocationName': location_result[1],
            'Rack': location_result[2],
            'Section': location_result[3],
            'Shelf': location_result[4],
            'LabName': location_result[5]
        }
        
        return jsonify({'success': True, 'location': location})
    except Exception as e:
        print(f"API error when fetching container location: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@container_mssql_bp.route('/api/containers', methods=['POST'])
def create_container():
    try:
        data = request.json
        
        # Basic validation
        if not data.get('description'):
            return jsonify({'success': False, 'error': 'Description is required'}), 400
        
        # Get current user (simplified for now)
        user_id = 1  # TODO: Implement proper user authentication
        
        # Create container
        result = mssql_db.execute_query("""
            INSERT INTO [container] (
                [Description], 
                [ContainerTypeID], 
                [IsMixed], 
                [ContainerCapacity], 
                [LocationID],
                [ContainerStatus]
            ) 
            OUTPUT INSERTED.ContainerID
            VALUES (?, ?, ?, ?, ?, 'Active')
        """, (
            data.get('description'),
            data.get('containerTypeId'),
            data.get('isMixed', False),
            data.get('capacity'),
            data.get('locationId')
        ), fetch_one=True)
        
        if result:
            container_id = result[0]
            
            # Log activity
            mssql_db.execute_query("""
                INSERT INTO [history] (
                    [Timestamp], 
                    [ActionType], 
                    [UserID], 
                    [Notes]
                )
                VALUES (GETDATE(), 'Container created', ?, ?)
            """, (
                user_id,
                f"Container '{data.get('description')}' created with ID {container_id}"
            ))
            
            return jsonify({
                'success': True, 
                'container_id': container_id,
                'message': 'Container created successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create container'}), 500
            
    except Exception as e:
        print(f"API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@container_mssql_bp.route('/api/containers/available')
def get_available_containers():
    try:
        # First try a simpler query to debug
        containers_results = mssql_db.execute_query("""
            SELECT 
                c.[ContainerID],
                c.[Description],
                c.[ContainerCapacity],
                0 as CurrentAmount,
                ISNULL(sl.[LocationName], 'Unknown') as LocationName
            FROM [container] c
            LEFT JOIN [storagelocation] sl ON c.[LocationID] = sl.[LocationID]
            WHERE c.[ContainerStatus] = 'Active' OR c.[ContainerStatus] IS NULL
            ORDER BY c.[ContainerID] DESC
        """, fetch_all=True)
        
        containers = []
        for row in containers_results:
            containers.append({
                'ContainerID': row[0],
                'Description': row[1],
                'ContainerCapacity': row[2],
                'CurrentAmount': row[3],
                'LocationName': row[4] or 'Unknown'
            })
        
        return jsonify({'success': True, 'containers': containers})
    except Exception as e:
        print(f"API error when fetching available containers: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@container_mssql_bp.route('/api/containers/types')
def get_container_types():
    try:
        container_types_results = mssql_db.execute_query("""
            SELECT [ContainerTypeID], [TypeName], [Description], [DefaultCapacity] 
            FROM [containertype]
        """, fetch_all=True)
        
        container_types = []
        for row in container_types_results:
            container_types.append({
                'ContainerTypeID': row[0],
                'TypeName': row[1],
                'Description': row[2],
                'DefaultCapacity': row[3]
            })
        
        return jsonify({'success': True, 'types': container_types})
    except Exception as e:
        print(f"API error when fetching container types: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@container_mssql_bp.route('/api/locations/<int:location_id>')
def get_location(location_id):
    try:
        location_result = mssql_db.execute_query("""
            SELECT 
                sl.[LocationID],
                sl.[LocationName],
                sl.[Rack],
                sl.[Section], 
                sl.[Shelf],
                l.[LabName]
            FROM [storagelocation] sl
            JOIN [lab] l ON sl.[LabID] = l.[LabID]
            WHERE sl.[LocationID] = ?
        """, (location_id,), fetch_one=True)
        
        if not location_result:
            return jsonify({'success': False, 'error': 'Location not found'}), 404
        
        location = {
            'LocationID': location_result[0],
            'LocationName': location_result[1],
            'Rack': location_result[2],
            'Section': location_result[3],
            'Shelf': location_result[4],
            'LabName': location_result[5]
        }
        
        return jsonify({'success': True, 'location': location})
    except Exception as e:
        print(f"API error getting location details: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@container_mssql_bp.route('/api/locations')
def get_all_locations():
    try:
        locations_results = mssql_db.execute_query("""
            SELECT 
                sl.[LocationID],
                sl.[LocationName],
                sl.[Rack],
                sl.[Section], 
                sl.[Shelf],
                l.[LabName]
            FROM [storagelocation] sl
            JOIN [lab] l ON sl.[LabID] = l.[LabID]
            ORDER BY sl.[Rack], sl.[Section], sl.[Shelf]
        """, fetch_all=True)
        
        locations = []
        for row in locations_results:
            locations.append({
                'LocationID': row[0],
                'LocationName': row[1],
                'Rack': row[2],
                'Section': row[3],
                'Shelf': row[4],
                'LabName': row[5]
            })
        
        return jsonify({'success': True, 'locations': locations})
    except Exception as e:
        print(f"API error getting all locations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@container_mssql_bp.route('/api/basic-locations')
def get_basic_locations():
    try:
        locations_results = mssql_db.execute_query("""
            SELECT [LocationID], [LocationName]
            FROM [storagelocation]
            ORDER BY [Rack], [Section], [Shelf]
        """, fetch_all=True)
        
        locations = []
        for row in locations_results:
            locations.append({
                'LocationID': row[0],
                'LocationName': row[1]
            })
        
        return jsonify({'success': True, 'locations': locations})
    except Exception as e:
        print(f"API error getting basic locations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@container_mssql_bp.route('/api/containers/add-sample', methods=['POST'])
def add_sample_to_container():
    try:
        data = request.json
        
        # Validation
        if not data.get('containerId'):
            return jsonify({'success': False, 'error': 'Container ID missing'}), 400
        if not data.get('sampleId'):
            return jsonify({'success': False, 'error': 'Sample ID missing'}), 400
        
        container_id = data.get('containerId')
        sample_id = data.get('sampleId')
        amount = data.get('amount', 1)
        user_id = 1  # TODO: Implement proper user authentication
        
        # Check container capacity
        container_result = mssql_db.execute_query("""
            SELECT 
                c.[ContainerCapacity],
                ISNULL(SUM(cs.[Amount]), 0) as CurrentAmount
            FROM [container] c
            LEFT JOIN [containersample] cs ON c.[ContainerID] = cs.[ContainerID]
            WHERE c.[ContainerID] = ?
            GROUP BY c.[ContainerID], c.[ContainerCapacity]
        """, (container_id,), fetch_one=True)
        
        if container_result:
            container_capacity = container_result[0]
            current_amount = container_result[1] or 0
            
            if container_capacity and (current_amount + amount > container_capacity):
                if not data.get('force_add', False):
                    return jsonify({
                        'success': False,
                        'error': f'Cannot add {amount} samples to container. Current: {current_amount}, Capacity: {container_capacity}, Available: {container_capacity - current_amount}'
                    })
        
        # Get sample storage ID
        storage_result = mssql_db.execute_query("""
            SELECT [StorageID] FROM [samplestorage] WHERE [SampleID] = ?
        """, (sample_id,), fetch_one=True)
        
        if not storage_result:
            return jsonify({'success': False, 'error': 'Sample storage not found'}), 400
        
        storage_id = storage_result[0]
        
        # Add sample to container
        mssql_db.execute_query("""
            INSERT INTO [containersample] ([ContainerID], [SampleStorageID], [Amount])
            VALUES (?, ?, ?)
        """, (container_id, storage_id, amount))
        
        # Log activity
        mssql_db.execute_query("""
            INSERT INTO [history] (
                [Timestamp], 
                [ActionType], 
                [UserID], 
                [SampleID],
                [Notes]
            )
            VALUES (GETDATE(), 'Sample added to container', ?, ?, ?)
        """, (
            user_id,
            sample_id,
            f"Sample {sample_id} added to container {container_id} with amount {amount}"
        ))
        
        return jsonify({
            'success': True,
            'message': 'Sample added to container successfully'
        })
        
    except Exception as e:
        print(f"API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@container_mssql_bp.route('/api/containers/<int:container_id>', methods=['DELETE'])
def delete_container(container_id):
    try:
        user_id = 1  # TODO: Implement proper user authentication
        
        # Check if container has samples
        samples_count = mssql_db.execute_query("""
            SELECT COUNT(*) FROM [containersample] WHERE [ContainerID] = ?
        """, (container_id,), fetch_one=True)
        
        if samples_count and samples_count[0] > 0:
            return jsonify({
                'success': False,
                'error': 'Cannot delete container that contains samples'
            }), 400
        
        # Delete container
        mssql_db.execute_query("""
            DELETE FROM [container] WHERE [ContainerID] = ?
        """, (container_id,))
        
        # Log activity
        mssql_db.execute_query("""
            INSERT INTO [history] (
                [Timestamp], 
                [ActionType], 
                [UserID], 
                [Notes]
            )
            VALUES (GETDATE(), 'Container deleted', ?, ?)
        """, (
            user_id,
            f"Container {container_id} deleted"
        ))
        
        return jsonify({
            'success': True,
            'message': 'Container deleted successfully'
        })
        
    except Exception as e:
        print(f"API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@container_mssql_bp.route('/api/containers/<int:container_id>', methods=['GET'])
def get_container_details(container_id):
    try:
        # Get container details
        container_result = mssql_db.execute_query("""
            SELECT 
                c.[ContainerID],
                c.[Description],
                c.[ContainerTypeID],
                c.[IsMixed],
                c.[ContainerCapacity],
                ct.[TypeName],
                ISNULL(c.[ContainerStatus], 'Active') as Status,
                c.[LocationID]
            FROM [container] c
            LEFT JOIN [containertype] ct ON c.[ContainerTypeID] = ct.[ContainerTypeID]
            WHERE c.[ContainerID] = ?
        """, (container_id,), fetch_one=True)
        
        if not container_result:
            return jsonify({'success': False, 'error': 'Container not found'}), 404
        
        container = {
            'ContainerID': container_result[0],
            'Description': container_result[1],
            'ContainerTypeID': container_result[2],
            'IsMixed': container_result[3],
            'ContainerCapacity': container_result[4],
            'TypeName': container_result[5],
            'Status': container_result[6],
            'LocationID': container_result[7]
        }
        
        # Get samples in container
        samples_results = mssql_db.execute_query("""
            SELECT 
                s.[SampleID],
                s.[Description],
                s.[PartNumber],
                cs.[Amount],
                CASE
                    WHEN u.[UnitName] IS NULL THEN 'pcs'
                    WHEN LOWER(u.[UnitName]) = 'stk' THEN 'pcs'
                    ELSE u.[UnitName]
                END as Unit,
                sl.[LocationName],
                ss.[ExpireDate],
                FORMAT(r.[ReceivedDate], 'dd-MM-yyyy') as RegisteredDate,
                ss.[StorageID] as SampleStorageID
            FROM [containersample] cs
            JOIN [samplestorage] ss ON cs.[SampleStorageID] = ss.[StorageID]
            JOIN [sample] s ON ss.[SampleID] = s.[SampleID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            LEFT JOIN [reception] r ON s.[ReceptionID] = r.[ReceptionID]
            LEFT JOIN [unit] u ON s.[UnitID] = u.[UnitID]
            WHERE cs.[ContainerID] = ?
        """, (container_id,), fetch_all=True)
        
        samples = []
        for row in samples_results:
            samples.append({
                'SampleID': row[0],
                'Description': row[1],
                'PartNumber': row[2],
                'Amount': row[3],
                'Unit': row[4],
                'LocationName': row[5],
                'ExpireDate': row[6],
                'RegisteredDate': row[7],
                'SampleStorageID': row[8]
            })
        
        # Get container history
        history_results = mssql_db.execute_query("""
            SELECT TOP 20
                FORMAT(h.[Timestamp], 'dd-MM-yyyy HH:mm') as Timestamp,
                h.[ActionType],
                h.[Notes],
                u.[Name] as UserName
            FROM [history] h
            LEFT JOIN [user] u ON h.[UserID] = u.[UserID]
            WHERE h.[Notes] LIKE '%Container ' + CAST(? AS NVARCHAR) + '%'
            ORDER BY h.[Timestamp] DESC
        """, (container_id,), fetch_all=True)
        
        history = []
        for row in history_results:
            history.append({
                'Timestamp': row[0],
                'ActionType': row[1],
                'Notes': row[2],
                'UserName': row[3]
            })
        
        return jsonify({
            'success': True,
            'container': container,
            'samples': samples,
            'history': history
        })
        
    except Exception as e:
        print(f"API error getting container details: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500