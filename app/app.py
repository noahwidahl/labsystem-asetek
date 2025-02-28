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
        # Hent antal prøver på lager
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM Sample s
            JOIN SampleStorage ss ON s.SampleID = ss.SampleID
            WHERE s.Status = 'På lager' AND ss.AmountRemaining > 0
        """)
        sample_count = cursor.fetchone()[0]
        
        # Hent prøver der udløber snart (indenfor 14 dage)
        cursor.execute("""
            SELECT COUNT(*) FROM SampleStorage
            WHERE ExpireDate <= DATE_ADD(CURRENT_DATE(), INTERVAL 14 DAY)
            AND AmountRemaining > 0
        """)
        expiring_count = cursor.fetchone()[0]
        
        # Hent nye prøver i dag
        cursor.execute("""
            SELECT COUNT(*) FROM Reception
            WHERE DATE(ReceivedDate) = CURDATE()
        """)
        new_today = cursor.fetchone()[0]
        
        # Hent antal aktive tests
        cursor.execute("SELECT COUNT(*) FROM Test WHERE CreatedDate > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)")
        active_tests_count = cursor.fetchone()[0]
        
        # Hent seneste historik
        cursor.execute("""
            SELECT 
                h.LogID,
                DATE_FORMAT(h.Timestamp, '%d. %M %Y') as FormattedDate,
                h.ActionType,
                u.Name,
                COALESCE(s.SampleID, ts.GeneratedIdentifier, 'N/A') as ItemID,
                h.Notes
            FROM History h
            LEFT JOIN User u ON h.UserID = u.UserID
            LEFT JOIN Sample s ON h.SampleID = s.SampleID
            LEFT JOIN TestSample ts ON h.TestID = ts.TestID
            ORDER BY h.Timestamp DESC
            LIMIT 5
        """)
        history_items = []
        for item in cursor.fetchall():
            sample_desc = f"PRV-{item[4]}" if item[4] and item[4] != 'N/A' else 'N/A'
            history_items.append({
                "LogID": item[0],
                "Timestamp": item[1],
                "ActionType": item[2],
                "UserName": item[3],
                "SampleDesc": sample_desc,
                "Notes": item[5]
            })
        
        cursor.close()
        
        return render_template('sections/dashboard.html', 
                             sample_count=sample_count,
                             expiring_count=expiring_count,
                             new_today=new_today,
                             active_tests_count=active_tests_count,
                             history_items=history_items)
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        return render_template('sections/dashboard.html', error="Fejl ved indlæsning af dashboard")

@app.route('/storage')
def storage():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT 
                s.SampleID, 
                s.Description, 
                ss.AmountRemaining, 
                u.UnitName, 
                sl.LocationName, 
                r.ReceivedDate, 
                s.Status,
                l.LabName
            FROM Sample s
            JOIN SampleStorage ss ON s.SampleID = ss.SampleID
            JOIN Unit u ON s.UnitID = u.UnitID
            JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
            JOIN Reception r ON s.ReceptionID = r.ReceptionID
            JOIN Lab l ON sl.LabID = l.LabID
            WHERE ss.AmountRemaining > 0
            ORDER BY s.SampleID DESC
        """)
        
        samples_data = cursor.fetchall()
        
        # Hent aktive brugere til disposal modal
        cursor.execute("SELECT UserID, Name FROM User")
        users = [dict(UserID=row[0], Name=row[1]) for row in cursor.fetchall()]
        
        cursor.close()
        
        # Konverter tuple data til dictionary for lettere brug i template
        samples = []
        for sample in samples_data:
            samples.append({
                "SampleID": f"PRV-{sample[0]}",
                "Description": sample[1],
                "Amount": f"{sample[2]} {sample[3]}",
                "LocationID": sample[4],
                "registered": sample[5].strftime('%Y-%m-%d %H:%M') if sample[5] else "Ukendt",
                "Status": sample[6] if sample[6] else "På lager",
                "LabName": sample[7]
            })
        
        return render_template('sections/storage.html', samples=samples, users=users)
    except Exception as e:
        print(f"Error loading storage: {e}")
        return render_template('sections/storage.html', error="Fejl ved indlæsning af lager")

@app.route('/register')
def register():
    try:
        cursor = mysql.connection.cursor()
        
        # Hent leverandører
        cursor.execute("SELECT SupplierID, SupplierName FROM Supplier")
        suppliers = [dict(SupplierID=row[0], SupplierName=row[1]) for row in cursor.fetchall()]
        
        # Hent brugere
        cursor.execute("SELECT UserID, Name FROM User")
        users = [dict(UserID=row[0], Name=row[1]) for row in cursor.fetchall()]
        
        # Hent enheder
        cursor.execute("SELECT UnitID, UnitName FROM Unit")
        units = [dict(UnitID=row[0], UnitName=row[1]) for row in cursor.fetchall()]
        
        # Hent labs
        cursor.execute("SELECT LabID, LabName FROM Lab")
        labs = [dict(LabID=row[0], LabName=row[1]) for row in cursor.fetchall()]
        
        # Hent lokationer
        cursor.execute("""
            SELECT l.LocationID, l.LocationName, lb.LabName
            FROM StorageLocation l
            JOIN Lab lb ON l.LabID = lb.LabID
        """)
        locations = []
        for row in cursor.fetchall():
            locations.append({
                'LocationID': row[0],
                'LocationName': row[1],
                'LabName': row[2]
            })
        
        cursor.close()
        
        return render_template('sections/register.html', 
                             suppliers=suppliers,
                             users=users,
                             units=units,
                             locations=locations,
                             labs=labs)
    except Exception as e:
        print(f"Error loading register: {e}")
        return render_template('sections/register.html', error="Fejl ved indlæsning af registreringsform")

@app.route('/testing')
def testing():
    try:
        cursor = mysql.connection.cursor()
        
        # Hent aktive tests med antal prøver
        cursor.execute("""
            SELECT 
                t.TestID, 
                t.TestName, 
                t.Description, 
                u.Name, 
                t.CreatedDate, 
                COUNT(ts.TestSampleID) as sample_count
            FROM Test t
            JOIN User u ON t.UserID = u.UserID
            LEFT JOIN TestSample ts ON t.TestID = ts.TestID
            WHERE t.CreatedDate > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
            GROUP BY t.TestID
        """)
        
        tests_data = cursor.fetchall()
        
        # Konverter tuple data til dictionary
        active_tests = []
        for test in tests_data:
            active_tests.append({
                "TestID": test[0],
                "TestName": test[1] if test[1] else f"Test {test[0]}",
                "Description": test[2] if test[2] else "",
                "UserName": test[3],
                "CreatedDate": test[4].strftime('%d. %B %Y') if test[4] else "Ukendt",
                "sample_count": test[5]
            })
        
        # Hent tilgængelige prøver
        cursor.execute("""
            SELECT 
                s.SampleID, 
                s.Description, 
                ss.AmountRemaining, 
                sl.LocationName
            FROM Sample s
            JOIN SampleStorage ss ON s.SampleID = ss.SampleID
            JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
            WHERE ss.AmountRemaining > 0
            AND s.Status = 'På lager'
        """)
        
        samples_data = cursor.fetchall()
        samples = []
        for sample in samples_data:
            samples.append({
                "SampleID": f"PRV-{sample[0]}",
                "Description": sample[1],
                "Amount": sample[2],
                "LocationID": sample[3]
            })
        
        # Hent brugere
        cursor.execute("SELECT UserID, Name FROM User")
        users = [dict(UserID=row[0], Name=row[1]) for row in cursor.fetchall()]
        
        cursor.close()
        
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
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT 
                h.LogID,
                DATE_FORMAT(h.Timestamp, '%d. %M %Y') as FormattedDate,
                h.ActionType,
                u.Name,
                COALESCE(s.SampleID, ts.GeneratedIdentifier, 'N/A') as ItemID,
                h.Notes
            FROM History h
            LEFT JOIN User u ON h.UserID = u.UserID
            LEFT JOIN Sample s ON h.SampleID = s.SampleID
            LEFT JOIN TestSample ts ON h.TestID = ts.TestID
            ORDER BY h.Timestamp DESC
            LIMIT 20
        """)
        history_data = cursor.fetchall()
        cursor.close()
        
        history_items = []
        for item in history_data:
            sample_desc = f"PRV-{item[4]}" if item[4] and item[4] != 'N/A' else 'N/A'
            history_items.append({
                "LogID": item[0],
                "Timestamp": item[1],
                "ActionType": item[2],
                "UserName": item[3],
                "SampleDesc": sample_desc,
                "Notes": item[5]
            })
        
        return render_template('sections/history.html', history_items=history_items)
    except Exception as e:
        print(f"Error loading history: {e}")
        return render_template('sections/history.html', error="Fejl ved indlæsning af historik")

# API Endpoints
@app.route('/api/expiring-samples')
def get_expiring_samples():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT 
                CONCAT('PRV-', s.SampleID) as SampleID, 
                s.Description, 
                ss.ExpireDate, 
                DATEDIFF(ss.ExpireDate, CURRENT_DATE()) as days_until_expiry,
                sl.LocationName
            FROM Sample s
            JOIN SampleStorage ss ON s.SampleID = ss.SampleID
            JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
            WHERE ss.ExpireDate <= DATE_ADD(CURRENT_DATE(), INTERVAL 14 DAY)
            AND s.Status = 'På lager'
            AND ss.AmountRemaining > 0
        """)
        
        columns = [col[0] for col in cursor.description]
        expiring_samples = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        for sample in expiring_samples:
            if isinstance(sample['ExpireDate'], datetime):
                sample['ExpireDate'] = sample['ExpireDate'].strftime('%Y-%m-%d')
        
        cursor.close()
        
        return jsonify({'samples': expiring_samples})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': 'Database fejl'}), 500

@app.route('/api/storage-locations')
def get_storage_locations():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT 
                sl.LocationName,
                COUNT(ss.StorageID) as count,
                CASE WHEN COUNT(ss.StorageID) > 0 THEN 'occupied' ELSE 'available' END as status,
                l.LabName
            FROM StorageLocation sl
            JOIN Lab l ON sl.LabID = l.LabID
            LEFT JOIN SampleStorage ss ON sl.LocationID = ss.LocationID AND ss.AmountRemaining > 0
            GROUP BY sl.LocationID
        """)
        
        columns = [col[0] for col in cursor.description]
        locations = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        
        return jsonify({'locations': locations})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': 'Database fejl'}), 500

@app.route('/api/samples', methods=['POST'])
def create_sample():
    try:
        data = request.json
        cursor = mysql.connection.cursor()
        
        # Opret reception post først
        cursor.execute("""
            INSERT INTO Reception (SupplierID, ReceivedDate, UserID, Notes)
            VALUES (%s, NOW(), %s, %s)
        """, (
            data.get('supplier'),
            data.get('owner'),
            "Registreret via app"
        ))
        
        reception_id = cursor.lastrowid
        
        # Indsæt selve prøven
        cursor.execute("""
            INSERT INTO Sample (
                Type, 
                Description, 
                Status, 
                Amount, 
                UnitID, 
                OwnerID, 
                ReceptionID,
                IsUnique,
                Barcode
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            "Standard",
            data.get('description'),
            "På lager",
            data.get('totalAmount'),
            data.get('unit'),
            data.get('owner'),
            reception_id,
            1 if data.get('hasSerialNumbers') else 0,
            data.get('serialNumbers')[0] if data.get('serialNumbers') and data.get('hasSerialNumbers') else None
        ))
        
        sample_id = cursor.lastrowid
        
        # Indsæt til lager
        cursor.execute("""
            INSERT INTO SampleStorage (
                SampleID, 
                LocationID, 
                AmountRemaining, 
                ExpireDate
            )
            VALUES (%s, %s, %s, %s)
        """, (
            sample_id,
            data.get('storageLocation'),
            data.get('totalAmount'),
            data.get('expiryDate')
        ))
        
        # Log aktiviteten
        cursor.execute("""
            INSERT INTO History (Timestamp, ActionType, UserID, SampleID, Notes)
            VALUES (NOW(), %s, %s, %s, %s)
        """, (
            'Modtaget',
            data.get('owner'),
            sample_id,
            f"Prøve registreret af bruger ID {data.get('owner')}"
        ))
        
        # Hvis der er serienumre og prøven er unik, registrér serienumre i container
        if data.get('hasSerialNumbers') and data.get('serialNumbers'):
            # Opret container til serienumre, hvis de eksisterer
            cursor.execute("""
                INSERT INTO Container (Description, IsMixed)
                VALUES (%s, %s)
            """, (
                f"Container for {data.get('description')}",
                0  # Ikke blandet
            ))
            container_id = cursor.lastrowid
            
            # Hent storage ID
            cursor.execute("SELECT StorageID FROM SampleStorage WHERE SampleID = %s", (sample_id,))
            storage_id = cursor.fetchone()[0]
            
            # Indsæt serienumre som containersample
            cursor.execute("""
                INSERT INTO ContainerSample (SampleStorageID, ContainerID, Amount)
                VALUES (%s, %s, %s)
            """, (
                storage_id,
                container_id,
                len(data.get('serialNumbers'))
            ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'success': True, 'sample_id': f"PRV-{sample_id}"})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/createTest', methods=['POST'])
def api_create_test():
    try:
        data = request.json
        cursor = mysql.connection.cursor()
        
        # Opret testen
        cursor.execute("""
            INSERT INTO Test (TestNo, TestName, Description, CreatedDate, UserID)
            VALUES (%s, %s, %s, NOW(), %s)
        """, (
            f"T{data.get('type')}-{datetime.now().strftime('%Y%m%d')}",
            data.get('testName', 'Ny test'),
            data.get('description', ''),
            data.get('owner')
        ))
        
        test_id = cursor.lastrowid
        
        # Tilføj prøver til testen
        if data.get('samples'):
            for i, sample_data in enumerate(data.get('samples')):
                sample_id = sample_data.get('id').replace('PRV-', '')
                amount = int(sample_data.get('amount', 1))
                
                for j in range(amount):
                    # Generer unikt identifikations-id for test sample
                    test_sample_id = f"T{test_id}_{i+1}_{j+1}"
                    
                    cursor.execute("""
                        INSERT INTO TestSample (SampleID, TestID, TestIteration, GeneratedIdentifier)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        sample_id,
                        test_id,
                        j+1,
                        test_sample_id
                    ))
                    
                    # Reducer mængden på lager
                    cursor.execute("""
                        UPDATE SampleStorage 
                        SET AmountRemaining = AmountRemaining - 1
                        WHERE SampleID = %s AND AmountRemaining > 0
                        LIMIT 1
                    """, (sample_id,))
        
        # Log aktiviteten
        cursor.execute("""
            INSERT INTO History (Timestamp, ActionType, UserID, TestID, Notes)
            VALUES (NOW(), %s, %s, %s, %s)
        """, (
            'Test oprettet',
            data.get('owner'),
            test_id,
            f"Test T{test_id} oprettet af bruger ID {data.get('owner')}"
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'success': True, 'test_id': f"T{test_id}"})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/createDisposal', methods=['POST'])
def api_create_disposal():
    try:
        data = request.json
        cursor = mysql.connection.cursor()
        
        # Opret kassation
        cursor.execute("""
            INSERT INTO Disposal (SampleID, UserID, DisposalDate, AmountDisposed, Notes)
            VALUES (%s, %s, NOW(), %s, %s)
        """, (
            data.get('sampleId'),
            data.get('userId'),
            data.get('amount'),
            data.get('notes', '')
        ))
        
        disposal_id = cursor.lastrowid
        
        # Opdater lagerantal
        cursor.execute("""
            UPDATE SampleStorage 
            SET AmountRemaining = AmountRemaining - %s
            WHERE SampleID = %s AND AmountRemaining >= %s
        """, (
            data.get('amount'),
            data.get('sampleId'),
            data.get('amount')
        ))
        
        # Tjek om der er 0 tilbage, og opdater status
        cursor.execute("""
            SELECT AmountRemaining FROM SampleStorage 
            WHERE SampleID = %s
        """, (data.get('sampleId'),))
        
        remaining = cursor.fetchone()[0]
        
        if remaining <= 0:
            cursor.execute("""
                UPDATE Sample 
                SET Status = 'Kasseret'
                WHERE SampleID = %s
            """, (data.get('sampleId'),))
        
        # Log aktiviteten
        cursor.execute("""
            INSERT INTO History (Timestamp, ActionType, UserID, SampleID, Notes)
            VALUES (NOW(), %s, %s, %s, %s)
        """, (
            'Kasseret',
            data.get('userId'),
            data.get('sampleId'),
            f"Prøve kasseret: {data.get('amount')} enheder"
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'success': True, 'disposal_id': disposal_id})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/labs')
def get_labs():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT LabID, LabName FROM Lab")
        
        columns = [col[0] for col in cursor.description]
        labs = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        
        return jsonify({'labs': labs})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': 'Database fejl'}), 500

@app.route('/api/containers')
def api_containers():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT 
                c.ContainerID,
                c.Description,
                c.IsMixed,
                COUNT(cs.ContainerSampleID) as sample_count,
                SUM(cs.Amount) as total_items
            FROM Container c
            LEFT JOIN ContainerSample cs ON c.ContainerID = cs.ContainerID
            GROUP BY c.ContainerID
            ORDER BY c.ContainerID DESC
        """)
        
        columns = [col[0] for col in cursor.description]
        containers = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        
        return jsonify({'containers': containers})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': 'Database fejl'}), 500

@app.route('/api/createContainer', methods=['POST'])
def api_create_container():
    try:
        data = request.json
        cursor = mysql.connection.cursor()
        
        # Opret container
        cursor.execute("""
            INSERT INTO Container (Description, IsMixed)
            VALUES (%s, %s)
        """, (
            data.get('description'),
            data.get('isMixed')
        ))
        
        container_id = cursor.lastrowid
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'success': True, 'container_id': container_id})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/activeSamples')
def api_active_samples():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT 
                s.SampleID,
                CONCAT('PRV-', s.SampleID) as SampleIDFormatted,
                s.Description,
                ss.AmountRemaining,
                u.UnitName as Unit,
                sl.LocationName
            FROM Sample s
            JOIN SampleStorage ss ON s.SampleID = ss.SampleID
            JOIN Unit u ON s.UnitID = u.UnitID
            JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
            WHERE ss.AmountRemaining > 0
            AND s.Status = 'På lager'
            ORDER BY s.SampleID DESC
        """)
        
        columns = [col[0] for col in cursor.description]
        samples = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        
        return jsonify({'samples': samples})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': 'Database fejl'}), 500

@app.route('/api/recentDisposals')
def api_recent_disposals():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT 
                CONCAT('PRV-', s.SampleID) as SampleID,
                d.DisposalDate,
                d.AmountDisposed,
                u.Name as DisposedBy
            FROM Disposal d
            JOIN Sample s ON d.SampleID = s.SampleID
            JOIN User u ON d.UserID = u.UserID
            ORDER BY d.DisposalDate DESC
            LIMIT 5
        """)
        
        columns = [col[0] for col in cursor.description]
        disposals = []
        
        for row in cursor.fetchall():
            disposal = dict(zip(columns, row))
            if isinstance(disposal['DisposalDate'], datetime):
                disposal['DisposalDate'] = disposal['DisposalDate'].strftime('%Y-%m-%d')
            disposals.append(disposal)
        
        cursor.close()
        
        return jsonify({'disposals': disposals})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': 'Database fejl'}), 500

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)