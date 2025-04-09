"""
Test script for multiple identical samples with direct storage.
This script will test both cases:
1. Multiple identical samples with separate storage (different locations)
2. Multiple identical samples without separate storage (same location)
"""

from flask import Flask, request, jsonify
from app.services.sample_service import SampleService
from app.utils.db import DatabaseManager

app = Flask(__name__)

@app.route('/test_direct_storage', methods=['GET'])
def test_direct_storage():
    # Create a test sample data with multiple identical samples
    sample_data = {
        'description': 'Test Multiple Samples',
        'totalAmount': 10,
        'unit': 1,
        'sampleType': 'multiple',
        'isMultiPackage': True,
        'packageCount': 2,
        'amountPerPackage': 5,
        'storageOption': 'direct',
        'owner': 1,
        'expiryDate': '2023-12-31'
    }
    
    results = []
    
    # Test Case 1: Multiple samples with separate storage (different locations)
    test_data_1 = sample_data.copy()
    test_data_1['separateStorage'] = True
    test_data_1['differentLocations'] = True
    test_data_1['packageLocations'] = [
        {'packageNumber': 1, 'locationId': 1},
        {'packageNumber': 2, 'locationId': 2}
    ]
    
    # Test Case 2: Multiple samples without separate storage (same location)
    test_data_2 = sample_data.copy()
    test_data_2['separateStorage'] = False
    test_data_2['storageLocation'] = 3  # Use location ID 3 for all samples
    
    # Print test data for inspection
    print("Test Case 1 (Separate Storage):", test_data_1)
    print("Test Case 2 (Combined Storage):", test_data_2)
    
    return jsonify({
        'message': 'Test data prepared for direct storage tests',
        'test_case_1': test_data_1,
        'test_case_2': test_data_2
    })

if __name__ == '__main__':
    app.run(debug=True)