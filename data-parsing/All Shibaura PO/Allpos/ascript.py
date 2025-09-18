import pdfplumber
import csv
from pathlib import Path
import re

def find_po_number(text):
    """Find text pattern 'PO-' followed by numbers."""
    po_pattern = r'PO-\d+'
    match = re.search(po_pattern, text)
    return match.group(0) if match else None

def process_pdf(pdf_path):
    """Extract text from PDF and find PO number."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text()
            po_number = find_po_number(text)
            return {
                'filename': pdf_path.name,
                'po_number': po_number or 'Not Found'
            }
    except Exception as e:
        return {
            'filename': pdf_path.name,
            'po_number': f'Error: {str(e)}'
        }

def main():
    # Get all PDFs in current directory
    current_dir = Path('.')
    pdf_files = list(current_dir.glob('*.pdf'))
    
    if not pdf_files:
        print("No PDF files found in current directory")
        return
    
    # Process PDFs and write results
    results = [process_pdf(pdf) for pdf in pdf_files]
    
    # Write to CSV
    output_file = 'po_numbers.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['filename', 'po_number'])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Processed {len(pdf_files)} files")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()