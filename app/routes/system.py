from flask import Blueprint, jsonify
import socket

system_bp = Blueprint('system', __name__)
mysql = None

def init_system(blueprint, mysql_client):
    global mysql
    mysql = mysql_client

@system_bp.route('/api/system/info', methods=['GET'])
def get_system_info():
    """
    Returnerer systemoplysninger som server IP og hostname
    """
    try:
        # Forsøg at få den lokale IP-adresse
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Behøver ikke faktisk at oprette forbindelse, men dette er en måde at få den lokale IP
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        hostname = socket.gethostname()
        
        return jsonify({
            'status': 'success',
            'server_ip': local_ip,
            'hostname': hostname
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Kunne ikke hente systemoplysninger: {str(e)}',
            'server_ip': '127.0.0.1',  # Fallback til localhost
            'hostname': 'unknown'
        })