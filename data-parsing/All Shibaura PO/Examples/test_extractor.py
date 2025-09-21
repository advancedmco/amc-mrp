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
    print(f"Processing {pdf_path}...")
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        text = page.extract_text()
        
        print("Extracted text preview:")
        print(text[:500] + "..." if len(text) > 500 else text)
        print("\n" + "="*50 + "\n")
        
        # Extract PO details and grand total
        po_number, po_date = extract_po_details(text)
        grand_total = extract_grand_total(text)
        
        print(f"PO Number: {po_number}")
        print(f"PO Date: {po_date}")
        print(f"Grand Total: {grand_total}")
        
        # Extract line items
        line_items = extract_line_items(page)
        
        print(f"Extracted {len(line_items)} line items")
        for item in line_items:
            print(f"  Line {item.get('Ln', 'N/A')}: {item.get('Item_Number', 'N/A')} - {item.get('Description', 'N/A')[:50]}...")
        
        # Add PO details and grand total to each line item
        for item in line_items:
            item.update({
                'PO_Number': po_number,
                'PO_Date': po_date,
                'Grand_Total': grand_total
            })
        
        return line_items

def main():
    # Test with the 4 example files
    example_files = [
        'example-po-format1-1item.pdf',
        'example-po-format1-multi-lines.pdf', 
        'example-po-format-2-single.pdf',
        'example-po-format-2-multi-lines.pdf'
    ]
    
    for pdf_file in example_files:
        if Path(pdf_file).exists():
            try:
                line_items = process_pdf(pdf_file)
                print(f"\n{'='*60}\n")
            except Exception as e:
                print(f"Error processing {pdf_file}: {str(e)}")
                print(f"\n{'='*60}\n")

if __name__ == "__main__":
    main()
