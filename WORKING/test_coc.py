#!/usr/bin/env python3
"""
Test Script for COC Generator
Tests all components of the Certificate of Completion generation system.

Author: Advanced Machine Co. MRP System
Created: August 2025
"""

import os
import sys
import getpass
from datetime import datetime, date
import mysql.connector
from mysql.connector import Error

# Add the current directory to Python path to import cocGenerate
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from cocGenerate import COCGenerator, load_config
    print("✓ COC Generator module imported successfully")
except ImportError as e:
    print(f"✗ Failed to import COC Generator: {e}")
    print("Make sure cocGenerate.py is in the same directory")
    sys.exit(1)


class COCTester:
    """
    Comprehensive tester for COC Generator
    """
    
    def __init__(self):
        self.db_connection = None
        self.test_work_order_id = None
        self.config = None
        
    def print_header(self, title):
        """Print a formatted header"""
        print("\n" + "="*60)
        print(f" {title}")
        print("="*60)
    
    def print_step(self, step_num, description):
        """Print a test step"""
        print(f"\n[Step {step_num}] {description}")
        print("-" * 40)
    
    def get_database_config(self):
        """Get database configuration from docker-config environment"""
        
        return {
            'host': os.environ.get('DB_HOST'),
            'database': os.environ.get('DB_NAME'),
            'user': os.environ.get('DB_USER'),
            'password': os.environ.get('DB_PASSWORD'),
            'port': 3306
        }
    
    def test_database_connection(self, db_config):
        """Test database connectivity"""
        self.print_step(1, "Testing Database Connection")
        
        try:
            self.db_connection = mysql.connector.connect(**db_config)
            if self.db_connection.is_connected():
                print("✓ Database connection successful")
                
                # Test basic query
                cursor = self.db_connection.cursor()
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                print(f"✓ MySQL Version: {version[0]}")
                cursor.close()
                return True
        except Error as e:
            print(f"✗ Database connection failed: {e}")
            return False
    
    def validate_existing_data(self):
        """Validate existing test data in database"""
        self.print_step(2, "Validating Existing Test Data")
        
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            
            # Check customers
            cursor.execute("SELECT CustomerID, CustomerName FROM Customers")
            customers = cursor.fetchall()
            print(f"✓ Found {len(customers)} customers:")
            for customer in customers:
                print(f"  - {customer['CustomerName']} (ID: {customer['CustomerID']})")
            
            # Check parts
            cursor.execute("SELECT PartID, PartNumber, PartName FROM Parts")
            parts = cursor.fetchall()
            print(f"✓ Found {len(parts)} parts:")
            for part in parts:
                print(f"  - {part['PartNumber']}: {part['PartName']} (ID: {part['PartID']})")
            
            # Check vendors
            cursor.execute("SELECT VendorID, VendorName FROM Vendors")
            vendors = cursor.fetchall()
            print(f"✓ Found {len(vendors)} vendors:")
            for vendor in vendors:
                print(f"  - {vendor['VendorName']} (ID: {vendor['VendorID']})")
            
            cursor.close()
            
            if customers and parts:
                return customers[0], parts[0]  # Return first customer and part for testing
            else:
                print("✗ Missing required test data")
                return None, None
                
        except Error as e:
            print(f"✗ Data validation failed: {e}")
            return None, None
    
    def create_test_work_order(self, customer, part):
        """Create a test work order for COC generation"""
        self.print_step(3, "Creating Test Work Order")
        
        try:
            cursor = self.db_connection.cursor()
            
            # Insert test work order
            insert_query = """
            INSERT INTO WorkOrders (
                CustomerID, PartID, CustomerPONumber, QuantityOrdered, 
                QuantityCompleted, StartDate, DueDate, Status, Notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                customer['CustomerID'],
                part['PartID'],
                'TEST-PO-12345',
                100,
                95,  # Slightly less than ordered to simulate real scenario
                date.today(),
                date.today(),
                'Completed',
                'Test work order for COC generation testing'
            )
            
            cursor.execute(insert_query, values)
            self.db_connection.commit()
            
            self.test_work_order_id = cursor.lastrowid
            print(f"✓ Test work order created with ID: {self.test_work_order_id}")
            
            # Get the auto-generated work order number
            cursor.execute("SELECT WorkOrderNumber FROM WorkOrders WHERE WorkOrderID = %s", 
                         (self.test_work_order_id,))
            wo_number = cursor.fetchone()[0]
            print(f"✓ Work Order Number: {wo_number}")
            
            # Add production stage data
            stage_query = """
            INSERT INTO ProductionStages (
                WorkOrderID, StageName, QuantityIn, QuantityOut, StageDate, Notes
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            stage_values = (
                self.test_work_order_id,
                'ready to ship',
                95,
                95,
                date.today(),
                'Final quantity ready for shipment'
            )
            
            cursor.execute(stage_query, stage_values)
            self.db_connection.commit()
            print("✓ Production stage data added")
            
            cursor.close()
            return True
            
        except Error as e:
            print(f"✗ Test work order creation failed: {e}")
            return False
    
    def test_template_exists(self):
        """Test if COC template exists"""
        self.print_step(4, "Checking COC Template")
        
        template_path = "DevAssets/COC Template.docx"
        if os.path.exists(template_path):
            print(f"✓ Template found: {template_path}")
            return template_path
        else:
            print(f"✗ Template not found: {template_path}")
            # Try alternative path
            alt_path = "../DevAssets/COC Template.docx"
            if os.path.exists(alt_path):
                print(f"✓ Template found at alternative path: {alt_path}")
                return alt_path
            else:
                print("✗ Template not found at alternative path either")
                return None
    
    def setup_coc_config(self, db_config, template_path):
        """Setup configuration for COC generator"""
        self.print_step(5, "Setting up COC Generator Configuration")
        
        # Create output directory
        output_dir = "CACHE"
        os.makedirs(output_dir, exist_ok=True)
        
        self.config = {
            'database': db_config,
            'quickbooks': {
                'client_id': '',
                'client_secret': '',
                'redirect_uri': '',
                'refresh_token': '',
                'company_id': '',
                'environment': 'sandbox'
            },
            'template': {
                'path': template_path
            },
            'output': {
                'directory': output_dir
            }
        }
        
        print("✓ COC Generator configuration created")
        print(f"✓ Output directory: {output_dir}")
        print(f"✓ Template path: {template_path}")
        return True
    
    def test_coc_generation(self):
        """Test the actual COC generation"""
        self.print_step(6, "Testing COC Generation")
        
        try:
            # Initialize COC Generator
            print("Initializing COC Generator...")
            coc_gen = COCGenerator(self.config)
            
            # Generate COC
            print(f"Generating COC for Work Order ID: {self.test_work_order_id}")
            pdf_path, cert_id = coc_gen.generate_coc(
                work_order_id=self.test_work_order_id,
                created_by="Test Script"
            )
            
            print(f"✓ COC generated successfully!")
            print(f"✓ PDF Path: {pdf_path}")
            print(f"✓ Certificate Log ID: {cert_id}")
            
            # Verify PDF exists
            if os.path.exists(pdf_path):
                file_size = os.path.getsize(pdf_path)
                print(f"✓ PDF file exists ({file_size} bytes)")
            else:
                print("✗ PDF file not found")
                return False
            
            # Verify database logging
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM CertificatesLog WHERE CertificateLogID = %s", (cert_id,))
            cert_record = cursor.fetchone()
            
            if cert_record:
                print("✓ Certificate logged to database:")
                print(f"  - Certificate Number: {cert_record['CertificateNumber']}")
                print(f"  - Part Number: {cert_record['PartNumber']}")
                print(f"  - Quantity: {cert_record['Quantity']}")
                print(f"  - Completion Date: {cert_record['CompletionDate']}")
            else:
                print("✗ Certificate not found in database")
                return False
            
            cursor.close()
            coc_gen.close_connections()
            
            return True, pdf_path
            
        except Exception as e:
            print(f"✗ COC generation failed: {e}")
            return False, None
    
    def cleanup_test_data(self):
        """Clean up test data"""
        self.print_step(7, "Cleanup Test Data")
        
        response = input("Do you want to clean up the test work order? (y/n): ").lower()
        
        if response == 'y':
            try:
                cursor = self.db_connection.cursor()
                
                # Delete production stages
                cursor.execute("DELETE FROM ProductionStages WHERE WorkOrderID = %s", 
                             (self.test_work_order_id,))
                
                # Delete certificates log
                cursor.execute("DELETE FROM CertificatesLog WHERE WorkOrderID = %s", 
                             (self.test_work_order_id,))
                
                # Delete work order
                cursor.execute("DELETE FROM WorkOrders WHERE WorkOrderID = %s", 
                             (self.test_work_order_id,))
                
                self.db_connection.commit()
                cursor.close()
                
                print("✓ Test data cleaned up")
            except Error as e:
                print(f"✗ Cleanup failed: {e}")
        else:
            print("Test data preserved for further inspection")
    
    def run_full_test(self):
        """Run the complete test suite"""
        self.print_header("COC Generator Test Suite")
        
        try:
            # Step 1: Database connection
            db_config = self.get_database_config()
            if not self.test_database_connection(db_config):
                return False
            
            # Step 2: Validate existing data
            customer, part = self.validate_existing_data()
            if not customer or not part:
                return False
            
            # Step 3: Create test work order
            if not self.create_test_work_order(customer, part):
                return False
            
            # Step 4: Check template
            template_path = self.test_template_exists()
            if not template_path:
                return False
            
            # Step 5: Setup configuration
            if not self.setup_coc_config(db_config, template_path):
                return False
            
            # Step 6: Test COC generation
            success, pdf_path = self.test_coc_generation()
            if not success:
                return False
            
            # Success summary
            self.print_header("TEST RESULTS - SUCCESS!")
            print("✓ All tests passed successfully!")
            print(f"✓ Generated COC PDF: {pdf_path}")
            print("✓ Database logging working correctly")
            print("✓ COC Generator is ready for production use")
            
            # Step 7: Cleanup
            self.cleanup_test_data()
            
            return True
            
        except Exception as e:
            print(f"\n✗ Test suite failed with error: {e}")
            return False
        
        finally:
            if self.db_connection and self.db_connection.is_connected():
                self.db_connection.close()
                print("\nDatabase connection closed")


def main():
    """Main test function"""
    print("COC Generator Test Script")
    print("This script will test all components of the Certificate of Completion generator")
    print("\nPrerequisites:")
    print("- MySQL server running on localhost")
    print("- Database 'amcmrp' exists with schema created")
    print("- User 'amc' has access to the database")
    print("- COC Template.docx exists in DevAssets folder")
    
    input("\nPress Enter to continue...")
    
    tester = COCTester()
    success = tester.run_full_test()
    
    if success:
        print("\n🎉 COC Generator is ready to use!")
        print("\nNext steps:")
        print("1. Install any missing Python dependencies if needed")
        print("2. Set up QuickBooks integration (optional)")
        print("3. Integrate into your MRP web interface")
    else:
        print("\n❌ Some tests failed. Please review the errors above.")
        print("Common issues:")
        print("- Missing Python dependencies (pip install mysql-connector-python python-docx pypandoc)")
        print("- Missing pandoc system dependency (brew install pandoc on macOS)")
        print("- Database connection issues")
        print("- Missing COC template file")
        print("- File permissions for PDF generation")


if __name__ == "__main__":
    main()
