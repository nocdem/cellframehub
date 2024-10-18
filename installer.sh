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

#!/bin/bash

CFG_FILE="/opt/cellframe-node/etc/cellframe-node.cfg"

# Ensure the [plugins] section exists, and necessary parameters are correctly set
if grep -q "\[plugins\]" $CFG_FILE; then
    echo "Modifying existing [plugins] section in $CFG_FILE"

    # Ensure 'enabled=true' is present, uncommented if necessary
    if grep -q "^#.*enabled=" $CFG_FILE; then
        sed -i '/^#.*enabled=/c\enabled=true' $CFG_FILE  # Uncomment and set to 'true'
    elif grep -q "enabled=" $CFG_FILE; then
        sed -i '/enabled=/c\enabled=true' $CFG_FILE  # Ensure it's set to 'true'
    else
        # Add 'enabled=true' if it doesn't exist
        sed -i '/\[plugins\]/a enabled=true' $CFG_FILE
    fi

    # Ensure 'py_load=true' is present, uncommented if necessary
    if grep -q "^#.*py_load=" $CFG_FILE; then
        sed -i '/^#.*py_load=/c\py_load=true' $CFG_FILE  # Uncomment and set to 'true'
    elif grep -q "py_load=" $CFG_FILE; then
        sed -i '/py_load=/c\py_load=true' $CFG_FILE  # Ensure it's set to 'true'
    else
        # Add 'py_load=true' if it doesn't exist
        sed -i '/\[plugins\]/a py_load=true' $CFG_FILE
    fi

    # Ensure 'py_path=/opt/cellframe-node/var/lib/plugins' is present, uncommented if necessary
    if grep -q "^#.*py_path=" $CFG_FILE; then
        sed -i '/^#.*py_path=/c\py_path=/opt/cellframe-node/var/lib/plugins' $CFG_FILE  # Uncomment and correct the path
    elif grep -q "py_path=" $CFG_FILE; then
        sed -i '/py_path=/c\py_path=/opt/cellframe-node/var/lib/plugins' $CFG_FILE  # Ensure the correct path is set
    else
        # Add 'py_path=/opt/cellframe-node/var/lib/plugins' if it doesn't exist
        sed -i '/\[plugins\]/a py_path=/opt/cellframe-node/var/lib/plugins' $CFG_FILE
    fi

else
    # Add the [plugins] section and the necessary parameters if the section doesn't exist
    echo "Adding new [plugins] section to $CFG_FILE"
    echo "[plugins]" >> $CFG_FILE
    echo "enabled=true" >> $CFG_FILE
    echo "py_load=true" >> $CFG_FILE
    echo "py_path=/opt/cellframe-node/var/lib/plugins" >> $CFG_FILE
fi

# Restart cellframe-node service
service cellframe-node restart

echo "Installation and configuration completed on localhost!"
