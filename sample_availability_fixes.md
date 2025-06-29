# Sample Availability Issue - Specific Solutions

## Problem
Sample 32 shows "Available: 0" when trying to move to test, preventing test assignment.

## Root Cause Analysis

### 1. Availability Calculation Logic
The system uses `COALESCE(SUM(AmountRemaining), 0)` from `samplestorage` table:
- If `AmountRemaining = 0` for all records → Available = 0
- If no `samplestorage` records exist → Available = 0
- If sample has active test allocations → Available = AmountRemaining - AllocatedToTests

### 2. Status Filtering
Samples must have `Status = 'In Storage'` to be available for tests.

### 3. Task-Specific Logic
For task-assigned samples, additional filtering applies with allocated amounts.

## Specific Solutions

### Solution 1: Data Reconciliation Query
```sql
-- Check current state of sample 32
SELECT 
    s.SampleID, s.Description, s.Status, s.Amount as OriginalAmount,
    ss.StorageID, ss.AmountRemaining, ss.LocationID,
    COALESCE(SUM(tsu.AmountAllocated), 0) as AllocatedToTests
FROM sample s
LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
LEFT JOIN testsampleusage tsu ON s.SampleID = tsu.SampleID 
    AND tsu.Status IN ('Allocated', 'Active')
WHERE s.SampleID = 32
GROUP BY s.SampleID, s.Description, s.Status, s.Amount, ss.StorageID, ss.AmountRemaining, ss.LocationID;
```

### Solution 2: Fix Missing or Incorrect AmountRemaining
```sql
-- If samplestorage.AmountRemaining is 0 but should have amount:
UPDATE samplestorage 
SET AmountRemaining = (
    SELECT Amount 
    FROM sample 
    WHERE sample.SampleID = samplestorage.SampleID
) 
WHERE SampleID = 32 AND AmountRemaining = 0;
```

### Solution 3: Fix Sample Status
```sql
-- If sample status is incorrect:
UPDATE sample 
SET Status = 'In Storage' 
WHERE SampleID = 32 AND Status != 'In Storage';
```

### Solution 4: Create Missing SampleStorage Record
```sql
-- If no samplestorage record exists:
INSERT INTO samplestorage (SampleID, LocationID, AmountRemaining)
SELECT 
    SampleID, 
    1 as LocationID, -- Default location
    Amount
FROM sample 
WHERE SampleID = 32 
AND NOT EXISTS (SELECT 1 FROM samplestorage WHERE SampleID = 32);
```

### Solution 5: Enhanced Error Handling in Frontend
Add to `test_service.py` add_samples_to_test function around line 198:

```python
if available < amount:
    # Enhanced error message with debugging info
    cursor.execute("""
        SELECT 
            s.Status,
            s.Amount as OriginalAmount,
            COUNT(ss.StorageID) as StorageRecords,
            COALESCE(SUM(ss.AmountRemaining), 0) as TotalRemaining,
            COALESCE(SUM(tsu.AmountAllocated), 0) as AllocatedToTests
        FROM sample s
        LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
        LEFT JOIN testsampleusage tsu ON s.SampleID = tsu.SampleID 
            AND tsu.Status IN ('Allocated', 'Active')
        WHERE s.SampleID = %s
        GROUP BY s.SampleID, s.Status, s.Amount
    """, (sample_id,))
    
    debug_info = cursor.fetchone()
    
    detailed_error = f'Insufficient amount for sample {sample_id}. '
    detailed_error += f'Available: {available}, Requested: {amount}. '
    
    if debug_info:
        detailed_error += f'Debug info - Status: {debug_info[0]}, '
        detailed_error += f'Original Amount: {debug_info[1]}, '
        detailed_error += f'Storage Records: {debug_info[2]}, '
        detailed_error += f'Total Remaining: {debug_info[3]}, '
        detailed_error += f'Allocated to Tests: {debug_info[4]}'
    
    return {
        'success': False,
        'error': detailed_error
    }
```

### Solution 6: Improved Container Move Logic
Update the container service to better handle amount tracking:

```python
# In container_service.py, enhance the add_sample_to_container method
# After moving samples, ensure AmountRemaining is properly updated:

if amount >= sample_amount_remaining:
    # Moving ALL items - update the container location but preserve amount tracking
    cursor.execute("""
        UPDATE SampleStorage 
        SET LocationID = (SELECT LocationID FROM container WHERE ContainerID = %s)
        WHERE StorageID = %s
    """, (container_id, storage_id))
else:
    # Moving SOME items - ensure both samples maintain correct amounts
    # ... (existing logic)
    
    # IMPORTANT: Verify that the sum of amounts equals original
    cursor.execute("""
        SELECT 
            s.Amount as OriginalAmount,
            COALESCE(SUM(ss.AmountRemaining), 0) as CurrentTotal
        FROM sample s
        LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
        WHERE s.SampleID = %s
        GROUP BY s.Amount
    """, (sample_id,))
    
    verification = cursor.fetchone()
    if verification and verification[1] != verification[0]:
        # Amount mismatch detected - log warning
        print(f"WARNING: Amount mismatch for sample {sample_id}. "
              f"Original: {verification[0]}, Current Total: {verification[1]}")
```

### Solution 7: Immediate Fix Script
```python
# Create a maintenance script to fix sample 32 specifically:
def fix_sample_32():
    with db.transaction() as cursor:
        # 1. Check current state
        cursor.execute("""
            SELECT s.SampleID, s.Amount, s.Status, 
                   COALESCE(SUM(ss.AmountRemaining), 0) as CurrentRemaining
            FROM sample s
            LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
            WHERE s.SampleID = 32
            GROUP BY s.SampleID, s.Amount, s.Status
        """)
        
        current_state = cursor.fetchone()
        if not current_state:
            print("Sample 32 not found")
            return
        
        sample_id, original_amount, status, current_remaining = current_state
        
        # 2. Fix status if needed
        if status != 'In Storage':
            cursor.execute("UPDATE sample SET Status = 'In Storage' WHERE SampleID = 32")
            print(f"Updated sample 32 status from '{status}' to 'In Storage'")
        
        # 3. Fix amount if needed
        if current_remaining == 0 and original_amount > 0:
            # Check if samplestorage record exists
            cursor.execute("SELECT COUNT(*) FROM samplestorage WHERE SampleID = 32")
            storage_count = cursor.fetchone()[0]
            
            if storage_count == 0:
                # Create missing samplestorage record
                cursor.execute("""
                    INSERT INTO samplestorage (SampleID, LocationID, AmountRemaining)
                    VALUES (32, 1, %s)
                """, (original_amount,))
                print(f"Created missing samplestorage record for sample 32 with amount {original_amount}")
            else:
                # Update existing record
                cursor.execute("""
                    UPDATE samplestorage 
                    SET AmountRemaining = %s 
                    WHERE SampleID = 32
                """, (original_amount,))
                print(f"Updated samplestorage AmountRemaining to {original_amount} for sample 32")
        
        # 3. Verify fix
        cursor.execute("""
            SELECT COALESCE(SUM(AmountRemaining), 0) 
            FROM samplestorage 
            WHERE SampleID = 32
        """)
        new_available = cursor.fetchone()[0]
        print(f"Sample 32 now has {new_available} units available")
```

## Prevention Measures

### 1. Add Data Validation Triggers
```sql
DELIMITER //
CREATE TRIGGER validate_sample_amounts
    BEFORE UPDATE ON samplestorage
    FOR EACH ROW
BEGIN
    IF NEW.AmountRemaining < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'AmountRemaining cannot be negative';
    END IF;
END//
DELIMITER ;
```

### 2. Regular Data Consistency Checks
```sql
-- Query to find samples with potential issues
SELECT 
    s.SampleID,
    s.Description,
    s.Amount as OriginalAmount,
    COALESCE(SUM(ss.AmountRemaining), 0) as CurrentRemaining,
    s.Status,
    CASE 
        WHEN s.Status = 'In Storage' AND COALESCE(SUM(ss.AmountRemaining), 0) = 0 THEN 'ISSUE: Zero remaining but In Storage'
        WHEN s.Status != 'In Storage' AND COALESCE(SUM(ss.AmountRemaining), 0) > 0 THEN 'ISSUE: Has remaining but not In Storage'
        WHEN COUNT(ss.StorageID) = 0 THEN 'ISSUE: No storage records'
        ELSE 'OK'
    END as Status_Check
FROM sample s
LEFT JOIN samplestorage ss ON s.SampleID = ss.SampleID
GROUP BY s.SampleID, s.Description, s.Amount, s.Status
HAVING Status_Check LIKE 'ISSUE:%'
ORDER BY s.SampleID;
```

### 3. Enhanced Frontend Validation
Add validation in the testing interface to provide better feedback when samples are unavailable.

## Implementation Priority

1. **Immediate**: Run Solution 7 (fix script) to resolve sample 32 specifically
2. **Short-term**: Implement Solution 5 (enhanced error handling) for better debugging
3. **Medium-term**: Add Solutions 1-4 as maintenance procedures
4. **Long-term**: Implement prevention measures (triggers and consistency checks)