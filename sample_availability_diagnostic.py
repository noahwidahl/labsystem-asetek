#!/usr/bin/env python3
"""
Sample Availability Diagnostic and Fix Tool
This script helps diagnose and fix sample availability issues like sample 32 showing "Available: 0"
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def diagnose_sample(sample_id, connection=None):
    """
    Diagnose availability issues for a specific sample
    
    Args:
        sample_id (int): The sample ID to diagnose
        connection: Database connection object (if using Flask-SQLAlchemy or similar)
    
    Returns:
        dict: Diagnostic results and recommendations
    """
    
    # For demonstration purposes, this shows the SQL queries that would be used
    # In a real implementation, you would execute these against your database
    
    print(f"=== DIAGNOSTIC REPORT FOR SAMPLE {sample_id} ===\n")
    
    # Query 1: Basic sample information
    basic_query = f"""
    SELECT 
        SampleID, Description, PartNumber, Status, Amount, Barcode, Type, TaskID
    FROM sample 
    WHERE SampleID = {sample_id};
    """
    print("1. Basic Sample Data Query:")
    print(basic_query)
    print()
    
    # Query 2: Storage information
    storage_query = f"""
    SELECT 
        StorageID, SampleID, LocationID, AmountRemaining, ExpireDate
    FROM samplestorage 
    WHERE SampleID = {sample_id};
    """
    print("2. Storage Data Query:")
    print(storage_query)
    print()
    
    # Query 3: Test allocations
    test_allocation_query = f"""
    SELECT 
        UsageID, TestID, SampleIdentifier, AmountAllocated, 
        AmountUsed, AmountReturned, Status, CreatedDate
    FROM testsampleusage 
    WHERE SampleID = {sample_id}
    ORDER BY CreatedDate DESC;
    """
    print("3. Test Allocations Query:")
    print(test_allocation_query)
    print()
    
    # Query 4: Availability calculation (same as test service)
    availability_query = f"""
    SELECT COALESCE(SUM(AmountRemaining), 0) as Available
    FROM samplestorage 
    WHERE SampleID = {sample_id};
    """
    print("4. Current Availability Calculation:")
    print(availability_query)
    print()
    
    # Query 5: Comprehensive diagnostic
    comprehensive_query = f"""
    SELECT 
        s.SampleID,
        s.Description,
        s.Status,
        s.Amount as OriginalAmount,
        COUNT(ss.StorageID) as StorageRecords,
        COALESCE(SUM(ss.AmountRemaining), 0) as TotalRemaining,
        COALESCE(SUM(CASE 
            WHEN tsu.Status IN ('Allocated', 'Active') 
            THEN tsu.AmountAllocated 
            ELSE 0 
        END), 0) as AllocatedToTests,
        (COALESCE(SUM(ss.AmountRemaining), 0) - COALESCE(SUM(CASE 
            WHEN tsu.Status IN ('Allocated', 'Active') 
            THEN tsu.AmountAllocated 
            ELSE 0 
        END), 0)) as EffectivelyAvailable
    FROM sample s
    LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
    LEFT JOIN testsampleusage tsu ON s.SampleID = tsu.SampleID
    WHERE s.SampleID = {sample_id}
    GROUP BY s.SampleID, s.Description, s.Status, s.Amount;
    """
    print("5. Comprehensive Diagnostic Query:")
    print(comprehensive_query)
    print()
    
    # Query 6: Container relationships
    container_query = f"""
    SELECT 
        cs.ContainerSampleID, cs.ContainerID, cs.Amount,
        c.Description as ContainerDescription,
        c.ContainerCapacity,
        sl.LocationName as ContainerLocation
    FROM containersample cs
    JOIN samplestorage ss ON cs.SampleStorageID = ss.StorageID
    JOIN container c ON cs.ContainerID = c.ContainerID
    LEFT JOIN storagelocation sl ON c.LocationID = sl.LocationID
    WHERE ss.SampleID = {sample_id};
    """
    print("6. Container Relationships Query:")
    print(container_query)
    print()
    
    return {
        'queries': {
            'basic': basic_query,
            'storage': storage_query,
            'test_allocations': test_allocation_query,
            'availability': availability_query,
            'comprehensive': comprehensive_query,
            'containers': container_query
        }
    }

def generate_fix_queries(sample_id, issue_type):
    """
    Generate SQL fix queries based on the diagnosed issue type
    
    Args:
        sample_id (int): The sample ID to fix
        issue_type (str): Type of issue ('zero_remaining', 'wrong_status', 'missing_storage', 'active_allocations')
    
    Returns:
        list: List of SQL queries to fix the issue
    """
    
    fixes = []
    
    if issue_type == 'zero_remaining':
        fixes.append({
            'description': 'Restore AmountRemaining from original sample amount',
            'query': f"""
            UPDATE samplestorage 
            SET AmountRemaining = (
                SELECT Amount 
                FROM sample 
                WHERE sample.SampleID = samplestorage.SampleID
            ) 
            WHERE SampleID = {sample_id} AND AmountRemaining = 0;
            """
        })
    
    elif issue_type == 'wrong_status':
        fixes.append({
            'description': 'Fix sample status to In Storage',
            'query': f"""
            UPDATE sample 
            SET Status = 'In Storage' 
            WHERE SampleID = {sample_id} AND Status != 'In Storage';
            """
        })
    
    elif issue_type == 'missing_storage':
        fixes.append({
            'description': 'Create missing samplestorage record',
            'query': f"""
            INSERT INTO samplestorage (SampleID, LocationID, AmountRemaining)
            SELECT 
                SampleID, 
                1 as LocationID, -- Default location
                Amount
            FROM sample 
            WHERE SampleID = {sample_id} 
            AND NOT EXISTS (SELECT 1 FROM samplestorage WHERE SampleID = {sample_id});
            """
        })
    
    elif issue_type == 'active_allocations':
        fixes.append({
            'description': 'Check and potentially fix active test allocations',
            'query': f"""
            -- First, check which tests have active allocations
            SELECT 
                tsu.TestID, t.TestNo, t.Status as TestStatus,
                tsu.AmountAllocated, tsu.Status as AllocationStatus
            FROM testsampleusage tsu
            JOIN test t ON tsu.TestID = t.TestID
            WHERE tsu.SampleID = {sample_id} 
            AND tsu.Status IN ('Allocated', 'Active');
            
            -- If test is completed but allocation is still active, update it:
            -- UPDATE testsampleusage 
            -- SET Status = 'Returned', AmountReturned = AmountAllocated
            -- WHERE SampleID = {sample_id} 
            -- AND TestID IN (SELECT TestID FROM test WHERE Status = 'Completed')
            -- AND Status IN ('Allocated', 'Active');
            """
        })
    
    elif issue_type == 'comprehensive_fix':
        # A comprehensive fix that addresses multiple potential issues
        fixes.extend([
            {
                'description': 'Step 1: Ensure sample has correct status',
                'query': f"""
                UPDATE sample 
                SET Status = CASE 
                    WHEN EXISTS (
                        SELECT 1 FROM testsampleusage tsu 
                        WHERE tsu.SampleID = sample.SampleID 
                        AND tsu.Status IN ('Allocated', 'Active')
                    ) THEN 'In Test'
                    WHEN EXISTS (
                        SELECT 1 FROM samplestorage ss 
                        WHERE ss.SampleID = sample.SampleID 
                        AND ss.AmountRemaining > 0
                    ) THEN 'In Storage'
                    ELSE 'Consumed'
                END
                WHERE SampleID = {sample_id};
                """
            },
            {
                'description': 'Step 2: Create samplestorage record if missing',
                'query': f"""
                INSERT INTO samplestorage (SampleID, LocationID, AmountRemaining)
                SELECT 
                    s.SampleID, 
                    COALESCE(
                        (SELECT LocationID FROM samplestorage WHERE SampleID = s.SampleID LIMIT 1),
                        1
                    ) as LocationID,
                    s.Amount
                FROM sample s
                WHERE s.SampleID = {sample_id} 
                AND NOT EXISTS (SELECT 1 FROM samplestorage WHERE SampleID = s.SampleID);
                """
            },
            {
                'description': 'Step 3: Reconcile amounts if needed',
                'query': f"""
                UPDATE samplestorage ss
                JOIN sample s ON ss.SampleID = s.SampleID
                SET ss.AmountRemaining = GREATEST(
                    s.Amount - COALESCE((
                        SELECT SUM(tsu.AmountAllocated - COALESCE(tsu.AmountReturned, 0))
                        FROM testsampleusage tsu 
                        WHERE tsu.SampleID = s.SampleID 
                        AND tsu.Status IN ('Allocated', 'Active')
                    ), 0),
                    0
                )
                WHERE s.SampleID = {sample_id}
                AND ss.AmountRemaining = 0;
                """
            }
        ])
    
    return fixes

def print_common_issues_and_solutions():
    """Print common sample availability issues and their solutions"""
    
    print("\n=== COMMON SAMPLE AVAILABILITY ISSUES AND SOLUTIONS ===\n")
    
    issues = [
        {
            'issue': 'Sample shows Available: 0',
            'causes': [
                'samplestorage.AmountRemaining = 0',
                'Sample status is not "In Storage"',
                'No samplestorage records exist',
                'Sample has active test allocations'
            ],
            'diagnostic_steps': [
                'Check sample status',
                'Check samplestorage records',
                'Check active test allocations',
                'Verify original sample amount'
            ]
        },
        {
            'issue': 'Sample not appearing in available lists',
            'causes': [
                'Status filtering (Status != "In Storage")',
                'Task-specific filtering',
                'Amount filtering (AmountRemaining <= 0)',
                'Database query joins failing'
            ],
            'diagnostic_steps': [
                'Check WHERE clauses in queries',
                'Verify JOIN conditions',
                'Check HAVING clauses',
                'Verify sample meets all criteria'
            ]
        },
        {
            'issue': 'Amount tracking inconsistencies',
            'causes': [
                'Container moves not updating amounts properly',
                'Test allocations/returns not balanced',
                'Manual data changes',
                'Concurrent access issues'
            ],
            'diagnostic_steps': [
                'Compare sample.Amount vs SUM(samplestorage.AmountRemaining)',
                'Check test allocation vs return amounts',
                'Audit container move history',
                'Check for orphaned records'
            ]
        }
    ]
    
    for i, issue_info in enumerate(issues, 1):
        print(f"{i}. {issue_info['issue']}")
        print("   Possible Causes:")
        for cause in issue_info['causes']:
            print(f"   - {cause}")
        print("   Diagnostic Steps:")
        for step in issue_info['diagnostic_steps']:
            print(f"   - {step}")
        print()

if __name__ == "__main__":
    print("Sample Availability Diagnostic Tool")
    print("===================================")
    
    if len(sys.argv) > 1:
        try:
            sample_id = int(sys.argv[1])
            print(f"Diagnosing Sample ID: {sample_id}")
            diagnose_sample(sample_id)
            
            if len(sys.argv) > 2:
                issue_type = sys.argv[2]
                print(f"\nGenerating fix queries for issue type: {issue_type}")
                fixes = generate_fix_queries(sample_id, issue_type)
                for i, fix in enumerate(fixes, 1):
                    print(f"\nFix {i}: {fix['description']}")
                    print(fix['query'])
            
        except ValueError:
            print("Error: Sample ID must be a number")
    else:
        print("Usage: python sample_availability_diagnostic.py <sample_id> [issue_type]")
        print("Issue types: zero_remaining, wrong_status, missing_storage, active_allocations, comprehensive_fix")
        print("\nFor Sample 32 specifically:")
        print("python sample_availability_diagnostic.py 32 comprehensive_fix")
    
    print_common_issues_and_solutions()