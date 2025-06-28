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

@system_bp.route('/api/system/migrate-expiration', methods=['POST'])
def migrate_expiration():
    """
    Run the expiration system database migration
    """
    try:
        cursor = mysql.connection.cursor()
        
        # Check if ExpireDate column already exists
        cursor.execute("SHOW COLUMNS FROM Sample LIKE 'ExpireDate'")
        if cursor.fetchone():
            return jsonify({
                'status': 'success',
                'message': 'ExpireDate column already exists'
            })
        
        # Add ExpireDate column to Sample table
        cursor.execute("""
            ALTER TABLE Sample 
            ADD COLUMN ExpireDate DATE DEFAULT NULL COMMENT 'Date when sample expires and should trigger notification'
        """)
        
        # Add index for efficient expiration queries
        cursor.execute("CREATE INDEX idx_sample_expire_date ON Sample (ExpireDate)")
        
        # Update existing samples to have default expire date (2 months from registration)
        cursor.execute("""
            UPDATE Sample 
            SET ExpireDate = DATE_ADD(
                COALESCE(
                    (SELECT r.ReceivedDate FROM Reception r WHERE r.ReceptionID = Sample.ReceptionID),
                    NOW()
                ), 
                INTERVAL 2 MONTH
            )
            WHERE ExpireDate IS NULL
        """)
        
        # Create ExpirationNotification table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ExpirationNotification (
                NotificationID INT AUTO_INCREMENT PRIMARY KEY,
                SampleID INT NOT NULL,
                UserID INT NOT NULL,
                NotificationType ENUM('EXPIRING_SOON', 'EXPIRED') NOT NULL,
                NotificationDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                IsRead BOOLEAN DEFAULT FALSE,
                ReadDate DATETIME NULL,
                FOREIGN KEY (SampleID) REFERENCES Sample(SampleID) ON DELETE CASCADE,
                FOREIGN KEY (UserID) REFERENCES User(UserID) ON DELETE CASCADE,
                INDEX idx_notification_user_date (UserID, NotificationDate),
                INDEX idx_notification_sample (SampleID),
                INDEX idx_notification_unread (IsRead, UserID)
            ) ENGINE=InnoDB COMMENT='Tracks expiration notifications sent to users'
        """)
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({
            'status': 'success',
            'message': 'Expiration system migration completed successfully'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Migration failed: {str(e)}'
        }), 500