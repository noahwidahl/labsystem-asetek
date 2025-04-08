import mysql.connector
from mysql.connector import Error
import json

def get_db_structure_and_sample_data():
    result = {}
    
    try:
        # Opret forbindelse til databasen
        connection = mysql.connector.connect(
            host='localhost',
            user='root',  # Erstat med din faktiske bruger
            password='0LLEbr0dR00T!',  # Erstat med din faktiske adgangskode
            database='lab_system'  # Erstat med dit faktiske databasenavn
        )
        
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            
            # Få alle tabeller
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            result["tables"] = []
            
            # For hver tabel
            for table_info in tables:
                table_name = list(table_info.values())[0]
                table_data = {"name": table_name, "columns": [], "sample_data": []}
                
                # Få kolonnestruktur
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                table_data["columns"] = columns
                
                # Få eksempeldata (max 5 rækker)
                try:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                    sample_rows = cursor.fetchall()
                    table_data["sample_data"] = sample_rows
                except Error as e:
                    table_data["sample_data"] = [{"error": str(e)}]
                
                result["tables"].append(table_data)
            
            # Test nogle specifikke queries der er relevante for sample storage
            result["specific_queries"] = {}
            
            # Test query for samples i storage
            cursor.execute("""
                SELECT 
                    s.SampleID, s.PartNumber, s.Description, s.Status, 
                    ss.AmountRemaining, u.UnitName,
                    sl.LocationName
                FROM Sample s
                LEFT JOIN SampleStorage ss ON s.SampleID = ss.SampleID
                LEFT JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
                LEFT JOIN Unit u ON s.UnitID = u.UnitID
                WHERE s.Status = 'In Storage'
                LIMIT 10
            """)
            result["specific_queries"]["samples_in_storage"] = cursor.fetchall()
            
            # Test med flere kolonner
            cursor.execute("""
                SELECT 
                    s.SampleID, s.PartNumber, s.Description, s.Status, 
                    ss.AmountRemaining, u.UnitName,
                    sl.LocationName, s.IsUnique, r.ReceivedDate,
                    DATE_FORMAT(s.TimestampCreated, '%Y-%m-%d %H:%i') AS Registered
                FROM Sample s
                LEFT JOIN SampleStorage ss ON s.SampleID = ss.SampleID
                LEFT JOIN StorageLocation sl ON ss.LocationID = sl.LocationID
                LEFT JOIN Unit u ON s.UnitID = u.UnitID
                LEFT JOIN Reception r ON s.ReceptionID = r.ReceptionID
                LIMIT 10
            """)
            result["specific_queries"]["detailed_samples"] = cursor.fetchall()
            
            # Counts
            cursor.execute("SELECT COUNT(*) AS Sample_Count FROM Sample")
            result["specific_queries"]["sample_count"] = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(*) AS SampleStorage_Count FROM SampleStorage")
            result["specific_queries"]["samplestorage_count"] = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(*) AS SampleStorage_Count FROM SampleStorage WHERE AmountRemaining > 0")
            result["specific_queries"]["samples_with_amount"] = cursor.fetchone()
            
    except Error as e:
        result["error"] = str(e)
    
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
    
    return result

if __name__ == "__main__":
    # Få data
    db_info = get_db_structure_and_sample_data()
    
    # Konverter datetime-objekter til strenge for JSON-serialisering
    def json_serial(obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        raise TypeError(f"Type {type(obj)} not serializable")
    
    # Gem til fil
    with open('db_structure_and_data.json', 'w') as f:
        json.dump(db_info, f, default=json_serial, indent=2)
    
    print("Database struktur og eksempeldata er gemt i 'db_structure_and_data.json'")