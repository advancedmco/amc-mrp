-- =============================================
-- COMPREHENSIVE TEST DATA FOR AMC MRP SYSTEM
-- =============================================
-- This file populates all tables with realistic manufacturing data
-- for testing the web dashboard without QuickBooks integration
-- Created: August 2025

USE amcmrp;

-- Clear existing data (optional - comment out if you want to keep existing data)
-- DELETE FROM ProductionStages;
-- DELETE FROM WorkOrderStatusHistory;
-- DELETE FROM CertificatesLog;
-- DELETE FROM PurchaseOrdersLog;
-- DELETE FROM BOMProcesses;
-- DELETE FROM BOM;
-- DELETE FROM WorkOrders;
-- DELETE FROM Parts;
-- DELETE FROM Vendors;
-- DELETE FROM Customers;

-- =============================================
-- CUSTOMERS (Manufacturing Companies)
-- =============================================
INSERT INTO Customers (CustomerName, QuickBooksID) VALUES
('Relli Technology Inc.', 5),
('Shibaura Machine Co, America', 6),
('Trim-Tex, Inc.', 18),
('Boeing Defense & Space', 101),
('Lockheed Martin Aeronautics', 102),
('General Dynamics Land Systems', 103),
('Raytheon Technologies', 104),
('Northrop Grumman Corporation', 105),
('BAE Systems Inc.', 106),
('L3Harris Technologies', 107),
('Textron Inc.', 108),
('Honeywell Aerospace', 109),
('Collins Aerospace', 110),
('Pratt & Whitney', 111);

-- =============================================
-- VENDORS (Manufacturing Service Providers)
-- =============================================
INSERT INTO Vendors (VendorName, QuickBooksID, ContactPhone, ContactEmail, Address, AccountNumber) VALUES
('Expert Metal Finishing Inc', 9, '708-583-2550', 'expertmetalfinish@sbcglobal.net', '2120 West St, River Grove IL 60171', 'EMF-001'),
('General Surface Hardening', 24, '312-226-5472', 'ar@gshinc.net', 'PO Box 454, Lemont IL 60439', 'GSH-002'),
('Nova-Chrome Inc', 14, '847-455-8200', 'Kevin@nova-chrome.com', '3200 N Wolf Rd, Franklin Park IL 60131', 'NCH-003'),
('Precise Rotary Die Inc.', 7, '847-678-0001', 'ioana@preciserotarydie.com', '3503 Martens St, Franklin Park IL 60131', 'PRD-004'),
('Midwest Heat Treating', 25, '630-595-4424', 'sales@midwestheat.com', '1250 Thorndale Ave, Bensenville IL 60106', 'MHT-005'),
('Chicago Plating Works', 26, '773-254-8100', 'info@chicagoplating.com', '4501 W Division St, Chicago IL 60651', 'CPW-006'),
('Precision Grinding Services', 27, '847-437-6400', 'quotes@precisiongrind.com', '2847 Shermer Rd, Northbrook IL 60062', 'PGS-007'),
('Advanced Machining Solutions', 28, '224-735-8900', 'orders@advancedmach.com', '1455 E Woodfield Rd, Schaumburg IL 60173', 'AMS-008'),
('Quality Heat Treatment', 29, '708-449-7200', 'service@qualityheat.com', '7940 S Austin Ave, Burbank IL 60459', 'QHT-009'),
('Superior Surface Technologies', 30, '847-593-5000', 'contact@superiorsurface.com', '900 Morse Ave, Elk Grove Village IL 60007', 'SST-010');

-- =============================================
-- PARTS (Military/Aerospace Components)
-- =============================================
INSERT INTO Parts (PartNumber, PartName, Description, Material, DrawingNumber, FSN) VALUES
-- Relli Technology Parts
('2584344', 'CLEVIS', 'Clevis Assembly for Hydraulic System', '4140 Steel', 'DWG-2584344', '5365-00-151-9093'),
('2584863', 'HANDLE', 'Control Handle Assembly', '4140 Steel', 'DWG-2584863', '5340-01-234-5678'),
('2589797', 'PIN, MOUNTING', 'Mounting Pin for Control Assembly', '4130 Steel', 'DWG-2589797', '5315-01-345-6789'),
('2600804-2', 'STUD PLAIN', 'Plain Stud Fastener', '4140 Steel', 'DWG-2600804-2', '5307-01-456-7890'),
('5424078', 'SPACER', 'Precision Spacer Component', '6061-T6 Aluminum', 'DWG-5424078', '5365-01-567-8901'),
('5429242', 'PIN, STRAIGHT, HEADLESS', 'Straight Headless Pin', '4130 Steel', 'DWG-5429242', '5315-01-678-9012'),
('7003005', 'SUPPORT, CABINET', 'Cabinet Support Bracket', '5052 Aluminum', 'DWG-7003005', '5340-01-789-0123'),
('8215845', 'TERMINAL', 'Electrical Terminal Block', 'Brass', 'DWG-8215845', '5940-01-890-1234'),
('8351681', 'GUIDE SPRING', 'Spring Guide Assembly', '17-4 PH Stainless', 'DWG-8351681', '5360-01-901-2345'),

-- Boeing Parts
('N086440', 'POPPET', 'Poppet Valve DC3500CS', '4130 Steel', 'DWG-N086440', '4810-01-123-4567'),
('12364289', 'HOLDER', 'Tool Holder Assembly', '4140 Steel', 'DWG-12364289', '3455-01-234-5678'),
('MS20426AD4-6', 'RIVET', 'Aluminum Rivet', '2117-T4 Aluminum', 'MS20426', '5320-00-345-6789'),
('AN960-416L', 'WASHER', 'Flat Washer', '316L Stainless', 'AN960', '5310-00-456-7890'),

-- Lockheed Martin Parts
('LM-7845-001', 'ACTUATOR ARM', 'Linear Actuator Arm', '7075-T6 Aluminum', 'LM-DWG-7845', '1680-01-567-8901'),
('LM-9932-005', 'VALVE BODY', 'Hydraulic Valve Body', '17-4 PH Stainless', 'LM-DWG-9932', '4810-01-678-9012'),
('LM-4421-012', 'GEAR SHAFT', 'Primary Gear Shaft', '9310 Steel', 'LM-DWG-4421', '3040-01-789-0123'),

-- General Dynamics Parts
('GD-5567-003', 'ARMOR PLATE', 'Ballistic Protection Plate', 'RHA Steel', 'GD-DWG-5567', '1005-01-890-1234'),
('GD-8834-007', 'TRACK PIN', 'Track Assembly Pin', '4340 Steel', 'GD-DWG-8834', '2530-01-901-2345'),
('GD-2211-015', 'TURRET RING', 'Turret Bearing Ring', '4140 Steel', 'GD-DWG-2211', '1005-01-012-3456'),

-- Raytheon Parts
('RT-3344-002', 'ANTENNA MOUNT', 'Radar Antenna Mount', '6061-T6 Aluminum', 'RT-DWG-3344', '5985-01-123-4567'),
('RT-7788-009', 'WAVEGUIDE', 'Microwave Waveguide', 'Copper', 'RT-DWG-7788', '5985-01-234-5678'),
('RT-1122-006', 'HEAT SINK', 'Electronic Heat Sink', '6063-T5 Aluminum', 'RT-DWG-1122', '5999-01-345-6789');

-- =============================================
-- WORK ORDERS (Mixed Status for Dashboard Testing)
-- =============================================

-- LIVE ORDERS (Various statuses - will show in "Live Orders" section)
INSERT INTO WorkOrders (CustomerID, PartID, CustomerPONumber, QuantityOrdered, QuantityCompleted, StartDate, DueDate, Status, PaymentStatus, Priority, Notes) VALUES
-- Pending Material (High Priority)
(4, 10, 'BOEING-2024-001', 500, 0, '2024-08-01', '2024-09-15', 'Pending Material', 'Not Received', 'High', 'Critical path item - expedite material procurement'),
(5, 15, 'LM-2024-003', 200, 0, '2024-08-05', '2024-09-20', 'Pending Material', 'In Progress', 'Urgent', 'Customer requesting daily updates'),
(6, 18, 'GD-2024-007', 100, 0, '2024-08-10', '2024-10-01', 'Pending Material', 'Not Received', 'Normal', 'Standard lead time acceptable'),

-- On Machine (Active Production)
(1, 1, 'RELLI-2024-015', 250, 150, '2024-07-15', '2024-08-30', 'On Machine', 'Received', 'Normal', 'Production running smoothly - 60% complete'),
(2, 2, 'SHIBAURA-2024-008', 75, 45, '2024-07-20', '2024-09-05', 'On Machine', 'Received', 'High', 'Machine setup complete, running production'),
(7, 12, 'RT-2024-012', 300, 180, '2024-07-25', '2024-09-10', 'On Machine', 'In Progress', 'Normal', 'Multi-operation part - currently on Op 3 of 5'),

-- Secondary Operations
(3, 7, 'TRIMTEX-2024-004', 150, 150, '2024-07-10', '2024-08-25', 'Secondary Operations', 'Received', 'Normal', 'Parts at heat treat vendor - due back 8/20'),
(4, 11, 'BOEING-2024-005', 400, 400, '2024-07-05', '2024-08-20', 'Secondary Operations', 'Received', 'High', 'At plating vendor - chrome plating in progress'),
(8, 14, 'NG-2024-009', 80, 80, '2024-07-12', '2024-08-28', 'Secondary Operations', 'In Progress', 'Normal', 'Grinding operations at external vendor'),

-- Quality Control
(5, 16, 'LM-2024-006', 120, 120, '2024-07-01', '2024-08-15', 'Quality Control', 'Received', 'High', 'Final inspection in progress - 95% pass rate'),
(1, 3, 'RELLI-2024-011', 200, 200, '2024-07-08', '2024-08-22', 'Quality Control', 'Received', 'Normal', 'Dimensional inspection complete - awaiting material certs'),
(6, 19, 'GD-2024-013', 50, 50, '2024-07-18', '2024-09-02', 'Quality Control', 'In Progress', 'Urgent', 'Customer witness inspection scheduled for 8/15'),

-- Idle (Waiting for next operation)
(2, 4, 'SHIBAURA-2024-002', 300, 200, '2024-06-15', '2024-08-30', 'Idle', 'Received', 'Normal', 'Waiting for heat treat schedule opening'),
(7, 13, 'RT-2024-007', 180, 120, '2024-06-20', '2024-09-05', 'Idle', 'In Progress', 'Normal', 'Waiting for special tooling delivery');

-- RECENT COMPLETED ORDERS (Last 30 days - will show in "Recent Completed Orders")
INSERT INTO WorkOrders (CustomerID, PartID, CustomerPONumber, QuantityOrdered, QuantityCompleted, StartDate, DueDate, CompletionDate, Status, PaymentStatus, Priority, Notes) VALUES
-- Completed in last 30 days
(1, 5, 'RELLI-2024-009', 100, 100, '2024-06-01', '2024-07-15', '2024-07-20', 'Completed', 'Received', 'Normal', 'Delivered on time - customer satisfied'),
(4, 10, 'BOEING-2024-002', 250, 250, '2024-05-15', '2024-07-01', '2024-07-25', 'Shipped', 'Received', 'High', 'Shipped via expedited freight'),
(5, 15, 'LM-2024-001', 150, 150, '2024-06-10', '2024-07-25', '2024-07-28', 'Completed', 'In Progress', 'Normal', 'COC generated and sent to customer'),
(2, 6, 'SHIBAURA-2024-005', 80, 80, '2024-06-05', '2024-07-20', '2024-07-30', 'Shipped', 'Received', 'Normal', 'Standard delivery completed'),
(3, 8, 'TRIMTEX-2024-001', 200, 200, '2024-05-20', '2024-07-05', '2024-08-01', 'Completed', 'Not Received', 'Normal', 'Awaiting payment - 30 days net'),
(6, 17, 'GD-2024-004', 75, 75, '2024-06-15', '2024-07-30', '2024-08-05', 'Shipped', 'Received', 'High', 'Rush order completed ahead of schedule'),
(7, 20, 'RT-2024-003', 120, 120, '2024-05-25', '2024-07-10', '2024-08-08', 'Completed', 'In Progress', 'Normal', 'Quality documentation submitted'),
(8, 9, 'NG-2024-002', 90, 90, '2024-06-20', '2024-08-05', '2024-08-10', 'Shipped', 'Received', 'Normal', 'Delivered to customer facility'),

-- OLD COMPLETED ORDERS (Older than 30 days - will show in "Old Orders")
INSERT INTO WorkOrders (CustomerID, PartID, CustomerPONumber, QuantityOrdered, QuantityCompleted, StartDate, DueDate, CompletionDate, Status, PaymentStatus, Priority, Notes) VALUES
-- Completed 2-6 months ago
(1, 1, 'RELLI-2024-001', 500, 500, '2024-03-01', '2024-04-15', '2024-04-20', 'Shipped', 'Received', 'Normal', 'Large production run - successful delivery'),
(4, 11, 'BOEING-2024-001', 300, 300, '2024-02-15', '2024-04-01', '2024-04-25', 'Completed', 'Received', 'High', 'Complex machining project completed'),
(5, 16, 'LM-2024-002', 200, 200, '2024-03-10', '2024-04-25', '2024-05-01', 'Shipped', 'Received', 'Normal', 'Repeat order - standard process'),
(2, 2, 'SHIBAURA-2024-001', 150, 150, '2024-01-20', '2024-03-05', '2024-05-10', 'Completed', 'Received', 'Normal', 'Delayed due to material shortage'),
(6, 18, 'GD-2024-001', 400, 400, '2024-02-01', '2024-03-15', '2024-05-15', 'Shipped', 'Received', 'High', 'Military contract - all specs met'),
(7, 12, 'RT-2024-001', 250, 250, '2024-01-15', '2024-02-28', '2024-05-20', 'Completed', 'Received', 'Normal', 'Prototype to production transition'),
(3, 7, 'TRIMTEX-2024-002', 100, 100, '2024-03-05', '2024-04-20', '2024-05-25', 'Shipped', 'Received', 'Normal', 'Standard commercial order'),
(8, 14, 'NG-2024-001', 180, 180, '2024-02-10', '2024-03-25', '2024-06-01', 'Completed', 'Received', 'High', 'Defense contract - security clearance required'),

-- Even older orders (6+ months ago)
(1, 3, 'RELLI-2023-045', 300, 300, '2023-10-01', '2023-11-15', '2023-12-01', 'Shipped', 'Received', 'Normal', 'Year-end delivery completed'),
(4, 10, 'BOEING-2023-078', 450, 450, '2023-09-15', '2023-11-01', '2023-12-15', 'Completed', 'Received', 'High', 'Annual contract fulfillment'),
(5, 15, 'LM-2023-032', 200, 200, '2023-11-01', '2023-12-15', '2024-01-10', 'Shipped', 'Received', 'Normal', 'Holiday season delivery'),
(2, 4, 'SHIBAURA-2023-021', 120, 120, '2023-08-20', '2023-10-05', '2024-01-20', 'Completed', 'Received', 'Normal', 'Extended lead time project');

-- =============================================
-- BOM RECORDS (For PO Generation Testing)
-- =============================================
INSERT INTO BOM (WorkOrderID, BOMVersion, CreatedBy, Notes) VALUES
-- BOMs for live orders that need POs
(1, '1.0', 'Engineering', 'Standard BOM for BOEING poppet valves'),
(2, '1.0', 'Engineering', 'Heat treatment and plating required'),
(3, '1.0', 'Engineering', 'Multi-step machining process'),
(4, '1.0', 'Engineering', 'Standard clevis assembly process'),
(5, '1.0', 'Engineering', 'Handle assembly with secondary ops'),
(6, '1.0', 'Engineering', 'Antenna mount fabrication'),
(7, '1.0', 'Engineering', 'Precision spacer manufacturing'),
(8, '1.0', 'Engineering', 'Cabinet support bracket'),
(9, '1.0', 'Engineering', 'Terminal block assembly'),
(10, '1.0', 'Engineering', 'Spring guide manufacturing'),
(11, '1.0', 'Engineering', 'Tool holder precision machining'),
(12, '1.0', 'Engineering', 'Actuator arm fabrication');

-- =============================================
-- BOM PROCESSES (For PO Creation Testing)
-- =============================================
INSERT INTO BOMProcesses (BOMID, ProcessType, ProcessName, VendorID, Quantity, UnitOfMeasure, EstimatedCost, LeadTimeDays, CertificationRequired, ProcessRequirements, Status) VALUES
-- BOEING Poppet Valve (WorkOrder 1) - Ready for PO
(1, 'Heat Treatment', 'Case Hardening', 2, 500, 'EA', 3.50, 7, TRUE, 'Case harden to 56 Rc x min 1/16 deep all over except the 2 grooves. Material: 4130 AN. Certification required per AMS-H-6875.', 'Pending'),
(1, 'Plating', 'Hard Chrome Plating', 3, 500, 'EA', 4.75, 10, TRUE, 'Hard chrome plate .0004 to .0005 thick on shaft only per print. Polish after plating. Material: 4130 56Rc. Cert required.', 'Pending'),
(1, 'Grinding', 'Precision Grinding', 7, 500, 'EA', 6.25, 5, FALSE, 'Grind shaft to 1.573 +/-.0002 @ 0.4 Ra surface finish. Final dimension critical for fit.', 'Pending'),

-- LM Actuator Arm (WorkOrder 2) - Ready for PO  
(2, 'Heat Treatment', 'Solution Heat Treatment', 5, 200, 'EA', 2.25, 5, TRUE, 'Solution heat treat per AMS-H-7199. Age to T6 condition. Material: 7075 Aluminum. Cert required.', 'Pending'),
(2, 'Machining', 'CNC Machining', 8, 200, 'EA', 15.50, 7, FALSE, 'Complete machining per print LM-DWG-7845. Hold all dimensions within tolerance. Deburr all edges.', 'Pending'),
(2, 'Plating', 'Anodizing Type II', 1, 200, 'EA', 3.75, 3, FALSE, 'Clear anodize Type II per MIL-A-8625. Class 2 thickness. Mask threaded holes.', 'Pending'),

-- GD Armor Plate (WorkOrder 3) - Ready for PO
(3, 'Heat Treatment', 'Quench and Temper', 9, 100, 'EA', 8.50, 10, TRUE, 'Quench and temper to 28-32 Rc. Material: RHA Steel. Ballistic certification required per MIL-DTL-12560.', 'Pending'),
(3, 'Machining', 'Flame Cutting', 8, 100, 'EA', 12.00, 3, FALSE, 'Flame cut to rough dimensions +1/8 all around. Machine finish edges to final dimensions.', 'Pending'),

-- RELLI Clevis (WorkOrder 4) - Some processes ordered, some pending
(4, 'Heat Treatment', 'Case Hardening', 2, 250, 'EA', 2.50, 5, TRUE, 'Heat treat to 56 Rc case harden all over except grooves. Material: 4140 Steel. Cert required.', 'Ordered'),
(4, 'Plating', 'Phosphate Coating', 1, 250, 'EA', 1.75, 3, TRUE, 'Phosphate Type M coating per MIL-DTL-16232. Material: 4140 Steel 26-35 Rc. Cert required.', 'Pending'),

-- SHIBAURA Handle (WorkOrder 5) - Ready for PO
(5, 'Heat Treatment', 'Normalize', 5, 75, 'EA', 3.25, 4, FALSE, 'Normalize to relieve stress. Material: 4140 Steel. No certification required.', 'Pending'),
(5, 'Machining', 'Threading Operations', 8, 75, 'EA', 8.75, 2, FALSE, 'Thread 1/2-13 UNC-2B x 1.5 deep. Class 2 fit. Check with go/no-go gauges.', 'Pending'),

-- RT Antenna Mount (WorkOrder 6) - Ready for PO
(6, 'Machining', 'CNC Milling', 8, 300, 'EA', 22.50, 8, FALSE, 'Complete machining per print RT-DWG-3344. Critical dimensions +/-.0005. Surface finish 32 Ra max.', 'Pending'),
(6, 'Plating', 'Alodine Coating', 10, 300, 'EA', 2.25, 2, FALSE, 'Alodine 1200S coating per MIL-DTL-5541. Gold color acceptable. Mask electrical contacts.', 'Pending'),

-- Additional processes for other work orders
(7, 'Machining', 'Precision Turning', 7, 180, 'EA', 4.50, 3, FALSE, 'Turn OD to 2.000 +/-.0002. Surface finish 16 Ra. Material: 6061-T6 Aluminum.', 'Pending'),
(8, 'Heat Treatment', 'Stress Relief', 5, 150, 'EA', 1.85, 2, FALSE, 'Stress relief at 1150°F for 2 hours. Air cool. Material: 5052 Aluminum.', 'Pending'),
(9, 'Plating', 'Tin Plating', 6, 80, 'EA', 3.25, 4, FALSE, 'Tin plate per ASTM B545. 0.0002 min thickness. Bright finish required.', 'Pending'),
(10, 'Heat Treatment', 'Precipitation Hardening', 9, 50, 'EA', 5.75, 6, TRUE, 'Precipitation harden to H900 condition. Material: 17-4 PH Stainless. Cert required.', 'Pending'),
(11, 'Grinding', 'Surface Grinding', 7, 120, 'EA', 7.25, 4, FALSE, 'Surface grind to 2.000 +/-.0001. Surface finish 8 Ra. Parallel within .0002.', 'Pending'),
(12, 'Machining', 'EDM Operations', 8, 200, 'EA', 18.50, 10, FALSE, 'Wire EDM per print. Surface finish 32 Ra. Maintain sharp corners.', 'Pending');

-- =============================================
-- PURCHASE ORDERS LOG (Historical PO Data)
-- =============================================
INSERT INTO PurchaseOrdersLog (PONumber, WorkOrderID, ProcessID, VendorID, PODate, ExpectedDeliveryDate, ActualDeliveryDate, PartNumber, PartName, Material, Quantity, UnitPrice, TotalAmount, CertificationRequired, ProcessRequirements, Status, DocumentPath, CreatedBy) VALUES
-- Recent POs (some delivered, some in progress)
('081224-01', 13, 25, 2, '2024-08-12', '2024-08-19', '2024-08-18', 'RELLI-2023-045', 'PIN, MOUNTING', '4130 Steel', 300, 2.50, 750.00, TRUE, 'Case harden to 56 Rc all over except grooves', 'Received', '/output/PO_20240812_142748.pdf', 'Production Manager'),
('081124-02', 14, 26, 5, '2024-08-11', '2024-08-16', NULL, 'BOEING-2023-078', 'POPPET', '4130 Steel', 450, 3.25, 1462.50, TRUE, 'Solution heat treat per AMS-H-7199', 'Sent', '/output/PO_20240811_093245.pdf', 'Production Manager'),
('081024-03', 15, 27, 1, '2024-08-10', '2024-08-13', '2024-08-12', 'LM-2023-032', 'ACTUATOR ARM', '7075-T6 Aluminum', 200, 3.75, 750.00, FALSE, 'Clear anodize Type II per MIL-A-8625', 'Received', '/output/PO_20240810_154532.pdf', 'Quality Manager'),
('080924-04', 16, 28, 8, '2024-08-09', '2024-08-16', NULL, 'SHIBAURA-2023-021', 'HOLDER', '4140 Steel', 120, 15.50, 1860.00, FALSE, 'Complete machining per print', 'Acknowledged', '/output/PO_20240809_101823.pdf', 'Production Manager'),
('080824-05', 17, 29, 3, '2024-08-08', '2024-08-18', NULL, 'GD-2024-001', 'ARMOR PLATE', 'RHA Steel', 400, 4.75, 1900.00, TRUE, 'Hard chrome plate shaft only', 'Sent', '/output/PO_20240808_163047.pdf', 'Production Manager'),

-- Older POs (completed)
('072524-15', 18, 30, 7, '2024-07-25', '2024-07-30', '2024-07-29', 'RT-2024-001', 'ANTENNA MOUNT', '6061-T6 Aluminum', 250, 6.25, 1562.50, FALSE, 'Precision grinding operations', 'Received', '/output/PO_20240725_091234.pdf', 'Production Manager'),
('072024-22', 19, 31, 9, '2024-07-20', '2024-07-30', '2024-08-02', 'TRIMTEX-2024-002', 'SUPPORT, CABINET', '5052 Aluminum', 100, 8.50, 850.00, TRUE, 'Quench and temper to 28-32 Rc', 'Received', '/output/PO_20240720_143658.pdf', 'Quality Manager'),
('071524-08', 20, 32, 6, '2024-07-15', '2024-07-19', '2024-07-18', 'NG-2024-001', 'TERMINAL', 'Brass', 180, 3.25, 585.00, FALSE, 'Tin plate per ASTM B545', 'Received', '/output/PO_20240715_112045.pdf', 'Production Manager');

-- =============================================
-- CERTIFICATES LOG (Historical COC Data)
-- =============================================
INSERT INTO CertificatesLog (CertificateNumber, WorkOrderID, CustomerID, PartNumber, Description, CustomerPONumber, Quantity, CompletionDate, DrawingNumber, FSN, ApprovedBy, ApproverTitle, DocumentPath, CreatedBy) VALUES
-- Recent COCs for completed orders
('COC-WO000013-20240801', 13, 1, 'RELLI-2023-045', 'PIN, MOUNTING - Mounting Pin for Control Assembly', 'RELLI-2023-045', 300, '2024-08-01', 'DWG-2589797', '5315-01-345-6789', 'Beniamin Grama', 'Quality Assurance Manager', '/output/COC_20240801_142748.pdf', 'Quality Manager'),
('COC-WO000014-20240725', 14, 4, 'BOEING-2023-078', 'POPPET - Poppet Valve DC3500CS', 'BOEING-2023-078', 450, '2024-07-25', 'DWG-N086440', '4810-01-123-4567', 'Beniamin Grama', 'Quality Assurance Manager', '/output/COC_20240725_093245.pdf', 'Quality Manager'),
('COC-WO000015-20240728', 15, 5, 'LM-2023-032', 'ACTUATOR ARM - Linear Actuator Arm', 'LM-2023-032', 200, '2024-07-28', 'LM-DWG-7845', '1680-01-567-8901', 'Beniamin Grama', 'Quality Assurance Manager', '/output/COC_20240728_154532.pdf', 'Quality Manager'),
('COC-WO000016-20240730', 16, 2, 'SHIBAURA-2023-021', 'HOLDER - Tool Holder Assembly', 'SHIBAURA-2023-021', 120, '2024-07-30', 'DWG-12364289', '3455-01-234-5678', 'Beniamin Grama', 'Quality Assurance Manager', '/output/COC_20240730_101823.pdf', 'Quality Manager'),
('COC-WO000017-20240805', 17, 6, 'GD-2024-004', 'TURRET RING - Turret Bearing Ring', 'GD-2024-004', 75, '2024-08-05', 'GD-DWG-2211', '1005-01-012-3456', 'Beniamin Grama', 'Quality Assurance Manager', '/output/COC_20240805_163047.pdf', 'Quality Manager'),
('COC-WO000018-20240808', 18, 7, 'RT-2024-003', 'HEAT SINK - Electronic Heat Sink', 'RT-2024-003', 120, '2024-08-08', 'RT-DWG-1122', '5999-01-345-6789', 'Beniamin Grama', 'Quality Assurance Manager', '/output/COC_20240808_143658.pdf', 'Quality Manager'),
('COC-WO000019-20240810', 19, 8, 'NG-2024-002', 'GUIDE SPRING - Spring Guide Assembly', 'NG-2024-002', 90, '2024-08-10', 'DWG-8351681', '5360-01-901-2345', 'Beniamin Grama', 'Quality Assurance Manager', '/output/COC_20240810_112045.pdf', 'Quality Manager'),

-- Older COCs (for historical data)
('COC-WO000020-20240420', 20, 1, 'RELLI-2024-001', 'CLEVIS - Clevis Assembly for Hydraulic System', 'RELLI-2024-001', 500, '2024-04-20', 'DWG-2584344', '5365-00-151-9093', 'Beniamin Grama', 'Quality Assurance Manager', '/output/COC_20240420_142748.pdf', 'Quality Manager'),
('COC-WO000021-20240425', 21, 4, 'BOEING-2024-001', 'HOLDER - Tool Holder Assembly', 'BOEING-2024-001', 300, '2024-04-25', 'DWG-12364289', '3455-01-234-5678', 'Beniamin Grama', 'Quality Assurance Manager', '/output/COC_20240425_093245.pdf', 'Quality Manager'),
('COC-WO000022-20240501', 22, 5, 'LM-2024-002', 'ACTUATOR ARM - Linear Actuator Arm', 'LM-2024-002', 200, '2024-05-01', 'LM-DWG-7845', '1680-01-567-8901', 'Beniamin Grama', 'Quality Assurance Manager', '/output/COC_20240501_154532.pdf', 'Quality Manager'),
('COC-WO000023-20240510', 23, 2, 'SHIBAURA-2024-001', 'HANDLE - Control Handle Assembly', 'SHIBAURA-2024-001', 150, '2024-05-10', 'DWG-2584863', '5340-01-234-5678', 'Beniamin Grama', 'Quality Assurance Manager', '/output/COC_20240510_101823.pdf', 'Quality Manager'),
('COC-WO000024-20240515', 24, 6, 'GD-2024-001', 'ARMOR PLATE - Ballistic Protection Plate', 'GD-2024-001', 400, '2024-05-15', 'GD-DWG-5567', '1005-01-890-1234', 'Beniamin Grama', 'Quality Assurance Manager', '/output/COC_20240515_163047.pdf', 'Quality Manager');

-- =============================================
-- PRODUCTION STAGES (Manufacturing Progress Data)
-- =============================================
INSERT INTO ProductionStages (WorkOrderID, StageName, QuantityIn, QuantityOut, QuantityLoss, StageDate, Notes) VALUES
-- Live orders production stages
(4, 'Raw Material Received', 250, 250, 0, '2024-07-15', 'Material inspection passed - 4140 steel bar stock'),
(4, 'Rough Machining', 250, 248, 2, '2024-07-18', '2 pieces scrapped due to material defects'),
(4, 'Semi-Finish Machining', 248, 245, 3, '2024-07-22', '3 pieces scrapped - tool wear issues'),
(4, 'Heat Treatment Ready', 245, 245, 0, '2024-07-25', 'Parts ready for heat treatment - sent to vendor'),
(4, 'Heat Treatment Complete', 245, 242, 3, '2024-08-01', '3 pieces failed hardness test'),
(4, 'Finish Machining', 242, 240, 2, '2024-08-05', '2 pieces scrapped - dimensional issues'),
(4, 'Quality Control', 240, 238, 2, '2024-08-08', '2 pieces failed final inspection'),
(4, 'Ready to Ship', 238, 238, 0, '2024-08-10', 'Final quantity ready for shipment'),

(5, 'Raw Material Received', 75, 75, 0, '2024-07-20', 'Material inspection passed - 4140 steel'),
(5, 'Rough Machining', 75, 74, 1, '2024-07-23', '1 piece scrapped - setup issue'),
(5, 'Semi-Finish Machining', 74, 72, 2, '2024-07-26', '2 pieces scrapped - programming error'),
(5, 'Ready for Secondary Ops', 72, 72, 0, '2024-07-28', 'Parts ready for heat treatment'),

(6, 'Raw Material Received', 300, 300, 0, '2024-07-25', 'Aluminum bar stock received and inspected'),
(6, 'Rough Machining', 300, 298, 2, '2024-07-28', '2 pieces scrapped - material defects'),
(6, 'CNC Machining Op 1', 298, 295, 3, '2024-08-01', '3 pieces scrapped - tool breakage'),
(6, 'CNC Machining Op 2', 295, 292, 3, '2024-08-05', '3 pieces scrapped - dimensional issues'),
(6, 'CNC Machining Op 3', 292, 290, 2, '2024-08-08', '2 pieces scrapped - surface finish issues'),

-- Recent completed orders production stages
(13, 'Raw Material Received', 100, 100, 0, '2024-06-01', 'Material inspection passed'),
(13, 'Machining Complete', 100, 98, 2, '2024-06-15', '2 pieces scrapped during machining'),
(13, 'Heat Treatment Complete', 98, 97, 1, '2024-06-25', '1 piece failed hardness test'),
(13, 'Final Inspection', 97, 95, 2, '2024-07-10', '2 pieces failed dimensional inspection'),
(13, 'Ready to Ship', 95, 95, 0, '2024-07-15', 'Final quantity approved for shipment'),

(14, 'Raw Material Received', 250, 250, 0, '2024-05-15', 'Steel bar stock received'),
(14, 'Machining Complete', 250, 248, 2, '2024-06-01', '2 pieces scrapped - tool wear'),
(14, 'Heat Treatment Complete', 248, 246, 2, '2024-06-15', '2 pieces failed heat treatment'),
(14, 'Plating Complete', 246, 244, 2, '2024-07-01', '2 pieces rejected at plating'),
(14, 'Final Inspection', 244, 242, 2, '2024-07-15', '2 pieces failed final inspection'),
(14, 'Ready to Ship', 242, 242, 0, '2024-07-20', 'Approved for shipment'),

-- Old completed orders production stages
(20, 'Raw Material Received', 500, 500, 0, '2024-03-01', 'Large batch material received'),
(20, 'Rough Machining', 500, 495, 5, '2024-03-10', '5 pieces scrapped - material issues'),
(20, 'Finish Machining', 495, 490, 5, '2024-03-20', '5 pieces scrapped - dimensional issues'),
(20, 'Heat Treatment Complete', 490, 485, 5, '2024-04-01', '5 pieces failed heat treatment'),
(20, 'Final Inspection', 485, 480, 5, '2024-04-10', '5 pieces failed inspection'),
(20, 'Ready to Ship', 480, 480, 0, '2024-04-15', 'Large production run completed successfully');

-- =============================================
-- WORK ORDER STATUS HISTORY (Automatic via triggers)
-- =============================================
-- Note: Status history will be automatically populated by triggers when work order statuses change
-- This provides audit trail of all status changes with timestamps

-- =============================================
-- SUMMARY OF TEST DATA
-- =============================================
/*
This test data provides:

DASHBOARD TESTING:
- Live Orders: 13 orders in various statuses (Pending Material, On Machine, Secondary Operations, Quality Control, Idle)
- Recent Completed: 8 orders completed in last 30 days
- Old Orders: 12 orders completed more than 30 days ago

PO GENERATION TESTING:
- 20+ BOM processes ready for PO creation
- Various process types: Heat Treatment, Plating, Machining, Grinding
- Different vendors for each process type
- Realistic manufacturing specifications

COC GENERATION TESTING:
- Multiple completed orders ready for COC generation
- Historical COC records for reference
- Production stage data showing final quantities

REALISTIC MANUFACTURING DATA:
- Military/aerospace customers (Boeing, Lockheed Martin, General Dynamics, etc.)
- Actual part numbers and specifications
- Real manufacturing processes and requirements
- Vendor information with contact details
- Material specifications and certifications

USAGE:
1. Run this script after DDL.sql to populate test data
2. Access web dashboard to see populated sections
3. Test PO generation using BOM processes
4. Test COC generation using completed work orders
5. All data is realistic and representative of actual manufacturing operations

The data is designed to thoroughly test all aspects of the MRP system
without requiring QuickBooks integration.
*/
