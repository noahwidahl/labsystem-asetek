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
            
            # Get suppliers
            cursor.execute("SELECT SupplierID, SupplierName FROM Supplier")
            suppliers = [dict(SupplierID=row[0], SupplierName=row[1]) for row in cursor.fetchall()]
            
            # Get users
            cursor.execute("SELECT UserID, Name FROM User")
            users = [dict(UserID=row[0], Name=row[1]) for row in cursor.fetchall()]
            
            # Get units
            cursor.execute("SELECT UnitID, UnitName FROM Unit ORDER BY UnitName")
            units = [dict(UnitID=row[0], UnitName=row[1]) for row in cursor.fetchall()]
            
            # Get locations
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
                                error="Error loading registration form")
    
    @blueprint.route('/storage')
    def storage():
        try:
            samples = sample_service.get_all_samples()
            
            # Convert to format used by template
            samples_for_template = []
            for sample in samples:
                # Get additional information
                cursor = mysql.connection.cursor()
                
                # Get reception date
                cursor.execute("SELECT ReceivedDate FROM Reception WHERE ReceptionID = %s", (sample.reception_id,))
                reception_result = cursor.fetchone()
                reception_date = reception_result[0] if reception_result else None
                
                # Get unit
                cursor.execute("SELECT UnitName FROM Unit WHERE UnitID = %s", (sample.unit_id,))
                unit_result = cursor.fetchone()
                unit = unit_result[0] if unit_result else "pcs"
                
                # Get location
                cursor.execute("""
                    SELECT sl.LocationName 
                    FROM SampleStorage ss 
                    JOIN StorageLocation sl ON ss.LocationID = sl.LocationID 
                    WHERE ss.SampleID = %s
                """, (sample.id,))
                location_result = cursor.fetchone()
                location = location_result[0] if location_result else "Unknown"
                
                cursor.close()
                
                samples_for_template.append({
                    "ID": f"SMP-{sample.id}",
                    "Description": sample.description,
                    "Reception": reception_date.strftime('%Y-%m-%d') if reception_date else "Unknown",
                    "Amount": f"{sample.amount} {unit}",
                    "Location": location,
                    "Registered": reception_date.strftime('%Y-%m-%d %H:%M') if reception_date else "Unknown",
                    "Status": sample.status
                })
            
            return render_template('sections/storage.html', samples=samples_for_template)
        except Exception as e:
            print(f"Error loading storage: {e}")
            return render_template('sections/storage.html', error="Error loading storage")
    
    @blueprint.route('/api/samples', methods=['POST'])
    def create_sample():
        try:
            data = request.json
            
            # Validate input
            validation_result = validate_sample_data(data)
            if not validation_result.get('valid', False):
                return jsonify({
                    'success': False, 
                    'error': validation_result.get('error'),
                    'field': validation_result.get('field')
                }), 400
            
            # Get current user
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            # Create the sample via service
            result = sample_service.create_sample(data, user_id)
            
            return jsonify(result)
        except Exception as e:
            print(f"API error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500