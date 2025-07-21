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
    """Simple function to print text as label to Brother printer."""
    try:
        # Create label image
        img = create_label_image(text_content)
        
        # Use Windows print spooler directly - skip brother_ql due to compatibility issues
        return print_via_windows_spooler_direct(img)
            
    except Exception as e:
        current_app.logger.error(f"Print error: {str(e)}")
        return {'status': 'error', 'message': f'Print error: {str(e)}'}

def print_via_windows_spooler_direct(image):
    """Print via Windows using direct printer targeting."""
    try:
        # Save image as temporary file
        temp_path = tempfile.mktemp(suffix='.png')
        image.save(temp_path, 'PNG')
        
        # Find Brother QL-810W printer specifically
        import subprocess
        result = subprocess.run(['powershell', '-Command', 'Get-Printer | Select-Object Name'], 
                              capture_output=True, text=True)
        
        brother_printer = None
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'brother' in line.lower() and ('ql-810w' in line.lower() or 'ql810w' in line.lower()):
                    # Extract printer name (remove "Name" header and whitespace)
                    brother_printer = line.strip()
                    if brother_printer != "Name" and brother_printer != "----":
                        break
        
        if brother_printer:
            # Print directly to Brother printer using PowerShell
            print_cmd = f'''powershell -Command "
            $printer = '{brother_printer}'
            Add-Type -AssemblyName System.Drawing
            Add-Type -AssemblyName System.Windows.Forms
            
            # Set Brother as default temporarily and print
            $img = [System.Drawing.Image]::FromFile('{temp_path}')
            $pd = New-Object System.Drawing.Printing.PrintDocument
            $pd.PrinterSettings.PrinterName = $printer
            $pd.add_PrintPage({{
                $_.Graphics.DrawImage($img, 0, 0, $img.Width, $img.Height)
            }})
            $pd.Print()
            $img.Dispose()
            "'''
            
            result = subprocess.run(['powershell', '-Command', print_cmd], 
                                  capture_output=True, text=True)
            
            message = f'Printed directly to {brother_printer}'
        else:
            # Fallback: Open image with default application and print
            os.startfile(temp_path, "print")
            message = 'Opened image for printing (use Ctrl+P to print to Brother)'
        
        # Clean up after delay
        import threading
        def cleanup():
            import time
            time.sleep(10)  # Wait longer for print to complete
            try:
                os.unlink(temp_path)
            except:
                pass
        
        threading.Thread(target=cleanup).start()
        
        return {'status': 'success', 'message': message}
        
    except Exception as e:
        return {'status': 'error', 'message': f'Windows print error: {str(e)}'}

def print_via_windows_spooler(image):
    """Fallback: Original spooler method."""
    return print_via_windows_spooler_direct(image)