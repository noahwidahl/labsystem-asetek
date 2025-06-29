# DATABASE UPDATE REQUIRED

Before testing the new functionality, you MUST run these SQL commands:

## 1. Container Barcode Support:
```sql
ALTER TABLE container ADD COLUMN Barcode VARCHAR(100) UNIQUE AFTER ContainerID;
```

## 2. Sample Serial Number Support:
```sql
-- Create proper serial number table for multiple serial numbers per sample
CREATE TABLE IF NOT EXISTS sampleserialnumber (
    SerialNumberID INT AUTO_INCREMENT PRIMARY KEY,
    SampleID INT NOT NULL,
    SerialNumber VARCHAR(255) NOT NULL,
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    IsActive BOOLEAN DEFAULT TRUE,
    INDEX idx_sample_serial (SampleID),
    INDEX idx_serial_number (SerialNumber),
    FOREIGN KEY (SampleID) REFERENCES sample(SampleID) ON DELETE CASCADE,
    UNIQUE KEY unique_serial_number (SerialNumber)
);

-- Remove incorrect single SerialNumber column if it exists
ALTER TABLE sample DROP COLUMN IF EXISTS SerialNumber;
```

## What this update does:
- Adds a `Barcode` field to the `container` table
- Makes it UNIQUE to prevent duplicate container barcodes
- Places it right after the `ContainerID` field

## After running the SQL:
1. New containers will automatically get CNT-xxx barcodes
2. The scanner will be able to find containers by their CNT- barcodes
3. Container labels will include the generated barcode

## Scanner Changes Made:
✅ Removed TST- test sample barcode support (not used in database)
✅ Updated to support your actual BC-format sample barcodes  
✅ Simplified to only 2 barcode types: CNT- (containers) and BC-/SMP- (samples)
✅ Fixed sample status display (In Storage, In Test, Consumed etc.)

## New Barcode System:
- **CNT-1, CNT-2, CNT-3** = Containers (with auto-generated barcodes)
- **BC23-1751211213, SMP-29** = Samples (existing format + SMP- for Sample ID)
- **No more TST-** format (was causing "invalid barcode format" errors)

Test by:
1. Creating a new container → should get CNT-barcode automatically
2. Scanning the CNT-barcode → should show container details
3. Scanning existing BC- sample barcodes → should work as before