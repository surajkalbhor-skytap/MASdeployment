# MAS Deployment Automation

This repository contains two main scripts that work together to automate the deployment of MAS templates across regions in Skytap Cloud:

- **MASdeployInterRegion.py**:  
  The main script that orchestrates the process of creating, copying, and deploying MAS templates between source and destination VMs/environments. 
  It handles both same-region and inter-region scenarios and logs all operations into a log file (and an accompanying JSON iteration file).

- **check_dependencies.sh**:  
  A shell script that checks whether all required dependencies are installed. 
  It first checks for Python 3.6 or higher, verifies that you are running inside a virtual environment, and ensures that `pip` and the `requests` module are installed and up-to-date.
  
**Note:**  
*The script will list available commands for upgrading/installing Python and for creating/activating a virtual environment if it detects any missing prerequisites. 
  However, it does not guarantee that all prerequisites will be installed automatically—if installation fails (for example, due to your system being externally managed), you must install them manually as described in the output.*

## Prerequisites
Before running the main deployment script, please ensure you have the following:
- **Python 3.6 or higher**  
  You can check your Python version using:
  ```bash
  python3 --version
If your version is less than 3.6, follow the instructions provided by check_dependencies.sh to upgrade Python.

- **A Virtual Environment**
It is highly recommended to run the project in a virtual environment. If you haven't set one up, use:
python3 -m venv venv
source venv/bin/activate

- **Required Python Libraries:**
This project requires the requests module. The check_dependencies.sh script will help verify this and upgrade pip and install requests if needed. If automatic installation fails, please follow its instructions and install them manually.


## Git
**1. Clone the Repository**
Open your terminal and run:
git clone https://github.com/your_username/MASdeployment.git
cd MASdeployment


## How to Use

**1. Install Dependencies**

Before running the main script, run the dependency checker:
./check_dependencies.sh

This script will:
- Check if Python 3.6+ is installed.
- Verify that you are running inside a virtual environment.
- Check and upgrade pip and install requests.

Important:
If the dependency checker fails to install any package due to an externally managed environment (common on macOS), it will provide instructions on how to create a virtual environment and manually install the required packages.


**2. Run the Main Deployment Script**

For a new MAS deployment, run:
python3 MASdeployInterRegion.py
Follow the on-screen prompts:

For a new deployment, select option 1.
For resuming a pending deployment (in case of inter-region deployment), select option2 and provide the iteration number as instructed by the script.

**3. Reading the Logs**

All operations performed by the script are logged in a file saved in the logs directory. The log file and the iteration file share the same base filename (a UTC timestamp) and are created automatically. You can review the log for details about:
VM details and configuration IDs.
MAS groups attached or intended for deployment.
Deployment operations and any errors that occurred.
For example, if the log file is named 20251122075237.log, the corresponding iteration file will be named ~20251122075237.json. the last one or two digits may change depending on teh timestamp both the files have been created.

**4. Updating the Repository**

To update your local copy with the latest changes:

Navigate to your project directory.
Run: ``` git pull ```

If you have any local modifications to files, either commit or stash them before pulling (see Git’s documentation on handling merge conflicts).

If you encounter errors like:
error: Your local changes to the following files would be overwritten by merge:
    check_dependencies.sh

Please stash your local changes before running git pull.

**Dependency Issues:**
If check_dependencies.sh instructs you to manually install dependencies, follow the printed instructions to create a virtual environment and use pip (or pipx) to install missing packages.

**Contributing**
Feel free to fork this repository and submit pull requests if you have suggestions or improvements. Make sure to update tests as appropriate.

**Skytap Support**
