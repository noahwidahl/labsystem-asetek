"""
LabSystem Application Entry Point (MSSQL Version)

This is the main entry point for running the Laboratory Management System
with Microsoft SQL Server backend and Entra ID authentication.

Usage:
    python run_mssql.py

Configuration:
    - Ensure environment variables are set for database and Azure credentials
    - See ENTRA_ID_SETUP.md for detailed configuration instructions
    - Application runs on http://localhost:5000 by default

The application will start in debug mode for development. For production
deployment, use a proper WSGI server like gunicorn.
"""
import os

# Import the SQL Server version of create_app directly
from app.__init___mssql import create_app

app = create_app()

if __name__ == '__main__':
    # Kør Flask-appen på alle netværksinterfaces, så den er tilgængelig på hele netværket
    app.run(debug=True, host='0.0.0.0', port=5000)