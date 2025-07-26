"""
Custom Brother QL printer utility that bypasses brother_ql library issues.
Sends raw data directly to printer via network socket.
"""
import socket
import tempfile
import os
from PIL import Image, ImageDraw, ImageFont
from flask import current_app

def create_label_image(text_content, width=696, height=200):
    """Create a label image from text content."""
    # Create white background image
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to load fonts
    try:
        font_small = ImageFont.truetype("arial.ttf", 14)
        font_medium = ImageFont.truetype("arial.ttf", 18)
        font_large = ImageFont.truetype("arial.ttf", 24)
    except:
        # Fallback to default font
        font_small = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_large = ImageFont.load_default()
    
    # Parse text content and draw lines
    lines = text_content.strip().split('\n')
    y_offset = 10
    margin = 10
    
    for line in lines:
        if not line.strip():
            y_offset += 10
            continue
            
        clean_line = line.strip().replace('│', '').replace('╭', '').replace('╰', '').replace('─', '').replace('╮', '').replace('╯', '')
        
        if not clean_line:
            y_offset += 5
            continue
        
        # Choose font based on content
        if any(header in clean_line.upper() for header in ['SAMPLE:', 'CONTAINER:', 'TEST:', 'LABEL']):
            current_font = font_large
            line_height = 28
        elif any(important in clean_line.upper() for important in ['BARCODE:', 'ID:', 'PART:']):
            current_font = font_medium
            line_height = 22
        else:
            current_font = font_small
            line_height = 18
        
        # Draw text
        draw.text((margin, y_offset), clean_line, fill='black', font=current_font)
        y_offset += line_height
    
    return img

def try_brother_ql_usb(image_path):
    """Try printing via brother_ql USB."""
    try:
        import subprocess
        cmd = ['brother_ql', '-b', 'pyusb', '-m', 'QL-810W', 'print', '-l', '62', image_path]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return True, "Printed via brother_ql USB"
        else:
            return False, f"brother_ql USB failed: {result.stderr}"
            
    except Exception as e:
        return False, f"brother_ql USB error: {str(e)}"

def try_brother_ql_network(image_path, printer_ip):
    """Try printing via brother_ql network."""
    try:
        import subprocess
        cmd = ['brother_ql', '-b', 'network', '-m', 'QL-810W', '-p', f'tcp://{printer_ip}:9100', 'print', '-l', '62', image_path]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return True, f"Printed via brother_ql network to {printer_ip}"
        else:
            return False, f"brother_ql network failed: {result.stderr}"
            
    except Exception as e:
        return False, f"brother_ql network error: {str(e)}"

def print_label_simple(text_content, printer_ip="192.168.1.142"):
    """Simple function to print text as label to Brother printer using brother_ql library."""
    try:
        from brother_ql.conversion import convert
        from brother_ql.backends.helpers import send
        from brother_ql.raster import BrotherQLRaster
        from PIL import Image
        import tempfile
        import os
        
        # Create label image
        img = create_label_image(text_content)
        
        # Create raster data using brother_ql
        qlr = BrotherQLRaster('QL-810W')
        convert(qlr, [img], '62', dither=False, compress=False, red=False, rotate='0')
        
        # Send to printer via network
        send(instructions=qlr.data, printer_identifier=f'tcp://{printer_ip}', backend_identifier='network', blocking=True)
        
        current_app.logger.info(f"Label printed successfully to Brother QL-810W at {printer_ip}")
        return {'status': 'success', 'message': f'Label printed successfully to Brother QL-810W at {printer_ip}'}
            
    except ImportError as e:
        current_app.logger.error(f"Brother QL library not available: {str(e)}")
        return {'status': 'error', 'message': f'Brother QL library not installed: {str(e)}'}
    except Exception as e:
        current_app.logger.error(f"Print error: {str(e)}")
        return {'status': 'error', 'message': f'Print error: {str(e)}'}

# Removed Windows spooler functions - using brother_ql library instead