#!/bin/bash

# Muspi Service Restarter
# Restarts the muspi systemd service

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SERVICE_NAME="muspi.service"

echo -e "${GREEN}=== Muspi Service Restart ===${NC}\n"

# Check if service is installed
if ! systemctl list-unit-files | grep -q "^${SERVICE_NAME}"; then
    echo -e "${RED}Error: Muspi service is not installed${NC}"
    echo ""
    echo "Please install the service first by running:"
    echo -e "  ${GREEN}./install_service.sh${NC}"
    echo ""
    exit 1
fi

# Check if service is running
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo -e "${YELLOW}Service is running, restarting...${NC}"
    sudo systemctl restart ${SERVICE_NAME}
else
    echo -e "${YELLOW}Service is not running, starting...${NC}"
    sudo systemctl start ${SERVICE_NAME}
fi

# Wait a moment for service to start
sleep 1

# Check if restart was successful
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo -e "${GREEN}✓${NC} Service restarted successfully"
    echo ""
    echo "Service status:"
    sudo systemctl status ${SERVICE_NAME} --no-pager -l
    echo ""
    echo -e "${YELLOW}Tip: View logs with: ./catlog.sh${NC}"
else
    echo -e "${RED}✗${NC} Service failed to start"
    echo ""
    echo "Error details:"
    sudo systemctl status ${SERVICE_NAME} --no-pager -l
    echo ""
    echo -e "${YELLOW}Check logs with: sudo journalctl -u ${SERVICE_NAME} -n 50${NC}"
    exit 1
fi