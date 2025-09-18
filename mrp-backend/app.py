import os
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
# Using direct API calls instead of quickbooks-python library due to compatibility issues
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for caching
cached_data = {
    'customers': [],
    'vendors': [],
    'items': [],
    'last_updated': None
}

# Search indexes
search_indexes = {
    'client_names': [],
    'vendor_names': [],
    'client_pos': [],
    'product_names': [],
    'product_descriptions': [],
    'part_names': [],
    'part_numbers': []
}

# QuickBooks configuration
QB_CLIENT_ID = os.getenv('QUICKBOOKS_CLIENT_ID')
QB_CLIENT_SECRET = os.getenv('QUICKBOOKS_CLIENT_SECRET')
QB_SANDBOX_BASE_URL = os.getenv('QUICKBOOKS_SANDBOX_BASE_URL')
QB_REDIRECT_URI = 'http://localhost:5002/callback'  # For local development

# Token storage (in production, use secure storage)
tokens = {
    'access_token': None,
    'refresh_token': None,
    'expires_at': None
}

def refresh_access_token():
    """Refresh the access token using refresh token"""
    if not tokens['refresh_token']:
        logger.error("No refresh token available")
        return False

    data = {
        'grant_type': 'refresh_token',
        'refresh_token': tokens['refresh_token']
    }

    # Create basic auth header
    import base64
    auth_string = f"{QB_CLIENT_ID}:{QB_CLIENT_SECRET}"
    auth_bytes = auth_string.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

    headers = {
        'Accept': 'application/json',
        'Authorization': f'Basic {auth_b64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        response = requests.post(
            'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer',
            data=data,
            headers=headers
        )

        if response.status_code == 200:
            token_data = response.json()
            tokens['access_token'] = token_data['access_token']
            tokens['refresh_token'] = token_data['refresh_token']
            tokens['expires_at'] = datetime.now() + timedelta(seconds=token_data['expires_in'])
            logger.info("Access token refreshed successfully")
            return True
        else:
            logger.error(f"Failed to refresh token: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        return False

def is_token_expired():
    """Check if access token is expired or will expire soon"""
    if not tokens['expires_at']:
        return True
    return datetime.now() >= tokens['expires_at'] - timedelta(minutes=5)

def ensure_valid_token():
    """Ensure we have a valid access token"""
    if is_token_expired():
        return refresh_access_token()
    return True

def make_qb_request(endpoint, company_id='1234567890'):
    """Make a request to QuickBooks API"""
    if not tokens['access_token']:
        logger.error("No access token available")
        return None

    url = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{company_id}/{endpoint}"
    headers = {
        'Authorization': f'Bearer {tokens["access_token"]}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"QuickBooks API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error making QuickBooks request: {str(e)}")
        return None

def fetch_customers():
    """Fetch all customers from QuickBooks"""
    if not ensure_valid_token():
        logger.error("No valid token available for fetching customers")
        return []

    try:
        response = make_qb_request('customer')
        if response and 'Customer' in response:
            return response['Customer']
        return []
    except Exception as e:
        logger.error(f"Error fetching customers: {str(e)}")
        return []

def fetch_vendors():
    """Fetch all vendors from QuickBooks"""
    if not ensure_valid_token():
        logger.error("No valid token available for fetching vendors")
        return []

    try:
        response = make_qb_request('vendor')
        if response and 'Vendor' in response:
            return response['Vendor']
        return []
    except Exception as e:
        logger.error(f"Error fetching vendors: {str(e)}")
        return []

def fetch_items():
    """Fetch all items from QuickBooks"""
    if not ensure_valid_token():
        logger.error("No valid token available for fetching items")
        return []

    try:
        response = make_qb_request('item')
        if response and 'Item' in response:
            return response['Item']
        return []
    except Exception as e:
        logger.error(f"Error fetching items: {str(e)}")
        return []

def build_search_indexes():
    """Build search indexes from cached data"""
    global search_indexes

    # Clear existing indexes
    for key in search_indexes:
        search_indexes[key] = []

    # Build client names index
    for customer in cached_data['customers']:
        if 'Name' in customer:
            search_indexes['client_names'].append({
                'id': customer.get('Id'),
                'name': customer['Name'],
                'type': 'customer'
            })

    # Build vendor names index
    for vendor in cached_data['vendors']:
        if 'Name' in vendor:
            search_indexes['vendor_names'].append({
                'id': vendor.get('Id'),
                'name': vendor['Name'],
                'type': 'vendor'
            })

    # Build product names and descriptions index
    for item in cached_data['items']:
        if 'Name' in item:
            search_indexes['product_names'].append({
                'id': item.get('Id'),
                'name': item['Name'],
                'type': 'item'
            })
        if 'Description' in item and item['Description']:
            search_indexes['product_descriptions'].append({
                'id': item.get('Id'),
                'description': item['Description'],
                'type': 'item'
            })

def update_cache():
    """Update cached data from QuickBooks"""
    global cached_data

    logger.info("Updating cache from QuickBooks...")

    cached_data['customers'] = fetch_customers()
    cached_data['vendors'] = fetch_vendors()
    cached_data['items'] = fetch_items()
    cached_data['last_updated'] = datetime.now()

    # Build search indexes
    build_search_indexes()

    logger.info(f"Cache updated. Customers: {len(cached_data['customers'])}, Vendors: {len(cached_data['vendors'])}, Items: {len(cached_data['items'])}")

def search_index(index_name, query, limit=15):
    """Search a specific index"""
    if index_name not in search_indexes:
        return []

    index = search_indexes[index_name]
    query_lower = query.lower()

    results = []
    for item in index:
        if index_name == 'client_names' and query_lower in item['name'].lower():
            results.append(item)
        elif index_name == 'vendor_names' and query_lower in item['name'].lower():
            results.append(item)
        elif index_name == 'product_names' and query_lower in item['name'].lower():
            results.append(item)
        elif index_name == 'product_descriptions' and 'description' in item and query_lower in item['description'].lower():
            results.append(item)

    return results[:limit]

# API Routes
@app.route('/api/search/<index_name>', methods=['GET'])
def search(index_name):
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 15))

    if not query:
        return jsonify({'error': 'Query parameter required'}), 400

    results = search_index(index_name, query, limit)
    return jsonify({
        'query': query,
        'results': results,
        'total': len(results)
    })

@app.route('/api/cache/status', methods=['GET'])
def cache_status():
    return jsonify({
        'last_updated': cached_data['last_updated'].isoformat() if cached_data['last_updated'] else None,
        'customers_count': len(cached_data['customers']),
        'vendors_count': len(cached_data['vendors']),
        'items_count': len(cached_data['items'])
    })

@app.route('/api/cache/refresh', methods=['POST'])
def manual_refresh():
    update_cache()
    return jsonify({'message': 'Cache refreshed successfully'})

# OAuth callback route (for initial setup)
@app.route('/callback')
def oauth_callback():
    code = request.args.get('code')
    if code:
        # Exchange code for tokens
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': QB_REDIRECT_URI
        }

        # Create basic auth header
        import base64
        auth_string = f"{QB_CLIENT_ID}:{QB_CLIENT_SECRET}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

        headers = {
            'Accept': 'application/json',
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.post(
            'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer',
            data=data,
            headers=headers
        )

        if response.status_code == 200:
            token_data = response.json()
            tokens['access_token'] = token_data['access_token']
            tokens['refresh_token'] = token_data['refresh_token']
            tokens['expires_at'] = datetime.now() + timedelta(seconds=token_data['expires_in'])
            return jsonify({'message': 'OAuth successful'})
        else:
            return jsonify({'error': 'OAuth failed'}), 400

    return jsonify({'error': 'No code provided'}), 400

def start_scheduler():
    """Start the background scheduler for cache updates"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_cache, 'interval', hours=1)
    scheduler.start()

    # Initial cache update
    update_cache()

if __name__ == '__main__':
    # Start scheduler in background thread
    scheduler_thread = threading.Thread(target=start_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    app.run(host='0.0.0.0', port=5002, debug=True)
