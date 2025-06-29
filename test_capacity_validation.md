# Container Capacity Validation Test Scenarios

## Test Cases Added

### 1. **Sample Registration - New Container Capacity Check**
**Location:** `app/services/sample_service.py`
- ✅ Validates sample amount against container capacity before creating container
- ✅ Checks both existing container types and new container types
- ✅ Returns error if sample amount exceeds capacity

### 2. **Sample Registration - Existing Container Capacity Check**
**Location:** `app/services/sample_service.py`
- ✅ Validates sample amount against existing container's available capacity
- ✅ Calculates current usage and available space
- ✅ Returns error if adding sample would exceed capacity

### 3. **Container Service - Add Sample Validation**
**Location:** `app/services/container_service.py`
- ✅ Enhanced existing capacity check with better error messages
- ✅ Shows available space in error message
- ✅ Works with force_add parameter to override if needed

### 4. **Frontend Validation - Real-time Capacity Checks**
**Location:** `app/static/js/register-validation.js` and `app/static/js/register-containers.js`
- ✅ Validates capacity during form submission
- ✅ Real-time validation when amount or container type changes
- ✅ Shows warning messages for capacity issues
- ✅ Validates both existing and new containers

## Test Scenarios to Validate

### Scenario 1: Register 50 samples in container with capacity 30
**Expected:** Error message: "Sample amount (50) exceeds container capacity (30)"

### Scenario 2: Add 6 samples to existing container with 25/30 capacity
**Expected:** Error message: "Cannot add 6 samples to container. Container has 5 of 30 units available (current: 25)"

### Scenario 3: Create new container type with capacity 20, try to register 25 samples
**Expected:** Error message: "Sample amount (25) exceeds container capacity (20)"

### Scenario 4: Select existing container via dropdown that shows "5/100 available", try to register 10 samples
**Expected:** Warning message: "Sample amount (10) exceeds available container capacity (5)"

## Implementation Details

### Backend Validation Points:
1. `sample_service.create_sample()` - Checks capacity before container creation
2. `container_service.add_sample_to_container()` - Validates on sample addition
3. Both services return detailed error messages with current/available amounts

### Frontend Validation Points:
1. Form submission validation in step 2
2. Real-time validation on input changes
3. Warning display system with visual feedback
4. Capacity parsing from container dropdown text

### Database Queries Added:
```sql
-- Check existing container capacity
SELECT c.ContainerCapacity, IFNULL(SUM(cs.Amount), 0) as CurrentAmount
FROM container c
LEFT JOIN ContainerSample cs ON c.ContainerID = cs.ContainerID
WHERE c.ContainerID = ? GROUP BY c.ContainerID, c.ContainerCapacity

-- Check container type capacity
SELECT DefaultCapacity FROM ContainerType WHERE ContainerTypeID = ?
```

## Error Message Examples:

### Registration Errors:
- "Sample amount (50) exceeds container capacity (30). Please choose a larger container type or reduce the sample amount."
- "Cannot add 25 samples to container. Current: 20, Capacity: 30, Available: 10"

### API Errors:
- "Cannot add 6 samples to container. Container has 5 of 30 units available (current: 25)"

### Frontend Warnings:
- "Sample amount (10) exceeds available container capacity (5)"
- "Sample amount (25) exceeds container capacity (20). Please choose a larger container type or reduce the sample amount."