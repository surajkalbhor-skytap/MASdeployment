#!/usr/bin/env python3
import sys
import subprocess

def check_python_version():
    if sys.version_info < (3, 6):
        sys.exit("Python 3.6 or higher is required.")

def check_module(module_name, package_name=None):
    try:
        __import__(module_name)
        print(f"Module '{module_name}' is installed.")
    except ImportError:
        print(f"Module '{module_name}' is not installed. Installing...")
        if not package_name:
            package_name = module_name
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"Module '{module_name}' has been installed.")

if __name__ == "__main__":
    check_python_version()
    # Only 'requests' is external; others are built-in.
    check_module("requests")
    print("All dependencies are met.")