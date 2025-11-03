#!/usr/bin/env python3
"""
Test script for QuickBooks integration
"""
import requests
import json
import time

BASE_URL = "http://localhost:5002"

def test_api_endpoints():
    """Test all API endpoints"""
    print("Testing QuickBooks Integration API...")
    print("=" * 50)
    
    # Test 1: Check configuration
    print("1. Testing configuration endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/config")
        if response.status_code == 200:
            config = response.json()
            print(f"   ✓ Config loaded successfully")
            print(f"   - Company ID: {config.get('company_id')}")
            print(f"   - Has Access Token: {config.get('has_access_token')}")
            print(f"   - Has Refresh Token: {config.get('has_refresh_token')}")
            print(f"   - Token Expires: {config.get('token_expires_at')}")
        else:
            print(f"   ✗ Config endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Config endpoint error: {str(e)}")
    
    print()
    
    # Test 2: Check cache status
    print("2. Testing cache status endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/cache/status")
        if response.status_code == 200:
            status = response.json()
            print(f"   ✓ Cache status retrieved successfully")
            print(f"   - Last Updated: {status.get('last_updated')}")
            print(f"   - Customers: {status.get('customers_count')}")
            print(f"   - Vendors: {status.get('vendors_count')}")
            print(f"   - Items: {status.get('items_count')}")
            
            # Check if we have data
            total_records = status.get('customers_count', 0) + status.get('vendors_count', 0) + status.get('items_count', 0)
            if total_records > 0:
                print(f"   ✓ Data successfully retrieved from QuickBooks!")
            else:
                print(f"   ⚠ No data found - OAuth authentication may be needed")
        else:
            print(f"   ✗ Cache status endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Cache status endpoint error: {str(e)}")
    
    print()
    
    # Test 3: Manual cache refresh
    print("3. Testing manual cache refresh...")
    try:
        response = requests.post(f"{BASE_URL}/api/cache/refresh")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Cache refresh triggered: {result.get('message')}")
            
            # Wait a moment and check status again
            time.sleep(2)
            response = requests.get(f"{BASE_URL}/api/cache/status")
            if response.status_code == 200:
                status = response.json()
                total_records = status.get('customers_count', 0) + status.get('vendors_count', 0) + status.get('items_count', 0)
                print(f"   - After refresh: {total_records} total records")
        else:
            print(f"   ✗ Cache refresh failed: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Cache refresh error: {str(e)}")
    
    print()
    
    # Test 4: Search endpoints (if we have data)
    print("4. Testing search endpoints...")
    search_endpoints = ['client_names', 'vendor_names', 'product_names', 'product_descriptions']
    
    for endpoint in search_endpoints:
        try:
            # Test with a common search term
            response = requests.get(f"{BASE_URL}/api/search/{endpoint}?q=test&limit=5")
            if response.status_code == 200:
                results = response.json()
                print(f"   ✓ {endpoint}: {results.get('total', 0)} results")
            else:
                print(f"   ✗ {endpoint}: Failed ({response.status_code})")
        except Exception as e:
            print(f"   ✗ {endpoint}: Error - {str(e)}")
    
    print()
    print("=" * 50)
    print("Test completed!")
    
    # Final status check
    try:
        response = requests.get(f"{BASE_URL}/api/cache/status")
        if response.status_code == 200:
            status = response.json()
            total_records = status.get('customers_count', 0) + status.get('vendors_count', 0) + status.get('items_count', 0)
            
            if total_records > 0:
                print(f"✓ SUCCESS: {total_records} records retrieved from QuickBooks")
                print("  The integration is working correctly!")
            else:
                print("⚠ WARNING: No data retrieved from QuickBooks")
                print("  This could mean:")
                print("  1. OAuth authentication is needed")
                print("  2. The QuickBooks company has no data")
                print("  3. There's an API connectivity issue")
                print()
                print("  To authenticate, visit:")
                print("  https://appcenter.intuit.com/connect/oauth2?client_id=ABbK0d9uTJsEGwlP7W9YNqRpTdj0GDVmxMmyWaYVvwZ10CyVC4&response_type=code&scope=com.intuit.quickbooks.accounting&redirect_uri=https://mrp.inge.st/callback&state=test")
        else:
            print("✗ FAILED: Could not get final status")
    except Exception as e:
        print(f"✗ FAILED: Final status check error - {str(e)}")

if __name__ == "__main__":
    test_api_endpoints()
