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
QB_COMPANY_ID = os.getenv('QUICKBOOKS_COMPANY_ID', '1234567890')  # Use env var or fallback
PRODUCTION_URI = os.getenv('PRODUCTION_URI', 'http://localhost:5002')
QB_REDIRECT_URI = f'{PRODUCTION_URI}/callback'  # Use production URI for callback

# Debug logging for environment variables
logger.info(f"Environment variables loaded:")
logger.info(f"QB_CLIENT_ID: {'***' + QB_CLIENT_ID[-4:] if QB_CLIENT_ID else 'None'}")
logger.info(f"QB_COMPANY_ID: {QB_COMPANY_ID}")
logger.info(f"QB_SANDBOX_BASE_URL: {QB_SANDBOX_BASE_URL}")
logger.info(f"PRODUCTION_URI: {PRODUCTION_URI}")
logger.info(f"QB_REDIRECT_URI: {QB_REDIRECT_URI}")

# Token storage file path
TOKEN_FILE = '/tmp/qb_tokens.json'

# Token storage (with file persistence)
tokens = {
    'access_token': None,
    'refresh_token': None,
    'expires_at': None,
    'company_id': None
}

def load_tokens():
    """Load tokens from file if they exist"""
    global tokens
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                saved_tokens = json.load(f)
                tokens.update(saved_tokens)
                # Convert expires_at string back to datetime
                if tokens['expires_at']:
                    tokens['expires_at'] = datetime.fromisoformat(tokens['expires_at'])
                logger.info("Tokens loaded from file")
                logger.info(f"Token expires at: {tokens['expires_at']}")
    except Exception as e:
        logger.error(f"Error loading tokens: {str(e)}")

def save_tokens():
    """Save tokens to file"""
    try:
        # Convert datetime to string for JSON serialization
        tokens_to_save = tokens.copy()
        if tokens_to_save['expires_at']:
            tokens_to_save['expires_at'] = tokens_to_save['expires_at'].isoformat()
        
        with open(TOKEN_FILE, 'w') as f:
            json.dump(tokens_to_save, f)
        logger.info("Tokens saved to file")
    except Exception as e:
        logger.error(f"Error saving tokens: {str(e)}")

# Load tokens on startup
load_tokens()

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
            save_tokens()  # Save tokens to file
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

def make_qb_request(endpoint, company_id=None):
    """Make a request to QuickBooks API"""
    if not tokens['access_token']:
        logger.error("No access token available")
        return None

    # Use provided company_id or fall back to environment variable
    company_id = company_id or QB_COMPANY_ID
    logger.info(f"Using QuickBooks Company ID: {company_id}")

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
        # Use proper QuickBooks API query syntax
        response = make_qb_request("query?query=SELECT * FROM Customer MAXRESULTS 1000")
        if response and 'QueryResponse' in response and 'Customer' in response['QueryResponse']:
            customers = response['QueryResponse']['Customer']
            logger.info(f"Successfully fetched {len(customers)} customers")
            return customers
        else:
            logger.warning("No customers found in QuickBooks response")
            logger.debug(f"Response structure: {response}")
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
        # Use proper QuickBooks API query syntax
        response = make_qb_request("query?query=SELECT * FROM Vendor MAXRESULTS 1000")
        if response and 'QueryResponse' in response and 'Vendor' in response['QueryResponse']:
            vendors = response['QueryResponse']['Vendor']
            logger.info(f"Successfully fetched {len(vendors)} vendors")
            return vendors
        else:
            logger.warning("No vendors found in QuickBooks response")
            logger.debug(f"Response structure: {response}")
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
        # Use proper QuickBooks API query syntax
        response = make_qb_request("query?query=SELECT * FROM Item MAXRESULTS 1000")
        if response and 'QueryResponse' in response and 'Item' in response['QueryResponse']:
            items = response['QueryResponse']['Item']
            logger.info(f"Successfully fetched {len(items)} items")
            return items
        else:
            logger.warning("No items found in QuickBooks response")
            logger.debug(f"Response structure: {response}")
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

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration for debugging"""
    return jsonify({
        'company_id': QB_COMPANY_ID,
        'client_id': QB_CLIENT_ID[:10] + '...' if QB_CLIENT_ID else None,  # Partial for security
        'has_access_token': tokens['access_token'] is not None,
        'has_refresh_token': tokens['refresh_token'] is not None,
        'token_expires_at': tokens['expires_at'].isoformat() if tokens['expires_at'] else None
    })

@app.route('/api/cache/refresh', methods=['POST'])
def manual_refresh():
    update_cache()
    return jsonify({'message': 'Cache refreshed successfully'})

# OAuth callback route (for initial setup)
@app.route('/callback')
def oauth_callback():
    logger.info("OAuth callback received")
    logger.info(f"Request args: {dict(request.args)}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request URL: {request.url}")

    code = request.args.get('code')
    error = request.args.get('error')
    state = request.args.get('state')

    if error:
        logger.error(f"OAuth error: {error}")
        logger.error(f"Error description: {request.args.get('error_description')}")
        return jsonify({
            'error': error,
            'error_description': request.args.get('error_description')
        }), 400

    if code:
        logger.info(f"Authorization code received: {code[:10]}...")
        logger.info(f"Using redirect URI: {QB_REDIRECT_URI}")

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

        logger.info("Exchanging authorization code for tokens...")

        try:
            response = requests.post(
                'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer',
                data=data,
                headers=headers,
                timeout=30
            )

            logger.info(f"Token exchange response status: {response.status_code}")

            if response.status_code == 200:
                token_data = response.json()
                tokens['access_token'] = token_data['access_token']
                tokens['refresh_token'] = token_data['refresh_token']
                tokens['expires_at'] = datetime.now() + timedelta(seconds=token_data['expires_in'])
                
                # Store company ID from callback if available
                realm_id = request.args.get('realmId')
                if realm_id:
                    tokens['company_id'] = realm_id
                    logger.info(f"Company ID stored: {realm_id}")
                
                save_tokens()  # Save tokens to file
                logger.info("OAuth successful! Tokens obtained and stored.")
                logger.info(f"Access token expires in: {token_data['expires_in']} seconds")

                # Trigger immediate cache update with new tokens
                try:
                    update_cache()
                except Exception as e:
                    logger.error(f"Error during initial cache update: {str(e)}")

                return jsonify({
                    'message': 'OAuth successful',
                    'expires_in': token_data['expires_in'],
                    'token_type': token_data.get('token_type', 'bearer'),
                    'company_id': realm_id
                })
            else:
                logger.error(f"OAuth failed with status {response.status_code}")
                logger.error(f"Response: {response.text}")
                return jsonify({
                    'error': 'OAuth failed',
                    'status_code': response.status_code,
                    'response': response.text
                }), 400

        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception during token exchange: {str(e)}")
            return jsonify({
                'error': 'Request failed',
                'details': str(e)
            }), 500

    logger.warning("No authorization code provided in callback")
    return jsonify({
        'error': 'No code provided',
        'received_args': dict(request.args)
    }), 400

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
