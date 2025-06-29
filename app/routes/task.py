from flask import Blueprint, render_template, jsonify, request
from app.services.task_service import TaskService
from app.utils.auth import get_current_user
from datetime import datetime

task_bp = Blueprint('task', __name__)

def init_task(blueprint, mysql):
    task_service = TaskService(mysql)
    
    @blueprint.route('/tasks')
    def tasks_page():
        """
        Render the task management page.
        """
        try:
            cursor = mysql.connection.cursor()
            
            # Get users for assignment dropdowns
            cursor.execute("SELECT UserID, Name FROM user ORDER BY Name")
            users = [dict(UserID=row[0], Name=row[1]) for row in cursor.fetchall()]
            
            cursor.close()
            
            return render_template('sections/tasks.html', users=users)
        except Exception as e:
            print(f"Error loading tasks page: {e}")
            return render_template('sections/tasks.html', error="Error loading task management page")
    
    @blueprint.route('/api/tasks', methods=['GET'])
    def get_tasks():
        """
        Get all tasks with optional filtering.
        """
        try:
            status_filter = request.args.get('status')
            assigned_filter = request.args.get('assigned_to')
            search_term = request.args.get('search')
            
            tasks = task_service.get_all_tasks(
                status_filter=status_filter,
                assigned_filter=assigned_filter,
                search_term=search_term
            )
            
            tasks_data = [task.to_dict() for task in tasks]
            
            return jsonify({
                'success': True,
                'tasks': tasks_data,
                'count': len(tasks_data)
            })
            
        except Exception as e:
            print(f"Error getting tasks: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @blueprint.route('/api/tasks', methods=['POST'])
    def create_task():
        """
        Create a new task.
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400
            
            # Get current user
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            result = task_service.create_task(data, user_id)
            
            if result['success']:
                return jsonify(result), 201
            else:
                return jsonify(result), 400
                
        except Exception as e:
            print(f"Error creating task: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @blueprint.route('/api/tasks/<int:task_id>', methods=['GET'])
    def get_task(task_id):
        """
        Get a specific task by ID with samples and tests.
        """
        try:
            task = task_service.get_task_by_id(task_id)
            
            if not task:
                return jsonify({
                    'success': False,
                    'error': 'Task not found'
                }), 404
            
            # Get task samples and tests
            samples = task_service.get_task_samples(task_id)
            tests = task_service.get_task_tests(task_id)
            
            return jsonify({
                'success': True,
                'task': task.to_dict(),
                'samples': samples,
                'tests': tests
            })
            
        except Exception as e:
            print(f"Error getting task: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @blueprint.route('/api/tasks/<int:task_id>', methods=['PUT'])
    def update_task(task_id):
        """
        Update a task.
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400
            
            # Get current user
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            result = task_service.update_task(task_id, data, user_id)
            
            return jsonify(result)
            
        except Exception as e:
            print(f"Error updating task: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @blueprint.route('/api/tasks/<int:task_id>', methods=['DELETE'])
    def delete_task(task_id):
        """
        Delete a task.
        """
        try:
            # Get current user
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            result = task_service.delete_task(task_id, user_id)
            
            return jsonify(result)
            
        except Exception as e:
            print(f"Error deleting task: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @blueprint.route('/api/tasks/stats')
    def get_task_stats():
        """
        Get task statistics for dashboard.
        """
        try:
            stats = task_service.get_task_statistics()
            
            return jsonify({
                'success': True,
                'stats': stats
            })
            
        except Exception as e:
            print(f"Error getting task statistics: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @blueprint.route('/api/tasks/overview')
    def get_tasks_overview():
        """
        Get task overview with statistics.
        """
        try:
            overviews = task_service.get_task_overview()
            
            return jsonify({
                'success': True,
                'tasks': overviews
            })
            
        except Exception as e:
            print(f"Error getting task overview: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @blueprint.route('/api/tasks/<int:task_id>/overview')
    def get_task_overview(task_id):
        """
        Get detailed overview for a specific task.
        """
        try:
            overview = task_service.get_task_overview(task_id)
            
            if not overview:
                return jsonify({
                    'success': False,
                    'error': 'Task not found'
                }), 404
            
            return jsonify({
                'success': True,
                'task': overview
            })
            
        except Exception as e:
            print(f"Error getting task overview: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @blueprint.route('/api/tasks/<int:task_id>/tests')
    def get_task_tests(task_id):
        """
        Get all tests assigned to a task.
        """
        try:
            tests = task_service.get_task_tests(task_id)
            
            return jsonify({
                'success': True,
                'tests': tests,
                'count': len(tests)
            })
            
        except Exception as e:
            print(f"Error getting task tests: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @blueprint.route('/api/tasks/<int:task_id>/samples')
    def get_task_samples(task_id):
        """
        Get all samples assigned to a task.
        """
        try:
            samples = task_service.get_task_samples(task_id)
            
            return jsonify({
                'success': True,
                'samples': samples,
                'count': len(samples)
            })
            
        except Exception as e:
            print(f"Error getting task samples: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @blueprint.route('/api/tasks/<int:task_id>/assign-sample', methods=['POST'])
    def assign_sample_to_task(task_id):
        """
        Assign a sample to a task.
        """
        try:
            data = request.get_json()
            
            if not data or 'sample_id' not in data:
                return jsonify({
                    'success': False,
                    'error': 'Sample ID is required'
                }), 400
            
            sample_id = data['sample_id']
            purpose = data.get('purpose', '')
            
            # Get current user
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            result = task_service.assign_sample_to_task(task_id, sample_id, user_id, purpose)
            
            return jsonify(result)
            
        except Exception as e:
            print(f"Error assigning sample to task: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @blueprint.route('/api/tasks/<int:task_id>/next-test-number')
    def get_next_test_number(task_id):
        """
        Generate the next test number for a task.
        """
        try:
            test_number = task_service.generate_next_test_number(task_id)
            
            return jsonify({
                'success': True,
                'test_number': test_number
            })
            
        except Exception as e:
            print(f"Error generating test number: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @blueprint.route('/api/samples/available-for-task')
    def get_available_samples_for_task():
        """
        Get samples available for task assignment.
        """
        try:
            task_id = request.args.get('task_id')
            search = request.args.get('search', '')
            
            cursor = mysql.connection.cursor()
            
            # Base query for available samples
            base_conditions = """
                WHERE s.Status = 'In Storage'
                AND (ss.AmountRemaining > 0 OR ss.AmountRemaining IS NULL)
            """
            
            # Exclude samples already assigned to this task
            if task_id:
                base_conditions += f" AND s.SampleID NOT IN (SELECT SampleID FROM tasksample WHERE TaskID = {task_id})"
            
            # Add search conditions if provided
            search_conditions = ""
            search_params = []
            if search:
                search_conditions = """
                    AND (s.Description LIKE %s 
                         OR s.Barcode LIKE %s 
                         OR s.PartNumber LIKE %s
                         OR CONCAT('SMP-', s.SampleID) LIKE %s)
                """
                search_term = f"%{search}%"
                search_params = [search_term, search_term, search_term, search_term]
            
            # Get available samples
            query = f"""
                SELECT 
                    s.SampleID, 
                    s.Description, 
                    s.Barcode,
                    IFNULL(s.PartNumber, '') as PartNumber,
                    ss.AmountRemaining,
                    IFNULL(sl.LocationName, 'Unknown') as LocationName,
                    CASE
                        WHEN un.UnitName IS NULL THEN 'pcs'
                        WHEN LOWER(un.UnitName) = 'stk' THEN 'pcs'
                        ELSE un.UnitName
                    END as Unit
                FROM sample s
                LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
                LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
                LEFT JOIN unit un ON s.UnitID = un.UnitID
                {base_conditions}
                {search_conditions}
                ORDER BY s.SampleID DESC
                LIMIT 50
            """
            
            cursor.execute(query, search_params)
            
            columns = [col[0] for col in cursor.description]
            samples = []
            
            for row in cursor.fetchall():
                sample_dict = dict(zip(columns, row))
                sample_dict['SampleIDFormatted'] = f"SMP-{sample_dict['SampleID']}"
                
                # If AmountRemaining is NULL, set it to 1 as a fallback
                if sample_dict['AmountRemaining'] is None:
                    sample_dict['AmountRemaining'] = 1
                
                samples.append(sample_dict)
            
            cursor.close()
            
            return jsonify({
                'success': True,
                'samples': samples,
                'count': len(samples)
            })
            
        except Exception as e:
            print(f"Error getting available samples: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500