# Base Initial Data for AMC MRP System

## Overview

The `base_initial_data.sql` file provides a minimal, complete dataset that satisfies all database foreign key constraints and provides a working baseline for the MRP system. This data is designed to:

1. **Satisfy all constraints** - Every foreign key relationship has valid data
2. **Provide realistic examples** - Uses actual part numbers and vendors from Shibaura operations
3. **Enable immediate testing** - System can be tested without importing additional data
4. **Demonstrate workflows** - Shows complete workflows from customer PO to completion

## Data Structure

### Dependency Chain

The data is inserted in order to satisfy foreign key constraints:

```
1. Customers (5 records)
   ↓
2. Vendors (11 records)
   ↓
3. Parts (10 records)
   ↓
4. CustomerPurchaseOrders (3 records)
   ├→ CustomerPOLineItems (6 records)
   └→ WorkOrders (3 records)
       ├→ BOM (3 records)
       │   └→ BOMProcesses (15 records)
       │       └→ PurchaseOrdersLog (2 records)
       ├→ CertificatesLog (1 record)
       ├→ WorkOrderStatusHistory (7 records)
       └→ ProductionStages (6 records)
```

## Included Data

### 1. Customers (5 records)
- **Shibaura** - Primary customer (historical and active orders)
- **US Navy** - Government customer with active order
- **US Army** - Available for future orders
- **General Dynamics** - Defense contractor
- **Northrop Grumman** - Defense contractor

### 2. Vendors (11 records)

**Raw Material Vendors:**
- Metal Supermarkets
- OnlineMetals.com

**Heat Treatment Vendors:**
- Advanced Heat Treat
- Thermal Processing Inc

**Plating Vendors:**
- Quality Plating Services (Chrome)
- DFL Finishing
- Zinc Solutions

**Grinding Vendors:**
- Precision Grinding Co
- Surface Solutions

**Machining Vendors:**
- ABC Machine Shop
- XYZ Precision Machining

### 3. Parts (10 records)

Sample parts from actual Shibaura catalog:
- 438S5707 - SPACER FOR PLUNGER UNIT
- 9W331301 - COVER FOR DC500J-MS
- 9W331104 - GUIDE SHAFT DBS500-800MS
- Y132076 - ELECTRODE PROBE CHROME
- S571163 - LINER FOR S-SHAFT
- 695T7002 - LEFT HAND SCREW ROD
- N054085 - PISTON HEAD
- H319551 - SEAT C2G16
- Y074129 - FLANGE FOR C2G16
- Y042138 - LINK C

### 4. Customer Purchase Orders (3 records)

**Completed Historical Orders:**
- **PO-43230** (Shibaura, 2018) - Single line item, completed
- **PO-98408** (Shibaura, 2021) - Two line items, completed

**Active Order:**
- **PO-NAVY-2025-001** (US Navy, 2025) - Three line items, in progress
  - Line 1: 50 electrode probes - In Production
  - Line 2: 25 piston heads - Pending
  - Line 3: 40 valve seats - Pending

### 5. Work Orders (3 records)

**WO #1 - Completed (Shibaura spacer)**
- Status: Completed → Shipped
- Demonstrates full workflow completion
- Has certificate of completion

**WO #2 - Active (Navy electrode probes)**
- Status: On Machine
- Demonstrates active production
- Material received, machining in progress
- Pending chrome plating

**WO #3 - Pending (Navy piston heads)**
- Status: Pending Material
- Demonstrates waiting for material
- Complex BOM with heat treatment

### 6. Bill of Materials (3 BOMs, 15 processes)

**BOM #1 - Simple Part (Spacer):**
1. Raw Material (4140 Steel)
2. CNC Machining (Internal)
3. Inspection (Internal)

**BOM #2 - Medium Complexity (Electrode Probe):**
1. Raw Material (303 Stainless with cert)
2. CNC Turning & Threading (Internal)
3. Chrome Plating (External - QPS)
4. Final Inspection (Internal with testing)

**BOM #3 - Complex Part (Piston Head):**
1. Raw Material (4140 Steel with cert)
2. Rough Machining (Internal)
3. Heat Treatment (External - AHT)
4. Final Machining (Internal)
5. Precision Grinding (External - PGC)
6. CMM Inspection (Internal with testing)

### 7. Purchase Orders Log (2 records)

- **PO-2025-001** - Raw material for electrode probes (Received)
- **PO-2025-002** - Chrome plating service (Created)

### 8. Certificates of Completion (1 record)

- **COC-2018-001** - Certificate for completed Shibaura spacer

### 9. Work Order Status History (7 records)

Tracks all status changes for work orders:
- WO #1: Complete lifecycle (Created → Shipped)
- WO #2: Partial lifecycle (Created → On Machine)

### 10. Production Stages (6 records)

Quantity tracking through production:
- WO #1: Material Receipt → Turning → Inspection (1 pc, no loss)
- WO #2: Material Receipt → Setup → In Progress (50 → 48 → 45, shows realistic scrap)

## Use Cases Demonstrated

### 1. Complete Historical Order
Work Order #1 shows a fully completed order:
- Customer PO received
- Work order created
- BOM defined
- Material ordered
- Parts manufactured
- Quality inspection
- Certificate issued
- Order shipped

### 2. Active Production Order
Work Order #2 shows an order in progress:
- Material received and verified
- Machining in progress
- Quantity tracking with scrap
- Pending external process (plating)
- Status history tracked

### 3. Pending Material Order
Work Order #3 shows an order waiting to start:
- Customer PO confirmed
- BOM created
- Material on order
- Complex multi-step process planned
- External processes identified

## Loading the Data

### Method 1: Manual Load (Recommended for Development)

```bash
# After running DDL.sql, load base data
mysql -h localhost -P 3307 -u amc -p'Workbench.lavender.chrome' amcmrp < base_initial_data.sql
```

### Method 2: Include in DDL

Add to the end of `DDL.sql`:
```sql
-- Load base initial data
SOURCE base_initial_data.sql;
```

### Method 3: Docker Container Init

Copy to `/docker-entrypoint-initdb.d/` in the database container for automatic loading.

## Validation Queries

### Verify All Tables Have Data
```sql
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
SELECT 'BOMProcesses', COUNT(*) FROM BOMProcesses;
```

### Check Foreign Key Integrity
```sql
-- Should return 0 orphaned records
SELECT COUNT(*) as OrphanedWorkOrders
FROM WorkOrders wo
LEFT JOIN Customers c ON wo.CustomerID = c.CustomerID
LEFT JOIN Parts p ON wo.PartID = p.PartID
WHERE c.CustomerID IS NULL OR p.PartID IS NULL;

SELECT COUNT(*) as OrphanedBOMProcesses
FROM BOMProcesses bp
LEFT JOIN BOM b ON bp.BOMID = b.BOMID
WHERE b.BOMID IS NULL;
```

### View Active Orders
```sql
SELECT
    wo.WorkOrderID,
    c.CustomerName,
    p.PartNumber,
    wo.QuantityOrdered,
    wo.Status,
    wo.DueDate
FROM WorkOrders wo
JOIN Customers c ON wo.CustomerID = c.CustomerID
JOIN Parts p ON wo.PartID = p.PartID
WHERE wo.Status NOT IN ('Completed', 'Shipped')
ORDER BY wo.DueDate;
```

### View BOM Costs
```sql
SELECT
    wo.WorkOrderID,
    p.PartNumber,
    bp.ProcessName,
    bp.ProcessType,
    v.VendorName,
    bp.EstimatedCost,
    bp.Status
FROM WorkOrders wo
JOIN Parts p ON wo.PartID = p.PartID
JOIN BOM b ON wo.WorkOrderID = b.WorkOrderID
JOIN BOMProcesses bp ON b.BOMID = bp.BOMID
LEFT JOIN Vendors v ON bp.VendorID = v.VendorID
WHERE wo.WorkOrderID = 2
ORDER BY bp.ProcessID;
```

## Extending the Base Data

### Adding More Customers
```sql
INSERT INTO Customers (CustomerName, QuickBooksID) VALUES
('Boeing', NULL),
('Lockheed Martin', NULL);
```

### Adding More Parts
```sql
INSERT INTO Parts (PartNumber, PartName, Description, Material) VALUES
('CUST-001', 'Custom Part Name', 'Part description', 'Material spec');
```

### Creating New Work Orders
```sql
INSERT INTO WorkOrders (CustomerID, PartID, CustomerPONumber, QuantityOrdered, DueDate, Status, Priority)
VALUES (
    (SELECT CustomerID FROM Customers WHERE CustomerName = 'US Army'),
    (SELECT PartID FROM Parts WHERE PartNumber = 'S571163'),
    'ARMY-2025-001',
    100,
    '2025-06-30',
    'Pending Material',
    'Normal'
);
```

## Best Practices

1. **Don't modify base data** - Treat this as read-only reference data
2. **Add your own data** - Create new records for your actual work
3. **Use the base data for testing** - Perfect for integration tests
4. **Reference the examples** - Use as templates for creating new records
5. **Maintain constraints** - Always ensure foreign keys are satisfied

## Notes

- All dates are realistic based on the workflow timelines
- Costs are estimated and should be updated with actuals
- QuickBooks IDs are NULL for fresh installations
- Vendor contact information is placeholder data
- Drawing numbers follow the pattern DWG-{PartNumber}
- Certificate approver is set to default QA manager
