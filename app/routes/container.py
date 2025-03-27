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
            
            # Konverter til format anvendt af template
            containers_for_template = []
            for container in containers:
                container_dict = container.to_dict()
                container_dict['TypeName'] = getattr(container, 'type_name', 'Standard')
                container_dict['SampleCount'] = getattr(container, 'sample_count', 0)
                container_dict['TotalItems'] = getattr(container, 'total_items', 0)
                containers_for_template.append(container_dict)
            
            # Hent container typer
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT ContainerTypeID, TypeName, Description, DefaultCapacity FROM ContainerType")
            type_columns = [col[0] for col in cursor.description]
            container_types = [dict(zip(type_columns, row)) for row in cursor.fetchall()]
            
            # Hent aktive prøver til "Tilføj prøve" funktionen
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
                AND s.Status = 'På lager'
                ORDER BY s.SampleID DESC
            """)
            
            columns = [col[0] for col in cursor.description]
            available_samples = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            cursor.close()
            
            return render_template('sections/containers.html', 
                                containers=containers_for_template,
                                container_types=container_types,
                                available_samples=available_samples)
        except Exception as e:
            print(f"Error loading containers: {e}")
            import traceback
            traceback.print_exc()
            return render_template('sections/containers.html', 
                                error=f"Fejl ved indlæsning af containere: {str(e)}",
                                containers=[],
                                container_types=[],
                                available_samples=[])
    
    @blueprint.route('/api/containers/<int:container_id>/location')
    def get_container_location(container_id):
        try:
            # Hent containerens placering
            location = container_service.get_container_location(container_id)
            
            return jsonify({'success': True, 'location': location})
        except Exception as e:
            print(f"API error ved hentning af containerplacering: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500

    @blueprint.route('/api/containers', methods=['POST'])
    def create_container():
        try:
            data = request.json
            
            # Validering af input
            validation_result = validate_container_data(data)
            if not validation_result.get('valid', False):
                return jsonify({
                    'success': False, 
                    'error': validation_result.get('error'),
                    'field': validation_result.get('field')
                }), 400
            
            # Hent aktuel bruger
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            # Opret container via service
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
            # Hent containere der kan indeholde prøver
            containers = container_service.get_available_containers()
            
            return jsonify({'success': True, 'containers': containers})
        except Exception as e:
            print(f"API error ved hentning af tilgængelige containere: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
            
    @blueprint.route('/api/containers/add-sample', methods=['POST'])
    def add_sample_to_container():
        try:
            data = request.json
            
            # Validering af input
            if not data.get('containerId'):
                return jsonify({'success': False, 'error': 'Container ID mangler'}), 400
                
            if not data.get('sampleId'):
                return jsonify({'success': False, 'error': 'Sample ID mangler'}), 400
                
            # Hent aktuel bruger
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            # Tilføj prøve til container via service
            result = container_service.add_sample_to_container(
                data.get('containerId'),
                data.get('sampleId'),
                data.get('amount', 1),
                user_id
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
            # Hent aktuel bruger
            current_user = get_current_user()
            user_id = current_user['UserID']
            
            # Slet container via service
            result = container_service.delete_container(container_id, user_id)
            
            return jsonify(result)
        except Exception as e:
            print(f"API error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500