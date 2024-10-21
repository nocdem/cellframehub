#!/bin/bash

# Directories
PLUGIN_DIR="/opt/cellframe-node/var/lib/plugins/hub"
NETWORK_DIR="/opt/cellframe-node/etc/network"
HUB_NETWORK_DIR="/opt/cellframe-node/etc/network/hub"
CFG_FILE="/opt/cellframe-node/etc/cellframe-node.cfg"

# URLs to download
PLUGIN_FILES=(
  "https://raw.githubusercontent.com/nocdem/cellframehub/refs/heads/main/plugin/hub.py"
  "https://raw.githubusercontent.com/nocdem/cellframehub/refs/heads/main/plugin/manifest.json"
  "https://raw.githubusercontent.com/nocdem/cellframehub/refs/heads/main/plugin/hub_req.txt"
)
NETWORK_FILE="https://raw.githubusercontent.com/nocdem/cellframehub/refs/heads/main/network/hub.cfg"
CHAIN_CFG_FILE="https://raw.githubusercontent.com/nocdem/cellframehub/refs/heads/main/network/hub/chain-0.cfg"

# Create directories if they don't exist
mkdir -p $PLUGIN_DIR
mkdir -p $HUB_NETWORK_DIR

# Download plugin files
cd $PLUGIN_DIR
for url in "${PLUGIN_FILES[@]}"; do
    wget -N $url
done

# Download hub.cfg
cd $NETWORK_DIR
wget -N $NETWORK_FILE

# Download chain-0.cfg
cd $HUB_NETWORK_DIR
wget -N $CHAIN_CFG_FILE

# Install required packages
cd $PLUGIN_DIR

/opt/cellframe-node/python/bin/pip3 install -r hub_req.txt
/opt/cellframe-node/python/bin/python3.10 -m pip install --upgrade pip
    echo "py_load=true" >> $CFG_FILE



# Restart cellframe-node service
service cellframe-node restart

echo "Installation and configuration completed on localhost!"
