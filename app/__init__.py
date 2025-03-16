from flask import Flask, render_template
from flask_mysqldb import MySQL
import os
from dotenv import load_dotenv

mysql = MySQL()

def create_app():
    app = Flask(__name__, static_folder='static')
    
    # Indlæs konfiguration
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(dotenv_path)
    
    app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
    app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
    app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
    app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
    
    # Initialiser MySQL
    mysql.init_app(app)
    
    # Tilføj context processor for current_user
    from app.utils.auth import get_current_user
    @app.context_processor
    def inject_current_user():
        return {'current_user': get_current_user(mysql)}
    
    # Registrer blueprints
    from app.routes import register_blueprints
    register_blueprints(app, mysql)
    
    # Registrer error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500
    
    return app