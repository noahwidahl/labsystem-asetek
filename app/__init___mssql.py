"""
LabSystem Flask Application Factory (MSSQL Version)

This is the main application factory for the Laboratory Management System.
It configures Flask with Microsoft SQL Server as the database backend
and Microsoft Entra ID for authentication.

Key Components:
- MSSQL database connection via pyodbc
- Entra ID authentication for Microsoft 365 users
- Blueprint-based route organization
- Template and static file serving

Required Environment Variables:
- MSSQL_SERVER, MSSQL_DATABASE, MSSQL_USERNAME, MSSQL_PASSWORD
- AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID
- SECRET_KEY (for Flask sessions)
"""
from flask import Flask, render_template
import os
from dotenv import load_dotenv

def create_app():
    import os
    # Get the absolute path to the app directory
    app_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(app_dir, 'templates')
    static_dir = os.path.join(app_dir, 'static')
    
    app = Flask(__name__, static_folder=static_dir, template_folder=template_dir)
    
    # Indlæs konfiguration
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(dotenv_path)
    
    # SQL Server configuration
    app.config['MSSQL_SERVER'] = os.getenv('MSSQL_SERVER')
    app.config['MSSQL_DATABASE'] = os.getenv('MSSQL_DATABASE')
    app.config['MSSQL_USERNAME'] = os.getenv('MSSQL_USERNAME')
    app.config['MSSQL_PASSWORD'] = os.getenv('MSSQL_PASSWORD')
    app.config['MSSQL_DRIVER'] = os.getenv('MSSQL_DRIVER', 'ODBC Driver 18 for SQL Server')
    app.config['MSSQL_TRUST_CERT'] = os.getenv('MSSQL_TRUST_CERT', 'yes')
    
    # Deaktivér cache for templates
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    
    # Flask secret key for sessions
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    
    # Azure/Entra ID configuration
    app.config['AZURE_CLIENT_ID'] = os.getenv('AZURE_CLIENT_ID')
    app.config['AZURE_CLIENT_SECRET'] = os.getenv('AZURE_CLIENT_SECRET') 
    app.config['AZURE_TENANT_ID'] = os.getenv('AZURE_TENANT_ID')
    
    # Set environment variables for mssql_db module
    os.environ['MSSQL_SERVER'] = app.config['MSSQL_SERVER']
    os.environ['MSSQL_DATABASE'] = app.config['MSSQL_DATABASE']
    os.environ['MSSQL_USERNAME'] = app.config['MSSQL_USERNAME'] or ''
    os.environ['MSSQL_PASSWORD'] = app.config['MSSQL_PASSWORD'] or ''
    os.environ['MSSQL_DRIVER'] = app.config['MSSQL_DRIVER']
    os.environ['MSSQL_TRUST_CERT'] = app.config['MSSQL_TRUST_CERT']
    
    # Tilføj context processor for current_user (Entra ID + SQL Server version)
    from app.utils.entra_auth import get_current_user_entra
    from app.utils.mssql_db import mssql_db
    
    @app.context_processor
    def inject_current_user():
        # Also inject Azure config for frontend
        return {
            'current_user': get_current_user_entra(mssql_db),
            'azure_client_id': app.config.get('AZURE_CLIENT_ID', ''),
            'azure_tenant_id': app.config.get('AZURE_TENANT_ID', '')
        }
    
    # Registrer authentication blueprint
    from app.routes.auth import auth_bp
    
    # Registrer SQL Server blueprints
    from app.routes.dashboard_mssql import dashboard_mssql_bp
    from app.routes.sample_mssql import sample_mssql_bp
    from app.routes.container_mssql import container_mssql_bp
    from app.routes.test_mssql import test_mssql_bp
    from app.routes.task_mssql import task_mssql_bp
    from app.routes.scanner_mssql import scanner_mssql_bp
    from app.routes.expiration_mssql import expiration_mssql_bp
    from app.routes.barcode_mssql import barcode_mssql_bp
    from app.routes.system_mssql import system_mssql_bp
    from app.routes.printer_mssql import printer_mssql_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_mssql_bp)
    app.register_blueprint(sample_mssql_bp)
    app.register_blueprint(container_mssql_bp)
    app.register_blueprint(test_mssql_bp)
    app.register_blueprint(task_mssql_bp)
    app.register_blueprint(scanner_mssql_bp)
    app.register_blueprint(expiration_mssql_bp)
    app.register_blueprint(barcode_mssql_bp)
    app.register_blueprint(system_mssql_bp)
    app.register_blueprint(printer_mssql_bp)
    
    # Root route - redirect to dashboard or login
    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('dashboard_mssql.dashboard'))
    
    # Registrer error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500
    
    return app