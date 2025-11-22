# Database Schema Issues - Analysis and Fixes

## Critical Issues Found

### 1. **MISSING: WorkOrderNumber Column** ⚠️ CRITICAL
**Problem:**
- Frontend code extensively uses `WorkOrderNumber` field
- Schema only has `WorkOrderID` (auto-increment integer)
- No human-readable work order number exists

**Impact:**
- Frontend queries will fail when selecting `wo.WorkOrderNumber`
- Users need formatted work order numbers (e.g., "WO-10001")

**Fix:**
```sql
ALTER TABLE WorkOrders
ADD COLUMN WorkOrderNumber VARCHAR(50) UNIQUE AFTER WorkOrderID;

-- Generate work order numbers for existing records
UPDATE WorkOrders
SET WorkOrderNumber = CONCAT('WO-', LPAD(WorkOrderID, 5, '0'));
```

---

### 2. **MISSING: QuantityOrdered Column in WorkOrders** ⚠️ CRITICAL
**Problem:**
- WorkOrders table has `QuantityCompleted` but NO `QuantityOrdered`
- Frontend expects `wo.QuantityOrdered` in queries
- Current schema relies on joining to `CustomerPOLineItems.Quantity` via view

**Issue:**
- What if a work order is for a different quantity than the PO line item?
- What if multiple work orders are created for one large PO line item?
- Work orders should have their own quantity, independent of PO

**Fix:**
```sql
ALTER TABLE WorkOrders
ADD COLUMN QuantityOrdered INT NOT NULL DEFAULT 1 AFTER PartID;
```

---

### 3. **MISSING: Foreign Key from CustomerPOLineItems.Part_Number to Parts.PartID** ⚠️ HIGH
**Problem:**
- `CustomerPOLineItems` uses `Part_Number VARCHAR(100)` (string)
- No foreign key relationship to `Parts` table
- Allows data integrity issues (typos, orphaned part numbers)

**Issue:**
- Part_Number is stored as free text, not linked to Parts.PartID
- Can create parts that don't exist in Parts table
- No referential integrity

**Fix:**
```sql
-- Add PartID column
ALTER TABLE CustomerPOLineItems
ADD COLUMN PartID INT AFTER Line_Number,
ADD FOREIGN KEY (PartID) REFERENCES Parts(PartID);

-- Part_Number can remain for display/reference but should not be primary link
```

---

### 4. **MISSING: CustomerPOID Column in WorkOrders** ⚠️ MEDIUM
**Problem:**
- Frontend code tries to use `CustomerPOID` field
- WorkOrders only has `CustomerPOLineItemID`
- Need direct link to CustomerPurchaseOrders.PO_ID

**Current Schema:**
```
WorkOrders.CustomerPOLineItemID → CustomerPOLineItems.LineItem_ID
CustomerPOLineItems.PO_ID → CustomerPurchaseOrders.PO_ID
```

**Issue:**
- Requires JOIN through CustomerPOLineItems to get PO header info
- Frontend expects direct `CustomerPOID` reference

**Fix:**
```sql
-- Add CustomerPOID for direct reference to PO header
ALTER TABLE WorkOrders
ADD COLUMN CustomerPOID INT AFTER CustomerPOLineItemID,
ADD FOREIGN KEY (CustomerPOID) REFERENCES CustomerPurchaseOrders(PO_ID);
```

---

### 5. **Naming Inconsistency: Database vs Frontend** ⚠️ LOW-MEDIUM
**Problem:**
- Database uses: `PO_Number`, `PO_ID`, `LineItem_ID` (snake_case)
- Frontend expects: `PONumber`, `CustomerPONumber`, `WorkOrderNumber` (camelCase)
- View uses aliases but inconsistently

**Examples:**
- Schema: `cpo.PO_Number`
- View alias: `CustomerPONumber`
- Frontend: expects `CustomerPONumber`

**Fix:**
- Use consistent aliases in ALL views
- OR rename columns to match frontend expectations (breaking change)
- Recommended: Keep database in snake_case, ensure views always alias properly

---

### 6. **Logical Issue: WorkOrder → PO Relationship** ⚠️ MEDIUM
**Problem:**
- A WorkOrder should be based on ONE line item from a Customer PO
- Current schema has this: `CustomerPOLineItemID INT`
- BUT: It's nullable, and there's confusion about what fields to use

**Current Issues:**
- `CustomerPOLineItemID` is nullable - work orders might not link to PO
- Frontend tries to get `CustomerPONumber` separately instead of through the relationship
- `QuantityOrdered` should come from the work order itself, not the PO line item

**Proper Relationships:**
```
CustomerPurchaseOrders (PO Header)
  ├─ CustomerPOLineItems (Line items - many per PO)
       ├─ PartID → Parts.PartID
       ├─ Quantity (PO line item quantity)
       └─ WorkOrders (Many work orders can be created per line item)
            ├─ CustomerPOLineItemID → References the line item
            ├─ QuantityOrdered (Work order specific quantity)
            └─ PartID (Redundant but denormalized for performance)
```

---

### 7. **MISSING: Index on WorkOrders.WorkOrderNumber** ⚠️ LOW
**Problem:**
- Will add WorkOrderNumber column
- No index for lookups by work order number

**Fix:**
```sql
CREATE UNIQUE INDEX idx_work_order_number ON WorkOrders(WorkOrderNumber);
```

---

### 8. **MISSING: Default/Auto-generation for WorkOrderNumber** ⚠️ MEDIUM
**Problem:**
- When new work orders are created, WorkOrderNumber needs to be generated
- Should be automatic, not manual

**Fix:**
- Use BEFORE INSERT trigger to auto-generate WorkOrderNumber
- Format: `WO-{5-digit-padded-id}`

```sql
DELIMITER //
CREATE TRIGGER trg_generate_work_order_number
BEFORE INSERT ON WorkOrders
FOR EACH ROW
BEGIN
    IF NEW.WorkOrderNumber IS NULL THEN
        SET NEW.WorkOrderNumber = CONCAT('WO-', LPAD(NEW.WorkOrderID, 5, '0'));
    END IF;
END//
DELIMITER ;
```

---

## Summary of Required Changes

### Immediate (Critical):
1. ✅ Add `WorkOrderNumber VARCHAR(50) UNIQUE` to WorkOrders
2. ✅ Add `QuantityOrdered INT NOT NULL` to WorkOrders
3. ✅ Add `PartID INT` to CustomerPOLineItems with foreign key
4. ✅ Add trigger to auto-generate WorkOrderNumber

### High Priority:
5. ✅ Add `CustomerPOID INT` to WorkOrders for direct PO reference
6. ✅ Update views to use consistent column aliases
7. ✅ Add indexes for new columns

### Nice to Have:
8. ⚠️ Update frontend to use proper foreign key relationships
9. ⚠️ Add validation constraints (quantity > 0, etc.)
10. ⚠️ Consider denormalization strategy for performance

---

## Migration Strategy

1. Create migration script that ALTERs existing tables
2. Backfill WorkOrderNumber for existing records
3. Update CustomerPOLineItems to link PartID based on Part_Number
4. Update views to include new fields
5. Test frontend compatibility
6. Deploy to staging first

---

## Additional Observations

### Good Things Already in Place:
✅ CustomerPOLineItems table exists (proper normalization)
✅ WorkOrders.CustomerPOLineItemID foreign key exists
✅ Views provide abstraction layer for complex queries
✅ Proper indexing on foreign keys
✅ Status history tracking with triggers

### Areas for Future Improvement:
- Consider adding `LineItemID` to WorkOrders for better traceability
- Add CHECK constraints for quantities > 0
- Add audit trail for CustomerPOLineItems changes
- Consider soft deletes instead of CASCADE deletes
