#!/usr/bin/env python3
"""
Development setup script
"""
import os
import sys

def setup_development_environment():
    """Setup development environment"""
    print("Setting up Agent OS Mobile development environment...")
    
    # Create necessary directories
    dirs = ["data", "logs", "migrations"]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"  ✅ Created directory: {d}")
    
    # Check Python version
    python_version = sys.version_info
    print(f"  ✅ Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Check for required files
    required_files = ["requirements.txt", "__init__.py", "models.py"]
    for f in required_files:
        if os.path.exists(f):
            print(f"  ✅ Found: {f}")
        else:
            print(f"  ⚠️  Missing: {f}")
    
    print("\n✅ Development environment setup complete!")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Run tests: python -m pytest tests/test_minimal.py")
    print("3. Start development server: uvicorn main:app --reload")

if __name__ == "__main__":
    setup_development_environment()
