"""
Custom Brother QL printer utility that bypasses brother_ql library issues.
Sends raw data directly to printer via network socket.
"""
import socket
import tempfile
import os
from PIL import Image, ImageDraw, ImageFont
from flask import current_app

def create_label_image(text_content, width=696, max_height=1500):  # Use max_height instead of fixed height
    """Create a label image from text content with dynamic height."""
    current_app.logger.info(f"=== BARCODE DEBUG: Starting label creation ===")
    current_app.logger.info(f"Full text content: {text_content}")
    current_app.logger.info(f"Label max dimensions: {width}x{max_height}")
    
    # First pass: calculate actual height needed
    lines = text_content.strip().split('\n')
    estimated_height = 20  # Start with margin
    
    for line in lines:
        if not line.strip():
            estimated_height += 10
            continue
            
        clean_line = line.strip().replace('│', '').replace('╭', '').replace('╰', '').replace('─', '').replace('╮', '').replace('╯', '')
        
        if not clean_line:
            estimated_height += 5
            continue
        
        # Estimate height based on content type
        if 'CONTAINER LABEL' in clean_line.upper() or 'SAMPLE LABEL' in clean_line.upper():
            estimated_height += 50
        elif clean_line.startswith('Container: CNT-') or clean_line.startswith('Sample: SMP-'):
            estimated_height += 35
        elif 'Barcode:' in clean_line:
            estimated_height += 65  # Space for barcode image + text
        else:
            estimated_height += 28
    
    # Add some margin at the bottom
    estimated_height += 30
    
    # Use the smaller of estimated height or max height
    actual_height = min(estimated_height, max_height)
    
    current_app.logger.info(f"=== BARCODE DEBUG: Calculated actual height: {actual_height} (estimated: {estimated_height}) ===")
    
    # Create white background image with calculated height
    img = Image.new('RGB', (width, actual_height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to load fonts - optimized sizes for better readability
    try:
        font_small = ImageFont.truetype("arial.ttf", 24)  # Reduced from 36
        font_medium = ImageFont.truetype("arial.ttf", 32)  # Reduced from 48
        font_large = ImageFont.truetype("arial.ttf", 48)   # Reduced from 64
    except:
        # Fallback to default font
        font_small = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_large = ImageFont.load_default()
    
    # Parse text content and draw lines
    lines = text_content.strip().split('\n')
    current_app.logger.info(f"=== BARCODE DEBUG: Found {len(lines)} lines to process ===")
    for i, line in enumerate(lines):
        current_app.logger.info(f"Line {i}: '{line}'")
    
    y_offset = 10
    margin = 10
    barcode_count = 0
    
    for line_num, line in enumerate(lines):
        if not line.strip():
            y_offset += 10
            continue
            
        clean_line = line.strip().replace('│', '').replace('╭', '').replace('╰', '').replace('─', '').replace('╮', '').replace('╯', '')
        
        if not clean_line:
            y_offset += 5
            continue
        
        # Choose font based content - optimized for readability
        if 'CONTAINER LABEL' in clean_line.upper() or 'SAMPLE LABEL' in clean_line.upper():
            # Main header - keep large
            current_font = font_large
            line_height = 50
        elif clean_line.startswith('Container: CNT-') or clean_line.startswith('Sample: SMP-'):
            # Sample/Container ID lines - use medium font
            current_font = font_medium
            line_height = 35
        elif any(header in clean_line.upper() for header in ['SAMPLE:', 'TEST:', 'LABEL']):
            current_font = font_medium  # Reduced from large
            line_height = 35  # Reduced
        elif any(important in clean_line.upper() for important in ['BARCODE:', 'ID:', 'PART:']):
            current_font = font_medium
            line_height = 35
        else:
            current_font = font_small
            line_height = 28
        
        # Process barcode lines immediately when encountered
        if 'Barcode:' in clean_line:
            barcode_count += 1
            # Extract barcode value
            barcode_value = clean_line.split('Barcode:')[1].strip()
            current_app.logger.info(f"=== BARCODE DEBUG #{barcode_count}: Found barcode line ===")
            current_app.logger.info(f"Raw line: '{line}'")
            current_app.logger.info(f"Clean line: '{clean_line}'")
            current_app.logger.info(f"Extracted barcode value: '{barcode_value}'")
            
            # Add some spacing before barcode
            y_offset += 10
            
            try:
                # Try to generate barcode using python-barcode library
                from barcode import Code128
                from barcode.writer import ImageWriter
                import io
                
                # Create barcode image with smaller height
                code128 = Code128(barcode_value, writer=ImageWriter())
                barcode_buffer = io.BytesIO()
                code128.write(barcode_buffer, {
                    'text_distance': 3,   # Reduced text distance
                    'module_height': 10,  # Slightly taller bars
                    'module_width': 0.4,  # Slightly wider bars for better scanning
                    'font_size': 8,       # Smaller text under barcode
                    'text': True          # Ensure text is shown
                })
                barcode_buffer.seek(0)
                
                # Load barcode image
                barcode_img = Image.open(barcode_buffer)
                
                # Make barcode smaller and wider - resize to desired dimensions
                barcode_width = width - 100  # Leave more margin on sides
                barcode_height = 40  # Reduced height to save space
                barcode_img = barcode_img.resize((barcode_width, barcode_height))
                
                # Position barcode after text content
                barcode_x = (width - barcode_width) // 2  # Center horizontally
                barcode_y = y_offset  # Position right after text
                
                # Paste barcode onto label
                img.paste(barcode_img, (barcode_x, barcode_y))
                current_app.logger.info(f"=== BARCODE DEBUG #{barcode_count}: Successfully generated and pasted barcode ===")
                current_app.logger.info(f"Barcode value: '{barcode_value}'")
                current_app.logger.info(f"Barcode position: ({barcode_x}, {barcode_y})")
                current_app.logger.info(f"Barcode size: {barcode_width}x{barcode_height}")
                
                # Move y_offset past the barcode for next content
                y_offset += barcode_height + 10
                
            except ImportError as e:
                current_app.logger.error(f"=== BARCODE DEBUG #{barcode_count}: ImportError - {e} ===")
                current_app.logger.warning("Python-barcode library not installed. Install with: pip install python-barcode[images]")
                # Fallback: Draw simple bars manually
                barcode_height = draw_simple_barcode(draw, barcode_value, width, y_offset, font_small)
                current_app.logger.info(f"=== BARCODE DEBUG #{barcode_count}: Used fallback barcode, height: {barcode_height} ===")
                y_offset += barcode_height + 10  # Move past simple barcode
            except Exception as e:
                current_app.logger.error(f"=== BARCODE DEBUG #{barcode_count}: Exception during barcode generation - {e} ===")
                import traceback
                current_app.logger.error(f"=== BARCODE DEBUG #{barcode_count}: Full traceback:\n{traceback.format_exc()}")
                # Fallback: Draw simple bars manually
                barcode_height = draw_simple_barcode(draw, barcode_value, width, y_offset, font_small)
                current_app.logger.info(f"=== BARCODE DEBUG #{barcode_count}: Used fallback after exception, height: {barcode_height} ===")
                y_offset += barcode_height + 10  # Move past simple barcode
        else:
            # Draw text only if it's not a barcode line
            current_app.logger.info(f"=== BARCODE DEBUG: Drawing text line {line_num}: '{clean_line}' ===")
            draw.text((margin, y_offset), clean_line, fill='black', font=current_font)
            y_offset += line_height
    
    current_app.logger.info(f"=== BARCODE DEBUG: Finished processing. Total barcodes found: {barcode_count} ===")
    current_app.logger.info(f"=== BARCODE DEBUG: Final image size: {img.size} ===")
    return img

def draw_simple_barcode(draw, barcode_value, width, y_position, font):
    """Draw a simple barcode-like representation when barcode library isn't available."""
    current_app.logger.info(f"=== BARCODE DEBUG: Drawing simple barcode for '{barcode_value}' at y={y_position} ===")
    # Position barcode at the given y_position instead of calculated bottom
    barcode_y = y_position
    barcode_width = width - 100  # Match the main barcode width margins
    barcode_x = (width - barcode_width) // 2  # Center horizontally
    
    # Draw simple vertical lines to represent barcode - make it smaller/wider
    bar_width = max(2, barcode_width // len(barcode_value))  # Ensure minimum bar width
    barcode_height = 40  # Reduced height to match main barcode
    
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
    
    # Return the total height used by the barcode
    total_height = barcode_height + 25  # barcode + text + spacing
    current_app.logger.info(f"=== BARCODE DEBUG: Simple barcode completed, total height: {total_height} ===")
    return total_height

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
    current_app.logger.info(f"=== PRINT DEBUG: Starting print_label_simple ===")
    current_app.logger.info(f"Printer IP: {printer_ip}")
    current_app.logger.info(f"Text content length: {len(text_content)}")
    try:
        from brother_ql.conversion import convert
        from brother_ql.backends.helpers import send
        from brother_ql.raster import BrotherQLRaster
        from PIL import Image
        import tempfile
        import os
        
        current_app.logger.info(f"=== PRINT DEBUG: About to create label image ===")
        # Create label image
        img = create_label_image(text_content)
        current_app.logger.info(f"=== PRINT DEBUG: Label image created successfully, size: {img.size} ===")
        
        # Save debug image to temp file for inspection
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            debug_path = temp_file.name
            img.save(debug_path)
            current_app.logger.info(f"=== PRINT DEBUG: Saved debug image to {debug_path} ===")
        
        # Create raster data using brother_ql
        current_app.logger.info(f"=== PRINT DEBUG: Creating raster data ===")
        qlr = BrotherQLRaster('QL-810W')
        convert(qlr, [img], '62', dither=False, compress=False, red=False, rotate='0')
        current_app.logger.info(f"=== PRINT DEBUG: Raster data created, size: {len(qlr.data)} bytes ===")
        
        # Send to printer via network
        current_app.logger.info(f"=== PRINT DEBUG: Sending to printer at tcp://{printer_ip} ===")
        send(instructions=qlr.data, printer_identifier=f'tcp://{printer_ip}', backend_identifier='network', blocking=True)
        
        current_app.logger.info(f"=== PRINT DEBUG: Print job completed successfully ===")
        current_app.logger.info(f"Label printed successfully to Brother QL-810W at {printer_ip}")
        return {'status': 'success', 'message': f'Label printed successfully to Brother QL-810W at {printer_ip}'}
            
    except ImportError as e:
        current_app.logger.error(f"=== PRINT DEBUG: ImportError - {str(e)} ===")
        current_app.logger.error(f"Brother QL library not available: {str(e)}")
        return {'status': 'error', 'message': f'Brother QL library not installed: {str(e)}'}
    except Exception as e:
        current_app.logger.error(f"=== PRINT DEBUG: Exception during printing - {str(e)} ===")
        import traceback
        current_app.logger.error(f"=== PRINT DEBUG: Full traceback:\n{traceback.format_exc()}")
        current_app.logger.error(f"Print error: {str(e)}")
        return {'status': 'error', 'message': f'Print error: {str(e)}'}

# Removed Windows spooler functions - using brother_ql library instead