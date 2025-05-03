from flask import Blueprint, request, jsonify, render_template, current_app
import os
import subprocess
import json
import tempfile
import logging

printer_bp = Blueprint('printer', __name__)
mysql = None

def init_printer(blueprint, mysql_client):
    global mysql
    mysql = mysql_client

@printer_bp.route('/api/print/label', methods=['POST'])
def print_label():
    """
    Endpoint til at udskrive labels med Brother-printeren.
    Forventer et JSON-objekt med label_type og data.
    """
    try:
        data = request.get_json()
        current_app.logger.info(f"Modtaget data til udskrivning: {data}")
        
        if not data or 'label_type' not in data or 'data' not in data:
            return jsonify({'status': 'error', 'message': 'Ugyldig anmodning. Mangler label_type eller data'}), 400
        
        label_type = data['label_type']
        label_data = data['data']
        
        # Få konfigurationsværdier fra miljøvariable eller standard
        printer_app_path = os.getenv('BROTHER_APP_PATH', '')
        
        # Tjek om printer-app er konfigureret
        if not printer_app_path:
            return jsonify({
                'status': 'error', 
                'message': 'Printerapplikationen er ikke konfigureret. Sæt BROTHER_APP_PATH miljøvariablen'
            }), 500
        
        # Forbered label-data baseret på typen
        label_content = format_label(label_type, label_data)
        
        # Gem midlertidigt data til filen
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w') as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(label_content)
        
        try:
            # Kald det eksterne printerprogram med filepath som parameter
            process = subprocess.Popen([printer_app_path, temp_file_path], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE)
            stdout, stderr = process.communicate(timeout=30)
            
            if process.returncode != 0:
                error_message = stderr.decode('utf-8', errors='ignore')
                current_app.logger.error(f"Fejl ved udskrivning: {error_message}")
                return jsonify({'status': 'error', 'message': f'Fejl ved udskrivning: {error_message}'}), 500
            
            return jsonify({
                'status': 'success', 
                'message': 'Label udskrevet succesfuldt'
            })
            
        except subprocess.TimeoutExpired:
            process.kill()
            return jsonify({'status': 'error', 'message': 'Timeout ved udskrivning af label'}), 500
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Fejl ved kald af printerapplikation: {str(e)}'}), 500
        finally:
            # Opryd midlertidig fil
            try:
                os.unlink(temp_file_path)
            except:
                pass
                
    except Exception as e:
        current_app.logger.error(f"Fejl ved behandling af udskrivningsanmodning: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Fejl ved behandling af udskrivningsanmodning: {str(e)}'}), 500

def format_label(label_type, data):
    """
    Formaterer labeldata baseret på labeltypen.
    Returnerer en streng, der skal sendes til printeren.
    """
    if label_type == 'sample':
        # Format for prøve-labels
        return f"""
SAMPLE: {data.get('SampleIDFormatted', '')}
DESC: {data.get('Description', '')}
BARCODE: {data.get('Barcode', '')}
PART#: {data.get('PartNumber', '')}
TYPE: {data.get('Type', '')}
AMOUNT: {data.get('Amount', '')} {data.get('UnitName', '')}
        """
    elif label_type == 'location':
        # Format for lokationslabels
        return f"""
LOCATION: {data.get('Name', '')}
TYPE: {data.get('Type', '')}
BARCODE: {data.get('Barcode', '')}
        """
    elif label_type == 'container':
        # Format for beholderlabels
        return f"""
CONTAINER: {data.get('ContainerIDFormatted', '')}
TYPE: {data.get('Type', '')}
BARCODE: {data.get('Barcode', '')}
LOCATION: {data.get('LocationName', '')}
        """
    else:
        # Ukendt labeltype
        return f"UNKNOWN LABEL TYPE: {label_type}\n{json.dumps(data, indent=2)}"

@printer_bp.route('/api/print/test', methods=['POST'])
def test_print():
    """
    Testendpoint til at udskrive en testlabel.
    """
    try:
        test_data = {
            'label_type': 'test',
            'data': {
                'message': 'Dette er en testlabel',
                'timestamp': 'Test tidsstempel'
            }
        }
        
        # Brug den eksisterende print_label funktion
        response = print_label()
        return response
        
    except Exception as e:
        current_app.logger.error(f"Fejl ved testudskrivning: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Fejl ved testudskrivning: {str(e)}'}), 500