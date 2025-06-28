from flask import Blueprint, render_template, jsonify, request
from app.services.test_service import TestService
from app.utils.auth import get_current_user
from datetime import datetime

test_bp = Blueprint('test', __name__)

def init_test(blueprint, mysql):
    test_service = TestService(mysql)
    
    @blueprint.route('/testing')
    def testing():
        try:
            # Get active tests
            active_tests = test_service.get_active_tests()
            
            # Get available samples for test creation
            cursor = mysql.connection.cursor()
            cursor.execute("""
                SELECT 
                    s.SampleID, 
                    s.Description, 
                    s.PartNumber,
                    COALESCE(SUM(ss.AmountRemaining), s.Amount, 1) as AmountAvailable,
                    sl.LocationName,
                    s.Status
                FROM Sample s
                LEFT JOIN SampleStorage ss ON s.SampleID = ss.SampleID
                LEFT JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
                WHERE s.Status = 'In Storage'
                GROUP BY s.SampleID, s.Description, s.PartNumber, sl.LocationName, s.Status, s.Amount
                HAVING AmountAvailable > 0
                ORDER BY s.Description
            """)
            
            samples_data = cursor.fetchall()
            samples = []
            for sample in samples_data:
                samples.append({
                    "SampleID": sample[0],
                    "SampleIDFormatted": f"SMP-{sample[0]}",
                    "Description": sample[1],
                    "PartNumber": sample[2] or "",
                    "AmountAvailable": sample[3],
                    "LocationName": sample[4] or "Unknown",
                    "Status": sample[5]
                })
            
            # Get users
            cursor.execute("SELECT UserID, Name FROM User ORDER BY Name")
            users = [dict(UserID=row[0], Name=row[1]) for row in cursor.fetchall()]
            
            cursor.close()
            
            return render_template('sections/testing.html', 
                                active_tests=active_tests, 
                                samples=samples,
                                users=users)
        except Exception as e:
            print(f"Error loading testing: {e}")
            import traceback
            traceback.print_exc()
            return render_template('sections/testing.html', 
                                error="Error loading test administration")
    
    @blueprint.route('/api/tests/create', methods=['POST'])
    def create_test():
        try:
            data = request.json
            user_id = get_current_user()['UserID']
            
            result = test_service.create_test(data, user_id)
            return jsonify(result)
            
        except Exception as e:
            print(f"Error creating test: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to create test: {str(e)}'
            }), 500
    
    @blueprint.route('/api/tests/create-iteration', methods=['POST'])
    def create_test_iteration():
        try:
            data = request.json
            user_id = get_current_user()['UserID']
            base_test_no = data.get('base_test_no')
            
            if not base_test_no:
                return jsonify({
                    'success': False,
                    'error': 'Base test number is required'
                }), 400
            
            result = test_service.create_test_iteration(base_test_no, data, user_id)
            return jsonify(result)
            
        except Exception as e:
            print(f"Error creating test iteration: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to create test iteration: {str(e)}'
            }), 500
    
    @blueprint.route('/api/tests/<int:test_id>/add-samples', methods=['POST'])
    def add_samples_to_test(test_id):
        try:
            data = request.json
            user_id = get_current_user()['UserID']
            sample_assignments = data.get('samples', [])
            
            result = test_service.add_samples_to_test(test_id, sample_assignments, user_id)
            return jsonify(result)
            
        except Exception as e:
            print(f"Error adding samples to test: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to add samples to test: {str(e)}'
            }), 500
    
    @blueprint.route('/api/tests/<int:test_id>/samples', methods=['GET'])
    def get_test_samples(test_id):
        try:
            samples = test_service.get_test_samples(test_id)
            return jsonify({
                'success': True,
                'samples': samples
            })
            
        except Exception as e:
            print(f"Error getting test samples: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to get test samples: {str(e)}'
            }), 500
    
    @blueprint.route('/api/tests/samples/<int:usage_id>/remove', methods=['POST'])
    def remove_sample_from_test(usage_id):
        try:
            data = request.json
            user_id = get_current_user()['UserID']
            
            action = data.get('action')  # 'return' or 'transfer'
            amount = data.get('amount')
            target_test_id = data.get('target_test_id')
            notes = data.get('notes', '')
            
            if not action or not amount:
                return jsonify({
                    'success': False,
                    'error': 'Action and amount are required'
                }), 400
            
            if action == 'transfer' and not target_test_id:
                return jsonify({
                    'success': False,
                    'error': 'Target test ID is required for transfer'
                }), 400
            
            result = test_service.remove_sample_from_test(
                usage_id, action, amount, user_id, target_test_id, notes
            )
            return jsonify(result)
            
        except Exception as e:
            print(f"Error removing sample from test: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to remove sample from test: {str(e)}'
            }), 500
    
    @blueprint.route('/api/tests/<int:test_id>/status', methods=['PUT'])
    def update_test_status(test_id):
        try:
            data = request.json
            user_id = get_current_user()['UserID']
            new_status = data.get('status')
            
            if not new_status:
                return jsonify({
                    'success': False,
                    'error': 'Status is required'
                }), 400
            
            valid_statuses = ['Created', 'In Progress', 'Completed', 'Archived']
            if new_status not in valid_statuses:
                return jsonify({
                    'success': False,
                    'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                }), 400
            
            result = test_service.update_test_status(test_id, new_status, user_id)
            return jsonify(result)
            
        except Exception as e:
            print(f"Error updating test status: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to update test status: {str(e)}'
            }), 500
    
    @blueprint.route('/api/tests/<int:test_id>/complete', methods=['POST'])
    def complete_test(test_id):
        try:
            data = request.json
            user_id = get_current_user()['UserID']
            sample_completions = data.get('sample_completions', [])
            
            result = test_service.complete_test(test_id, sample_completions, user_id)
            return jsonify(result)
            
        except Exception as e:
            print(f"Error completing test: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to complete test: {str(e)}'
            }), 500
    
    @blueprint.route('/api/samples/<int:sample_id>/test-history', methods=['GET'])
    def get_sample_test_history(sample_id):
        try:
            history = test_service.get_sample_test_history(sample_id)
            return jsonify({
                'success': True,
                'history': history
            })
            
        except Exception as e:
            print(f"Error getting sample test history: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to get sample test history: {str(e)}'
            }), 500
    
    @blueprint.route('/api/tests/<int:test_id>/details', methods=['GET'])
    def get_test_details(test_id):
        try:
            cursor = mysql.connection.cursor()
            
            # Get test info
            cursor.execute("""
                SELECT TestID, TestNo, TestName, Description, Status, CreatedDate, UserID
                FROM Test WHERE TestID = %s
            """, (test_id,))
            
            test_result = cursor.fetchone()
            if not test_result:
                return jsonify({
                    'success': False,
                    'error': 'Test not found'
                }), 404
            
            # Get user name
            cursor.execute("SELECT Name FROM User WHERE UserID = %s", (test_result[6],))
            user_result = cursor.fetchone()
            user_name = user_result[0] if user_result else 'Unknown'
            
            test_info = {
                'test_id': test_result[0],
                'test_no': test_result[1],
                'test_name': test_result[2],
                'description': test_result[3],
                'status': test_result[4],
                'created_date': test_result[5],
                'user_name': user_name
            }
            
            # Get samples
            samples = test_service.get_test_samples(test_id)
            
            cursor.close()
            
            return jsonify({
                'success': True,
                'test': test_info,
                'samples': samples
            })
            
        except Exception as e:
            print(f"Error getting test details: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to get test details: {str(e)}'
            }), 500