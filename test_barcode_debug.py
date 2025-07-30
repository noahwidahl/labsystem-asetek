#!/usr/bin/env python3
"""
Simple test script to debug barcode generation in container labels.
Run this to test if barcodes are being generated properly.
"""

import sys
import os
sys.path.append('.')

# Set minimal env variables for testing
os.environ['SECRET_KEY'] = 'test'
os.environ['MYSQL_HOST'] = 'localhost'
os.environ['MYSQL_USER'] = 'root'  
os.environ['MYSQL_PASSWORD'] = 'test'
os.environ['MYSQL_DB'] = 'labsystem'

def test_barcode_generation():
    """Test the barcode generation and label formatting"""
    
    from app import create_app
    from app.utils.brother_printer import create_label_image
    
    app = create_app()
    with app.app_context():
        print("=== BARCODE DEBUG TEST ===")
        
        # Test label content with multiple barcodes similar to container format
        test_content = """CONTAINER LABEL
===============
Container: CNT-0001
Type: Standard
Description: Test Container
Location: 1.1.1
Samples: 2 items
Date: 29-07-2025

SAMPLE CONTENTS:

1. Sample: SMP-001
   Part: TEST-PART-001
   Desc: Test Sample 1
   Barcode: SMP1202507290001

2. Sample: SMP-002
   Part: TEST-PART-002  
   Desc: Test Sample 2
   Barcode: SMP2202507290002

CONTAINER BARCODE:
Barcode: CNT120250729001"""

        print("Test content:")
        print(test_content)
        print("\n" + "="*50)
        
        try:
            print("Creating label image...")
            img = create_label_image(test_content)
            print(f"✓ Label image created successfully: {img.size}")
            
            # Save debug image
            debug_path = 'debug_container_label.png'
            img.save(debug_path)
            print(f"✓ Debug image saved to: {debug_path}")
            
            # Check if python-barcode is available
            try:
                from barcode import Code128
                from barcode.writer import ImageWriter
                print("✓ python-barcode library is available")
                
                # Test individual barcode generation
                test_barcode = "SMP1202507290001"
                code128 = Code128(test_barcode, writer=ImageWriter())
                print(f"✓ Successfully created Code128 for: {test_barcode}")
                
            except ImportError as e:
                print(f"⚠ python-barcode library not available: {e}")
                print("   Barcodes will use simple fallback rendering")
                
        except Exception as e:
            print(f"✗ Error creating label image: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        return True

if __name__ == "__main__":
    success = test_barcode_generation()
    if success:
        print("\n✓ Test completed successfully!")
        print("Check the debug_container_label.png file to see if barcodes are rendered.")
    else:
        print("\n✗ Test failed!")
        sys.exit(1)