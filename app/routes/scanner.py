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
        # First try: Direct sample barcode lookup
        cursor.execute("""
            SELECT s.SampleID, s.Barcode, s.PartNumber, s.Description, s.Status,
                   s.Amount, s.UnitID, s.OwnerID, s.ReceptionID, s.SerialNumber,
                   r.ReceivedDate, r.TrackingNumber, sp.SupplierName,
                   u.UnitName, sl.LocationName, c.ContainerID, c.Description as ContainerDescription,
                   receiver.Name as ReceivedBy
            FROM Sample s
            LEFT JOIN Reception r ON s.ReceptionID = r.ReceptionID
            LEFT JOIN Supplier sp ON r.SupplierID = sp.SupplierID
            LEFT JOIN Unit u ON s.UnitID = u.UnitID
            LEFT JOIN SampleStorage ss ON s.SampleID = ss.SampleID
            LEFT JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
            LEFT JOIN Container c ON ss.ContainerID = c.ContainerID
            LEFT JOIN User receiver ON r.ReceivedBy = receiver.UserID
            WHERE s.Barcode = %s
        """, (barcode,))
        
        result = cursor.fetchone()
        if result:
            return format_sample_result(result, 'barcode')
        
        # Second try: Serial number lookup (for unique samples)
        cursor.execute("""
            SELECT s.SampleID, s.Barcode, s.PartNumber, s.Description, s.Status,
                   s.Amount, s.UnitID, s.OwnerID, s.ReceptionID, s.SerialNumber,
                   r.ReceivedDate, r.TrackingNumber, sp.SupplierName,
                   u.UnitName, sl.LocationName, c.ContainerID, c.Description as ContainerDescription,
                   receiver.Name as ReceivedBy
            FROM Sample s
            LEFT JOIN Reception r ON s.ReceptionID = r.ReceptionID
            LEFT JOIN Supplier sp ON r.SupplierID = sp.SupplierID
            LEFT JOIN Unit u ON s.UnitID = u.UnitID
            LEFT JOIN SampleStorage ss ON s.SampleID = ss.SampleID
            LEFT JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
            LEFT JOIN Container c ON ss.ContainerID = c.ContainerID
            LEFT JOIN User receiver ON r.ReceivedBy = receiver.UserID
            WHERE s.SerialNumber = %s
        """, (barcode,))
        
        result = cursor.fetchone()
        if result:
            return format_sample_result(result, 'serial_number')
        
        # Third try: Container barcode lookup (find samples in container)
        # Support both direct barcode match and new CNT format
        cursor.execute("""
            SELECT c.ContainerID, c.Description, c.Barcode, c.ContainerTypeID,
                   sl.LocationName, COUNT(ss.SampleID) as SampleCount,
                   ct.TypeName as ContainerType
            FROM container c
            LEFT JOIN containersample cs ON c.ContainerID = cs.ContainerID
            LEFT JOIN samplestorage ss ON cs.SampleStorageID = ss.StorageID
            LEFT JOIN storagelocation sl ON c.LocationID = sl.LocationID
            LEFT JOIN containertype ct ON c.ContainerTypeID = ct.ContainerTypeID
            WHERE c.Barcode = %s OR %s LIKE CONCAT('CNT', LPAD(c.ContainerID, 4, '0'), '%%')
            GROUP BY c.ContainerID
        """, (barcode, barcode))
        
        result = cursor.fetchone()
        if result:
            return format_container_result(result, barcode)
        
        # Fourth try: Test sample identifier lookup (T1234.5_1 format and new TST format)
        if ('_' in barcode and barcode.startswith('T')) or barcode.startswith('TST'):
            cursor.execute("""
                SELECT ts.TestSampleID, ts.GeneratedIdentifier, ts.TestID, ts.SampleID,
                       t.TestNo, t.TestName, s.Description, s.PartNumber, s.Status,
                       sl.LocationName
                FROM testsample ts
                JOIN test t ON ts.TestID = t.TestID
                JOIN sample s ON ts.SampleID = s.SampleID
                LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
                LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
                WHERE ts.GeneratedIdentifier = %s
            """, (barcode,))
            
            result = cursor.fetchone()
            if result:
                return format_test_sample_result(result, barcode)
            
            # Also try to match new TST format by extracting sample and test IDs
            if barcode.startswith('TST'):
                try:
                    # Extract sample ID and test ID from TST format (TST{sampleID}{testID}{timestamp})
                    # This is a simplified approach - in practice you might need more sophisticated parsing
                    barcode_data = barcode[3:]  # Remove 'TST' prefix
                    if len(barcode_data) >= 2:
                        # Try to find samples with test data
                        cursor.execute("""
                            SELECT ts.TestSampleID, ts.GeneratedIdentifier, ts.TestID, ts.SampleID,
                                   t.TestNo, t.TestName, s.Description, s.PartNumber, s.Status,
                                   sl.LocationName
                            FROM testsample ts
                            JOIN test t ON ts.TestID = t.TestID
                            JOIN sample s ON ts.SampleID = s.SampleID
                            LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
                            LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
                            WHERE CONCAT('TST', ts.SampleID, ts.TestID) LIKE %s
                        """, (barcode[:10] + '%',))  # Match first part of barcode
                        
                        result = cursor.fetchone()
                        if result:
                            return format_test_sample_result(result, barcode)
                except:
                    pass  # If parsing fails, continue to return None
        
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
        'SerialNumber': result[9],
        'ReceivedDate': result[10].strftime('%Y-%m-%d') if result[10] else None,
        'TrackingNumber': result[11],
        'SupplierName': result[12],
        'UnitName': result[13] or 'pcs',
        'LocationName': result[14] or 'Unknown',
        'ContainerID': result[15],
        'ContainerDescription': result[16],
        'ReceivedBy': result[17]
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
            INSERT INTO History (SampleID, ContainerID, ActionType, Notes, UserID, Timestamp)
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
            FROM Sample 
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
            FROM Sample 
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
            UPDATE Sample 
            SET SerialNumber = %s
            WHERE SampleID = %s
        """, (serial_number, sample_id))
        
        # Log the action
        cursor.execute("""
            INSERT INTO History (SampleID, ActionType, Notes, UserID, Timestamp)
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
            FROM Sample s 
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