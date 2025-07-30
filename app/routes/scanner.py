from flask import Blueprint, request, jsonify, render_template, current_app
from app.models.sample import Sample
from app.utils.auth import get_current_user
import json
import logging
from datetime import datetime

scanner_bp = Blueprint('scanner', __name__)
mysql = None

def init_scanner(blueprint, mysql_client):
    global mysql
    mysql = mysql_client

def lookup_sample_by_barcode(barcode):
    """
    Enhanced database lookup for samples by barcode.
    Supports multiple barcode types: sample barcodes, serial numbers, container barcodes.
    """
    cursor = mysql.connection.cursor()
    
    try:
        # First try: EXACT sample barcode lookup (strict matching)
        cursor.execute("""
            SELECT s.SampleID, s.Barcode, s.PartNumber, s.Description, s.Status,
                   s.Amount, s.UnitID, s.OwnerID, s.ReceptionID, 
                   r.ReceivedDate, r.TrackingNumber, sp.SupplierName,
                   u.UnitName, sl.LocationName, c.ContainerID, c.Description as ContainerDescription,
                   receiver.Name as ReceivedBy
            FROM sample s
            LEFT JOIN reception r ON s.ReceptionID = r.ReceptionID
            LEFT JOIN supplier sp ON r.SupplierID = sp.SupplierID
            LEFT JOIN unit u ON s.UnitID = u.UnitID
            LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
            LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
            LEFT JOIN containersample cs ON ss.StorageID = cs.SampleStorageID
            LEFT JOIN container c ON cs.ContainerID = c.ContainerID
            LEFT JOIN user receiver ON r.UserID = receiver.UserID
            WHERE s.Barcode = %s AND s.Barcode IS NOT NULL AND s.Barcode != ''
        """, (barcode,))
        
        result = cursor.fetchone()
        if result:
            # For barcode lookup, we don't have SerialNumber in result, so adjust the mapping
            sample_result = {
                'type': 'sample',
                'lookup_type': 'barcode',
                'SampleID': result[0],
                'SampleIDFormatted': f"SMP-{result[0]}",
                'Barcode': result[1],
                'PartNumber': result[2],
                'Description': result[3],
                'Status': result[4],
                'Amount': result[5],
                'SerialNumber': None,  # Not included in barcode lookup
                'ReceivedDate': result[9].strftime('%Y-%m-%d') if result[9] else None,
                'TrackingNumber': result[10],
                'SupplierName': result[11],
                'UnitName': result[12] or 'pcs',
                'LocationName': result[13] or 'Unknown',
                'ContainerID': result[14],
                'ContainerDescription': result[15],
                'ReceivedBy': result[16]
            }
            return sample_result
        
        # Second try: EXACT serial number lookup (strict matching)
        cursor.execute("""
            SELECT s.SampleID, s.Barcode, s.PartNumber, s.Description, s.Status,
                   s.Amount, s.UnitID, s.OwnerID, s.ReceptionID, sn.SerialNumber,
                   r.ReceivedDate, r.TrackingNumber, sp.SupplierName,
                   u.UnitName, sl.LocationName, c.ContainerID, c.Description as ContainerDescription,
                   receiver.Name as ReceivedBy
            FROM sample s
            LEFT JOIN sampleserialnumber sn ON s.SampleID = sn.SampleID AND sn.IsActive = 1
            LEFT JOIN reception r ON s.ReceptionID = r.ReceptionID
            LEFT JOIN supplier sp ON r.SupplierID = sp.SupplierID
            LEFT JOIN unit u ON s.UnitID = u.UnitID
            LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
            LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
            LEFT JOIN containersample cs ON ss.StorageID = cs.SampleStorageID
            LEFT JOIN container c ON cs.ContainerID = c.ContainerID
            LEFT JOIN user receiver ON r.UserID = receiver.UserID
            WHERE sn.SerialNumber = %s AND sn.SerialNumber IS NOT NULL AND sn.SerialNumber != ''
        """, (barcode,))
        
        result = cursor.fetchone()
        if result:
            return format_sample_result(result, 'serial_number')
        
        # Third try: EXACT container barcode lookup (strict matching)
        cursor.execute("""
            SELECT c.ContainerID, c.Description, c.Barcode, c.ContainerTypeID,
                   sl.LocationName, COUNT(ss.SampleID) as SampleCount,
                   ct.TypeName as ContainerType
            FROM container c
            LEFT JOIN containersample cs ON c.ContainerID = cs.ContainerID
            LEFT JOIN samplestorage ss ON cs.SampleStorageID = ss.StorageID
            LEFT JOIN storagelocation sl ON c.LocationID = sl.LocationID
            LEFT JOIN containertype ct ON c.ContainerTypeID = ct.ContainerTypeID
            WHERE (c.Barcode = %s AND c.Barcode IS NOT NULL AND c.Barcode != '') 
               OR (%s = CONCAT('CNT-', c.ContainerID))
            GROUP BY c.ContainerID
        """, (barcode, barcode))
        
        result = cursor.fetchone()
        if result:
            return format_container_result(result, barcode)
        
        # Fourth try: Test sample identifier lookup (T1234.5_1 format)
        if ('_' in barcode and barcode.startswith('T')):
            cursor.execute("""
                SELECT tsu.UsageID, tsu.SampleIdentifier, tsu.TestID, tsu.SampleID,
                       t.TestNo, t.TestName, s.Description, s.PartNumber, s.Status,
                       sl.LocationName
                FROM testsampleusage tsu
                JOIN test t ON tsu.TestID = t.TestID
                JOIN sample s ON tsu.SampleID = s.SampleID
                LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
                LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
                WHERE tsu.SampleIdentifier = %s
            """, (barcode,))
            
            result = cursor.fetchone()
            if result:
                return format_test_sample_result(result, barcode)
        
        return None
        
    finally:
        cursor.close()

def format_sample_result(result, lookup_type):
    """
    Format sample database result into response format.
    """
    return {
        'type': 'sample',
        'lookup_type': lookup_type,
        'SampleID': result[0],
        'SampleIDFormatted': f"SMP-{result[0]}",
        'Barcode': result[1],
        'PartNumber': result[2],
        'Description': result[3],
        'Status': result[4],
        'Amount': result[5],
        'SerialNumber': result[9] if len(result) > 9 and result[9] else None,  # SerialNumber for serial lookup
        'ReceivedDate': result[10].strftime('%Y-%m-%d') if len(result) > 10 and result[10] else None,
        'TrackingNumber': result[11] if len(result) > 11 else None,
        'SupplierName': result[12] if len(result) > 12 else None,
        'UnitName': result[13] if len(result) > 13 else 'pcs',
        'LocationName': result[14] if len(result) > 14 else 'Unknown',
        'ContainerID': result[15] if len(result) > 15 else None,
        'ContainerDescription': result[16] if len(result) > 16 else None,
        'ReceivedBy': result[17] if len(result) > 17 else None
    }

def format_container_result(result, barcode):
    """
    Format container database result into response format.
    """
    return {
        'type': 'container',
        'lookup_type': 'container_barcode',
        'ContainerID': result[0],
        'ContainerIDFormatted': f"CNT-{result[0]}",
        'Description': result[1],
        'Barcode': result[2],
        'LocationName': result[4],
        'SampleCount': result[5],
        'ContainerType': result[6],
        'scanned_barcode': barcode
    }

def format_test_sample_result(result, barcode):
    """
    Format test sample database result into response format.
    """
    return {
        'type': 'test_sample',
        'lookup_type': 'test_identifier',
        'TestSampleID': result[0],
        'GeneratedIdentifier': result[1],
        'TestID': result[2],
        'SampleID': result[3],
        'TestNo': result[4],
        'TestName': result[5],
        'SampleDescription': result[6],
        'PartNumber': result[7],
        'Status': result[8],
        'LocationName': result[9],
        'scanned_barcode': barcode
    }

def log_scan_action(barcode, result, user_id=None):
    """
    Log scan actions to database for audit trail.
    """
    try:
        if user_id is None:
            current_user = get_current_user(mysql)
            user_id = current_user.get('UserID', 1)
        
        cursor = mysql.connection.cursor()
        
        action_type = "Barcode scanned"
        if result:
            if result['type'] == 'sample':
                notes = f"Scanned sample barcode: {barcode} (Sample ID: {result['SampleID']})"
                sample_id = result['SampleID']
                container_id = result.get('ContainerID')
            elif result['type'] == 'container':
                notes = f"Scanned container barcode: {barcode} (Container ID: {result['ContainerID']})"
                sample_id = None
                container_id = result['ContainerID']
            elif result['type'] == 'test_sample':
                notes = f"Scanned test sample: {barcode} (Test: {result['TestNo']})"
                sample_id = result['SampleID']
                container_id = None
            else:
                notes = f"Scanned barcode: {barcode}"
                sample_id = None
                container_id = None
        else:
            notes = f"Scanned unknown barcode: {barcode}"
            sample_id = None
            container_id = None
        
        cursor.execute("""
            INSERT INTO history (SampleID, ContainerID, ActionType, Notes, UserID, Timestamp)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (sample_id, container_id, action_type, notes, user_id, datetime.now()))
        
        mysql.connection.commit()
        cursor.close()
        
    except Exception as e:
        current_app.logger.error(f"Failed to log scan action: {str(e)}")

@scanner_bp.route('/api/scanner/data', methods=['POST'])
def receive_scan_data():
    """
    Enhanced endpoint for receiving scan data from Zebra DataWedge.
    Supports multiple barcode types: sample barcodes, serial numbers, container barcodes, test identifiers.
    """
    try:
        data = request.get_json()
        current_app.logger.info(f"Scan data received: {data}")
        
        if not data or 'barcode' not in data:
            return jsonify({
                'status': 'error', 
                'message': 'No valid barcode received'
            }), 400
        
        barcode = data['barcode'].strip()
        
        if not barcode:
            return jsonify({
                'status': 'error',
                'message': 'Empty barcode received'
            }), 400
        
        # Enhanced database lookup
        result = lookup_sample_by_barcode(barcode)
        
        if not result:
            # Log the unsuccessful scan attempt
            log_scan_action(barcode, None)
            
            return jsonify({
                'status': 'not_found',
                'message': f'Barcode not found: {barcode}',
                'barcode': barcode
            }), 404
        
        # Log successful scan
        log_scan_action(barcode, result)
        
        return jsonify({
            'status': 'success',
            'message': f'{result["type"].title()} found by {result["lookup_type"]}',
            'result_type': result['type'],
            'lookup_type': result['lookup_type'],
            'sample' if result['type'] == 'sample' else result['type']: result,
            'barcode': barcode
        })
        
    except Exception as e:
        current_app.logger.error(f"Scanner data processing error: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Scanner data processing error: {str(e)}'
        }), 500

@scanner_bp.route('/scanner', methods=['GET'])
def scanner_page():
    """
    Viser scanner-administrationsside med mulighed for at teste scanning og udskrivning.
    """
    return render_template('sections/scanner.html')

@scanner_bp.route('/debug-scanner', methods=['GET'])
def debug_scanner_page():
    """
    Debug page for testing scanner functionality
    """
    from flask import current_app
    import os
    debug_file_path = os.path.join(current_app.root_path, '..', 'debug_scanner_complete.html')
    try:
        with open(debug_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return "<h1>Debug file not found</h1><p>debug_scanner_complete.html not found</p>", 404

@scanner_bp.route('/api/scanner/test', methods=['POST'])
def test_scanner():
    """
    Test endpoint for simulating scanner requests from web interface.
    Uses the same enhanced lookup as the main scanner endpoint.
    """
    try:
        data = request.get_json()
        if not data or 'barcode' not in data:
            return jsonify({
                'status': 'error', 
                'message': 'No valid barcode provided'
            }), 400
        
        # Use the same enhanced scanning logic
        return receive_scan_data()
    
    except Exception as e:
        current_app.logger.error(f"Scanner test error: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Scanner test error: {str(e)}'
        }), 500

@scanner_bp.route('/api/scanner/serial-register', methods=['POST'])
def register_serial_number():
    """
    New endpoint for registering/updating serial numbers for unique samples.
    Used when scanning serial numbers that need to be associated with samples.
    """
    try:
        data = request.get_json()
        
        if not data or 'serial_number' not in data or 'sample_id' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields: serial_number and sample_id'
            }), 400
        
        serial_number = data['serial_number'].strip()
        sample_id = data['sample_id']
        
        cursor = mysql.connection.cursor()
        
        # Check if sample exists and is unique
        cursor.execute("""
            SELECT SampleID, IsUnique, SerialNumber, Description
            FROM sample 
            WHERE SampleID = %s
        """, (sample_id,))
        
        sample = cursor.fetchone()
        if not sample:
            cursor.close()
            return jsonify({
                'status': 'error',
                'message': f'Sample ID {sample_id} not found'
            }), 404
        
        if not sample[1]:  # IsUnique field
            cursor.close()
            return jsonify({
                'status': 'error',
                'message': 'Sample is not marked as unique - serial numbers only apply to unique samples'
            }), 400
        
        # Check if serial number is already used by another sample
        cursor.execute("""
            SELECT SampleID, Description 
            FROM sample 
            WHERE SerialNumber = %s AND SampleID != %s
        """, (serial_number, sample_id))
        
        existing = cursor.fetchone()
        if existing:
            cursor.close()
            return jsonify({
                'status': 'error',
                'message': f'Serial number {serial_number} already used by sample {existing[0]}: {existing[1]}'
            }), 409
        
        # Update the sample with the serial number
        cursor.execute("""
            UPDATE sample 
            SET SerialNumber = %s
            WHERE SampleID = %s
        """, (serial_number, sample_id))
        
        # Log the action
        cursor.execute("""
            INSERT INTO history (SampleID, ActionType, Notes, UserID, Timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            sample_id,
            'Serial number registered',
            f'Serial number {serial_number} registered for unique sample',
            get_current_user(mysql).get('UserID', 1),  # Current user
            datetime.now()
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        # Get sample data for print confirmation
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT s.SampleID, s.Description, s.Barcode, s.PartNumber
            FROM sample s 
            WHERE s.SampleID = %s
        """, (sample_id,))
        sample_data = cursor.fetchone()
        cursor.close()
        
        sample_info = {
            'SampleID': sample_data[0],
            'SampleIDFormatted': f'SMP-{sample_data[0]}',
            'Description': sample_data[1],
            'Barcode': sample_data[2],
            'PartNumber': sample_data[3] or ''
        }
        
        return jsonify({
            'status': 'success',
            'message': f'Serial number {serial_number} registered for sample {sample_id}',
            'sample_id': sample_id,
            'serial_number': serial_number,
            'sample_data': sample_info,
            'show_print_confirmation': True
        })
        
    except Exception as e:
        current_app.logger.error(f"Serial number registration error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Serial number registration error: {str(e)}'
        }), 500

@scanner_bp.route('/api/scanner/simulate', methods=['POST', 'GET'])
def simulate_scan():
    """Simulate scanning without actual barcode - for testing scanner integration."""
    try:
        # Get barcode from request or use default
        if request.method == 'POST' and request.is_json:
            data = request.get_json() or {}
            barcode = data.get('barcode', 'TEST123456')
        else:
            barcode = request.args.get('barcode', 'TEST123456')
        
        current_app.logger.info(f"SIMULATED scan data: {barcode}")
        
        # Simulate database lookup
        simulated_result = {
            'type': 'sample',
            'lookup_type': 'barcode',
            'SampleID': 123,
            'SampleIDFormatted': 'SMP-123',
            'Barcode': barcode,
            'PartNumber': 'PART-456',
            'Description': 'Simulated Test Sample',
            'Status': 'In Storage',
            'Amount': 5,
            'SerialNumber': None,
            'ReceivedDate': '2024-01-15',
            'TrackingNumber': 'TRK-789',
            'SupplierName': 'Test Supplier',
            'UnitName': 'pcs',
            'LocationName': 'Storage-A1',
            'ContainerID': None,
            'ContainerDescription': None,
            'ReceivedBy': 'Test User'
        }
        
        # Log simulated scan (but don't save to database)
        current_app.logger.info(f"SIMULATED scan result: {simulated_result}")
        
        return jsonify({
            'status': 'success',
            'message': f'SIMULATED: Sample found by barcode scan',
            'result_type': 'sample',
            'lookup_type': 'barcode',
            'sample': simulated_result,
            'barcode': barcode,
            'simulation': True
        })
        
    except Exception as e:
        current_app.logger.error(f"Scanner simulation error: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Scanner simulation error: {str(e)}'
        }), 500

@scanner_bp.route('/api/scanner/test-barcodes', methods=['GET'])
def get_test_barcodes():
    """Get some real barcodes from database for testing scanner."""
    try:
        cursor = mysql.connection.cursor()
        
        # Get some sample barcodes
        cursor.execute("""
            SELECT SampleID, Barcode, Description, PartNumber
            FROM sample 
            WHERE Barcode IS NOT NULL AND Barcode != '' 
            LIMIT 10
        """)
        samples = cursor.fetchall()
        
        # Get some container barcodes  
        cursor.execute("""
            SELECT ContainerID, Barcode, Description
            FROM container 
            WHERE Barcode IS NOT NULL AND Barcode != ''
            LIMIT 5
        """)
        containers = cursor.fetchall()
        
        cursor.close()
        
        test_barcodes = {
            'samples': [
                {
                    'barcode': row[1], 
                    'description': f"SMP-{row[0]}: {row[2]} ({row[3] or 'No Part#'})"
                } 
                for row in samples
            ],
            'containers': [
                {
                    'barcode': row[1], 
                    'description': f"CNT-{row[0]}: {row[2]}"
                } 
                for row in containers  
            ],
            'test_barcodes': [
                {'barcode': 'TEST123', 'description': 'Basic test barcode'},
                {'barcode': '123456789', 'description': 'Numeric test barcode'},
                {'barcode': 'ABC123DEF', 'description': 'Alphanumeric test'},
                {'barcode': 'SMP-001', 'description': 'Sample format test'}
            ]
        }
        
        return jsonify({
            'status': 'success',
            'message': 'Test barcodes retrieved',
            'barcodes': test_barcodes
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get test barcodes: {str(e)}'
        }), 500

@scanner_bp.route('/scanner-app')
def scanner_app():
    """Dedicated scanner app page for Zebra devices."""
    return render_template('scanner_app.html')

@scanner_bp.route('/scanner-only')
def scanner_only():
    """Scanner-only interface - no access to main LabSystem features."""
    return render_template('scanner_only.html')

@scanner_bp.route('/scanner-print-desktop')
def scanner_print_desktop():
    """Desktop scanner/print interface - shows last 5 scans with print functionality."""
    return render_template('scanner_print_desktop.html')

@scanner_bp.route('/api/scanner/webhook', methods=['POST'])
def scanner_webhook():
    """Webhook endpoint for external scanner apps."""
    try:
        # Handle different data formats from old apps
        content_type = request.headers.get('Content-Type', '')
        
        if 'application/json' in content_type:
            data = request.get_json()
            barcode = data.get('barcode') or data.get('data') or data.get('scan_data')
        else:
            # Handle form data or raw text
            data = request.form.to_dict() if request.form else {}
            barcode = (data.get('barcode') or 
                      data.get('data') or 
                      request.data.decode('utf-8').strip())
        
        if not barcode:
            return jsonify({
                'status': 'error',
                'message': 'No barcode data received'
            }), 400
        
        current_app.logger.info(f"Webhook scan received: {barcode}")
        
        # Use the same lookup logic as main scanner endpoint
        result = lookup_sample_by_barcode(barcode)
        
        if not result:
            log_scan_action(barcode, None)
            return jsonify({
                'status': 'not_found',
                'message': f'Barcode not found: {barcode}',
                'barcode': barcode
            }), 404
        
        # Log successful scan
        log_scan_action(barcode, result)
        
        return jsonify({
            'status': 'success',
            'message': f'{result["type"].title()} found by webhook',
            'result_type': result['type'],
            'lookup_type': result['lookup_type'],
            'data': result,
            'barcode': barcode
        })
        
    except Exception as e:
        current_app.logger.error(f"Webhook scanner error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Webhook scanner error: {str(e)}'
        }), 500