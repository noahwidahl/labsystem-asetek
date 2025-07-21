#!/usr/bin/env python3
"""
Production startup script for LabSystem
Run this at the deployment location
"""

from app import create_app
import os

if __name__ == '__main__':
    # Create Flask app
    app = create_app()
    
    # Get local IP for display
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print("="*50)
    print("🧪 LabSystem Production Server")
    print("="*50)
    print(f"Server IP: {local_ip}")
    print(f"Scanner URL: http://{local_ip}:5000/scanner-app")
    print(f"Full System: http://{local_ip}:5000")
    print("="*50)
    print("Scanner Instructions:")
    print(f"1. Connect MC330M to same WiFi")
    print(f"2. Open Chrome on MC330M")
    print(f"3. Go to: http://{local_ip}:5000/scanner-app")
    print(f"4. Bookmark for easy access")
    print("="*50)
    
    # Start server on all interfaces
    app.run(
        host='0.0.0.0',  # Listen on all network interfaces
        port=5000,
        debug=False,     # Production mode
        threaded=True    # Handle multiple requests
    )