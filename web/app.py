#!/usr/bin/env python3
"""
Advanced Machine Co. MRP Web Dashboard
Simple web interface for managing work orders, COCs, and POs.

Author: Advanced Machine Co. MRP System
Created: August 2025
"""

import os
import sys
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from datetime import datetime, date, timedelta
import mysql.connector
from mysql.connector import Error
import logging

# Add WORKING directory to path to import generators
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'WORKING'))

try:
    from cocGenerate import COCGenerator, load_config as load_coc_config
    from poGenerate import POGenerator, load_config as load_po_config
except ImportError as e:
    print(f"Warning: Could not import generators: {e}")
    COCGenerator = None
    POGenerator = None

app = Flask(__name__)
app.secret_key = 'amc-mrp-dashboard-secret-key'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MRPDashboard:
    """Main dashboard class for MRP operations"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'mysql'),
            'database': os.getenv('DB_NAME', 'amcmrp'),
            'user': os.getenv('DB_USER', 'amc'),
            'password': os.getenv('DB_PASSWORD', 'Workbench.lavender.chrome'),
            'port': int(os.getenv('DB_PORT', 3306))
        }
    
    def get_db_connection(self):
        """Get database connection"""
        try:
            return mysql.connector.connect(**self.db_config)
        except Error as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def get_live_orders(self):
        """Get all open/active work orders"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
            SELECT 
                wo.WorkOrderID,
                wo.WorkOrderNumber,
                wo.CustomerPONumber,
                wo.QuantityOrdered,
                wo.QuantityCompleted,
                wo.StartDate,
                wo.DueDate,
                wo.Status,
                wo.Priority,
                wo.PaymentStatus,
                c.CustomerName,
                p.PartNumber,
                p.PartName,
                p.Material,
                DATEDIFF(wo.DueDate, CURDATE()) as DaysUntilDue
            FROM WorkOrders wo
            JOIN Customers c ON wo.CustomerID = c.CustomerID
            JOIN Parts p ON wo.PartID = p.PartID
            WHERE wo.Status != 'Completed' AND wo.Status != 'Shipped'
            ORDER BY wo.CreatedDate DESC
            """
            
            cursor.execute(query)
            orders = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return orders
            
        except Error as e:
            logger.error(f"Failed to get live orders: {e}")
            return []
    
    def get_recent_completed_orders(self):
        """Get recently completed orders (last 30 days)"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
            SELECT 
                wo.WorkOrderID,
                wo.WorkOrderNumber,
                wo.CustomerPONumber,
                wo.QuantityOrdered,
                wo.QuantityCompleted,
                wo.CompletionDate,
                wo.PaymentStatus,
                c.CustomerName,
                p.PartNumber,
                p.PartName,
                p.Material,
                cl.CertificateNumber,
                cl.DocumentPath as COCPath
            FROM WorkOrders wo
            JOIN Customers c ON wo.CustomerID = c.CustomerID
            JOIN Parts p ON wo.PartID = p.PartID
            LEFT JOIN CertificatesLog cl ON wo.WorkOrderID = cl.WorkOrderID
            WHERE wo.Status IN ('Completed', 'Shipped')
            AND wo.CompletionDate >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            ORDER BY wo.CompletionDate DESC
            """
            
            cursor.execute(query)
            orders = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return orders
            
        except Error as e:
            logger.error(f"Failed to get recent completed orders: {e}")
            return []
    
    def get_old_orders(self):
        """Get old completed orders (older than 30 days)"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
            SELECT 
                wo.WorkOrderID,
                wo.WorkOrderNumber,
                wo.CustomerPONumber,
                wo.QuantityOrdered,
                wo.QuantityCompleted,
                wo.CompletionDate,
                wo.PaymentStatus,
                c.CustomerName,
                p.PartNumber,
                p.PartName,
                p.Material,
                cl.CertificateNumber,
                cl.DocumentPath as COCPath
            FROM WorkOrders wo
            JOIN Customers c ON wo.CustomerID = c.CustomerID
            JOIN Parts p ON wo.PartID = p.PartID
            LEFT JOIN CertificatesLog cl ON wo.WorkOrderID = cl.WorkOrderID
            WHERE wo.Status IN ('Completed', 'Shipped')
            AND wo.CompletionDate < DATE_SUB(NOW(), INTERVAL 30 DAY)
            ORDER BY wo.CompletionDate DESC
            LIMIT 100
            """
            
            cursor.execute(query)
            orders = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return orders
            
        except Error as e:
            logger.error(f"Failed to get old orders: {e}")
            return []
    
    def get_order_details(self, work_order_id):
        """Get detailed information for a specific work order"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get work order details
            query = """
            SELECT 
                wo.*,
                c.CustomerName,
                c.QuickBooksID as CustomerQBID,
                p.PartNumber,
                p.PartName,
                p.Description as PartDescription,
                p.Material,
                p.DrawingNumber,
                p.FSN
            FROM WorkOrders wo
            JOIN Customers c ON wo.CustomerID = c.CustomerID
            JOIN Parts p ON wo.PartID = p.PartID
            WHERE wo.WorkOrderID = %s
            """
            
            cursor.execute(query, (work_order_id,))
            order = cursor.fetchone()
            
            if not order:
                return None
            
            # Get BOM processes for this work order
            bom_query = """
            SELECT 
                bp.ProcessID,
                bp.ProcessType,
                bp.ProcessName,
                bp.Quantity,
                bp.EstimatedCost,
                bp.Status,
                bp.CertificationRequired,
                v.VendorName
            FROM BOMProcesses bp
            JOIN BOM b ON bp.BOMID = b.BOMID
            LEFT JOIN Vendors v ON bp.VendorID = v.VendorID
            WHERE b.WorkOrderID = %s
            ORDER BY bp.ProcessType, bp.ProcessName
            """
            
            cursor.execute(bom_query, (work_order_id,))
            processes = cursor.fetchall()
            
            order['BOMProcesses'] = processes
            
            cursor.close()
            conn.close()
            
            return order
            
        except Error as e:
            logger.error(f"Failed to get order details: {e}")
            return None
    
    def update_payment_status(self, work_order_id, payment_status):
        """Update payment status for a work order"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            query = """
            UPDATE WorkOrders 
            SET PaymentStatus = %s, UpdatedDate = CURRENT_TIMESTAMP 
            WHERE WorkOrderID = %s
            """
            
            cursor.execute(query, (payment_status, work_order_id))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return True
            
        except Error as e:
            logger.error(f"Failed to update payment status: {e}")
            return False

# Initialize dashboard
dashboard = MRPDashboard()

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        live_orders = dashboard.get_live_orders()
        recent_completed = dashboard.get_recent_completed_orders()
        old_orders = dashboard.get_old_orders()
        
        return render_template('dashboard.html',
                             live_orders=live_orders,
                             recent_completed=recent_completed,
                             old_orders=old_orders)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash(f"Error loading dashboard: {e}", 'error')
        return render_template('dashboard.html',
                             live_orders=[],
                             recent_completed=[],
                             old_orders=[])

@app.route('/order_details/<int:work_order_id>')
def order_details(work_order_id):
    """Get order details as JSON"""
    try:
        order = dashboard.get_order_details(work_order_id)
        if order:
            # Convert date objects to strings for JSON serialization
            for key, value in order.items():
                if isinstance(value, (date, datetime)):
                    order[key] = value.strftime('%Y-%m-%d') if isinstance(value, date) else value.strftime('%Y-%m-%d %H:%M:%S')
            
            # Convert BOM processes dates
            if 'BOMProcesses' in order:
                for process in order['BOMProcesses']:
                    for key, value in process.items():
                        if isinstance(value, (date, datetime)):
                            process[key] = value.strftime('%Y-%m-%d') if isinstance(value, date) else value.strftime('%Y-%m-%d %H:%M:%S')
            
            return jsonify(order)
        else:
            return jsonify({'error': 'Order not found'}), 404
    except Exception as e:
        logger.error(f"Error getting order details: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate_coc/<int:work_order_id>', methods=['POST'])
def generate_coc(work_order_id):
    """Generate Certificate of Completion"""
    try:
        if not COCGenerator:
            return jsonify({'error': 'COC Generator not available'}), 500
        
        # Load COC configuration
        config = load_coc_config()
        
        # Initialize COC generator
        coc_gen = COCGenerator(config)
        
        # Generate COC
        pdf_path, cert_id = coc_gen.generate_coc(work_order_id, created_by="Web Dashboard")
        
        # Close connections
        coc_gen.close_connections()
        
        return jsonify({
            'success': True,
            'message': 'COC generated successfully',
            'pdf_path': pdf_path,
            'certificate_id': cert_id
        })
        
    except Exception as e:
        logger.error(f"COC generation failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/create_po/<int:process_id>', methods=['POST'])
def create_po(process_id):
    """Create Purchase Order"""
    try:
        if not POGenerator:
            return jsonify({'error': 'PO Generator not available'}), 500
        
        # Load PO configuration
        config = load_po_config()
        
        # Initialize PO generator
        po_gen = POGenerator(config)
        
        # Generate PO
        pdf_path, po_id = po_gen.generate_internal_po(process_id, created_by="Web Dashboard")
        
        # Close connections
        po_gen.close_connections()
        
        return jsonify({
            'success': True,
            'message': 'PO created successfully',
            'pdf_path': pdf_path,
            'po_id': po_id
        })
        
    except Exception as e:
        logger.error(f"PO creation failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/update_payment/<int:work_order_id>', methods=['POST'])
def update_payment(work_order_id):
    """Update payment status"""
    try:
        data = request.get_json()
        payment_status = data.get('payment_status')
        
        if payment_status not in ['Not Received', 'In Progress', 'Received']:
            return jsonify({'error': 'Invalid payment status'}), 400
        
        success = dashboard.update_payment_status(work_order_id, payment_status)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Payment status updated successfully'
            })
        else:
            return jsonify({'error': 'Failed to update payment status'}), 500
            
    except Exception as e:
        logger.error(f"Payment status update failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_pdf/<path:filename>')
def download_pdf(filename):
    """Download generated PDF files"""
    try:
        # Security check - only allow files from output directory
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
        file_path = os.path.join(output_dir, filename)
        
        if os.path.exists(file_path) and file_path.startswith(os.path.abspath(output_dir)):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
            
    except Exception as e:
        logger.error(f"File download failed: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
