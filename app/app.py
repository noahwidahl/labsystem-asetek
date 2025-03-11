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

# Add current_user to all templates
@app.context_processor
def inject_current_user():
    return {'current_user': get_current_user()}

# Hjælpefunktion til at hente aktuel bruger
def get_current_user():
    # I et reelt system ville dette komme fra session eller autentifikation
    # For nu bruger vi en dummy-implementering der antager, at brugeren er "Admin Bruger"
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT UserID, Name FROM User WHERE Name = 'BWM' LIMIT 1")
    user = cursor.fetchone()
    cursor.close()
    
    if user:
        return {"UserID": user[0], "Name": user[1]}
    else:
        return {"UserID": 1, "Name": "BWM"}  # Fallback

@app.route('/')
@app.route('/dashboard')
def dashboard():
    try:
        # Hent antal prøver på lager
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM Sample WHERE Status = 'På lager'")
        sample_count = cursor.fetchone()[0] or 0
        
        # Hent prøver der udløber snart (indenfor 14 dage)
        cursor.execute("""
            SELECT COUNT(*) FROM SampleStorage ss
            JOIN Sample s ON ss.SampleID = s.SampleID
            WHERE ss.ExpireDate <= DATE_ADD(CURRENT_DATE(), INTERVAL 14 DAY)
            AND s.Status = 'På lager'
            AND ss.AmountRemaining > 0
        """)
        expiring_count = cursor.fetchone()[0] or 0
        
        # Hent nye prøver i dag
        cursor.execute("""
            SELECT COUNT(*) FROM Reception
            WHERE DATE(ReceivedDate) = CURRENT_DATE()
        """)
        new_today = cursor.fetchone()[0] or 0
        
        # Hent antal aktive tests - ændret for at undgå brug af Status-kolonnen
        cursor.execute("SELECT COUNT(*) FROM Test")
        active_tests_count = cursor.fetchone()[0] or 0
        
        # Hent seneste historik med mere detaljeret information
        cursor.execute("""
            SELECT 
                h.LogID, 
                h.ActionType, 
                h.Notes,
                IFNULL(s.Description, 'N/A') as SampleDesc,
                u.Name as UserName,
                DATE_FORMAT(h.Timestamp, '%d-%m-%Y %H:%i') as Timestamp
            FROM History h
            LEFT JOIN Sample s ON h.SampleID = s.SampleID
            LEFT JOIN User u ON h.UserID = u.UserID
            ORDER BY h.Timestamp DESC
            LIMIT 5
        """)
        
        columns = [col[0] for col in cursor.description]
        history_items = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Initialiser storage locations
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
            LIMIT 12
        """)
        
        columns = [col[0] for col in cursor.description]
        locations = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        
        return render_template('sections/dashboard.html', 
                            sample_count=sample_count,
                            expiring_count=expiring_count,
                            new_today=new_today,
                            active_tests_count=active_tests_count,
                            history_items=history_items,
                            locations=locations)
    except Exception as e:
        import traceback
        error_message = f"Fejl: {str(e)}\n{traceback.format_exc()}"
        print(error_message)
        return render_template('sections/dashboard.html', 
                            error=error_message,
                            sample_count=0,
                            expiring_count=0,
                            new_today=0,
                            active_tests_count=0,
                            history_items=[],
                            locations=[])
    
@app.route('/test')
def test():
    return render_template('test.html')
    
@app.route('/storage')
def storage():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT 
                s.SampleID, 
                s.Description, 
                r.ReceivedDate as ModtagelseDato,
                ss.AmountRemaining as Antal,
                u.UnitName as Enhed, 
                sl.LocationName as Placering, 
                DATE_FORMAT(r.ReceivedDate, '%Y-%m-%d %H:%i') as Registreret,
                s.Status
            FROM Sample s
            JOIN SampleStorage ss ON s.SampleID = ss.SampleID
            JOIN Unit u ON s.UnitID = u.UnitID
            JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
            JOIN Reception r ON s.ReceptionID = r.ReceptionID
            WHERE ss.AmountRemaining > 0
            ORDER BY s.SampleID DESC
        """)
        
        samples_data = cursor.fetchall()
        
        # Konverter tuple data til dictionary for lettere brug i template
        samples = []
        for sample in samples_data:
            samples.append({
                "ID": f"PRV-{sample[0]}",
                "Beskrivelse": sample[1],
                "Modtagelse": sample[2].strftime('%Y-%m-%d') if sample[2] else "Ukendt",
                "Antal": f"{sample[3]} {sample[4]}", # Inkluder enheden her
                "Placering": sample[5],
                "Registreret": sample[6] if sample[6] else "Ukendt",
                "Status": sample[7] if sample[7] else "På lager"
            })
        
        return render_template('sections/storage.html', samples=samples)
    except Exception as e:
        print(f"Error loading storage: {e}")
        return render_template('sections/storage.html', error="Fejl ved indlæsning af lager")

@app.route('/api/previous-registrations')
def get_previous_registrations():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT 
                s.SampleID as id,
                s.Description as description,
                DATE_FORMAT(r.ReceivedDate, '%d-%m-%Y') as date
            FROM Sample s
            JOIN Reception r ON s.ReceptionID = r.ReceptionID
            ORDER BY r.ReceivedDate DESC
            LIMIT 10
        """)
        
        columns = [col[0] for col in cursor.description]
        registrations = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        
        return jsonify({'registrations': registrations})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': 'Database fejl'}), 500

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
        cursor.execute("SELECT UnitID, UnitName FROM Unit ORDER BY UnitName")
        units = [dict(UnitID=row[0], UnitName=row[1]) for row in cursor.fetchall()]
        
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
                             locations=locations)
    except Exception as e:
        print(f"Error loading register page: {e}")
        return render_template('sections/register.html', 
                              error="Fejl ved indlæsning af registreringsform")

@app.route('/testing')
def testing():
    try:
        cursor = mysql.connection.cursor()
        
        # Hent alle tests fra de sidste 30 dage
        cursor.execute("""
            SELECT 
                t.TestID, 
                t.TestNo, 
                t.TestName, 
                t.Description, 
                u.Name, 
                t.CreatedDate, 
                COUNT(ts.TestSampleID) as sample_count,
                (SELECT COUNT(*) FROM History h 
                 WHERE h.TestID = t.TestID AND h.ActionType = 'Test afsluttet') as is_completed
            FROM Test t
            JOIN User u ON t.UserID = u.UserID
            LEFT JOIN TestSample ts ON t.TestID = ts.TestID
            WHERE t.CreatedDate > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
            GROUP BY t.TestID
            ORDER BY t.CreatedDate DESC
        """)
        
        tests_data = cursor.fetchall()
        
        # Filtrer kun aktive tests (som ikke er markeret som afsluttet i History)
        active_tests = []
        for test in tests_data:
            is_completed = test[7] > 0  # Hvis der er mindst én "Test afsluttet" handling i History
            
            if not is_completed:  # Vis kun tests, der ikke er afsluttet
                active_tests.append({
                    "TestID": test[0],
                    "TestNo": test[1] if test[1] else f"Test {test[0]}",
                    "TestName": test[2] if test[2] else f"Test {test[0]}",
                    "Description": test[3] if test[3] else "",
                    "UserName": test[4],
                    "CreatedDate": test[5].strftime('%d. %B %Y') if test[5] else "Ukendt",
                    "sample_count": test[6]
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
                "SampleID": sample[0],
                "SampleIDFormatted": f"PRV-{sample[0]}",
                "Description": sample[1],
                "AmountRemaining": sample[2],
                "LocationName": sample[3]
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
    
@app.route('/api/suppliers', methods=['POST'])
def create_supplier():
    try:
        data = request.json
        supplier_name = data.get('name')
        
        if not supplier_name:
            return jsonify({'error': 'Leverandørnavn er påkrævet'}), 400
        
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO Supplier (SupplierName) VALUES (%s)", (supplier_name,))
        supplier_id = cursor.lastrowid
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'success': True, 'supplier_id': supplier_id})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/history')
def history():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT 
                h.LogID,
                DATE_FORMAT(h.Timestamp, '%d. %M %Y') as FormattedDate,
                h.ActionType,
                u.Name as UserName,
                COALESCE(s.SampleID, ts.GeneratedIdentifier, 'N/A') as ItemID,
                h.Notes,
                r.ReceptionID
            FROM History h
            LEFT JOIN User u ON h.UserID = u.UserID
            LEFT JOIN Sample s ON h.SampleID = s.SampleID
            LEFT JOIN TestSample ts ON h.TestID = ts.TestID
            LEFT JOIN Reception r ON s.ReceptionID = r.ReceptionID
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
                "Notes": item[5],
                "ReceptionID": item[6] if item[6] else None
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
        
        # Print modtagne data for debugging
        print(f"Modtaget data: {data}")
        
        # Få bruger-ID'et fra den aktuelle bruger
        current_user = get_current_user()
        user_id = current_user['UserID']
        
        # Håndtering af supplier
        supplier_id = None
        if data.get('supplier') and data.get('supplier').strip():
            try:
                supplier_id = int(data.get('supplier'))
            except (ValueError, TypeError):
                supplier_id = None
        
        # Sikre korrekt dato-formattering
        reception_date = datetime.now()
        if data.get('receptionDate'):
            try:
                reception_date = datetime.strptime(data.get('receptionDate'), '%Y-%m-%d')
            except (ValueError, TypeError):
                reception_date = datetime.now()
        
        # Indsæt reception post med bruger-ID'et fra current_user
        cursor.execute("""
            INSERT INTO Reception (
                SupplierID, 
                ReceivedDate, 
                UserID, 
                TrackingNumber,
                SourceType,
                Notes
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            supplier_id,
            reception_date,
            user_id,
            data.get('trackingNumber', ''),
            'Ekstern' if supplier_id else 'Intern',
            data.get('other', 'Registreret via lab system')
        ))
        
        reception_id = cursor.lastrowid
        
        # Bestem om det er en multi-pakke eller enkelt prøve
        is_multi_package = data.get('isMultiPackage', False)
        package_count = int(data.get('packageCount', 1)) if is_multi_package else 1
        
        # Generer en unik barcode hvis ikke angivet
        base_barcode = data.get('barcode', '')
        if not base_barcode:
            # Generer en unik barcode baseret på timestamp og reception ID
            base_barcode = f"BC{reception_id}-{int(datetime.now().timestamp())}"
        
        # Variable til at holde styr på sample_id og storage_id for den første prøve
        first_sample_id = None
        first_storage_id = None
        
        # Bestem om pakkerne har forskellige lokationer
        different_locations = data.get('differentLocations', False)
        package_locations = data.get('packageLocations', [])
        
        # Print locationdata til debugging
        print(f"Different locations: {different_locations}")
        print(f"Package locations: {package_locations}")
        
        # Flag for containeroprettelse
        create_containers = data.get('createContainers', False)
        container_ids = []  # Liste til at holde styr på oprettede containere
        
        # Iterér gennem antal pakker
        for i in range(package_count):
            # Generer barcode for hver pakke
            barcode = f"{base_barcode}-{i+1}" if package_count > 1 else base_barcode
            
            # Beregn mængde per pakke
            total_amount = int(data.get('totalAmount', 0))
            amount_per_package = int(data.get('amountPerPackage', total_amount // package_count)) if is_multi_package else total_amount
            
            # Juster sidste pakke hvis der er rest ved division
            if i == package_count - 1 and not is_multi_package and total_amount % package_count != 0:
                amount_per_package += total_amount % package_count
            
            # Indsæt prøven i Sample tabel
            cursor.execute("""
                INSERT INTO Sample (
                    Barcode, 
                    IsUnique, 
                    Type, 
                    Description, 
                    Status, 
                    Amount, 
                    UnitID, 
                    OwnerID, 
                    ReceptionID
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                barcode,
                1 if data.get('hasSerialNumbers') else 0,  # IsUnique flagget
                data.get('sampleType', 'Standard'),
                data.get('description') + (f" (Pakke {i+1})" if is_multi_package and package_count > 1 else ""),
                "På lager",
                amount_per_package,
                data.get('unit'),
                data.get('owner'),
                reception_id
            ))
            
            sample_id = cursor.lastrowid
            
            # Gem den første sample_id for senere reference
            if first_sample_id is None:
                first_sample_id = sample_id
            
            # Bestem lokation for denne pakke
            location_id = None
            if different_locations and package_locations:
                # Find pakkedata for denne pakkenummer
                package_data = next((p for p in package_locations if str(p.get('packageNumber', '')) == str(i+1)), None)
                if package_data:
                    location_id = package_data.get('locationId')
                    print(f"Fandt lokation for pakke {i+1}: {location_id}")
            
            # Brug standard lokation hvis ingen specifik findes
            if not location_id:
                location_id = data.get('storageLocation')
                
            # Sikkerhedstjek - sæt standard lokation hvis stadig ingen
            if not location_id:
                print("ADVARSEL: Ingen lokation fundet, bruger standard lokation 1")
                location_id = "1"
            
            print(f"Bruger lokation {location_id} for pakke {i+1}")
            
            # Indsæt til SampleStorage med den valgte lokation
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
                location_id,
                amount_per_package,
                data.get('expiryDate')
            ))
            
            storage_id = cursor.lastrowid
            
            # Gem den første storage_id for senere reference
            if first_storage_id is None:
                first_storage_id = storage_id
            
            # Opret container hvis create_containers er true
            if create_containers:
                # Brug container-specifik beskrivelse hvis angivet, ellers brug prøvebeskrivelsen
                container_description = data.get('containerDescription', '')
                if not container_description:
                    container_description = data.get('description')
                    if is_multi_package and package_count > 1:
                        container_description += f" (Container {i+1})"
                
                # Hent is_mixed fra container-specifik checkbox
                is_mixed = data.get('containerIsMixed', False)
                
                cursor.execute("""
                    INSERT INTO Container (
                        Description, 
                        IsMixed
                    )
                    VALUES (%s, %s)
                """, (
                    container_description,
                    1 if is_mixed else 0
                ))
                container_id = cursor.lastrowid
                container_ids.append(container_id)
                
                # Kobl container til sample storage
                cursor.execute("""
                    INSERT INTO ContainerSample (
                        SampleStorageID, 
                        ContainerID, 
                        Amount
                    )
                    VALUES (%s, %s, %s)
                """, (
                    storage_id,
                    container_id,
                    amount_per_package
                ))
                
                # Log oprettelse af container i History
                cursor.execute("""
                    INSERT INTO History (
                        Timestamp, 
                        ActionType, 
                        UserID, 
                        SampleID, 
                        Notes
                    )
                    VALUES (NOW(), %s, %s, %s, %s)
                """, (
                    'Container oprettet',
                    user_id,
                    sample_id,
                    f"Container {container_id} oprettet med beskrivelse: {container_description}"
                ))
        
        # Håndter serienumre hvis relevant
        if data.get('hasSerialNumbers') and data.get('serialNumbers'):
            serial_numbers = data.get('serialNumbers')
            for i, serial_number in enumerate(serial_numbers):
                cursor.execute("""
                    INSERT INTO SampleSerialNumber (
                        SampleID, 
                        SerialNumber
                    )
                    VALUES (%s, %s)
                """, (
                    first_sample_id,
                    serial_number
                ))
        
        # Log aktiviteten i History tabellen
        cursor.execute("""
            INSERT INTO History (
                Timestamp, 
                ActionType, 
                UserID, 
                SampleID, 
                Notes
            )
            VALUES (NOW(), %s, %s, %s, %s)
        """, (
            'Modtaget',
            user_id,
            first_sample_id,
            f"Prøve(r) registreret: {package_count} pakke(r) - total mængde: {data.get('totalAmount')}"
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        # Returner relevant data
        response_data = {
            'success': True, 
            'sample_id': f"PRV-{first_sample_id}", 
            'reception_id': reception_id,
            'package_count': package_count
        }
        
        if create_containers and container_ids:
            response_data['container_ids'] = container_ids
            
        return jsonify(response_data)
    except Exception as e:
        print(f"API error: {e}")
        import traceback
        traceback.print_exc()
        mysql.connection.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/createTest', methods=['POST'])
def api_create_test():
    try:
        data = request.json
        cursor = mysql.connection.cursor()
        
        # Få den aktuelle bruger
        current_user = get_current_user()
        user_id = current_user['UserID']
        
        # Brug det angivne test-nummer direkte
        test_type = data.get('type', '')
        
        # Test nummer format: T1234.5, T2345.6, osv.
        test_number = f"T{test_type}"
        
        # Generer test-navn baseret på type
        test_name = ""
        if "1234.5" in test_type:
            test_name = "Tryk Test"
        elif "2345.6" in test_type:
            test_name = "Termisk Test"
        elif "3456.7" in test_type:
            test_name = "Holdbarhed Test"
        else:
            test_name = f"Test {test_type.upper()}"
        
        # Opret testen
        cursor.execute("""
            INSERT INTO Test (TestNo, TestName, Description, CreatedDate, UserID)
            VALUES (%s, %s, %s, NOW(), %s)
        """, (
            test_number,
            test_name,
            data.get('description', ''),
            user_id
        ))
        
        test_id = cursor.lastrowid
        
        # Tilføj prøver til testen
        if data.get('samples'):
            samples_added = 0
            
            for sample_idx, sample_data in enumerate(data.get('samples')):
                sample_id = sample_data.get('id')
                amount = int(sample_data.get('amount', 1))
                
                for i in range(amount):
                    # Generer unikt identifikations-id for test sample
                    # Tilføj tidsstempel for at sikre unikhed
                    timestamp = int(datetime.now().timestamp() * 1000)
                    base_identifier = f"{test_number}_{samples_added + 1}"
                    test_sample_id = f"{base_identifier}"
                    
                    # Tjek om denne identifier allerede eksisterer
                    cursor.execute("""
                        SELECT COUNT(*) FROM TestSample 
                        WHERE GeneratedIdentifier = %s
                    """, (test_sample_id,))
                    
                    count = cursor.fetchone()[0]
                    
                    # Hvis den allerede eksisterer, tilføj et unikt suffix
                    if count > 0:
                        test_sample_id = f"{base_identifier}_{timestamp % 1000}"
                    
                    cursor.execute("""
                        INSERT INTO TestSample (SampleID, TestID, TestIteration, GeneratedIdentifier)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        sample_id,
                        test_id,
                        samples_added + 1,
                        test_sample_id
                    ))
                    
                    # Reducer mængden på lager
                    cursor.execute("""
                        UPDATE SampleStorage 
                        SET AmountRemaining = AmountRemaining - 1
                        WHERE SampleID = %s AND AmountRemaining > 0
                        LIMIT 1
                    """, (sample_id,))
                    
                    samples_added += 1
        
        # Log aktiviteten
        cursor.execute("""
            INSERT INTO History (Timestamp, ActionType, UserID, TestID, Notes)
            VALUES (NOW(), %s, %s, %s, %s)
        """, (
            'Test oprettet',
            user_id,
            test_id,
            f"Test {test_number} oprettet af {current_user['Name']}"
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'success': True, 'test_id': test_number})
    except Exception as e:
        print(f"API error ved oprettelse af test: {e}")
        mysql.connection.rollback()
        cursor.close()
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
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/completeTest/<test_id>', methods=['POST'])
def api_complete_test(test_id):
    try:
        cursor = mysql.connection.cursor()
        
        # Hent aktuel bruger
        current_user = get_current_user()
        user_id = current_user['UserID']
        
        # Prøv at konvertere til heltal hvis det er et tal
        try:
            test_id_int = int(test_id)
            # Hvis det er et heltal, søg på TestID
            cursor.execute("SELECT TestID, TestNo FROM Test WHERE TestID = %s", (test_id_int,))
        except ValueError:
            # Hvis det ikke er et heltal, søg på TestNo
            cursor.execute("SELECT TestID, TestNo FROM Test WHERE TestNo = %s", (test_id,))
        
        test_data = cursor.fetchone()
        
        if not test_data:
            return jsonify({'error': 'Test ikke fundet'}), 404
        
        actual_test_id = test_data[0]
        test_no = test_data[1]
        
        # Da vi ikke har Status eller CompletedDate kolonner, kan vi ikke markere testen som afsluttet i databasen
        # Vi vil blot logge handlingen i History-tabellen
        
        # Log aktiviteten
        cursor.execute("""
            INSERT INTO History (Timestamp, ActionType, UserID, TestID, Notes)
            VALUES (NOW(), %s, %s, %s, %s)
        """, (
            'Test afsluttet',
            user_id,
            actual_test_id,
            f"Test {test_no} afsluttet af {current_user['Name']}"
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'success': True, 'test_id': test_no})
    except Exception as e:
        print(f"API error: {e}")
        import traceback
        traceback.print_exc()
        mysql.connection.rollback()
        if 'cursor' in locals():
            cursor.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/testDetails/<test_id>')
def api_test_details(test_id):
    try:
        cursor = mysql.connection.cursor()
        
        # Tjek om test_id er et heltal eller en streng
        try:
            test_id_int = int(test_id)
            # Hvis det er et heltal, søg på TestID
            cursor.execute("""
                SELECT t.TestID, t.TestNo, t.TestName, t.Description, t.CreatedDate, u.Name as UserName
                FROM Test t 
                JOIN User u ON t.UserID = u.UserID
                WHERE t.TestID = %s
            """, (test_id_int,))
        except ValueError:
            # Hvis det ikke er et heltal, søg på TestNo
            cursor.execute("""
                SELECT t.TestID, t.TestNo, t.TestName, t.Description, t.CreatedDate, u.Name as UserName
                FROM Test t 
                JOIN User u ON t.UserID = u.UserID
                WHERE t.TestNo = %s
            """, (test_id,))
        
        test_data = cursor.fetchone()
        
        if not test_data:
            return jsonify({'error': 'Test ikke fundet'}), 404
        
        actual_test_id = test_data[0]
        
        # Tjek om testen er afsluttet
        cursor.execute("""
            SELECT COUNT(*) FROM History 
            WHERE TestID = %s AND ActionType = 'Test afsluttet'
        """, (actual_test_id,))
        
        is_completed = cursor.fetchone()[0] > 0
        
        if is_completed:
            return jsonify({'error': 'Testen er afsluttet og ikke længere aktiv'}), 404
        
        # Byg testdata
        test = {
            'TestID': test_data[0],
            'TestNo': test_data[1],
            'TestName': test_data[2],
            'Description': test_data[3],
            'CreatedDate': test_data[4].strftime('%d. %b %Y') if test_data[4] else 'Ukendt',
            'UserName': test_data[5],
            'Samples': []
        }
        
        # Hent prøver i testen
        cursor.execute("""
            SELECT ts.TestSampleID, ts.GeneratedIdentifier, s.Description, s.SampleID, ts.SampleID as OriginalSampleID
            FROM TestSample ts
            JOIN Sample s ON ts.SampleID = s.SampleID
            WHERE ts.TestID = %s
        """, (actual_test_id,))
        
        samples_data = cursor.fetchall()
        
        for sample in samples_data:
            test['Samples'].append({
                'TestSampleID': sample[0],
                'GeneratedIdentifier': sample[1],
                'Description': sample[2],
                'SampleID': sample[3],
                'OriginalSampleID': sample[4]
            })
        
        # Returner resultatet
        cursor.close()
        return jsonify({'test': test})
    except Exception as e:
        print(f"API error ved testDetails: {e}")
        if 'cursor' in locals():
            cursor.close()
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
                COALESCE(ct.TypeName, 'Standard') as TypeName,
                COUNT(cs.ContainerSampleID) as sample_count,
                SUM(COALESCE(cs.Amount, 0)) as total_items,
                c.ContainerStatus
            FROM Container c
            LEFT JOIN ContainerType ct ON c.ContainerTypeID = ct.ContainerTypeID
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

@app.route('/api/disposeSample', methods=['POST'])
def api_dispose_sample():
    try:
        data = request.json
        test_sample_id = data.get('testSampleId')
        
        if not test_sample_id:
            return jsonify({'error': 'Manglende test sample ID'}), 400
        
        cursor = mysql.connection.cursor()
        
        # Hent aktuel bruger
        current_user = get_current_user()
        user_id = current_user['UserID']
        
        # Hent test sample information
        cursor.execute("""
            SELECT ts.SampleID, ts.TestID, t.TestNo, s.Description
            FROM TestSample ts
            JOIN Test t ON ts.TestID = t.TestID
            JOIN Sample s ON ts.SampleID = s.SampleID
            WHERE ts.TestSampleID = %s
        """, (test_sample_id,))
        
        sample_data = cursor.fetchone()
        
        if not sample_data:
            return jsonify({'error': 'Test sample ikke fundet'}), 404
        
        sample_id, test_id, test_no, description = sample_data
        
        # Opret kassation for test sample
        cursor.execute("""
            INSERT INTO Disposal (SampleID, UserID, DisposalDate, AmountDisposed, Notes, TestSampleID)
            VALUES (%s, %s, NOW(), %s, %s, %s)
        """, (
            sample_id,
            user_id,
            1,  # Mængde er altid 1 for test samples
            f"Test sample {test_sample_id} kasseret",
            test_sample_id
        ))
        
        # Opdater test sample status
        cursor.execute("""
            UPDATE TestSample
            SET Status = 'Kasseret', DisposalDate = NOW()
            WHERE TestSampleID = %s
        """, (test_sample_id,))
        
        # Log aktiviteten
        cursor.execute("""
            INSERT INTO History (Timestamp, ActionType, UserID, TestID, SampleID, Notes)
            VALUES (NOW(), %s, %s, %s, %s, %s)
        """, (
            'Test sample kasseret',
            user_id,
            test_id,
            sample_id,
            f"Test sample kasseret: {test_no} - {description}"
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"API error: {e}")
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/disposeAllTestSamples', methods=['POST'])
def api_dispose_all_test_samples():
    try:
        data = request.json
        test_id = data.get('testId')
        
        print(f"Modtaget request med data: {data}")
        
        if not test_id:
            return jsonify({'error': 'Manglende test ID'}), 400
        
        cursor = mysql.connection.cursor()
        
        # Hent aktuel bruger
        current_user = get_current_user()
        user_id = current_user['UserID']
        
        # Hent test information
        cursor.execute("""
            SELECT TestNo FROM Test WHERE TestID = %s
        """, (test_id,))
        
        test_data = cursor.fetchone()
        if not test_data:
            return jsonify({'error': 'Test ikke fundet'}), 404
        
        test_no = test_data[0]
        
        # Hent alle aktive test samples
        cursor.execute("""
            SELECT ts.TestSampleID, ts.SampleID, s.Description
            FROM TestSample ts
            JOIN Sample s ON ts.SampleID = s.SampleID
            WHERE ts.TestID = %s
        """, (test_id,))
        
        test_samples = cursor.fetchall()
        
        if not test_samples:
            return jsonify({'success': True, 'message': 'Ingen test samples fundet'}), 200
        
        # Log aktiviteten
        cursor.execute("""
            INSERT INTO History (Timestamp, ActionType, UserID, TestID, Notes)
            VALUES (NOW(), %s, %s, %s, %s)
        """, (
            'Alle test samples kasseret',
            user_id,
            test_id,
            f"Alle prøver kasseret fra test {test_no} ({len(test_samples)} prøver)"
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'success': True, 'count': len(test_samples)})
    except Exception as e:
        print(f"API error ved disposeAllTestSamples: {e}")
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/containers')
def containers():
    try:
        cursor = mysql.connection.cursor()
        
        # Simpel forespørgsel for at hente containere
        cursor.execute("""
            SELECT 
                c.ContainerID,
                c.Description,
                c.IsMixed,
                'Standard' as TypeName,  # Default værdi hvis ContainerType ikke findes
                'Aktiv' as Status,       # Default værdi
                COUNT(cs.ContainerSampleID) as sample_count,
                SUM(COALESCE(cs.Amount, 0)) as total_items
            FROM Container c
            LEFT JOIN ContainerSample cs ON c.ContainerID = cs.ContainerID
            GROUP BY c.ContainerID
            ORDER BY c.ContainerID DESC
        """)
        
        containers_data = cursor.fetchall()
        containers = []
        
        for container in containers_data:
            containers.append({
                "ContainerID": container[0],
                "Description": container[1],
                "IsMixed": "Ja" if container[2] else "Nej",
                "TypeName": container[3],
                "Status": container[4],
                "SampleCount": container[5] or 0,
                "TotalItems": container[6] or 0
            })
        
        # Print containere til debug
        print(f"Fandt {len(containers)} containere")
        
        # Hent container typer hvis tabellen eksisterer
        container_types = []
        try:
            cursor.execute("SHOW TABLES LIKE 'ContainerType'")
            if cursor.fetchone():
                cursor.execute("SELECT ContainerTypeID, TypeName FROM ContainerType ORDER BY TypeName")
                container_types = [dict(ContainerTypeID=row[0], TypeName=row[1]) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Fejl ved hentning af container typer: {e}")
            
        # Hvis ingen typer findes, tilføj en standard type
        if not container_types:
            container_types = [
                {"ContainerTypeID": 1, "TypeName": "Standard"}
            ]
        
        # Hent aktive prøver til "Tilføj prøve" funktionen
        cursor.execute("""
            SELECT 
                s.SampleID,
                CONCAT('PRV-', s.SampleID) as SampleIDFormatted,
                s.Description,
                ss.AmountRemaining,
                u.UnitName as Unit
            FROM Sample s
            JOIN SampleStorage ss ON s.SampleID = ss.SampleID
            JOIN Unit u ON s.UnitID = u.UnitID
            WHERE ss.AmountRemaining > 0
            AND s.Status = 'På lager'
            ORDER BY s.SampleID DESC
        """)
        
        available_samples = []
        for sample in cursor.fetchall():
            available_samples.append({
                "SampleID": sample[0],
                "SampleIDFormatted": sample[1],
                "Description": sample[2],
                "AmountRemaining": sample[3],
                "Unit": sample[4]
            })
        
        cursor.close()
        
        return render_template('sections/containers.html', 
                              containers=containers,
                              container_types=container_types,
                              available_samples=available_samples)
    except Exception as e:
        print(f"Error loading containers: {e}")
        import traceback
        traceback.print_exc()
        return render_template('sections/containers.html', error=f"Fejl ved indlæsning af containere: {str(e)}")


@app.route('/api/container-types')
def get_container_types():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT 
                ContainerTypeID,
                TypeName,
                DefaultCapacity,
                Description,
                (SELECT COUNT(*) FROM Container WHERE ContainerTypeID = ct.ContainerTypeID) as usage_count
            FROM ContainerType ct
            ORDER BY TypeName
        """)
        
        columns = [col[0] for col in cursor.description]
        types = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        
        return jsonify({'types': types})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': 'Database fejl'}), 500


@app.route('/api/containers/available')
def get_available_containers():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT 
                c.ContainerID,
                c.Description,
                c.ContainerCapacity,
                COUNT(cs.ContainerSampleID) as sample_count,
                c.IsMixed
            FROM Container c
            LEFT JOIN ContainerSample cs ON c.ContainerID = cs.ContainerID
            WHERE c.ContainerStatus = 'Aktiv' OR c.ContainerStatus IS NULL
            GROUP BY c.ContainerID
            HAVING c.ContainerCapacity IS NULL OR sample_count < c.ContainerCapacity OR TRUE
        """)
        
        columns = [col[0] for col in cursor.description]
        containers = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        
        return jsonify({'containers': containers})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': 'Database fejl'}), 500


@app.route('/api/containers/<int:container_id>', methods=['DELETE'])
def api_delete_container(container_id):
    try:
        cursor = mysql.connection.cursor()
        
        # Check if container has samples
        cursor.execute("""
            SELECT COUNT(*) FROM ContainerSample
            WHERE ContainerID = %s
        """, (container_id,))
        
        sample_count = cursor.fetchone()[0]
        
        if sample_count > 0:
            cursor.close()
            return jsonify({'success': False, 'error': 'Containeren indeholder prøver og kan ikke slettes. Fjern alle prøver først.'}), 400
        
        # Delete the container
        cursor.execute("""
            DELETE FROM Container
            WHERE ContainerID = %s
        """, (container_id,))
        
        # Log the deletion
        cursor.execute("""
            INSERT INTO History (Timestamp, ActionType, UserID, Notes)
            VALUES (NOW(), %s, %s, %s)
        """, (
            'Container slettet',
            1,  # Default user ID
            f"Container {container_id} slettet"
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/containers/<int:container_id>/samples')
def get_container_samples(container_id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT 
                s.SampleID,
                s.Description,
                cs.Amount,
                sl.LocationName,
                ss.ExpireDate
            FROM ContainerSample cs
            JOIN SampleStorage ss ON cs.SampleStorageID = ss.StorageID
            JOIN Sample s ON ss.SampleID = s.SampleID
            JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
            WHERE cs.ContainerID = %s
        """, (container_id,))
        
        columns = [col[0] for col in cursor.description]
        samples = []
        
        for row in cursor.fetchall():
            sample_dict = dict(zip(columns, row))
            if isinstance(sample_dict['ExpireDate'], datetime):
                sample_dict['ExpireDate'] = sample_dict['ExpireDate'].strftime('%Y-%m-%d')
            samples.append(sample_dict)
        
        cursor.close()
        
        return jsonify({'samples': samples})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': 'Database fejl'}), 500


@app.route('/api/containers/add-sample', methods=['POST'])
def add_sample_to_container():
    try:
        data = request.json
        cursor = mysql.connection.cursor()
        
        # Get the container
        cursor.execute("""
            SELECT IsMixed, ContainerCapacity FROM Container
            WHERE ContainerID = %s
        """, (data.get('containerId'),))
        
        container = cursor.fetchone()
        if not container:
            return jsonify({'success': False, 'error': 'Container findes ikke'}), 404
        
        is_mixed = container[0]
        container_capacity = container[1]
        
        # Check if container allows mixed contents
        if not is_mixed:
            # Check if container already has samples of a different type
            cursor.execute("""
                SELECT DISTINCT s.Type 
                FROM ContainerSample cs
                JOIN SampleStorage ss ON cs.SampleStorageID = ss.StorageID
                JOIN Sample s ON ss.SampleID = s.SampleID
                WHERE cs.ContainerID = %s
            """, (data.get('containerId'),))
            
            existing_types = cursor.fetchall()
            if existing_types:
                # Check if new sample matches existing type
                cursor.execute("""
                    SELECT Type FROM Sample WHERE SampleID = %s
                """, (data.get('sampleId'),))
                
                new_sample_type = cursor.fetchone()
                if new_sample_type and new_sample_type[0] != existing_types[0][0]:
                    return jsonify({
                        'success': False, 
                        'error': 'Containeren tillader ikke blandet indhold. Alle prøver skal være af samme type.'
                    }), 400
        
        # Check container capacity
        if container_capacity:
            cursor.execute("""
                SELECT SUM(Amount) FROM ContainerSample WHERE ContainerID = %s
            """, (data.get('containerId'),))
            
            current_amount = cursor.fetchone()[0] or 0
            if current_amount + data.get('amount', 1) > container_capacity:
                return jsonify({
                    'success': False, 
                    'error': f'Container kapacitet overskredet. Maksimal kapacitet: {container_capacity}, nuværende: {current_amount}'
                }), 400
        
        # Find sample storage ID
        cursor.execute("""
            SELECT StorageID FROM SampleStorage
            WHERE SampleID = %s AND AmountRemaining >= %s
            LIMIT 1
        """, (data.get('sampleId'), data.get('amount', 1)))
        
        storage = cursor.fetchone()
        if not storage:
            return jsonify({'success': False, 'error': 'Utilstrækkelig mængde på lager'}), 400
        
        storage_id = storage[0]
        
        # Add sample to container
        cursor.execute("""
            INSERT INTO ContainerSample (SampleStorageID, ContainerID, Amount)
            VALUES (%s, %s, %s)
        """, (
            storage_id,
            data.get('containerId'),
            data.get('amount', 1)
        ))
        
        # Log the action
        cursor.execute("""
            INSERT INTO History (Timestamp, ActionType, UserID, SampleID, Notes)
            VALUES (NOW(), %s, %s, %s, %s)
        """, (
            'Tilføjet til container',
            1,  # Default user ID
            data.get('sampleId'),
            f"Prøve tilføjet til Container {data.get('containerId')}"
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/test-db')
def test_db():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        return f"Database connection working: {result}"
    except Exception as e:
        return f"Database error: {str(e)}"    


@app.route('/admin/db-tables')
def db_tables():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        table_contents = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            table_contents[table_name] = {
                'columns': columns,
                'rows': rows
            }
        
        cursor.close()
        return render_template('admin/db_tables.html', tables=tables, table_contents=table_contents)
    except Exception as e:
        return f"Error accessing database: {str(e)}"

@app.route('/api/containers/remove-sample', methods=['POST'])
def remove_sample_from_container():
    try:
        data = request.json
        cursor = mysql.connection.cursor()
        
        # Find the container sample
        cursor.execute("""
            SELECT cs.ContainerSampleID, cs.Amount, s.SampleID
            FROM ContainerSample cs
            JOIN SampleStorage ss ON cs.SampleStorageID = ss.StorageID
            JOIN Sample s ON ss.SampleID = s.SampleID
            WHERE cs.ContainerID = %s AND s.SampleID = %s
            LIMIT 1
        """, (data.get('containerId'), data.get('sampleId')))
        
        container_sample = cursor.fetchone()
        if not container_sample:
            return jsonify({'success': False, 'error': 'Prøve ikke fundet i container'}), 404
        
        container_sample_id = container_sample[0]
        current_amount = container_sample[1]
        sample_id = container_sample[2]
        
        # Check amount
        if data.get('amount', 1) > current_amount:
            return jsonify({'success': False, 'error': 'Kan ikke fjerne flere enheder end der er i containeren'}), 400
        
        if data.get('amount', 1) == current_amount:
            # Remove entire record
            cursor.execute("""
                DELETE FROM ContainerSample
                WHERE ContainerSampleID = %s
            """, (container_sample_id,))
        else:
            # Update amount
            cursor.execute("""
                UPDATE ContainerSample
                SET Amount = Amount - %s
                WHERE ContainerSampleID = %s
            """, (data.get('amount', 1), container_sample_id))
        
        # Log the action
        cursor.execute("""
            INSERT INTO History (Timestamp, ActionType, UserID, SampleID, Notes)
            VALUES (NOW(), %s, %s, %s, %s)
        """, (
            'Fjernet fra container',
            1,  # Default user ID
            sample_id,
            f"Prøve fjernet fra Container {data.get('containerId')}"
        ))
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/debug-output')
def debug_output():
    # Test simpel direkte HTML
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Debug Output</title>
        <style>
            body { background-color: yellow; padding: 30px; }
        </style>
    </head>
    <body>
        <h1>Direkte HTML Output Test</h1>
        <p>Hvis du kan se denne tekst med gul baggrund, virker direkte HTML-output.</p>
    </body>
    </html>
    """
@app.route('/test-subdir')
def test_subdir():
    try:
        return render_template('debug/simple.html')
    except Exception as e:
        return f"Fejl ved indlæsning af simple.html fra undermappe: {str(e)}", 500
    
# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)