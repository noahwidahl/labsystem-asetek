"""
Custom Brother QL printer utility that bypasses brother_ql library issues.
Sends raw data directly to printer via network socket.
"""
import socket
import tempfile
import os
from PIL import Image, ImageDraw, ImageFont
from flask import current_app

def create_label_image(text_content, width=696, height=500):
    """Create a label image from text content."""
    # Create white background image
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to load fonts - much larger sizes to match test label
    try:
        font_small = ImageFont.truetype("arial.ttf", 36)
        font_medium = ImageFont.truetype("arial.ttf", 48)
        font_large = ImageFont.truetype("arial.ttf", 64)
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
        
        # Choose font based content - much larger line heights for double-sized fonts
        if any(header in clean_line.upper() for header in ['SAMPLE:', 'CONTAINER:', 'TEST:', 'LABEL']):
            current_font = font_large
            line_height = 76
        elif any(important in clean_line.upper() for important in ['BARCODE:', 'ID:', 'PART:']):
            current_font = font_medium
            line_height = 60
        else:
            current_font = font_small
            line_height = 48
        
        # Skip drawing the barcode line as text - we'll draw it as actual barcode
        if 'Barcode:' not in clean_line:
            # Draw text only if it's not a barcode line
            draw.text((margin, y_offset), clean_line, fill='black', font=current_font)
            y_offset += line_height
    
    # Add some spacing after text before barcode
    y_offset += 20
    
    # Add barcode after all text if text content contains "Barcode:"
    barcode_value = None
    for line in lines:
        if 'Barcode:' in line:
            barcode_value = line.split('Barcode:')[1].strip()
            break
    
    if barcode_value:
        try:
            # Try to generate barcode using python-barcode library
            from barcode import Code128
            from barcode.writer import ImageWriter
            import io
            
            # Create barcode image with smaller height
            code128 = Code128(barcode_value, writer=ImageWriter())
            barcode_buffer = io.BytesIO()
            code128.write(barcode_buffer, {
                'text_distance': 5, 
                'module_height': 8,  # Smaller height
                'module_width': 0.3  # Narrower bars for wider appearance
            })
            barcode_buffer.seek(0)
            
            # Load barcode image
            barcode_img = Image.open(barcode_buffer)
            
            # Make barcode smaller and wider - resize to desired dimensions
            barcode_width = width - 100  # Leave more margin on sides
            barcode_height = 60  # Fixed smaller height
            barcode_img = barcode_img.resize((barcode_width, barcode_height))
            
            # Position barcode after text content
            barcode_x = (width - barcode_width) // 2  # Center horizontally
            barcode_y = y_offset  # Position right after text
            
            # Paste barcode onto label
            img.paste(barcode_img, (barcode_x, barcode_y))
            current_app.logger.info(f"Generated barcode for value: {barcode_value}")
            
        except ImportError:
            current_app.logger.warning("Python-barcode library not installed. Install with: pip install python-barcode[images]")
            # Fallback: Draw simple bars manually
            draw_simple_barcode(draw, barcode_value, width, y_offset, font_small)
        except Exception as e:
            current_app.logger.warning(f"Barcode generation failed: {e}")
            # Fallback: Draw simple bars manually
            draw_simple_barcode(draw, barcode_value, width, y_offset, font_small)
    
    return img

def draw_simple_barcode(draw, barcode_value, width, y_position, font):
    """Draw a simple barcode-like representation when barcode library isn't available."""
    # Position barcode at the given y_position instead of calculated bottom
    barcode_y = y_position
    barcode_width = width - 100  # Match the main barcode width margins
    barcode_x = (width - barcode_width) // 2  # Center horizontally
    
    # Draw simple vertical lines to represent barcode - make it smaller/wider
    bar_width = max(2, barcode_width // len(barcode_value))  # Ensure minimum bar width
    barcode_height = 60  # Fixed height to match main barcode
    
    for i, char in enumerate(barcode_value):
        x = barcode_x + (i * bar_width)
        # Create simple bars with consistent height
        bar_height = barcode_height - 10  # Slightly shorter than container
        draw.rectangle([x, barcode_y, x + bar_width - 1, barcode_y + bar_height], fill='black')
    
    # Add text below bars
    text_y = barcode_y + barcode_height + 5
    text_bbox = draw.textbbox((0, 0), barcode_value, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_x = (width - text_width) // 2  # Center text
    draw.text((text_x, text_y), barcode_value, fill='black', font=font)

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