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
from requests.exceptions import Timeout, ConnectionError, RequestException
import pymysql
from pymysql.cursors import DictCursor
from importers import ImportCoordinator

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'db'),
    'user': os.getenv('DB_USER', 'amc'),
    'password': os.getenv('DB_PASSWORD', 'Workbench.lavender.chrome'),
    'database': os.getenv('DB_NAME', 'amcmrp'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'cursorclass': DictCursor,
    'charset': 'utf8mb4'
}

def get_db_connection():
    """Get database connection"""
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

# Timeout and retry configuration
QB_API_TIMEOUT = int(os.getenv('QB_API_TIMEOUT', '30'))  # Default 30 seconds for QB API calls
QB_AUTH_TIMEOUT = int(os.getenv('QB_AUTH_TIMEOUT', '30'))  # Default 30 seconds for OAuth calls
QB_MAX_RETRIES = int(os.getenv('QB_MAX_RETRIES', '3'))  # Maximum number of retry attempts
QB_RETRY_BACKOFF_FACTOR = float(os.getenv('QB_RETRY_BACKOFF_FACTOR', '2.0'))  # Exponential backoff multiplier
QB_INITIAL_RETRY_DELAY = float(os.getenv('QB_INITIAL_RETRY_DELAY', '1.0'))  # Initial retry delay in seconds

# Circuit breaker configuration
CIRCUIT_BREAKER_THRESHOLD = int(os.getenv('CIRCUIT_BREAKER_THRESHOLD', '5'))  # Failures before opening circuit
CIRCUIT_BREAKER_TIMEOUT = int(os.getenv('CIRCUIT_BREAKER_TIMEOUT', '60'))  # Seconds before attempting reset

# Circuit breaker state
circuit_breaker = {
    'failures': 0,
    'last_failure_time': None,
    'state': 'closed'  # closed, open, half-open
}

logger.info(f"Timeout configuration: API={QB_API_TIMEOUT}s, Auth={QB_AUTH_TIMEOUT}s, Max Retries={QB_MAX_RETRIES}")

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
QB_CLIENT_ID = os.getenv('QB_CLIENT_ID')
QB_CLIENT_SECRET = os.getenv('QB_CLIENT_SECRET')
QB_SANDBOX_BASE_URL = os.getenv('QB_SANDBOX_BASE_URL', 'https://sandbox-quickbooks.api.intuit.com')
QB_COMPANY_ID = os.getenv('QB_COMPANY_ID')  # Will be set during OAuth if not provided
QB_ENVIRONMENT = os.getenv('QB_ENVIRONMENT', 'sandbox')
PRODUCTION_URI = os.getenv('PRODUCTION_URI', 'http://localhost:5002')
# Use QB_REDIRECT_URI if provided, otherwise construct from PRODUCTION_URI
QB_REDIRECT_URI = os.getenv('QB_REDIRECT_URI', f'{PRODUCTION_URI}/callback')

# Validate required environment variables
def validate_env_vars():
    """Validate that required environment variables are set"""
    required_vars = {
        'QB_CLIENT_ID': QB_CLIENT_ID,
        'QB_CLIENT_SECRET': QB_CLIENT_SECRET,
        'QB_SANDBOX_BASE_URL': QB_SANDBOX_BASE_URL
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

# Token storage file path (fallback for backward compatibility)
TOKEN_FILE = '/tmp/qb_tokens.json'

# Token storage (with database persistence)
tokens = {
    'access_token': None,
    'refresh_token': None,
    'expires_at': None,
    'company_id': None
}

def load_tokens():
    """Load tokens from database (with file fallback for migration)"""
    global tokens

    # Try loading from database first
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT AccessToken, RefreshToken, CompanyID, ExpiresAt
                    FROM OAuthTokens
                    WHERE ServiceName = 'QuickBooks'
                    LIMIT 1
                """)
                result = cursor.fetchone()

                if result:
                    tokens['access_token'] = result['AccessToken']
                    tokens['refresh_token'] = result['RefreshToken']
                    tokens['company_id'] = result['CompanyID']
                    if result['ExpiresAt']:
                        tokens['expires_at'] = result['ExpiresAt']
                    logger.info("Tokens loaded from database")
                    logger.info(f"Token expires at: {tokens['expires_at']}")
                    conn.close()
                    return
                else:
                    logger.info("No tokens found in database")
            conn.close()
        except Exception as e:
            logger.error(f"Error loading tokens from database: {str(e)}")
            if conn:
                conn.close()

    # Fallback: Try loading from file for backward compatibility
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                saved_tokens = json.load(f)
                tokens.update(saved_tokens)
                # Convert expires_at string back to datetime
                if tokens['expires_at']:
                    tokens['expires_at'] = datetime.fromisoformat(tokens['expires_at'])
                logger.info("Tokens loaded from file (legacy)")
                logger.info(f"Token expires at: {tokens['expires_at']}")
                # Migrate to database
                save_tokens()
                # Remove old file after successful migration
                try:
                    os.remove(TOKEN_FILE)
                    logger.info("Migrated tokens from file to database")
                except:
                    pass
    except Exception as e:
        logger.error(f"Error loading tokens from file: {str(e)}")

def save_tokens():
    """Save tokens to database"""
    conn = get_db_connection()
    if not conn:
        logger.error("Cannot save tokens: database connection failed")
        return

    try:
        with conn.cursor() as cursor:
            # Use INSERT ... ON DUPLICATE KEY UPDATE for upsert behavior
            cursor.execute("""
                INSERT INTO OAuthTokens (ServiceName, AccessToken, RefreshToken, CompanyID, ExpiresAt)
                VALUES ('QuickBooks', %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    AccessToken = VALUES(AccessToken),
                    RefreshToken = VALUES(RefreshToken),
                    CompanyID = VALUES(CompanyID),
                    ExpiresAt = VALUES(ExpiresAt)
            """, (
                tokens['access_token'],
                tokens['refresh_token'],
                tokens['company_id'],
                tokens['expires_at']
            ))
            conn.commit()
            logger.info("Tokens saved to database")
    except Exception as e:
        logger.error(f"Error saving tokens to database: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

def clear_tokens():
    """Clear tokens from memory and database to enable fresh authentication"""
    global tokens
    tokens = {
        'access_token': None,
        'refresh_token': None,
        'expires_at': None,
        'company_id': None
    }

    # Delete from database
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM OAuthTokens WHERE ServiceName = 'QuickBooks'")
                conn.commit()
                logger.info("Tokens deleted from database")
        except Exception as e:
            logger.error(f"Error deleting tokens from database: {str(e)}")
            conn.rollback()
        finally:
            conn.close()

    # Also delete token file if it exists (cleanup legacy)
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
            logger.info("Legacy token file deleted")
    except Exception as e:
        logger.error(f"Error deleting token file: {str(e)}")

# Load tokens on startup
load_tokens()

def check_circuit_breaker():
    """Check circuit breaker state and update if needed"""
    global circuit_breaker

    if circuit_breaker['state'] == 'open':
        # Check if timeout has passed
        if circuit_breaker['last_failure_time']:
            time_since_failure = (datetime.now() - circuit_breaker['last_failure_time']).total_seconds()
            if time_since_failure >= CIRCUIT_BREAKER_TIMEOUT:
                logger.info("Circuit breaker timeout expired, attempting reset (half-open state)")
                circuit_breaker['state'] = 'half-open'
                return True
        logger.warning("Circuit breaker is OPEN - rejecting requests to protect system")
        return False

    return True

def record_circuit_breaker_success():
    """Record a successful API call"""
    global circuit_breaker
    if circuit_breaker['state'] == 'half-open':
        logger.info("Circuit breaker reset - service recovered")
    circuit_breaker['failures'] = 0
    circuit_breaker['state'] = 'closed'

def record_circuit_breaker_failure():
    """Record a failed API call"""
    global circuit_breaker
    circuit_breaker['failures'] += 1
    circuit_breaker['last_failure_time'] = datetime.now()

    if circuit_breaker['failures'] >= CIRCUIT_BREAKER_THRESHOLD:
        if circuit_breaker['state'] != 'open':
            logger.error(f"Circuit breaker OPENED after {circuit_breaker['failures']} failures")
        circuit_breaker['state'] = 'open'

def retry_with_backoff(func, *args, max_retries=None, **kwargs):
    """
    Retry a function with exponential backoff

    Args:
        func: Function to retry
        *args: Positional arguments for func
        max_retries: Maximum retry attempts (default: QB_MAX_RETRIES)
        **kwargs: Keyword arguments for func

    Returns:
        Result of func or None on failure
    """
    if max_retries is None:
        max_retries = QB_MAX_RETRIES

    last_exception = None

    for attempt in range(max_retries):
        try:
            result = func(*args, **kwargs)
            if result is not None:
                return result
        except (Timeout, ConnectionError) as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = QB_INITIAL_RETRY_DELAY * (QB_RETRY_BACKOFF_FACTOR ** attempt)
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries} attempts failed: {str(e)}")
        except RequestException as e:
            # For other request exceptions, don't retry
            logger.error(f"Request exception (not retrying): {str(e)}")
            last_exception = e
            break
        except Exception as e:
            # For unexpected exceptions, don't retry
            logger.error(f"Unexpected exception (not retrying): {str(e)}")
            last_exception = e
            break

    if last_exception:
        logger.error(f"Operation failed after retries: {str(last_exception)}")
    return None

def categorize_error(status_code, response_text=""):
    """
    Categorize HTTP errors for better handling

    Returns: (error_type, error_message, is_retryable)
    """
    if status_code == 400:
        return ("bad_request", "Invalid request to QuickBooks API", False)
    elif status_code == 401:
        return ("unauthorized", "Authentication token expired or invalid", True)
    elif status_code == 403:
        return ("forbidden", "Access forbidden - check permissions", False)
    elif status_code == 404:
        return ("not_found", "Resource not found in QuickBooks", False)
    elif status_code == 429:
        return ("rate_limited", "QuickBooks API rate limit exceeded", True)
    elif status_code == 500:
        return ("server_error", "QuickBooks server error", True)
    elif status_code == 503:
        return ("service_unavailable", "QuickBooks service temporarily unavailable", True)
    else:
        return ("unknown", f"HTTP {status_code}: {response_text[:100]}", False)

def refresh_access_token():
    """Refresh the access token using refresh token"""
    if not tokens['refresh_token']:
        logger.error("No refresh token available - please re-authenticate via OAuth")
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
            headers=headers,
            timeout=QB_AUTH_TIMEOUT
        )

        if response.status_code == 200:
            token_data = response.json()
            tokens['access_token'] = token_data['access_token']
            tokens['refresh_token'] = token_data['refresh_token']
            tokens['expires_at'] = datetime.now() + timedelta(seconds=token_data['expires_in'])
            save_tokens()  # Save tokens to file
            logger.info("Access token refreshed successfully")
            return True
        elif response.status_code == 401:
            # Refresh token is invalid or expired - clear tokens to allow re-authentication
            error_type, error_msg, is_retryable = categorize_error(response.status_code, response.text)
            logger.error(f"Refresh token is invalid or expired ({error_type}): {error_msg}")
            logger.error("Clearing tokens to allow re-authentication. Please complete OAuth flow again.")
            clear_tokens()
            return False
        else:
            error_type, error_msg, is_retryable = categorize_error(response.status_code, response.text)
            logger.error(f"Failed to refresh token ({error_type}): {error_msg}")
            logger.debug(f"Response: {response.text}")

            # If error indicates invalid credentials, clear tokens
            if response.status_code in [400, 403]:
                logger.error("Token refresh failed with auth error - clearing tokens to allow re-authentication")
                clear_tokens()

            return False
    except Timeout:
        logger.error(f"Token refresh timeout after {QB_AUTH_TIMEOUT}s - QuickBooks OAuth server may be unreachable")
        return False
    except ConnectionError as e:
        logger.error(f"Connection error during token refresh: {str(e)} - check network connectivity")
        return False
    except RequestException as e:
        logger.error(f"Request error during token refresh: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error refreshing token: {str(e)}")
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

def make_qb_request(endpoint, company_id=None, max_retries=None):
    """
    Make a request to QuickBooks API with timeout, retry logic, and circuit breaker

    Args:
        endpoint: API endpoint to call
        company_id: QuickBooks company ID (optional, will use stored value if not provided)
        max_retries: Maximum retry attempts (default: QB_MAX_RETRIES)

    Returns:
        JSON response or None on failure
    """
    # Check circuit breaker
    if not check_circuit_breaker():
        logger.error("Circuit breaker is OPEN - request rejected")
        return None

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

    if max_retries is None:
        max_retries = QB_MAX_RETRIES

    last_error = None

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=QB_API_TIMEOUT)

            if response.status_code == 200:
                # Success - record it for circuit breaker
                record_circuit_breaker_success()
                return response.json()

            elif response.status_code == 401:
                # Token expired - try to refresh and retry
                logger.warning("Access token expired or invalid (401). Attempting token refresh...")
                if refresh_access_token():
                    logger.info("Token refreshed successfully, retrying request...")
                    headers['Authorization'] = f'Bearer {tokens["access_token"]}'
                    response = requests.get(url, headers=headers, timeout=QB_API_TIMEOUT)
                    if response.status_code == 200:
                        record_circuit_breaker_success()
                        return response.json()

                error_type, error_msg, is_retryable = categorize_error(response.status_code, response.text)
                logger.error(f"QuickBooks API error after token refresh ({error_type}): {error_msg}")
                record_circuit_breaker_failure()
                return None

            elif response.status_code == 429:
                # Rate limited - retry with exponential backoff
                error_type, error_msg, is_retryable = categorize_error(response.status_code, response.text)
                logger.warning(f"QuickBooks API rate limited (429). Attempt {attempt + 1}/{max_retries}")

                if attempt < max_retries - 1:
                    delay = QB_INITIAL_RETRY_DELAY * (QB_RETRY_BACKOFF_FACTOR ** attempt)
                    logger.info(f"Waiting {delay:.1f}s before retry due to rate limiting...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Rate limit exceeded after {max_retries} attempts")
                    record_circuit_breaker_failure()
                    return None

            elif response.status_code >= 500:
                # Server error - retry with exponential backoff
                error_type, error_msg, is_retryable = categorize_error(response.status_code, response.text)
                logger.warning(f"QuickBooks server error ({error_type}). Attempt {attempt + 1}/{max_retries}")

                if attempt < max_retries - 1:
                    delay = QB_INITIAL_RETRY_DELAY * (QB_RETRY_BACKOFF_FACTOR ** attempt)
                    logger.info(f"Retrying in {delay:.1f}s due to server error...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Server error persisted after {max_retries} attempts: {error_msg}")
                    record_circuit_breaker_failure()
                    return None

            else:
                # Other errors - don't retry
                error_type, error_msg, is_retryable = categorize_error(response.status_code, response.text)
                logger.error(f"QuickBooks API error ({error_type}): {error_msg}")
                logger.debug(f"Response: {response.text[:500]}")
                record_circuit_breaker_failure()
                return None

        except Timeout:
            last_error = f"Request timeout after {QB_API_TIMEOUT}s"
            logger.warning(f"{last_error}. Attempt {attempt + 1}/{max_retries}")

            if attempt < max_retries - 1:
                delay = QB_INITIAL_RETRY_DELAY * (QB_RETRY_BACKOFF_FACTOR ** attempt)
                logger.info(f"Retrying in {delay:.1f}s...")
                time.sleep(delay)
                continue
            else:
                logger.error(f"Request failed after {max_retries} timeout attempts")
                record_circuit_breaker_failure()
                return None

        except ConnectionError as e:
            last_error = f"Connection error: {str(e)}"
            logger.warning(f"{last_error}. Attempt {attempt + 1}/{max_retries}")

            if attempt < max_retries - 1:
                delay = QB_INITIAL_RETRY_DELAY * (QB_RETRY_BACKOFF_FACTOR ** attempt)
                logger.info(f"Retrying in {delay:.1f}s...")
                time.sleep(delay)
                continue
            else:
                logger.error(f"Connection failed after {max_retries} attempts")
                record_circuit_breaker_failure()
                return None

        except RequestException as e:
            logger.error(f"Request exception: {str(e)}")
            record_circuit_breaker_failure()
            return None

        except Exception as e:
            logger.error(f"Unexpected error making QuickBooks request: {str(e)}")
            record_circuit_breaker_failure()
            return None

    # Should not reach here, but just in case
    logger.error(f"Request failed after all retry attempts: {last_error}")
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

    # Skip cache update if not authenticated
    if not tokens['access_token'] or not tokens['refresh_token']:
        logger.warning("Skipping cache update - not authenticated. Please complete OAuth flow.")
        return

    logger.info("Updating cache from QuickBooks...")

    try:
        cached_data['customers'] = fetch_customers()
        cached_data['vendors'] = fetch_vendors()
        cached_data['items'] = fetch_items()
        cached_data['invoices'] = fetch_invoices()
        cached_data['last_updated'] = datetime.now()

        # Build search indexes
        build_search_indexes()

        logger.info(f"Cache updated. Customers: {len(cached_data['customers'])}, Vendors: {len(cached_data['vendors'])}, Items: {len(cached_data['items'])}, Invoices: {len(cached_data['invoices'])}")
    except Exception as e:
        logger.error(f"Error during cache update: {str(e)}")
        # Don't raise - just log and continue

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
            'error': 'QuickBooks credentials not configured. Please set QB_CLIENT_ID and QB_CLIENT_SECRET in your .env file'
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

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    """Get authentication status and recommendations"""
    is_authenticated = tokens['access_token'] is not None and tokens['refresh_token'] is not None
    is_expired = is_token_expired() if tokens['expires_at'] else True
    has_config = QB_CLIENT_ID is not None and QB_CLIENT_SECRET is not None

    status = {
        'authenticated': is_authenticated,
        'token_expired': is_expired,
        'has_config': has_config,
        'circuit_breaker_state': circuit_breaker['state'],
        'expires_at': tokens['expires_at'].isoformat() if tokens['expires_at'] else None,
        'company_id': tokens.get('company_id') or QB_COMPANY_ID
    }

    # Provide recommendations
    if not has_config:
        status['recommendation'] = 'Configure QB_CLIENT_ID and QB_CLIENT_SECRET in .env'
        status['action'] = 'configure'
    elif not is_authenticated:
        status['recommendation'] = 'Complete OAuth flow to authenticate'
        status['action'] = 'authenticate'
    elif is_expired:
        status['recommendation'] = 'Token expired - will attempt automatic refresh on next API call'
        status['action'] = 'wait'
    elif circuit_breaker['state'] == 'open':
        status['recommendation'] = 'Circuit breaker is open due to failures - waiting for automatic recovery'
        status['action'] = 'wait'
    else:
        status['recommendation'] = 'Connected and ready'
        status['action'] = 'none'

    return jsonify(status)

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from QuickBooks by clearing tokens"""
    try:
        # Clear tokens using the dedicated function
        clear_tokens()

        # Clear cached data
        global cached_data
        cached_data = {
            'customers': [],
            'vendors': [],
            'items': [],
            'invoices': [],
            'last_updated': None
        }

        # Reset circuit breaker to allow fresh authentication
        global circuit_breaker
        circuit_breaker = {
            'failures': 0,
            'last_failure_time': None,
            'state': 'closed'
        }

        logger.info("Disconnected from QuickBooks and reset circuit breaker")

        return jsonify({
            'success': True,
            'message': 'Disconnected from QuickBooks successfully. Circuit breaker reset.'
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
        'cache_age_minutes': (datetime.now() - cached_data['last_updated']).total_seconds() / 60 if cached_data['last_updated'] else None,
        'circuit_breaker': circuit_breaker['state'],
        'circuit_breaker_failures': circuit_breaker['failures']
    })

@app.route('/api/circuit-breaker/status', methods=['GET'])
def circuit_breaker_status():
    """Get circuit breaker status"""
    return jsonify({
        'state': circuit_breaker['state'],
        'failures': circuit_breaker['failures'],
        'last_failure_time': circuit_breaker['last_failure_time'].isoformat() if circuit_breaker['last_failure_time'] else None,
        'threshold': CIRCUIT_BREAKER_THRESHOLD,
        'timeout_seconds': CIRCUIT_BREAKER_TIMEOUT
    })

@app.route('/api/circuit-breaker/reset', methods=['POST'])
def circuit_breaker_reset():
    """Manually reset circuit breaker"""
    global circuit_breaker
    circuit_breaker = {
        'failures': 0,
        'last_failure_time': None,
        'state': 'closed'
    }
    logger.info("Circuit breaker manually reset")
    return jsonify({
        'success': True,
        'message': 'Circuit breaker has been reset',
        'state': circuit_breaker['state']
    })

# =============================================
# DATA IMPORT ENDPOINTS
# =============================================

@app.route('/api/import/quickbooks', methods=['POST'])
def import_from_quickbooks():
    """
    Import data from QuickBooks cached data.

    Request body (optional):
    {
        "entities": ["customers", "vendors", "items", "invoices"],  // Specific entities to import
        "options": {
            "update_existing": true,
            "mark_complete": true,
            "payment_received": true
        }
    }
    """
    try:
        request_data = request.get_json() or {}
        entities_to_import = request_data.get('entities', ['customers', 'vendors', 'items', 'invoices'])
        options = request_data.get('options', {})

        # Prepare QuickBooks data
        qb_data = {}

        if 'customers' in entities_to_import:
            qb_data['customers'] = cached_data.get('customers', [])

        if 'vendors' in entities_to_import:
            qb_data['vendors'] = cached_data.get('vendors', [])

        if 'items' in entities_to_import:
            qb_data['items'] = cached_data.get('items', [])

        if 'invoices' in entities_to_import:
            qb_data['invoices'] = cached_data.get('invoices', [])

        # Check if we have any data
        total_records = sum(len(data) for data in qb_data.values())
        if total_records == 0:
            return jsonify({
                'error': 'No data available',
                'message': 'QuickBooks cache is empty. Please refresh cache or authenticate first.'
            }), 400

        # Initialize coordinator
        coordinator = ImportCoordinator(DB_CONFIG, logger)

        # Set default options
        import_options = {
            'vendors': {'update_existing': options.get('update_existing', True)},
            'customers': {'update_existing': options.get('update_existing', True)},
            'items': {'update_existing': options.get('update_existing', True)},
            'invoices': {
                'mark_as_complete': options.get('mark_complete', True),
                'set_payment_received': options.get('payment_received', True),
                'create_missing_customers': True,
                'create_missing_parts': True
            }
        }

        # Perform import
        logger.info(f"Starting QuickBooks data import: {entities_to_import}")
        results = coordinator.import_all_from_quickbooks(qb_data, **import_options)

        return jsonify({
            'success': True,
            'message': 'Import completed',
            'results': results
        })

    except Exception as e:
        logger.error(f"Error during QuickBooks import: {e}", exc_info=True)
        return jsonify({
            'error': 'Import failed',
            'message': str(e)
        }), 500


@app.route('/api/import/vendors', methods=['POST'])
def import_vendors():
    """
    Import vendor data.

    Request body:
    {
        "data": [...],  // Array of vendor records
        "options": {
            "update_existing": true
        }
    }
    """
    try:
        request_data = request.get_json()
        if not request_data or 'data' not in request_data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body must contain "data" field with vendor records'
            }), 400

        vendor_data = request_data['data']
        options = request_data.get('options', {'update_existing': True})

        coordinator = ImportCoordinator(DB_CONFIG, logger)
        results = coordinator.import_vendors(vendor_data, **options)

        return jsonify({
            'success': True,
            'message': 'Vendor import completed',
            'results': results
        })

    except Exception as e:
        logger.error(f"Error during vendor import: {e}", exc_info=True)
        return jsonify({
            'error': 'Import failed',
            'message': str(e)
        }), 500


@app.route('/api/import/customers', methods=['POST'])
def import_customers():
    """
    Import customer data.

    Request body:
    {
        "data": [...],  // Array of customer records
        "options": {
            "update_existing": true
        }
    }
    """
    try:
        request_data = request.get_json()
        if not request_data or 'data' not in request_data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body must contain "data" field with customer records'
            }), 400

        customer_data = request_data['data']
        options = request_data.get('options', {'update_existing': True})

        coordinator = ImportCoordinator(DB_CONFIG, logger)
        results = coordinator.import_customers(customer_data, **options)

        return jsonify({
            'success': True,
            'message': 'Customer import completed',
            'results': results
        })

    except Exception as e:
        logger.error(f"Error during customer import: {e}", exc_info=True)
        return jsonify({
            'error': 'Import failed',
            'message': str(e)
        }), 500


@app.route('/api/import/products', methods=['POST'])
def import_products():
    """
    Import product/part data.

    Request body:
    {
        "data": [...],  // Array of product records
        "options": {
            "update_existing": true,
            "filter_inventory": false,
            "filter_non_inventory": false
        }
    }
    """
    try:
        request_data = request.get_json()
        if not request_data or 'data' not in request_data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body must contain "data" field with product records'
            }), 400

        product_data = request_data['data']
        options = request_data.get('options', {'update_existing': True})

        coordinator = ImportCoordinator(DB_CONFIG, logger)
        results = coordinator.import_products(product_data, **options)

        return jsonify({
            'success': True,
            'message': 'Product import completed',
            'results': results
        })

    except Exception as e:
        logger.error(f"Error during product import: {e}", exc_info=True)
        return jsonify({
            'error': 'Import failed',
            'message': str(e)
        }), 500


@app.route('/api/import/invoices', methods=['POST'])
def import_invoices():
    """
    Import invoice data and create/update work orders.

    Request body:
    {
        "data": [...],  // Array of invoice records
        "options": {
            "mark_as_complete": true,
            "set_payment_received": true,
            "create_missing_customers": true,
            "create_missing_parts": true
        }
    }
    """
    try:
        request_data = request.get_json()
        if not request_data or 'data' not in request_data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'Request body must contain "data" field with invoice records'
            }), 400

        invoice_data = request_data['data']
        options = request_data.get('options', {
            'mark_as_complete': True,
            'set_payment_received': True,
            'create_missing_customers': True,
            'create_missing_parts': True
        })

        coordinator = ImportCoordinator(DB_CONFIG, logger)
        results = coordinator.import_invoices(invoice_data, **options)

        return jsonify({
            'success': True,
            'message': 'Invoice import completed',
            'results': results
        })

    except Exception as e:
        logger.error(f"Error during invoice import: {e}", exc_info=True)
        return jsonify({
            'error': 'Import failed',
            'message': str(e)
        }), 500


@app.route('/api/import/status', methods=['GET'])
def import_status():
    """Get import capabilities and status."""
    return jsonify({
        'available_importers': ['vendors', 'customers', 'products', 'invoices'],
        'quickbooks_cache_status': {
            'customers': len(cached_data.get('customers', [])),
            'vendors': len(cached_data.get('vendors', [])),
            'items': len(cached_data.get('items', [])),
            'invoices': len(cached_data.get('invoices', []))
        },
        'database_connected': get_db_connection() is not None
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

                # Reset circuit breaker on successful authentication
                global circuit_breaker
                circuit_breaker = {
                    'failures': 0,
                    'last_failure_time': None,
                    'state': 'closed'
                }
                logger.info("Circuit breaker reset after successful authentication")

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

    # Only run initial cache update if we have valid tokens
    if tokens['access_token'] and tokens['refresh_token']:
        logger.info("Valid tokens found - running initial cache update")
        update_cache()
    else:
        logger.info("No valid tokens - skipping initial cache update. Please authenticate via OAuth.")

if __name__ == '__main__':
    # Start scheduler in background thread
    scheduler_thread = threading.Thread(target=start_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    app.run(host='0.0.0.0', port=5002, debug=True)
