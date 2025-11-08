# Customer Purchase Orders Database

This document describes the Customer PO database tables and import functionality.

## Database Schema

### CustomerPurchaseOrders Table
Stores header-level information for customer purchase orders.

| Column | Type | Description |
|--------|------|-------------|
| PO_ID | INT | Primary key (auto-increment) |
| PO_Number | VARCHAR(50) | Unique PO number from customer |
| CustomerID | INT | Foreign key to Customers table |
| Order_Date | DATE | Date customer placed the order |
| Total_Value | DECIMAL(10,2) | Total value of entire PO |
| Status | ENUM | Status: Open, In Progress, Completed, Cancelled |
| Notes | TEXT | Optional notes about the PO |
| CreatedDate | TIMESTAMP | Record creation timestamp |
| UpdatedDate | TIMESTAMP | Last update timestamp |

### CustomerPOLineItems Table
Stores individual line items (parts) for each customer PO.

| Column | Type | Description |
|--------|------|-------------|
| LineItem_ID | INT | Primary key (auto-increment) |
| PO_ID | INT | Foreign key to CustomerPurchaseOrders |
| Line_Number | INT | Line number on the PO |
| Part_Number | VARCHAR(100) | Part number being ordered |
| Description | VARCHAR(500) | Part description |
| Quantity | INT | Quantity ordered |
| Unit_Price | DECIMAL(10,2) | Price per unit |
| Extended_Price | DECIMAL(10,2) | Total line price (Qty × Unit Price) |
| Due_Date | DATE | Due date for this line item |
| Status | ENUM | Status: Pending, In Production, Completed, Shipped |
| Notes | TEXT | Optional notes about the line item |
| CreatedDate | TIMESTAMP | Record creation timestamp |
| UpdatedDate | TIMESTAMP | Last update timestamp |

### vw_CustomerPODetails View
A convenient view that joins CustomerPurchaseOrders, CustomerPOLineItems, and Customers tables.

```sql
SELECT * FROM vw_CustomerPODetails WHERE PO_Number = '43230';
```

Returns all information about a PO including customer name and all line items.

## Database Structure Benefits

### Normalization
- **No data repetition**: PO header info (order date, total) stored once per PO
- **Easy updates**: Changing a PO order date requires updating only one record
- **Data integrity**: Foreign key constraints ensure referential integrity

### Scalability
- Can easily add PO-level shipping addresses, terms, or notes
- Can track line item status independently
- Can aggregate costs and quantities easily

## Importing Shibaura PO Data

### Prerequisites
1. Database must be running (via docker-compose or standalone)
2. DDL.sql must have been executed to create tables
3. Python 3.x with mysql-connector-python installed

### Running the Import Script

```bash
# From the database directory
cd /home/user/amc-mrp/database

# Run the import script
python3 import_shibaura_pos.py
```

### Import Process

The script will:
1. Read `DevAssets/Shibaura_POs.csv`
2. Parse and organize data by PO number
3. Create/find the 'Shibaura' customer in the database
4. Import unique POs (skips duplicates)
5. Import all line items for each PO
6. Set status to 'Completed' since these are historical orders

### Database Configuration

The script uses these environment variables (with defaults):
- `DB_HOST` (default: localhost)
- `DB_NAME` (default: amcmrp)
- `DB_USER` (default: amc)
- `DB_PASSWORD` (default: Workbench.lavender.chrome)
- `DB_PORT` (default: 3306)

When running in Docker, the database is accessible at:
- Host: localhost
- Port: 3307 (mapped from container's 3306)
- User: amc
- Password: Workbench.lavender.chrome
- Database: amcmrp

To run import from outside Docker:
```bash
DB_PORT=3307 python3 import_shibaura_pos.py
```

## Example Queries

### Get all POs for a customer
```sql
SELECT
    PO_Number,
    Order_Date,
    Total_Value,
    Status
FROM CustomerPurchaseOrders
WHERE CustomerID = (SELECT CustomerID FROM Customers WHERE CustomerName = 'Shibaura')
ORDER BY Order_Date DESC;
```

### Get line items for a specific PO
```sql
SELECT
    Line_Number,
    Part_Number,
    Description,
    Quantity,
    Unit_Price,
    Extended_Price,
    Due_Date,
    Status
FROM CustomerPOLineItems
WHERE PO_ID = (SELECT PO_ID FROM CustomerPurchaseOrders WHERE PO_Number = '43230')
ORDER BY Line_Number;
```

### Get all open/pending line items
```sql
SELECT
    cpo.PO_Number,
    li.Line_Number,
    li.Part_Number,
    li.Quantity,
    li.Due_Date,
    DATEDIFF(li.Due_Date, CURDATE()) as DaysUntilDue
FROM CustomerPOLineItems li
JOIN CustomerPurchaseOrders cpo ON li.PO_ID = cpo.PO_ID
WHERE li.Status IN ('Pending', 'In Production')
ORDER BY li.Due_Date;
```

### Calculate total value for a customer
```sql
SELECT
    c.CustomerName,
    COUNT(DISTINCT cpo.PO_ID) as Total_POs,
    COUNT(li.LineItem_ID) as Total_LineItems,
    SUM(li.Extended_Price) as Total_Value
FROM Customers c
LEFT JOIN CustomerPurchaseOrders cpo ON c.CustomerID = cpo.CustomerID
LEFT JOIN CustomerPOLineItems li ON cpo.PO_ID = li.PO_ID
WHERE c.CustomerName = 'Shibaura'
GROUP BY c.CustomerID;
```

### Find parts ordered most frequently
```sql
SELECT
    Part_Number,
    COUNT(*) as Times_Ordered,
    SUM(Quantity) as Total_Quantity,
    AVG(Unit_Price) as Avg_Unit_Price
FROM CustomerPOLineItems
GROUP BY Part_Number
ORDER BY Times_Ordered DESC
LIMIT 10;
```

## Integration with Work Orders

The CustomerPurchaseOrders system is separate from the WorkOrders table but can be linked:

### Option 1: Link via Customer PO Number
The WorkOrders table has a `CustomerPONumber` field that can reference `CustomerPurchaseOrders.PO_Number`.

### Option 2: Create work orders from customer PO line items
```sql
-- Example: Create work order from customer PO line item
INSERT INTO WorkOrders (
    CustomerID,
    PartID,
    CustomerPONumber,
    QuantityOrdered,
    DueDate,
    Status
)
SELECT
    cpo.CustomerID,
    (SELECT PartID FROM Parts WHERE PartNumber = li.Part_Number),
    cpo.PO_Number,
    li.Quantity,
    li.Due_Date,
    'Pending Material'
FROM CustomerPOLineItems li
JOIN CustomerPurchaseOrders cpo ON li.PO_ID = cpo.PO_ID
WHERE li.LineItem_ID = ?;  -- Specific line item to convert
```

## Maintenance

### Checking for missing parts
```sql
-- Find parts in customer POs that don't exist in Parts table
SELECT DISTINCT
    li.Part_Number,
    COUNT(*) as Times_Ordered
FROM CustomerPOLineItems li
LEFT JOIN Parts p ON li.Part_Number = p.PartNumber
WHERE p.PartID IS NULL
GROUP BY li.Part_Number
ORDER BY Times_Ordered DESC;
```

### Data validation
```sql
-- Verify line item totals match extended prices
SELECT
    PO_Number,
    Line_Number,
    Part_Number,
    Quantity,
    Unit_Price,
    Extended_Price,
    (Quantity * Unit_Price) as Calculated_Price,
    ABS(Extended_Price - (Quantity * Unit_Price)) as Difference
FROM vw_CustomerPODetails
WHERE ABS(Extended_Price - (Quantity * Unit_Price)) > 0.01
ORDER BY Difference DESC;
```
