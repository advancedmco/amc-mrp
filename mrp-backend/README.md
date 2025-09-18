# MRP Backend - QuickBooks Integration Service

A Python Flask-based backend service that integrates with QuickBooks Online (QBO) to provide real-time data access and search capabilities for MRP (Material Requirements Planning) operations.

## Overview

This service acts as a daemon that:
- Maintains OAuth2 authentication with QuickBooks Online
- Automatically refreshes access tokens to prevent expiration
- Fetches and caches customer, vendor, and product/service data hourly
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

### Search Endpoints

- `GET /api/search/client_names?q={query}&limit=15`
- `GET /api/search/vendor_names?q={query}&limit=15`
- `GET /api/search/product_names?q={query}&limit=15`
- `GET /api/search/product_descriptions?q={query}&limit=15`

### Management Endpoints

- `GET /api/cache/status` - Get cache status and counts
- `POST /api/cache/refresh` - Manually trigger cache refresh

### OAuth Endpoints

- `GET /callback` - OAuth2 callback handler

## Data Structure

### Cached Data

The service maintains three main data collections:

- **Customers**: Client information with names and contact details
- **Vendors**: Supplier information with names and contact details
- **Items**: Products and services with names, descriptions, and pricing

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
- Additional QuickBooks entities (invoices, bills, etc.)
- Metrics and monitoring dashboard
