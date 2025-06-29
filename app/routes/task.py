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
    
