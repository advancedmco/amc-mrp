# PO Processing Scripts

This repository contains Python scripts for extracting and processing Purchase Order (PO) information from PDF documents.

## Scripts Overview

### 1. extractor.py
The main extraction script that processes PO PDF documents and extracts structured data into CSV format.

**What it does:**
- Parses PDF files using `pdfplumber` to extract text and table data
- Extracts key PO information: PO number, date, and grand total
- Processes line items from tables including: line number, item number, description, due date, quantity, unit price, and extended price
- Handles multi-line descriptions in table cells
- Outputs all data to a consolidated CSV file (`purchase_orders.csv`)

**How it works:**
1. Scans the current directory for all PDF files
2. For each PDF, extracts the first page content
3. Uses regex patterns to find PO number, date, and grand total
4. Extracts table data with intelligent parsing to handle multi-line descriptions
5. Combines all extracted data and writes to CSV with standardized formatting

### 2. fix_csv.py
A utility script to fix CSV files that have formatting issues with bracket notation split across multiple lines.

**What it does:**
- Reads a CSV file and identifies lines with broken bracket pairs (`[` and `]`)
- Reconstructs broken entries by combining lines that were split inappropriately
- Creates a new "adjusted" CSV file with the corrections

**How it works:**
1. Reads the entire CSV file line by line
2. Identifies lines containing opening brackets `[` without closing brackets `]`
3. Stores these lines and combines them with the next line containing the closing bracket `]`
4. Outputs the corrected data to a new CSV file with `_adjusted` suffix

## Dependencies

### Required Python Packages
- `pdfplumber` - For PDF text and table extraction
- `csv` - Built-in Python module for CSV handling
- `pathlib` - Built-in Python module for file path operations
- `re` - Built-in Python module for regular expressions
- `datetime` - Built-in Python module for date handling
- `sys` - Built-in Python module for system operations
- `os` - Built-in Python module for operating system interface

### External Dependencies
Only `pdfplumber` needs to be installed via pip. All other modules are part of Python's standard library.

## Setting Up Python Virtual Environment for VSCode

### 1. Create Virtual Environment
```bash
# Navigate to your project directory
cd "/Users/brendeenee/SynologyDriveAMC/Administrative/processing-data/PO Processing"

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 2. Install Dependencies
```bash
# With virtual environment activated
pip install pdfplumber
```

### 3. Configure VSCode to Use Virtual Environment

#### Method 1: Command Palette
1. Open VSCode in your project directory
2. Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
3. Type "Python: Select Interpreter"
4. Choose the interpreter from your virtual environment:
   ```
   ./venv/bin/python
   ```

#### Method 2: VSCode Settings
1. Create or edit `.vscode/settings.json` in your project root:
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.terminal.activateEnvironment": true
}
```

### 4. Verify Setup
Create a simple test to verify the environment is working:
```bash
python -c "import pdfplumber; print('pdfplumber installed successfully')"
```

## How to Run the Scripts

### Running extractor.py

**Prerequisites:**
- Place all PO PDF files in the `All Shibaura PO/` directory
- Ensure virtual environment is activated
- Ensure `pdfplumber` is installed

**Command:**
```bash
# Navigate to the All Shibaura PO directory
cd "All Shibaura PO"

# Run the extractor
python extractor.py
```

**Output:**
- Creates `purchase_orders.csv` in the same directory
- Console output shows processing progress and results
- Each PDF file's line items are appended to the CSV

**Expected Console Output:**
```
Found X PDF files to process
Processing filename.pdf (1/X)...
Successfully extracted Y line items from filename.pdf
...
Processing complete. Processed X files.
Output saved to purchase_orders.csv
```

### Running fix_csv.py

**Prerequisites:**
- Have a CSV file that needs bracket notation fixes
- Virtual environment activated (though only built-in modules are used)

**Command:**
```bash
python "All Shibaura PO/fix_csv.py" path/to/your/file.csv
```

**Example:**
```bash
python "All Shibaura PO/fix_csv.py" "All Shibaura PO/purchase_orders.csv"
```

**Output:**
- Creates a new file with `_adjusted` suffix (e.g., `purchase_orders_adjusted.csv`)
- Console output confirms the output file location

## CSV Output Format

The `extractor.py` script produces a CSV with the following columns:

| Column | Description |
|--------|-------------|
| PO_Number | Purchase Order number |
| PO_Date | Purchase Order date (MM/DD/YYYY format) |
| Ln | Line number within the PO |
| Item_Number | Product/item number |
| Description | Item description (may contain multiple lines) |
| Due_Date | Required delivery date |
| Qty_Ordered | Quantity ordered |
| Unit_Price | Price per unit (cleaned of $ and commas) |
| Extended_Price | Total price for line item (cleaned of $ and commas) |
| Grand_Total | Total PO amount (cleaned of $ and commas) |

## Troubleshooting

### Common Issues

1. **pdfplumber not found**
   - Ensure virtual environment is activated
   - Run `pip install pdfplumber`

2. **No PDF files found**
   - Verify PDFs are in the correct directory
   - Check file extensions are `.pdf` (case sensitive)

3. **Permission errors**
   - Ensure write permissions in the output directory
   - Close any CSV files that might be open in Excel/other programs

4. **Empty CSV output**
   - Check that PDFs contain the expected table structure
   - Verify PDF text is extractable (not scanned images)

### VSCode Python Issues

1. **Wrong Python interpreter**
   - Use Command Palette → "Python: Select Interpreter"
   - Choose the virtual environment interpreter

2. **Terminal not using virtual environment**
   - Check `.vscode/settings.json` has correct configuration
   - Manually activate: `source venv/bin/activate`

## File Structure

```
PO Processing/
├── README.md
├── venv/                          # Virtual environment
├── All Shibaura PO/
│   ├── extractor.py              # Main extraction script
│   ├── fix_csv.py                # CSV correction utility
│   ├── *.pdf                     # PO PDF files to process
│   └── purchase_orders.csv       # Generated output
└── All Relli PO/                 # Other PO files
    └── *.pdf
```

## Notes

- The extractor processes all PDF files in the current directory when run
- Each run overwrites the previous `purchase_orders.csv` file
- Multi-line descriptions in PDFs are properly handled and preserved
- Currency symbols and commas are automatically cleaned from numeric fields
- The scripts are designed specifically for Shibaura PO document format
