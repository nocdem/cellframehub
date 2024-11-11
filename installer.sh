#!/bin/bash

# Directories
PLUGIN_DIR="/opt/cellframe-node/var/lib/plugins/hub"
NETWORK_DIR="/opt/cellframe-node/etc/network"
HUB_NETWORK_DIR="/opt/cellframe-node/etc/network/hub"
CA_DIR="/opt/cellframe-node/share/ca"
CFG_FILE="/opt/cellframe-node/etc/cellframe-node.cfg"

# URLs to download
PLUGIN_FILES=(
  "https://raw.githubusercontent.com/nocdem/cellframehub/refs/heads/main/plugin/hub.py"
  "https://raw.githubusercontent.com/nocdem/cellframehub/refs/heads/main/plugin/manifest.json"
  "https://raw.githubusercontent.com/nocdem/cellframehub/refs/heads/main/plugin/hub_req.txt"
)
NETWORK_FILE="https://raw.githubusercontent.com/nocdem/cellframehub/refs/heads/main/network/hub.cfg"
CHAIN_CFG_FILE="https://raw.githubusercontent.com/nocdem/cellframehub/refs/heads/main/network/hub/chain-0.cfg"

# Additional files to download into CA directory
DCERT_FILES=(
  "https://github.com/nocdem/cellframehub/raw/refs/heads/main/network/hub.master.0.dcert"
  "https://github.com/nocdem/cellframehub/raw/refs/heads/main/network/hub.master.1.dcert"
  "https://github.com/nocdem/cellframehub/raw/refs/heads/main/network/hub.master.2.dcert"
  "https://github.com/nocdem/cellframehub/raw/refs/heads/main/network/hub.root.0.dcert"
  "https://github.com/nocdem/cellframehub/raw/refs/heads/main/network/hub.root.1.dcert"
)

# Create directories if they don't exist
mkdir -p "$PLUGIN_DIR"
mkdir -p "$HUB_NETWORK_DIR"
mkdir -p "$CA_DIR"

# Download plugin files
cd "$PLUGIN_DIR" || exit
for url in "${PLUGIN_FILES[@]}"; do
    wget -N "$url" || { echo "Failed to download $url"; exit 1; }
done

# Download hub.cfg
cd "$NETWORK_DIR" || exit
wget -N "$NETWORK_FILE" || { echo "Failed to download $NETWORK_FILE"; exit 1; }

# Download chain-0.cfg
cd "$HUB_NETWORK_DIR" || exit
wget -N "$CHAIN_CFG_FILE" || { echo "Failed to download $CHAIN_CFG_FILE"; exit 1; }

# Download dcert files into CA directory
cd "$CA_DIR" || exit
for url in "${DCERT_FILES[@]}"; do
    wget -N "$url" || { echo "Failed to download $url"; exit 1; }
done

# Upgrade pip and install required packages
cd "$PLUGIN_DIR" || exit
/opt/cellframe-node/python/bin/python3.10 -m pip install --upgrade pip || { echo "Failed to upgrade pip"; exit 1; }
/opt/cellframe-node/python/bin/pip3 install -r hub_req.txt || { echo "Failed to install requirements"; exit 1; }

# Check if py_load=true or #py_load=true exists in the config file
if grep -q "#py_load=true" "$CFG_FILE"; then
    # Uncomment the line if found
    sed -i 's/#py_load=true/py_load=true/' "$CFG_FILE"
elif ! grep -q "py_load=true" "$CFG_FILE"; then
    # Append the line if it doesn't exist at all
    echo "py_load=true" >> "$CFG_FILE"
fi

# Restart cellframe-node service
service cellframe-node restart || { echo "Failed to restart cellframe-node"; exit 1; }

echo "Installation and configuration completed on localhost!"
