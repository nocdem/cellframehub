import json
import os
import requests
import threading
import time
import subprocess
import socket
import psutil
import re
from datetime import datetime, timedelta
import socket

# Paths for the updater
LOCAL_MANIFEST = "/opt/cellframe-node/var/lib/plugins/hub/manifest.json"
REMOTE_MANIFEST_URL = "https://raw.githubusercontent.com/nocdem/cellframehub/refs/heads/main/plugin/manifest.json"
REMOTE_HUB_URL = "https://raw.githubusercontent.com/nocdem/cellframehub/refs/heads/main/plugin/hub.py"
PLUGIN_PATH = "/opt/cellframe-node/var/lib/plugins/hub/"

# Cached Data Storage
cached_data = {
    'hostname': socket.gethostname(),
    'our_node_address': None  # Store our node's address here
}
CLI = "/opt/cellframe-node/bin/cellframe-node-cli"  # Path to cellframe-node-cli binary
def init():
    t = threading.Thread(target=run_periodically, args=(30,))  # Start the periodic task every 30 minutes
    t.start()
    return 0
def deinit():
    #  deinitialization
    return 0
# Get service uptime
def getServiceUptime():
    try:
        for proc in psutil.process_iter(['pid', 'name', 'create_time']):
            if proc.info['name'] == "cellframe-node":
                uptime_seconds = time.time() - proc.info['create_time']
                return formatUptime(uptime_seconds)
        return "cellframe-node process not found"
    except Exception as e:
        return f"Error: {str(e)}"
# Format uptime in days, hours, minutes, and seconds
def formatUptime(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
# Get the node version
def getNodeVersion():
    try:
        result = subprocess.run([CLI, "version"], capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return result.stdout.strip().split()[-1]  # Extract the version part only
        else:
            return f"Error: {result.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"
# Fetch network names
def getNetworkNames():
    try:
        result = subprocess.run(
            [CLI, "net", "list"],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            networks = result.stdout.strip().split("\n")
            individual_networks = []
            for net in networks:
                if not net.startswith("networks:"):
                    individual_networks.extend([n.strip() for n in net.split(",") if n.strip()])
            print(f"Detected networks: {individual_networks}")
            return individual_networks
        else:
            print(f"Error running net list command: {result.stderr}")
            return []
    except Exception as e:
        print(f"Error: {str(e)}")
        return []
# Fetch network status for each network
def getNetworkStatus(network):
    try:
        result = subprocess.run(
            [CLI, "net", "get", "status", "-net", network],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            return parseNetworkStatus(result.stdout.strip())
        else:
            return f"Error running net get status command for {network}: {result.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"
# Parse network status output
def parseNetworkStatus(output):
    network_info = {}
    lines = output.splitlines()
    for i, line in enumerate(lines):
        if "current:" in line and "NET_STATE" in line:
            network_info['our_node_state'] = line.split(":")[1].strip()
        elif "target:" in line and "NET_STATE" in line:
            network_info['network_state'] = line.split(":")[1].strip()
        elif "main:" in line:
            block_height = lines[i + 3].split(":")[1].strip()
            sync_percent = lines[i + 4].split(":")[1].strip()
            main_status = lines[i + 1].split(":")[1].strip()
            network_info['block_height'] = block_height
            network_info['sync_percentage'] = sync_percent
            network_info['main_status'] = main_status
        elif "current_addr:" in line:
            node_address = line.split(":", 1)[1].strip()
            cached_data['our_node_address'] = node_address
            print(f"Detected node address: {cached_data['our_node_address']}")
    if not cached_data['our_node_address']:
        print("Warning: No node address detected in network status output.")
    return network_info
# Read network config file and return blocks_sign_cert and fee_addr
def readNetworkConfig(network):
    config_file = f"/opt/cellframe-node/etc/network/{network}.cfg"
    net_config = {}
    try:
        with open(config_file, "r") as file:
            text = file.read()
        # Extract blocks-sign-cert
        pattern_cert = r"^blocks-sign-cert=(.+)"
        cert_match = re.search(pattern_cert, text, re.MULTILINE)
        if cert_match:
            net_config['blocks_sign_cert'] = cert_match.group(1).strip()
        else:
            print(f"Warning: blocks-sign-cert not found in {network}.cfg")
        # Extract fee_addr
        pattern_fee = r"^fee_addr=(.+)"
        fee_match = re.search(pattern_fee, text, re.MULTILINE)
        if fee_match:
            net_config['fee_addr'] = fee_match.group(1).strip()
            print(f"Detected fee_addr: {net_config['fee_addr']}")  # Debugging statement
        else:
            print(f"Warning: fee_addr not found in {network}.cfg")
        return net_config
    except FileNotFoundError:
        print(f"Error: Config file for network {network} not found.")
        return None
    except Exception as e:
        print(f"Error reading {network}.cfg: {str(e)}")
        return None
# Get stake info
def getStakeInfo(network, blocks_sign_cert):
    if blocks_sign_cert:
        try:
            result = subprocess.run(
                [CLI, "srv_stake", "list", "keys", "-net", network, "-cert", blocks_sign_cert],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                return parseStakeInfo(result.stdout.strip())
            else:
                return f"Error running srv_stake list keys command: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"
    return None
# Parse the stake information output

def parseStakeInfo(output):
    stake_info = {}
    lines = output.splitlines()

    # Initialize default values to ensure keys are always set
    stake_info['stake_value'] = "0"
    stake_info['sovereign_addr'] = "N/A"
    stake_info['sovereign_tax'] = "0"

    # Iterate through each line and search for the relevant keys
    for line in lines:
        if "stake_value:" in line:
            stake_info['stake_value'] = line.split(":", 1)[1].strip()
        elif "sovereign_addr:" in line:
            stake_info['sovereign_addr'] = line.split(":", 1)[1].strip()
        elif "sovereign_tax:" in line:
            stake_info['sovereign_tax'] = line.split(":", 1)[1].strip()

    return stake_info

# Fetch rewards for the last 30 days
def fetch_tx_history(fee_addr):
    result = subprocess.run([CLI, "tx_history", "-addr", fee_addr], capture_output=True, text=True)
    return result.stdout
# Extract block reward transactions
def get_block_reward_transactions(history):
    reward_transactions = []
    lines = history.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if "status: ACCEPTED" in line:
            for j in range(i, i + 35):
                if j < len(lines) and "service: block_reward" in lines[j]:
                    reward_transactions.append("\n".join(lines[i:i + 35]))
                    break
        i += 1
    return reward_transactions
# Filter transactions by day
def filter_transactions_by_day(transactions, day):
    daily_transactions = []
    for transaction in transactions:
        match = re.search(r'tx_created:\s*([\w, :]+)', transaction)
        if match:
            tx_date_str = match.group(1).strip()
            try:
                tx_date = datetime.strptime(tx_date_str, "%a, %d %b %Y %H:%M:%S").strftime("%a, %d %b %Y")
                if tx_date == day:
                    daily_transactions.append(transaction)
            except ValueError as e:
                print(f"Error parsing date: {tx_date_str} - {e}")
    return daily_transactions
# Filter for reward collecting
def filter_for_reward_collecting(transactions):
    reward_transactions = []
    for transaction in transactions:
        lines = transaction.splitlines()
        for i, line in enumerate(lines):
            if "source_address: reward collecting" in line:
                reward_transactions.append("\n".join(lines[max(0, i-4):i+4]))
    return reward_transactions
# Extract rewards
def extract_rewards(transactions):
    total_reward = 0
    for transaction in transactions:
        match = re.search(r'recv_coins:\s*([\d.]+)', transaction)
        if match:
            total_reward += float(match.group(1))
    return total_reward
# Calculate rewards for a specific day
def calculate_rewards_for_day(history, day):
    block_reward_transactions = get_block_reward_transactions(history)
    daily_transactions = filter_transactions_by_day(block_reward_transactions, day)
    reward_transactions = filter_for_reward_collecting(daily_transactions)
    return extract_rewards(reward_transactions)
# Calculate rewards for the last 30 days
def calculate_rewards(fee_addr):
    history = fetch_tx_history(fee_addr)
    rewards = {}
    for i in range(30):
        day = (datetime.now() - timedelta(days=i)).strftime("%a, %d %b %Y")
        rewards[day] = calculate_rewards_for_day(history, day)
    return rewards

# Calculate moving averages (MA7 and MA30)
def calculate_moving_averages(rewards, stake_value, sovereign_tax):
    # Convert the sovereign_tax percentage to a decimal
    sovereign_tax_decimal = float(sovereign_tax) / 100

    # Calculate the multiplier to get 100% of the income
    total_income_multiplier = 1 / (1 - sovereign_tax_decimal)

    # Adjust rewards to represent 100% of the income
    adjusted_rewards = {day: value * total_income_multiplier for day, value in rewards.items()}

    # Convert the adjusted rewards to a list of values
    reward_values = list(adjusted_rewards.values())

    # Calculate MA7 (for the last 7 days)
    ma7 = sum(reward_values[:7]) / 7 if len(reward_values) >= 7 else 0

    # Calculate MA30 (for the last 30 days)
    ma30 = sum(reward_values[:30]) / 30 if len(reward_values) >= 30 else 0

    # Deposited amount is the stake value multiplied by 1000
    deposited_amount = stake_value * 1000

    # Calculate APY based on MA7 and MA30
    ma7_apy = (ma7 * 365 / deposited_amount) * 100 if deposited_amount > 0 else 0
    ma30_apy = (ma30 * 365 / deposited_amount) * 100 if deposited_amount > 0 else 0

    return ma7, ma30, ma7_apy, ma30_apy, adjusted_rewards


def collectAllData():
    collected_data = {
        "networks": {}
    }
    # Collect system information
    collected_data['hostname'] = cached_data['hostname']
    collected_data['service_uptime'] = getServiceUptime()
    collected_data['node_version'] = getNodeVersion()
    collected_data['timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")

    # Fetch all network data
    networks = getNetworkNames()
    if isinstance(networks, list):
        for network in networks:
            print(f"Processing network: {network}")
            network_status = getNetworkStatus(network)
            # Read network config and fetch rewards
            network_config = readNetworkConfig(network)

            if isinstance(network_config, dict):
                blocks_sign_cert = network_config.get('blocks_sign_cert')
                if not blocks_sign_cert:
                    print(f"Warning: No blocks-sign-cert found for network {network}. Skipping this network.")
                    continue  # Skip this network

                # Process stake information
                stake_info = getStakeInfo(network, blocks_sign_cert)
                if isinstance(stake_info, dict):
                    # Include stake value and sovereign address/tax if available
                    collected_data['networks'][network] = network_status
                    collected_data['networks'][network].update(stake_info)

                    if 'sovereign_addr' in stake_info and 'sovereign_tax' in stake_info:
                        collected_data['networks'][network]['sovereign_addr_info'] = {
                            "sovereign_addr": stake_info['sovereign_addr'],
                            "sovereign_tax": stake_info['sovereign_tax']
                        }
                    else:
                        print(f"No sovereign_addr_info found for network {network}")
                        collected_data['networks'][network]['sovereign_addr_info'] = None

                # Check fee address and rewards
                fee_addr = network_config.get('fee_addr')
                if fee_addr:
                    # Calculate rewards and adjusted values
                    rewards = calculate_rewards(fee_addr)
                    ma7, ma30, ma7_apy, ma30_apy, adjusted_rewards = calculate_moving_averages(
                        rewards, float(stake_info['stake_value']), stake_info['sovereign_tax']
                    )

                    # Write adjusted values to the collected data
                    collected_data['networks'][network]['fee_addr_info'] = {
                        "fee_addr": fee_addr,
                        "ma7": {
                            "date": datetime.now().strftime("%a, %d %b %Y"),
                            "value": ma7,
                            "apy": ma7_apy
                        },
                        "ma30": {
                            "date": datetime.now().strftime("%a, %d %b %Y"),
                            "value": ma30,
                            "apy": ma30_apy
                        },
                        "rewards": adjusted_rewards
                    }
                else:
                    print(f"Warning: No fee_addr found for network {network}")
                    collected_data['networks'][network]['fee_addr_info'] = None
            else:
                print(f"Warning: No config found for network {network}")
                continue  # Skip this network as well if no config is found
    else:
        print("No networks found.")

    # Ensure node address is available
    if cached_data['our_node_address']:
        print(f"Using node address: {cached_data['our_node_address']}")
        collected_data['node_addr'] = cached_data['our_node_address']
    else:
        collected_data['node_addr'] = "Node address not available"
        print("Warning: Node address could not be detected.")

    return collected_data


def generateFinalOutput():
    collected_data = collectAllData()
    final_data = {
        "node_addr": collected_data['node_addr'],
        "hostname": collected_data['hostname'],
        "service_uptime": collected_data['service_uptime'],
        "node_version": collected_data['node_version'],
        "timestamp": collected_data['timestamp'],
        "network_info": {
            network: {
                "our_node_state": collected_data['networks'][network].get("our_node_state"),
                "network_state": collected_data['networks'][network].get("network_state"),
                "main_status": collected_data['networks'][network].get("main_status"),
                "sync_percentage": collected_data['networks'][network].get("sync_percentage"),
                "block_height": collected_data['networks'][network].get("block_height"),
                "stake_value": collected_data['networks'][network].get("stake_value"),
                "sovereign_addr_info": collected_data['networks'][network].get("sovereign_addr_info"),
                "fee_addr_info": collected_data['networks'][network].get("fee_addr_info")
            } for network in collected_data['networks']
        }
    }
    # Write to output.json
    with open("/opt/cellframe-node/var/lib/plugins/hub/output.json", "w") as f:
        json.dump(final_data, f, indent=4)
    print("Normal output saved to output.json")
# Write data to GDB
def write_to_gdb(group_name, key, value):
    try:
        result = subprocess.run(
            [CLI, "global_db", "write", "-group", group_name, "-key", key, "-value", str(value)],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"Successfully wrote {key}: {value} to {group_name}")
        else:
            print(f"Error writing {key}: {value} to {group_name}: {result.stderr}")
    except Exception as e:
        print(f"Error: {str(e)}")



def transform_to_db_structure_and_write():
    # Read from the output.json file
    with open("/opt/cellframe-node/var/lib/plugins/hub/output.json", "r") as f:
        data = json.load(f)

    group_name = "hub"  # Group name in the global database
    node_addr = data['node_addr'].replace("::", "").replace(":", "")  # Format node address

    # Write basic node information to GDB
    write_to_gdb(group_name, f"{node_addr}_hostname", data['hostname'])
    write_to_gdb(group_name, f"{node_addr}_service_uptime", data['service_uptime'])
    write_to_gdb(group_name, f"{node_addr}_node_version", data['node_version'])
    write_to_gdb(group_name, f"{node_addr}_timestamp", data['timestamp'])

    # Write network-related information to GDB
    for network, info in data['network_info'].items():
        write_to_gdb(group_name, f"{node_addr}_{network}_our_node_state", info['our_node_state'])
        write_to_gdb(group_name, f"{node_addr}_{network}_network_state", info['network_state'])
        write_to_gdb(group_name, f"{node_addr}_{network}_main_status", info['main_status'])
        write_to_gdb(group_name, f"{node_addr}_{network}_sync_percentage", info['sync_percentage'])
        write_to_gdb(group_name, f"{node_addr}_{network}_block_height", info['block_height'])
        write_to_gdb(group_name, f"{node_addr}_{network}_stake_value", info['stake_value'])

        # Write fee_addr_info if present
        fee_addr_info = info.get('fee_addr_info')
        if fee_addr_info:
            write_to_gdb(group_name, f"{node_addr}_{network}_fee_addr_info_fee_addr", fee_addr_info['fee_addr'])
            write_to_gdb(group_name, f"{node_addr}_{network}_fee_addr_info_ma7_{fee_addr_info['ma7']['date'].replace(',', '').replace(' ', '_')}", fee_addr_info['ma7']['value'])
            write_to_gdb(group_name, f"{node_addr}_{network}_fee_addr_info_ma7_apy", fee_addr_info['ma7']['apy'])
            write_to_gdb(group_name, f"{node_addr}_{network}_fee_addr_info_ma30_{fee_addr_info['ma30']['date'].replace(',', '').replace(' ', '_')}", fee_addr_info['ma30']['value'])
            write_to_gdb(group_name, f"{node_addr}_{network}_fee_addr_info_ma30_apy", fee_addr_info['ma30']['apy'])

            # Write only today's and yesterday's rewards
            rewards = fee_addr_info['rewards']
            for reward_date, reward_value in rewards.items():
                # Filter to only today and yesterday's rewards
                today = datetime.now().strftime("%a, %d %b %Y")
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%a, %d %b %Y")
                if reward_date in [today, yesterday]:
                    reward_key = f"{node_addr}_{network}_fee_addr_info_rewards_{reward_date.replace(',', '').replace(' ', '_')}"
                    write_to_gdb(group_name, reward_key, reward_value)

        # Write sovereign_addr_info if present
        sovereign_addr_info = info.get('sovereign_addr_info')
        if sovereign_addr_info:
            write_to_gdb(group_name, f"{node_addr}_{network}_sovereign_addr_info_sovereign_addr", sovereign_addr_info['sovereign_addr'])
            write_to_gdb(group_name, f"{node_addr}_{network}_sovereign_addr_info_sovereign_tax", sovereign_addr_info['sovereign_tax'])
        else:
            print(f"No sovereign_addr_info found for network {network}")

    print("Data successfully written to GDB.")


# -------------- UPDATER FUNCTIONS ----------------

def get_version_from_manifest(manifest_path):
    """Reads the version from a local manifest file."""
    try:
        with open(manifest_path, 'r') as f:
            data = json.load(f)
            return data.get("version")
    except FileNotFoundError:
        print(f"Local manifest file not found: {manifest_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error parsing manifest file: {manifest_path}")
        return None

def fetch_remote_manifest():
    """Fetches the manifest.json file from the remote GitHub URL."""
    try:
        response = requests.get(REMOTE_MANIFEST_URL)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch remote manifest: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Error fetching remote manifest: {e}")
        return None

def download_file(url, path):
    """Downloads a file from a given URL and saves it to the specified path."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(path, 'wb') as f:
                f.write(response.content)
            print(f"Successfully downloaded {url} to {path}")
        else:
            print(f"Failed to download {url}: {response.status_code}")
    except requests.RequestException as e:
        print(f"Error downloading file {url}: {e}")

def reload_plugin():
    """Reloads the plugin without restarting the node."""
    try:
        result = subprocess.run([CLI, "plugin", "reload"], capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print("Plugin reloaded successfully.")
        else:
            print(f"Error reloading plugin: {result.stderr}")
    except Exception as e:
        print(f"Error: {str(e)}")

def update_plugin_if_needed():
    """Checks if an update is needed and downloads the latest version if available."""
    local_version = get_version_from_manifest(LOCAL_MANIFEST)
    remote_manifest = fetch_remote_manifest()

    if remote_manifest:
        remote_version = remote_manifest.get("version")
        if local_version is None or (remote_version and remote_version > local_version):
            print(f"Updating plugin from version {local_version} to {remote_version}...")
            download_file(REMOTE_HUB_URL, os.path.join(PLUGIN_PATH, "hub.py"))
            download_file(REMOTE_MANIFEST_URL, os.path.join(PLUGIN_PATH, "manifest.json"))
            print("Update completed! Reloading plugin...")
            reload_plugin()  # Reload the plugin instead of restarting the node
        else:
            print(f"Plugin is already up-to-date (version {local_version}).")
    else:
        print("Could not fetch remote manifest. Update aborted.")
# -------------- ORIGINAL FUNCTIONALITY ----------------

# Main function that runs the required tasks every 30 minutes
def main_task():
    print("Running main task...")
    update_plugin_if_needed()  # Check for updates
    # Generate the output file
    generateFinalOutput()
    # Write to GDB
    transform_to_db_structure_and_write()
    print("Task completed. Waiting for the next run...")
# Run the task every 30 minutes
def run_periodically(interval_in_minutes=30):
    interval_in_seconds = interval_in_minutes * 60
    while True:
        main_task()
        time.sleep(interval_in_seconds)
if __name__ == "__main__":
    run_periodically(30)  # Run the task every 30 minutes
