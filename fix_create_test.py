#!/usr/bin/env python3

# This script provides a direct fix for the test creation issues
# by examining the issue and updating the test.py model file

import os
import sys
import re

# Path to the file
models_file = 'app/models/test.py'

if not os.path.exists(models_file):
    print(f"Error: Could not find {models_file}")
    sys.exit(1)

print("Fixing Test class's from_dict method...")

# Read the original file
with open(models_file, 'r') as f:
    content = f.read()

# Define a simpler fix for test creation
new_from_dict = """    @classmethod
    def from_dict(cls, data):
        test_type = data.get('type', '')
        
        # Simple approach - use timestamp for test number
        from datetime import datetime
        current_date = datetime.now()
        test_number = current_date.strftime("%d%H%M")  # Day, hour, minute as test number
        iteration = 1
        
        # Format: T1234.5
        test_id = f"T{test_number}.{iteration}"
        
        # Use exactly what was entered as test name
        test_name = test_type
        
        return cls(
            test_no=test_id,
            test_name=test_name,
            description=data.get('description', ''),
            user_id=data.get('owner')
        )"""

# Replace the from_dict method
pattern = re.compile(r'    @classmethod\s+def from_dict\(cls, data\):.*?return cls\(.*?\)', re.DOTALL)
match = pattern.search(content)

if match:
    # Extract the method and replace it
    start, end = match.span()
    replaced_content = content[:start] + new_from_dict + content[end:]
    
    # Write the modified file
    with open(models_file, 'w') as f:
        f.write(replaced_content)
    
    print(f"Successfully updated {models_file}")
    print("The test creation should now work with a simpler approach that doesn't rely on database queries")
else:
    print("Could not find the from_dict method in the Test class")
    sys.exit(1)