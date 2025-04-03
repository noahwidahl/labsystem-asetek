from flask import Blueprint, render_template, jsonify, request
from app.services.container_service import ContainerService
from app.utils.auth import get_current_user
from app.utils.validators import validate_container_data

container_bp = Blueprint('container', __name__)

def init_container(blueprint, mysql):
    container_service = ContainerService(mysql)
    
    @blueprint.route('/containers')
    def containers():
        try:
            # Hent containere
            containers = container_service.get_all_containers()
            
            # Convert to format used by template
            containers_for_template = []
            for container in containers:
                container_dict = container.to_dict()
                container_dict['TypeName'] = getattr(container, 'type_name', 'Standard')
                container_dict['SampleCount'] = getattr(container, 'sample_count', 0)
                container_dict['TotalItems'] = getattr(container, 'total_items', 0)
                container_dict['LocationName'] = getattr(container, 'location_name', 'Unknown')
                containers_for_template.append(container_dict)
            
            cursor = mysql.connection.cursor()
            
            # Get container types
            cursor.execute("SELECT ContainerTypeID, TypeName, Description, DefaultCapacity FROM ContainerType")
            type_columns = [col[0] for col in cursor.description]
            container_types = [dict(zip(type_columns, row)) for row in cursor.fetchall()]
            
            # Get storage locations for dropdown
            cursor.execute("""
                SELECT LocationID, LocationName, Rack, Section, Shelf
                FROM storagelocation
                ORDER BY Rack, Section, Shelf
            """)
            location_columns = [col[0] for col in cursor.description]
            locations = [dict(zip(location_columns, row)) for row in cursor.fetchall()]
            
            # Get active samples for the "Add sample" function
            cursor.execute("""
                SELECT 
                    s.SampleID,
                    CONCAT('SMP-', s.SampleID) as SampleIDFormatted,
                    s.Description,
                    ss.AmountRemaining,
                    u.UnitName as Unit
                FROM Sample s
                JOIN SampleStorage ss ON s.SampleID = ss.SampleID
                JOIN Unit u ON s.UnitID = u.UnitID
                WHERE ss.AmountRemaining > 0
                AND s.Status = 'In Storage'
                ORDER BY s.SampleID DESC
            """)
            
            columns = [col[0] for col in cursor.description]
            available_samples = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            cursor.close()
            
            return render_template('sections/containers.html', 
                                containers=containers_for_template,
                                container_types=container_types,
                                available_samples=available_samples,
                                locations=locations)
        except Exception as e:
            print(f"Error loading containers: {e}")
            import traceback
            traceback.print_exc()
            return render_template('sections/containers.html', 
                                error=f"Error loading containers: {str(e)}",
                                containers=[],
                                container_types=[],
                                available_samples=[],
                                locations=[])
    
    @blueprint.route('/api/containers/<int:container_id>/location')
    def get_container_location(container_id):
        try:
            # Get container location
            location = container_service.get_container_location(container_id)
            
            return jsonify({'success': True, 'location': location})
        except Exception as e:
            print(f"API error when fetching container location: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500

    @blueprint.route('/api/containers', methods=['POST'])
    def create_container():
        try:
            data = request.json
            
            # Validation of input
            validation_result = validate_container_data(data)
            if not validation_result.get('valid', False):
                return jsonify({
                    'success': False, 
                    'error': validation_result.get('error'),
                    'field': validation_result.get('field')
                }), 400
            
            # Get current user
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            # Create container via service
            result = container_service.create_container(data, user_id)
            
            return jsonify(result)
        except Exception as e:
            print(f"API error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @blueprint.route('/api/containers/available')
    def get_available_containers():
        try:
            # Get containers that can hold samples
            containers = container_service.get_available_containers()
            
            return jsonify({'success': True, 'containers': containers})
        except Exception as e:
            print(f"API error when fetching available containers: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
            
    @blueprint.route('/api/containers/types')
    def get_container_types():
        try:
            cursor = mysql.connection.cursor()
            
            # Get container types
            cursor.execute("SELECT ContainerTypeID, TypeName, Description, DefaultCapacity FROM ContainerType")
            type_columns = [col[0] for col in cursor.description]
            container_types = [dict(zip(type_columns, row)) for row in cursor.fetchall()]
            
            cursor.close()
            
            return jsonify({'success': True, 'types': container_types})
        except Exception as e:
            print(f"API error when fetching container types: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
            
    @blueprint.route('/api/containers/add-sample', methods=['POST'])
    def add_sample_to_container():
        try:
            data = request.json
            
            # Validation of input
            if not data.get('containerId'):
                return jsonify({'success': False, 'error': 'Container ID missing'}), 400
                
            if not data.get('sampleId'):
                return jsonify({'success': False, 'error': 'Sample ID missing'}), 400
                
            # Get current user
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            # Add sample to container via service
            result = container_service.add_sample_to_container(
                data.get('containerId'),
                data.get('sampleId'),
                data.get('amount', 1),
                user_id,
                data.get('force_add', False)  # Added force_add parameter to bypass capacity check
            )
            
            return jsonify(result)
        except Exception as e:
            print(f"API error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @blueprint.route('/api/containers/<int:container_id>', methods=['DELETE'])
    def delete_container(container_id):
        try:
            # Get current user
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            # Delete container via service
            result = container_service.delete_container(container_id, user_id)
            
            return jsonify(result)
        except Exception as e:
            print(f"API error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
            
    @blueprint.route('/api/containers/<int:container_id>', methods=['GET'])
    def get_container_details(container_id):
        try:
            # Connect to database directly for this complex query
            cursor = mysql.connection.cursor()
            
            # Get container details
            cursor.execute("""
                SELECT 
                    c.ContainerID,
                    c.Description,
                    c.ContainerTypeID,
                    c.IsMixed,
                    c.ContainerCapacity,
                    ct.TypeName,
                    'Active' as Status
                FROM container c
                LEFT JOIN containertype ct ON c.ContainerTypeID = ct.ContainerTypeID
                WHERE c.ContainerID = %s
            """, (container_id,))
            
            container_result = cursor.fetchone()
            if not container_result:
                return jsonify({'success': False, 'error': 'Container not found'}), 404
            
            # Convert to dict with column names
            container_cols = [col[0] for col in cursor.description]
            container = dict(zip(container_cols, container_result))
            
            # Get samples in this container
            cursor.execute("""
                SELECT 
                    s.SampleID,
                    s.Description,
                    cs.Amount,
                    sl.LocationName,
                    ss.ExpireDate
                FROM containersample cs
                JOIN samplestorage ss ON cs.SampleStorageID = ss.StorageID
                JOIN sample s ON ss.SampleID = s.SampleID
                LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
                WHERE cs.ContainerID = %s
            """, (container_id,))
            
            samples_result = cursor.fetchall()
            samples_cols = [col[0] for col in cursor.description]
            samples = [dict(zip(samples_cols, row)) for row in samples_result]
            
            # Get container history
            cursor.execute("""
                SELECT 
                    h.Timestamp,
                    h.ActionType,
                    h.Notes,
                    u.Name as UserName
                FROM history h
                LEFT JOIN user u ON h.UserID = u.UserID
                WHERE h.Notes LIKE %s
                ORDER BY h.Timestamp DESC
                LIMIT 20
            """, (f"%Container {container_id}%",))
            
            history_result = cursor.fetchall()
            history_cols = [col[0] for col in cursor.description]
            history = [dict(zip(history_cols, row)) for row in history_result]
            
            cursor.close()
            
            return jsonify({
                'success': True,
                'container': container,
                'samples': samples,
                'history': history
            })
        except Exception as e:
            print(f"API error getting container details: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500