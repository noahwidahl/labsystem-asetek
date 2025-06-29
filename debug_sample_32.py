#!/usr/bin/env python3
"""
Debug script for sample availability issue
Specifically checks sample 32 to understand why it shows "Available: 0"
"""

import mysql.connector
from mysql.connector import Error

def check_sample_32():
    """Check sample 32's data and availability calculation"""
    print("=== DEBUG: Sample 32 Availability Investigation ===\n")
    
    try:
        # Connect to database using same credentials as db_explorer.py
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='0LLEbr0dR00T!',
            database='lab_system'
        )
        
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
        
        # 1. Check basic sample data
        print("1. Basic Sample Data:")
        print("-" * 40)
        cursor.execute("""
            SELECT 
                SampleID, Description, PartNumber, Status, Amount, Barcode, Type, TaskID
            FROM sample 
            WHERE SampleID = 32
        """)
        sample_data = cursor.fetchone()
        
        if not sample_data:
            print("ERROR: Sample 32 not found!")
            return
        
        for key, value in sample_data.items():
            print(f"{key}: {value}")
        print()
        
        # 2. Check samplestorage data
        print("2. Sample Storage Data:")
        print("-" * 40)
        cursor.execute("""
            SELECT 
                StorageID, SampleID, LocationID, AmountRemaining, ExpireDate
            FROM samplestorage 
            WHERE SampleID = 32
        """)
        storage_data = cursor.fetchall()
        
        if not storage_data:
            print("ERROR: No storage records found for sample 32!")
        else:
            for record in storage_data:
                for key, value in record.items():
                    print(f"{key}: {value}")
                print()
        
        # 3. Check test allocations
        print("3. Test Sample Usage (Active Allocations):")
        print("-" * 40)
        cursor.execute("""
            SELECT 
                UsageID, TestID, SampleIdentifier, AmountAllocated, 
                AmountUsed, AmountReturned, Status, CreatedDate
            FROM testsampleusage 
            WHERE SampleID = 32
            ORDER BY CreatedDate DESC
        """)
        test_usage = cursor.fetchall()
        
        if not test_usage:
            print("No test usage records found")
        else:
            for record in test_usage:
                for key, value in record.items():
                    print(f"{key}: {value}")
                print()
        
        # 4. Calculate availability using the same logic as add_samples_to_test
        print("4. Availability Calculation (Same as add_samples_to_test):")
        print("-" * 40)
        cursor.execute("""
            SELECT COALESCE(SUM(AmountRemaining), 0) 
            FROM samplestorage 
            WHERE SampleID = 32
        """)
        available = cursor.fetchone()
        available_amount = available['COALESCE(SUM(AmountRemaining), 0)'] if available else 0
        print(f"Available amount (SUM of AmountRemaining): {available_amount}")
        print()
        
        # 5. Check the testing page query logic
        print("5. Testing Page Query Logic:")
        print("-" * 40)
        cursor.execute("""
            SELECT 
                s.SampleID, 
                s.Description, 
                s.PartNumber,
                COALESCE(SUM(ss.AmountRemaining), s.Amount, 1) as AmountAvailable,
                sl.LocationName,
                s.Status
            FROM sample s
            LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
            LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
            WHERE s.SampleID = 32
            GROUP BY s.SampleID, s.Description, s.PartNumber, sl.LocationName, s.Status, s.Amount
        """)
        testing_page_data = cursor.fetchone()
        
        if testing_page_data:
            for key, value in testing_page_data.items():
                print(f"{key}: {value}")
        print()
        
        # 6. Check for task-specific availability (if sample has TaskID)
        if sample_data.get('TaskID'):
            print("6. Task-Specific Availability (get_available_samples_for_task):")
            print("-" * 40)
            cursor.execute("""
                SELECT 
                    s.SampleID,
                    s.Description,
                    s.PartNumber,
                    s.Barcode,
                    ss.AmountRemaining,
                    COALESCE(sl.LocationName, 'Unknown') as LocationName,
                    CASE
                        WHEN un.UnitName IS NULL THEN 'pcs'
                        WHEN LOWER(un.UnitName) = 'stk' THEN 'pcs'
                        ELSE un.UnitName
                    END as Unit,
                    COALESCE(SUM(tsu.AmountAllocated), 0) as AllocatedToTests
                FROM sample s
                LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
                LEFT JOIN storagelocation sl ON ss.LocationID = sl.LocationID
                LEFT JOIN unit un ON s.UnitID = un.UnitID
                LEFT JOIN testsampleusage tsu ON s.SampleID = tsu.SampleID AND tsu.Status IN ('Allocated', 'Active')
                WHERE s.TaskID = %s AND s.SampleID = 32
                AND s.Status = 'In Storage'
                GROUP BY s.SampleID, s.Description, s.PartNumber, s.Barcode, 
                         ss.AmountRemaining, sl.LocationName, un.UnitName
                HAVING (ss.AmountRemaining - COALESCE(AllocatedToTests, 0)) > 0
            """, (sample_data['TaskID'],))
            
            task_availability = cursor.fetchone()
            if task_availability:
                for key, value in task_availability.items():
                    print(f"{key}: {value}")
                available_for_task = (task_availability.get('AmountRemaining', 0) or 0) - (task_availability.get('AllocatedToTests', 0) or 0)
                print(f"Calculated Available for Task: {available_for_task}")
            else:
                print("Sample 32 not available for its assigned task (may be filtered out)")
        print()
        
        # 7. Check container storage relationships
        print("7. Container Storage Relationships:")
        print("-" * 40)
        cursor.execute("""
            SELECT 
                cs.ContainerSampleID, cs.ContainerID, cs.Amount,
                c.Description as ContainerDescription,
                c.ContainerCapacity,
                sl.LocationName as ContainerLocation
            FROM containersample cs
            JOIN samplestorage ss ON cs.SampleStorageID = ss.StorageID
            JOIN container c ON cs.ContainerID = c.ContainerID
            LEFT JOIN storagelocation sl ON c.LocationID = sl.LocationID
            WHERE ss.SampleID = 32
        """)
        container_data = cursor.fetchall()
        
        if not container_data:
            print("Sample 32 is not stored in any containers")
        else:
            for record in container_data:
                for key, value in record.items():
                    print(f"{key}: {value}")
                print()
        
        # 8. Recommendations
        print("8. Analysis and Recommendations:")
        print("-" * 40)
        
        # Check if sample has AmountRemaining = 0
        total_remaining = sum(record.get('AmountRemaining', 0) or 0 for record in storage_data)
        total_allocated = sum(record.get('AmountAllocated', 0) or 0 for record in test_usage if record.get('Status') in ['Allocated', 'Active'])
        
        print(f"Total AmountRemaining across all storage records: {total_remaining}")
        print(f"Total amount allocated to active tests: {total_allocated}")
        print(f"Sample original amount: {sample_data.get('Amount', 'Unknown')}")
        print(f"Sample status: {sample_data.get('Status', 'Unknown')}")
        
        if total_remaining == 0:
            print("\nISSUE IDENTIFIED: Sample has 0 AmountRemaining")
            print("Possible causes:")
            print("- Sample was fully consumed in tests")
            print("- Sample was moved to containers and amount tracking was lost")
            print("- Data inconsistency between sample.Amount and samplestorage.AmountRemaining")
            
            if total_allocated > 0:
                print("- Sample has active test allocations but no remaining amount")
                print("  This suggests the allocation process may have bugs")
        
        if sample_data.get('Status') != 'In Storage':
            print(f"\nISSUE: Sample status is '{sample_data.get('Status')}', not 'In Storage'")
            print("This will filter it out of available samples lists")
        
        print("\nPossible solutions:")
        print("1. Check if AmountRemaining should be restored from container moves")
        print("2. Verify test allocation/deallocation logic")
        print("3. Update sample status if appropriate")
        print("4. Reconcile sample.Amount with samplestorage.AmountRemaining")
        
        cursor.close()
        connection.close()
        
    except Error as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    check_sample_32()