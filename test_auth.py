#!/usr/bin/env python3
"""
Test script to verify Django REST API authentication
"""
import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_login():
    """Test login endpoint"""
    print("Testing login endpoint...")
    
    url = f"{BASE_URL}/auth/login/"
    data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Login successful!")
            result = response.json()
            print(f"\nAccess Token: {result['access_token'][:20]}...")
            print(f"Token Type: {result['token_type']}")
            print(f"Expires In: {result['expires_in']} seconds")
            print(f"\nUser Info:")
            print(f"  Username: {result['user']['username']}")
            print(f"  Email: {result['user']['email']}")
            print(f"  Role: {result['user']['role']}")
            print(f"  Active: {result['user']['is_active']}")
            
            return result['access_token']
        else:
            print("❌ Login failed!")
            print(f"Error: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed! Make sure Django server is running on port 8000")
        return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


def test_current_user(token):
    """Test current user endpoint with token"""
    print("\n" + "="*50)
    print("Testing current user endpoint...")
    
    url = f"{BASE_URL}/auth/me/"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Authentication successful!")
            user = response.json()
            print(json.dumps(user, indent=2))
        else:
            print("❌ Authentication failed!")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def test_logout(token):
    """Test logout endpoint"""
    print("\n" + "="*50)
    print("Testing logout endpoint...")
    
    url = f"{BASE_URL}/auth/logout/"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.post(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Logout successful!")
            print(response.json())
        else:
            print("❌ Logout failed!")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    print("="*50)
    print("Django REST API Authentication Test")
    print("="*50)
    
    # Test login
    token = test_login()
    
    if token:
        # Test authenticated endpoint
        test_current_user(token)
        
        # Test logout
        test_logout(token)
    
    print("\n" + "="*50)
    print("Test completed!")
