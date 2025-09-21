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
    return cleaned.isdigit() or (cleaned.replace('.', '').isdigit() and cleaned.count('.') <= 1)

def clean_cell(cell):
    """Clean cell content."""
    if cell is None:
        return ''
    return str(cell).strip()

def find_column_indices(header_row):
    """Find column indices based on header row."""
    if not header_row:
        return {}
    
    indices = {}
    for i, cell in enumerate(header_row):
        cell_text = clean_cell(cell).lower()
        if 'ln' in cell_text or 'line' in cell_text:
            indices['ln'] = i
        elif 'part' in cell_text or 'item' in cell_text:
            indices['part'] = i
        elif 'description' in cell_text or 'desc' in cell_text:
            indices['description'] = i
        elif 'due' in cell_text and 'date' in cell_text:
            indices['due_date'] = i
        elif 'qty' in cell_text or 'quantity' in cell_text:
            indices['qty'] = i
        elif 'amount' in cell_text:
            indices['amount'] = i
        elif 'unit' in cell_text and 'price' in cell_text:
            indices['unit_price'] = i
        elif 'extended' in cell_text or 'total' in cell_text:
            indices['extended_price'] = i
    
    return indices

def extract_line_items_flexible(page):
    """Extract line items with flexible column detection."""
    # Try different table extraction strategies
    strategies = [
        {'vertical_strategy': 'text', 'horizontal_strategy': 'text'},
        {'vertical_strategy': 'lines', 'horizontal_strategy': 'lines'},
        {'vertical_strategy': 'text', 'horizontal_strategy': 'lines'},
        {'vertical_strategy': 'lines', 'horizontal_strategy': 'text'}
    ]
    
    for strategy in strategies:
        table = page.extract_table(strategy)
        if table and len(table) > 1:
            line_items = process_table(table)
            if line_items:
                return line_items
    
    return []

def process_table(table):
    """Process extracted table to get line items."""
    if not table:
        return []
    
    line_items = []
    header_row_index = None
    column_indices = {}
    
    # Find header row
    for i, row in enumerate(table):
        if row and any(cell and ('Ln' in str(cell) or 'Part' in str(cell) or 'Description' in str(cell)) for cell in row):
            header_row_index = i
            column_indices = find_column_indices(row)
            break
    
    if header_row_index is None:
        # If no clear header found, assume first row is header and try to infer columns
        header_row_index = 0
        # Try to infer column positions based on typical PO format
        if len(table[0]) >= 10:
            column_indices = {
                'ln': 0,
                'part': 1, 
                'description': 2,
                'due_date': 3,
                'qty': 4,
                'amount': 5,
                'unit_price': 6,
                'extended_price': 7
            }
    
    # Process data rows
    current_item = None
    description_buffer = []
    
    for row_idx, row in enumerate(table[header_row_index + 1:], start=header_row_index + 1):
        if not row or not any(row):
            continue
            
        row = [clean_cell(cell) for cell in row]
        
        # Check if this starts a new line item
        ln_col = column_indices.get('ln', 0)
        if ln_col < len(row) and is_line_number(row[ln_col]):
            # Save previous item
            if current_item:
                current_item['Description'] = ' '.join(description_buffer).strip()
                line_items.append(current_item)
            
            # Start new item
            part_col = column_indices.get('part', 1)
            desc_col = column_indices.get('description', 2)
            due_date_col = column_indices.get('due_date', 3)
            qty_col = column_indices.get('qty', 4)
            amount_col = column_indices.get('amount', 5)
            unit_price_col = column_indices.get('unit_price', 6)
            extended_price_col = column_indices.get('extended_price', 7)
            
            current_item = {
                'Ln': row[ln_col] if ln_col < len(row) else '',
                'Part': row[part_col] if part_col < len(row) else '',
                'Description': row[desc_col] if desc_col < len(row) else '',
                'Due Date': row[due_date_col] if due_date_col < len(row) else '',
                'Qty': row[qty_col] if qty_col < len(row) else '',
                'Amount': row[amount_col] if amount_col < len(row) else '',
                'Unit Price': row[unit_price_col] if unit_price_col < len(row) else '',
                'Extended Price': row[extended_price_col] if extended_price_col < len(row) else ''
            }
            
            description_buffer = [current_item['Description']] if current_item['Description'] else []
            
        # Handle continuation lines for description
        elif current_item:
            desc_col = column_indices.get('description', 2)
            if desc_col < len(row) and row[desc_col]:
                description_buffer.append(row[desc_col])
    
    # Add the last item
    if current_item:
        current_item['Description'] = ' '.join(description_buffer).strip()
        line_items.append(current_item)
    
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
        
        # Extract line items using flexible approach
        line_items = extract_line_items_flexible(page)
        
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
        write_to_csv(all_line_items, 'extracted_data.csv')
        print("Results written to extracted_data.csv")

if __name__ == "__main__":
    main()
