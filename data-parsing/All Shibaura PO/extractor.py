import pdfplumber
import csv
from pathlib import Path
import re
from datetime import datetime

def extract_po_details(page_text):
    """Extract PO number and date from the page text."""
    po_match = re.search(r'P\.O\. Number / Date:\s*([A-Z0-9-]+)\s+(\d{2}/\d{2}/\d{4})', page_text)
    if po_match:
        return po_match.group(1), po_match.group(2)
    return None, None

def extract_grand_total(page_text):
    """Extract grand total from the page text."""
    total_match = re.search(r'Grand total\s*([\d,]+\.\d{2})', page_text)
    if total_match:
        return float(total_match.group(1).replace(',', ''))
    return None

def is_line_number(text):
    """Check if the text is a valid line number."""
    if not text:
        return False
    cleaned = text.strip()
    return cleaned.isdigit() or cleaned.replace('.', '').isdigit()

def clean_cell(cell):
    """Clean cell content."""
    if cell is None:
        return ''
    return str(cell).strip()

def extract_line_items(page):
    """Extract line items from the page, handling multi-line descriptions."""
    # Extract table with specific settings
    table = page.extract_table({
        'vertical_strategy': 'text',
        'horizontal_strategy': 'text',
        'snap_tolerance': 3,
        'join_tolerance': 3,
    })
    
    if not table:
        return []
    
    line_items = []
    current_item = None
    description_buffer = []
    
    # Find header row to determine column indices
    header_row_index = None
    for i, row in enumerate(table):
        if row and any('Ln' in str(cell) for cell in row):
            header_row_index = i
            break
    
    if header_row_index is None:
        return []
    
    # Process rows after header
    for row in table[header_row_index + 1:]:
        if not row or not any(row):  # Skip empty rows
            continue
            
        # Clean row data
        row = [clean_cell(cell) for cell in row]
        
        # Check if this is a start of a new line item
        if is_line_number(row[0]):
            # Save previous item if exists
            if current_item:
                current_item['Description'] = '\n'.join(description_buffer)
                line_items.append(current_item)
            
            # Start new item
            description_text = row[2] if len(row) > 2 else ''
            description_buffer = [description_text] if description_text else []
            
            try:
                current_item = {
                    'Ln': row[0],
                    'Item_Number': row[1] if len(row) > 1 else '',
                    'Due_Date': row[3] if len(row) > 3 else '',
                    'Qty_Ordered': row[5] if len(row) > 5 else '',
                    'Unit_Price': row[8] if len(row) > 8 else '',
                    'Extended_Price': row[9] if len(row) > 9 else ''
                }
            except Exception:
                continue
        
        # If this is a continuation row (part of multi-line description)
        elif current_item and row[2]:
            description_buffer.append(row[2])
    
    # Don't forget to add the last item
    if current_item:
        current_item['Description'] = '\n'.join(description_buffer)
        line_items.append(current_item)
    
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
        
        # Add PO details and grand total to each line item
        for item in line_items:
            item.update({
                'PO_Number': po_number,
                'PO_Date': po_date,
                'Grand_Total': grand_total
            })
        
        return line_items

def write_to_csv(line_items, output_file, write_header=False):
    """Write line items to CSV file."""
    field_names = [
        'PO_Number', 'PO_Date', 'Ln', 'Item_Number', 'Description', 
        'Due_Date', 'Qty_Ordered', 'Unit_Price', 'Extended_Price', 'Grand_Total'
    ]
    
    mode = 'w' if write_header else 'a'
    with open(output_file, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=field_names)
        if write_header:
            writer.writeheader()
        for item in line_items:
            # Clean and standardize data before writing
            clean_item = {
                'PO_Number': item.get('PO_Number', ''),
                'PO_Date': item.get('PO_Date', ''),
                'Ln': item.get('Ln', '').strip(),
                'Item_Number': item.get('Item_Number', '').strip(),
                'Description': item.get('Description', '').replace('\r', '\n'),
                'Due_Date': item.get('Due_Date', '').strip(),
                'Qty_Ordered': item.get('Qty_Ordered', '').strip(),
                'Unit_Price': item.get('Unit_Price', '').strip().replace('$', '').replace(',', ''),
                'Extended_Price': item.get('Extended_Price', '').strip().replace('$', '').replace(',', ''),
                'Grand_Total': str(item.get('Grand_Total', '')).replace('$', '').replace(',', '')
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