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

# Function to add or update a configuration under [plugins]
ensure_config_in_plugins_section() {
    local config_key="$1"
    local config_value="$2"

    if grep -q "^#.*$config_key" $CFG_FILE; then
        # Uncomment the line if it exists and is commented
        sed -i "/^#.*$config_key/c\\$config_key=$config_value" $CFG_FILE
    elif grep -q "$config_key=" $CFG_FILE; then
        # Modify the line if it exists
        sed -i "/$config_key=/c\\$config_key=$config_value" $CFG_FILE
    else
        # Append the line right below the [plugins] section
        sed -i '/\[plugins\]/a\'"$config_key=$config_value" $CFG_FILE
    fi
}

# Check if the [plugins] section exists
if grep -q "\[plugins\]" $CFG_FILE; then
    echo "Modifying existing [plugins] section in $CFG_FILE"

    # Ensure 'enabled=true' is present and correctly set
    ensure_config_in_plugins_section "enabled" "true"

    # Ensure 'py_load=true' is present and correctly set
    ensure_config_in_plugins_section "py_load" "true"

    # Ensure 'py_path=/opt/cellframe-node/var/lib/plugins' is present and correctly set
    ensure_config_in_plugins_section "py_path" "/opt/cellframe-node/var/lib/plugins"
    
else
    # Add the [plugins] section and the necessary parameters if the section doesn't exist
    echo "Adding new [plugins] section to $CFG_FILE"
    echo "[plugins]" >> $CFG_FILE
    echo "enabled=true" >> $CFG_FILE
    echo "py_load=true" >> $CFG_FILE
    echo "py_path=/opt/cellframe-node/var/lib/plugins" >> $CFG_FILE
fi

# Search and remove any duplicate lines in the config file
echo "Checking for duplicate lines in $CFG_FILE"
awk '!seen[$0]++' $CFG_FILE > temp_file && mv temp_file $CFG_FILE

echo "Configuration update complete and duplicates removed."


# Restart cellframe-node service
service cellframe-node restart

echo "Installation and configuration completed on localhost!"
