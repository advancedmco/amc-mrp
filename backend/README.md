# MRP Backend - QuickBooks Integration Service

A Python Flask-based backend service that integrates with QuickBooks Online (QBO) to provide real-time data access and search capabilities for MRP (Material Requirements Planning) operations.

## Overview

This service acts as a daemon that:
- Maintains OAuth2 authentication with QuickBooks Online
- Automatically refreshes access tokens to prevent expiration
- Fetches and caches customer, vendor, product/service, and invoice data hourly
- Provides fast search APIs for web applications
- Runs continuously in the background

## Features

- **OAuth2 Token Management**: Automatic token refresh with configurable check intervals
- **Data Caching**: Hourly cache updates from QuickBooks API
- **Search Indexes**: In-memory indexes for fast searching
- **RESTful API**: Flask-based API endpoints for data access
- **Docker Support**: Containerized deployment with docker-compose

## Prerequisites

- Python 3.11+
- QuickBooks Online sandbox or production account
- Valid QuickBooks API credentials (Client ID, Client Secret)
- Docker and docker-compose (for containerized deployment)

## Quick Start

### Local Development with Virtual Environment

1. **Navigate to the backend directory:**
   ```bash
   cd mrp-backend
   ```

2. **Set up virtual environment:**
   ```bash
   python setup_venv.py
   ```

3. **Activate virtual environment:**
   - Windows: `activate_venv.bat`
   - Linux/Mac: `source activate_venv.sh`

4. **Run the service:**
   ```bash
   python app.py
   ```

The service will start on `http://localhost:5002`

Authenticate backend container with QBO Oauth via `https://appcenter.intuit.com/connect/oauth2?client_id=ABbK0d9uTJsEGwlP7W9YNqRpTdj0GDVmxMmyWaYVvwZ10CyVC4&response_type=code&scope=com.intuit.quickbooks.accounting&redirect_uri=https://mrp.inge.st/callback&state=test
`

### Docker Deployment

1. **Ensure .env file is configured** with QuickBooks credentials
2. **Start with docker-compose:**
   ```bash
   docker-compose up mrp-backend
   ```

## Configuration

### Environment Variables

Create a `.env` file in the project root with:

```env
# QuickBooks API Credentials
QUICKBOOKS_CLIENT_ID=your_client_id_here
QUICKBOOKS_CLIENT_SECRET=your_client_secret_here
QUICKBOOKS_SANDBOX_BASE_URL=https://sandbox-quickbooks.api.intuit.com

# Database Connection (if needed)
DB_HOST=mysql
DB_USER=amc
DB_PASSWORD=your_db_password
DB_NAME=amcmrp

# Security
SECRET_KEY=your_secret_key_here
```

### QuickBooks OAuth2 Setup

1. **Register your application** in the QuickBooks Developer Console
2. **Configure redirect URI:** `http://localhost:5002/callback` (for local development)
3. **Obtain Client ID and Client Secret**
4. **Initial OAuth flow:** Visit the authorization URL to grant permissions

## API Endpoints

### 🔍 Search Endpoints
Live search functionality with fast in-memory indexing. All search endpoints support partial matching and are case-insensitive.

#### `GET /api/search/{index_name}`
**Parameters:**
- `q` (required): Search query string
- `limit` (optional): Maximum results to return (default: 15, max: 100)

**Available Indexes:**
- `client_names` - Search customer names, company names, and email addresses
- `vendor_names` - Search vendor names, company names, and email addresses  
- `product_names` - Search product/service names and SKUs
- `product_descriptions` - Search product descriptions and names
- `part_names` - Alias for product_names (search product names and SKUs)
- `part_numbers` - Search SKUs and product names
- `client_pos` - Client purchase orders (future implementation)

**Example Requests:**
```bash
# Search for customers containing "acme"
GET /api/search/client_names?q=acme&limit=10

# Search for products containing "widget"
GET /api/search/product_names?q=widget&limit=5

# Search for vendors by email domain
GET /api/search/vendor_names?q=@example.com&limit=20
```

**Response Format:**
```json
{
  "query": "search_term",
  "results": [
    {
      "id": "123",
      "name": "Product Name",
      "type": "item",
      "active": true,
      "sku": "PROD-001",
      "unit_price": 29.99
    }
  ],
  "total": 1
}
```

### 📊 Cache Management Endpoints

#### `GET /api/cache/status`
Get current cache status and data counts.

**Response:**
```json
{
  "last_updated": "2025-09-20T19:47:30.642440",
  "customers_count": 25,
  "vendors_count": 12,
  "items_count": 150,
  "invoices_count": 42
}
```

#### `POST /api/cache/refresh`
Manually trigger cache refresh from QuickBooks.

**Response:**
```json
{
  "message": "Cache refreshed successfully"
}
```

### 🔧 System Information Endpoints

#### `GET /api/config`
Get current system configuration (for debugging).

**Response:**
```json
{
  "company_id": "9341455374253726",
  "client_id": "ABbK0d9uTJ...",
  "has_access_token": true,
  "has_refresh_token": true,
  "token_expires_at": "2025-09-20T20:47:30.642440"
}
```

#### `GET /api/health`
Health check endpoint with system status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-20T19:47:30.642440",
  "version": "1.0.0",
  "authenticated": true,
  "cache_age_minutes": 15.5
}
```

#### `GET /api/indexes/status`
Get status of all search indexes.

**Response:**
```json
{
  "indexes": {
    "client_names": 25,
    "vendor_names": 12,
    "product_names": 150,
    "product_descriptions": 89,
    "part_names": 150,
    "part_numbers": 45,
    "client_pos": 0
  },
  "total_indexed_items": 471,
  "available_indexes": ["client_names", "vendor_names", "product_names", ...]
}
```

### 📋 Data Access Endpoints (Debug/Development)

#### `GET /api/data/customers`
Get raw customer data from cache.

**Parameters:**
- `limit` (optional): Maximum records to return (default: 50)

#### `GET /api/data/vendors`
Get raw vendor data from cache.

**Parameters:**
- `limit` (optional): Maximum records to return (default: 50)

#### `GET /api/data/items`
Get raw item data from cache.

**Parameters:**
- `limit` (optional): Maximum records to return (default: 50)

#### `GET /api/data/invoices`
Get raw invoice data from cache.

**Parameters:**
- `limit` (optional): Maximum records to return (default: 50)

### 🔐 OAuth Endpoints

#### `GET /callback`
OAuth2 callback handler for QuickBooks authentication.

**Note:** This endpoint is called automatically by QuickBooks during the OAuth flow.

## 🧪 Testing the API

### Quick Test Commands

```bash
# Check if service is running
curl http://localhost:5002/api/health

# Check authentication status
curl http://localhost:5002/api/config

# Check cache status
curl http://localhost:5002/api/cache/status

# Check search indexes
curl http://localhost:5002/api/indexes/status

# Test search functionality (after authentication)
curl "http://localhost:5002/api/search/client_names?q=test&limit=5"
curl "http://localhost:5002/api/search/product_names?q=widget&limit=10"

# Manually refresh cache
curl -X POST http://localhost:5002/api/cache/refresh

# Get sample data
curl "http://localhost:5002/api/data/customers?limit=5"
curl "http://localhost:5002/api/data/items?limit=10"
curl "http://localhost:5002/api/data/invoices?limit=10"
```

### PowerShell Test Commands (Windows)

```powershell
# Check service health
Invoke-RestMethod -Uri "http://localhost:5002/api/health" -Method Get

# Check cache status
Invoke-RestMethod -Uri "http://localhost:5002/api/cache/status" -Method Get

# Test search
Invoke-RestMethod -Uri "http://localhost:5002/api/search/client_names?q=test&limit=5" -Method Get

# Refresh cache
Invoke-RestMethod -Uri "http://localhost:5002/api/cache/refresh" -Method Post
```

### Using the Test Script

Run the comprehensive test script:
```bash
# Inside Docker container
docker exec amc-mrp-backend python test_qb_integration.py

# Or locally (if running outside Docker)
python test_qb_integration.py
```

## Data Structure

### Cached Data

The service maintains four main data collections:

- **Customers**: Client information with names and contact details
- **Vendors**: Supplier information with names and contact details
- **Items**: Products and services with names, descriptions, and pricing
- **Invoices**: Invoice data with customer references, line items, and amounts

### Search Indexes

Fast in-memory indexes for:
- Client names
- Vendor names
- Product names
- Product descriptions
- Part names (mapped to product names)
- Part numbers (mapped to product names)

## Architecture

### Components

1. **Token Manager**: Handles OAuth2 token refresh and validation
2. **Data Fetcher**: Retrieves data from QuickBooks API
3. **Cache Manager**: Maintains in-memory data cache
4. **Index Builder**: Creates searchable indexes from cached data
5. **API Server**: Flask application serving search endpoints

### Background Processes

- **Scheduler**: Runs hourly cache updates
- **Token Refresh**: Checks token expiration every 5 minutes
- **Health Monitoring**: Logs cache status and API health

## Development

### Project Structure

```
mrp-backend/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── setup_venv.py         # Virtual environment setup script
├── README.md             # This file
└── instructions.txt      # Original requirements
```

### Adding New Search Indexes

1. Add index name to `search_indexes` dictionary in `app.py`
2. Implement indexing logic in `build_search_indexes()` function
3. Add API endpoint in the routes section
4. Update this README with the new endpoint

### Extending Data Sources

1. Add new fetch function (e.g., `fetch_invoices()`)
2. Update `update_cache()` to include new data
3. Build appropriate search indexes
4. Add corresponding API endpoints

## Monitoring and Logging

The service provides comprehensive logging:
- Token refresh events
- Cache update operations
- API request/response details
- Error conditions and recovery

Check logs for:
- Successful token refreshes
- Cache update completion times
- Search query performance
- API error responses

## Troubleshooting

### Common Issues

1. **Token Expiration**: Service automatically handles refresh
2. **API Rate Limits**: Implements appropriate delays between requests
3. **Network Issues**: Includes retry logic for failed requests
4. **Data Sync Issues**: Manual refresh available via API

### Debug Mode

Run with debug logging:
```bash
export FLASK_ENV=development
python app.py
```

### Health Checks

- Check cache status: `GET /api/cache/status`
- Verify token validity in logs
- Monitor container logs with `docker-compose logs mrp-backend`

## Security Considerations

- Store credentials securely (use .env, not in code)
- Implement proper token storage for production
- Use HTTPS in production deployments
- Regularly rotate API credentials
- Monitor for unusual API usage patterns

## Performance

- **Cache Updates**: Hourly refresh (configurable)
- **Search Performance**: In-memory indexes, sub-second response times
- **Memory Usage**: Optimized for typical QuickBooks data volumes
- **Concurrent Requests**: Flask default threading model

## Future Enhancements

- Database persistence for cached data
- Advanced search with filters and sorting
- Real-time data synchronization
- Additional QuickBooks entities (bills, purchase orders, etc.)
- Invoice search indexing
- Metrics and monitoring dashboard
