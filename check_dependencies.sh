#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if Python3 is installed
if ! command_exists python3; then
    echo "Python3 is not installed."
    echo "Please install Python3 using one of the following commands:"
    echo "  - On macOS (with Homebrew): brew install python3"
    echo "  - On Ubuntu/Debian: sudo apt update && sudo apt install python3"
    echo "  - On CentOS/Fedora: sudo yum install python3"
    exit 1
fi

# Check Python version (requires at least 3.6)
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.6"

version_lt() {
    # Compares two version strings; returns 0 (true) if $1 < $2
    [ "$(printf '%s\n' "$@" | sort -V | head -n 1)" != "$2" ]
}

if version_lt "$PYTHON_VERSION" "$required_version"; then
    echo "Your Python version is $PYTHON_VERSION which is less than the required $required_version."
    echo "To upgrade Python:"
    echo "  - On macOS with Homebrew, try: brew install python3   OR   brew upgrade python3"
    echo "  - On Ubuntu/Debian, try: sudo apt update && sudo apt install python3.8"
    echo "  - On CentOS/Fedora, try: sudo yum install python38"
    echo "Once upgraded, create a virtual environment using:"
    echo "  python3 -m venv venv"
    echo "Then activate it:"
    echo "  source venv/bin/activate"
    echo "Finally, upgrade pip and install dependencies:"
    echo "  pip install --upgrade pip"
    echo "  pip install requests"
    exit 1
fi

# Check if running inside a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "You are not running this script inside a virtual environment."
    echo "It is recommended to use a virtual environment. To create one, run:"
    echo "  python3 -m venv venv"
    echo "Then activate it:"
    echo "  source venv/bin/activate"
    echo "After activation, upgrade pip and install requests:"
    echo "  pip install --upgrade pip"
    echo "  pip install requests"
    exit 1
fi

# Check if pip is installed
if ! command_exists pip; then
    echo "pip is not installed. Installing pip..."
    python3 -m ensurepip --upgrade
fi

echo "Upgrading pip to the latest version..."
pip install --upgrade pip

# Check if requests module is installed; if not, try installing it
if ! python3 -c "import requests" 2>/dev/null; then
    echo "Module 'requests' is not installed. Attempting to install..."
    # Try installing the module in the user directory.
    if ! pip install --user requests; then
        echo "Automatic installation failed."
        echo "If you are using a system where Python is externally managed (e.g., Homebrew on macOS),"
        echo "please create a virtual environment and install dependencies manually:"
        echo "  python3 -m venv venv"
        echo "  source venv/bin/activate"
        echo "  pip install --upgrade pip"
        echo "  pip install requests"
        exit 1
    fi
    echo "Module 'requests' has been installed successfully."
else
    echo "Module 'requests' is already installed."
fi

echo "All dependencies are met."
