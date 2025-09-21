# Shibaura PO Data Extractor

This tool extracts purchase order data from Shibaura Machine Company PDF files and converts them to CSV format.

## Overview

This development environment has instructions for developing extractors effectively
- Isolate 1 of each unique style of invoice in individual PDFs
- Manually output and establish a benchmark output that is accurate
- Start AI on instructions.txt to tune the extractor for the PDFs in folder.

## Features

- **Multi-format support**: Handles different PDF layouts automatically
- **Robust extraction**: Uses multiple table extraction strategies
- **Data validation**: Validates dates, numbers, and line items
- **Clean output**: Removes metadata contamination and formats data consistently
- **Error handling**: Continues processing even if individual files fail

## Requirements

- Python 3.7+
- Virtual environment (recommended)
- Dependencies listed in `requirements.txt`

## Quick Start

### 1. Setup Environment

```bash
# Make the setup script executable and run it
chmod +x python_venv_setup.sh
./python_venv_setup.sh
```

This will:
- Create a Python virtual environment
- Install required dependencies
- Activate the environment

### 2. Prepare Your PDFs

Place your Shibaura PO PDF files in the current directory (same as extractor.py).

### 3. Run the Extractor

```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Run the extractor
python extractor.py
```

### 4. Check Results

The extracted data will be saved to `output.csv` in the same directory.

## Configuration

### Input Directory
By default, the script looks for PDF files in the current directory. To change this, modify the `input_dir` variable in `extractor.py`:

```python
input_dir = Path('./your-pdf-directory')
```

### Output File
By default, output is saved to `output.csv`. To change this, modify the `output_csv` variable:

```python
output_csv = 'your-output-file.csv'
```

## Testing

The `Examples` directory includes 4 test PDF files representing different formats:

1. **example-po-format1-1item.pdf**: Single item, Format 1
2. **example-po-format1-multi-lines.pdf**: Multiple items, Format 1  
3. **example-po-format-2-single.pdf**: Single item, Format 2
4. **example-po-format-2-multi-lines.pdf**: Multiple items, Format 2

To test the extractor with these files:

```bash
# Create a test directory and copy example files
mkdir test-run
cp example-po-*.pdf test-run/

# Modify extractor.py temporarily to point to test-run directory
# Then run the extractor
python extractor.py
```

## Troubleshooting

### Debug Mode

To see detailed extraction information, you can add debug prints to the `process_pdf` function in `extractor.py`.

## Technical Details

### Extraction Strategy

The extractor uses a multi-strategy approach:

1. **Pattern Recognition**: Multiple regex patterns for PO numbers, dates, and totals
2. **Table Detection**: Tries different table extraction methods (text-based, line-based, hybrid)
3. **Column Mapping**: Intelligent field detection based on content validation
4. **Data Cleaning**: Removes metadata contamination and standardizes formats

### Supported PDF Variations

- Different company headers (Toshiba vs Shibaura)
- Various date formats (MM/DD/YYYY, M/D/YYYY)
- Multiple table layouts
- Single and multi-line descriptions
- Different column arrangements

## Contributing

To improve the extractor:

1. Test with new PDF formats
2. Add additional validation rules
3. Enhance error handling
4. Optimize extraction performance

## License

This tool is part of the AMC MRP system.
