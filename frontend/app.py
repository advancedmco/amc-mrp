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
import requests
from collections import defaultdict

# Add WORKING directory to path to import generators
sys.path.append(os.path.join(os.path.dirname(__file__), 'generators'))

try:
    from cocGenerate import COCGenerator, load_config as load_coc_config
    from poGenerate import POGenerator, load_config as load_po_config
except ImportError as e:
    print(f"Warning: Could not import generators: {e}")
    COCGenerator = None
    POGenerator = None

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MRPDashboard:
    """Main dashboard class for MRP operations"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
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
                p.Description,
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
                wo.CustomerPONumber,
                wo.QuantityOrdered,
                wo.QuantityCompleted,
                wo.CompletionDate,
                wo.PaymentStatus,
                c.CustomerName,
                p.PartNumber,
                p.Description,
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
                wo.CustomerPONumber,
                wo.QuantityOrdered,
                wo.QuantityCompleted,
                wo.CompletionDate,
                wo.PaymentStatus,
                c.CustomerName,
                p.PartNumber,
                p.Description,
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
                p.Description,
                p.Material,
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

    def get_dashboard_metrics(self):
        """Get key performance metrics for dashboard"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)

            metrics = {}

            # Active orders count
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM WorkOrders
                WHERE Status NOT IN ('Completed', 'Shipped')
            """)
            metrics['active_orders'] = cursor.fetchone()['count']

            # Orders due this week
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM WorkOrders
                WHERE Status NOT IN ('Completed', 'Shipped')
                AND DueDate BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
            """)
            metrics['due_this_week'] = cursor.fetchone()['count']

            # Overdue orders
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM WorkOrders
                WHERE Status NOT IN ('Completed', 'Shipped')
                AND DueDate < CURDATE()
            """)
            metrics['overdue_orders'] = cursor.fetchone()['count']

            # Pending payment count
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM WorkOrders
                WHERE PaymentStatus = 'Not Received'
                AND Status IN ('Completed', 'Shipped')
            """)
            metrics['pending_payments'] = cursor.fetchone()['count']

            # Total revenue (estimated from completed orders)
            cursor.execute("""
                SELECT
                    SUM(bp.ActualCost) as total_revenue
                FROM WorkOrders wo
                JOIN BOM b ON wo.WorkOrderID = b.WorkOrderID
                JOIN BOMProcesses bp ON b.BOMID = bp.BOMID
                WHERE wo.Status IN ('Completed', 'Shipped')
                AND wo.CompletionDate >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """)
            result = cursor.fetchone()
            metrics['monthly_revenue'] = float(result['total_revenue']) if result['total_revenue'] else 0.0

            # Orders completed this month
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM WorkOrders
                WHERE Status IN ('Completed', 'Shipped')
                AND CompletionDate >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """)
            metrics['completed_this_month'] = cursor.fetchone()['count']

            # Average completion time (days)
            cursor.execute("""
                SELECT AVG(DATEDIFF(CompletionDate, StartDate)) as avg_days
                FROM WorkOrders
                WHERE Status IN ('Completed', 'Shipped')
                AND CompletionDate >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                AND StartDate IS NOT NULL
            """)
            result = cursor.fetchone()
            metrics['avg_completion_days'] = float(result['avg_days']) if result['avg_days'] else 0.0

            cursor.close()
            conn.close()

            return metrics

        except Error as e:
            logger.error(f"Failed to get dashboard metrics: {e}")
            return {}

    def get_chart_data(self):
        """Get aggregated data for charts"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)

            chart_data = {}

            # Orders by status
            cursor.execute("""
                SELECT Status, COUNT(*) as count
                FROM WorkOrders
                WHERE Status NOT IN ('Completed', 'Shipped')
                GROUP BY Status
                ORDER BY count DESC
            """)
            chart_data['orders_by_status'] = cursor.fetchall()

            # Orders by priority
            cursor.execute("""
                SELECT Priority, COUNT(*) as count
                FROM WorkOrders
                WHERE Status NOT IN ('Completed', 'Shipped')
                GROUP BY Priority
                ORDER BY FIELD(Priority, 'Urgent', 'High', 'Normal', 'Low')
            """)
            chart_data['orders_by_priority'] = cursor.fetchall()

            # Payment status distribution
            cursor.execute("""
                SELECT PaymentStatus, COUNT(*) as count
                FROM WorkOrders
                WHERE Status IN ('Completed', 'Shipped')
                GROUP BY PaymentStatus
            """)
            chart_data['payment_status'] = cursor.fetchall()

            # Orders timeline (last 30 days)
            cursor.execute("""
                SELECT
                    DATE(CompletionDate) as date,
                    COUNT(*) as count
                FROM WorkOrders
                WHERE CompletionDate >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY DATE(CompletionDate)
                ORDER BY date
            """)
            chart_data['completion_timeline'] = cursor.fetchall()

            # Top customers by order count
            cursor.execute("""
                SELECT
                    c.CustomerName,
                    COUNT(wo.WorkOrderID) as order_count
                FROM WorkOrders wo
                JOIN Customers c ON wo.CustomerID = c.CustomerID
                WHERE wo.CreatedDate >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                GROUP BY c.CustomerID, c.CustomerName
                ORDER BY order_count DESC
                LIMIT 10
            """)
            chart_data['top_customers'] = cursor.fetchall()

            cursor.close()
            conn.close()

            return chart_data

        except Error as e:
            logger.error(f"Failed to get chart data: {e}")
            return {}

    def get_filtered_orders(self, status=None, priority=None, search=None, sort_by='CreatedDate', sort_order='DESC', limit=100, offset=0):
        """Get orders with filtering, sorting, and pagination"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # Build query with filters
            query = """
            SELECT
                wo.WorkOrderID,
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
                p.Description,
                p.Material,
                DATEDIFF(wo.DueDate, CURDATE()) as DaysUntilDue
            FROM WorkOrders wo
            JOIN Customers c ON wo.CustomerID = c.CustomerID
            JOIN Parts p ON wo.PartID = p.PartID
            WHERE 1=1
            """

            params = []

            if status:
                query += " AND wo.Status = %s"
                params.append(status)

            if priority:
                query += " AND wo.Priority = %s"
                params.append(priority)

            if search:
                query += """ AND (
                    wo.WorkOrderID LIKE %s OR
                    wo.CustomerPONumber LIKE %s OR
                    c.CustomerName LIKE %s OR
                    p.PartNumber LIKE %s OR
                    p.Description LIKE %s
                )"""
                search_param = f"%{search}%"
                params.extend([search_param] * 5)

            # Add sorting
            allowed_sort_fields = ['WorkOrderID', 'CustomerName', 'DueDate', 'Status', 'Priority', 'CreatedDate']
            if sort_by in allowed_sort_fields:
                sort_order = 'ASC' if sort_order.upper() == 'ASC' else 'DESC'
                query += f" ORDER BY wo.{sort_by} {sort_order}"
            else:
                query += " ORDER BY wo.CreatedDate DESC"

            # Add pagination
            query += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cursor.execute(query, params)
            orders = cursor.fetchall()

            # Get total count
            count_query = """
            SELECT COUNT(*) as total
            FROM WorkOrders wo
            JOIN Customers c ON wo.CustomerID = c.CustomerID
            JOIN Parts p ON wo.PartID = p.PartID
            WHERE 1=1
            """

            if status:
                count_query += " AND wo.Status = %s"
            if priority:
                count_query += " AND wo.Priority = %s"
            if search:
                count_query += """ AND (
                    wo.WorkOrderID LIKE %s OR
                    wo.CustomerPONumber LIKE %s OR
                    c.CustomerName LIKE %s OR
                    p.PartNumber LIKE %s OR
                    p.Description LIKE %s
                )"""

            cursor.execute(count_query, params[:-2])  # Exclude limit/offset
            total = cursor.fetchone()['total']

            cursor.close()
            conn.close()

            return {'orders': orders, 'total': total}

        except Error as e:
            logger.error(f"Failed to get filtered orders: {e}")
            return {'orders': [], 'total': 0}

    def get_customers(self):
        """Get all customers"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT CustomerID, CustomerName, QuickBooksID
                FROM Customers
                ORDER BY CustomerName
            """)
            customers = cursor.fetchall()

            cursor.close()
            conn.close()

            return customers

        except Error as e:
            logger.error(f"Failed to get customers: {e}")
            return []

    def get_parts(self):
        """Get all parts"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT PartID, PartNumber, Description, Material, FSN
                FROM Parts
                ORDER BY PartNumber
            """)
            parts = cursor.fetchall()

            cursor.close()
            conn.close()

            return parts

        except Error as e:
            logger.error(f"Failed to get parts: {e}")
            return []

    def get_vendors(self):
        """Get all vendors"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT VendorID, VendorName, QuickBooksID
                FROM Vendors
                ORDER BY VendorName
            """)
            vendors = cursor.fetchall()

            cursor.close()
            conn.close()

            return vendors

        except Error as e:
            logger.error(f"Failed to get vendors: {e}")
            return []

    def get_customer_pos(self):
        """Get all customer purchase orders"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT
                    cpo.CustomerPOID,
                    cpo.PONumber,
                    cpo.PODate,
                    cpo.DueDate,
                    c.CustomerName
                FROM CustomerPurchaseOrders cpo
                JOIN Customers c ON cpo.CustomerID = c.CustomerID
                ORDER BY cpo.PODate DESC
            """)
            customer_pos = cursor.fetchall()

            cursor.close()
            conn.close()

            return customer_pos

        except Error as e:
            logger.error(f"Failed to get customer POs: {e}")
            return []

    def get_all_workorders(self):
        """Get all workorders"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT
                    wo.WorkOrderID,
                    wo.WorkOrderNumber,
                    p.PartNumber,
                    p.Description,
                    c.CustomerName
                FROM WorkOrders wo
                JOIN Parts p ON wo.PartID = p.PartID
                JOIN Customers c ON wo.CustomerID = c.CustomerID
                ORDER BY wo.CreatedDate DESC
            """)
            workorders = cursor.fetchall()

            cursor.close()
            conn.close()

            return workorders

        except Error as e:
            logger.error(f"Failed to get workorders: {e}")
            return []

    def add_customer_po(self, po_number, customer_id, po_date, due_date=None, notes=None, pdf_path=None):
        """Add a new customer purchase order"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            query = """
            INSERT INTO CustomerPurchaseOrders
            (PONumber, CustomerID, PODate, DueDate, Notes, DocumentPath, CreatedDate, UpdatedDate)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """

            cursor.execute(query, (po_number, customer_id, po_date, due_date, notes, pdf_path))
            conn.commit()

            cursor.close()
            conn.close()

            return True, 'Customer PO created successfully'

        except Error as e:
            logger.error(f"Failed to add customer PO: {e}")
            return False, str(e)

    def add_workorder(self, work_order_number, customer_id, part_id, customer_po_id=None,
                     quantity_ordered=1, start_date=None, due_date=None, status='Idle',
                     priority='Normal', notes=None):
        """Add a new workorder"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Check if CustomerPOID is valid
            if customer_po_id and customer_po_id != '':
                # Get CustomerPONumber from CustomerPOID
                cursor.execute("SELECT PONumber FROM CustomerPurchaseOrders WHERE CustomerPOID = %s", (customer_po_id,))
                result = cursor.fetchone()
                customer_po_number = result[0] if result else None
            else:
                customer_po_id = None
                customer_po_number = None

            query = """
            INSERT INTO WorkOrders
            (WorkOrderNumber, CustomerID, PartID, CustomerPOID, CustomerPONumber,
             QuantityOrdered, QuantityCompleted, StartDate, DueDate, Status, Priority,
             Notes, CreatedDate, UpdatedDate)
            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """

            cursor.execute(query, (work_order_number, customer_id, part_id, customer_po_id,
                                 customer_po_number, quantity_ordered, start_date, due_date,
                                 status, priority, notes))
            conn.commit()

            work_order_id = cursor.lastrowid

            # Create BOM entry for this workorder
            bom_query = """
            INSERT INTO BOM (WorkOrderID, CreatedDate, UpdatedDate)
            VALUES (%s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            cursor.execute(bom_query, (work_order_id,))
            conn.commit()

            cursor.close()
            conn.close()

            return True, 'Workorder created successfully'

        except Error as e:
            logger.error(f"Failed to add workorder: {e}")
            return False, str(e)

    def add_bom_process(self, work_order_id, process_type, process_name, vendor_id=None,
                       quantity=1, estimated_cost=None, status='Pending',
                       certification_required=0, notes=None):
        """Add a new BOM process"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Get or create BOM for this workorder
            cursor.execute("SELECT BOMID FROM BOM WHERE WorkOrderID = %s", (work_order_id,))
            result = cursor.fetchone()

            if result:
                bom_id = result[0]
            else:
                # Create BOM if it doesn't exist
                cursor.execute("""
                    INSERT INTO BOM (WorkOrderID, CreatedDate, UpdatedDate)
                    VALUES (%s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (work_order_id,))
                conn.commit()
                bom_id = cursor.lastrowid

            # Add BOM process
            query = """
            INSERT INTO BOMProcesses
            (BOMID, ProcessType, ProcessName, VendorID, Quantity, EstimatedCost,
             Status, CertificationRequired, Notes, CreatedDate, UpdatedDate)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """

            cursor.execute(query, (bom_id, process_type, process_name, vendor_id,
                                 quantity, estimated_cost, status, certification_required, notes))
            conn.commit()

            cursor.close()
            conn.close()

            return True, 'BOM process created successfully'

        except Error as e:
            logger.error(f"Failed to add BOM process: {e}")
            return False, str(e)

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

@app.route('/quickbooks')
def quickbooks_status():
    """QuickBooks connection status page"""
    return render_template('quickbooks_status.html')

@app.route('/quickbooks/data')
def quickbooks_data_viewer():
    """QuickBooks data viewer page"""
    return render_template('quickbooks_data.html')

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

@app.route('/api/dashboard/metrics')
def api_dashboard_metrics():
    """API endpoint for dashboard metrics"""
    try:
        metrics = dashboard.get_dashboard_metrics()
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/charts')
def api_dashboard_charts():
    """API endpoint for chart data"""
    try:
        chart_data = dashboard.get_chart_data()
        # Convert date objects to strings for JSON serialization
        if 'completion_timeline' in chart_data:
            for item in chart_data['completion_timeline']:
                if 'date' in item and isinstance(item['date'], (date, datetime)):
                    item['date'] = item['date'].strftime('%Y-%m-%d')
        return jsonify(chart_data)
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders')
def api_orders():
    """API endpoint for orders with filtering and pagination"""
    try:
        status = request.args.get('status')
        priority = request.args.get('priority')
        search = request.args.get('search')
        sort_by = request.args.get('sort_by', 'CreatedDate')
        sort_order = request.args.get('sort_order', 'DESC')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        result = dashboard.get_filtered_orders(
            status=status,
            priority=priority,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset
        )

        # Convert date objects to strings
        for order in result['orders']:
            for key, value in order.items():
                if isinstance(value, (date, datetime)):
                    order[key] = value.strftime('%Y-%m-%d') if isinstance(value, date) else value.strftime('%Y-%m-%d %H:%M:%S')

        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/qb/sync_status')
def api_qb_sync_status():
    """Get QuickBooks sync status from backend"""
    try:
        backend_url = os.getenv('BACKEND_URL', 'http://backend:5002')
        response = requests.get(f'{backend_url}/api/cache/status', timeout=5)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Backend not available'}), 503

    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to backend: {e}")
        return jsonify({'error': 'Cannot connect to QuickBooks backend', 'details': str(e)}), 503

@app.route('/api/qb/refresh', methods=['POST'])
def api_qb_refresh():
    """Trigger QuickBooks cache refresh"""
    try:
        backend_url = os.getenv('BACKEND_URL', 'http://backend:5002')
        response = requests.post(f'{backend_url}/api/cache/refresh', timeout=30)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Backend refresh failed'}), 500

    except requests.exceptions.RequestException as e:
        logger.error(f"Error triggering backend refresh: {e}")
        return jsonify({'error': 'Cannot connect to QuickBooks backend', 'details': str(e)}), 503

@app.route('/api/qb/config')
def api_qb_config():
    """Get QuickBooks configuration"""
    try:
        backend_url = os.getenv('BACKEND_URL', 'http://backend:5002')
        response = requests.get(f'{backend_url}/api/config', timeout=5)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Backend not available'}), 503

    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting QB config: {e}")
        return jsonify({'error': 'Cannot connect to QuickBooks backend', 'details': str(e)}), 503

@app.route('/api/qb/auth_url')
def api_qb_auth_url():
    """Get QuickBooks OAuth authorization URL"""
    try:
        backend_url = os.getenv('BACKEND_URL', 'http://backend:5002')
        response = requests.get(f'{backend_url}/api/auth/url', timeout=5)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting auth URL: {e}")
        return jsonify({'error': 'Cannot connect to QuickBooks backend', 'details': str(e)}), 503

@app.route('/api/qb/disconnect', methods=['POST'])
def api_qb_disconnect():
    """Disconnect from QuickBooks"""
    try:
        backend_url = os.getenv('BACKEND_URL', 'http://backend:5002')
        response = requests.post(f'{backend_url}/api/disconnect', timeout=5)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        logger.error(f"Error disconnecting from QB: {e}")
        return jsonify({'error': 'Cannot connect to QuickBooks backend', 'details': str(e)}), 503

@app.route('/api/qb/test')
def api_qb_test():
    """Test QuickBooks connection"""
    try:
        backend_url = os.getenv('BACKEND_URL', 'http://backend:5002')
        response = requests.get(f'{backend_url}/api/test', timeout=10)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        logger.error(f"Error testing QB connection: {e}")
        return jsonify({'error': 'Cannot connect to QuickBooks backend', 'details': str(e)}), 503

@app.route('/api/qb/data/customers')
def api_qb_customers():
    """Get QuickBooks customers data"""
    try:
        backend_url = os.getenv('BACKEND_URL', 'http://backend:5002')
        limit = request.args.get('limit', 1000)
        response = requests.get(f'{backend_url}/api/data/customers?limit={limit}', timeout=10)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting QB customers: {e}")
        return jsonify({'error': 'Cannot connect to QuickBooks backend', 'details': str(e)}), 503

@app.route('/api/qb/data/vendors')
def api_qb_vendors():
    """Get QuickBooks vendors data"""
    try:
        backend_url = os.getenv('BACKEND_URL', 'http://backend:5002')
        limit = request.args.get('limit', 1000)
        response = requests.get(f'{backend_url}/api/data/vendors?limit={limit}', timeout=10)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting QB vendors: {e}")
        return jsonify({'error': 'Cannot connect to QuickBooks backend', 'details': str(e)}), 503

@app.route('/api/qb/data/items')
def api_qb_items():
    """Get QuickBooks items data"""
    try:
        backend_url = os.getenv('BACKEND_URL', 'http://backend:5002')
        limit = request.args.get('limit', 1000)
        response = requests.get(f'{backend_url}/api/data/items?limit={limit}', timeout=10)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting QB items: {e}")
        return jsonify({'error': 'Cannot connect to QuickBooks backend', 'details': str(e)}), 503

@app.route('/api/qb/data/invoices')
def api_qb_invoices():
    """Get QuickBooks invoices data"""
    try:
        backend_url = os.getenv('BACKEND_URL', 'http://backend:5002')
        limit = request.args.get('limit', 1000)
        response = requests.get(f'{backend_url}/api/data/invoices?limit={limit}', timeout=10)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting QB invoices: {e}")
        return jsonify({'error': 'Cannot connect to QuickBooks backend', 'details': str(e)}), 503

@app.route('/api/customers')
def api_customers():
    """Get all customers"""
    try:
        customers = dashboard.get_customers()
        return jsonify({'customers': customers})
    except Exception as e:
        logger.error(f"Error getting customers: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/parts')
def api_parts():
    """Get all parts"""
    try:
        parts = dashboard.get_parts()
        return jsonify({'parts': parts})
    except Exception as e:
        logger.error(f"Error getting parts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vendors')
def api_vendors():
    """Get all vendors"""
    try:
        vendors = dashboard.get_vendors()
        return jsonify({'vendors': vendors})
    except Exception as e:
        logger.error(f"Error getting vendors: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/customer_pos')
def api_customer_pos():
    """Get all customer purchase orders"""
    try:
        customer_pos = dashboard.get_customer_pos()
        return jsonify({'customer_pos': customer_pos})
    except Exception as e:
        logger.error(f"Error getting customer POs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/workorders')
def api_workorders():
    """Get all workorders"""
    try:
        workorders = dashboard.get_all_workorders()
        return jsonify({'workorders': workorders})
    except Exception as e:
        logger.error(f"Error getting workorders: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/customer_po/add', methods=['POST'])
def api_add_customer_po():
    """Add a new customer purchase order with optional PDF upload"""
    try:
        po_number = request.form.get('po_number')
        customer_id = request.form.get('customer_id')
        po_date = request.form.get('po_date')
        due_date = request.form.get('due_date')
        notes = request.form.get('notes')

        if not po_number or not customer_id or not po_date:
            return jsonify({'error': 'Missing required fields'}), 400

        # Handle file upload
        pdf_path = None
        if 'po_file' in request.files:
            file = request.files['po_file']
            if file and file.filename:
                # Save file to uploads directory
                upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'customer_pos')
                os.makedirs(upload_dir, exist_ok=True)

                # Generate unique filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{po_number}_{timestamp}.pdf"
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                pdf_path = os.path.join('uploads', 'customer_pos', filename)

        # Add to database
        success, message = dashboard.add_customer_po(
            po_number=po_number,
            customer_id=customer_id,
            po_date=po_date,
            due_date=due_date,
            notes=notes,
            pdf_path=pdf_path
        )

        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({'error': message}), 500

    except Exception as e:
        logger.error(f"Error adding customer PO: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/workorder/add', methods=['POST'])
def api_add_workorder():
    """Add a new workorder"""
    try:
        data = request.get_json()

        required_fields = ['work_order_number', 'customer_id', 'part_id', 'quantity_ordered', 'due_date', 'status', 'priority']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        success, message = dashboard.add_workorder(
            work_order_number=data['work_order_number'],
            customer_id=data['customer_id'],
            part_id=data['part_id'],
            customer_po_id=data.get('customer_po_id'),
            quantity_ordered=data['quantity_ordered'],
            start_date=data.get('start_date'),
            due_date=data['due_date'],
            status=data['status'],
            priority=data['priority'],
            notes=data.get('notes')
        )

        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({'error': message}), 500

    except Exception as e:
        logger.error(f"Error adding workorder: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bom/add', methods=['POST'])
def api_add_bom():
    """Add a new BOM process"""
    try:
        data = request.get_json()

        required_fields = ['work_order_id', 'process_type', 'process_name', 'quantity', 'status']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        success, message = dashboard.add_bom_process(
            work_order_id=data['work_order_id'],
            process_type=data['process_type'],
            process_name=data['process_name'],
            vendor_id=data.get('vendor_id'),
            quantity=data['quantity'],
            estimated_cost=data.get('estimated_cost'),
            status=data['status'],
            certification_required=data.get('certification_required', 0),
            notes=data.get('notes')
        )

        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({'error': message}), 500

    except Exception as e:
        logger.error(f"Error adding BOM process: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
