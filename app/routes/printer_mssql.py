from flask import Blueprint, request, jsonify, current_app
from app.utils.mssql_db import mssql_db
from datetime import datetime
import os

printer_mssql_bp = Blueprint('printer_mssql', __name__)

print("DEBUG: MSSQL Printer blueprint created successfully")

@printer_mssql_bp.route('/api/print/sample/<int:sample_id>', methods=['POST'])
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
        current_app.logger.error(f"Sample label print endpoint error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Sample label print error: {str(e)}'
        }), 500

@printer_mssql_bp.route('/api/print/container/<int:container_id>', methods=['POST'])
def print_container_label_endpoint(container_id):
    """
    MSSQL version - Endpoint to print container label for a specific container.
    """
    try:
        current_app.logger.info(f"=== CONTAINER ENDPOINT DEBUG: Received request to print container {container_id} ===")
        data = request.get_json() or {}
        auto_print = data.get('auto_print', True)
        
        # Get container details
        container_result = mssql_db.execute_query("""
            SELECT 
                c.[ContainerID],
                c.[Description],
                ct.[TypeName],
                sl.[LocationName],
                c.[ContainerCapacity]
            FROM [container] c
            LEFT JOIN [containertype] ct ON c.[ContainerTypeID] = ct.[ContainerTypeID]
            LEFT JOIN [storagelocation] sl ON c.[LocationID] = sl.[LocationID]
            WHERE c.[ContainerID] = ?
        """, (container_id,), fetch_one=True)
        
        if not container_result:
            return jsonify({
                'status': 'error',
                'message': f'Container {container_id} not found'
            }), 404
        
        # Get all samples in the container with task information
        samples_result = mssql_db.execute_query("""
            SELECT 
                s.[SampleID],
                s.[Description],
                s.[PartNumber],
                s.[Barcode],
                cs.[Amount],
                t.[TaskName]
            FROM [containersample] cs
            JOIN [samplestorage] ss ON cs.[SampleStorageID] = ss.[StorageID]
            JOIN [sample] s ON ss.[SampleID] = s.[SampleID]
            LEFT JOIN [task] t ON s.[TaskID] = t.[TaskID]
            WHERE cs.[ContainerID] = ?
            ORDER BY s.[SampleID]
        """, (container_id,), fetch_all=True)
        
        # Prepare container data for label
        container_data = {
            'ContainerID': container_result[0],
            'Description': container_result[1] or '',
            'Type': container_result[2] or 'Standard',
            'LocationName': container_result[3] or '',
            'ContainerCapacity': container_result[4] or 0,
            'samples': []
        }
        
        # Get task information from first sample (if any)
        first_sample_task = 'None'
        if samples_result and len(samples_result) > 0:
            first_sample_task = samples_result[0][5] or 'None'  # TaskName is index 5
        container_data['TaskName'] = first_sample_task
        
        # Add sample information with proper barcode generation
        for sample_row in samples_result:
            sample_id = sample_row[0]
            existing_barcode = sample_row[3]
            
            # Generate proper barcode if none exists
            if not existing_barcode or existing_barcode.strip() == '':
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                generated_barcode = f"SMP{sample_id}{timestamp[-6:]}"
                
                # Update the database with the new barcode
                try:
                    mssql_db.execute_query("""
                        UPDATE [sample] SET [Barcode] = ? WHERE [SampleID] = ?
                    """, (generated_barcode, sample_id))
                    current_app.logger.info(f"Generated and saved barcode {generated_barcode} for sample {sample_id}")
                    barcode_to_use = generated_barcode
                except Exception as e:
                    current_app.logger.error(f"Failed to update barcode for sample {sample_id}: {str(e)}")
                    barcode_to_use = f'SMP{sample_id}'
            else:
                barcode_to_use = existing_barcode
            
            sample_data = {
                'SampleID': sample_id,
                'Description': sample_row[1] or '',
                'PartNumber': sample_row[2] or '',
                'Barcode': barcode_to_use,
                'Amount': sample_row[4] or 1
            }
            container_data['samples'].append(sample_data)
        
        # Get or generate container barcode
        existing_barcode_result = mssql_db.execute_query(
            "SELECT [Barcode] FROM [container] WHERE [ContainerID] = ?", 
            (container_id,), 
            fetch_one=True
        )
        
        if existing_barcode_result and existing_barcode_result[0]:
            container_barcode = existing_barcode_result[0]
            current_app.logger.info(f"Using existing container barcode: {container_barcode}")
        else:
            # Generate new barcode and save it
            container_barcode = f"CNT-{container_id}"
            
            try:
                mssql_db.execute_query(
                    "UPDATE [container] SET [Barcode] = ? WHERE [ContainerID] = ?", 
                    (container_barcode, container_id)
                )
                current_app.logger.info(f"Generated and saved new container barcode: {container_barcode}")
            except Exception as e:
                current_app.logger.error(f"Failed to save container barcode: {e}")
        
        container_data['Barcode'] = container_barcode
        
        # Use the container printing function from printer.py but with MSSQL data
        from app.routes.printer import format_label_enhanced, print_to_device, get_printer_config, log_print_action
        
        if auto_print:
            # Get printer configuration
            printer_config = get_printer_config('container')
            if not printer_config:
                printer_config = get_printer_config('sample')
            
            if not printer_config:
                printer_config = {
                    'printer_type': 'brother_ql810w',
                    'format': 'standard',
                    'use_zpl': False,
                    'description': 'Brother QL-810W (default configuration)'
                }
            
            # Format and print label
            label_content = format_label_enhanced('container', container_data, printer_config)
            result = print_to_device(label_content, printer_config)
            
            # Log print action (skip MySQL logging since we're using MSSQL)
            # if result['status'] == 'success':
            #     log_print_action('container', container_data, printer_config)
            
            return jsonify(result)
        else:
            return jsonify({
                'status': 'success',
                'message': 'Container label data prepared',
                'container_data': container_data
            })
        
    except Exception as e:
        current_app.logger.error(f"Container label print endpoint error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Container label print error: {str(e)}'
        }), 500

@printer_mssql_bp.route('/api/print/test-sample', methods=['POST'])
def print_test_sample_label():
    """
    MSSQL version - Endpoint to print test sample labels for individual test specimens.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        # Import functions from printer.py
        from app.routes.printer import generate_barcode, get_printer_config, format_label_enhanced, print_to_device
        
        # Generate test barcode if not provided
        if 'TestBarcode' not in data:
            data['TestBarcode'] = generate_barcode('test_sample', data)
        
        # Get printer configuration
        printer_config = get_printer_config('test_sample')
        if not printer_config:
            return jsonify({
                'status': 'error',
                'message': 'No printer configured for test sample labels. Set BROTHER_TEST_PRINTER_PATH environment variable.'
            }), 500
        
        # Format and print label
        label_content = format_label_enhanced('test_sample', data, printer_config)
        result = print_to_device(label_content, printer_config)
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Test sample label print error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Test sample label print error: {str(e)}'
        }), 500

@printer_mssql_bp.route('/api/print/label', methods=['POST'])
def print_label():
    """
    MSSQL version - Enhanced endpoint for printing labels with multiple printer support.
    """
    try:
        data = request.get_json()
        current_app.logger.info(f"Print request received: {data}")
        
        if not data or 'label_type' not in data or 'data' not in data:
            return jsonify({
                'status': 'error', 
                'message': 'Invalid request. Missing label_type or data'
            }), 400
        
        label_type = data['label_type']
        label_data = data['data']
        printer_id = data.get('printer_id')  # Optional specific printer
        
        # Import functions from printer.py
        from app.routes.printer import get_printer_config, generate_barcode, format_label_enhanced, print_to_device
        
        # Get printer configuration for this label type
        printer_config = get_printer_config(label_type, printer_id)
        if not printer_config:
            return jsonify({
                'status': 'error', 
                'message': f'No printer configured for label type: {label_type}'
            }), 500
        
        # Generate barcode if not provided
        if 'Barcode' not in label_data or not label_data['Barcode']:
            label_data['Barcode'] = generate_barcode(label_type, label_data)
        
        # Format label content based on type and printer
        label_content = format_label_enhanced(label_type, label_data, printer_config)
        
        # Print the label
        result = print_to_device(label_content, printer_config)
        
        return jsonify(result)
                
    except Exception as e:
        current_app.logger.error(f"Print request error: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Print request processing error: {str(e)}'
        }), 500

@printer_mssql_bp.route('/api/print/test', methods=['POST', 'GET'])
def test_print():
    """MSSQL version - Test printing endpoint"""
    try:
        from app.routes.printer import generate_barcode, get_printer_config, format_label_enhanced, print_to_device
        
        label_type = 'sample'
        
        test_data = {
            'label_type': label_type,
            'data': {
                'message': 'This is a test label',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'SampleIDFormatted': 'TEST-001',
                'Description': 'Test Sample for Printer (MSSQL)',
                'PartNumber': 'TEST-PART-001',
                'Type': 'Test',
                'Amount': '1',
                'UnitName': 'pcs'
            }
        }
        
        # Get printer configuration
        printer_config = get_printer_config(label_type)
        if not printer_config:
            printer_config = {
                'description': 'Brother QL-810W Test Configuration (MSSQL)',
                'app_path': 'enabled',
                'printer_type': 'brother_ql810w',
                'format': 'compact'
            }
        
        # Generate test barcode
        test_data['data']['Barcode'] = generate_barcode('test', test_data['data'])
        
        # Format and print
        label_content = format_label_enhanced('test', test_data['data'], printer_config)
        result = print_to_device(label_content, printer_config)
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Test print error: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Test print error: {str(e)}'
        }), 500

@printer_mssql_bp.route('/api/print/simulate', methods=['POST', 'GET'])
def simulate_print():
    """MSSQL version - Simulate printing without actually sending to printer"""
    try:
        from app.routes.printer import generate_barcode, get_printer_config, format_label_enhanced
        
        label_type = 'sample'
        
        test_data = {
            'label_type': label_type,
            'data': {
                'message': 'This is a SIMULATED test label (MSSQL)',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'SampleIDFormatted': 'TEST-001',
                'Description': 'Test Sample for Printer (MSSQL SIMULATION)',
                'PartNumber': 'TEST-PART-001',
                'Type': 'Test',
                'Amount': '1',
                'UnitName': 'pcs'
            }
        }
        
        # Get printer configuration
        printer_config = get_printer_config(label_type)
        if not printer_config:
            printer_config = {
                'description': 'Brother QL-810W Test Configuration (MSSQL SIMULATION)',
                'app_path': 'enabled',
                'printer_type': 'brother_ql810w',
                'format': 'compact'
            }
        
        # Generate test barcode
        test_data['data']['Barcode'] = generate_barcode('test', test_data['data'])
        
        # Format label content but don't print
        label_content = format_label_enhanced('test', test_data['data'], printer_config)
        
        # Simulate successful printing
        return jsonify({
            'status': 'success',
            'message': 'MSSQL SIMULATED: Label would be printed successfully',
            'label_content': label_content,
            'printer_config': printer_config['description']
        })
        
    except Exception as e:
        current_app.logger.error(f"Test simulate error: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Test simulate error: {str(e)}'
        }), 500

@printer_mssql_bp.route('/api/print/config', methods=['GET'])
def get_printer_config_info():
    """
    MSSQL version - Get information about configured printers for different label types.
    """
    try:
        from app.routes.printer import PRINTER_CONFIG
        
        config_info = {}
        
        for label_type, config in PRINTER_CONFIG.items():
            app_path = os.getenv(config['app_path_env'], '')
            fallback_path = os.getenv('BROTHER_APP_PATH', '')
            
            config_info[label_type] = {
                'description': config['description'],
                'printer_type': config['printer_type'],
                'format': config['format'],
                'configured': bool(app_path or fallback_path),
                'env_var': config['app_path_env'],
                'app_path': app_path or fallback_path
            }
        
        return jsonify({
            'status': 'success',
            'printers': config_info
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error', 
            'message': str(e)
        }), 500

@printer_mssql_bp.route('/api/print/storage-info/<int:sample_id>', methods=['GET'])
def get_sample_storage_info(sample_id):
    """
    MSSQL version - Get information about how a sample is stored and recommend appropriate label printing strategy.
    """
    try:
        # Check if sample is in a container
        result = mssql_db.execute_query("""
            SELECT 
                s.[SampleID],
                s.[Description],
                c.[ContainerID],
                c.[Description] as ContainerDescription,
                ct.[TypeName] as ContainerType,
                sl.[LocationName],
                COUNT(cs2.[SampleStorageID]) as SamplesInContainer
            FROM [sample] s
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [containersample] cs ON ss.[StorageID] = cs.[SampleStorageID]
            LEFT JOIN [container] c ON cs.[ContainerID] = c.[ContainerID]
            LEFT JOIN [containertype] ct ON c.[ContainerTypeID] = ct.[ContainerTypeID]
            LEFT JOIN [storagelocation] sl ON c.[LocationID] = sl.[LocationID]
            LEFT JOIN [containersample] cs2 ON c.[ContainerID] = cs2.[ContainerID]
            WHERE s.[SampleID] = ?
            GROUP BY s.[SampleID], s.[Description], c.[ContainerID], c.[Description], ct.[TypeName], sl.[LocationName]
        """, (sample_id,), fetch_one=True)
        
        if not result:
            return jsonify({
                'status': 'error',
                'message': f'Sample {sample_id} not found'
            }), 404
        
        sample_id = result[0]
        sample_description = result[1]
        container_id = result[2]
        container_description = result[3]
        container_type = result[4]
        location_name = result[5]
        samples_in_container = result[6] if result[6] else 0
        
        storage_info = {
            'sample_id': sample_id,
            'sample_description': sample_description,
            'storage_type': 'container' if container_id else 'direct',
            'location_name': location_name
        }
        
        if container_id:
            # Sample is in container
            storage_info.update({
                'container_id': container_id,
                'container_description': container_description,
                'container_type': container_type,
                'samples_in_container': samples_in_container,
                'recommended_label': 'container',
                'label_strategy': 'Print container label with all sample barcodes'
            })
        else:
            # Direct storage
            storage_info.update({
                'recommended_label': 'sample',
                'label_strategy': 'Print individual sample label'
            })
        
        return jsonify({
            'status': 'success',
            'storage_info': storage_info
        })
        
    except Exception as e:
        current_app.logger.error(f"Storage info error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Storage info error: {str(e)}'
        }), 500