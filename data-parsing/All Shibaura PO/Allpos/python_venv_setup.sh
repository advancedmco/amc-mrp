#!/bin/bash

# Set the virtual environment name (you can change this)
VENV_NAME="venv"

# Check if virtual environment already exists
if [ -d "$VENV_NAME" ]; then
    echo "Virtual environment '$VENV_NAME' already exists. Activating..."
    source "$VENV_NAME/bin/activate"
else
    echo "Creating virtual environment '$VENV_NAME'..."
    python3 -m venv "$VENV_NAME"
    
    # Check if venv creation was successful
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment"
        exit 1
    fi
    
    echo "Activating virtual environment..."
    source "$VENV_NAME/bin/activate"
    
    # Check if requirements.txt exists and install dependencies
    if [ -f "requirements.txt" ]; then
        echo "Installing requirements from requirements.txt..."
        pip install -r requirements.txt
        
        if [ $? -eq 0 ]; then
            echo "Requirements installed successfully!"
        else
            echo "Warning: Some requirements failed to install"
        fi
    else
        echo "No requirements.txt found, skipping package installation"
    fi
fi

echo "Virtual environment is now active!"
echo "Python path: $(which python)"
echo "To deactivate, run: deactivate"