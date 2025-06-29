#!/usr/bin/env python3
"""
Barcode Scanner Diagnostics Script
Tests the backend functionality for barcode scanning
"""

import requests
import json
import time
import subprocess
import sys
import os

def test_flask_server():
    """Test if Flask server is running"""
    try:
        response = requests.get('http://localhost:5000', timeout=5)
        print(f"✓ Flask server is running (Status: {response.status_code})")
        return True
    except requests.exceptions.ConnectionError:
        print("✗ Flask server is not running")
        return False
    except requests.exceptions.Timeout:
        print("✗ Flask server timeout")
        return False

def test_barcode_api(barcode):
    """Test barcode API endpoint"""
    try:
        url = f'http://localhost:5000/api/barcode/{barcode}'
        print(f"\nTesting API: {url}")
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200 and data.get('success'):
            print(f"✓ API test passed for {barcode}")
            return True
        else:
            print(f"✗ API test failed for {barcode}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ API request failed: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"✗ JSON decode error: {e}")
        return False

def check_javascript_files():
    """Check if JavaScript files exist"""
    js_files = [
        'app/static/js/barcode-scanner.js',
        'app/static/js/scanner-functions.js',
        'app/templates/base.html',
        'app/templates/sections/scanner.html'
    ]
    
    print("\n=== JavaScript Files Check ===")
    for file_path in js_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} exists")
            # Check file size
            size = os.path.getsize(file_path)
            print(f"  Size: {size} bytes")
        else:
            print(f"✗ {file_path} not found")

def check_database_connection():
    """Check database connection"""
    try:
        import MySQLdb
        print("\n=== Database Connection Check ===")
        print("✓ MySQLdb module is available")
        
        # Try to connect (adjust credentials as needed)
        try:
            conn = MySQLdb.connect(
                host='localhost',
                user='root',
                passwd='1234',
                db='labsystem'
            )
            print("✓ Database connection successful")
            
            cursor = conn.cursor()
            
            # Test sample query
            cursor.execute("SELECT COUNT(*) FROM sample WHERE Barcode LIKE 'BC%'")
            count = cursor.fetchone()[0]
            print(f"✓ Found {count} samples with BC barcodes")
            
            # Test container query
            cursor.execute("SELECT COUNT(*) FROM container")
            count = cursor.fetchone()[0]
            print(f"✓ Found {count} containers")
            
            conn.close()
            return True
            
        except MySQLdb.Error as e:
            print(f"✗ Database connection failed: {e}")
            return False
            
    except ImportError:
        print("✗ MySQLdb module not available")
        return False

def test_specific_barcodes():
    """Test the specific barcodes mentioned in the issue"""
    test_barcodes = ['BC1-1751138774-1', 'CNT-12']
    
    print("\n=== Testing Specific Barcodes ===")
    for barcode in test_barcodes:
        success = test_barcode_api(barcode)
        if not success:
            print(f"Issue with barcode: {barcode}")

def check_browser_console_errors():
    """Generate a simple HTML page to check for console errors"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Console Error Check</title>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</head>
<body>
    <div id="console-output"></div>
    <script>
        // Capture console errors
        const originalConsoleError = console.error;
        const errors = [];
        
        console.error = function(...args) {
            errors.push(args.join(' '));
            originalConsoleError.apply(console, arguments);
        };
        
        // Try to load barcode scanner
        const script = document.createElement('script');
        script.src = './app/static/js/barcode-scanner.js';
        script.onload = function() {
            console.log('Barcode scanner loaded successfully');
            // Try to create instance
            try {
                if (typeof BarcodeScanner !== 'undefined') {
                    const scanner = new BarcodeScanner();
                    console.log('BarcodeScanner instance created');
                } else {
                    console.error('BarcodeScanner class not found');
                }
            } catch (e) {
                console.error('Error creating BarcodeScanner:', e);
            }
        };
        script.onerror = function() {
            console.error('Failed to load barcode scanner script');
        };
        document.head.appendChild(script);
        
        // Display errors after 2 seconds
        setTimeout(function() {
            const output = document.getElementById('console-output');
            if (errors.length > 0) {
                output.innerHTML = '<h3>Console Errors Found:</h3><ul>';
                errors.forEach(error => {
                    output.innerHTML += '<li>' + error + '</li>';
                });
                output.innerHTML += '</ul>';
            } else {
                output.innerHTML = '<h3>No console errors detected</h3>';
            }
        }, 2000);
    </script>
</body>
</html>
    """
    
    with open('console_error_check.html', 'w') as f:
        f.write(html_content)
    
    print("\n=== Browser Console Check ===")
    print("Created console_error_check.html - open this in a browser to check for JavaScript errors")

def main():
    print("Barcode Scanner Diagnostics")
    print("=" * 50)
    
    # Test Flask server
    if not test_flask_server():
        print("\nStarting Flask server test...")
        print("Please make sure the Flask app is running: python run.py")
        print("Or check if it's running on a different port")
    
    # Check files
    check_javascript_files()
    
    # Check database
    check_database_connection()
    
    # Test APIs
    test_specific_barcodes()
    
    # Generate console error checker
    check_browser_console_errors()
    
    print("\n" + "=" * 50)
    print("Diagnostics complete!")
    print("\nCommon Issues and Solutions:")
    print("1. If Flask server is not running: python run.py")
    print("2. If database connection fails: Check MySQL credentials in .env")
    print("3. If JavaScript files missing: Check file paths")
    print("4. If API returns 404: Check route registration")
    print("5. If Bootstrap errors: Check CDN links in base.html")
    print("6. Open console_error_check.html in browser to check for JS errors")

if __name__ == '__main__':
    main()