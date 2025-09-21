#!/bin/bash

# Shibaura PO Data Extractor - Virtual Environment Setup Script
# This script creates, activates, and enters a Python virtual environment

set -e  # Exit on any error

# Configuration
VENV_NAME="venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check Python version
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed or not in PATH"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_status "Found Python $PYTHON_VERSION"
    
    # Check if Python version is 3.7 or higher
    if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 7) else 1)'; then
        print_success "Python version is compatible"
    else
        print_error "Python 3.7 or higher is required. Found: $PYTHON_VERSION"
        exit 1
    fi
}

# Function to create virtual environment
create_venv() {
    print_status "Creating virtual environment '$VENV_NAME'..."
    
    if python3 -m venv "$VENV_NAME"; then
        print_success "Virtual environment created successfully"
    else
        print_error "Failed to create virtual environment"
        exit 1
    fi
}

# Function to activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    
    if [ -f "$VENV_NAME/bin/activate" ]; then
        source "$VENV_NAME/bin/activate"
        print_success "Virtual environment activated"
    else
        print_error "Virtual environment activation script not found"
        exit 1
    fi
}

# Function to install requirements
install_requirements() {
    if [ -f "$REQUIREMENTS_FILE" ]; then
        print_status "Installing requirements from requirements.txt..."
        
        # Upgrade pip first
        pip install --upgrade pip
        
        if pip install -r "$REQUIREMENTS_FILE"; then
            print_success "Requirements installed successfully!"
        else
            print_error "Failed to install some requirements"
            exit 1
        fi
    else
        print_warning "No requirements.txt found at $REQUIREMENTS_FILE"
        print_status "Skipping package installation"
    fi
}

# Function to verify installation
verify_installation() {
    print_status "Verifying installation..."
    
    # Check if pdfplumber is installed
    if python -c "import pdfplumber; print('pdfplumber version:', pdfplumber.__version__)" 2>/dev/null; then
        print_success "pdfplumber is installed and working"
    else
        print_error "pdfplumber is not properly installed"
        exit 1
    fi
}

# Function to display usage information
show_usage() {
    echo ""
    print_success "Setup complete! Here's how to use the extractor:"
    echo ""
    echo "1. Place your Shibaura PO PDF files in the '../Allpos/' directory"
    echo "2. Run the extractor:"
    echo "   python extractor.py"
    echo ""
    echo "3. Check the output in 'purchase_orders.csv'"
    echo ""
    echo "To deactivate the virtual environment later, run: deactivate"
    echo "To reactivate it, run: source $VENV_NAME/bin/activate"
    echo ""
}

# Main execution
main() {
    echo "=========================================="
    echo "  Shibaura PO Data Extractor Setup"
    echo "=========================================="
    echo ""
    
    # Change to script directory
    cd "$SCRIPT_DIR"
    
    # Check Python installation
    check_python
    
    # Check if virtual environment already exists
    if [ -d "$VENV_NAME" ]; then
        print_warning "Virtual environment '$VENV_NAME' already exists"
        
        # Ask user if they want to recreate it
        read -p "Do you want to recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Removing existing virtual environment..."
            rm -rf "$VENV_NAME"
            create_venv
        else
            print_status "Using existing virtual environment"
        fi
    else
        create_venv
    fi
    
    # Activate virtual environment
    activate_venv
    
    # Install requirements
    install_requirements
    
    # Verify installation
    verify_installation
    
    # Show usage information
    show_usage
    
    print_success "Virtual environment is ready!"
    print_status "Python path: $(which python)"
    print_status "Working directory: $(pwd)"
    
    # Start a new shell with the virtual environment activated
    print_status "Starting new shell with virtual environment activated..."
    echo "Type 'exit' to leave this environment"
    exec "$SHELL"
}

# Run main function
main "$@"
