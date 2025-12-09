#!/bin/bash

# Muspi Service Installer
# Automatically detects current directory and installs systemd service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="muspi.service"
SERVICE_FILE="${SCRIPT_DIR}/${SERVICE_NAME}"
SYSTEMD_DIR="/etc/systemd/system"
VENV_PYTHON="${SCRIPT_DIR}/venv/bin/python"
MAIN_PY="${SCRIPT_DIR}/main.py"

echo -e "${GREEN}=== Muspi Service Installer ===${NC}\n"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Please do not run this script as root${NC}"
    echo "Run it as: ./install_service.sh"
    exit 1
fi

# Check if venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}Error: Virtual environment not found at ${VENV_PYTHON}${NC}"
    echo "Please run install_dependencies.sh first to create the virtual environment"
    exit 1
fi

# Check if main.py exists
if [ ! -f "$MAIN_PY" ]; then
    echo -e "${RED}Error: main.py not found at ${MAIN_PY}${NC}"
    exit 1
fi

# Get current user
CURRENT_USER=$(whoami)

echo "Detected configuration:"
echo "  - Install directory: ${SCRIPT_DIR}"
echo "  - Python executable: ${VENV_PYTHON}"
echo "  - Main script: ${MAIN_PY}"
echo "  - Service user: ${CURRENT_USER}"
echo ""

# Create service file with dynamic paths
echo "Creating service file..."
cat > "${SERVICE_FILE}" << EOF
[Unit]
Description=Muspi Service
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${SCRIPT_DIR}
ExecStart=${VENV_PYTHON} ${MAIN_PY}
Restart=always
RestartSec=3
# 允许访问用户级的 PulseAudio
Environment="XDG_RUNTIME_DIR=/run/user/1000"
Environment="PULSE_RUNTIME_PATH=/run/user/1000/pulse"

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓${NC} Service file created at ${SERVICE_FILE}"

# Check if service already exists
if systemctl list-unit-files | grep -q "^${SERVICE_NAME}"; then
    echo -e "${YELLOW}⚠${NC}  Service already exists, it will be updated"

    # Stop the service if it's running
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        echo "Stopping existing service..."
        sudo systemctl stop ${SERVICE_NAME}
        echo -e "${GREEN}✓${NC} Service stopped"
    fi
fi

# Copy service file to systemd directory
echo "Installing service to ${SYSTEMD_DIR}/${SERVICE_NAME}..."
sudo cp "${SERVICE_FILE}" "${SYSTEMD_DIR}/${SERVICE_NAME}"
echo -e "${GREEN}✓${NC} Service file installed"

# Reload systemd daemon
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload
echo -e "${GREEN}✓${NC} Systemd daemon reloaded"

# Enable service
echo "Enabling service to start on boot..."
sudo systemctl enable ${SERVICE_NAME}
echo -e "${GREEN}✓${NC} Service enabled"

echo ""
echo -e "${GREEN}=== Installation Complete! ===${NC}\n"
echo "Service management commands:"
echo "  Start service:   sudo systemctl start ${SERVICE_NAME}"
echo "  Stop service:    sudo systemctl stop ${SERVICE_NAME}"
echo "  Restart service: sudo systemctl restart ${SERVICE_NAME}"
echo "  View status:     sudo systemctl status ${SERVICE_NAME}"
echo "  View logs:       sudo journalctl -u ${SERVICE_NAME} -f"
echo "  Disable service: sudo systemctl disable ${SERVICE_NAME}"
echo ""

# Ask if user wants to start the service now
read -p "Do you want to start the service now? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting service..."
    sudo systemctl start ${SERVICE_NAME}
    echo -e "${GREEN}✓${NC} Service started"
    echo ""
    echo "Checking service status..."
    sudo systemctl status ${SERVICE_NAME} --no-pager
else
    echo "Service not started. You can start it later with:"
    echo "  sudo systemctl start ${SERVICE_NAME}"
fi

echo ""
echo -e "${GREEN}Done!${NC}"
