from flask import Blueprint, jsonify, request
from app.utils.mssql_db import mssql_db

barcode_mssql_bp = Blueprint('barcode_mssql', __name__)

@barcode_mssql_bp.route('/api/barcode/<barcode>', methods=['GET'])
def lookup_barcode(barcode):
    """
    Universal barcode lookup endpoint for scanner functionality - MSSQL version.
    Handles containers (CNT-), samples (BC/SMP-), and test samples (TST-).
    """
    print(f"🚀 DEBUG API: lookup_barcode called with: {barcode}")
    try:
        barcode = barcode.upper().strip()
        print(f"🔍 DEBUG API: Processed barcode: {barcode}")
        
        # Determine barcode type and lookup accordingly
        if barcode.startswith('CNT-'):
            print(f"📦 DEBUG API: Container barcode detected")
            return lookup_container_barcode(barcode)
        elif barcode.startswith('BC') or barcode.startswith('SMP-'):
            print(f"🧪 DEBUG API: Sample barcode detected")
            return lookup_sample_barcode(barcode)
        else:
            print(f"❌ DEBUG API: Unknown barcode format: {barcode}")
            return jsonify({
                'success': False,
                'error': f'Unknown barcode format: {barcode}'
            }), 400
            
    except Exception as e:
        print(f"💥 DEBUG API: Error looking up barcode {barcode}: {e}")
        import traceback
        print(f"🔥 DEBUG API: Full traceback:\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def lookup_container_barcode(barcode):
    """Lookup container by CNT- barcode - MSSQL version"""
    print(f"📦 DEBUG API: lookup_container_barcode called with: {barcode}")
    # Extract container ID from CNT-123 format
    try:
        container_id = int(barcode.replace('CNT-', ''))
        print(f"🔢 DEBUG API: Extracted container ID: {container_id}")
    except ValueError:
        print(f"❌ DEBUG API: Invalid container barcode format: {barcode}")
        return jsonify({
            'success': False,
            'error': f'Invalid container barcode format: {barcode}'
        }), 400
    
    # Get container information
    container_result = mssql_db.execute_query("""
        SELECT 
            c.[ContainerID], c.[Description], c.[ContainerCapacity], c.[ContainerStatus],
            ct.[TypeName], sl.[LocationName]
        FROM [container] c
        LEFT JOIN [containertype] ct ON c.[ContainerTypeID] = ct.[ContainerTypeID]
        LEFT JOIN [storagelocation] sl ON c.[LocationID] = sl.[LocationID]
        WHERE c.[ContainerID] = ?
    """, (container_id,), fetch_one=True)
    
    if not container_result:
        return jsonify({
            'success': False,
            'error': f'Container not found: {barcode}'
        }), 404
    
    container = {
        'ContainerID': container_result[0],
        'Description': container_result[1],
        'ContainerCapacity': container_result[2],
        'ContainerStatus': container_result[3],
        'TypeName': container_result[4] or 'Unknown',
        'LocationName': container_result[5] or 'Unknown'
    }
    
    # Get samples in container
    samples_result = mssql_db.execute_query("""
        SELECT 
            s.[SampleID], s.[Description], s.[Barcode], cs.[Amount],
            CONCAT('SMP-', s.[SampleID]) as SampleIDFormatted
        FROM [containersample] cs
        JOIN [samplestorage] ss ON cs.[SampleStorageID] = ss.[StorageID]
        JOIN [sample] s ON ss.[SampleID] = s.[SampleID]
        WHERE cs.[ContainerID] = ?
        ORDER BY s.[Description]
    """, (container_id,), fetch_all=True)
    
    samples = []
    if samples_result:
        for row in samples_result:
            samples.append({
                'SampleID': row[0],
                'Description': row[1],
                'Barcode': row[2],
                'Amount': row[3],
                'SampleIDFormatted': row[4]
            })
    
    return jsonify({
        'success': True,
        'type': 'container',
        'barcode': barcode,
        'container': container,
        'samples': samples
    })

def lookup_sample_barcode(barcode):
    """Lookup sample by BC- or SMP- barcode - MSSQL version"""
    if barcode.startswith('SMP-'):
        # SMP- format - lookup by Sample ID
        try:
            sample_id = int(barcode.replace('SMP-', ''))
            query_condition = "s.[SampleID] = ?"
            query_param = sample_id
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'Invalid SMP barcode format: {barcode}'
            }), 400
    else:
        # BC- format - lookup by barcode field
        query_condition = "s.[Barcode] = ?"
        query_param = barcode
    
    # Get sample information
    sample_result = mssql_db.execute_query(f"""
        SELECT 
            s.[SampleID], s.[Barcode], s.[Description], s.[PartNumber], s.[Status], 
            s.[Amount], s.[ExpireDate], u.[UnitName],
            CONCAT('SMP-', s.[SampleID]) as SampleIDFormatted
        FROM [sample] s
        LEFT JOIN [unit] u ON s.[UnitID] = u.[UnitID]
        WHERE {query_condition}
    """, (query_param,), fetch_one=True)
    
    if not sample_result:
        return jsonify({
            'success': False,
            'error': f'Sample not found: {barcode}'
        }), 404
    
    sample = {
        'SampleID': sample_result[0],
        'Barcode': sample_result[1],
        'Description': sample_result[2],
        'PartNumber': sample_result[3],
        'Status': sample_result[4],
        'Amount': sample_result[5],
        'ExpireDate': sample_result[6].strftime('%Y-%m-%d') if sample_result[6] else None,
        'UnitName': sample_result[7],
        'SampleIDFormatted': sample_result[8]
    }
    
    # Get storage information
    storage_result = mssql_db.execute_query("""
        SELECT TOP 1
            ss.[AmountRemaining], sl.[LocationName],
            c.[Description] as ContainerDescription
        FROM [samplestorage] ss
        LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
        LEFT JOIN [containersample] cs ON ss.[StorageID] = cs.[SampleStorageID]
        LEFT JOIN [container] c ON cs.[ContainerID] = c.[ContainerID]
        WHERE ss.[SampleID] = ?
        ORDER BY ss.[StorageID] DESC
    """, (sample['SampleID'],), fetch_one=True)
    
    storage = {}
    if storage_result:
        storage = {
            'AmountRemaining': storage_result[0],
            'LocationName': storage_result[1],
            'ContainerDescription': storage_result[2]
        }
    
    # Get recent history
    history_result = mssql_db.execute_query("""
        SELECT TOP 5 [ActionType], [Timestamp], [Notes]
        FROM [history]
        WHERE [SampleID] = ?
        ORDER BY [Timestamp] DESC
    """, (sample['SampleID'],), fetch_all=True)
    
    history = []
    if history_result:
        for row in history_result:
            history.append({
                'ActionType': row[0],
                'Timestamp': row[1].isoformat(),
                'Notes': row[2]
            })
    
    return jsonify({
        'success': True,
        'type': 'sample',
        'barcode': barcode,
        'sample': sample,
        'storage': storage,
        'history': history
    })