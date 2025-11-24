#!/usr/bin/env python3
import sys
import subprocess

def check_python_version():
    if sys.version_info < (3, 6):
        sys.exit("Python 3.6 or higher is required.")

def check_module(module_name, package_name=None):
    try:
        __import__(module_name)
        print(f"Module '{module_name}' is already installed.")
    except ImportError:
        print(f"Module '{module_name}' is not installed. Attempting to install...")
        if not package_name:
            package_name = module_name
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", package_name])
            print(f"Module '{module_name}' installed successfully.")
        except subprocess.CalledProcessError as e:
            print("Automatic installation failed due to an externally-managed environment.")
            print("Please create a virtual environment and install dependencies manually:")
            print("   python3 -m venv venv")
            print("   source venv/bin/activate")
            print("   pip install requests")
            sys.exit(1)

if __name__ == "__main__":
    check_python_version()
    check_module("requests")
    print("All dependencies are met.")