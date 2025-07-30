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
        'zebra_app_path_env': 'ZEBRA_SAMPLE_PRINTER_PATH',
        'default_path': '',
        'description': 'Brother QL-810W for Sample Labels (Zebra Scanner Compatible)',
        'format': 'compact',  # Smaller format for individual samples
        'use_zpl': True  # Use ZPL for Zebra scanner compatibility
    },
    'container': {
        'printer_type': 'brother_ql810w', 
        'app_path_env': 'BROTHER_CONTAINER_PRINTER_PATH',
        'zebra_app_path_env': 'ZEBRA_CONTAINER_PRINTER_PATH',
        'default_path': '',
        'description': 'Brother QL-810W for Container Labels (Zebra Scanner Compatible)',
        'format': 'large',  # Larger format for packages/containers
        'use_zpl': True  # Use ZPL for Zebra scanner compatibility
    },
    'package': {
        'printer_type': 'brother_ql810w', 
        'app_path_env': 'BROTHER_PACKAGE_PRINTER_PATH',
        'default_path': '',
        'description': 'Brother QL-810W for Package Labels', 
        'format': 'large'  # Larger format for packages
    },
    'test_sample': {
        'printer_type': 'brother_ql810w',
        'app_path_env': 'BROTHER_TEST_PRINTER_PATH',
        'default_path': '',
        'description': 'Brother QL-810W for Test Sample Labels',
        'format': 'compact'  # Compact format for test samples
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
    Supports both Brother and Zebra printers with automatic ZPL detection.
    """
    if label_type in PRINTER_CONFIG:
        config = PRINTER_CONFIG[label_type].copy()
        
        # Check for Zebra printer first (if ZPL is enabled)
        zebra_path = os.getenv(config.get('zebra_app_path_env', ''), '')
        use_zebra = os.getenv('USE_ZEBRA_PRINTERS', 'False').lower() == 'true'
        
        if zebra_path and use_zebra:
            config['app_path'] = zebra_path
            config['use_zpl'] = True
            config['printer_type'] = 'zebra'
            config['description'] = config['description'].replace('Brother QL-810W', 'Zebra ZPL Printer')
            return config
        
        # Fall back to Brother printer
        printer_path = os.getenv(config['app_path_env'], '')
        
        # Fall back to general BROTHER_APP_PATH if specific not set
        if not printer_path:
            printer_path = os.getenv('BROTHER_APP_PATH', '')
        
        if printer_path:
            config['app_path'] = printer_path
            config['use_zpl'] = False
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
        return f"CNT-{container_id}"
    elif label_type == 'test_sample':
        sample_id = label_data.get('SampleID', '')
        test_id = label_data.get('TestID', '')
        return f"TST{sample_id}{test_id}{timestamp[-4:]}"
    elif label_type == 'location':
        location_name = label_data.get('LocationName', '').replace('.', '')
        return f"LOC{location_name}{timestamp[-4:]}"
    else:
        return f"LAB{timestamp}"

def generate_zpl_barcode(barcode_data, barcode_type='128', height=60, width=3):
    """
    Generate ZPL (Zebra Programming Language) barcode command optimized for scanning.
    """
    if barcode_type == '128':
        # Code 128 - most reliable for alphanumeric data
        return f"^BY{width},3,{height}^BC,{height},Y,N,N^FD{barcode_data}^FS"
    elif barcode_type == 'QR':
        # QR Code - good for mobile scanners
        return f"^BQN,2,6,M,7^FD{barcode_data}^FS"
    elif barcode_type == '39':
        # Code 39 - widely compatible
        return f"^BY{width},3,{height}^B3,N,{height},Y,N^FD{barcode_data}^FS"
    else:
        # Default to Code 128
        return f"^BY{width},3,{height}^BC,{height},Y,N,N^FD{barcode_data}^FS"

def format_label_enhanced(label_type, data, printer_config):
    """
    Enhanced label formatting with improved layouts for different label types.
    Supports both text-based and ZPL (Zebra) formats.
    """
    format_type = printer_config.get('format', 'standard')
    use_zpl = printer_config.get('use_zpl', False)
    
    if label_type == 'sample':
        if use_zpl:
            # ZPL format for Zebra printers with dynamic height based on content
            barcode = data.get('Barcode', '')
            sample_id = data.get('SampleIDFormatted', '')
            description = data.get('Description', '')
            part_number = data.get('PartNumber', '')
            amount = data.get('Amount', '')
            unit_name = data.get('UnitName', '')
            location = data.get('LocationName', '')
            expire_date = data.get('ExpireDate', '')
            
            # Start building ZPL with header
            zpl_lines = [
                "^XA",
                "^LH0,0^FS",
                "^FO30,20^A0N,25,25^FDSAMPLE LABEL^FS",
                f"^FO30,60^A0N,22,22^FD{sample_id}^FS"
            ]
            
            current_y = 100
            
            # Add description (always present)
            if description:
                zpl_lines.append(f"^FO30,{current_y}^A0N,22,22^FDDesc: {description[:25]}^FS")
                current_y += 25
            
            # Add part number if present
            if part_number:
                zpl_lines.append(f"^FO30,{current_y}^A0N,22,22^FDPart: {part_number[:20]}^FS")
                current_y += 25
            
            # Add amount
            if amount:
                zpl_lines.append(f"^FO30,{current_y}^A0N,22,22^FDAmt: {amount} {unit_name}^FS")
                current_y += 25
            
            # Add location if present
            if location:
                zpl_lines.append(f"^FO30,{current_y}^A0N,22,22^FDLoc: {location[:20]}^FS")
                current_y += 25
            
            # Add expire date if present
            if expire_date:
                zpl_lines.append(f"^FO30,{current_y}^A0N,22,22^FDExp: {expire_date}^FS")
                current_y += 25
            
            # Add task information
            task_name = data.get('TaskName', 'None')
            zpl_lines.append(f"^FO30,{current_y}^A0N,22,22^FDTask: {task_name[:20]}^FS")
            current_y += 25
            
            # Add some space before barcode
            current_y += 15
            
            # Add barcode
            zpl_lines.append(f"^FO30,{current_y}{generate_zpl_barcode(barcode, '128', 80, 3)}")
            current_y += 95  # Barcode height + margin
            
            # Add barcode text
            zpl_lines.append(f"^FO30,{current_y}^A0N,18,18^FD{barcode}^FS")
            current_y += 25
            
            # Add timestamp
            zpl_lines.append(f"^FO30,{current_y}^A0N,16,16^FD{datetime.now().strftime('%d-%m-%Y %H:%M')}^FS")
            
            # Close ZPL
            zpl_lines.append("^XZ")
            
            return "\n".join(zpl_lines)
        elif format_type == 'compact':
            expire_date = data.get('ExpireDate', '')
            location_name = data.get('LocationName', '')
            task_name = data.get('TaskName', 'None')
            return f"""SAMPLE LABEL
============
ID: {data.get('SampleIDFormatted', '')}
Desc: {data.get('Description', '')}
Part: {data.get('PartNumber', '')}
Amt: {data.get('Amount', '')} {data.get('UnitName', '')}
Exp: {expire_date}
Loc: {location_name}
Task: {task_name}
Barcode: {data.get('Barcode', '')}
"""
        else:
            task_name = data.get('TaskName', 'None')
            return f"""
SAMPLE LABEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sample ID: {data.get('SampleIDFormatted', '')}
Description: {data.get('Description', '')}
Barcode: {data.get('Barcode', '')}
Part Number: {data.get('PartNumber', '')}
Type: {data.get('Type', '')}
Amount: {data.get('Amount', '')} {data.get('UnitName', '')}
Task: {task_name}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    elif label_type in ['container', 'package']:
        # Enhanced container label with multiple barcodes and sample information
        samples = data.get('samples', [])
        packing_date = data.get('PackingDate', datetime.now().strftime('%d-%m-%Y'))
        current_app.logger.info(f"=== FORMAT LABEL DEBUG: Container label requested with {len(samples)} samples ===")
        current_app.logger.info(f"=== FORMAT LABEL DEBUG: use_zpl = {printer_config.get('use_zpl', False)} ===")
        
        if use_zpl:
            # ZPL format for container labels with dynamic height based on content
            container_barcode = data.get('Barcode', f"CNT-{data.get('ContainerID', '')}")
            container_id = data.get('ContainerID', '')
            container_type = data.get('Type', data.get('ContainerType', ''))
            location = data.get('LocationName', '')
            description = data.get('Description', '')
            
            # Start building ZPL with header
            zpl_lines = [
                "^XA",
                "^LH0,0^FS",
                "^FO30,20^A0N,30,30^FDCONTAINER LABEL^FS",
                f"^FO30,60^A0N,22,22^FDCNT-{container_id:0>4}^FS"
            ]
            
            current_y = 110
            
            # Add container info
            if description:
                zpl_lines.append(f"^FO30,{current_y}^A0N,22,22^FDDesc: {description[:20]}^FS")
                current_y += 25
            
            if container_type:
                zpl_lines.append(f"^FO30,{current_y}^A0N,22,22^FDType: {container_type[:20]}^FS")
                current_y += 25
            
            # Add task information
            task_name = data.get('TaskName', 'None')
            zpl_lines.append(f"^FO30,{current_y}^A0N,22,22^FDTask: {task_name[:20]}^FS")
            current_y += 25
            
            if location:
                zpl_lines.append(f"^FO30,{current_y}^A0N,22,22^FDLocation: {location[:18]}^FS")
                current_y += 25
            
            zpl_lines.append(f"^FO30,{current_y}^A0N,22,22^FDSamples: {len(samples)}^FS")
            current_y += 35
            
            # Add container barcode
            zpl_lines.append(f"^FO30,{current_y}{generate_zpl_barcode(container_barcode, '128', 100, 4)}")
            current_y += 115  # Barcode height + margin
            
            zpl_lines.append(f"^FO30,{current_y}^A0N,22,22^FD{container_barcode}^FS")
            current_y += 35
            
            # Add sample information if present
            if samples:
                zpl_lines.append(f"^FO30,{current_y}^A0N,20,20^FDSample Contents:^FS")
                current_y += 25
                
                # Show up to 7 samples to fit the requirement
                max_samples = min(7, len(samples))
                for i, sample in enumerate(samples[:max_samples]):
                    sample_id = sample.get('SampleID', '')
                    sample_desc = sample.get('Description', '')[:15]  # Truncate for space
                    sample_barcode = sample.get('Barcode', f"SMP{sample_id}")
                    
                    zpl_lines.append(f"^FO30,{current_y}^A0N,16,16^FD{i+1}. SMP-{sample_id:0>3} {sample_desc}^FS")
                    current_y += 20
                    zpl_lines.append(f"^FO30,{current_y}^A0N,14,14^FD   {sample_barcode}^FS")
                    current_y += 18
                
                if len(samples) > max_samples:
                    zpl_lines.append(f"^FO30,{current_y}^A0N,16,16^FD... and {len(samples)-max_samples} more samples^FS")
                    current_y += 25
            
            # Add timestamp
            current_y += 10
            zpl_lines.append(f"^FO30,{current_y}^A0N,16,16^FD{datetime.now().strftime('%d-%m-%Y %H:%M')}^FS")
            
            # Close ZPL
            zpl_lines.append("^XZ")
            
            return "\n".join(zpl_lines)
        
        # Create simple container label matching sample format with actual barcodes
        current_app.logger.info(f"=== CONTAINER FORMAT DEBUG: Creating container label for {len(samples)} samples ===")
        
        # Check if this is a multi-part label
        label_part = data.get('label_part', '')
        part_info = f" ({label_part})" if label_part else ""
        
        # Add status indicator for empty containers
        status_info = " - EMPTY" if len(samples) == 0 else ""
        
        task_name = data.get('TaskName', 'None')
        label_content = f"""CONTAINER LABEL{part_info}{status_info}
===============
Container: CNT-{data.get('ContainerID', ''):0>4}
Type: {data.get('Type', data.get('ContainerType', ''))}
Description: {data.get('Description', '')}
Task: {task_name}
Location: {data.get('LocationName', '')}
Samples: {len(samples)} items{part_info}
Date: {packing_date}

SAMPLE CONTENTS:
"""
        current_app.logger.info(f"=== CONTAINER FORMAT DEBUG: Header created{part_info}, now adding {len(samples)} sample entries ===")
        
        # Add sample contents or empty container message
        if len(samples) == 0:
            # Empty container
            label_content += f"\n** CONTAINER IS EMPTY **\nNo samples currently stored.\n"
            current_app.logger.info(f"=== CONTAINER FORMAT DEBUG: Container is empty ===")
        else:
            # Add each sample with its info and barcode for physical printing
            for i, sample in enumerate(samples):
                sample_id = sample.get('SampleID', '')
                barcode = sample.get('Barcode', f'SMP{sample_id}')
                part_number = sample.get('PartNumber', '')
                description = sample.get('Description', '')
                
                current_app.logger.info(f"=== CONTAINER FORMAT DEBUG: Processing sample {i+1}: ID={sample_id}, Barcode='{barcode}' ===")
                
                # Add sample info without numbers
                label_content += f"\nSample: SMP-{sample_id:0>3}"
                if part_number:
                    label_content += f"\nPart: {part_number}"
                if description and len(description) <= 25:
                    label_content += f"\nDesc: {description}"
                
                # Add barcode line - this will be converted to actual barcode by brother_printer.py
                barcode_line = f"\nBarcode: {barcode}\n"
                label_content += barcode_line
                current_app.logger.info(f"=== CONTAINER FORMAT DEBUG: Added barcode line: '{barcode_line.strip()}' ===")
        
        # Add container barcode at the end for easy scanning
        container_barcode = data.get('Barcode', f"CNT-{data.get('ContainerID', '')}")
        container_barcode_section = f"\nCONTAINER BARCODE:\nBarcode: {container_barcode}"
        label_content += container_barcode_section
        current_app.logger.info(f"=== CONTAINER FORMAT DEBUG: Added container barcode section: '{container_barcode_section.strip()}' ===")
        current_app.logger.info(f"=== CONTAINER FORMAT DEBUG: Final label content ({len(label_content)} chars):\n{label_content}")
        return label_content
    
    elif label_type == 'location':
        return f"""LOCATION LABEL
==============
Location: {data.get('LocationName', '')}
Type: {data.get('Type', 'Storage')}
Description: {data.get('Description', '')}
Barcode: {data.get('Barcode', '')}
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
    
    elif label_type == 'test_sample':
        # Test sample labels for individual test specimens
        return f"""TEST SAMPLE LABEL
=================
Sample: {data.get('SampleIDFormatted', '')}
Test ID: {data.get('TestID', '')}
Part: {data.get('PartNumber', '')}
Test Type: {data.get('TestType', '')}
Container: CNT-{data.get('ContainerID', ''):0>4}
Date: {datetime.now().strftime('%d-%m-%Y')}
Barcode: {data.get('TestBarcode', '')}
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
    Send label content to Brother QL printer using custom utility.
    """
    import os
    from app.utils.brother_printer import print_label_simple
    
    # Get printer IP from environment variable
    printer_ip = os.getenv('BROTHER_PRINTER_IP', '192.168.1.142')
    
    try:
        # Use custom printer utility
        result = print_label_simple(label_content, printer_ip)
        
        if result['status'] == 'success':
            return {
                'status': 'success', 
                'message': f'Label printed successfully: {result["message"]}'
            }
        else:
            current_app.logger.error(f"Printer error: {result['message']}")
            return {
                'status': 'error', 
                'message': result['message']
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
            
            # Insert into History table - check if we have sample_id or container_id
            if sample_id:
                cursor.execute("""
                    INSERT INTO History (SampleID, ActionType, Notes, UserID, Timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    sample_id,
                    action_type,
                    notes,
                    1,  # Default user - should be replaced with actual user from session
                    datetime.now()
                ))
            elif container_id:
                # For container labels, log against all samples in the container
                cursor.execute("""
                    INSERT INTO History (SampleID, ActionType, Notes, UserID, Timestamp)
                    SELECT DISTINCT s.SampleID, %s, %s, %s, %s
                    FROM containersample cs
                    JOIN samplestorage ss ON cs.SampleStorageID = ss.StorageID
                    JOIN sample s ON ss.SampleID = s.SampleID
                    WHERE cs.ContainerID = %s
                """, (
                    action_type,
                    f"{notes} (Container: CNT-{container_id:04d})",
                    1,
                    datetime.now(),
                    container_id
                ))
            
            mysql.connection.commit()
            cursor.close()
            
    except Exception as e:
        current_app.logger.error(f"Failed to log print action: {str(e)}")

def print_sample_label(sample_data, auto_print=True):
    """
    Print individual sample label for direct storage samples.
    Returns success status and message.
    """
    try:
        # Generate sample barcode if not provided
        if 'Barcode' not in sample_data or not sample_data['Barcode']:
            sample_data['Barcode'] = generate_barcode('sample', sample_data)
        
        if auto_print:
            # Get printer configuration
            printer_config = get_printer_config('sample')
            if not printer_config:
                # Create a default printer configuration for direct printing
                printer_config = {
                    'printer_type': 'brother_ql810w',
                    'format': 'compact',
                    'use_zpl': False,
                    'description': 'Brother QL-810W (default configuration)'
                }
            
            # Format and print label
            label_content = format_label_enhanced('sample', sample_data, printer_config)
            result = print_to_device(label_content, printer_config)
            
            # Log print action
            if result['status'] == 'success':
                log_print_action('sample', sample_data, printer_config)
            
            return result
        else:
            return {
                'status': 'success',
                'message': 'Sample label data prepared',
                'sample_data': sample_data
            }
            
    except Exception as e:
        current_app.logger.error(f"Error printing sample label: {str(e)}")
        return {
            'status': 'error',
            'message': f'Failed to print sample label: {str(e)}'
        }

def print_container_label(container_id, auto_print=True, max_samples_per_label=7):
    """
    Print container label with all sample barcodes and information.
    Returns success status and message.
    """
    current_app.logger.info(f"=== CONTAINER PRINT DEBUG: Starting print_container_label for container {container_id} ===")
    try:
        if not mysql or not mysql.connection:
            return {
                'status': 'error',
                'message': 'Database connection not available'
            }
        
        cursor = mysql.connection.cursor()
        
        # Get container details
        cursor.execute("""
            SELECT 
                c.ContainerID,
                c.Description,
                ct.TypeName,
                sl.LocationName,
                c.ContainerCapacity
            FROM container c
            LEFT JOIN containertype ct ON c.ContainerTypeID = ct.ContainerTypeID
            LEFT JOIN storagelocation sl ON c.LocationID = sl.LocationID
            WHERE c.ContainerID = %s
        """, (container_id,))
        
        container_result = cursor.fetchone()
        if not container_result:
            cursor.close()
            return {
                'status': 'error',
                'message': f'Container {container_id} not found'
            }
        
        # Get all samples in the container with task information
        # Note: using correct lowercase table names from database schema
        cursor.execute("""
            SELECT 
                s.SampleID,
                s.Description,
                s.PartNumber,
                s.Barcode,
                cs.Amount,
                t.TaskName
            FROM containersample cs
            JOIN samplestorage ss ON cs.SampleStorageID = ss.StorageID
            JOIN sample s ON ss.SampleID = s.SampleID
            LEFT JOIN task t ON s.TaskID = t.TaskID
            WHERE cs.ContainerID = %s
            ORDER BY s.SampleID
        """, (container_id,))
        
        samples_result = cursor.fetchall()
        current_app.logger.info(f"=== CONTAINER PRINT DEBUG: Found {len(samples_result)} samples in container {container_id} ===")
        for i, sample_row in enumerate(samples_result):
            current_app.logger.info(f"Sample {i+1}: ID={sample_row[0]}, Desc='{sample_row[1]}', Part='{sample_row[2]}', Barcode='{sample_row[3]}', Amount={sample_row[4]}")
        
        # Also log container details for debugging
        current_app.logger.info(f"=== CONTAINER PRINT DEBUG: Container details ===")
        current_app.logger.info(f"Container ID: {container_result[0]}")
        current_app.logger.info(f"Description: {container_result[1]}")
        current_app.logger.info(f"Type: {container_result[2]}")
        current_app.logger.info(f"Location: {container_result[3]}")
        current_app.logger.info(f"Capacity: {container_result[4]}")
        cursor.close()
        
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
                # Generate a scannable barcode for this sample
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                generated_barcode = f"SMP{sample_id}{timestamp[-6:]}"
                
                # Update the database with the new barcode
                try:
                    update_cursor = mysql.connection.cursor()
                    update_cursor.execute("""
                        UPDATE sample SET Barcode = %s WHERE SampleID = %s
                    """, (generated_barcode, sample_id))
                    mysql.connection.commit()
                    update_cursor.close()
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
        # First check if container already has a barcode in database
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT Barcode FROM container WHERE ContainerID = %s", (container_id,))
        existing_barcode_result = cursor.fetchone()
        cursor.close()
        
        if existing_barcode_result and existing_barcode_result[0]:
            container_barcode = existing_barcode_result[0]
            current_app.logger.info(f"Using existing container barcode: {container_barcode}")
        else:
            # Generate new barcode and save it - use consistent CNT-{id} format
            container_barcode = f"CNT-{container_id}"
            
            # Update container with new barcode
            try:
                cursor = mysql.connection.cursor()
                cursor.execute("UPDATE container SET Barcode = %s WHERE ContainerID = %s", (container_barcode, container_id))
                mysql.connection.commit()
                cursor.close()
                current_app.logger.info(f"Generated and saved new container barcode: {container_barcode}")
            except Exception as e:
                current_app.logger.error(f"Failed to save container barcode: {e}")
                # Use generated barcode anyway
        
        container_data['Barcode'] = container_barcode
        
        if auto_print:
            # Get printer configuration - try container first, then fall back to sample printer
            printer_config = get_printer_config('container')
            if not printer_config:
                # Fall back to sample printer configuration
                printer_config = get_printer_config('sample')
            
            if not printer_config:
                # Create a default printer configuration for direct printing
                printer_config = {
                    'printer_type': 'brother_ql810w',
                    'format': 'standard',
                    'use_zpl': False,
                    'description': 'Brother QL-810W (default configuration)'
                }
            
            current_app.logger.info(f"=== CONTAINER PRINT DEBUG: Container has {len(container_data['samples'])} samples, max per label: {max_samples_per_label} ===")
            
            # Check if we need to split into multiple labels
            all_samples = container_data['samples']
            if len(all_samples) <= max_samples_per_label:
                # Single label
                current_app.logger.info(f"=== CONTAINER PRINT DEBUG: Printing single label ===")
                current_app.logger.info(f"=== CONTAINER PRINT DEBUG: Container data keys: {list(container_data.keys())} ===")
                current_app.logger.info(f"=== CONTAINER PRINT DEBUG: Printer config: {printer_config} ===")
                
                label_content = format_label_enhanced('container', container_data, printer_config)
                current_app.logger.info(f"=== CONTAINER PRINT DEBUG: Formatted label content (first 300 chars): {label_content[:300]}... ===")
                current_app.logger.info(f"=== CONTAINER PRINT DEBUG: Full label content:\n{label_content} ===")
                
                result = print_to_device(label_content, printer_config)
                current_app.logger.info(f"=== CONTAINER PRINT DEBUG: Print device result: {result} ===")
                
                if result['status'] == 'success':
                    log_print_action('container', container_data, printer_config)
                
                return result
            else:
                # Multiple labels needed
                total_labels = (len(all_samples) + max_samples_per_label - 1) // max_samples_per_label
                current_app.logger.info(f"=== CONTAINER PRINT DEBUG: Splitting into {total_labels} labels ===")
                
                results = []
                for label_num in range(total_labels):
                    start_idx = label_num * max_samples_per_label
                    end_idx = min(start_idx + max_samples_per_label, len(all_samples))
                    
                    # Create container data for this label
                    label_container_data = container_data.copy()
                    label_container_data['samples'] = all_samples[start_idx:end_idx]
                    label_container_data['label_part'] = f"{label_num + 1}/{total_labels}"
                    
                    current_app.logger.info(f"=== CONTAINER PRINT DEBUG: Printing label {label_num + 1}/{total_labels} with samples {start_idx+1}-{end_idx} ===")
                    
                    label_content = format_label_enhanced('container', label_container_data, printer_config)
                    result = print_to_device(label_content, printer_config)
                    results.append(result)
                    
                    if result['status'] == 'success':
                        log_print_action('container', label_container_data, printer_config)
                    
                # Return combined result
                success_count = sum(1 for r in results if r['status'] == 'success')
                return {
                    'status': 'success' if success_count == total_labels else 'partial',
                    'message': f'Printed {success_count}/{total_labels} container labels successfully',
                    'results': results
                }
        else:
            return {
                'status': 'success',
                'message': 'Container label data prepared',
                'container_data': container_data
            }
            
    except Exception as e:
        current_app.logger.error(f"Error printing container label: {str(e)}")
        return {
            'status': 'error',
            'message': f'Failed to print container label: {str(e)}'
        }

@printer_bp.route('/api/print/sample/<int:sample_id>', methods=['POST'])
def print_sample_label_endpoint(sample_id):
    """
    Endpoint to print sample label for a specific sample.
    """
    try:
        data = request.get_json() or {}
        auto_print = data.get('auto_print', True)
        
        if not mysql or not mysql.connection:
            return jsonify({
                'status': 'error',
                'message': 'Database connection not available'
            }), 500
        
        cursor = mysql.connection.cursor()
        
        # Get sample details
        cursor.execute("""
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
            FROM sample s
            LEFT JOIN unit u ON s.UnitID = u.UnitID
            LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
            LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
            LEFT JOIN task t ON s.TaskID = t.TaskID
            WHERE s.SampleID = %s
        """, (sample_id,))
        
        sample_result = cursor.fetchone()
        cursor.close()
        
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
        
        result = print_sample_label(sample_data, auto_print)
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Sample label print endpoint error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Sample label print error: {str(e)}'
        }), 500

@printer_bp.route('/api/print/container/<int:container_id>', methods=['POST'])
def print_container_label_endpoint(container_id):
    """
    Endpoint to print container label for a specific container.
    """
    try:
        current_app.logger.info(f"=== CONTAINER ENDPOINT DEBUG: Received request to print container {container_id} ===")
        data = request.get_json() or {}
        auto_print = data.get('auto_print', True)
        current_app.logger.info(f"=== CONTAINER ENDPOINT DEBUG: Request data: {data} ===")
        current_app.logger.info(f"=== CONTAINER ENDPOINT DEBUG: auto_print = {auto_print} ===")
        
        result = print_container_label(container_id, auto_print)
        current_app.logger.info(f"=== CONTAINER ENDPOINT DEBUG: Print result: {result} ===")
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Container label print endpoint error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Container label print error: {str(e)}'
        }), 500

@printer_bp.route('/api/print/test-sample', methods=['POST'])
def print_test_sample_label():
    """
    Endpoint to print test sample labels for individual test specimens.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
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
        
        # Log print action
        if result['status'] == 'success':
            log_print_action('test_sample', data, printer_config)
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Test sample label print error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Test sample label print error: {str(e)}'
        }), 500

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

@printer_bp.route('/api/print/test', methods=['POST', 'GET'])
def test_print():
    """Test printing - will actually print to Brother QL-810W"""
    try:
        # Get printer type from request or default to sample printer
        label_type = 'sample'  # Default for test
        
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
        
        # Get printer configuration - use default if not configured
        printer_config = get_printer_config(label_type)
        if not printer_config:
            # Create a basic config for testing
            printer_config = {
                'description': 'Brother QL-810W Test Configuration',
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

@printer_bp.route('/api/print/simulate', methods=['POST', 'GET'])
def simulate_print():
    """Simulate printing without actually sending to printer - for testing without labels."""
    try:
        # Get printer type from request or default to sample printer
        label_type = 'sample'  # Default for test
        
        test_data = {
            'label_type': label_type,
            'data': {
                'message': 'This is a SIMULATED test label',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'SampleIDFormatted': 'TEST-001',
                'Description': 'Test Sample for Printer (SIMULATION)',
                'PartNumber': 'TEST-PART-001',
                'Type': 'Test',
                'Amount': '1',
                'UnitName': 'pcs'
            }
        }
        
        # Get printer configuration - use default if not configured
        printer_config = get_printer_config(label_type)
        if not printer_config:
            # Create a basic config for testing
            printer_config = {
                'description': 'Brother QL-810W Test Configuration (SIMULATION)',
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
            'message': 'SIMULATED: Label would be printed successfully',
            'label_content': label_content,
            'printer_config': printer_config['description']
        })
        
    except Exception as e:
        current_app.logger.error(f"Test simulate error: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Test simulate error: {str(e)}'
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

@printer_bp.route('/api/print/storage-info/<int:sample_id>', methods=['GET'])
def get_sample_storage_info(sample_id):
    """
    Get information about how a sample is stored (container vs direct storage)
    and recommend appropriate label printing strategy.
    """
    try:
        if not mysql or not mysql.connection:
            return jsonify({
                'status': 'error',
                'message': 'Database connection not available'
            }), 500
        
        cursor = mysql.connection.cursor()
        
        # Check if sample is in a container
        cursor.execute("""
            SELECT 
                s.SampleID,
                s.Description,
                c.ContainerID,
                c.Description as ContainerDescription,
                ct.TypeName as ContainerType,
                sl.LocationName,
                COUNT(cs2.SampleStorageID) as SamplesInContainer
            FROM sample s
            LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
            LEFT JOIN containersample cs ON ss.StorageID = cs.SampleStorageID
            LEFT JOIN container c ON cs.ContainerID = c.ContainerID
            LEFT JOIN containertype ct ON c.ContainerTypeID = ct.ContainerTypeID
            LEFT JOIN storagelocation sl ON c.LocationID = sl.LocationID
            LEFT JOIN containersample cs2 ON c.ContainerID = cs2.ContainerID
            WHERE s.SampleID = %s
            GROUP BY s.SampleID, c.ContainerID
        """, (sample_id,))
        
        result = cursor.fetchone()
        cursor.close()
        
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

# Legacy function for backwards compatibility
def format_label(label_type, data):
    """
    Legacy format function for backwards compatibility.
    """
    config = {'format': 'standard'}
    return format_label_enhanced(label_type, data, config)