-- =============================================
-- Migration: Fix Work Order Schema Issues
-- Date: 2025-01-22
-- Purpose: Add missing columns and fix foreign key relationships
-- =============================================

USE amcmrp;

-- =============================================
-- STEP 1: Add WorkOrderNumber Column
-- =============================================
-- Add human-readable work order number
ALTER TABLE WorkOrders
ADD COLUMN WorkOrderNumber VARCHAR(50) UNIQUE AFTER WorkOrderID;

-- Backfill WorkOrderNumber for existing records
UPDATE WorkOrders
SET WorkOrderNumber = CONCAT('WO-', LPAD(WorkOrderID, 5, '0'))
WHERE WorkOrderNumber IS NULL;

-- Make it NOT NULL after backfill
ALTER TABLE WorkOrders
MODIFY COLUMN WorkOrderNumber VARCHAR(50) NOT NULL UNIQUE;

-- Add index for fast lookups
CREATE INDEX idx_work_order_number ON WorkOrders(WorkOrderNumber);

-- =============================================
-- STEP 2: Add QuantityOrdered Column
-- =============================================
-- Work orders need their own quantity, independent of PO line items
ALTER TABLE WorkOrders
ADD COLUMN QuantityOrdered INT NOT NULL DEFAULT 1 AFTER PartID;

-- Backfill QuantityOrdered from CustomerPOLineItems where linked
UPDATE WorkOrders wo
LEFT JOIN CustomerPOLineItems li ON wo.CustomerPOLineItemID = li.LineItem_ID
SET wo.QuantityOrdered = COALESCE(li.Quantity, 1)
WHERE wo.QuantityOrdered = 1; -- Only update defaults

-- =============================================
-- STEP 3: Add CustomerPOID Column
-- =============================================
-- Direct reference to Customer PO header for easier queries
ALTER TABLE WorkOrders
ADD COLUMN CustomerPOID INT AFTER CustomerPOLineItemID,
ADD FOREIGN KEY fk_workorder_customer_po (CustomerPOID)
    REFERENCES CustomerPurchaseOrders(PO_ID) ON DELETE SET NULL;

-- Backfill CustomerPOID from CustomerPOLineItems
UPDATE WorkOrders wo
INNER JOIN CustomerPOLineItems li ON wo.CustomerPOLineItemID = li.LineItem_ID
SET wo.CustomerPOID = li.PO_ID;

-- Add index
CREATE INDEX idx_customer_po ON WorkOrders(CustomerPOID);

-- =============================================
-- STEP 4: Add PartID to CustomerPOLineItems
-- =============================================
-- Link line items to Parts table for referential integrity
ALTER TABLE CustomerPOLineItems
ADD COLUMN PartID INT AFTER Line_Number;

-- Backfill PartID by matching Part_Number to Parts.PartNumber
UPDATE CustomerPOLineItems li
INNER JOIN Parts p ON li.Part_Number = p.PartNumber
SET li.PartID = p.PartID;

-- Add foreign key constraint
ALTER TABLE CustomerPOLineItems
ADD CONSTRAINT fk_lineitem_part
FOREIGN KEY (PartID) REFERENCES Parts(PartID);

-- Add index
CREATE INDEX idx_lineitem_part ON CustomerPOLineItems(PartID);

-- =============================================
-- STEP 5: Update Trigger for WorkOrderNumber Auto-Generation
-- =============================================
DROP TRIGGER IF EXISTS trg_generate_work_order_number;

DELIMITER //
CREATE TRIGGER trg_generate_work_order_number
BEFORE INSERT ON WorkOrders
FOR EACH ROW
BEGIN
    DECLARE next_id INT;

    -- Only generate if WorkOrderNumber is NULL
    IF NEW.WorkOrderNumber IS NULL OR NEW.WorkOrderNumber = '' THEN
        -- Get the next AUTO_INCREMENT value
        SELECT AUTO_INCREMENT INTO next_id
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = 'amcmrp' AND TABLE_NAME = 'WorkOrders';

        -- Generate WorkOrderNumber
        SET NEW.WorkOrderNumber = CONCAT('WO-', LPAD(COALESCE(NEW.WorkOrderID, next_id), 5, '0'));
    END IF;

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
        WHERE LineItem_ID = NEW.CustomerPOLineItemID;
    END IF;
END//
DELIMITER ;

-- =============================================
-- STEP 6: Update Views to Include New Fields
-- =============================================

-- Drop and recreate vw_WorkOrderSummary with new fields
DROP VIEW IF EXISTS vw_WorkOrderSummary;

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

-- Update vw_CustomerPODetails to include PartID
DROP VIEW IF EXISTS vw_CustomerPODetails;

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
-- STEP 7: Add Validation Constraints
-- =============================================

-- Ensure quantities are positive
ALTER TABLE WorkOrders
ADD CONSTRAINT chk_quantity_ordered_positive
    CHECK (QuantityOrdered > 0);

ALTER TABLE WorkOrders
ADD CONSTRAINT chk_quantity_completed_non_negative
    CHECK (QuantityCompleted >= 0);

ALTER TABLE CustomerPOLineItems
ADD CONSTRAINT chk_lineitem_quantity_positive
    CHECK (Quantity > 0);

-- =============================================
-- STEP 8: Add Comments for Documentation
-- =============================================

ALTER TABLE WorkOrders
MODIFY COLUMN WorkOrderNumber VARCHAR(50) NOT NULL UNIQUE
    COMMENT 'Human-readable work order number (e.g., WO-10001)';

ALTER TABLE WorkOrders
MODIFY COLUMN QuantityOrdered INT NOT NULL
    COMMENT 'Quantity ordered for this specific work order';

ALTER TABLE WorkOrders
MODIFY COLUMN CustomerPOID INT
    COMMENT 'Direct reference to Customer PO header (denormalized for performance)';

ALTER TABLE CustomerPOLineItems
MODIFY COLUMN PartID INT
    COMMENT 'Foreign key to Parts table for referential integrity';

-- =============================================
-- VERIFICATION QUERIES
-- =============================================

-- Verify all work orders have WorkOrderNumber
SELECT COUNT(*) as work_orders_without_number
FROM WorkOrders
WHERE WorkOrderNumber IS NULL OR WorkOrderNumber = '';

-- Verify all work orders have QuantityOrdered
SELECT COUNT(*) as work_orders_without_quantity
FROM WorkOrders
WHERE QuantityOrdered IS NULL OR QuantityOrdered <= 0;

-- Verify CustomerPOLineItems with PartID
SELECT
    COUNT(*) as total_line_items,
    SUM(CASE WHEN PartID IS NOT NULL THEN 1 ELSE 0 END) as line_items_with_part_id,
    SUM(CASE WHEN PartID IS NULL THEN 1 ELSE 0 END) as line_items_missing_part_id
FROM CustomerPOLineItems;

-- Show sample work order summary
SELECT * FROM vw_WorkOrderSummary LIMIT 5;

-- =============================================
-- ROLLBACK SCRIPT (Save separately if needed)
-- =============================================

/*
-- To rollback this migration:

ALTER TABLE WorkOrders DROP FOREIGN KEY fk_workorder_customer_po;
ALTER TABLE WorkOrders DROP COLUMN CustomerPOID;
ALTER TABLE WorkOrders DROP COLUMN QuantityOrdered;
ALTER TABLE WorkOrders DROP COLUMN WorkOrderNumber;

ALTER TABLE CustomerPOLineItems DROP FOREIGN KEY fk_lineitem_part;
ALTER TABLE CustomerPOLineItems DROP COLUMN PartID;

DROP TRIGGER IF EXISTS trg_generate_work_order_number;

-- Recreate original trigger
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

-- Recreate original views (see DDL.sql)
*/
