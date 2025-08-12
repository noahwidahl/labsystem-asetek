"""
Alternative run script for LabSystem with Microsoft SQL Server support.
Use this instead of run.py when running with SQL Server.
"""
from app import create_app
import os

# Import the SQL Server version of create_app
import importlib.util
spec = importlib.util.spec_from_file_location("app_mssql", "app/__init___mssql.py")
app_mssql = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_mssql)

app = app_mssql.create_app()

if __name__ == '__main__':
    # Kør Flask-appen på alle netværksinterfaces, så den er tilgængelig på hele netværket
    app.run(debug=True, host='0.0.0.0', port=5000)