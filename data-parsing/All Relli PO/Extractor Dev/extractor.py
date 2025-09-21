import pdfplumber
import csv
from pathlib import Path
import re
from datetime import datetime

def extract_po_details(page_text):
    """Extract PO number and date from the page text."""
    # Look for Relli PO format: "PURCHASE ORDER 554002-X1572-1" or just "705677-X1572-1"
    po_match = re.search(r'PURCHASE ORDER\s*[-]*\s*([0-9-]+[A-Z0-9-]+)', page_text)
    if not po_match:
        # Try alternative format without "PURCHASE ORDER" text
        po_match = re.search(r'([0-9]+-X1572-[0-9]+)', page_text)
    
    if po_match:
        po_number = po_match.group(1).strip()
        # Look for date in format "09/24/24" or "04/07/18" 
        date_match = re.search(r'DATE\s*[.|I]*\s*[PAGE\s]*\s*(\d{1,2}/\d{1,2}/\d{2,4})', page_text)
        if date_match:
            po_date = date_match.group(1)
            return po_number, po_date
    return None, None

def extract_grand_total(page_text):
    """Extract grand total from the page text."""
    patterns = [
        r'TOTAL ORDER\s+([\d,]+\.\d{1,2})',
        r'Grand total\s*([\d,]+\.\d{2})',
        r'Grand Total\s*([\d,]+\.\d{2})',
        r'GRAND TOTAL\s*([\d,]+\.\d{2})',
        r'Total\s*([\d,]+\.\d{2})'
    ]
    
    for pattern in patterns:
        total_match = re.search(pattern, page_text)
        if total_match:
            return float(total_match.group(1).replace(',', ''))
    
    return None

def is_line_number(text):
    """Check if the text is a valid line number."""
    if not text:
        return False
    cleaned = text.strip()
    return cleaned.isdigit() and int(cleaned) <= 50  # Reasonable line number limit

def clean_cell(cell):
    """Clean cell content."""
    if cell is None:
        return ''
    return str(cell).strip()

def clean_description(desc):
    """Clean description field by removing extra metadata."""
    if not desc:
        return ''
    
    # Remove common contamination patterns
    desc = re.sub(r'\*QUOTE.*', '', desc, flags=re.IGNORECASE | re.MULTILINE)
    desc = re.sub(r'\*DELIVERY.*', '', desc, flags=re.IGNORECASE | re.MULTILINE)
    desc = re.sub(r'upervisor.*', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'https?://.*', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'\d{1,2}/\d{1,2}/\d{4}.*', '', desc)
    desc = re.sub(r'\d{1,2}:\d{2}\s*(AM|PM).*', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'DATE\s*$', '', desc, flags=re.IGNORECASE)
    
    # Clean up whitespace and newlines
    desc = ' '.join(desc.split())
    return desc.strip()

def is_valid_date(text):
    """Check if text looks like a date."""
    if not text:
        return False
    # Match various date formats
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{4}',
        r'\d{1,2}/\d{1,2}/\d{2}',
        r'\d{4}-\d{1,2}-\d{1,2}'
    ]
    return any(re.match(pattern, text.strip()) for pattern in date_patterns)

def is_numeric(text):
    """Check if text is numeric (for qty, prices)."""
    if not text:
        return False
    try:
        float(text.replace(',', '').replace('$', ''))
        return True
    except:
        return False

def extract_line_items(page):
    """Extract line items with advanced parsing logic."""
    # Try extract_table first
    table = page.extract_table()
    if table and len(table) > 1:
        line_items = process_table_advanced(table)
        if line_items:
            return line_items
    
    # Use find_tables for better table detection
    tables = page.find_tables()
    for table_obj in tables:
        table = table_obj.extract()
        if table and len(table) > 1:
            line_items = process_table_advanced(table)
            if line_items:
                return line_items
    
    return []

def parse_multi_line_items(row):
    """Parse a row that contains multiple line items combined."""
    line_items = []
    
    if len(row) < 10:  # Need at least 10 columns for full data
        return line_items
    
    # Extract the combined data
    ln_data = row[0] if row[0] else ''
    part_data = row[1] if row[1] else ''
    desc_data = row[2] if row[2] else ''
    date_data = row[3] if row[3] else ''
    uom_data = row[4] if row[4] else ''
    qty_data = row[5] if row[5] else ''
    discount_pct_data = row[6] if row[6] else ''
    discount_amt_data = row[7] if row[7] else ''
    unit_price_data = row[8] if row[8] else ''
    extended_price_data = row[9] if row[9] else ''
    
    # Split by newlines to separate multiple items
    ln_lines = ln_data.split('\n') if ln_data else ['']
    part_lines = part_data.split('\n') if part_data else ['']
    desc_lines = desc_data.split('\n') if desc_data else ['']
    date_lines = date_data.split('\n') if date_data else ['']
    qty_lines = qty_data.split('\n') if qty_data else ['']
    unit_price_lines = unit_price_data.split('\n') if unit_price_data else ['']
    extended_price_lines = extended_price_data.split('\n') if extended_price_data else ['']
    
    # Parse the description lines to match with parts
    # Example: 'L481902 [SCREW TIP WRENCH\n60MM ISF - ECSXII 17A 17AT 19A\n19A\nTMW0002 [LINK PIN 1 EC950SX]\n*QUOTE: 13235\n*DELIVERY: 5 WEEKS FROM PO\nDATE'
    
    # Build items based on line numbers and parts
    for i, ln in enumerate(ln_lines):
        if ln.strip() and ln.strip().isdigit():
            part = part_lines[i] if i < len(part_lines) else ''
            
            # Find the description for this part
            description_parts = []
            found_part_desc = False
            
            for desc_line in desc_lines:
                desc_line = desc_line.strip()
                if not desc_line:
                    continue
                    
                # Check if this line starts with the current part number
                if desc_line.startswith(part.strip()) and part.strip():
                    found_part_desc = True
                    description_parts = [desc_line]
                elif found_part_desc:
                    # Check if this is the start of the next part
                    is_next_part = False
                    for next_part in part_lines:
                        if next_part.strip() and desc_line.startswith(next_part.strip()):
                            is_next_part = True
                            break
                    
                    if is_next_part:
                        break  # Stop collecting for this part
                    else:
                        # This is a continuation of the current part's description
                        description_parts.append(desc_line)
            
            # If we didn't find a part-specific description, try to extract by position
            if not description_parts and i < len(desc_lines):
                description_parts = [desc_lines[i]]
            
            line_item = {
                'Ln': ln.strip(),
                'Part': part.strip(),
                'Description': clean_description(' '.join(description_parts)),
                'Due_Date': date_lines[i] if i < len(date_lines) else '',
                'Qty_Ordered': qty_lines[i] if i < len(qty_lines) else '',
                'Amount': '0',
                'Unit_Price': unit_price_lines[i] if i < len(unit_price_lines) else '',
                'Extended_Price': extended_price_lines[i] if i < len(extended_price_lines) else ''
            }
            
            line_items.append(line_item)
    
    return line_items

def process_table_advanced(table):
    """Process extracted table with advanced logic."""
    if not table:
        return []
    
    line_items = []
    header_found = False
    
    for row_idx, row in enumerate(table):
        if not row or not any(row):
            continue
            
        row = [clean_cell(cell) for cell in row]
        
        # Skip header rows
        if not header_found and any('ITEM NO' in str(cell) or 'PART NUMBER' in str(cell) or 'DESCRIPTION' in str(cell) for cell in row):
            header_found = True
            continue
        
        if not header_found:
            continue
        
        # Check for multi-line format (combined line items in one row)
        if len(row) >= 10 and row[0] and '\n' in row[0]:
            # This looks like a multi-line format
            multi_items = parse_multi_line_items(row)
            line_items.extend(multi_items)
            continue
            
        # Check if this is a single line item row (starts with line number)
        if len(row) > 0 and is_line_number(row[0]):
            ln = row[0]
            part = row[3] if len(row) > 3 else ''
            description = clean_description(row[4]) if len(row) > 4 else ''
            due_date = row[8] if len(row) > 8 else ''
            qty = row[1] if len(row) > 1 else ''
            unit_price = row[5] if len(row) > 5 else ''
            extended_price = row[7] if len(row) > 7 else ''
            amount = '0'  # Default amount as shown in expected output
            
            line_item = {
                'Ln': ln,
                'Part': part,
                'Description': description,
                'Due_Date': due_date,
                'Qty_Ordered': qty,
                'Amount': amount,
                'Unit_Price': unit_price,
                'Extended_Price': extended_price
            }
            
            line_items.append(line_item)
    
    return line_items

def extract_line_items_from_text(text):
    """Extract line items from text for Relli PDFs."""
    line_items = []
    lines = text.split('\n')
    
    # Look for Relli-style line items
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Pattern for Relli line items: "1    500 EA 12012168"
        # Format: [line_num] [qty] [unit] [part_number]
        item_match = re.match(r'^(\d+)\s+(\d+)\s+EA\s+([A-Z0-9-]+)', line)
        if item_match:
            ln = item_match.group(1)
            qty = item_match.group(2)
            part = item_match.group(3)
            
            # Find description on the next line
            description = ''
            if i + 1 < len(lines):
                desc_line = lines[i + 1].strip()
                description = clean_description(desc_line)
            
            # Look for unit price and extension on subsequent lines
            unit_price = ''
            extended_price = ''
            due_date = ''
            
            # Search the next few lines for pricing info
            for j in range(i + 1, min(i + 10, len(lines))):
                search_line = lines[j].strip()
                
                # Look for price pattern: "19.28 E 9640.00 03/15/25"
                price_match = re.search(r'(\d+\.\d{2})\s+E\s+(\d+\.\d{2})\s+(\d{1,2}/\d{1,2}/\d{2})', search_line)
                if price_match:
                    unit_price = price_match.group(1)
                    extended_price = price_match.group(2)
                    due_date = price_match.group(3)
                    break
            
            line_item = {
                'Ln': ln,
                'Part': part,
                'Description': description,
                'Due_Date': due_date,
                'Qty_Ordered': qty,
                'Amount': '0',
                'Unit_Price': unit_price,
                'Extended_Price': extended_price
            }
            line_items.append(line_item)
    
    # If no line items found with the above method, try the single-item format
    if not line_items:
        for i, line in enumerate(lines):
            # Look for "125 EA 11450720-1" pattern (for Modern Format.pdf)
            item_match = re.search(r'(\d+)\s+EA\s+([A-Z0-9-]+)', line)
            if item_match:
                qty = item_match.group(1)
                part = item_match.group(2)
                
                # Find description on the same or next line
                description = ''
                desc_match = re.search(r'[A-Z0-9-]+\s+(.+)', line)
                if desc_match:
                    description = clean_description(desc_match.group(1))
                
                # Look for pricing info
                unit_price = ''
                extended_price = ''
                due_date = ''
                
                for j in range(i, min(i + 5, len(lines))):
                    search_line = lines[j].strip()
                    # Look for "22.20 E 2775.00 05/25/24" pattern
                    price_match = re.search(r'(\d+\.\d{2})\s+E\s+(\d+\.\d{2})\s+(\d{1,2}/\d{1,2}/\d{2})', search_line)
                    if price_match:
                        unit_price = price_match.group(1)
                        extended_price = price_match.group(2)
                        due_date = price_match.group(3)
                        break
                
                line_item = {
                    'Ln': '1',
                    'Part': part,
                    'Description': description,
                    'Due_Date': due_date,
                    'Qty_Ordered': qty,
                    'Amount': '0',
                    'Unit_Price': unit_price,
                    'Extended_Price': extended_price
                }
                line_items.append(line_item)
                break  # Only get the first item for single-item PDFs
        
        # If still no items found, try the Color.pdf format with parentheses
        if not line_items:
            for i, line in enumerate(lines):
                # Look for "150 (~20521751" pattern (for Color.pdf)
                item_match = re.search(r'(\d+)\s+\(([~A-Z0-9-]+)', line)
                if item_match:
                    qty = item_match.group(1)
                    part = item_match.group(2)
                    
                    # Find description on the same line after part number
                    description = ''
                    desc_match = re.search(r'\([~A-Z0-9-]+\s+(.+)', line)
                    if desc_match:
                        description = clean_description(desc_match.group(1))
                    
                    # Look for pricing info in subsequent lines
                    unit_price = ''
                    extended_price = ''
                    due_date = ''
                    
                    for j in range(i + 1, min(i + 10, len(lines))):
                        search_line = lines[j].strip()
                        # Look for "93.50 06/23/18" pattern
                        price_match = re.search(r'(\d+\.\d{2})\s*\)\s*(\d{1,2}/\d{1,2}/\d{2})', search_line)
                        if price_match:
                            unit_price = price_match.group(1)
                            due_date = price_match.group(2)
                            # Calculate extended price
                            try:
                                extended_price = str(float(unit_price) * int(qty))
                            except:
                                extended_price = unit_price
                            break
                    
                    line_item = {
                        'Ln': '1',
                        'Part': part,
                        'Description': description,
                        'Due_Date': due_date,
                        'Qty_Ordered': qty,
                        'Amount': '0',
                        'Unit_Price': unit_price,
                        'Extended_Price': extended_price
                    }
                    line_items.append(line_item)
                    break  # Only get the first item for single-item PDFs
    
    return line_items

def process_pdf(pdf_path):
    """Process a single PDF and return its line items."""
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        text = page.extract_text()
        
        # Extract PO details and grand total
        po_number, po_date = extract_po_details(text)
        grand_total = extract_grand_total(text)
        
        # Extract line items
        line_items = extract_line_items(page)
        if not line_items:
            line_items = extract_line_items_from_text(text)
        
        # Calculate grand_total if not found
        if line_items and grand_total is None:
            ext_sum = sum(float(item['Extended_Price'].replace(',', '')) for item in line_items if item['Extended_Price'])
            grand_total = ext_sum
        
        # Add PO details and grand total to each line item
        for item in line_items:
            item.update({
                'PO_Number': po_number,
                'Order_Date': po_date,
                'Grand_Total': grand_total,
                'PO': po_number if po_number else ''
            })
        
        return line_items

def write_to_csv(line_items, output_file, write_header=False):
    """Write line items to CSV file matching expected format."""
    field_names = [
        'Ln', 'Part', 'Description', 'Due Date', 'Qty', 'Amount', 
        'Unit Price', 'Extended Price', 'Order Date', 'Grand Total', 'PO'
    ]
    
    mode = 'w' if write_header else 'a'
    with open(output_file, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=field_names)
        if write_header:
            writer.writeheader()
        for item in line_items:
            # Clean and standardize data before writing
            due_date = (item.get('Due_Date') or '').strip()
            order_date = (item.get('Order_Date') or '').strip()
            qty = (item.get('Qty_Ordered') or '').strip()
            unit_price = (item.get('Unit_Price') or '').strip().replace('$', '').replace(',', '')
            extended_price = (item.get('Extended_Price') or '').strip().replace('$', '').replace(',', '')
            grand_total = str(item.get('Grand_Total') or '').replace('$', '').replace(',', '')
            
            # Format dates to m/d/yy without leading zeros
            def format_date(date_str):
                if not date_str:
                    return date_str
                try:
                    dt = datetime.strptime(date_str, '%m/%d/%Y')
                    m = dt.month
                    d = dt.day
                    y = dt.year % 100
                    return f'{m}/{d}/{y}'
                except:
                    return date_str
            
            due_date = format_date(due_date)
            order_date = format_date(order_date)
            
            # Remove .00 from whole numbers
            qty = re.sub(r'\.00$', '', qty)
            unit_price = re.sub(r'\.00$', '', unit_price)
            extended_price = re.sub(r'\.00$', '', extended_price)
            grand_total = re.sub(r'\.0$', '', grand_total)
            
            clean_item = {
                'Ln': item.get('Ln', '').strip(),
                'Part': item.get('Part', '').strip(),
                'Description': item.get('Description', '').strip(),
                'Due Date': due_date,
                'Qty': qty,
                'Amount': item.get('Amount', '').strip(),
                'Unit Price': unit_price,
                'Extended Price': extended_price,
                'Order Date': order_date,
                'Grand Total': grand_total,
                'PO': item.get('PO', '').strip()
            }
            writer.writerow(clean_item)

def main():
    # Configuration
    input_dir = Path('.')
    output_csv = 'purchase_orders.csv'
    
    # Create output CSV with headers
    first_file = True
    total_files = len(list(input_dir.glob('*.pdf')))
    processed_files = 0
    
    print(f"Found {total_files} PDF files to process")
    
    # Process each PDF in the directory
    for pdf_file in input_dir.glob('*.pdf'):
        try:
            print(f"Processing {pdf_file} ({processed_files + 1}/{total_files})...")
            line_items = process_pdf(pdf_file)
            write_to_csv(line_items, output_csv, write_header=first_file)
            first_file = False
            processed_files += 1
            print(f"Successfully extracted {len(line_items)} line items from {pdf_file}")
        except Exception as e:
            print(f"Error processing {pdf_file}: {str(e)}")
            continue
    
    print(f"\nProcessing complete. Processed {processed_files} files.")
    print(f"Output saved to {output_csv}")

if __name__ == "__main__":
    main()
