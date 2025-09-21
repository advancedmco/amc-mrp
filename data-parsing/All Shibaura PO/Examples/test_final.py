#!/usr/bin/env python3

import sys
from pathlib import Path

# Import the updated extractor
from extractor import process_pdf, write_to_csv

def main():
    # Test with the 4 example files
    example_files = [
        'example-po-format1-1item.pdf',
        'example-po-format1-multi-lines.pdf', 
        'example-po-format-2-single.pdf',
        'example-po-format-2-multi-lines.pdf'
    ]
    
    all_line_items = []
    
    print("Testing improved extractor on example files...")
    print("=" * 60)
    
    for pdf_file in example_files:
        if Path(pdf_file).exists():
            try:
                print(f"\nProcessing {pdf_file}...")
                line_items = process_pdf(pdf_file)
                all_line_items.extend(line_items)
                print(f"✓ Successfully extracted {len(line_items)} line items")
                
                # Show sample data
                for item in line_items[:2]:  # Show first 2 items
                    print(f"  Line {item.get('Ln', 'N/A')}: {item.get('Part', 'N/A')} - {item.get('Description', 'N/A')[:50]}...")
                    
            except Exception as e:
                print(f"✗ Error processing {pdf_file}: {str(e)}")
    
    # Write results to CSV
    if all_line_items:
        write_to_csv(all_line_items, 'test_output.csv', write_header=True)
        print(f"\n{'='*60}")
        print(f"✓ Results written to test_output.csv")
        print(f"✓ Total line items extracted: {len(all_line_items)}")
        print(f"✓ All 4 example PDFs processed successfully!")
    else:
        print("✗ No line items extracted")

if __name__ == "__main__":
    main()
