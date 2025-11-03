#!/usr/bin/env python3
"""
Startup script for Advanced Machine Co. MRP Web Dashboard
"""

import os
import sys

# Add the parent directory to the path so we can import from WORKING
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

if __name__ == '__main__':
    # Set environment variables for development
    os.getenv('DB_HOST')
    os.getenv('DB_NAME')
    os.getenv('DB_USER')
    os.getenv('DB_PASSWORD')
    os.getenv('DB_PORT', '3306')
    
    # Template and output paths
    os.getenv('COC_TEMPLATE_PATH')
    os.getenv('PO_TEMPLATE_PATH')
    os.getenv('COC_OUTPUT_DIR')
    os.getenv('PO_OUTPUT_DIR')
    
    print("Starting Advanced Machine Co. MRP Web Dashboard...")
    print("Dashboard will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
