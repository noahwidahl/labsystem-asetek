from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_mysqldb import MySQL
from datetime import datetime
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Initialize Flask with correct static folder
app = Flask(__name__, static_folder='static')

# Indlæs .env fra roden af projektet
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
print(f"Looking for .env file at: {dotenv_path}")
load_dotenv(dotenv_path)
print(f"Database being used: {os.getenv('MYSQL_DB')}")

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
        # For at simulere den oprindelige prototype bruger vi dummy data indtil databasen er aktiv
        sample_count = 45
        expiring_count = 8
        new_today = 5
        active_tests_count = 3
        
        return render_template('sections/dashboard.html', 
                             sample_count=sample_count,
                             expiring_count=expiring_count,
                             new_today=new_today,
                             active_tests_count=active_tests_count)
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        return render_template('sections/dashboard.html', error="Fejl ved indlæsning af dashboard")

@app.route('/storage')
def storage():
    try:
        # Dummy data for simulation until database is ready
        samples = [
            {
                "SampleID": "PRV-1001",
                "Description": "Køleløb Type A",
                "Amount": "27 stk",
                "LocationID": "A1.B2",
                "registered": "2024-02-20 13:45",
                "Status": "På lager"
            },
            {
                "SampleID": "PRV-1002",
                "Description": "O-rings 40mm",
                "Amount": "190 stk",
                "LocationID": "A2.C3",
                "registered": "2024-02-15 09:30",
                "Status": "På lager"
            },
            {
                "SampleID": "PRV-1003",
                "Description": "Gummislange",
                "Amount": "42 m",
                "LocationID": "B1.A4",
                "registered": "2024-01-28 11:20",
                "Status": "Udløber snart"
            }
        ]
        
        return render_template('sections/storage.html', samples=samples)
    except Exception as e:
        print(f"Error loading storage: {e}")
        return render_template('sections/storage.html', error="Fejl ved indlæsning af lager")

@app.route('/register')
def register():
    try:
        # Dummy data for simulation until database is ready
        suppliers = [
            {"SupplierID": 1, "SupplierName": "Leverandør 1"},
            {"SupplierID": 2, "SupplierName": "Leverandør 2"},
        ]
        
        users = [
            {"UserID": 1, "Name": "BWM"},
            {"UserID": 2, "Name": "JDO"},
        ]
        
        units = [
            {"UnitID": 1, "UnitName": "Stk"},
            {"UnitID": 2, "UnitName": "m"},
            {"UnitID": 3, "UnitName": "L"},
            {"UnitID": 4, "UnitName": "kg"},
        ]
        
        locations = [
            {"LocationID": 1, "LocationName": "Sektion A1"},
            {"LocationID": 2, "LocationName": "Sektion A2"},
            {"LocationID": 3, "LocationName": "Sektion B1"},
        ]
        
        return render_template('sections/register.html', 
                             suppliers=suppliers,
                             users=users,
                             units=units,
                             locations=locations)
    except Exception as e:
        print(f"Error loading register: {e}")
        return render_template('sections/register.html', error="Fejl ved indlæsning af registreringsform")

@app.route('/testing')
def testing():
    try:
        # Dummy data for simulation until database is ready
        active_tests = [
            {
                "TestID": "T1234.5",
                "TestName": "Køleløb Test",
                "Description": "Test af køleløb",
                "UserName": "BWM",
                "CreatedDate": "3. Oktober 2024",
                "sample_count": 8
            },
            {
                "TestID": "T2345.6",
                "TestName": "O-ring Test",
                "Description": "Test af O-rings",
                "UserName": "JDO",
                "CreatedDate": "3. Oktober 2024",
                "sample_count": 10
            }
        ]
        
        # Også hente prøver til modal dialogen
        samples = [
            {
                "SampleID": "PRV-1001",
                "Description": "Køleløb Type A",
                "Amount": 27,
                "LocationID": "A1.B2",
            },
            {
                "SampleID": "PRV-1002",
                "Description": "O-rings 40mm",
                "Amount": 190,
                "LocationID": "A2.C3",
            }
        ]
        
        users = [
            {"UserID": 1, "Name": "BWM"},
            {"UserID": 2, "Name": "JDO"},
        ]
        
        return render_template('sections/testing.html', 
                               active_tests=active_tests, 
                               samples=samples,
                               users=users)
    except Exception as e:
        print(f"Error loading testing: {e}")
        return render_template('sections/testing.html', error="Fejl ved indlæsning af test administration")

@app.route('/history')
def history():
    try:
        # Dummy data for simulation until database is ready
        history_items = [
            {
                "LogID": 1,
                "Timestamp": "13. Oktober 2024",
                "ActionType": "Modtaget",
                "UserName": "BWM",
                "SampleDesc": "T2345.6_7",
                "Notes": "Del af 200 O-rings modtaget. Placering: 1.2.3"
            },
            {
                "LogID": 2,
                "Timestamp": "3. Oktober 2024",
                "ActionType": "Testing",
                "UserName": "MM",
                "SampleDesc": "T2345.6_7",
                "Notes": "Udvalgt til test T2345.6. Del af gruppe på 10 O-rings."
            },
            {
                "LogID": 3,
                "Timestamp": "13. Oktober 2024",
                "ActionType": "Disposed",
                "UserName": "MM",
                "SampleDesc": "T2345.6_7",
                "Notes": "Prøve kasseret efter test."
            }
        ]
        
        return render_template('sections/history.html', history_items=history_items)
    except Exception as e:
        print(f"Error loading history: {e}")
        return render_template('sections/history.html', error="Fejl ved indlæsning af historik")

@app.route('/api/expiring-samples')
def get_expiring_samples():
    try:
        # Dummy data for simulation until database is ready
        expiring_samples = [
            {
                "SampleID": "PRV-1001",
                "Description": "Køleløb Type A",
                "ExpireDate": "2024-12-24",
                "days_until_expiry": 13,
                "LocationName": "A1.B2"
            }
        ]
        
        return jsonify({'samples': expiring_samples})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': 'Database fejl'}), 500

@app.route('/api/storage-locations')
def get_storage_locations():
    try:
        # Dummy data for simulation until database is ready
        locations = []
        for i in range(1, 13):
            a_num = (i - 1) // 4 + 1
            b_num = (i - 1) % 4 + 1
            
            # Nogle tilfældige lokationer er optaget
            is_occupied = i % 3 == 0
            
            locations.append({
                "LocationName": f"A{a_num}.B{b_num}",
                "count": 3 if is_occupied else 0,
                "status": "occupied" if is_occupied else "available"
            })
        
        return jsonify({'locations': locations})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': 'Database fejl'}), 500

@app.route('/api/samples', methods=['POST'])
def create_sample():
    try:
        # Når databasen er implementeret, vil denne kode gemme prøven
        data = request.json
        print(f"Received sample registration data: {data}")
        
        # I mellemtiden simulerer vi et vellykket svar
        return jsonify({'success': True, 'sample_id': 'PRV-' + str(1000 + len(data))})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/createTest', methods=['POST'])
def api_create_test():
    try:
        # Når databasen er implementeret, vil denne kode gemme testen
        data = request.json
        print(f"Received test creation data: {data}")
        
        # I mellemtiden simulerer vi et vellykket svar
        return jsonify({'success': True, 'test_id': 'T' + str(1000 + len(data))})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)