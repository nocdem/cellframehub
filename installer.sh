#!/bin/bash

# Check if the hostname is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <hostname>"
  exit 1
fi

# Constants
HOSTNAME=$1
APPS_TO_INSTALL="apache2 bc rsync"  # Modify this variable to add or remove applications
WALLET_DIR="/opt/cellframe-node/var/lib/wallet"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -i /root/.ssh/id_ed25519"
HOSTS_FILE="/etc/hosts"
NODE_STATS_URL="https://raw.githubusercontent.com/nocdem/cellframehub/main/node_stats"
HUB_STATS_URL="https://raw.githubusercontent.com/nocdem/cellframehub/main/hub_stats"
CRON_JOB="*/10 * * * * /root/hub_stats"

# Network definitions
declare -A NETWORKS
NETWORKS=(
  ["b"]="Backbone"
  ["k"]="KelVPN"
)

# Fetch the version number from node-version-badge.svg
VERSION_URL="https://pub.cellframe.net/linux/cellframe-node/master/node-version-badge.svg"
VERSION=$(wget -qO- "$VERSION_URL" | grep -oP '(?<=<text x="114.5" y="14">)[\d.]+(?=</text>)')

if [ -z "$VERSION" ]; then
  echo "Failed to retrieve the version number from $VERSION_URL"
  exit 1
else
  echo "Retrieved version number: $VERSION"
fi

# Construct the dynamic FILE_URL using the extracted version number
FILE_URL="https://pub.cellframe.net/linux/cellframe-node/master/cellframe-node-$VERSION-updtr-amd64.deb"

# Read the hosts from the hosts file
if ! grep -q "$HOSTNAME" "$HOSTS_FILE"; then
  echo "Host $HOSTNAME not found in $HOSTS_FILE"
  exit 1
fi

# Check if a wallet already exists for the node
WALLET_NAME="$HOSTNAME"
WALLET_FILE="$WALLET_DIR/$WALLET_NAME.dwallet"

# Create a new wallet if it does not already exist
if [ ! -f "$WALLET_FILE" ]; then
  echo "Creating new wallet for node $HOSTNAME..."
  /opt/cellframe-node/bin/cellframe-node-cli wallet new -w "$WALLET_NAME"
else
  echo "Wallet for node $HOSTNAME already exists."
fi

# Determine the network for the fee address extraction
NETWORK_PREFIX=${HOSTNAME:0:1}
NETWORK=${NETWORKS[$NETWORK_PREFIX]}

if [ -z "$NETWORK" ]; then
  echo "Error: Invalid hostname prefix. The hostname must start with one of: ${!NETWORKS[@]}"
  exit 1
fi

# Retrieve the wallet address to use as the fee address
FEE_ADDR=$(/opt/cellframe-node/bin/cellframe-node-cli wallet info -w "$WALLET_NAME" -net "$NETWORK" | grep -oP '(?<=addr:\s).*')

if [ -z "$FEE_ADDR" ]; then
  echo "Failed to retrieve wallet address for $HOSTNAME. Exiting."
  exit 1
else
  echo "Retrieved wallet address for fee_addr: $FEE_ADDR"
fi

# Copy SSH public key to the node for passwordless authentication
echo "Copying SSH public key to the node..."
ssh-copy-id root@$HOSTNAME

# Verify if the public key was added successfully
if ssh $SSH_OPTS root@$HOSTNAME "grep -q '$(cat /root/.ssh/id_ed25519.pub)' ~/.ssh/authorized_keys"; then
  echo "SSH public key successfully added."
else
  echo "Failed to add SSH public key. Exiting."
  exit 1
fi

# Extract the filename from the URL
FILENAME=$(basename "$FILE_URL")

# Define the commands for network configuration based on node type
NETWORK_COMMANDS=()
if [[ $HOSTNAME == b* ]]; then
  # Backbone node configuration
  NETWORK_COMMANDS+=("echo 'Configuring backbone node...'")
  NETWORK_COMMANDS+=("/opt/cellframe-node/bin/cellframe-node-config -e network KelVPN ensure off")
  NETWORK_COMMANDS+=("sed -i 's/^#node-role=full/node-role=master/' /opt/cellframe-node/etc/network/Backbone.cfg")
  NETWORK_COMMANDS+=("sed -i 's/^node-role=.*/node-role=master/' /opt/cellframe-node/etc/network/Backbone.cfg")
  NETWORK_COMMANDS+=("sed -i '/\[esbocs\]/,/^\s*$/s/^#//' /opt/cellframe-node/etc/network/Backbone.cfg")
  NETWORK_COMMANDS+=("sed -i 's/^blocks-sign-cert=.*/blocks-sign-cert=$HOSTNAME/' /opt/cellframe-node/etc/network/Backbone.cfg")
  NETWORK_COMMANDS+=("sed -i 's/^collecting_level=.*/collecting_level=10.0/' /opt/cellframe-node/etc/network/Backbone.cfg")
  NETWORK_COMMANDS+=("sed -i 's/^fee_addr=.*/fee_addr=$FEE_ADDR/' /opt/cellframe-node/etc/network/Backbone.cfg")
elif [[ $HOSTNAME == k* ]]; then
  # KelVPN node configuration
  NETWORK_COMMANDS+=("echo 'Configuring KelVPN node...'")
  NETWORK_COMMANDS+=("/opt/cellframe-node/bin/cellframe-node-config -e network Backbone ensure off")
  NETWORK_COMMANDS+=("sed -i 's/^#node-role=full/node-role=master/' /opt/cellframe-node/etc/network/KelVPN.cfg")
  NETWORK_COMMANDS+=("sed -i 's/^node-role=.*/node-role=master/' /opt/cellframe-node/etc/network/KelVPN.cfg")
  NETWORK_COMMANDS+=("sed -i '/\[esbocs\]/,/^\s*$/s/^#//' /opt/cellframe-node/etc/network/KelVPN.cfg")
  NETWORK_COMMANDS+=("sed -i 's/^blocks-sign-cert=.*/blocks-sign-cert=$HOSTNAME/' /opt/cellframe-node/etc/network/KelVPN.cfg")
  NETWORK_COMMANDS+=("sed -i 's/^collecting_level=.*/collecting_level=10.0/' /opt/cellframe-node/etc/network/KelVPN.cfg")
  NETWORK_COMMANDS+=("sed -i 's/^fee_addr=.*/fee_addr=$FEE_ADDR/' /opt/cellframe-node/etc/network/KelVPN.cfg")
fi

# Define the commands to run on the remote host
COMMANDS=(
  "echo 'Disabling password authentication and enabling public key authentication...' && \
   sed -i -e 's/^#PasswordAuthentication yes/PasswordAuthentication no/' \
   -e 's/^PasswordAuthentication yes/PasswordAuthentication no/' \
   -e 's/^#PubkeyAuthentication no/PubkeyAuthentication yes/' \
   -e 's/^PubkeyAuthentication no/PubkeyAuthentication yes/' /etc/ssh/sshd_config"
  "echo 'Restarting SSH service...' && systemctl restart sshd && sleep 2"
  "echo 'Updating package list and upgrading system...' && apt-get update && apt-get upgrade -y"
  "echo 'Installing applications...' && apt-get install -y $APPS_TO_INSTALL"
  "echo 'Configuring Apache...' && a2enmod cgid && systemctl restart apache2"
  "if [ ! -f /tmp/$FILENAME ]; then echo 'Downloading file...' && wget -O /tmp/$FILENAME $FILE_URL; else echo 'File already exists, skipping download.'; fi"
  "echo 'Changing hostname...' && hostnamectl set-hostname $HOSTNAME && sed -i 's/127.0.1.1.*/127.0.1.1 $HOSTNAME/' /etc/hosts"
  "echo 'Installing the downloaded package...' && dpkg -i /tmp/$FILENAME"
  "echo 'Fixing missing dependencies...' && apt-get install -f -y"
  "echo 'Stopping cellframe-node service...' && systemctl stop cellframe-node"
  "if [ ! -f /opt/cellframe-node/var/lib/$HOSTNAME.dcert ]; then echo 'Creating certificate for signing blocks...' && /opt/cellframe-node/bin/cellframe-node-tool cert create $HOSTNAME sig_dil; else echo 'Certificate $HOSTNAME.dcert already exists, skipping creation.'; fi"
  "echo 'Updating cellframe-node.cfg settings...' && sed -i '/\[server\]/!b;n;c\enabled=true' /opt/cellframe-node/etc/cellframe-node.cfg && sed -i '/\[mempool\]/!b;n;c\auto_proc=true' /opt/cellframe-node/etc/cellframe-node.cfg"
  "echo 'Downloading node_stats script...' && wget -O /usr/lib/cgi-bin/node_stats $NODE_STATS_URL && chmod +x /usr/lib/cgi-bin/node_stats"
  "echo 'Downloading hub_stats script...' && wget -O /root/hub_stats $HUB_STATS_URL && chmod +x /root/hub_stats"
  "echo 'Adding hub_stats to root crontab...' && (crontab -l 2>/dev/null; echo '$CRON_JOB') | crontab -"
)

# SSH into the host and execute the commands
for CMD in "${COMMANDS[@]}"; do
  ssh $SSH_OPTS root@$HOSTNAME "$CMD"
done

# Execute network configuration commands one by one
for NET_CMD in "${NETWORK_COMMANDS[@]}"; do
  ssh $SSH_OPTS root@$HOSTNAME "$NET_CMD"
done

# Restart the node service to apply changes
echo "Restarting cellframe-node service..."
ssh $SSH_OPTS root@$HOSTNAME "systemctl restart cellframe-node"

echo "Node setup and configuration complete."
