-- =============================================
-- BASE INITIAL DATA FOR AMC MRP SYSTEM
-- =============================================
-- This file contains minimal initial data to satisfy all database constraints
-- and provide a working baseline for the MRP system
-- Created: November 2025
-- =============================================

USE amcmrp;

-- =============================================
-- 1. CUSTOMERS - Base customer records
-- =============================================

INSERT INTO Customers (CustomerID, CustomerName, QuickBooksID) VALUES
(1,'Shibaura Machine', NULL),
(2,'Relli Technology', NULL);

-- =============================================
-- 2. VENDORS - Common vendors for various processes
-- =============================================

INSERT INTO Vendors (VendorName, ContactPhone, ContactEmail, Address, AccountNumber) VALUES
-- Raw Material Vendors
('Metal Supermarkets', '555-0101', 'orders@metalsupermarkets.com', '123 Industrial Way, City, ST 12345', 'MS-001'),
('OnlineMetals.com', '555-0102', 'sales@onlinemetals.com', '456 Steel Drive, City, ST 12345', 'OM-001'),

-- Heat Treatment Vendors
('Advanced Heat Treat', '555-0201', 'processing@advancedheattreat.com', '789 Furnace Blvd, City, ST 12345', 'AHT-001'),
('Thermal Processing Inc', '555-0202', 'info@thermalprocessing.com', '321 Heat Lane, City, ST 12345', 'TPI-001'),

-- Plating Vendors
('Quality Plating Services', '555-0301', 'quotes@qualityplating.com', '654 Chrome Street, City, ST 12345', 'QPS-001'),
('DFL Finishing', '555-0302', 'contact@dflfinishing.com', '987 Finish Ave, City, ST 12345', 'DFL-001'),
('Zinc Solutions', '555-0303', 'sales@zincsolutions.com', '147 Coating Road, City, ST 12345', 'ZS-001'),

-- Grinding Vendors
('Precision Grinding Co', '555-0401', 'service@precisiongrinding.com', '258 Grind Place, City, ST 12345', 'PGC-001'),
('Surface Solutions', '555-0402', 'info@surfacesolutions.com', '369 Polish Drive, City, ST 12345', 'SS-001'),

-- Machining Vendors
('ABC Machine Shop', '555-0501', 'shop@abcmachine.com', '741 Lathe Lane, City, ST 12345', 'ABC-001'),
('XYZ Precision Machining', '555-0502', 'quotes@xyzprecision.com', '852 Mill Street, City, ST 12345', 'XYZ-001');

-- =============================================
-- 3. PARTS - Sample parts from Shibaura
-- =============================================
-- IMPORTING FROM CSV
-- =============================================
-- 4. CUSTOMER PURCHASE ORDERS - Sample PO from Shibaura
-- =============================================

INSERT INTO CustomerPurchaseOrders (PO_Number, CustomerID, Order_Date, Total_Value, Status) VALUES
('43230', (SELECT CustomerID FROM Customers WHERE CustomerName = 'Shibaura'), '2018-05-16', 310.00, 'Completed'),
('98408', (SELECT CustomerID FROM Customers WHERE CustomerName = 'Shibaura'), '2021-10-06', 4725.00, 'Completed'),
('NAVY-2025-001', (SELECT CustomerID FROM Customers WHERE CustomerName = 'US Navy'), '2025-01-15', 15000.00, 'Open');

-- =============================================
-- 5. CUSTOMER PO LINE ITEMS - Line items for sample POs
-- =============================================

INSERT INTO CustomerPOLineItems (PO_ID, Line_Number, Part_Number, Description, Quantity, Unit_Price, Extended_Price, Due_Date, Status) VALUES
-- PO 43230
((SELECT PO_ID FROM CustomerPurchaseOrders WHERE PO_Number = '43230'), 1, '438S5707', '438S5707 [SPACER FOR PLUNGER UNIT]', 1, 310.00, 310.00, '2018-06-13', 'Completed'),

-- PO 98408
((SELECT PO_ID FROM CustomerPurchaseOrders WHERE PO_Number = '98408'), 1, '9W331301', '9W331301 [COVER FOR DC500J-MS]', 1, 325.00, 325.00, '2021-11-10', 'Completed'),
((SELECT PO_ID FROM CustomerPurchaseOrders WHERE PO_Number = '98408'), 2, '9W331104', '9W331104 [GUIDE SHAFT DBS500~800MS]', 2, 2200.00, 4400.00, '2021-11-10', 'Completed'),

-- PO NAVY-2025-001 (Current/Open order)
((SELECT PO_ID FROM CustomerPurchaseOrders WHERE PO_Number = 'NAVY-2025-001'), 1, 'Y132076', 'ELECTRODE PROBE CHROME', 50, 65.00, 3250.00, '2025-03-15', 'In Production'),
((SELECT PO_ID FROM CustomerPurchaseOrders WHERE PO_Number = 'NAVY-2025-001'), 2, 'N054085', 'PISTON HEAD', 25, 1150.00, 28750.00, '2025-03-30', 'Pending'),
((SELECT PO_ID FROM CustomerPurchaseOrders WHERE PO_Number = 'NAVY-2025-001'), 3, 'H319551', 'SEAT C2G16', 40, 2365.00, 94600.00, '2025-04-15', 'Pending');

-- =============================================
-- 6. WORK ORDERS - Sample work orders
-- =============================================

INSERT INTO WorkOrders (CustomerID, PartID, CustomerPONumber, QuantityOrdered, QuantityCompleted, StartDate, DueDate, Status, Priority, Notes) VALUES
-- Completed historical work order
(
    (SELECT CustomerID FROM Customers WHERE CustomerName = 'Shibaura'),
    (SELECT PartID FROM Parts WHERE PartNumber = '438S5707'),
    '43230',
    1,
    1,
    '2018-05-20',
    '2018-06-13',
    'Completed',
    'Normal',
    'Historical order from 2018'
),

-- Active work order for Navy
(
    (SELECT CustomerID FROM Customers WHERE CustomerName = 'US Navy'),
    (SELECT PartID FROM Parts WHERE PartNumber = 'Y132076'),
    'NAVY-2025-001',
    50,
    0,
    '2025-01-20',
    '2025-03-15',
    'On Machine',
    'High',
    'Navy contract - Chrome plating required'
),

-- Pending work order for Navy
(
    (SELECT CustomerID FROM Customers WHERE CustomerName = 'US Navy'),
    (SELECT PartID FROM Parts WHERE PartNumber = 'N054085'),
    'NAVY-2025-001',
    25,
    0,
    '2025-02-01',
    '2025-03-30',
    'Pending Material',
    'High',
    'Navy contract - Waiting for 4140 steel stock'
);

-- =============================================
-- 7. BOM - Bill of Materials for work orders
-- =============================================

INSERT INTO BOM (WorkOrderID, BOMVersion, CreatedBy, IsActive, Notes) VALUES
-- BOM for completed Shibaura work order
(1, '1.0', 'System', TRUE, 'Historical BOM from 2018'),

-- BOM for active Navy electrode probe order
(2, '1.0', 'Engineering', TRUE, 'Requires chrome plating - military spec'),

-- BOM for pending Navy piston head order
(3, '1.0', 'Engineering', TRUE, 'Heat treatment required');

-- =============================================
-- 8. BOM PROCESSES - Individual processes for each BOM
-- =============================================

INSERT INTO BOMProcesses (BOMID, ProcessType, ProcessName, VendorID, Quantity, UnitOfMeasure, EstimatedCost, LeadTimeDays, CertificationRequired, ProcessRequirements, Status) VALUES
-- BOM 1: Simple completed part (438S5707 - Spacer)
(1, 'Raw Material', '4140 Steel Round Bar',
    (SELECT VendorID FROM Vendors WHERE VendorName = 'Metal Supermarkets'),
    1, 'EA', 25.00, 3, FALSE, '1" diameter x 3" length', 'Completed'),
(1, 'Machining', 'CNC Turning',
    NULL,  -- Internal process
    1, 'EA', 150.00, 5, FALSE, 'Turn to print, 0.001" tolerance', 'Completed'),
(1, 'Inspection', 'Final Inspection',
    NULL,  -- Internal process
    1, 'EA', 35.00, 1, FALSE, 'CMM inspection per drawing', 'Completed'),

-- BOM 2: Navy electrode probe (Y132076) - Active
(2, 'Raw Material', '303 Stainless Steel Bar',
    (SELECT VendorID FROM Vendors WHERE VendorName = 'OnlineMetals.com'),
    50, 'EA', 15.00, 5, TRUE, '0.375" diameter x 2" length, Cert required', 'Completed'),
(2, 'Machining', 'CNC Turning & Threading',
    NULL,  -- Internal process
    50, 'EA', 35.00, 10, FALSE, 'Turn to 0.0005", thread 1/4-20 UNF', 'In Progress'),
(2, 'Plating', 'Chrome Plating',
    (SELECT VendorID FROM Vendors WHERE VendorName = 'Quality Plating Services'),
    50, 'EA', 12.00, 7, TRUE, 'MIL-C-14538 Class 1, 0.0002" min thickness', 'Pending'),
(2, 'Inspection', 'Final Inspection & Testing',
    NULL,  -- Internal process
    50, 'EA', 8.00, 2, TRUE, 'Electrical conductivity test, visual inspection', 'Pending'),

-- BOM 3: Navy piston head (N054085) - Pending material
(3, 'Raw Material', '4140 Steel Round Bar',
    (SELECT VendorID FROM Vendors WHERE VendorName = 'Metal Supermarkets'),
    25, 'EA', 45.00, 7, TRUE, '3" diameter x 4" length, Cert required', 'Pending'),
(3, 'Machining', 'CNC Turning & Milling',
    NULL,  -- Internal process
    25, 'EA', 250.00, 15, FALSE, 'Rough turn, semi-finish before HT', 'Pending'),
(3, 'Heat Treatment', 'Harden & Temper',
    (SELECT VendorID FROM Vendors WHERE VendorName = 'Advanced Heat Treat'),
    25, 'EA', 85.00, 10, TRUE, 'Harden to 28-32 HRC, temper, cert required', 'Pending'),
(3, 'Machining', 'Final Machining',
    NULL,  -- Internal process
    25, 'EA', 350.00, 12, FALSE, 'Finish grind, tight tolerances 0.0002"', 'Pending'),
(3, 'Grinding', 'Precision Grinding',
    (SELECT VendorID FROM Vendors WHERE VendorName = 'Precision Grinding Co'),
    25, 'EA', 125.00, 7, FALSE, 'Surface finish 16 RMS or better', 'Pending'),
(3, 'Inspection', 'CMM Inspection & Testing',
    NULL,  -- Internal process
    25, 'EA', 65.00, 3, TRUE, 'Full dimensional inspection, hardness test', 'Pending');

-- =============================================
-- 9. PURCHASE ORDERS LOG - Sample generated POs
-- =============================================

INSERT INTO PurchaseOrdersLog (
    PONumber, WorkOrderID, ProcessID, VendorID, PODate, ExpectedDeliveryDate,
    PartNumber, PartName, Material, Quantity, UnitPrice, TotalAmount,
    CertificationRequired, ProcessRequirements, Status, CreatedBy
) VALUES
-- PO for 303 Stainless for Navy electrode probes
(
    'PO-2025-001',
    2,
    (SELECT ProcessID FROM BOMProcesses WHERE BOMID = 2 AND ProcessType = 'Raw Material'),
    (SELECT VendorID FROM Vendors WHERE VendorName = 'OnlineMetals.com'),
    '2025-01-18',
    '2025-01-25',
    'Y132076',
    'ELECTRODE PROBE CHROME',
    '303 Stainless Steel',
    50,
    15.00,
    750.00,
    TRUE,
    '0.375" diameter x 2" length, Material Cert required',
    'Received',
    'System'
),

-- PO for chrome plating (pending)
(
    'PO-2025-002',
    2,
    (SELECT ProcessID FROM BOMProcesses WHERE BOMID = 2 AND ProcessType = 'Plating'),
    (SELECT VendorID FROM Vendors WHERE VendorName = 'Quality Plating Services'),
    '2025-02-01',
    '2025-02-10',
    'Y132076',
    'ELECTRODE PROBE CHROME',
    NULL,
    50,
    12.00,
    600.00,
    TRUE,
    'MIL-C-14538 Class 1, Chrome plating 0.0002" min thickness',
    'Created',
    'System'
);

-- =============================================
-- 10. CERTIFICATES LOG - Sample COC
-- =============================================

INSERT INTO CertificatesLog (
    CertificateNumber, WorkOrderID, CustomerID, PartNumber, Description,
    CustomerPONumber, Quantity, CompletionDate,
    ApprovedBy, ApproverTitle, CreatedBy
) VALUES
(
    'COC-2018-001',
    1,
    (SELECT CustomerID FROM Customers WHERE CustomerName = 'Shibaura'),
    '438S5707',
    'SPACER FOR PLUNGER UNIT',
    '43230',
    1,
    '2018-06-10',
    'DWG-438S5707',
    'Beniamin Grama',
    'Quality Assurance Manager',
    'System'
);

-- =============================================
-- 11. WORK ORDER STATUS HISTORY - Track status changes
-- =============================================

INSERT INTO WorkOrderStatusHistory (WorkOrderID, PreviousStatus, NewStatus, ChangedBy, Notes) VALUES
-- History for completed work order
(1, NULL, 'Pending Material', 'System', 'Work order created'),
(1, 'Pending Material', 'On Machine', 'Production', 'Material received, started machining'),
(1, 'On Machine', 'Quality Control', 'Production', 'Machining complete'),
(1, 'Quality Control', 'Completed', 'QA', 'Inspection passed'),
(1, 'Completed', 'Shipped', 'Shipping', 'Shipped to customer'),

-- History for active Navy work order
(2, NULL, 'Pending Material', 'System', 'Work order created'),
(2, 'Pending Material', 'On Machine', 'Production', 'Material received, machining in progress');

-- =============================================
-- 12. PRODUCTION STAGES - Track quantities
-- =============================================

INSERT INTO ProductionStages (WorkOrderID, StageName, QuantityIn, QuantityOut, QuantityLoss, StageDate, Notes) VALUES
-- Completed work order stages
(1, 'Raw Material Receipt', 1, 1, 0, '2018-05-20', 'Material received and inspected'),
(1, 'CNC Turning', 1, 1, 0, '2018-05-25', 'Turning operation complete'),
(1, 'Final Inspection', 1, 1, 0, '2018-06-08', 'Passed inspection'),

-- Active Navy work order stages
(2, 'Raw Material Receipt', 50, 50, 0, '2025-01-25', 'Material received with certs'),
(2, 'CNC Turning Setup', 50, 48, 2, '2025-01-28', 'Started machining, 2 scrapped in setup'),
(2, 'CNC Turning In Progress', 48, 45, 3, '2025-02-05', 'Machining ongoing, 3 additional scrap');

-- =============================================
-- DATA LOAD COMPLETE
-- =============================================

-- Verify data load
SELECT 'Customers' as TableName, COUNT(*) as RecordCount FROM Customers
UNION ALL
SELECT 'Vendors', COUNT(*) FROM Vendors
UNION ALL
SELECT 'Parts', COUNT(*) FROM Parts
UNION ALL
SELECT 'CustomerPurchaseOrders', COUNT(*) FROM CustomerPurchaseOrders
UNION ALL
SELECT 'CustomerPOLineItems', COUNT(*) FROM CustomerPOLineItems
UNION ALL
SELECT 'WorkOrders', COUNT(*) FROM WorkOrders
UNION ALL
SELECT 'BOM', COUNT(*) FROM BOM
UNION ALL
SELECT 'BOMProcesses', COUNT(*) FROM BOMProcesses
UNION ALL
SELECT 'PurchaseOrdersLog', COUNT(*) FROM PurchaseOrdersLog
UNION ALL
SELECT 'CertificatesLog', COUNT(*) FROM CertificatesLog
UNION ALL
SELECT 'WorkOrderStatusHistory', COUNT(*) FROM WorkOrderStatusHistory
UNION ALL
SELECT 'ProductionStages', COUNT(*) FROM ProductionStages;
