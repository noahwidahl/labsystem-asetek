from flask import Blueprint, request, jsonify, render_template, current_app
import os
import subprocess
import json
import tempfile
import logging
from datetime import datetime
import uuid

printer_bp = Blueprint('printer', __name__)
mysql = None

def init_printer(blueprint, mysql_client):
    global mysql
    mysql = mysql_client

# Printer configuration for different label types
PRINTER_CONFIG = {
    'sample': {
        'printer_type': 'brother_ql810w',
        'app_path_env': 'BROTHER_SAMPLE_PRINTER_PATH',
        'default_path': '',
        'description': 'Brother QL-810W for Sample Labels',
        'format': 'compact'  # Smaller format for individual samples
    },
    'container': {
        'printer_type': 'brother_ql810w', 
        'app_path_env': 'BROTHER_CONTAINER_PRINTER_PATH',
        'default_path': '',
        'description': 'Brother QL-810W for Container/Package Labels',
        'format': 'large'  # Larger format for packages/containers
    },
    'package': {
        'printer_type': 'brother_ql810w', 
        'app_path_env': 'BROTHER_PACKAGE_PRINTER_PATH',
        'default_path': '',
        'description': 'Brother QL-810W for Package Labels', 
        'format': 'large'  # Larger format for packages
    },
    'location': {
        'printer_type': 'brother_ql810w',
        'app_path_env': 'BROTHER_LOCATION_PRINTER_PATH', 
        'default_path': '',
        'description': 'Brother QL-810W for Location Labels',
        'format': 'medium'  # Medium format for location labels
    }
}

def get_printer_config(label_type, printer_id=None):
    """
    Get printer configuration for a specific label type.
    Falls back to BROTHER_APP_PATH if specific printer not configured.
    """
    if label_type in PRINTER_CONFIG:
        config = PRINTER_CONFIG[label_type].copy()
        
        # Try to get specific printer path
        printer_path = os.getenv(config['app_path_env'], '')
        
        # Fall back to general BROTHER_APP_PATH if specific not set
        if not printer_path:
            printer_path = os.getenv('BROTHER_APP_PATH', '')
        
        if printer_path:
            config['app_path'] = printer_path
            return config
    
    return None

def generate_barcode(label_type, label_data):
    """
    Generate a unique barcode for the label if one isn't provided.
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    
    if label_type == 'sample':
        sample_id = label_data.get('SampleID', '')
        return f"SMP{sample_id}{timestamp[-6:]}"
    elif label_type in ['container', 'package']:
        container_id = label_data.get('ContainerID', '')
        return f"CNT{container_id}{timestamp[-6:]}"
    elif label_type == 'location':
        location_name = label_data.get('LocationName', '').replace('.', '')
        return f"LOC{location_name}{timestamp[-4:]}"
    else:
        return f"LAB{timestamp}"

def format_label_enhanced(label_type, data, printer_config):
    """
    Enhanced label formatting with improved layouts for different label types.
    """
    format_type = printer_config.get('format', 'standard')
    
    if label_type == 'sample':
        if format_type == 'compact':
            return f"""
╭─────────────────────────────╮
│ SAMPLE: {data.get('SampleIDFormatted', ''):<18} │
│ DESC: {(data.get('Description', ''))[:22]:<22} │
│ BARCODE: {data.get('Barcode', ''):<17} │ 
│ PART#: {data.get('PartNumber', ''):<19} │
│ AMT: {data.get('Amount', '')} {data.get('UnitName', ''):<15} │
╰─────────────────────────────╯
"""
        else:
            return f"""
SAMPLE LABEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sample ID: {data.get('SampleIDFormatted', '')}
Description: {data.get('Description', '')}
Barcode: {data.get('Barcode', '')}
Part Number: {data.get('PartNumber', '')}
Type: {data.get('Type', '')}
Amount: {data.get('Amount', '')} {data.get('UnitName', '')}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    elif label_type in ['container', 'package']:
        return f"""
╔═══════════════════════════════════╗
║          PACKAGE/CONTAINER        ║
╠═══════════════════════════════════╣
║ ID: {data.get('ContainerIDFormatted', data.get('PackageID', '')):<28} ║
║ Type: {data.get('Type', data.get('ContainerType', '')):<26} ║
║ Barcode: {data.get('Barcode', ''):<23} ║
║ Location: {data.get('LocationName', ''):<21} ║
║ Contents: {data.get('SampleCount', data.get('Contents', '')):<21} ║
║ Created: {datetime.now().strftime('%Y-%m-%d %H:%M'):<22} ║
╚═══════════════════════════════════╝
"""
    
    elif label_type == 'location':
        return f"""
┌─────────────────────────────┐
│       LOCATION LABEL        │
├─────────────────────────────┤
│ Location: {data.get('LocationName', ''):<16} │
│ Type: {data.get('Type', 'Storage'):<20} │
│ Barcode: {data.get('Barcode', ''):<16} │
│ Description: {(data.get('Description', ''))[:13]:<13} │
└─────────────────────────────┘
"""
    
    elif label_type == 'test':
        return f"""
TEST LABEL
──────────────────────────────
Message: {data.get('message', 'Test Print')}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Printer: {printer_config.get('description', 'Unknown')}
──────────────────────────────
"""
    
    else:
        # Generic format for unknown types
        return f"""
LABEL TYPE: {label_type.upper()}
──────────────────────────────
{json.dumps(data, indent=2)}
──────────────────────────────
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

def print_to_device(label_content, printer_config):
    """
    Send label content to the configured printer device.
    """
    app_path = printer_config.get('app_path')
    
    if not app_path:
        return {
            'status': 'error', 
            'message': f'Printer ikke konfigureret. Sæt {printer_config["app_path_env"]} miljøvariabel'
        }
    
    # Create temporary file with label content
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w', encoding='utf-8') as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(label_content)
    
    try:
        # Execute printer application
        process = subprocess.Popen([app_path, temp_file_path], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(timeout=30)
        
        if process.returncode != 0:
            error_message = stderr.decode('utf-8', errors='ignore')
            current_app.logger.error(f"Printer fejl: {error_message}")
            return {
                'status': 'error', 
                'message': f'Fejl ved udskrivning: {error_message}'
            }
        
        return {
            'status': 'success', 
            'message': f'Label udskrevet succesfuldt på {printer_config["description"]}'
        }
        
    except subprocess.TimeoutExpired:
        process.kill()
        return {
            'status': 'error', 
            'message': 'Timeout ved udskrivning af label'
        }
    except Exception as e:
        return {
            'status': 'error', 
            'message': f'Fejl ved kald af printer: {str(e)}'
        }
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except:
            pass

def log_print_action(label_type, label_data, printer_config):
    """
    Log successful print actions to database for audit trail.
    """
    try:
        if mysql and mysql.connection:
            cursor = mysql.connection.cursor()
            
            # Determine the relevant ID for the history log
            sample_id = label_data.get('SampleID')
            container_id = label_data.get('ContainerID')
            
            action_type = f"Label printed"
            notes = f"Printed {label_type} label on {printer_config['description']}"
            
            # Add barcode to notes if available
            if 'Barcode' in label_data:
                notes += f" (Barcode: {label_data['Barcode']})"
            
            cursor.execute("""
                INSERT INTO History (SampleID, ContainerID, ActionType, Notes, UserID, Timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                sample_id,
                container_id, 
                action_type,
                notes,
                1,  # Default user - should be replaced with actual user from session
                datetime.now()
            ))
            
            mysql.connection.commit()
            cursor.close()
            
    except Exception as e:
        current_app.logger.error(f"Failed to log print action: {str(e)}")

@printer_bp.route('/api/print/label', methods=['POST'])
def print_label():
    """
    Enhanced endpoint for printing labels with multiple printer support.
    Supports different printers for different label types (sample, container, package, location).
    Automatically generates barcodes if not provided.
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
        
        # Log successful print
        if result['status'] == 'success':
            log_print_action(label_type, label_data, printer_config)
        
        return jsonify(result)
                
    except Exception as e:
        current_app.logger.error(f"Print request error: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Print request processing error: {str(e)}'
        }), 500

@printer_bp.route('/api/print/test', methods=['POST'])
def test_print():
    """
    Test endpoint for printing a test label on the default printer.
    """
    try:
        # Get printer type from request or default to sample printer
        data = request.get_json() or {}
        label_type = data.get('label_type', 'sample')
        
        test_data = {
            'label_type': label_type,
            'data': {
                'message': 'This is a test label',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'SampleIDFormatted': 'TEST-001',
                'Description': 'Test Sample for Printer',
                'PartNumber': 'TEST-PART-001',
                'Type': 'Test',
                'Amount': '1',
                'UnitName': 'pcs'
            }
        }
        
        # Get printer configuration
        printer_config = get_printer_config(label_type)
        if not printer_config:
            return jsonify({
                'status': 'error', 
                'message': f'No printer configured for test. Check environment variables.'
            }), 500
        
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

@printer_bp.route('/api/print/config', methods=['GET'])
def get_printer_config_info():
    """
    Get information about configured printers for different label types.
    """
    try:
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

# Legacy function for backwards compatibility
def format_label(label_type, data):
    """
    Legacy format function for backwards compatibility.
    """
    config = {'format': 'standard'}
    return format_label_enhanced(label_type, data, config)