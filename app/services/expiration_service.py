from datetime import datetime, timedelta
from app.utils.db import DatabaseManager

class ExpirationService:
    def __init__(self, mysql):
        self.mysql = mysql
        self.db = DatabaseManager(mysql)
    
    def get_user_notifications(self, user_id, include_read=False):
        """
        Get expiration notifications for a specific user.
        """
        read_filter = "" if include_read else "AND n.IsRead = FALSE"
        
        query = f"""
            SELECT 
                n.NotificationID,
                n.SampleID,
                n.NotificationType,
                n.NotificationDate,
                n.IsRead,
                n.ReadDate,
                s.Description as SampleDescription,
                s.PartNumber,
                s.ExpireDate,
                sl.LocationName,
                CASE 
                    WHEN n.NotificationType = 'EXPIRED' THEN DATEDIFF(CURDATE(), s.ExpireDate)
                    ELSE DATEDIFF(s.ExpireDate, CURDATE())
                END as DaysDifference
            FROM ExpirationNotification n
            JOIN Sample s ON n.SampleID = s.SampleID
            LEFT JOIN SampleStorage ss ON s.SampleID = ss.SampleID
            LEFT JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
            WHERE n.UserID = %s {read_filter}
            AND s.Status = 'In Storage'
            ORDER BY n.NotificationDate DESC
            LIMIT 50
        """
        
        result, _ = self.db.execute_query(query, (user_id,))
        
        notifications = []
        for row in result:
            notifications.append({
                'notification_id': row[0],
                'sample_id': row[1],
                'type': row[2],
                'date': row[3],
                'is_read': row[4],
                'read_date': row[5],
                'sample_description': row[6],
                'part_number': row[7],
                'expire_date': row[8],
                'location': row[9],
                'days_difference': row[10]
            })
        
        return notifications
    
    def mark_notification_read(self, notification_id, user_id):
        """
        Mark a notification as read.
        """
        query = """
            UPDATE ExpirationNotification 
            SET IsRead = TRUE, ReadDate = %s
            WHERE NotificationID = %s AND UserID = %s
        """
        
        result, _ = self.db.execute_query(query, (datetime.now(), notification_id, user_id))
        return result
    
    def mark_all_notifications_read(self, user_id):
        """
        Mark all notifications as read for a user.
        """
        query = """
            UPDATE ExpirationNotification 
            SET IsRead = TRUE, ReadDate = %s
            WHERE UserID = %s AND IsRead = FALSE
        """
        
        result, _ = self.db.execute_query(query, (datetime.now(), user_id))
        return result
    
    def get_expired_samples(self, user_id=None):
        """
        Get samples that have expired.
        """
        user_filter = "AND r.ReceivedBy = %s" if user_id else ""
        params = (user_id,) if user_id else ()
        
        query = f"""
            SELECT 
                s.SampleID,
                s.Description,
                s.PartNumber,
                s.ExpireDate,
                r.ReceivedDate,
                u.Name as RegisteredBy,
                sl.LocationName,
                DATEDIFF(CURDATE(), s.ExpireDate) as DaysOverdue
            FROM Sample s
            LEFT JOIN Reception r ON s.ReceptionID = r.ReceptionID
            LEFT JOIN User u ON r.ReceivedBy = u.UserID
            LEFT JOIN SampleStorage ss ON s.SampleID = ss.SampleID
            LEFT JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
            WHERE s.ExpireDate <= CURDATE() 
            AND s.Status = 'In Storage'
            {user_filter}
            ORDER BY s.ExpireDate ASC
        """
        
        result, _ = self.db.execute_query(query, params)
        
        expired_samples = []
        for row in result:
            expired_samples.append({
                'sample_id': row[0],
                'description': row[1],
                'part_number': row[2],
                'expire_date': row[3],
                'received_date': row[4],
                'registered_by': row[5],
                'location': row[6],
                'days_overdue': row[7]
            })
        
        return expired_samples
    
    def get_expiring_soon_samples(self, user_id=None, days_ahead=7):
        """
        Get samples that will expire soon.
        """
        user_filter = "AND r.ReceivedBy = %s" if user_id else ""
        params = (days_ahead, user_id) if user_id else (days_ahead,)
        
        query = f"""
            SELECT 
                s.SampleID,
                s.Description,
                s.PartNumber,
                s.ExpireDate,
                r.ReceivedDate,
                u.Name as RegisteredBy,
                sl.LocationName,
                DATEDIFF(s.ExpireDate, CURDATE()) as DaysUntilExpiry
            FROM Sample s
            LEFT JOIN Reception r ON s.ReceptionID = r.ReceptionID
            LEFT JOIN User u ON r.ReceivedBy = u.UserID
            LEFT JOIN SampleStorage ss ON s.SampleID = ss.SampleID
            LEFT JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
            WHERE s.ExpireDate > CURDATE() 
            AND s.ExpireDate <= DATE_ADD(CURDATE(), INTERVAL %s DAY)
            AND s.Status = 'In Storage'
            {user_filter}
            ORDER BY s.ExpireDate ASC
        """
        
        result, _ = self.db.execute_query(query, params)
        
        expiring_samples = []
        for row in result:
            expiring_samples.append({
                'sample_id': row[0],
                'description': row[1],
                'part_number': row[2],
                'expire_date': row[3],
                'received_date': row[4],
                'registered_by': row[5],
                'location': row[6],
                'days_until_expiry': row[7]
            })
        
        return expiring_samples
    
    def create_notifications_for_new_expirations(self):
        """
        Check for new expiring/expired samples and create notifications.
        This should be run daily via a scheduled task.
        """
        notifications_created = 0
        
        # Check for newly expired samples
        query_expired = """
            SELECT s.SampleID, COALESCE(r.ReceivedBy, 1) as UserID
            FROM Sample s
            LEFT JOIN Reception r ON s.ReceptionID = r.ReceptionID
            WHERE s.ExpireDate = CURDATE()
            AND s.Status = 'In Storage'
            AND NOT EXISTS (
                SELECT 1 FROM ExpirationNotification n 
                WHERE n.SampleID = s.SampleID 
                AND n.NotificationType = 'EXPIRED'
            )
        """
        
        result, _ = self.db.execute_query(query_expired, ())
        
        for row in result:
            sample_id, user_id = row
            insert_query = """
                INSERT INTO ExpirationNotification (SampleID, UserID, NotificationType)
                VALUES (%s, %s, 'EXPIRED')
            """
            self.db.execute_query(insert_query, (sample_id, user_id))
            notifications_created += 1
        
        # Check for samples expiring in 7 days
        query_expiring = """
            SELECT s.SampleID, COALESCE(r.ReceivedBy, 1) as UserID
            FROM Sample s
            LEFT JOIN Reception r ON s.ReceptionID = r.ReceptionID
            WHERE s.ExpireDate = DATE_ADD(CURDATE(), INTERVAL 7 DAY)
            AND s.Status = 'In Storage'
            AND NOT EXISTS (
                SELECT 1 FROM ExpirationNotification n 
                WHERE n.SampleID = s.SampleID 
                AND n.NotificationType = 'EXPIRING_SOON'
            )
        """
        
        result, _ = self.db.execute_query(query_expiring, ())
        
        for row in result:
            sample_id, user_id = row
            insert_query = """
                INSERT INTO ExpirationNotification (SampleID, UserID, NotificationType)
                VALUES (%s, %s, 'EXPIRING_SOON')
            """
            self.db.execute_query(insert_query, (sample_id, user_id))
            notifications_created += 1
        
        return notifications_created
    
    def extend_sample_expiry(self, sample_id, new_expire_date, user_id, note=""):
        """
        Extend the expiry date of a sample and log the action.
        """
        # Update sample expire date
        update_query = """
            UPDATE Sample 
            SET ExpireDate = %s
            WHERE SampleID = %s
        """
        
        self.db.execute_query(update_query, (new_expire_date, sample_id))
        
        # Log the action in history
        history_query = """
            INSERT INTO History (SampleID, ActionType, Notes, UserID, Timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        notes = f"Expire date extended to {new_expire_date}"
        if note:
            notes += f". Note: {note}"
        
        self.db.execute_query(history_query, (
            sample_id,
            'Expiry extended',
            notes,
            user_id,
            datetime.now()
        ))
        
        # Mark related notifications as read
        mark_read_query = """
            UPDATE ExpirationNotification 
            SET IsRead = TRUE, ReadDate = %s
            WHERE SampleID = %s AND IsRead = FALSE
        """
        
        self.db.execute_query(mark_read_query, (datetime.now(), sample_id))
        
        return True
    
    def get_notification_summary(self, user_id):
        """
        Get a summary of unread notifications for a user.
        """
        query = """
            SELECT 
                n.NotificationType,
                COUNT(*) as Count
            FROM ExpirationNotification n
            JOIN Sample s ON n.SampleID = s.SampleID
            WHERE n.UserID = %s 
            AND n.IsRead = FALSE
            AND s.Status = 'In Storage'
            GROUP BY n.NotificationType
        """
        
        result, _ = self.db.execute_query(query, (user_id,))
        
        summary = {
            'EXPIRED': 0,
            'EXPIRING_SOON': 0,
            'total': 0
        }
        
        for row in result:
            notification_type, count = row
            summary[notification_type] = count
            summary['total'] += count
        
        return summary