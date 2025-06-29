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
        # Fallback: If notification table doesn't exist, create notifications from samples directly
        try:
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
                FROM expirationnotification n
                JOIN sample s ON n.SampleID = s.SampleID
                LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
                LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
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
            
        except Exception as e:
            print(f"Notification table error: {e}. Using fallback method.")
            # Fallback: Generate notifications from sample data directly
            return self._generate_notifications_from_samples()
            
    def _generate_notifications_from_samples(self):
        """
        Fallback method to generate notifications directly from sample data
        """
        query = """
            SELECT 
                s.SampleID,
                s.SampleID as NotificationID,
                CASE 
                    WHEN s.ExpireDate <= CURDATE() THEN 'EXPIRED'
                    ELSE 'EXPIRING_SOON'
                END as NotificationType,
                CURDATE() as NotificationDate,
                FALSE as IsRead,
                NULL as ReadDate,
                s.Description as SampleDescription,
                s.PartNumber,
                s.ExpireDate,
                sl.LocationName,
                CASE 
                    WHEN s.ExpireDate <= CURDATE() THEN DATEDIFF(CURDATE(), s.ExpireDate)
                    ELSE DATEDIFF(s.ExpireDate, CURDATE())
                END as DaysDifference
            FROM sample s
            LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
            LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
            WHERE s.Status = 'In Storage'
            AND (s.ExpireDate <= CURDATE() OR s.ExpireDate <= DATE_ADD(CURDATE(), INTERVAL 14 DAY))
            ORDER BY s.ExpireDate ASC
            LIMIT 50
        """
        
        result, _ = self.db.execute_query(query, ())
        
        notifications = []
        for row in result:
            notifications.append({
                'notification_id': row[1],
                'sample_id': row[0],
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
        try:
            query = """
                UPDATE expirationnotification 
                SET IsRead = TRUE, ReadDate = %s
                WHERE NotificationID = %s AND UserID = %s
            """
            
            result, _ = self.db.execute_query(query, (datetime.now(), notification_id, user_id))
            return result
        except Exception as e:
            print(f"Mark notification read error: {e}. Notification table doesn't exist.")
            # Fallback: Just return success since we don't have a notification table
            return True
    
    def mark_all_notifications_read(self, user_id):
        """
        Mark all notifications as read for a user.
        """
        try:
            query = """
                UPDATE expirationnotification 
                SET IsRead = TRUE, ReadDate = %s
                WHERE UserID = %s AND IsRead = FALSE
            """
            
            result, _ = self.db.execute_query(query, (datetime.now(), user_id))
            return result
        except Exception as e:
            print(f"Mark all notifications read error: {e}. Notification table doesn't exist.")
            # Fallback: Just return success since we don't have a notification table
            return True
    
    def get_expired_samples(self, user_id=None):
        """
        Get samples that have expired.
        """
        user_filter = "AND r.UserID = %s" if user_id else ""
        params = (user_id,) if user_id else ()
        
        query = f"""
            SELECT 
                s.SampleID,
                s.Description,
                s.PartNumber,
                s.Barcode,
                s.ExpireDate,
                r.ReceivedDate,
                u.Name as RegisteredBy,
                sl.LocationName,
                DATEDIFF(CURDATE(), s.ExpireDate) as DaysOverdue
            FROM sample s
            LEFT JOIN reception r ON s.ReceptionID = r.ReceptionID
            LEFT JOIN user u ON r.UserID = u.UserID
            LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
            LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
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
                'barcode': row[3],
                'expire_date': row[4],
                'received_date': row[5],
                'registered_by': row[6],
                'location': row[7],
                'days_overdue': row[8]
            })
        
        return expired_samples
    
    def get_expiring_soon_samples(self, user_id=None, days_ahead=7):
        """
        Get samples that will expire soon.
        """
        user_filter = "AND r.UserID = %s" if user_id else ""
        params = (days_ahead, user_id) if user_id else (days_ahead,)
        
        query = f"""
            SELECT 
                s.SampleID,
                s.Description,
                s.PartNumber,
                s.Barcode,
                s.ExpireDate,
                r.ReceivedDate,
                u.Name as RegisteredBy,
                sl.LocationName,
                DATEDIFF(s.ExpireDate, CURDATE()) as DaysUntilExpiry
            FROM sample s
            LEFT JOIN reception r ON s.ReceptionID = r.ReceptionID
            LEFT JOIN user u ON r.UserID = u.UserID
            LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
            LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
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
                'barcode': row[3],
                'expire_date': row[4],
                'received_date': row[5],
                'registered_by': row[6],
                'location': row[7],
                'days_until_expiry': row[8]
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
            SELECT s.SampleID, COALESCE(r.UserID, 1) as UserID
            FROM sample s
            LEFT JOIN reception r ON s.ReceptionID = r.ReceptionID
            WHERE s.ExpireDate = CURDATE()
            AND s.Status = 'In Storage'
            AND NOT EXISTS (
                SELECT 1 FROM expirationnotification n 
                WHERE n.SampleID = s.SampleID 
                AND n.NotificationType = 'EXPIRED'
            )
        """
        
        result, _ = self.db.execute_query(query_expired, ())
        
        for row in result:
            sample_id, user_id = row
            insert_query = """
                INSERT INTO expirationnotification (SampleID, UserID, NotificationType)
                VALUES (%s, %s, 'EXPIRED')
            """
            self.db.execute_query(insert_query, (sample_id, user_id))
            notifications_created += 1
        
        # Check for samples expiring in 7 days
        query_expiring = """
            SELECT s.SampleID, COALESCE(r.UserID, 1) as UserID
            FROM sample s
            LEFT JOIN reception r ON s.ReceptionID = r.ReceptionID
            WHERE s.ExpireDate = DATE_ADD(CURDATE(), INTERVAL 7 DAY)
            AND s.Status = 'In Storage'
            AND NOT EXISTS (
                SELECT 1 FROM expirationnotification n 
                WHERE n.SampleID = s.SampleID 
                AND n.NotificationType = 'EXPIRING_SOON'
            )
        """
        
        result, _ = self.db.execute_query(query_expiring, ())
        
        for row in result:
            sample_id, user_id = row
            insert_query = """
                INSERT INTO expirationnotification (SampleID, UserID, NotificationType)
                VALUES (%s, %s, 'EXPIRING_SOON')
            """
            self.db.execute_query(insert_query, (sample_id, user_id))
            notifications_created += 1
        
        return notifications_created
    
    def sync_notifications_with_samples(self):
        """
        Sync notification table with current sample expire dates.
        This creates missing notifications for samples that should have them.
        """
        notifications_created = 0
        
        try:
            # Get all samples that are expired or expiring soon but don't have notifications
            query = """
                SELECT s.SampleID, 
                       COALESCE(r.UserID, 1) as UserID,
                       CASE 
                           WHEN s.ExpireDate <= CURDATE() THEN 'EXPIRED'
                           ELSE 'EXPIRING_SOON'
                       END as NotificationType
                FROM sample s
                LEFT JOIN reception r ON s.ReceptionID = r.ReceptionID
                WHERE s.Status = 'In Storage'
                AND (s.ExpireDate <= CURDATE() OR s.ExpireDate <= DATE_ADD(CURDATE(), INTERVAL 14 DAY))
                AND NOT EXISTS (
                    SELECT 1 FROM expirationnotification n 
                    WHERE n.SampleID = s.SampleID 
                    AND n.NotificationType = CASE 
                        WHEN s.ExpireDate <= CURDATE() THEN 'EXPIRED'
                        ELSE 'EXPIRING_SOON'
                    END
                )
            """
            
            result, _ = self.db.execute_query(query, ())
            
            for row in result:
                sample_id, user_id, notification_type = row
                
                # Insert notification
                insert_query = """
                    INSERT INTO expirationnotification (SampleID, UserID, NotificationType)
                    VALUES (%s, %s, %s)
                """
                
                try:
                    self.db.execute_query(insert_query, (sample_id, user_id, notification_type))
                    notifications_created += 1
                    print(f"Created {notification_type} notification for sample {sample_id}")
                except Exception as e:
                    print(f"Error creating notification for sample {sample_id}: {e}")
                    continue
            
            return notifications_created
            
        except Exception as e:
            print(f"Error syncing notifications: {e}")
            return 0
    
    def extend_sample_expiry(self, sample_id, new_expire_date, user_id, note=""):
        """
        Extend the expiry date of a sample and log the action.
        """
        try:
            cursor = self.mysql.connection.cursor()
            
            # Update sample expire date
            update_query = """
                UPDATE sample 
                SET ExpireDate = %s
                WHERE SampleID = %s
            """
            
            cursor.execute(update_query, (new_expire_date, sample_id))
            
            # Log the action in history
            history_query = """
                INSERT INTO history (SampleID, ActionType, Notes, UserID, Timestamp)
                VALUES (%s, %s, %s, %s, %s)
            """
            
            notes = f"Expire date extended to {new_expire_date}"
            if note:
                notes += f". Note: {note}"
            
            cursor.execute(history_query, (
                sample_id,
                'Expiry extended',
                notes,
                user_id,
                datetime.now()
            ))
            
            # Mark related notifications as read (if notification table exists)
            try:
                mark_read_query = """
                    UPDATE expirationnotification 
                    SET IsRead = TRUE, ReadDate = %s
                    WHERE SampleID = %s AND IsRead = FALSE
                """
                
                cursor.execute(mark_read_query, (datetime.now(), sample_id))
            except Exception as e:
                print(f"Mark related notifications read error: {e}. Notification table doesn't exist.")
            
            self.mysql.connection.commit()
            cursor.close()
            
            return True
            
        except Exception as e:
            print(f"Error extending sample expiry: {e}")
            raise e
    
    def get_notification_summary(self, user_id):
        """
        Get a summary of unread notifications for a user.
        """
        try:
            query = """
                SELECT 
                    n.NotificationType,
                    COUNT(*) as Count
                FROM expirationnotification n
                JOIN sample s ON n.SampleID = s.SampleID
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
            
        except Exception as e:
            print(f"Notification summary error: {e}. Using fallback method.")
            # Fallback: Count directly from sample data
            return self._generate_summary_from_samples()
            
    def _generate_summary_from_samples(self):
        """
        Fallback method to generate summary directly from sample data
        """
        query = """
            SELECT 
                CASE 
                    WHEN s.ExpireDate <= CURDATE() THEN 'EXPIRED'
                    ELSE 'EXPIRING_SOON'
                END as NotificationType,
                COUNT(*) as Count
            FROM sample s
            WHERE s.Status = 'In Storage'
            AND (s.ExpireDate <= CURDATE() OR s.ExpireDate <= DATE_ADD(CURDATE(), INTERVAL 14 DAY))
            GROUP BY NotificationType
        """
        
        result, _ = self.db.execute_query(query, ())
        
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