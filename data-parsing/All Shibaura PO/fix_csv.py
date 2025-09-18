import sys
import os
import csv

def fix_csv(input_file):
    # Read the input file first to get all lines
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    # Process the lines
    result = []
    stored_line = None
    stored_line_number = None
    
    for i, line in enumerate(lines):
        # If we have a stored line and this line ends with ]
        if stored_line is not None and line.strip().endswith(']'):
            # Split the current line by comma
            current_parts = line.strip().split(',')
            # Get the bracket ending part
            bracket_end = current_parts[0]  # Assuming it's in the first column
            
            # Split the stored line by comma
            stored_parts = stored_line.split(',')
            # Find the column with the open bracket
            for j, part in enumerate(stored_parts):
                if '[' in part and ']' not in part:
                    # Combine the broken bracket parts
                    stored_parts[j] = f'{part.strip()} {bracket_end}'
                    break
            
            # Reconstruct the line
            result.append(','.join(stored_parts))
            stored_line = None
        # If this line has [ but no ]
        elif '[' in line and ']' not in line:
            stored_line = line.rstrip()
        # Normal line
        else:
            if not (stored_line is not None and line.strip().endswith(']')):
                result.append(line.rstrip())
    
    # Create output filename
    output_file = input_file.replace('.csv', '_adjusted.csv')
    
    # Write the result
    with open(output_file, 'w', newline='') as f:
        f.write('\n'.join(result))
    
    print(f"Processed file saved as: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_csv.py input.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f"Error: File {input_file} not found")
        sys.exit(1)
    
    fix_csv(input_file)