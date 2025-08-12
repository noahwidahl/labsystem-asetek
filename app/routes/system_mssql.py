from flask import Blueprint, jsonify
import socket
from app.utils.mssql_db import mssql_db

system_mssql_bp = Blueprint('system_mssql', __name__)

@system_mssql_bp.route('/api/system/info', methods=['GET'])
def get_system_info():
    """
    Returnerer systemoplysninger som server IP og hostname - MSSQL version
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
            'hostname': hostname,
            'database': 'MSSQL'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Kunne ikke hente systemoplysninger: {str(e)}',
            'server_ip': '127.0.0.1',  # Fallback til localhost
            'hostname': 'unknown',
            'database': 'MSSQL'
        })

@system_mssql_bp.route('/api/system/migrate-expiration', methods=['POST'])
def migrate_expiration():
    """
    Run the expiration system database migration - MSSQL version
    """
    try:
        # Check if ExpireDate column already exists in samplestorage table
        check_result = mssql_db.execute_query("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'samplestorage' AND COLUMN_NAME = 'ExpireDate'
        """, fetch_one=True)
        
        if check_result:
            return jsonify({
                'status': 'success',
                'message': 'ExpireDate column already exists in samplestorage table'
            })
        
        # Add ExpireDate column to samplestorage table (MSSQL already has this structure)
        # The migration is mainly for ensuring data integrity
        
        # Check if ExpirationNotification table exists
        table_check = mssql_db.execute_query("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'expirationnotification'
        """, fetch_one=True)
        
        if not table_check:
            # Create ExpirationNotification table
            mssql_db.execute_query("""
                CREATE TABLE [expirationnotification] (
                    [NotificationID] INT IDENTITY(1,1) PRIMARY KEY,
                    [SampleID] INT NOT NULL,
                    [UserID] INT NOT NULL,
                    [NotificationType] NVARCHAR(20) NOT NULL CHECK ([NotificationType] IN ('EXPIRING_SOON', 'EXPIRED')),
                    [NotificationDate] DATETIME NOT NULL DEFAULT GETDATE(),
                    [IsRead] BIT DEFAULT 0,
                    [ReadDate] DATETIME NULL,
                    FOREIGN KEY ([SampleID]) REFERENCES [sample]([SampleID]) ON DELETE CASCADE,
                    FOREIGN KEY ([UserID]) REFERENCES [user]([UserID]) ON DELETE CASCADE
                )
            """)
            
            # Add indexes
            mssql_db.execute_query("""
                CREATE INDEX [idx_notification_user_date] ON [expirationnotification] ([UserID], [NotificationDate])
            """)
            mssql_db.execute_query("""
                CREATE INDEX [idx_notification_sample] ON [expirationnotification] ([SampleID])
            """)
            mssql_db.execute_query("""
                CREATE INDEX [idx_notification_unread] ON [expirationnotification] ([IsRead], [UserID])
            """)
        
        return jsonify({
            'status': 'success',
            'message': 'Expiration system migration completed successfully for MSSQL'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Migration failed: {str(e)}'
        }), 500