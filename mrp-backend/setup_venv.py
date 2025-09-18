#!/usr/bin/env python3
"""
Setup script for MRP Backend virtual environment
"""
import os
import sys
import subprocess
import venv
from pathlib import Path

def create_venv():
    """Create virtual environment"""
    venv_path = Path("venv")
    if venv_path.exists():
        print("Virtual environment already exists.")
        return venv_path

    print("Creating virtual environment...")
    venv.create(venv_path, with_pip=True)
    print(f"Virtual environment created at: {venv_path}")
    return venv_path

def install_requirements(venv_path):
    """Install requirements in virtual environment"""
    pip_path = venv_path / "Scripts" / "pip" if os.name == 'nt' else venv_path / "bin" / "pip"

    print("Installing requirements...")
    try:
        subprocess.check_call([
            str(pip_path), "install", "-r", "requirements.txt"
        ])
        print("Requirements installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install requirements: {e}")
        return False
    return True

def create_activation_script():
    """Create activation script for easy venv activation"""
    if os.name == 'nt':  # Windows
        script_content = """
@echo off
echo Activating MRP Backend virtual environment...
call venv\\Scripts\\activate.bat
echo Virtual environment activated. You can now run the backend with: python app.py
cmd /k
"""
        script_name = "activate_venv.bat"
    else:  # Unix-like
        script_content = """
#!/bin/bash
echo "Activating MRP Backend virtual environment..."
source venv/bin/activate
echo "Virtual environment activated. You can now run the backend with: python app.py"
exec $SHELL
"""
        script_name = "activate_venv.sh"

    with open(script_name, 'w') as f:
        f.write(script_content.strip())

    if os.name != 'nt':
        os.chmod(script_name, 0o755)

    print(f"Created activation script: {script_name}")

def main():
    """Main setup function"""
    print("Setting up MRP Backend development environment...")

    # Check if requirements.txt exists
    if not Path("requirements.txt").exists():
        print("Error: requirements.txt not found. Please ensure you're in the mrp-backend directory.")
        sys.exit(1)

    # Create virtual environment
    venv_path = create_venv()

    # Install requirements
    if not install_requirements(venv_path):
        sys.exit(1)

    # Create activation script
    create_activation_script()

    print("\nSetup complete!")
    print("To activate the virtual environment:")
    if os.name == 'nt':
        print("  Run: activate_venv.bat")
    else:
        print("  Run: source activate_venv.sh")
    print("Then run the backend with: python app.py")

if __name__ == "__main__":
    main()
