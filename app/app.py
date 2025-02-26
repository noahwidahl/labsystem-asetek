from flask import Flask, render_template, jsonify
from flask_mysqldb import MySQL
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask med korrekt static folder
app = Flask(__name__, static_folder='static')

# MySQL Configuration
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')

# Initialize MySQL
mysql = MySQL(app)

@app.route('/')
@app.route('/dashboard')
def dashboard():
    try:
        cursor = mysql.connection.cursor()
        
        # Hent data til dashboard
        cursor.execute('''
            SELECT COUNT(*) 
            FROM samples 
            WHERE status != "Slettet"
        ''')
        sample_count = cursor.fetchone()[0] if cursor.fetchone() else 0
        
        cursor.execute('''
            SELECT COUNT(*) 
            FROM samples 
            WHERE expiry_date <= DATE_ADD(CURDATE(), INTERVAL 14 DAY)
            AND status != "Slettet"
        ''')
        expiring_count = cursor.fetchone()[0] if cursor.fetchone() else 0
        
        cursor.execute('''
            SELECT COUNT(*) 
            FROM samples 
            WHERE DATE(registered) = CURDATE()
            AND status != "Slettet"
        ''')
        new_today = cursor.fetchone()[0] if cursor.fetchone() else 0
        
        cursor.execute('''
            SELECT COUNT(*) 
            FROM tests 
            WHERE status = "Aktiv"
        ''')
        active_tests_count = cursor.fetchone()[0] if cursor.fetchone() else 0
        
        return render_template('sections/dashboard.html',
                             sample_count=sample_count,
                             expiring_count=expiring_count,
                             new_today=new_today,
                             active_tests_count=active_tests_count)
                             
    except Exception as e:
        print(f"Database error: {e}")
        return render_template('sections/dashboard.html', error="Database fejl")
    finally:
        if cursor:
            cursor.close()

@app.route('/storage')
def storage():
    try:
        cursor = mysql.connection.cursor()
        
        cursor.execute('''
            SELECT id, description, amount, location, 
                   DATE_FORMAT(registered, '%Y-%m-%d %H:%i') as registered, 
                   status 
            FROM samples
            WHERE status != 'Slettet'
            ORDER BY registered DESC
        ''')
        
        samples = []
        columns = [column[0] for column in cursor.description]
        for row in cursor.fetchall():
            samples.append(dict(zip(columns, row)))
        
        return render_template('sections/storage.html', samples=samples)
    except Exception as e:
        print(f"Database error: {e}")
        return render_template('sections/storage.html', error="Database fejl")
    finally:
        if cursor:
            cursor.close()

@app.route('/register')
def register():
    try:
        cursor = mysql.connection.cursor()
        
        # For test formål - returner tom template hvis tabeller ikke eksisterer
        try:
            cursor.execute('SELECT id, name FROM suppliers')
            suppliers = cursor.fetchall()
            
            cursor.execute('SELECT id, username FROM users')
            users = cursor.fetchall()
        except:
            suppliers = []
            users = []
        
        return render_template('sections/register.html', 
                             suppliers=suppliers,
                             users=users)
    except Exception as e:
        print(f"Database error: {e}")
        return render_template('sections/register.html', error="Database fejl")
    finally:
        if cursor:
            cursor.close()

@app.route('/testing')
def testing():
    try:
        cursor = mysql.connection.cursor()
        
        cursor.execute('''
            SELECT t.*, COUNT(ts.sample_id) as sample_count 
            FROM tests t
            LEFT JOIN test_samples ts ON t.id = ts.test_id
            WHERE t.status = 'Aktiv'
            GROUP BY t.id
        ''')
        
        active_tests = cursor.fetchall()
        return render_template('sections/testing.html', active_tests=active_tests)
    except Exception as e:
        print(f"Database error: {e}")
        return render_template('sections/testing.html', error="Database fejl")
    finally:
        if cursor:
            cursor.close()

@app.route('/history')
def history():
    try:
        cursor = mysql.connection.cursor()
        
        cursor.execute('''
            SELECT * FROM activity_log
            ORDER BY timestamp DESC
            LIMIT 50
        ''')
        
        history_items = cursor.fetchall()
        return render_template('sections/history.html', history_items=history_items)
    except Exception as e:
        print(f"Database error: {e}")
        return render_template('sections/history.html', error="Database fejl")
    finally:
        if cursor:
            cursor.close()

@app.route('/api/expiring-samples')
def get_expiring_samples():
    try:
        cursor = mysql.connection.cursor()
        
        cursor.execute('''
            SELECT id, description, expiry_date, 
                   DATEDIFF(expiry_date, CURDATE()) as days_until_expiry,
                   location
            FROM samples
            WHERE expiry_date <= DATE_ADD(CURDATE(), INTERVAL 14 DAY)
            AND status != "Slettet"
            ORDER BY expiry_date ASC
        ''')
        
        expiring_samples = []
        columns = [column[0] for column in cursor.description]
        for row in cursor.fetchall():
            expiring_samples.append(dict(zip(columns, row)))
        
        return jsonify({'samples': expiring_samples})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': 'Database fejl'}), 500
    finally:
        if cursor:
            cursor.close()

@app.route('/api/storage-locations')
def get_storage_locations():
    try:
        cursor = mysql.connection.cursor()
        
        cursor.execute('''
            SELECT location, COUNT(*) as count,
            CASE 
                WHEN COUNT(*) >= capacity THEN 'occupied'
                ELSE 'available'
            END as status
            FROM storage_locations
            LEFT JOIN samples ON storage_locations.location = samples.location
            GROUP BY location
        ''')
        
        locations = []
        columns = [column[0] for column in cursor.description]
        for row in cursor.fetchall():
            locations.append(dict(zip(columns, row)))
        
        return jsonify({'locations': locations})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': 'Database fejl'}), 500
    finally:
        if cursor:
            cursor.close()

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)