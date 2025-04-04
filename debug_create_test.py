#!/usr/bin/env python3

"""
This script helps debug the test creation process by making a direct HTTP request
to the createTest API endpoint with mock data.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# URL to create test API endpoint
API_URL = "http://localhost:5000/api/createTest"

# Sample data for creating a test
test_data = {
    "type": "Debug Test",
    "owner": 1,  # Assuming user ID 1 exists
    "samples": [
        {"id": 1, "amount": 1}  # Assuming sample ID 1 exists
    ],
    "description": "Created by debug script"
}

# Headers for JSON request
headers = {
    "Content-Type": "application/json"
}

try:
    # Make the API request
    print(f"Sending request to {API_URL} with data: {json.dumps(test_data, indent=2)}")
    response = requests.post(API_URL, json=test_data, headers=headers)
    
    # Print response status and content
    print(f"Response status: {response.status_code}")
    
    if response.ok:
        print("Success!")
        print(f"Response content: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Error: {response.status_code}")
        print(f"Response content: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)