import os
import sys
sys.path.append('.')

# Set environment variables
os.environ['MSSQL_SERVER'] = 'localhost'
os.environ['MSSQL_DATABASE'] = 'labsystem'
os.environ['MSSQL_USERNAME'] = 'root'
os.environ['MSSQL_PASSWORD'] = 'test'
os.environ['MSSQL_DRIVER'] = 'ODBC Driver 18 for SQL Server'
os.environ['MSSQL_TRUST_CERT'] = 'yes'

try:
    from app.utils.mssql_db import mssql_db

    print("=== CONTAINER TABLE STRUCTURE ===")
    try:
        columns = mssql_db.execute_query("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'container'
            ORDER BY ORDINAL_POSITION
        """, fetch_all=True)
        
        print("Available columns:")
        for col in columns:
            print(f"  {col[0]} ({col[1]}) - Nullable: {col[2]} - Default: {col[3]}")
            
    except Exception as e:
        print(f"Error getting columns: {e}")

    print("\n=== CONTAINERTYPE TABLE ===")
    try:
        types = mssql_db.execute_query("""
            SELECT ContainerTypeID, TypeName, DefaultCapacity
            FROM [containertype]
            ORDER BY ContainerTypeID DESC
        """, fetch_all=True)
        
        print(f"Container types ({len(types)} found):")
        for t in types:
            print(f"  ID: {t[0]}, Name: {t[1]}, Capacity: {t[2]}")
            
    except Exception as e:
        print(f"Error getting container types: {e}")

    print("\n=== TEST CONTAINER CREATION ===")
    try:
        # Test creating a container similar to what the code does
        test_barcode = "TEST123"
        container_type_id = 4  # The one we saw created
        description = "Test container"
        location_id = 30
        is_mixed = False
        
        print(f"Attempting to create container with:")
        print(f"  Barcode: {test_barcode}")
        print(f"  ContainerTypeID: {container_type_id}")
        print(f"  Description: {description}")
        print(f"  LocationID: {location_id}")
        print(f"  IsMixed: {is_mixed}")
        
        result = mssql_db.execute_query("""
            INSERT INTO [container] ([Barcode], [ContainerTypeID], [Description], [LocationID], [ContainerCapacity], [ContainerStatus], [IsMixed])
            OUTPUT INSERTED.ContainerID
            SELECT ?, ?, ?, ?, [DefaultCapacity], 'Active', ?
            FROM [containertype] WHERE [ContainerTypeID] = ?
        """, (
            test_barcode,
            container_type_id,
            description,
            location_id,
            is_mixed,
            container_type_id
        ), fetch_one=True)
        
        if result:
            print(f"SUCCESS: Created container with ID: {result[0]}")
        else:
            print("FAILED: No result returned")
            
    except Exception as e:
        print(f"Error creating test container: {e}")
        import traceback
        traceback.print_exc()

    print("\n=== EXISTING CONTAINERS ===")
    try:
        containers = mssql_db.execute_query("""
            SELECT TOP 5 ContainerID, Description, ContainerTypeID, LocationID, ContainerCapacity, ContainerStatus, IsMixed, Barcode
            FROM [container] 
            ORDER BY ContainerID DESC
        """, fetch_all=True)
        
        print(f"Recent containers ({len(containers)} found):")
        for c in containers:
            print(f"  ID: {c[0]}, Desc: '{c[1]}', Type: {c[2]}, Loc: {c[3]}, Cap: {c[4]}, Status: '{c[5]}', Mixed: {c[6]}, Barcode: '{c[7]}'")
            
    except Exception as e:
        print(f"Error getting containers: {e}")

except Exception as e:
    print(f"Import error: {e}")
    import traceback
    traceback.print_exc()