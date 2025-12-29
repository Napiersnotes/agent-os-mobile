#!/usr/bin/env python3
"""
Setup script for tests - creates necessary structure
"""
import os
import sys

def setup_test_environment():
    """Setup test environment"""
    print("Setting up test environment...")
    
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Create __init__.py files if they don't exist
    init_files = [
        "__init__.py",
        "tests/__init__.py"
    ]
    
    for init_file in init_files:
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("# Package initialization\n")
            print(f"Created {init_file}")
    
    print("Test environment setup complete!")

if __name__ == "__main__":
    setup_test_environment()
