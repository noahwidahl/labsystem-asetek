from flask import Blueprint, jsonify, request, render_template
from app.utils.mssql_db import mssql_db
from datetime import datetime, timedelta

expiration_mssql_bp = Blueprint('expiration_mssql', __name__)

@expiration_mssql_bp.route('/expiry')
def expiry_page():
    try:
        # Get current user
        user_id = 1  # TODO: Implement proper user authentication
        
        return render_template('sections/expiry.html')
        
    except Exception as e:
        print(f"Error loading expiry page: {e}")
        return render_template('sections/expiry.html')

@expiration_mssql_bp.route('/api/samples/expired', methods=['GET'])
def get_expired_samples():
    """
    Get list of expired samples - MSSQL version.
    """
    try:
        user_id = 1  # TODO: Implement proper user authentication
        my_samples_only = request.args.get('my_samples_only', 'false').lower() == 'true'
        
        # Build WHERE clause
        where_conditions = ["s.[Status] = 'In Storage'", "ss.[ExpireDate] < GETDATE()"]
        params = []
        
        if my_samples_only:
            where_conditions.append("r.[UserID] = ?")
            params.append(user_id)
        
        query = """
            SELECT DISTINCT
                s.[SampleID],
                s.[Description],
                s.[PartNumber],
                s.[Barcode],
                ss.[ExpireDate],
                DATEDIFF(day, ss.[ExpireDate], GETDATE()) as DaysOverdue,
                u.[Name] as RegisteredBy,
                sl.[LocationName] as Location
            FROM [sample] s
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [reception] r ON s.[ReceptionID] = r.[ReceptionID]
            LEFT JOIN [user] u ON r.[UserID] = u.[UserID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            WHERE {}
            ORDER BY ss.[ExpireDate] ASC
        """.format(" AND ".join(where_conditions))
        
        results = mssql_db.execute_query(query, params, fetch_all=True)
        
        expired_samples = []
        for row in results:
            expired_samples.append({
                'sample_id': row[0],
                'description': row[1] or 'N/A',
                'part_number': row[2] or 'N/A',
                'barcode': row[3] or 'N/A',
                'expire_date': row[4].strftime('%Y-%m-%d') if row[4] else 'N/A',
                'days_overdue': row[5] or 0,
                'registered_by': row[6] or 'Unknown',
                'location': row[7] or 'Unknown'
            })
        
        return jsonify({
            'status': 'success',
            'expired_samples': expired_samples,
            'count': len(expired_samples)
        })
        
    except Exception as e:
        print(f"Error getting expired samples: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get expired samples: {str(e)}'
        }), 500

@expiration_mssql_bp.route('/api/samples/expiring-soon', methods=['GET'])
def get_expiring_soon_samples():
    """
    Get list of samples expiring soon - MSSQL version.
    """
    try:
        user_id = 1  # TODO: Implement proper user authentication
        my_samples_only = request.args.get('my_samples_only', 'false').lower() == 'true'
        days_ahead = int(request.args.get('days_ahead', 7))
        
        # Build WHERE clause
        where_conditions = [
            "s.[Status] = 'In Storage'",
            "ss.[ExpireDate] >= GETDATE()",
            f"ss.[ExpireDate] <= DATEADD(day, {days_ahead}, GETDATE())"
        ]
        params = []
        
        if my_samples_only:
            where_conditions.append("r.[UserID] = ?")
            params.append(user_id)
        
        query = """
            SELECT DISTINCT
                s.[SampleID],
                s.[Description],
                s.[PartNumber],
                s.[Barcode],
                ss.[ExpireDate],
                DATEDIFF(day, GETDATE(), ss.[ExpireDate]) as DaysUntilExpiry,
                u.[Name] as RegisteredBy,
                sl.[LocationName] as Location
            FROM [sample] s
            LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
            LEFT JOIN [reception] r ON s.[ReceptionID] = r.[ReceptionID]
            LEFT JOIN [user] u ON r.[UserID] = u.[UserID]
            LEFT JOIN [storagelocation] sl ON ss.[LocationID] = sl.[LocationID]
            WHERE {}
            ORDER BY ss.[ExpireDate] ASC
        """.format(" AND ".join(where_conditions))
        
        results = mssql_db.execute_query(query, params, fetch_all=True)
        
        expiring_samples = []
        for row in results:
            expiring_samples.append({
                'sample_id': row[0],
                'description': row[1] or 'N/A',
                'part_number': row[2] or 'N/A',
                'barcode': row[3] or 'N/A',
                'expire_date': row[4].strftime('%Y-%m-%d') if row[4] else 'N/A',
                'days_until_expiry': row[5] or 0,
                'registered_by': row[6] or 'Unknown',
                'location': row[7] or 'Unknown'
            })
        
        return jsonify({
            'status': 'success',
            'expiring_samples': expiring_samples,
            'count': len(expiring_samples)
        })
        
    except Exception as e:
        print(f"Error getting expiring soon samples: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get expiring soon samples: {str(e)}'
        }), 500

@expiration_mssql_bp.route('/api/notifications/expiration', methods=['GET'])
def get_expiration_notifications():
    """MSSQL version - Get expiration notifications for current user"""
    try:
        user_id = 1  # TODO: Implement proper user authentication
        
        notifications = mssql_db.execute_query("""
            SELECT 
                [NotificationID],
                [SampleID], 
                [NotificationType],
                [NotificationDate],
                [IsRead]
            FROM [expirationnotification]
            WHERE [UserID] = ?
            ORDER BY [NotificationDate] DESC
        """, (user_id,), fetch_all=True)
        
        notification_list = []
        for row in notifications:
            notification_list.append({
                'notification_id': row[0],
                'sample_id': row[1],
                'notification_type': row[2],
                'notification_date': row[3].isoformat(),
                'is_read': bool(row[4])
            })
        
        return jsonify({
            'status': 'success',
            'notifications': notification_list
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get notifications: {str(e)}'
        }), 500

@expiration_mssql_bp.route('/api/notifications/expiration/summary', methods=['GET'])
def get_expiration_summary():
    """MSSQL version - Get expiration notification summary"""
    try:
        user_id = 1  # TODO: Implement proper user authentication
        
        summary = mssql_db.execute_query("""
            SELECT 
                COUNT(*) as TotalNotifications,
                SUM(CASE WHEN [IsRead] = 0 THEN 1 ELSE 0 END) as UnreadCount
            FROM [expirationnotification]
            WHERE [UserID] = ?
        """, (user_id,), fetch_one=True)
        
        return jsonify({
            'status': 'success',
            'total_notifications': summary[0] if summary else 0,
            'unread_count': summary[1] if summary else 0
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get summary: {str(e)}'
        }), 500

@expiration_mssql_bp.route('/api/notifications/expiration/<int:notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    """MSSQL version - Mark a notification as read"""
    try:
        user_id = 1  # TODO: Implement proper user authentication
        
        mssql_db.execute_query("""
            UPDATE [expirationnotification]
            SET [IsRead] = 1, [ReadDate] = GETDATE()
            WHERE [NotificationID] = ? AND [UserID] = ?
        """, (notification_id, user_id))
        
        return jsonify({
            'status': 'success',
            'message': 'Notification marked as read'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to mark notification as read: {str(e)}'
        }), 500

@expiration_mssql_bp.route('/api/notifications/expiration/read-all', methods=['POST'])
def mark_all_notifications_read():
    """MSSQL version - Mark all notifications as read"""
    try:
        user_id = 1  # TODO: Implement proper user authentication
        
        mssql_db.execute_query("""
            UPDATE [expirationnotification]
            SET [IsRead] = 1, [ReadDate] = GETDATE()
            WHERE [UserID] = ? AND [IsRead] = 0
        """, (user_id,))
        
        return jsonify({
            'status': 'success',
            'message': 'All notifications marked as read'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to mark all notifications as read: {str(e)}'
        }), 500

@expiration_mssql_bp.route('/api/samples/<int:sample_id>/extend-expiry', methods=['POST'])
def extend_sample_expiry(sample_id):
    """MSSQL version - Extend sample expiry date"""
    try:
        data = request.get_json()
        if not data or 'new_expiry_date' not in data:
            return jsonify({
                'status': 'error',
                'message': 'New expiry date is required'
            }), 400
        
        new_expiry_date = data['new_expiry_date']
        
        # Update expiry date in samplestorage table
        mssql_db.execute_query("""
            UPDATE [samplestorage]
            SET [ExpireDate] = ?
            WHERE [SampleID] = ?
        """, (new_expiry_date, sample_id))
        
        # Log the action
        user_id = 1  # TODO: Implement proper user authentication
        mssql_db.execute_query("""
            INSERT INTO [history] ([SampleID], [ActionType], [Notes], [UserID], [Timestamp])
            VALUES (?, 'Expiry Extended', ?, ?, GETDATE())
        """, (sample_id, f'Expiry date extended to {new_expiry_date}', user_id))
        
        return jsonify({
            'status': 'success',
            'message': f'Sample {sample_id} expiry extended to {new_expiry_date}'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to extend expiry: {str(e)}'
        }), 500

@expiration_mssql_bp.route('/notifications', methods=['GET'])
def notifications_page():
    """MSSQL version - Render notifications page"""
    return render_template('sections/notifications.html')

@expiration_mssql_bp.route('/api/notifications/create-daily', methods=['POST'])
def create_daily_notifications():
    """MSSQL version - Create daily expiration notifications"""
    try:
        # This would typically be run by a scheduler
        # Get all users
        users = mssql_db.execute_query("SELECT [UserID] FROM [user]", fetch_all=True)
        
        notifications_created = 0
        for user_row in users:
            user_id = user_row[0]
            
            # Get samples expiring today or overdue for this user
            expired_samples = mssql_db.execute_query("""
                SELECT DISTINCT s.[SampleID]
                FROM [sample] s
                LEFT JOIN [samplestorage] ss ON s.[SampleID] = ss.[SampleID]
                LEFT JOIN [reception] r ON s.[ReceptionID] = r.[ReceptionID]
                WHERE r.[UserID] = ? AND s.[Status] = 'In Storage' 
                AND ss.[ExpireDate] <= GETDATE()
            """, (user_id,), fetch_all=True)
            
            # Create notifications
            for sample_row in expired_samples:
                sample_id = sample_row[0]
                
                # Check if notification already exists
                existing = mssql_db.execute_query("""
                    SELECT COUNT(*) FROM [expirationnotification]
                    WHERE [SampleID] = ? AND [UserID] = ? AND [NotificationType] = 'EXPIRED'
                """, (sample_id, user_id), fetch_one=True)
                
                if not existing[0]:
                    mssql_db.execute_query("""
                        INSERT INTO [expirationnotification] 
                        ([SampleID], [UserID], [NotificationType], [NotificationDate])
                        VALUES (?, ?, 'EXPIRED', GETDATE())
                    """, (sample_id, user_id))
                    notifications_created += 1
        
        return jsonify({
            'status': 'success',
            'message': f'Created {notifications_created} notifications'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to create daily notifications: {str(e)}'
        }), 500

@expiration_mssql_bp.route('/api/notifications/sync', methods=['POST'])
def sync_notifications():
    """MSSQL version - Sync notifications with current expiry status"""
    try:
        # Clean up old notifications
        mssql_db.execute_query("""
            DELETE FROM [expirationnotification]
            WHERE [NotificationDate] < DATEADD(day, -30, GETDATE())
        """)
        
        return jsonify({
            'status': 'success',
            'message': 'Notifications synchronized'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to sync notifications: {str(e)}'
        }), 500