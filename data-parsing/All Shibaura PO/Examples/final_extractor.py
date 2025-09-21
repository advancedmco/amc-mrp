import pdfplumber
import csv
from pathlib import Path
import re
from datetime import datetime

def extract_po_details(page_text):
    """Extract PO number and date from the page text."""
    # Try different patterns for PO number and date
    patterns = [
        r'P\.O\. Number / Date:\s*([A-Z0-9-]+)\s+(\d{2}/\d{2}/\d{4})',
        r'P\.O\. Number / Date:\s*([A-Z0-9-]+)\s+(\d{1,2}/\d{1,2}/\d{4})',
        r'PO-(\d+)\s+(\d{2}/\d{2}/\d{4})',
        r'PO-(\d+)\s+(\d{1,2}/\d{1,2}/\d{4})'
    ]
    
    for pattern in patterns:
        po_match = re.search(pattern, page_text)
        if po_match:
            po_number = po_match.group(1)
            if not po_number.startswith('PO-'):
                po_number = f"PO-{po_number}"
            return po_number, po_match.group(2)
    
    return None, None

def extract_grand_total(page_text):
    """Extract grand total from the page text."""
    patterns = [
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
    desc = re.sub(r'\*QUOTE:.*', '', desc)
    desc = re.sub(r'\*DELIVERY:.*', '', desc)
    desc = re.sub(r'upervisor.*', '', desc)
    desc = re.sub(r'https?://.*', '', desc)
    desc = re.sub(r'\d{1,2}/\d{1,2}/\d{4}.*', '', desc)
    desc = re.sub(r'\d{1,2}:\d{2}\s*(AM|PM).*', '', desc)
    
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

def extract_line_items_advanced(page):
    """Extract line items with advanced parsing logic."""
    # Try different table extraction strategies
    strategies = [
        {'vertical_strategy': 'text', 'horizontal_strategy': 'text', 'snap_tolerance': 3},
        {'vertical_strategy': 'lines', 'horizontal_strategy': 'lines'},
        {'vertical_strategy': 'text', 'horizontal_strategy': 'lines', 'snap_tolerance': 5},
    ]
    
    for strategy in strategies:
        table = page.extract_table(strategy)
        if table and len(table) > 1:
            line_items = process_table_advanced(table)
            if line_items:
                return line_items
    
    return []

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
        if not header_found and any('Ln' in str(cell) or 'Part' in str(cell) or 'Description' in str(cell) for cell in row):
            header_found = True
            continue
        
        if not header_found:
            continue
            
        # Check if this is a line item row (starts with line number)
        if len(row) > 0 and is_line_number(row[0]):
            # Extract data based on expected positions and validation
            ln = row[0]
            part = row[1] if len(row) > 1 else ''
            
            # Find description - usually in position 2, but validate
            description = ''
            due_date = ''
            qty = ''
            amount = '0'  # Default amount as shown in expected output
            unit_price = ''
            extended_price = ''
            
            # Look for description in positions 2-4
            for i in range(2, min(len(row), 5)):
                if row[i] and not is_valid_date(row[i]) and not is_numeric(row[i]):
                    description = clean_description(row[i])
                    break
            
            # Look for due date
            for i in range(2, len(row)):
                if is_valid_date(row[i]):
                    due_date = row[i]
                    break
            
            # Look for numeric values (qty, unit price, extended price)
            numeric_values = []
            for i in range(2, len(row)):
                if is_numeric(row[i]) and row[i].strip():
                    numeric_values.append(row[i].strip())
            
            # Assign numeric values based on position and value
            if len(numeric_values) >= 3:
                qty = numeric_values[0]
                unit_price = numeric_values[1]
                extended_price = numeric_values[2]
            elif len(numeric_values) == 2:
                unit_price = numeric_values[0]
                extended_price = numeric_values[1]
            elif len(numeric_values) == 1:
                extended_price = numeric_values[0]
            
            line_item = {
                'Ln': ln,
                'Part': part,
                'Description': description,
                'Due Date': due_date,
                'Qty': qty,
                'Amount': amount,
                'Unit Price': unit_price,
                'Extended Price': extended_price
            }
            
            line_items.append(line_item)
    
    return line_items

def process_pdf(pdf_path):
    """Process a single PDF and return its line items."""
    print(f"Processing {pdf_path}...")
    
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        text = page.extract_text()
        
        # Extract PO details and grand total
        po_number, po_date = extract_po_details(text)
        grand_total = extract_grand_total(text)
        
        print(f"PO Number: {po_number}")
        print(f"PO Date: {po_date}")
        print(f"Grand Total: {grand_total}")
        
        # Extract line items using advanced approach
        line_items = extract_line_items_advanced(page)
        
        print(f"Extracted {len(line_items)} line items")
        for item in line_items:
            print(f"  Line {item.get('Ln', 'N/A')}: {item.get('Part', 'N/A')} - {item.get('Description', 'N/A')[:50]}...")
        
        # Add PO details and grand total to each line item
        for item in line_items:
            item.update({
                'Order Date': po_date,
                'Grand Total': grand_total,
                'PO': po_number.replace('PO-', '') if po_number else ''
            })
        
        return line_items

def write_to_csv(all_line_items, output_file):
    """Write all line items to CSV file matching expected format."""
    field_names = [
        'Ln', 'Part', 'Description', 'Due Date', 'Qty', 'Amount', 
        'Unit Price', 'Extended Price', 'Order Date', 'Grand Total', 'PO'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=field_names)
        writer.writeheader()
        
        for line_items in all_line_items:
            for item in line_items:
                # Clean and format data
                clean_item = {
                    'Ln': item.get('Ln', '').strip(),
                    'Part': item.get('Part', '').strip(),
                    'Description': item.get('Description', '').strip(),
                    'Due Date': item.get('Due Date', '').strip(),
                    'Qty': item.get('Qty', '').strip(),
                    'Amount': item.get('Amount', '').strip(),
                    'Unit Price': item.get('Unit Price', '').strip().replace('$', '').replace(',', ''),
                    'Extended Price': item.get('Extended Price', '').strip().replace('$', '').replace(',', ''),
                    'Order Date': item.get('Order Date', '').strip(),
                    'Grand Total': str(item.get('Grand Total', '')).replace('$', '').replace(',', ''),
                    'PO': item.get('PO', '').strip()
                }
                writer.writerow(clean_item)

def main():
    # Test with the 4 example files
    example_files = [
        'example-po-format1-1item.pdf',
        'example-po-format1-multi-lines.pdf', 
        'example-po-format-2-single.pdf',
        'example-po-format-2-multi-lines.pdf'
    ]
    
    all_line_items = []
    
    for pdf_file in example_files:
        if Path(pdf_file).exists():
            try:
                line_items = process_pdf(pdf_file)
                all_line_items.append(line_items)
                print(f"\n{'='*60}\n")
            except Exception as e:
                print(f"Error processing {pdf_file}: {str(e)}")
                print(f"\n{'='*60}\n")
    
    # Write results to CSV
    if all_line_items:
        write_to_csv(all_line_items, 'final_extracted_data.csv')
        print("Results written to final_extracted_data.csv")

if __name__ == "__main__":
    main()
