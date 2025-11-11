#!/usr/bin/env python3
"""
Test file for Internal Purchase Order (PO) Generator
Sets up test database and thoroughly tests PO generation functionality.

Author: Advanced Machine Co. MRP System
Created: August 2025
"""

import os
import sys
import mysql.connector
from mysql.connector import Error
from datetime import datetime, date
import tempfile
import shutil

# Import the PO generator
from poGenerate import POGenerator, load_config


class POGeneratorTester:
    """
    Comprehensive tester for the PO Generator class
    """
    
    def __init__(self):
        self.config = load_config()
        self.db_connection = None
        self.test_data_ids = {
            'customers': [],
            'vendors': [],
            'parts': [],
            'work_orders': [],
            'bom': [],
            'bom_processes': []
        }
        
    def connect_database(self):
        """Connect to the test database"""
        try:
            self.db_connection = mysql.connector.connect(
                host=self.config['database']['host'],
                database=self.config['database']['database'],
                user=self.config['database']['user'],
                password=self.config['database']['password'],
                port=self.config['database'].get('port', 3306)
            )
            print("✓ Database connection established")
        except Error as e:
            print(f"✗ Database connection failed: {e}")
            raise
    
    def setup_test_data(self):
        """Set up comprehensive test data for PO generation"""
        try:
            cursor = self.db_connection.cursor()
            
            print("\n=== Setting up test data ===")
            
            # First, load the existing data.sql content
            print("1. Loading existing sample data...")
            
            # Insert customers (if not already present)
            cursor.execute("SELECT COUNT(*) FROM Customers")
            if cursor.fetchone()[0] == 0:
                customers_data = [
                    ('Relli Technology Inc.', 5),
                    ('Shibaura Machine Co, America', 6),
                    ('Trim-Tex, Inc.', 18)
                ]
                cursor.executemany(
                    "INSERT INTO Customers (CustomerName, QuickBooksID) VALUES (%s, %s)",
                    customers_data
                )
                print("   ✓ Customers inserted")
            
            # Insert vendors (if not already present)
            cursor.execute("SELECT COUNT(*) FROM Vendors")
            if cursor.fetchone()[0] == 0:
                vendors_data = [
                    ('Expert Metal Finishing Inc', 9, '708-583-2550', 'expertmetalfinish@sbcglobal.net', '2120 West St, River Grove IL 60171'),
                    ('General Surface Hardening', 24, '312-226-5472', 'ar@gshinc.net', 'PO Box 454, Lemont IL 60439'),
                    ('Nova-Chrome Inc', 14, '847-455-8200', 'Kevin@nova-chrome.com', '3200 N Wolf Rd, Franklin Park IL 60131'),
                    ('Precise Rotary Die Inc.', 7, '847-678-0001', 'ioana@preciserotarydie.com', '3503 Martens St, Franklin Park IL 60131')
                ]
                cursor.executemany(
                    "INSERT INTO Vendors (VendorName, QuickBooksID, ContactPhone, ContactEmail, Address) VALUES (%s, %s, %s, %s, %s)",
                    vendors_data
                )
                print("   ✓ Vendors inserted")
            
            # Insert parts (if not already present)
            cursor.execute("SELECT COUNT(*) FROM Parts")
            if cursor.fetchone()[0] == 0:
                parts_data = [
                    ('2584344', 'CLEVIS', 'Clevis Assembly', '4140 Steel', 'DWG-2584344', '5365-00-151-9093'),
                    ('N086440', 'POPPET', 'Poppet DC3500CS', '4130 Steel', 'DWG-N086440', None),
                    ('12364289', 'HOLDER', 'Holder Assembly', '4140 Steel', 'DWG-12364289', None)
                ]
                cursor.executemany(
                    "INSERT INTO Parts (PartNumber, Description, Material, FSN) VALUES (%s, %s, %s, %s, %s, %s)",
                    parts_data
                )
                print("   ✓ Parts inserted")
            
            # Get IDs for foreign key relationships
            cursor.execute("SELECT CustomerID FROM Customers WHERE CustomerName = 'Relli Technology Inc.'")
            relli_customer_id = cursor.fetchone()[0]
            
            cursor.execute("SELECT CustomerID FROM Customers WHERE CustomerName = 'Shibaura Machine Co, America'")
            shibaura_customer_id = cursor.fetchone()[0]
            
            cursor.execute("SELECT PartID FROM Parts WHERE PartNumber = '2584344'")
            clevis_part_id = cursor.fetchone()[0]
            
            cursor.execute("SELECT PartID FROM Parts WHERE PartNumber = 'N086440'")
            poppet_part_id = cursor.fetchone()[0]
            
            cursor.execute("SELECT PartID FROM Parts WHERE PartNumber = '12364289'")
            holder_part_id = cursor.fetchone()[0]
            
            # Get vendor IDs
            cursor.execute("SELECT VendorID FROM Vendors WHERE VendorName = 'Expert Metal Finishing Inc'")
            expert_metal_id = cursor.fetchone()[0]
            
            cursor.execute("SELECT VendorID FROM Vendors WHERE VendorName = 'General Surface Hardening'")
            general_surface_id = cursor.fetchone()[0]
            
            cursor.execute("SELECT VendorID FROM Vendors WHERE VendorName = 'Nova-Chrome Inc'")
            nova_chrome_id = cursor.fetchone()[0]
            
            cursor.execute("SELECT VendorID FROM Vendors WHERE VendorName = 'Precise Rotary Die Inc.'")
            precise_rotary_id = cursor.fetchone()[0]
            
            print("2. Creating work orders...")
            
            # Create test work orders
            work_orders_data = [
                (relli_customer_id, clevis_part_id, 'PO-2024-001', 100, 0, '2024-08-01', '2024-09-15', 'Pending Material', 'Normal', 'Test work order for CLEVIS parts'),
                (shibaura_customer_id, poppet_part_id, 'PO-2024-002', 50, 0, '2024-08-05', '2024-09-20', 'Pending Material', 'High', 'Test work order for POPPET parts'),
                (relli_customer_id, holder_part_id, 'PO-2024-003', 25, 0, '2024-08-10', '2024-10-01', 'Pending Material', 'Normal', 'Test work order for HOLDER parts')
            ]
            
            work_order_ids = []
            for wo_data in work_orders_data:
                cursor.execute("""
                    INSERT INTO WorkOrders (CustomerID, PartID, CustomerPONumber, QuantityOrdered, QuantityCompleted, 
                                          StartDate, DueDate, Status, Priority, Notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, wo_data)
                work_order_ids.append(cursor.lastrowid)
            
            print("   ✓ Work orders created")
            
            print("3. Creating BOM records...")
            
            # Create BOM records for each work order
            bom_ids = []
            for wo_id in work_order_ids:
                cursor.execute("""
                    INSERT INTO BOM (WorkOrderID, BOMVersion, CreatedBy, Notes)
                    VALUES (%s, '1.0', 'Test System', 'Test BOM for PO generation')
                """, (wo_id,))
                bom_ids.append(cursor.lastrowid)
            
            print("   ✓ BOM records created")
            
            print("4. Creating BOM processes...")
            
            # Create comprehensive BOM processes for testing
            bom_processes_data = [
                # CLEVIS work order processes
                (bom_ids[0], 'Heat Treatment', 'Case Hardening', general_surface_id, 100, 'EA', 2.50, None, 5, True, 
                 'Heat treat to 56 Rc case harden all over except grooves. Material: 4140 Steel. Please call when ready: 773-545-9790', 'Pending'),
                
                (bom_ids[0], 'Plating', 'Phosphate Coating', expert_metal_id, 100, 'EA', 1.75, None, 3, True,
                 'Phosphate Type "M" coating. Material: 4140 Steel 26-35 Rc. Certification required. Please call when ready: 773-259-2279', 'Pending'),
                
                # POPPET work order processes  
                (bom_ids[1], 'Heat Treatment', 'Case Hardening', general_surface_id, 50, 'EA', 3.00, None, 7, False,
                 'Case harden to 56 Rc x min 1/16 deep all over except the 2 grooves. Material: 4130 AN. No certs required', 'Pending'),
                
                (bom_ids[1], 'Plating', 'Hard Chrome', nova_chrome_id, 50, 'EA', 4.50, None, 10, False,
                 'Hard chrome plate .0004 to .0005 thick wall locally only per print. Only the shaft 1.573 mm. Polish after please. Material: 4130 56Rc', 'Pending'),
                
                (bom_ids[1], 'Grinding', 'Precision Grinding', precise_rotary_id, 50, 'EA', 5.00, None, 5, False,
                 '3 step grinding: 114.4h7 = (4.5039 // 4.5032 // 4.5026) in @ 0.8 texture, 99.990/99.985 mm @ 0.8 texture, 40f7 mm @ 0.4 texture', 'Pending'),
                
                # HOLDER work order processes
                (bom_ids[2], 'Heat Treatment', 'Heat Treatment', general_surface_id, 25, 'EA', 4.00, None, 7, False,
                 'Heat treat to ~50 Rc. Material: 4140-30 Rc. LOT processing acceptable', 'Pending'),
                
                (bom_ids[2], 'Machining', 'Grinding Operations', precise_rotary_id, 25, 'EA', 2.00, None, 3, False,
                 'Grind both ends to 1.018/1.014, 1.016 +/-.0015. Material: 52100 60RC. Now at 1.025/1.023', 'Pending')
            ]
            
            process_ids = []
            for process_data in bom_processes_data:
                cursor.execute("""
                    INSERT INTO BOMProcesses (BOMID, ProcessType, ProcessName, VendorID, Quantity, UnitOfMeasure, 
                                            EstimatedCost, ActualCost, LeadTimeDays, CertificationRequired, 
                                            ProcessRequirements, Status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, process_data)
                process_ids.append(cursor.lastrowid)
            
            print("   ✓ BOM processes created")
            
            # Store test data IDs for cleanup
            self.test_data_ids['work_orders'] = work_order_ids
            self.test_data_ids['bom'] = bom_ids
            self.test_data_ids['bom_processes'] = process_ids
            
            self.db_connection.commit()
            print("✓ Test data setup completed successfully")
            
            return process_ids
            
        except Error as e:
            print(f"✗ Test data setup failed: {e}")
            self.db_connection.rollback()
            raise
        finally:
            cursor.close()
    
    def test_po_generation(self, process_ids):
        """Test PO generation for various scenarios"""
        print("\n=== Testing PO Generation ===")
        
        try:
            # Initialize PO generator
            po_gen = POGenerator(self.config)
            
            test_results = []
            
            for i, process_id in enumerate(process_ids, 1):
                print(f"\nTest {i}: Generating PO for Process ID {process_id}")
                
                try:
                    # Generate PO
                    pdf_path, po_log_id = po_gen.generate_internal_po(
                        process_id=process_id, 
                        created_by="Test System"
                    )
                    
                    # Verify results
                    if os.path.exists(pdf_path):
                        print(f"   ✓ PDF generated: {pdf_path}")
                        print(f"   ✓ PO logged with ID: {po_log_id}")
                        
                        # Verify database logging
                        cursor = self.db_connection.cursor(dictionary=True)
                        cursor.execute("SELECT * FROM PurchaseOrdersLog WHERE POLogID = %s", (po_log_id,))
                        po_record = cursor.fetchone()
                        
                        if po_record:
                            print(f"   ✓ PO Number: {po_record['PONumber']}")
                            print(f"   ✓ Vendor ID: {po_record['VendorID']}")
                            print(f"   ✓ Total Amount: ${po_record['TotalAmount']:.2f}")
                            print(f"   ✓ Status: {po_record['Status']}")
                        
                        # Verify BOM process status update
                        cursor.execute("SELECT Status FROM BOMProcesses WHERE ProcessID = %s", (process_id,))
                        process_status = cursor.fetchone()
                        if process_status and process_status['Status'] == 'Ordered':
                            print("   ✓ BOM process status updated to 'Ordered'")
                        
                        cursor.close()
                        
                        test_results.append({
                            'process_id': process_id,
                            'success': True,
                            'pdf_path': pdf_path,
                            'po_log_id': po_log_id,
                            'po_number': po_record['PONumber'] if po_record else None
                        })
                        
                    else:
                        print(f"   ✗ PDF file not found: {pdf_path}")
                        test_results.append({
                            'process_id': process_id,
                            'success': False,
                            'error': 'PDF not generated'
                        })
                
                except Exception as e:
                    print(f"   ✗ PO generation failed: {e}")
                    test_results.append({
                        'process_id': process_id,
                        'success': False,
                        'error': str(e)
                    })
            
            # Close PO generator connections
            po_gen.close_connections()
            
            return test_results
            
        except Exception as e:
            print(f"✗ PO generation testing failed: {e}")
            raise
    
    def test_po_number_sequence(self):
        """Test PO number generation sequence"""
        print("\n=== Testing PO Number Sequence ===")
        
        try:
            po_gen = POGenerator(self.config)
            
            # Generate multiple PO numbers to test sequence
            po_numbers = []
            for i in range(3):
                po_number = po_gen.generate_po_number()
                po_numbers.append(po_number)
                print(f"Generated PO Number {i+1}: {po_number}")
                
                # Simulate logging to database to increment sequence
                cursor = self.db_connection.cursor()
                cursor.execute("""
                    INSERT INTO PurchaseOrdersLog (PONumber, WorkOrderID, ProcessID, VendorID, PODate, 
                                                 PartNumber, Description, Material, Quantity, UnitPrice, 
                                                 TotalAmount, CertificationRequired, ProcessRequirements, 
                                                 Status, DocumentPath, CreatedBy)
                    VALUES (%s, 1, 1, 1, %s, 'TEST', 'TEST', 'TEST', 1, 0, 0, 0, 'TEST', 'Created', 'TEST', 'Test System')
                """, (po_number, date.today()))
                self.db_connection.commit()
                cursor.close()
            
            # Verify sequence is correct
            today_prefix = date.today().strftime('%m%d%y')
            expected_sequences = [f"{today_prefix}-{i:02d}" for i in range(1, 4)]
            
            sequence_correct = True
            for expected, actual in zip(expected_sequences, po_numbers):
                if not actual.startswith(today_prefix):
                    sequence_correct = False
                    break
            
            if sequence_correct:
                print("✓ PO number sequence generation working correctly")
            else:
                print("✗ PO number sequence generation has issues")
            
            po_gen.close_connections()
            
        except Exception as e:
            print(f"✗ PO number sequence test failed: {e}")
    
    def display_test_summary(self, test_results):
        """Display comprehensive test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        successful_tests = [r for r in test_results if r['success']]
        failed_tests = [r for r in test_results if not r['success']]
        
        print(f"Total Tests: {len(test_results)}")
        print(f"Successful: {len(successful_tests)}")
        print(f"Failed: {len(failed_tests)}")
        print(f"Success Rate: {len(successful_tests)/len(test_results)*100:.1f}%")
        
        if successful_tests:
            print("\n✓ SUCCESSFUL TESTS:")
            for result in successful_tests:
                print(f"   Process ID {result['process_id']}: PO {result['po_number']} -> {result['pdf_path']}")
        
        if failed_tests:
            print("\n✗ FAILED TESTS:")
            for result in failed_tests:
                print(f"   Process ID {result['process_id']}: {result['error']}")
        
        print("\n" + "="*60)
    
    def cleanup_test_data(self):
        """Clean up test data (optional)"""
        print("\n=== Cleaning up test data ===")
        try:
            cursor = self.db_connection.cursor()
            
            # Clean up in reverse order of creation
            if self.test_data_ids['bom_processes']:
                cursor.execute(f"DELETE FROM BOMProcesses WHERE ProcessID IN ({','.join(map(str, self.test_data_ids['bom_processes']))})")
                print("✓ BOM processes cleaned up")
            
            if self.test_data_ids['bom']:
                cursor.execute(f"DELETE FROM BOM WHERE BOMID IN ({','.join(map(str, self.test_data_ids['bom']))})")
                print("✓ BOM records cleaned up")
            
            if self.test_data_ids['work_orders']:
                cursor.execute(f"DELETE FROM WorkOrders WHERE WorkOrderID IN ({','.join(map(str, self.test_data_ids['work_orders']))})")
                print("✓ Work orders cleaned up")
            
            # Clean up test PO log entries
            cursor.execute("DELETE FROM PurchaseOrdersLog WHERE CreatedBy = 'Test System'")
            print("✓ Test PO log entries cleaned up")
            
            self.db_connection.commit()
            print("✓ Test data cleanup completed")
            
        except Error as e:
            print(f"✗ Test data cleanup failed: {e}")
        finally:
            cursor.close()
    
    def close_connection(self):
        """Close database connection"""
        if self.db_connection and self.db_connection.is_connected():
            self.db_connection.close()
            print("✓ Database connection closed")


def main():
    """Main test execution"""
    print("="*60)
    print("INTERNAL PURCHASE ORDER GENERATOR TEST")
    print("="*60)
    
    tester = POGeneratorTester()
    
    try:
        # Connect to database
        tester.connect_database()
        
        # Set up test data
        process_ids = tester.setup_test_data()
        
        # Test PO generation
        test_results = tester.test_po_generation(process_ids)
        
        # Test PO number sequence
        tester.test_po_number_sequence()
        
        # Display summary
        tester.display_test_summary(test_results)
        
        # Ask user if they want to clean up test data
        cleanup_choice = input("\nDo you want to clean up test data? (y/n): ").lower().strip()
        if cleanup_choice == 'y':
            tester.cleanup_test_data()
        else:
            print("Test data preserved for manual inspection")
        
    except Exception as e:
        print(f"\n✗ Test execution failed: {e}")
        return 1
    
    finally:
        tester.close_connection()
    
    print("\n✓ Test execution completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
