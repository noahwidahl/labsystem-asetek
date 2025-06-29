from flask import Blueprint, request, jsonify, render_template
from app.services.expiration_service import ExpirationService
from app.utils.auth import get_current_user
from datetime import datetime, timedelta

expiration_bp = Blueprint('expiration', __name__)

def init_expiration(blueprint, mysql):
    expiration_service = ExpirationService(mysql)
    
    def get_current_user_with_mysql():
        return get_current_user(mysql)
    
    @blueprint.route('/api/notifications/expiration', methods=['GET'])
    def get_expiration_notifications():
        """
        Get expiration notifications for the current user.
        """
        try:
            user = get_current_user_with_mysql()
            user_id = user.get('UserID', 1)  # Extract UserID from dict
            include_read = request.args.get('include_read', 'false').lower() == 'true'
            
            notifications = expiration_service.get_user_notifications(user_id, include_read)
            
            return jsonify({
                'status': 'success',
                'notifications': notifications,
                'count': len(notifications)
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to get notifications: {str(e)}'
            }), 500
    
    @blueprint.route('/api/notifications/expiration/summary', methods=['GET'])
    def get_notification_summary():
        """
        Get a summary of unread expiration notifications.
        """
        try:
            user = get_current_user_with_mysql()
            user_id = user.get('UserID', 1)
            summary = expiration_service.get_notification_summary(user_id)
            
            return jsonify({
                'status': 'success',
                'summary': summary
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to get notification summary: {str(e)}'
            }), 500
    
    @blueprint.route('/api/notifications/expiration/<int:notification_id>/read', methods=['POST'])
    def mark_notification_read(notification_id):
        """
        Mark a specific notification as read.
        """
        try:
            user = get_current_user_with_mysql()
            user_id = user.get('UserID', 1)
            expiration_service.mark_notification_read(notification_id, user_id)
            
            return jsonify({
                'status': 'success',
                'message': 'Notification marked as read'
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to mark notification as read: {str(e)}'
            }), 500
    
    @blueprint.route('/api/notifications/expiration/read-all', methods=['POST'])
    def mark_all_notifications_read():
        """
        Mark all notifications as read for the current user.
        """
        try:
            user = get_current_user_with_mysql()
            user_id = user.get('UserID', 1)
            expiration_service.mark_all_notifications_read(user_id)
            
            return jsonify({
                'status': 'success',
                'message': 'All notifications marked as read'
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to mark all notifications as read: {str(e)}'
            }), 500
    
    @blueprint.route('/api/samples/expired', methods=['GET'])
    def get_expired_samples():
        """
        Get list of expired samples.
        """
        try:
            user = get_current_user_with_mysql()
            user_id = user.get('UserID', 1)
            my_samples_only = request.args.get('my_samples_only', 'false').lower() == 'true'
            
            if my_samples_only:
                expired_samples = expiration_service.get_expired_samples(user_id)
            else:
                expired_samples = expiration_service.get_expired_samples()
            
            return jsonify({
                'status': 'success',
                'expired_samples': expired_samples,
                'count': len(expired_samples)
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to get expired samples: {str(e)}'
            }), 500
    
    @blueprint.route('/api/samples/expiring-soon', methods=['GET'])
    def get_expiring_soon_samples():
        """
        Get list of samples expiring soon.
        """
        try:
            user = get_current_user_with_mysql()
            user_id = user.get('UserID', 1)
            my_samples_only = request.args.get('my_samples_only', 'false').lower() == 'true'
            days_ahead = int(request.args.get('days_ahead', 7))
            
            if my_samples_only:
                expiring_samples = expiration_service.get_expiring_soon_samples(user_id, days_ahead)
            else:
                expiring_samples = expiration_service.get_expiring_soon_samples(None, days_ahead)
            
            return jsonify({
                'status': 'success',
                'expiring_samples': expiring_samples,
                'count': len(expiring_samples)
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to get expiring samples: {str(e)}'
            }), 500
    
    @blueprint.route('/api/samples/<int:sample_id>/extend-expiry', methods=['POST'])
    def extend_sample_expiry(sample_id):
        """
        Extend the expiry date of a sample.
        """
        try:
            data = request.get_json()
            
            if not data or 'new_expire_date' not in data:
                return jsonify({
                    'status': 'error',
                    'message': 'New expire date is required'
                }), 400
            
            new_expire_date = datetime.strptime(data['new_expire_date'], '%Y-%m-%d').date()
            note = data.get('note', '')
            user = get_current_user()
            user_id = user.get('UserID') if user else 1
            
            # Validate that new date is in the future
            if new_expire_date <= datetime.now().date():
                return jsonify({
                    'status': 'error',
                    'message': 'New expire date must be in the future'
                }), 400
            
            expiration_service.extend_sample_expiry(sample_id, new_expire_date, user_id, note)
            
            return jsonify({
                'status': 'success',
                'message': f'Sample expiry extended to {new_expire_date}'
            })
            
        except ValueError as e:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }), 400
        except Exception as e:
            print(f"Error extending sample expiry: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'status': 'error',
                'message': f'Failed to extend sample expiry: {str(e)}'
            }), 500
    
    @blueprint.route('/notifications', methods=['GET'])
    def notifications_page():
        """
        Render the notifications page.
        """
        return render_template('sections/notifications.html')
    
    @blueprint.route('/api/notifications/create-daily', methods=['POST'])
    def create_daily_notifications():
        """
        Create notifications for newly expired/expiring samples.
        This endpoint should be called daily by a scheduled task.
        """
        try:
            notifications_created = expiration_service.create_notifications_for_new_expirations()
            
            return jsonify({
                'status': 'success',
                'message': f'Created {notifications_created} new notifications',
                'notifications_created': notifications_created
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to create daily notifications: {str(e)}'
            }), 500
    
    @blueprint.route('/api/notifications/sync', methods=['POST'])
    def sync_notifications():
        """
        Sync notifications with current sample expire dates.
        This creates missing notifications for samples that are expiring/expired.
        """
        try:
            notifications_created = expiration_service.sync_notifications_with_samples()
            
            return jsonify({
                'status': 'success',
                'message': f'Synced notifications. Created {notifications_created} new notifications',
                'notifications_created': notifications_created
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to sync notifications: {str(e)}'
            }), 500