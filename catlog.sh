#!/bin/bash

# Muspi Service journal logger
# Logs muspi service journal to console

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SERVICE_NAME="muspi.service"

# Check if service is installed
if ! systemctl list-unit-files | grep -q "^${SERVICE_NAME}"; then
    echo -e "${RED}Error: Muspi service is not installed${NC}"
    echo ""
    echo "Please install the service first by running:"
    echo -e "  ${GREEN}./install_service.sh${NC}"
    echo ""
    exit 1
fi

# Check if service exists but is not loaded (could be a stale installation)
if ! systemctl status ${SERVICE_NAME} &>/dev/null; then
    echo -e "${YELLOW}Warning: Service file exists but may not be loaded properly${NC}"
    echo "Try running: sudo systemctl daemon-reload"
    echo ""
fi

# Display service logs
echo -e "${GREEN}=== Muspi Service Logs ===${NC}"
echo -e "${YELLOW}Press Ctrl+C to exit${NC}\n"

journalctl -u ${SERVICE_NAME} -f --output=cat