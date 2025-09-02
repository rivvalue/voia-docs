#!/usr/bin/env python3
"""Simple token generation test to isolate the issue"""
import subprocess
import json

def test_local_endpoints():
    """Test local token generation"""
    print("=== Testing Local Token Generation ===")
    
    # Test health endpoint
    try:
        health_result = subprocess.run([
            'curl', '-s', 'http://localhost:5000/health'
        ], capture_output=True, text=True, timeout=10)
        
        if health_result.returncode == 0:
            print("✓ Health endpoint working")
            try:
                health_data = json.loads(health_result.stdout)
                print(f"  Status: {health_data.get('status')}")
                print(f"  Database: {health_data.get('database')}")
            except:
                print("  Health response not JSON")
        else:
            print("✗ Health endpoint failed")
    except Exception as e:
        print(f"✗ Health test error: {e}")
    
    # Test token endpoint
    try:
        token_result = subprocess.run([
            'curl', '-s', '-X', 'POST', 
            'http://localhost:5000/auth/request-token',
            '-H', 'Content-Type: application/json',
            '-d', '{"email": "test@example.com"}'
        ], capture_output=True, text=True, timeout=10)
        
        if token_result.returncode == 0:
            print("✓ Token endpoint reachable")
            try:
                token_data = json.loads(token_result.stdout)
                if 'token' in token_data:
                    print(f"✓ Token generated successfully")
                    print(f"  Email: {token_data.get('email')}")
                    print(f"  Expires in: {token_data.get('expires_in')} seconds")
                else:
                    print(f"✗ Token generation failed: {token_data}")
            except:
                print(f"✗ Token response not JSON: {token_result.stdout}")
        else:
            print("✗ Token endpoint failed")
    except Exception as e:
        print(f"✗ Token test error: {e}")

if __name__ == "__main__":
    test_local_endpoints()