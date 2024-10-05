from pycfhelpers.node.http.simple import CFSimpleHTTPServer, CFSimpleHTTPRequestHandler, CFSimpleHTTPResponse
import subprocess
import socket
import time

CLI = "/opt/cellframe-node/bin/cellframe-node-cli"

cached_data = {
    'hostname': socket.gethostname(),
}

# Function to fetch network names
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
            return [net.strip() for net in networks if net.strip() and not net.strip().startswith("networks:")]
        else:
            return f"Error running net list command: {result.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"

# Function to fetch network status for each network
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

# Function to parse network status output
def parseNetworkStatus(output):
    network_info = {}
    lines = output.splitlines()
    for line in lines:
        if "current:" in line and "NET_STATE" in line:
            network_info['our_node_state'] = line.split(":")[1].strip()
        elif "target:" in line and "NET_STATE" in line:
            network_info['network_state'] = line.split(":")[1].strip()
        elif "main:" in line:
            network_info['main_status'] = line.split(":")[1].strip()
    return network_info

# Function to collect all network status data
def collectNetworkStatus():
    collected_data = {
        "hostname": cached_data['hostname'],
        "networks": {},
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    # Fetch all network data
    networks = getNetworkNames()
    if isinstance(networks, list):
        for network in networks:
            collected_data['networks'][network] = getNetworkStatus(network)
    else:
        collected_data['networks']['error'] = networks

    return collected_data

# Function to generate the HTML response
def generateHTML(data):
    html = f"<html><head><title>Network Status</title></head><body>"
    html += f"<h1>Network Status for {data['hostname']}</h1>"
    html += f"<p>Timestamp: {data['timestamp']}</p>"

    for network, info in data['networks'].items():
        if isinstance(info, dict):
            html += f"<h2>Network: {network}</h2>"
            html += f"<p>Our Node State: {info.get('our_node_state', 'N/A')}</p>"
            html += f"<p>Network State: {info.get('network_state', 'N/A')}</p>"
            html += f"<p>Main Status: {info.get('main_status', 'N/A')}</p>"
        else:
            html += f"<h2>Error for network {network}: {info}</h2>"

    html += "</body></html>"
    return html

# Function to collect and format data
def getRawData():
    collected_data = collectNetworkStatus()
    return generateHTML(collected_data)

# Handle HTTP requests and respond with collected data
def request_handler(request: CFSimpleHTTPRequestHandler):
    response_body = getRawData().encode("utf-8")  # Collect data in HTML format
    response = CFSimpleHTTPResponse(body=response_body, code=200)
    response.headers = {
        "Content-Type": "text/html"
    }
    return response

# Start the HTTP server to serve the data
def init():
    handler = CFSimpleHTTPRequestHandler(methods=["GET"], handler=request_handler)
    CFSimpleHTTPServer().register_uri_handler(uri="/messages", handler=handler)
    return 0

def deinit():
    return 0
