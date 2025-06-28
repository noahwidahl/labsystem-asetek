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
            # Use string to avoid %d bytes error
            container_id_str = str(container_id)
            
            # Direct database query for container location
            cursor = mysql.connection.cursor()
            
            query = """
                SELECT 
                    sl.LocationID,
                    sl.LocationName,
                    sl.Rack,
                    sl.Section,
                    sl.Shelf,
                    l.LabName
                FROM container c
                JOIN storagelocation sl ON c.LocationID = sl.LocationID
                JOIN lab l ON sl.LabID = l.LabID
                WHERE c.ContainerID = """ + container_id_str
                
            cursor.execute(query)
            
            location_result = cursor.fetchone()
            
            if not location_result:
                # Try container service as fallback
                location = container_service.get_container_location(container_id)
                return jsonify({'success': True, 'location': location})
            
            # Convert to dict with column names
            location_cols = [col[0] for col in cursor.description]
            location = dict(zip(location_cols, location_result))
            
            cursor.close()
            
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
            
            # Add debug output for frontend
            print(f"DEBUG: API /api/containers/available returning {len(containers)} containers")
            if containers:
                print(f"DEBUG: First container: {containers[0]}")
            
            return jsonify({'success': True, 'containers': containers})
        except Exception as e:
            print(f"API error when fetching available containers: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}, 500)
            
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
            
    @blueprint.route('/api/containers/types/<int:container_type_id>', methods=['DELETE'])
    def delete_container_type(container_type_id):
        try:
            # Get current user
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            # Delete container type via service
            result = container_service.delete_container_type(container_type_id, user_id)
            
            return jsonify(result)
        except Exception as e:
            print(f"API error deleting container type: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
            
    @blueprint.route('/api/locations/<int:location_id>')
    def get_location(location_id):
        try:
            # Use string to avoid %d bytes error
            location_id_str = str(location_id)
            
            # Direct database query for storage location info
            cursor = mysql.connection.cursor()
            
            query = """
                SELECT 
                    sl.LocationID,
                    sl.LocationName,
                    sl.Rack,
                    sl.Section, 
                    sl.Shelf,
                    l.LabName
                FROM storagelocation sl
                JOIN lab l ON sl.LabID = l.LabID
                WHERE sl.LocationID = """ + location_id_str
                
            cursor.execute(query)
            
            location_result = cursor.fetchone()
            
            if not location_result:
                return jsonify({'success': False, 'error': 'Location not found'}), 404
            
            # Convert to dict with column names
            location_cols = [col[0] for col in cursor.description]
            location = dict(zip(location_cols, location_result))
            
            cursor.close()
            
            return jsonify({'success': True, 'location': location})
        except Exception as e:
            print(f"API error getting location details: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
            
    @blueprint.route('/api/locations')
    def get_all_locations():
        try:
            # Direct database query for all storage locations
            cursor = mysql.connection.cursor()
            
            query = """
                SELECT 
                    sl.LocationID,
                    sl.LocationName,
                    sl.Rack,
                    sl.Section, 
                    sl.Shelf,
                    l.LabName
                FROM storagelocation sl
                JOIN lab l ON sl.LabID = l.LabID
                ORDER BY sl.Rack, sl.Section, sl.Shelf
            """
                
            cursor.execute(query)
            
            # Convert to list of dicts with column names
            location_cols = [col[0] for col in cursor.description]
            locations = [dict(zip(location_cols, row)) for row in cursor.fetchall()]
            
            cursor.close()
            
            return jsonify({'success': True, 'locations': locations})
        except Exception as e:
            print(f"API error getting all locations: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
            
    @blueprint.route('/api/basic-locations')
    def get_basic_locations():
        try:
            # Simplified query for just location IDs and names
            cursor = mysql.connection.cursor()
            
            query = """
                SELECT 
                    LocationID,
                    LocationName
                FROM storagelocation
                ORDER BY Rack, Section, Shelf
            """
                
            cursor.execute(query)
            
            # Convert to list of dicts
            location_cols = [col[0] for col in cursor.description]
            locations = [dict(zip(location_cols, row)) for row in cursor.fetchall()]
            
            cursor.close()
            
            return jsonify({'success': True, 'locations': locations})
        except Exception as e:
            print(f"API error getting basic locations: {e}")
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
            # Convert to string to avoid %d bytes error
            container_id_str = str(container_id)
            
            # Connect to database directly for this complex query
            cursor = mysql.connection.cursor()
            
            # Get container details with field name aliasing to match database
            # Use string concatenation to avoid %d format error
            cursor.execute("""
                SELECT 
                    c.ContainerID,
                    c.Description,
                    c.ContainerTypeID,
                    c.IsMixed,
                    c.ContainerCapacity,
                    ct.TypeName,
                    COALESCE(c.ContainerStatus, 'Active') as Status,
                    c.LocationID
                FROM container c
                LEFT JOIN containertype ct ON c.ContainerTypeID = ct.ContainerTypeID
                WHERE c.ContainerID = """ + container_id_str)
            
            container_result = cursor.fetchone()
            if not container_result:
                return jsonify({'success': False, 'error': 'Container not found'}), 404
            
            # Convert to dict with column names
            container_cols = [col[0] for col in cursor.description]
            container = dict(zip(container_cols, container_result))
            
            # Ensure all numeric values are properly converted
            if 'ContainerID' in container and container['ContainerID'] is not None:
                container['ContainerID'] = int(container['ContainerID'])
            if 'ContainerTypeID' in container and container['ContainerTypeID'] is not None:
                container['ContainerTypeID'] = int(container['ContainerTypeID'])
            if 'ContainerCapacity' in container and container['ContainerCapacity'] is not None:
                try:
                    container['ContainerCapacity'] = int(container['ContainerCapacity'])
                except (ValueError, TypeError):
                    container['ContainerCapacity'] = 0
            
            # Get samples in this container with more detail
            cursor.execute("""
                SELECT 
                    s.SampleID,
                    s.Description,
                    s.PartNumber,
                    cs.Amount,
                    CASE
                        WHEN un.UnitName IS NULL THEN 'pcs'
                        WHEN LOWER(un.UnitName) = 'stk' THEN 'pcs'
                        ELSE un.UnitName
                    END as Unit,
                    sl.LocationName,
                    ss.ExpireDate,
                    DATE_FORMAT(r.ReceivedDate, '%d-%m-%Y') as RegisteredDate,
                    ss.StorageID as SampleStorageID
                FROM containersample cs
                JOIN samplestorage ss ON cs.SampleStorageID = ss.StorageID
                JOIN sample s ON ss.SampleID = s.SampleID
                LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
                LEFT JOIN reception r ON s.ReceptionID = r.ReceptionID
                LEFT JOIN unit un ON s.UnitID = un.UnitID
                WHERE cs.ContainerID = """ + container_id_str)
            
            samples_result = cursor.fetchall()
            samples_cols = [col[0] for col in cursor.description]
            samples = []
            
            # Properly convert all sample values to proper types
            for row in samples_result:
                sample_dict = dict(zip(samples_cols, row))
                
                # Convert SampleID to integer
                if 'SampleID' in sample_dict and sample_dict['SampleID'] is not None:
                    sample_dict['SampleID'] = int(sample_dict['SampleID'])
                
                # Convert Amount to float or int
                if 'Amount' in sample_dict and sample_dict['Amount'] is not None:
                    try:
                        sample_dict['Amount'] = float(sample_dict['Amount'])
                    except (ValueError, TypeError):
                        sample_dict['Amount'] = 0
                
                # Add to samples list
                samples.append(sample_dict)
            
            # Get container history with formatted timestamp
            # Use direct string concat to avoid % format issues
            cursor.execute("""
                SELECT 
                    DATE_FORMAT(h.Timestamp, '%d-%m-%Y %H:%i') as Timestamp,
                    h.ActionType,
                    h.Notes,
                    u.Name as UserName
                FROM history h
                LEFT JOIN user u ON h.UserID = u.UserID
                WHERE h.Notes LIKE '%Container """ + container_id_str + """%'
                ORDER BY h.Timestamp DESC
                LIMIT 20
            """)
            
            history_result = cursor.fetchall()
            history_cols = [col[0] for col in cursor.description]
            history = []
            
            # Process history records with properly formatted timestamps
            for row in history_result:
                history_dict = dict(zip(history_cols, row))
                # Ensure timestamp is a string
                if 'Timestamp' in history_dict and history_dict['Timestamp'] is not None:
                    history_dict['Timestamp'] = str(history_dict['Timestamp'])
                history.append(history_dict)
            
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