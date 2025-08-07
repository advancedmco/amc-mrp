
-- Advanced Machine Co. MRP System Database Schema
-- Created: August 2025
-- Purpose: Complete database structure for work order management, BOM, PO generation, and COC tracking

-- Create database and user (Docker Compose no longer creates these automatically)
CREATE DATABASE IF NOT EXISTS amcmrp;
CREATE USER IF NOT EXISTS 'amc'@'%' IDENTIFIED BY 'Workbench.lavender.chrome';
GRANT ALL PRIVILEGES ON amcmrp.* TO 'amc'@'%';
FLUSH PRIVILEGES;

USE amcmrp;

-- =============================================
-- CORE TABLES
-- =============================================

-- 1. Customers Table (Simple structure with QuickBooks integration)
CREATE TABLE Customers (
    CustomerID INT AUTO_INCREMENT PRIMARY KEY,
    CustomerName VARCHAR(100) NOT NULL,
    QuickBooksID INT UNIQUE,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_qb_id (QuickBooksID)
);

-- 2. Vendors Table (For BOM processes and PO generation)
CREATE TABLE Vendors (
    VendorID INT AUTO_INCREMENT PRIMARY KEY,
    VendorName VARCHAR(100) NOT NULL,
    QuickBooksID INT UNIQUE,
    ContactPhone VARCHAR(20),
    ContactEmail VARCHAR(100),
    Address TEXT,
    AccountNumber VARCHAR(50),
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_vendor_qb_id (QuickBooksID)
);

-- 3. Parts Table
CREATE TABLE Parts (
    PartID INT AUTO_INCREMENT PRIMARY KEY,
    PartNumber VARCHAR(100) NOT NULL UNIQUE,
    PartName VARCHAR(200) NOT NULL,
    Description TEXT,
    Material VARCHAR(100),
    DrawingNumber VARCHAR(100),
    FSN VARCHAR(50), -- Federal Stock Number
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_part_number (PartNumber)
);

-- 4. Work Orders Table (Main work order management)
CREATE TABLE WorkOrders (
    WorkOrderID INT AUTO_INCREMENT PRIMARY KEY,
    WorkOrderNumber VARCHAR(50) NOT NULL UNIQUE, -- Sequential numbering
    CustomerID INT NOT NULL,
    PartID INT NOT NULL,
    CustomerPONumber VARCHAR(100),
    QuantityOrdered INT NOT NULL,
    QuantityCompleted INT DEFAULT 0,
    StartDate DATE,
    DueDate DATE,
    CompletionDate DATE,
    Status ENUM('Pending Material', 'Idle', 'On Machine', 'Secondary Operations', 'Quality Control', 'Completed', 'Shipped') DEFAULT 'Pending Material',
    Priority ENUM('Low', 'Normal', 'High', 'Urgent') DEFAULT 'Normal',
    Notes TEXT,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID),
    FOREIGN KEY (PartID) REFERENCES Parts(PartID),
    INDEX idx_wo_number (WorkOrderNumber),
    INDEX idx_customer_po (CustomerPONumber),
    INDEX idx_status (Status)
);

-- =============================================
-- BOM TABLES
-- =============================================

-- 5. BOM Table (Bill of Materials linked to work orders)
CREATE TABLE BOM (
    BOMID INT AUTO_INCREMENT PRIMARY KEY,
    WorkOrderID INT NOT NULL,
    BOMVersion VARCHAR(10) DEFAULT '1.0',
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CreatedBy VARCHAR(100),
    IsActive BOOLEAN DEFAULT TRUE,
    Notes TEXT,
    FOREIGN KEY (WorkOrderID) REFERENCES WorkOrders(WorkOrderID),
    INDEX idx_work_order (WorkOrderID)
);

-- 6. BOM Processes Table (Individual processes within BOMs)
CREATE TABLE BOMProcesses (
    ProcessID INT AUTO_INCREMENT PRIMARY KEY,
    BOMID INT NOT NULL,
    ProcessType ENUM('Raw Material', 'Machining', 'Heat Treatment', 'Plating', 'Grinding', 'Inspection', 'Other') NOT NULL,
    ProcessName VARCHAR(100) NOT NULL,
    VendorID INT, -- NULL for internal processes
    Quantity INT NOT NULL,
    UnitOfMeasure VARCHAR(20) DEFAULT 'EA',
    EstimatedCost DECIMAL(10,2),
    ActualCost DECIMAL(10,2),
    LeadTimeDays INT,
    CertificationRequired BOOLEAN DEFAULT FALSE,
    ProcessRequirements TEXT, -- Multi-line requirements
    Status ENUM('Pending', 'Ordered', 'In Progress', 'Completed') DEFAULT 'Pending',
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (BOMID) REFERENCES BOM(BOMID),
    FOREIGN KEY (VendorID) REFERENCES Vendors(VendorID),
    INDEX idx_bom (BOMID),
    INDEX idx_process_type (ProcessType),
    INDEX idx_vendor (VendorID)
);

-- =============================================
-- LOGGING TABLES (For document generation history)
-- =============================================

-- 7. Purchase Orders Log Table (Historical record of all generated POs)
CREATE TABLE PurchaseOrdersLog (
    POLogID INT AUTO_INCREMENT PRIMARY KEY,
    PONumber VARCHAR(50) NOT NULL,
    WorkOrderID INT NOT NULL,
    ProcessID INT, -- Link to BOM process if applicable
    VendorID INT NOT NULL,
    PODate DATE NOT NULL,
    ExpectedDeliveryDate DATE,
    ActualDeliveryDate DATE,
    PartNumber VARCHAR(100),
    PartName VARCHAR(200),
    Material VARCHAR(100),
    Quantity INT NOT NULL,
    UnitPrice DECIMAL(10,2),
    TotalAmount DECIMAL(10,2),
    CertificationRequired BOOLEAN DEFAULT FALSE,
    ProcessRequirements TEXT,
    Status ENUM('Created', 'Sent', 'Acknowledged', 'Received', 'Cancelled') DEFAULT 'Created',
    DocumentPath VARCHAR(500), -- Path to generated PO document
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CreatedBy VARCHAR(100),
    FOREIGN KEY (WorkOrderID) REFERENCES WorkOrders(WorkOrderID),
    FOREIGN KEY (ProcessID) REFERENCES BOMProcesses(ProcessID),
    FOREIGN KEY (VendorID) REFERENCES Vendors(VendorID),
    INDEX idx_po_number (PONumber),
    INDEX idx_work_order_po (WorkOrderID),
    INDEX idx_vendor_po (VendorID)
);

-- 8. Certificates of Completion Log Table (Historical record of all generated COCs)
CREATE TABLE CertificatesLog (
    CertificateLogID INT AUTO_INCREMENT PRIMARY KEY,
    CertificateNumber VARCHAR(50) NOT NULL,
    WorkOrderID INT NOT NULL,
    CustomerID INT NOT NULL,
    PartNumber VARCHAR(100) NOT NULL,
    Description VARCHAR(200) NOT NULL,
    CustomerPONumber VARCHAR(100),
    Quantity INT NOT NULL,
    CompletionDate DATE NOT NULL,
    DrawingNumber VARCHAR(100),
    FSN VARCHAR(50),
    ApprovedBy VARCHAR(100) DEFAULT 'Beniamin Grama',
    ApproverTitle VARCHAR(100) DEFAULT 'Quality Assurance Manager',
    DocumentPath VARCHAR(500), -- Path to generated COC document
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CreatedBy VARCHAR(100),
    FOREIGN KEY (WorkOrderID) REFERENCES WorkOrders(WorkOrderID),
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID),
    INDEX idx_cert_number (CertificateNumber),
    INDEX idx_work_order_cert (WorkOrderID),
    INDEX idx_customer_cert (CustomerID)
);

-- =============================================
-- SUPPORTING TABLES
-- =============================================

-- 9. Work Order Status History (Track status changes)
CREATE TABLE WorkOrderStatusHistory (
    StatusHistoryID INT AUTO_INCREMENT PRIMARY KEY,
    WorkOrderID INT NOT NULL,
    PreviousStatus VARCHAR(50),
    NewStatus VARCHAR(50) NOT NULL,
    StatusDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ChangedBy VARCHAR(100),
    Notes TEXT,
    FOREIGN KEY (WorkOrderID) REFERENCES WorkOrders(WorkOrderID),
    INDEX idx_work_order_status (WorkOrderID)
);

-- 10. Production Stages (Track quantities through manufacturing process)
CREATE TABLE ProductionStages (
    StageID INT AUTO_INCREMENT PRIMARY KEY,
    WorkOrderID INT NOT NULL,
    StageName VARCHAR(100) NOT NULL,
    QuantityIn INT NOT NULL,
    QuantityOut INT,
    QuantityLoss INT DEFAULT 0,
    StageDate DATE NOT NULL,
    Notes TEXT,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (WorkOrderID) REFERENCES WorkOrders(WorkOrderID),
    INDEX idx_work_order_stage (WorkOrderID)
);

-- =============================================
-- TRIGGERS FOR AUTOMATION
-- =============================================

-- Trigger to auto-generate Work Order Numbers
DELIMITER //
CREATE TRIGGER trg_workorder_number 
BEFORE INSERT ON WorkOrders
FOR EACH ROW
BEGIN
    DECLARE next_number INT;
    SELECT COALESCE(MAX(CAST(SUBSTRING(WorkOrderNumber, 3) AS UNSIGNED)), 0) + 1 
    INTO next_number 
    FROM WorkOrders 
    WHERE WorkOrderNumber REGEXP '^WO[0-9]+$';
    
    SET NEW.WorkOrderNumber = CONCAT('WO', LPAD(next_number, 6, '0'));
END//
DELIMITER ;

-- Trigger to log status changes
DELIMITER //
CREATE TRIGGER trg_workorder_status_history 
AFTER UPDATE ON WorkOrders
FOR EACH ROW
BEGIN
    IF OLD.Status != NEW.Status THEN
        INSERT INTO WorkOrderStatusHistory (WorkOrderID, PreviousStatus, NewStatus, ChangedBy)
        VALUES (NEW.WorkOrderID, OLD.Status, NEW.Status, USER());
    END IF;
END//
DELIMITER ;

-- =============================================
-- VIEWS FOR COMMON QUERIES
-- =============================================

-- View for Work Order Summary
CREATE VIEW vw_WorkOrderSummary AS
SELECT 
    wo.WorkOrderID,
    wo.WorkOrderNumber,
    c.CustomerName,
    p.PartNumber,
    p.PartName,
    wo.CustomerPONumber,
    wo.QuantityOrdered,
    wo.QuantityCompleted,
    wo.Status,
    wo.Priority,
    wo.DueDate,
    DATEDIFF(wo.DueDate, CURDATE()) as DaysUntilDue
FROM WorkOrders wo
JOIN Customers c ON wo.CustomerID = c.CustomerID
JOIN Parts p ON wo.PartID = p.PartID;

-- View for BOM with Process Details
CREATE VIEW vw_BOMDetails AS
SELECT 
    b.BOMID,
    wo.WorkOrderNumber,
    bp.ProcessType,
    bp.ProcessName,
    v.VendorName,
    bp.Quantity,
    bp.EstimatedCost,
    bp.ActualCost,
    bp.Status as ProcessStatus,
    bp.CertificationRequired
FROM BOM b
JOIN WorkOrders wo ON b.WorkOrderID = wo.WorkOrderID
JOIN BOMProcesses bp ON b.BOMID = bp.BOMID
LEFT JOIN Vendors v ON bp.VendorID = v.VendorID;

-- =============================================
-- INDEXES FOR PERFORMANCE
-- =============================================

-- Additional indexes for common queries
CREATE INDEX idx_workorder_status_date ON WorkOrders(Status, DueDate);
CREATE INDEX idx_bom_process_status ON BOMProcesses(Status, ProcessType);
CREATE INDEX idx_po_log_date ON PurchaseOrdersLog(PODate);
CREATE INDEX idx_cert_log_date ON CertificatesLog(CompletionDate);

-- =============================================
-- COMMENTS AND DOCUMENTATION
-- =============================================

/*
DATABASE SCHEMA DOCUMENTATION:

This schema supports the Advanced Machine Co. MRP system with the following key features:

1. WORK ORDER MANAGEMENT:
   - Sequential work order numbering (WO000001, WO000002, etc.)
   - Status tracking through manufacturing stages
   - Quantity tracking with loss accounting
   - Customer and part associations

2. BOM MANAGEMENT:
   - Bill of Materials linked to work orders
   - Individual processes with vendor assignments
   - Cost tracking (estimated vs actual)
   - Certification requirements

3. DOCUMENT GENERATION LOGGING:
   - Purchase Orders: Historical record of all generated POs
   - Certificates of Completion: Historical record for military clients
   - Document path storage for file management

4. QUICKBOOKS INTEGRATION:
   - Customer and Vendor QuickBooks ID storage
   - Ready for API integration

5. REPORTING AND ANALYTICS:
   - Views for common queries
   - Status history tracking
   - Production stage monitoring

USAGE NOTES:
- Work Order Numbers are auto-generated using triggers
- Status changes are automatically logged
- All monetary values use DECIMAL(10,2) for precision
- Timestamps track creation and modification dates
- Foreign key constraints ensure data integrity

IMPLEMENTATION:
To implement this schema:
1. Run this script in MySQL
2. Verify all tables are created successfully
3. Test triggers with sample data
4. Begin building application layer on top
*/
