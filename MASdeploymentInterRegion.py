#!/usr/bin/env python3
import requests
import json
import base64
import time
import os
import sys
from datetime import datetime
import logging

# -------------------------------------------
# Logging setup and directory creation.
# -------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(script_dir, "logs")
os.makedirs(log_dir, exist_ok=True)
# Use the current UTC timestamp as the base name for both log and iteration files.
iteration_number = datetime.utcnow().strftime("%Y%m%d%H%M%S")
log_file_path = os.path.join(log_dir, f"{iteration_number}.log")
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s: %(message)s",
                              datefmt="%Y-%m-%dT%H:%M:%SZ")
fh = logging.FileHandler(log_file_path)
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)

# -------------------------------------------
# Load credentials from file.
# -------------------------------------------
cred_file = os.path.join(script_dir, "credentials.json")
if not os.path.exists(cred_file):
    logger.error("Credentials file 'credentials.json' not found in script directory.")
    sys.exit(1)
with open(cred_file, 'r') as f:
    creds = json.load(f)
username = creds.get("username")
token = creds.get("token")
if not username or not token:
    logger.error("Username or token not found in credentials file.")
    sys.exit(1)

# -------------------------------------------
# Global configuration.
# -------------------------------------------
headers = {
    "Authorization": f"Basic {base64.b64encode(f'{username}:{token}'.encode('utf-8')).decode('utf-8')}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}
BASE_URL = "https://cloud.skytap.com"

# The iteration file is saved in the same logs directory with the same base name.
def get_iteration_filepath(iter_num):
    return os.path.join(log_dir, f"{iter_num}.json")

# -------------------------------------------
# Utility functions.
# -------------------------------------------
def wait(seconds):
    time.sleep(seconds)

def get_vm_details(vm_id):
    url = f"{BASE_URL}/vms/{vm_id}.json"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        try:
            return resp.json()
        except Exception as e:
            logger.error("Error decoding JSON for VM %s: %s", vm_id, e)
            return None
    else:
        logger.error("Failed to get details for VM %s: %s", vm_id, resp.status_code)
        return None

def extract_configuration_id(vm_payload):
    configuration_url = vm_payload.get("configuration_url", "")
    return configuration_url.rstrip("/").split("/")[-1]

def get_region(configuration_id):
    url = f"{BASE_URL}/configurations/{configuration_id}.json"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        try:
            return resp.json().get("region", "")
        except Exception as e:
            logger.error("Error decoding JSON for configuration %s: %s", configuration_id, e)
            return None
    else:
        logger.error("Failed to get region for configuration %s: %s", configuration_id, resp.status_code)
        return None

def extract_mas_groups(vm_payload):
    mas_data = vm_payload.get("multi_attach_storage_groups", [])
    mas_ids = []
    if isinstance(mas_data, dict):
        for group in mas_data.values():
            if isinstance(group, dict):
                mas_id = group.get("id")
                if mas_id:
                    mas_ids.append(mas_id)
    elif isinstance(mas_data, list):
        for group in mas_data:
            if isinstance(group, dict):
                mas_id = group.get("id")
                if mas_id:
                    mas_ids.append(mas_id)
    else:
        logger.warning("MAS groups data not in expected format.")
    return mas_ids

def get_configuration_mas_groups(configuration_id):
    url = f"{BASE_URL}/configurations/{configuration_id}?section=multi_attach_storage.json"
    logger.info("Fetching MAS groups from destination configuration %s.", configuration_id)
    resp = requests.get(url, headers=headers)
    new_mas_ids = []
    try:
        mas_groups = resp.json().get("multi_attach_storage_groups", {})
        for group in mas_groups.values() if isinstance(mas_groups, dict) else mas_groups:
            mas_id = group.get("id")
            if mas_id:
                new_mas_ids.append(mas_id)
    except Exception as e:
        logger.error("Error decoding MAS groups JSON: %s. Raw response: %s", e, resp.text)
    logger.info("MAS groups in destination configuration %s: %s", configuration_id, new_mas_ids)
    return new_mas_ids

def delete_destination_mas_groups(vm_id, mas_ids, attached_mas_ids):
    """Detach only MAS groups that are attached to the destination VM."""
    for mas_id in mas_ids:
        if mas_id in attached_mas_ids:
            url = f"{BASE_URL}/multi_attach_storage_groups/{mas_id}/vm_attachments.json"
            payload = {"vm_ids": [vm_id]}
            logger.info("Detaching MAS group %s from destination VM %s.", mas_id, vm_id)
            resp = requests.delete(url, headers=headers, json=payload)
            if resp.status_code == 200:
                logger.info("Successfully detached MAS group %s from VM %s.", mas_id, vm_id)
            else:
                logger.error("Failed to detach MAS group %s; status: %s.", mas_id, resp.status_code)
        else:
            logger.info("MAS group %s is not attached to VM %s; skipping detachment.", mas_id, vm_id)

def delete_mas_group(mas_id):
    url = f"{BASE_URL}/multi_attach_storage_groups/{mas_id}"
    logger.info("Deleting MAS group %s from environment.", mas_id)
    resp = requests.delete(url, headers=headers)
    if resp.status_code == 200:
        logger.info("MAS group %s deleted successfully.", mas_id)
    else:
        logger.error("Failed to delete MAS group %s; status: %s.", mas_id, resp.status_code)

def create_source_mas_template(config_id, source_mas_ids):
    url = f"{BASE_URL}/templates.json"
    payload = {
        "configuration_id": config_id,
        "vm_instance_multiselect": [],
        "mas_group_multiselect": source_mas_ids
    }
    logger.info("Creating MAS template for configuration %s with source MAS groups: %s", config_id, source_mas_ids)
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code in [200, 201]:
        template_id = resp.json().get("id")
        logger.info("MAS template created. Template ID: %s", template_id)
        return template_id
    else:
        logger.error("MAS template creation failed; status: %s.", resp.status_code)
        return None

def copy_template_to_region(template_id, target_region):
    url = f"{BASE_URL}/templates.json"
    payload = {"template_id": template_id, "resource_mapping": {}, "target_region": target_region}
    logger.info("Copying template %s to region %s.", template_id, target_region)
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code in [200, 201]:
        dest_template_id = resp.json().get("id")
        logger.info("Template copy initiated. Destination Template ID: %s", dest_template_id)
        return dest_template_id
    else:
        logger.error("Template copy initiation failed; status: %s.", resp.status_code)
        return None

def check_template_status(template_id):
    url = f"{BASE_URL}/v2/templates/{template_id}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        if resp.json().get("busy", None) is None:
            logger.info("Template %s is ready and not busy.", template_id)
            return True
        else:
            logger.error("Template %s is busy. Please retry later.", template_id)
            return False
    else:
        logger.error("Failed to retrieve template status; status: %s.", resp.status_code)
        return False

def deploy_mas_template(dest_config_id, template_id):
    url = f"{BASE_URL}/configurations/{dest_config_id}.json"
    payload = {"merge_configuration": template_id}
    logger.info("Deploying MAS template %s to destination configuration %s.", template_id, dest_config_id)
    resp = requests.put(url, headers=headers, json=payload)
    if resp.status_code == 200:
        logger.info("MAS template deployed to configuration %s.", dest_config_id)
    else:
        logger.error("Deployment failed; status: %s.", resp.status_code)
    return resp

def delete_template(template_id):
    url = f"{BASE_URL}/templates/{template_id}.json"
    logger.info("Deleting MAS template %s.", template_id)
    resp = requests.delete(url, headers=headers)
    if resp.status_code == 200:
        logger.info("MAS template %s deleted.", template_id)
    else:
        logger.error("Failed to delete MAS template %s; status: %s.", template_id, resp.status_code)

def attach_mas_to_vm(vm_id, mas_ids):
    for mas_id in mas_ids:
        url = f"{BASE_URL}/multi_attach_storage_groups/{mas_id}/vm_attachments.json"
        payload = {"vm_ids": [vm_id]}
        logger.info("Attaching MAS group %s to destination VM %s.", mas_id, vm_id)
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code == 200:
            logger.info("MAS group %s attached to VM %s.", mas_id, vm_id)
        else:
            logger.error("Failed to attach MAS group %s; status: %s.", mas_id, resp.status_code)

def poll_vm_shutdown(vm_id, max_wait_sec=900, interval=30):
    logger.info("Waiting for VM %s shutdown (up to %s seconds).", vm_id, max_wait_sec)
    elapsed = 0
    while elapsed < max_wait_sec:
        details = get_vm_details(vm_id)
        if details and details.get("runstate", "").lower() in ["stopped", "powered off"]:
            logger.info("VM %s is shutdown.", vm_id)
            return True
        time.sleep(interval)
        elapsed += interval
    logger.error("VM %s did not shutdown within %s seconds.", vm_id, max_wait_sec)
    return False

def update_vm_runstate(config_id, vm_id, state):
    url = f"{BASE_URL}/v2/configurations/{config_id}/vms/{vm_id}.json"
    logger.info("Updating VM %s in configuration %s to '%s'.", vm_id, config_id, state)
    payload = {"runstate": state}
    resp = requests.put(url, headers=headers, json=payload)
    if resp.status_code == 200:
        logger.info("VM %s runstate updated to '%s'.", vm_id, state)
    else:
        logger.error("Failed to update VM %s runstate; status: %s.", vm_id, resp.status_code)
    return resp

def retry_step(func, *args):
    while True:
        response = func(*args)
        if isinstance(response, (dict, list, bool, str)) or (response and response.status_code == 200):
            return response
        logger.error("Step failed. Retry? (Y/y or N/n)")
        start = time.time()
        while time.time() - start < 300:
            user_input = input("Enter Y/y to retry or N/n to exit: ").strip().lower()
            if user_input in ["y", "n"]:
                break
        else:
            logger.error("No response within 5 minutes. Exiting.")
            sys.exit(1)
        if user_input == "n":
            logger.info("User chose not to retry. Exiting.")
            sys.exit(1)

def save_iteration_data(iter_num, data):
    path = os.path.join(log_dir, f"{iter_num}.json")
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
    logger.info("Iteration file saved to: %s", path)

def load_iteration_data(iter_num):
    path = os.path.join(log_dir, f"{iter_num}.json")
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None

# -------------------------------------------
# Main routine.
# -------------------------------------------
def main():
    activity_type = input("Select activity type:\n1. New MAS deployment\n2. Resume pending MAS deployment\nEnter 1 or 2: ").strip()
    
    if activity_type == "1":
        iter_num = iteration_number  
        iteration_data = {"iteration_number": iter_num, "timestamp": datetime.utcnow().isoformat()}
        
        source_vm_id = input("Enter the Source VM ID: ").strip()
        destination_vm_id = input("Enter the Destination VM ID: ").strip()
        iteration_data.update({"source_vm_id": source_vm_id, "destination_vm_id": destination_vm_id})
        logger.info("Source VM ID: %s, Destination VM ID: %s", source_vm_id, destination_vm_id)
        
        source_vm_payload = retry_step(get_vm_details, source_vm_id); wait(5)
        destination_vm_payload = retry_step(get_vm_details, destination_vm_id); wait(5)
        if not source_vm_payload or not destination_vm_payload:
            logger.error("Failed to get VM details. Exiting.")
            sys.exit(1)
        
        source_config_id = extract_configuration_id(source_vm_payload)
        dest_config_id = extract_configuration_id(destination_vm_payload)
        iteration_data.update({"source_config_id": source_config_id, "dest_config_id": dest_config_id})
        logger.info("Source Config ID: %s", source_config_id)
        logger.info("Destination Config ID: %s", dest_config_id); wait(5)
        
        source_region = retry_step(get_region, source_config_id); wait(5)
        dest_region = retry_step(get_region, dest_config_id); wait(5)
        iteration_data.update({"source_region": source_region, "dest_region": dest_region})
        logger.info("Source Region: %s", source_region)
        logger.info("Destination Region: %s", dest_region)
        same_region = (source_region == dest_region)
        
        if same_region:
            logger.info("Same-region detected; destination VM shutdown will occur after template creation.")
        else:
            logger.info("Different-region detected; destination VM remains running until resumed deployment.")
        
        dest_old_mas = extract_mas_groups(destination_vm_payload)
        iteration_data.update({"dest_vm_mas": dest_old_mas})
        logger.info("Destination VM MAS groups: %s", dest_old_mas); wait(5)
        
        source_mas = extract_mas_groups(source_vm_payload)
        iteration_data.update({"source_vm_mas": source_mas})
        logger.info("Source VM MAS groups: %s", source_mas); wait(5)
        
        old_config_mas = retry_step(get_configuration_mas_groups, dest_config_id); wait(5)
        iteration_data.update({"old_config_mas": old_config_mas})
        logger.info("Config MAS groups before deployment: %s", old_config_mas)
        
        source_template = retry_step(create_source_mas_template, source_config_id, source_mas); wait(5)
        iteration_data.update({"source_template": source_template})
        if not source_template:
            logger.error("Template creation failed. Exiting.")
            sys.exit(1)
        
        if same_region:
            logger.info("Same-region: Shutting down destination VM after template creation.")
            shutdown_resp = retry_step(update_vm_runstate, dest_config_id, destination_vm_id, "stopped")
            wait(5)
            if not shutdown_resp or shutdown_resp.status_code != 200 or not retry_step(poll_vm_shutdown, destination_vm_id):
                logger.error("Failed to shutdown destination VM. Exiting.")
                sys.exit(1)
        
        destination_template = None
        if not same_region:
            logger.info("Different-region: Initiating inter-region template copy...")
            destination_template = retry_step(copy_template_to_region, source_template, dest_region)
            wait(5)
            if not destination_template:
                logger.error("Template copy initiation failed. Exiting.")
                sys.exit(1)
            iteration_data.update({"destination_template": destination_template})
            save_iteration_data(iter_num, iteration_data)
            logger.info("Template copy initiated; destination template ID is %s.", destination_template)
            logger.info("After template copy is complete, resume deployment using option 2 with iteration number %s.", iter_num)
            sys.exit(1)
        
        save_iteration_data(iter_num, iteration_data)
        
        # For same-region deployment, shut down has already been performed above.
        delete_destination_mas_groups(destination_vm_id, old_config_mas, dest_old_mas); wait(5)
        for mas in dest_old_mas:
            delete_mas_group(mas); wait(5)
        template_to_deploy = destination_template if destination_template else source_template
        retry_step(deploy_mas_template, dest_config_id, template_to_deploy); wait(5)
        logger.info("Waiting 15 seconds after MAS template deployment.")
        time.sleep(15)
        new_config_mas = retry_step(get_configuration_mas_groups, dest_config_id); wait(5)
        new_deployed = list(set(new_config_mas) - set(old_config_mas))
        logger.info("New MAS groups deployed: %s", new_deployed)
        attach_mas_to_vm(destination_vm_id, new_deployed); wait(5)
        delete_template(source_template); wait(5)
        if destination_template:
            delete_template(destination_template); wait(5)
        retry_step(update_vm_runstate, dest_config_id, destination_vm_id, "running"); wait(5)
        save_iteration_data(iter_num, iteration_data)
        logger.info("Script completed successfully.")
    
    elif activity_type == "2":
        iter_num = input("Enter iteration number: ").strip()
        data = load_iteration_data(iter_num)
        if not data:
            logger.error("Iteration %s not found. Start a new iteration.", iter_num)
            if input("Start new iteration? (Y/y): ").strip().lower() == "y":
                main()
            else:
                sys.exit(1)
        destination_template = data.get("destination_template")
        dest_config_id = data.get("dest_config_id")
        destination_vm_id = data.get("destination_vm_id")
        old_config_mas = data.get("old_config_mas")
        dest_old_mas = data.get("dest_vm_mas")
        source_template = data.get("source_template")
        
        if not retry_step(check_template_status, destination_template):
            logger.error("Template is busy or not fully copied. Please retry or start a new deployment.")
            sys.exit(1)
        logger.info("Waiting 15 seconds after template check.")
        time.sleep(15)
        
        logger.info("Shutting down destination VM before resuming deployment.")
        shutdown_resp = retry_step(update_vm_runstate, dest_config_id, destination_vm_id, "stopped")
        wait(5)
        if not shutdown_resp or shutdown_resp.status_code != 200 or not retry_step(poll_vm_shutdown, destination_vm_id):
            logger.error("Failed to shutdown destination VM. Exiting.")
            sys.exit(1)
        
        delete_destination_mas_groups(destination_vm_id, old_config_mas, dest_old_mas); wait(5)
        for mas in dest_old_mas:
            delete_mas_group(mas); wait(5)
        retry_step(deploy_mas_template, dest_config_id, destination_template); wait(5)
        logger.info("Waiting 15 seconds after MAS template deployment.")
        time.sleep(15)
        new_config_mas = retry_step(get_configuration_mas_groups, dest_config_id); wait(5)
        new_deployed = list(set(new_config_mas) - set(old_config_mas))
        logger.info("New MAS groups deployed: %s", new_deployed)
        attach_mas_to_vm(destination_vm_id, new_deployed); wait(5)
        delete_template(source_template); wait(5)
        delete_template(destination_template); wait(5)
        retry_step(update_vm_runstate, dest_config_id, destination_vm_id, "running"); wait(5)
        logger.info("Script completed successfully.")
    else:
        logger.error("Invalid selection. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    main()
