import os
import json
import time
import base64
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
    'invoices': [],
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
QB_SANDBOX_BASE_URL = os.getenv('QUICKBOOKS_SANDBOX_BASE_URL', 'https://sandbox-quickbooks.api.intuit.com')
QB_COMPANY_ID = os.getenv('QUICKBOOKS_COMPANY_ID')  # Will be set during OAuth if not provided
QB_ENVIRONMENT = os.getenv('QB_ENVIRONMENT', 'sandbox')
PRODUCTION_URI = os.getenv('PRODUCTION_URI', 'http://localhost:5002')
# Use QB_REDIRECT_URI if provided, otherwise construct from PRODUCTION_URI
QB_REDIRECT_URI = os.getenv('QB_REDIRECT_URI', f'{PRODUCTION_URI}/callback')

# Validate required environment variables
def validate_env_vars():
    """Validate that required environment variables are set"""
    required_vars = {
        'QUICKBOOKS_CLIENT_ID': QB_CLIENT_ID,
        'QUICKBOOKS_CLIENT_SECRET': QB_CLIENT_SECRET,
        'QUICKBOOKS_SANDBOX_BASE_URL': QB_SANDBOX_BASE_URL
    }

    missing_vars = [var for var, value in required_vars.items() if not value]

    if missing_vars:
        logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.warning("QuickBooks integration may not work properly without these variables")
    else:
        logger.info("All required environment variables are set")

    return len(missing_vars) == 0

# Debug logging for environment variables
logger.info(f"Environment variables loaded:")
logger.info(f"QB_CLIENT_ID: {'***' + QB_CLIENT_ID[-4:] if QB_CLIENT_ID else 'None'}")
logger.info(f"QB_COMPANY_ID: {QB_COMPANY_ID or 'Will be set during OAuth'}")
logger.info(f"QB_SANDBOX_BASE_URL: {QB_SANDBOX_BASE_URL}")
logger.info(f"PRODUCTION_URI: {PRODUCTION_URI}")
logger.info(f"QB_REDIRECT_URI: {QB_REDIRECT_URI}")

# Validate environment variables
validate_env_vars()

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

    # Use provided company_id, fall back to stored company_id from OAuth, then environment variable
    company_id = company_id or tokens.get('company_id') or QB_COMPANY_ID

    if not company_id:
        logger.error("No company ID available. Complete OAuth flow to set company ID")
        return None

    logger.debug(f"Using QuickBooks Company ID: {company_id}")

    # Use environment variable for base URL
    url = f"{QB_SANDBOX_BASE_URL}/v3/company/{company_id}/{endpoint}"
    headers = {
        'Authorization': f'Bearer {tokens["access_token"]}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            logger.warning("Access token expired or invalid (401). Attempting token refresh...")
            # Try to refresh token and retry once
            if refresh_access_token():
                logger.info("Token refreshed successfully, retrying request...")
                headers['Authorization'] = f'Bearer {tokens["access_token"]}'
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    return response.json()
            logger.error("Failed to refresh token or retry request")
            return None
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

def fetch_invoices():
    """Fetch all invoices from QuickBooks"""
    if not ensure_valid_token():
        logger.error("No valid token available for fetching invoices")
        return []

    try:
        # Use proper QuickBooks API query syntax
        response = make_qb_request("query?query=SELECT * FROM Invoice MAXRESULTS 1000")
        if response and 'QueryResponse' in response and 'Invoice' in response['QueryResponse']:
            invoices = response['QueryResponse']['Invoice']
            logger.info(f"Successfully fetched {len(invoices)} invoices")
            return invoices
        else:
            logger.warning("No invoices found in QuickBooks response")
            logger.debug(f"Response structure: {response}")
            return []
    except Exception as e:
        logger.error(f"Error fetching invoices: {str(e)}")
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
                'type': 'customer',
                'active': customer.get('Active', True),
                'company_name': customer.get('CompanyName', customer.get('Name')),
                'email': customer.get('PrimaryEmailAddr', {}).get('Address') if customer.get('PrimaryEmailAddr') else None
            })

    # Build vendor names index
    for vendor in cached_data['vendors']:
        if 'Name' in vendor:
            search_indexes['vendor_names'].append({
                'id': vendor.get('Id'),
                'name': vendor['Name'],
                'type': 'vendor',
                'active': vendor.get('Active', True),
                'company_name': vendor.get('CompanyName', vendor.get('Name')),
                'email': vendor.get('PrimaryEmailAddr', {}).get('Address') if vendor.get('PrimaryEmailAddr') else None
            })

    # Build product names and descriptions index
    for item in cached_data['items']:
        if 'Name' in item:
            search_indexes['product_names'].append({
                'id': item.get('Id'),
                'name': item['Name'],
                'type': 'item',
                'active': item.get('Active', True),
                'item_type': item.get('Type'),
                'sku': item.get('Sku'),
                'unit_price': item.get('UnitPrice')
            })
            
            # Also add to part_names index (alias for product_names)
            search_indexes['part_names'].append({
                'id': item.get('Id'),
                'name': item['Name'],
                'type': 'item',
                'active': item.get('Active', True),
                'item_type': item.get('Type'),
                'sku': item.get('Sku'),
                'unit_price': item.get('UnitPrice')
            })
            
            # Add SKU to part_numbers index if available
            if item.get('Sku'):
                search_indexes['part_numbers'].append({
                    'id': item.get('Id'),
                    'name': item['Name'],
                    'sku': item.get('Sku'),
                    'type': 'item',
                    'active': item.get('Active', True),
                    'item_type': item.get('Type'),
                    'unit_price': item.get('UnitPrice')
                })
        
        if 'Description' in item and item['Description']:
            search_indexes['product_descriptions'].append({
                'id': item.get('Id'),
                'name': item.get('Name'),
                'description': item['Description'],
                'type': 'item',
                'active': item.get('Active', True),
                'item_type': item.get('Type'),
                'sku': item.get('Sku'),
                'unit_price': item.get('UnitPrice')
            })

    # Build client_pos index (Purchase Orders from customers - if available)
    # Note: This would require additional QuickBooks API calls for PurchaseOrder entities
    # For now, we'll leave this empty but the structure is ready
    search_indexes['client_pos'] = []
    
    logger.info(f"Search indexes built: {', '.join([f'{k}({len(v)})' for k, v in search_indexes.items() if v])}")

def update_cache():
    """Update cached data from QuickBooks"""
    global cached_data

    logger.info("Updating cache from QuickBooks...")

    cached_data['customers'] = fetch_customers()
    cached_data['vendors'] = fetch_vendors()
    cached_data['items'] = fetch_items()
    cached_data['invoices'] = fetch_invoices()
    cached_data['last_updated'] = datetime.now()

    # Build search indexes
    build_search_indexes()

    logger.info(f"Cache updated. Customers: {len(cached_data['customers'])}, Vendors: {len(cached_data['vendors'])}, Items: {len(cached_data['items'])}, Invoices: {len(cached_data['invoices'])}")

def search_index(index_name, query, limit=15):
    """Search a specific index"""
    if index_name not in search_indexes:
        return []

    index = search_indexes[index_name]
    query_lower = query.lower()

    results = []
    for item in index:
        match_found = False
        
        if index_name in ['client_names', 'vendor_names']:
            # Search in name, company_name, and email
            if (query_lower in item['name'].lower() or 
                (item.get('company_name') and query_lower in item['company_name'].lower()) or
                (item.get('email') and query_lower in item['email'].lower())):
                match_found = True
                
        elif index_name in ['product_names', 'part_names']:
            # Search in name and SKU
            if (query_lower in item['name'].lower() or 
                (item.get('sku') and query_lower in item['sku'].lower())):
                match_found = True
                
        elif index_name == 'part_numbers':
            # Search in SKU and name
            if (query_lower in item['sku'].lower() or 
                query_lower in item['name'].lower()):
                match_found = True
                
        elif index_name == 'product_descriptions':
            # Search in description and name
            if (query_lower in item['description'].lower() or 
                query_lower in item['name'].lower()):
                match_found = True
                
        elif index_name == 'client_pos':
            # Future implementation for client purchase orders
            # Currently empty but structure is ready
            pass
            
        if match_found:
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
    # Check if QuickBooks is authenticated and connected
    is_authenticated = tokens['access_token'] is not None and tokens['refresh_token'] is not None
    has_valid_config = QB_CLIENT_ID is not None and QB_CLIENT_SECRET is not None
    has_data = len(cached_data['customers']) > 0 or len(cached_data['vendors']) > 0 or len(cached_data['items']) > 0

    # Determine connection status
    if not has_valid_config:
        connection_status = 'not_configured'
    elif not is_authenticated:
        connection_status = 'not_authenticated'
    elif not has_data:
        connection_status = 'authenticated_no_data'
    else:
        connection_status = 'connected'

    return jsonify({
        'connection_status': connection_status,
        'is_authenticated': is_authenticated,
        'has_valid_config': has_valid_config,
        'last_updated': cached_data['last_updated'].isoformat() if cached_data['last_updated'] else None,
        'customers_count': len(cached_data['customers']),
        'vendors_count': len(cached_data['vendors']),
        'items_count': len(cached_data['items']),
        'invoices_count': len(cached_data['invoices'])
    })

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration for debugging"""
    return jsonify({
        'company_id': tokens.get('company_id') or QB_COMPANY_ID,
        'client_id': QB_CLIENT_ID[:10] + '...' if QB_CLIENT_ID else None,  # Partial for security
        'has_access_token': tokens['access_token'] is not None,
        'has_refresh_token': tokens['refresh_token'] is not None,
        'token_expires_at': tokens['expires_at'].isoformat() if tokens['expires_at'] else None,
        'redirect_uri': QB_REDIRECT_URI,
        'base_url': QB_SANDBOX_BASE_URL,
        'environment': os.getenv('QB_ENVIRONMENT', 'sandbox')
    })

@app.route('/api/auth/url', methods=['GET'])
def get_auth_url():
    """Generate QuickBooks OAuth authorization URL"""
    if not QB_CLIENT_ID or not QB_CLIENT_SECRET:
        return jsonify({
            'error': 'QuickBooks credentials not configured. Please set QUICKBOOKS_CLIENT_ID and QUICKBOOKS_CLIENT_SECRET in your .env file'
        }), 400

    # Generate state parameter for security (optional but recommended)
    import secrets
    state = secrets.token_urlsafe(32)

    # Build authorization URL
    auth_url = (
        'https://appcenter.intuit.com/connect/oauth2?'
        f'client_id={QB_CLIENT_ID}&'
        f'scope=com.intuit.quickbooks.accounting&'
        f'redirect_uri={QB_REDIRECT_URI}&'
        f'response_type=code&'
        f'state={state}'
    )

    logger.info(f"Generated OAuth URL with redirect URI: {QB_REDIRECT_URI}")

    return jsonify({
        'auth_url': auth_url,
        'state': state
    })

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from QuickBooks by clearing tokens"""
    global tokens

    try:
        # Clear tokens
        tokens = {
            'access_token': None,
            'refresh_token': None,
            'expires_at': None,
            'company_id': None
        }

        # Delete token file
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
            logger.info("Token file deleted")

        # Clear cached data
        global cached_data
        cached_data = {
            'customers': [],
            'vendors': [],
            'items': [],
            'invoices': [],
            'last_updated': None
        }

        logger.info("Disconnected from QuickBooks")

        return jsonify({
            'success': True,
            'message': 'Disconnected from QuickBooks successfully'
        })

    except Exception as e:
        logger.error(f"Error disconnecting: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/test', methods=['GET'])
def test_connection():
    """Test QuickBooks connection"""
    if not tokens['access_token']:
        return jsonify({
            'success': False,
            'error': 'Not authenticated. Please connect to QuickBooks first.'
        }), 401

    try:
        # Try to fetch company info
        company_id = tokens.get('company_id') or QB_COMPANY_ID

        if not company_id:
            return jsonify({
                'success': False,
                'error': 'Company ID not available. Please complete OAuth flow.'
            }), 400

        # Make a simple API call to test connection
        response = make_qb_request("companyinfo/" + company_id)

        if response and 'CompanyInfo' in response:
            company_info = response['CompanyInfo']
            return jsonify({
                'success': True,
                'message': f"Successfully connected to {company_info.get('CompanyName', 'QuickBooks')}",
                'company_name': company_info.get('CompanyName'),
                'company_id': company_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve company information. Connection may be invalid.'
            }), 500

    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cache/refresh', methods=['POST'])
def manual_refresh():
    update_cache()
    return jsonify({'message': 'Cache refreshed successfully'})

@app.route('/api/indexes/status', methods=['GET'])
def indexes_status():
    """Get status of all search indexes"""
    return jsonify({
        'indexes': {name: len(index) for name, index in search_indexes.items()},
        'total_indexed_items': sum(len(index) for index in search_indexes.values()),
        'available_indexes': list(search_indexes.keys())
    })

@app.route('/api/data/customers', methods=['GET'])
def get_customers():
    """Get all cached customer data (for debugging)"""
    limit = int(request.args.get('limit', 50))
    return jsonify({
        'customers': cached_data['customers'][:limit],
        'total': len(cached_data['customers']),
        'showing': min(limit, len(cached_data['customers']))
    })

@app.route('/api/data/vendors', methods=['GET'])
def get_vendors():
    """Get all cached vendor data (for debugging)"""
    limit = int(request.args.get('limit', 50))
    return jsonify({
        'vendors': cached_data['vendors'][:limit],
        'total': len(cached_data['vendors']),
        'showing': min(limit, len(cached_data['vendors']))
    })

@app.route('/api/data/items', methods=['GET'])
def get_items():
    """Get all cached item data (for debugging)"""
    limit = int(request.args.get('limit', 50))
    return jsonify({
        'items': cached_data['items'][:limit],
        'total': len(cached_data['items']),
        'showing': min(limit, len(cached_data['items']))
    })

@app.route('/api/data/invoices', methods=['GET'])
def get_invoices():
    """Get all cached invoice data (for debugging)"""
    limit = int(request.args.get('limit', 50))
    return jsonify({
        'invoices': cached_data['invoices'][:limit],
        'total': len(cached_data['invoices']),
        'showing': min(limit, len(cached_data['invoices']))
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'authenticated': tokens['access_token'] is not None,
        'cache_age_minutes': (datetime.now() - cached_data['last_updated']).total_seconds() / 60 if cached_data['last_updated'] else None
    })

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
