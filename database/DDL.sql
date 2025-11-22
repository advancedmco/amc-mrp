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
-- DROP EVERYTHING
-- =============================================
DROP VIEW IF EXISTS vw_CustomerPODetails;
DROP VIEW IF EXISTS vw_BOMDetails;
DROP VIEW IF EXISTS vw_WorkOrderSummary;

DROP TRIGGER IF EXISTS trg_workorder_status_history;

DROP TABLE IF EXISTS OAuthTokens;
DROP TABLE IF EXISTS ProductionStages;
DROP TABLE IF EXISTS WorkOrderStatusHistory;
DROP TABLE IF EXISTS CertificatesLog;
DROP TABLE IF EXISTS PurchaseOrdersLog;
DROP TABLE IF EXISTS BOMProcesses;
DROP TABLE IF EXISTS BOM;
DROP TABLE IF EXISTS WorkOrders;
DROP TABLE IF EXISTS CustomerPOLineItems;
DROP TABLE IF EXISTS CustomerPurchaseOrders;
DROP TABLE IF EXISTS Parts;
DROP TABLE IF EXISTS Vendors;
DROP TABLE IF EXISTS Customers;

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
    Description TEXT,
    Material VARCHAR(100),
    FSN VARCHAR(50), -- Federal Stock Number
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_part_number (PartNumber)
);

-- 4. Customer Purchase Orders Table (Incoming orders from customers)
CREATE TABLE CustomerPurchaseOrders (
    PO_ID INT AUTO_INCREMENT PRIMARY KEY,
    PO_Number VARCHAR(50) NOT NULL UNIQUE,
    CustomerID INT,
    Order_Date DATE NOT NULL,
    Total_Value DECIMAL(10,2),
    Status ENUM('Open', 'In Progress', 'Completed', 'Cancelled') DEFAULT 'Open',
    Notes TEXT,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID),
    INDEX idx_po_number (PO_Number),
    INDEX idx_customer_po (CustomerID),
    INDEX idx_order_date (Order_Date)
);

-- 5. Customer PO Line Items Table (Individual parts on each customer PO)
CREATE TABLE CustomerPOLineItems (
    LineItem_ID INT AUTO_INCREMENT PRIMARY KEY,
    PO_ID INT NOT NULL,
    Line_Number INT NOT NULL,
    PartID INT COMMENT 'Foreign key to Parts table for referential integrity',
    Part_Number VARCHAR(100) NOT NULL,
    Description VARCHAR(500),
    Quantity INT NOT NULL,
    Unit_Price DECIMAL(10,2),
    Due_Date DATE,
    Status ENUM('Pending', 'In Production', 'Completed', 'Shipped') DEFAULT 'Pending',
    Notes TEXT,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (PO_ID) REFERENCES CustomerPurchaseOrders(PO_ID) ON DELETE CASCADE,
    FOREIGN KEY (PartID) REFERENCES Parts(PartID),
    INDEX idx_po_line (PO_ID, Line_Number),
    INDEX idx_part_id (PartID),
    INDEX idx_part_number_line (Part_Number),
    INDEX idx_due_date (Due_Date),
    INDEX idx_status (Status),
    CONSTRAINT chk_lineitem_quantity_positive CHECK (Quantity > 0)
);

-- 6. Work Orders Table (Main work order management)
CREATE TABLE WorkOrders (
    WorkOrderID INT AUTO_INCREMENT PRIMARY KEY,
    WorkOrderNumber VARCHAR(50) UNIQUE COMMENT 'Human-readable work order number (e.g., WO-10001)',
    CustomerID INT NOT NULL,
    PartID INT NOT NULL,
    CustomerPOID INT COMMENT 'Direct reference to Customer PO header (denormalized for performance)',
    CustomerPOLineItemID INT,
    QuantityOrdered INT NOT NULL DEFAULT 1 COMMENT 'Quantity ordered for this specific work order',
    QuantityCompleted INT DEFAULT 0,
    StartDate DATE,
    DueDate DATE,
    CompletionDate DATE,
    Status ENUM('Pending Material', 'Idle', 'On Machine', 'Secondary Operations', 'Quality Control', 'Completed', 'Shipped') DEFAULT 'Pending Material',
    PaymentStatus ENUM('Not Received', 'In Progress', 'Received') DEFAULT 'Not Received',
    Priority ENUM('Low', 'Normal', 'High', 'Urgent') DEFAULT 'Normal',
    Notes TEXT,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID),
    FOREIGN KEY (PartID) REFERENCES Parts(PartID),
    FOREIGN KEY (CustomerPOID) REFERENCES CustomerPurchaseOrders(PO_ID) ON DELETE SET NULL,
    FOREIGN KEY (CustomerPOLineItemID) REFERENCES CustomerPOLineItems(LineItem_ID),
    INDEX idx_work_order_number (WorkOrderNumber),
    INDEX idx_customer_po (CustomerPOID),
    INDEX idx_customer_po_lineitem (CustomerPOLineItemID),
    INDEX idx_status (Status),
    CONSTRAINT chk_quantity_ordered_positive CHECK (QuantityOrdered > 0),
    CONSTRAINT chk_quantity_completed_non_negative CHECK (QuantityCompleted >= 0)
) AUTO_INCREMENT=10000;

-- =============================================
-- BOM TABLES
-- =============================================

-- 7. BOM Table (Bill of Materials linked to work orders)
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

-- 8. BOM Processes Table (Individual processes within BOMs)
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

-- 9. Purchase Orders Log Table (Historical record of all generated POs to vendors)
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
    Description TEXT,
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

-- 10. Certificates of Completion Log Table (Historical record of all generated COCs)
CREATE TABLE CertificatesLog (
    CertificateLogID INT AUTO_INCREMENT PRIMARY KEY,
    CertificateNumber VARCHAR(50) NOT NULL,
    WorkOrderID INT NOT NULL,
    WorkOrderNumber VARCHAR(50) COMMENT 'Work order number for reference (optional, may not be used initially)',
    CustomerID INT NOT NULL,
    PartNumber VARCHAR(100) NOT NULL,
    Description VARCHAR(200) NOT NULL,
    CustomerPONumber VARCHAR(100),
    Quantity INT NOT NULL,
    CompletionDate DATE NOT NULL,
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

-- 11. Work Order Status History (Track status changes)
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

-- 12. Production Stages (Track quantities through manufacturing process)
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

-- 13. OAuth Tokens (Persistent storage for QuickBooks OAuth credentials)
CREATE TABLE OAuthTokens (
    TokenID INT AUTO_INCREMENT PRIMARY KEY,
    ServiceName VARCHAR(50) NOT NULL DEFAULT 'QuickBooks',
    AccessToken TEXT,
    RefreshToken TEXT,
    CompanyID VARCHAR(100),
    ExpiresAt DATETIME,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY idx_service_name (ServiceName)
);

-- =============================================
-- TRIGGERS FOR AUTOMATION
-- =============================================

-- Trigger to auto-populate related fields BEFORE INSERT
DELIMITER //
CREATE TRIGGER trg_workorder_before_insert
BEFORE INSERT ON WorkOrders
FOR EACH ROW
BEGIN
    -- Auto-populate CustomerPOID from CustomerPOLineItemID if provided
    IF NEW.CustomerPOLineItemID IS NOT NULL AND NEW.CustomerPOID IS NULL THEN
        SELECT PO_ID INTO NEW.CustomerPOID
        FROM CustomerPOLineItems
        WHERE LineItem_ID = NEW.CustomerPOLineItemID;
    END IF;

    -- Auto-populate PartID from CustomerPOLineItemID if provided and PartID is NULL
    IF NEW.CustomerPOLineItemID IS NOT NULL AND NEW.PartID IS NULL THEN
        SELECT PartID INTO NEW.PartID
        FROM CustomerPOLineItems
        WHERE LineItem_ID = NEW.CustomerPOLineItemID
        LIMIT 1;
    END IF;
END//
DELIMITER ;

-- Trigger to auto-generate WorkOrderNumber AFTER INSERT (when WorkOrderID is available)
DELIMITER //
CREATE TRIGGER trg_workorder_after_insert
AFTER INSERT ON WorkOrders
FOR EACH ROW
BEGIN
    -- Auto-generate WorkOrderNumber if not provided
    IF NEW.WorkOrderNumber IS NULL OR NEW.WorkOrderNumber = '' THEN
        UPDATE WorkOrders
        SET WorkOrderNumber = CONCAT('WO-', LPAD(NEW.WorkOrderID, 5, '0'))
        WHERE WorkOrderID = NEW.WorkOrderID;
    END IF;
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
    c.CustomerID,
    p.PartNumber,
    p.PartID,
    p.Description as PartDescription,
    cpo.PO_Number as CustomerPONumber,
    cpo.PO_ID as CustomerPOID,
    li.LineItem_ID as CustomerPOLineItemID,
    li.Quantity as POLineItemQuantity,
    wo.QuantityOrdered,
    wo.QuantityCompleted,
    wo.Status,
    wo.PaymentStatus,
    wo.Priority,
    wo.StartDate,
    wo.DueDate,
    wo.CompletionDate,
    DATEDIFF(wo.DueDate, CURDATE()) as DaysUntilDue,
    wo.Notes,
    wo.CreatedDate,
    wo.UpdatedDate
FROM WorkOrders wo
JOIN Customers c ON wo.CustomerID = c.CustomerID
JOIN Parts p ON wo.PartID = p.PartID
LEFT JOIN CustomerPOLineItems li ON wo.CustomerPOLineItemID = li.LineItem_ID
LEFT JOIN CustomerPurchaseOrders cpo ON wo.CustomerPOID = cpo.PO_ID;

-- View for BOM with Process Details
CREATE VIEW vw_BOMDetails AS
SELECT
    b.BOMID,
    b.WorkOrderID,
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

-- View for Customer PO Details with Line Items
CREATE VIEW vw_CustomerPODetails AS
SELECT
    cpo.PO_ID as CustomerPOID,
    cpo.PO_Number as CustomerPONumber,
    c.CustomerName,
    c.CustomerID,
    cpo.Order_Date as OrderDate,
    cpo.Total_Value as TotalValue,
    cpo.Status as POStatus,
    li.LineItem_ID as LineItemID,
    li.Line_Number as LineNumber,
    li.Part_Number as PartNumber,
    li.PartID,
    p.Description as PartDescription,
    li.Description as LineItemDescription,
    li.Quantity,
    li.Unit_Price as UnitPrice,
    li.Due_Date as DueDate,
    li.Status as LineItemStatus,
    DATEDIFF(li.Due_Date, CURDATE()) as DaysUntilDue,
    li.Notes
FROM CustomerPurchaseOrders cpo
LEFT JOIN Customers c ON cpo.CustomerID = c.CustomerID
LEFT JOIN CustomerPOLineItems li ON cpo.PO_ID = li.PO_ID
LEFT JOIN Parts p ON li.PartID = p.PartID;

-- =============================================
-- INDEXES FOR PERFORMANCE
-- =============================================

-- Additional indexes for common queries
CREATE INDEX idx_workorder_status_date ON WorkOrders(Status, DueDate);
CREATE INDEX idx_payment_status ON WorkOrders(PaymentStatus);
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
    - Primary key `WorkOrderID` serves as the unique identifier.
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
- `WorkOrderID` is an auto-incrementing primary key.
- Status changes are automatically logged.
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
