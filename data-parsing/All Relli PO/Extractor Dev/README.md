# Relli Purchase Order PDF Extractor

This tool extracts line item data from Relli Technology Inc. purchase order PDFs and outputs the results to a CSV file.

## Features

- Extracts data from multiple Relli PO PDF formats:
  - Multi-page PDFs with multiple line items (2-pager.pdf)
  - Single-item PDFs with different layouts (Modern Format.pdf, Color.pdf)
  - PDFs with highlights and annotations (Modern with Highlights.pdf)
- Automatically detects PO numbers, dates, and pricing information
- Outputs clean CSV data matching the expected benchmark format
- Handles various edge cases and PDF layout variations

## Setup

1. Ensure you have Python 3.x installed
2. Set up the virtual environment and install dependencies:
   ```bash
   chmod +x python_venv_setup.sh
   ./python_venv_setup.sh
   ```
3. Activate the virtual environment:
   ```bash
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate     # On Windows
   ```

## Usage

1. Place your Relli PO PDF files in the same directory as `extractor.py`
2. Run the extractor:
   ```bash
   python extractor.py
   ```
3. The tool will process all PDF files in the directory and output results to `purchase_orders.csv`

## Output Format

The CSV output includes the following columns:
- `Ln`: Line number
- `Part`: Part number  
- `Description`: Item description
- `Due Date`: Delivery date (MM/DD/YY format)
- `Qty`: Quantity ordered
- `Amount`: Amount (typically 0)
- `Unit Price`: Price per unit
- `Extended Price`: Total price for line item
- `Order Date`: PO date (MM/DD/YY format)
- `Grand Total`: Total order amount
- `PO`: Purchase order number

## Supported PDF Formats

The extractor handles various Relli PO formats:
- Standard multi-line item format
- Single-item format with "EA" units
- Color/highlighted PDFs
- PDFs with parentheses-enclosed part numbers

## Files Processed

The tool will automatically process all `.pdf` files in the current directory and report the number of line items extracted from each file.
