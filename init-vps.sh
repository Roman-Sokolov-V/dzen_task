#!/bin/bash
set -e

# Configuration
PROJECT_DIR="dzen_task"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting system initialization for dzen-task...${NC}"

# 1. Update system packages
echo -e "${YELLOW}Updating system packages...${NC}"
sudo apt-get update -y

# 2. Check and enable swap (Критично для найдешевшого тарифу Zomro)
echo -e "${YELLOW}Checking swap space...${NC}"
if ! swapon --show | grep -q "swap"; then
    echo -e "${YELLOW}No swap space detected. Creating swap file...${NC}"
    RAM_MB=$(free -m | awk '/Mem:/ {print $2}')
    if [ "$RAM_MB" -lt 2048 ]; then
        SWAP_SIZE=2048
    else
        SWAP_SIZE=$RAM_MB
    fi
    if [ "$SWAP_SIZE" -gt 4096 ]; then
        SWAP_SIZE=4096
    fi
    SWAP_FILE="/swapfile"
    sudo fallocate -l ${SWAP_SIZE}M $SWAP_FILE
    sudo chmod 600 $SWAP_FILE
    sudo mkswap $SWAP_FILE
    sudo swapon $SWAP_FILE
    echo "$SWAP_FILE none swap sw 0 0" | sudo tee -a /etc/fstab
    echo -e "${GREEN}Swap file of ${SWAP_SIZE}MB created and enabled.${NC}"
else
    echo -e "${GREEN}Swap space is already configured.${NC}"
fi

# 3. Install Docker Engine & Docker Compose Plugin
echo -e "${YELLOW}Installing Docker Engine...${NC}"
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings

curl -fsSL https://://docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://://docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 4. Create base deployment target directory
# Використовуємо $HOME (для root це буде /root/app)
DEPLOY_DIR="$HOME/app/$PROJECT_DIR"
mkdir -p $DEPLOY_DIR

echo -e "${GREEN}System is ready for GitHub Actions deployment!${NC}"
echo -e "${YELLOW}Target directory created at:${NC} $DEPLOY_DIR"

