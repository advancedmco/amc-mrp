#!/usr/bin/env python3
"""
Test script for QuickBooks integration with timeout and retry support
"""
import requests
import json
import time
import sys

BASE_URL = "http://localhost:5002"

# Timeout configuration
REQUEST_TIMEOUT = 10  # seconds for most requests
REFRESH_TIMEOUT = 60  # seconds for cache refresh
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds between retries

def make_request_with_retry(method, url, max_retries=MAX_RETRIES, timeout=REQUEST_TIMEOUT, **kwargs):
    """
    Make an HTTP request with retry logic and timeout

    Args:
        method: HTTP method ('get', 'post', etc.)
        url: URL to request
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds
        **kwargs: Additional arguments to pass to requests

    Returns:
        Response object or None on failure
    """
    for attempt in range(max_retries):
        try:
            if method.lower() == 'get':
                response = requests.get(url, timeout=timeout, **kwargs)
            elif method.lower() == 'post':
                response = requests.post(url, timeout=timeout, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            return response

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print(f"   ⚠ Request timeout ({timeout}s). Retrying in {RETRY_DELAY}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(RETRY_DELAY)
            else:
                print(f"   ✗ Request failed after {max_retries} timeout attempts")
                return None

        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                print(f"   ⚠ Connection error. Retrying in {RETRY_DELAY}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(RETRY_DELAY)
            else:
                print(f"   ✗ Connection failed after {max_retries} attempts: {str(e)}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"   ✗ Request exception: {str(e)}")
            return None

    return None

def test_api_endpoints():
    """Test all API endpoints"""
    print("Testing QuickBooks Integration API...")
    print("=" * 50)
    
    # Test 1: Check configuration
    print("1. Testing configuration endpoint...")
    response = make_request_with_retry('get', f"{BASE_URL}/api/config")
    if response and response.status_code == 200:
        config = response.json()
        print(f"   ✓ Config loaded successfully")
        print(f"   - Company ID: {config.get('company_id')}")
        print(f"   - Has Access Token: {config.get('has_access_token')}")
        print(f"   - Has Refresh Token: {config.get('has_refresh_token')}")
        print(f"   - Token Expires: {config.get('token_expires_at')}")
    elif response:
        print(f"   ✗ Config endpoint failed: {response.status_code}")
    else:
        print(f"   ✗ Config endpoint unreachable")
    
    print()
    
    # Test 2: Check cache status
    print("2. Testing cache status endpoint...")
    response = make_request_with_retry('get', f"{BASE_URL}/api/cache/status")
    if response and response.status_code == 200:
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
    elif response:
        print(f"   ✗ Cache status endpoint failed: {response.status_code}")
    else:
        print(f"   ✗ Cache status endpoint unreachable")
    
    print()
    
    # Test 3: Manual cache refresh
    print("3. Testing manual cache refresh...")
    response = make_request_with_retry('post', f"{BASE_URL}/api/cache/refresh", timeout=REFRESH_TIMEOUT)
    if response and response.status_code == 200:
        result = response.json()
        print(f"   ✓ Cache refresh triggered: {result.get('message')}")

        # Wait a moment and check status again
        time.sleep(2)
        response = make_request_with_retry('get', f"{BASE_URL}/api/cache/status")
        if response and response.status_code == 200:
            status = response.json()
            total_records = status.get('customers_count', 0) + status.get('vendors_count', 0) + status.get('items_count', 0)
            print(f"   - After refresh: {total_records} total records")
    elif response:
        print(f"   ✗ Cache refresh failed: {response.status_code}")
    else:
        print(f"   ✗ Cache refresh endpoint unreachable")
    
    print()
    
    # Test 4: Search endpoints (if we have data)
    print("4. Testing search endpoints...")
    search_endpoints = ['client_names', 'vendor_names', 'product_names', 'product_descriptions']

    for endpoint in search_endpoints:
        # Test with a common search term
        response = make_request_with_retry('get', f"{BASE_URL}/api/search/{endpoint}?q=test&limit=5")
        if response and response.status_code == 200:
            results = response.json()
            print(f"   ✓ {endpoint}: {results.get('total', 0)} results")
        elif response:
            print(f"   ✗ {endpoint}: Failed ({response.status_code})")
        else:
            print(f"   ✗ {endpoint}: Unreachable")
    
    print()

    # Test 5: Circuit breaker status
    print("5. Testing circuit breaker status...")
    response = make_request_with_retry('get', f"{BASE_URL}/api/circuit-breaker/status")
    if response and response.status_code == 200:
        cb_status = response.json()
        print(f"   ✓ Circuit breaker status retrieved")
        print(f"   - State: {cb_status.get('state')}")
        print(f"   - Failures: {cb_status.get('failures')}")
        print(f"   - Threshold: {cb_status.get('threshold')}")
    elif response:
        print(f"   ✗ Circuit breaker endpoint failed: {response.status_code}")
    else:
        print(f"   ✗ Circuit breaker endpoint unreachable")

    print()
    print("=" * 50)
    print("Test completed!")

    # Final status check
    response = make_request_with_retry('get', f"{BASE_URL}/api/cache/status")
    if response and response.status_code == 200:
        status = response.json()
        total_records = status.get('customers_count', 0) + status.get('vendors_count', 0) + status.get('items_count', 0)

        if total_records > 0:
            print(f"✓ SUCCESS: {total_records} records retrieved from QuickBooks")
            print("  The integration is working correctly!")
            sys.exit(0)
        else:
            print("⚠ WARNING: No data retrieved from QuickBooks")
            print("  This could mean:")
            print("  1. OAuth authentication is needed")
            print("  2. The QuickBooks company has no data")
            print("  3. There's an API connectivity issue")
            print()
            print("  To authenticate, visit:")
            print("  https://appcenter.intuit.com/connect/oauth2?client_id=ABbK0d9uTJsEGwlP7W9YNqRpTdj0GDVmxMmyWaYVvwZ10CyVC4&response_type=code&scope=com.intuit.quickbooks.accounting&redirect_uri=https://mrp.inge.st/callback&state=test")
            sys.exit(1)
    else:
        print("✗ FAILED: Could not get final status")
        sys.exit(2)

if __name__ == "__main__":
    test_api_endpoints()
