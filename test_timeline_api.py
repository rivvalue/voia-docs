#!/usr/bin/env python3
"""Test timeline API endpoint with proper Flask context"""

import sys
sys.path.insert(0, '/home/runner/workspace')

from app import app
from flask import session

def test_timeline_api():
    """Test timeline API with authenticated session"""
    with app.test_client() as client:
        with client.session_transaction() as sess:
            # Simulate logged in user for business account ID 1
            sess['business_account_id'] = 1
            sess['business_user_id'] = 1
            sess['business_user_email'] = 'test@test.com'
        
        # Make request to timeline API
        response = client.get('/business/campaigns/api/timeline-data')
        
        print("\n" + "="*60)
        print("Timeline API Test Results")
        print("="*60)
        print(f"\nStatus Code: {response.status_code}")
        print(f"\nResponse Headers:")
        for key, value in response.headers:
            print(f"  {key}: {value}")
        
        print(f"\nResponse Data:")
        if response.is_json:
            import json
            data = response.get_json()
            print(json.dumps(data, indent=2, default=str))
        else:
            print(response.data.decode('utf-8')[:500])
        
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    test_timeline_api()
