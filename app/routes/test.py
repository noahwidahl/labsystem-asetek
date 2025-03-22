from flask import Blueprint, render_template, jsonify, request
from app.services.test_service import TestService
from app.utils.auth import get_current_user
from app.utils.validators import validate_test_data

test_bp = Blueprint('test', __name__)

def init_test(blueprint, mysql):
    test_service = TestService(mysql)
    
    @blueprint.route('/testing')
    def testing():
        try:
            # Hent aktive tests
            active_tests = test_service.get_active_tests()
            
            # Konverter til format anvendt af template
            active_tests_for_template = []
            for test in active_tests:
                active_tests_for_template.append({
                    "TestID": test.id,
                    "TestNo": test.test_no,
                    "TestName": test.test_name or f"Test {test.id}",
                    "Description": test.description or "",
                    "UserName": getattr(test, 'user_name', 'Ukendt'),
                    "CreatedDate": test.created_date.strftime('%d. %B %Y') if test.created_date else "Ukendt",
                    "sample_count": getattr(test, 'sample_count', 0)
                })
            
            # Hent tilgængelige prøver
            cursor = mysql.connection.cursor()
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
                    "SampleIDFormatted": f"SMP-{sample[0]}",
                    "Description": sample[1],
                    "AmountRemaining": sample[2],
                    "LocationName": sample[3]
                })
            
            # Hent brugere
            cursor.execute("SELECT UserID, Name FROM User")
            users = [dict(UserID=row[0], Name=row[1]) for row in cursor.fetchall()]
            
            cursor.close()
            
            return render_template('sections/testing.html', 
                                active_tests=active_tests_for_template, 
                                samples=samples,
                                users=users)
        except Exception as e:
            print(f"Error loading testing: {e}")
            return render_template('sections/testing.html', error="Fejl ved indlæsning af test administration")
    
    @blueprint.route('/api/createTest', methods=['POST'])
    def create_test():
        try:
            data = request.json
            
            # Validering af input
            validation_result = validate_test_data(data)
            if not validation_result.get('valid', False):
                return jsonify({
                    'success': False, 
                    'error': validation_result.get('error'),
                    'field': validation_result.get('field')
                }), 400
            
            # Hent aktuel bruger
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            # Opret test via service
            result = test_service.create_test(data, user_id)
            
            return jsonify(result)
        except Exception as e:
            print(f"API error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @blueprint.route('/api/completeTest/<test_id>', methods=['POST'])
    def complete_test(test_id):
        try:
            # Hent aktuel bruger
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            # Afslut test via service
            result = test_service.complete_test(test_id, user_id)
            
            return jsonify(result)
        except Exception as e:
            print(f"API error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500