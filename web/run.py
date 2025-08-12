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
    os.environ.setdefault('DB_HOST', 'mysql')
    os.environ.setdefault('DB_NAME', 'amcmrp')
    os.environ.setdefault('DB_USER', 'amc')
    os.environ.setdefault('DB_PASSWORD', 'Workbench.lavender.chrome')
    os.environ.setdefault('DB_PORT', '3306')
    
    # Template and output paths
    os.environ.setdefault('COC_TEMPLATE_PATH', '../DevAssets/COC Template.docx')
    os.environ.setdefault('COC_OUTPUT_DIR', '../output')
    os.environ.setdefault('PO_TEMPLATE_PATH', '../DevAssets/PO Template.docx')
    os.environ.setdefault('PO_OUTPUT_DIR', '../output')
    
    print("Starting Advanced Machine Co. MRP Web Dashboard...")
    print("Dashboard will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
