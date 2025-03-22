from flask import Blueprint, render_template, jsonify, request
from app.services.sample_service import SampleService
from app.utils.auth import get_current_user
from app.utils.validators import validate_sample_data

sample_bp = Blueprint('sample', __name__)

def init_sample(blueprint, mysql):
    sample_service = SampleService(mysql)
    
    @blueprint.route('/register')
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
    
    @blueprint.route('/storage')
    def storage():
        try:
            samples = sample_service.get_all_samples()
            
            # Konverter til format anvendt af template
            samples_for_template = []
            for sample in samples:
                # Hent yderligere information
                cursor = mysql.connection.cursor()
                
                # Hent modtagelsesdato
                cursor.execute("SELECT ReceivedDate FROM Reception WHERE ReceptionID = %s", (sample.reception_id,))
                reception_result = cursor.fetchone()
                modtagelse_dato = reception_result[0] if reception_result else None
                
                # Hent enhed
                cursor.execute("SELECT UnitName FROM Unit WHERE UnitID = %s", (sample.unit_id,))
                unit_result = cursor.fetchone()
                enhed = unit_result[0] if unit_result else "stk"
                
                # Hent placering
                cursor.execute("""
                    SELECT sl.LocationName 
                    FROM SampleStorage ss 
                    JOIN StorageLocation sl ON ss.LocationID = sl.LocationID 
                    WHERE ss.SampleID = %s
                """, (sample.id,))
                location_result = cursor.fetchone()
                placering = location_result[0] if location_result else "Ukendt"
                
                cursor.close()
                
                samples_for_template.append({
                    "ID": f"SMP-{sample.id}",
                    "Beskrivelse": sample.description,
                    "Modtagelse": modtagelse_dato.strftime('%Y-%m-%d') if modtagelse_dato else "Ukendt",
                    "Antal": f"{sample.amount} {enhed}",
                    "Placering": placering,
                    "Registreret": modtagelse_dato.strftime('%Y-%m-%d %H:%M') if modtagelse_dato else "Ukendt",
                    "Status": sample.status
                })
            
            return render_template('sections/storage.html', samples=samples_for_template)
        except Exception as e:
            print(f"Error loading storage: {e}")
            return render_template('sections/storage.html', error="Fejl ved indlæsning af lager")
    
    @blueprint.route('/api/samples', methods=['POST'])
    def create_sample():
        try:
            data = request.json
            
            # Validering af input
            validation_result = validate_sample_data(data)
            if not validation_result.get('valid', False):
                return jsonify({
                    'success': False, 
                    'error': validation_result.get('error'),
                    'field': validation_result.get('field')
                }), 400
            
            # Hent aktuel bruger
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            # Opret prøven via service
            result = sample_service.create_sample(data, user_id)
            
            return jsonify(result)
        except Exception as e:
            print(f"API error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500