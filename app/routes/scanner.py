from flask import Blueprint, request, jsonify, render_template, current_app
from app.models.sample import Sample
import json
import logging

scanner_bp = Blueprint('scanner', __name__)
mysql = None

def init_scanner(blueprint, mysql_client):
    global mysql
    mysql = mysql_client

@scanner_bp.route('/api/scanner/data', methods=['POST'])
def receive_scan_data():
    """
    Endpoint til at modtage scanningsdata fra Zebra DataWedge.
    Forventer et JSON-objekt med en barcode-værdi.
    """
    try:
        # Log den modtagne data til fejlfinding
        data = request.get_json()
        current_app.logger.info(f"Modtaget scanningsdata: {data}")
        
        if not data or 'barcode' not in data:
            return jsonify({'status': 'error', 'message': 'Ingen gyldig stregkode modtaget'}), 400
        
        barcode = data['barcode']
        
        # Find prøven i databasen baseret på stregkode
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT s.*, r.received_date, u.name as unit_name, l.name as location_name
            FROM samples s
            LEFT JOIN receptions r ON s.reception_id = r.id
            LEFT JOIN units u ON s.unit_id = u.id
            LEFT JOIN locations l ON s.location_id = l.id
            WHERE s.barcode = %s
        """, (barcode,))
        
        result = cursor.fetchone()
        cursor.close()
        
        if not result:
            return jsonify({
                'status': 'not_found',
                'message': f'Stregkode ikke fundet: {barcode}'
            }), 404
        
        # Konverter databaseresultat til et Sample-objekt
        sample = Sample.from_db_row(result)
        
        return jsonify({
            'status': 'success',
            'message': 'Stregkode scannet og fundet',
            'sample': sample.to_dict(),
        })
        
    except Exception as e:
        current_app.logger.error(f"Fejl ved behandling af scanning: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Fejl ved behandling af scanning: {str(e)}'}), 500

@scanner_bp.route('/scanner', methods=['GET'])
def scanner_page():
    """
    Viser scanner-administrationsside med mulighed for at teste scanning og udskrivning.
    """
    return render_template('sections/scanner.html')

@scanner_bp.route('/api/scanner/test', methods=['POST'])
def test_scanner():
    """
    Testendpoint til at simulere en scanner-anmodning fra webgrænsefladen.
    """
    try:
        data = request.get_json()
        if not data or 'barcode' not in data:
            return jsonify({'status': 'error', 'message': 'Ingen gyldig stregkode modtaget'}), 400
        
        # Videresend til den normale scanningshåndtering
        return receive_scan_data()
    
    except Exception as e:
        current_app.logger.error(f"Fejl ved test af scanning: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Fejl ved test af scanning: {str(e)}'}), 500