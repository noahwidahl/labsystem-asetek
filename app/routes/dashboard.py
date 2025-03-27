from flask import Blueprint, render_template, jsonify

dashboard_bp = Blueprint('dashboard', __name__)

def _get_storage_locations(mysql):
    """Henter lagerplaceringer fra databasen"""
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT 
            sl.LocationID,
            sl.LocationName,
            COUNT(ss.StorageID) as count,
            'available' as status,
            IFNULL(l.LabName, 'Unknown') as LabName,
            sl.Reol,
            sl.Sektion,
            sl.Hylde
        FROM StorageLocation sl
        LEFT JOIN Lab l ON sl.LabID = l.LabID
        LEFT JOIN SampleStorage ss ON sl.LocationID = ss.LocationID AND ss.AmountRemaining > 0
        GROUP BY sl.LocationID, sl.LocationName, l.LabName, sl.Reol, sl.Sektion, sl.Hylde
        ORDER BY sl.Reol, sl.Sektion, sl.Hylde
    """)
    
    columns = [col[0] for col in cursor.description]
    locations = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    cursor.close()
    return locations

def init_dashboard(blueprint, mysql):
    @blueprint.route('/')
    @blueprint.route('/dashboard')
    def dashboard():
        try:
            # Hent antal prøver på lager
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM Sample WHERE Status = 'På lager'")
            sample_count = cursor.fetchone()[0] or 0
            
            # Hent prøver der udløber snart (indenfor 14 dage)
            cursor.execute("""
                SELECT COUNT(*) FROM SampleStorage ss
                JOIN Sample s ON ss.SampleID = s.SampleID
                WHERE ss.ExpireDate <= DATE_ADD(CURRENT_DATE(), INTERVAL 14 DAY)
                AND s.Status = 'På lager'
                AND ss.AmountRemaining > 0
            """)
            expiring_count = cursor.fetchone()[0] or 0
            
            # Hent nye prøver i dag
            cursor.execute("""
                SELECT COUNT(*) FROM Reception
                WHERE DATE(ReceivedDate) = CURRENT_DATE()
            """)
            new_today = cursor.fetchone()[0] or 0
            
            # Hent antal aktive tests
            cursor.execute("SELECT COUNT(*) FROM Test")
            active_tests_count = cursor.fetchone()[0] or 0
            
            # Hent seneste historik
            cursor.execute("""
                SELECT 
                    h.LogID, 
                    h.ActionType, 
                    h.Notes,
                    IFNULL(s.Description, 'N/A') as SampleDesc,
                    u.Name as UserName,
                    DATE_FORMAT(h.Timestamp, '%d-%m-%Y %H:%i') as Timestamp
                FROM History h
                LEFT JOIN Sample s ON h.SampleID = s.SampleID
                LEFT JOIN User u ON h.UserID = u.UserID
                ORDER BY h.Timestamp DESC
                LIMIT 5
            """)
            
            columns = [col[0] for col in cursor.description]
            history_items = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            cursor.close()
            
            # Hent lagerplaceringer via hjælpefunktionen
            locations = _get_storage_locations(mysql)
            
            return render_template('sections/dashboard.html', 
                                sample_count=sample_count,
                                expiring_count=expiring_count,
                                new_today=new_today,
                                active_tests_count=active_tests_count,
                                history_items=history_items,
                                locations=locations)
        except Exception as e:
            import traceback
            error_message = f"Fejl: {str(e)}\n{traceback.format_exc()}"
            print(error_message)
            return render_template('sections/dashboard.html', 
                                error=error_message,
                                sample_count=0,
                                expiring_count=0,
                                new_today=0,
                                active_tests_count=0,
                                history_items=[],
                                locations=[])
    
    @blueprint.route('/history')
    def history():
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("""
                SELECT 
                    h.LogID,
                    DATE_FORMAT(h.Timestamp, '%d. %M %Y') as FormattedDate,
                    h.ActionType,
                    u.Name as UserName,
                    COALESCE(s.SampleID, ts.GeneratedIdentifier, 'N/A') as ItemID,
                    h.Notes,
                    r.ReceptionID
                FROM History h
                LEFT JOIN User u ON h.UserID = u.UserID
                LEFT JOIN Sample s ON h.SampleID = s.SampleID
                LEFT JOIN TestSample ts ON h.TestID = ts.TestID
                LEFT JOIN Reception r ON s.ReceptionID = r.ReceptionID
                ORDER BY h.Timestamp DESC
                LIMIT 20
            """)
            history_data = cursor.fetchall()
            cursor.close()
            
            history_items = []
            for item in history_data:
                sample_desc = f"SMP-{item[4]}" if item[4] and item[4] != 'N/A' else 'N/A'
                history_items.append({
                    "LogID": item[0],
                    "Timestamp": item[1],
                    "ActionType": item[2],
                    "UserName": item[3],
                    "SampleDesc": sample_desc,
                    "Notes": item[5],
                    "ReceptionID": item[6] if item[6] else None
                })
            
            return render_template('sections/history.html', history_items=history_items)
        except Exception as e:
            print(f"Error loading history: {e}")
            return render_template('sections/history.html', error="Error loading history")
    
    @blueprint.route('/api/storage-locations')
    def get_storage_locations():
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("""
                SELECT 
                    sl.LocationID,
                    sl.LocationName,
                    COUNT(ss.StorageID) as count,
                    'available' as status,
                    IFNULL(l.LabName, 'Unknown') as LabName
                FROM StorageLocation sl
                LEFT JOIN Lab l ON sl.LabID = l.LabID
                LEFT JOIN SampleStorage ss ON sl.LocationID = ss.LocationID AND ss.AmountRemaining > 0
                GROUP BY sl.LocationID, sl.LocationName, l.LabName
                ORDER BY sl.LocationName
            """)
            
            columns = [col[0] for col in cursor.description]
            locations = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            cursor.close()
            return jsonify({'locations': locations})
        except Exception as e:
            print(f"API error ved hentning af lagerplaceringer: {e}")
            return jsonify({'error': str(e)}), 500