#!/bin/bash
# SongLab Backend Deployment Script for RTX 5070 Server

set -e  # Exit on error

echo "🚀 SongLab GPU Backend Deployment Script"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then 
   echo -e "${RED}Please run with sudo${NC}"
   exit 1
fi

# Check NVIDIA GPU
echo -e "${YELLOW}Checking GPU...${NC}"
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}nvidia-smi not found. Please install NVIDIA drivers${NC}"
    exit 1
fi

nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
echo -e "${GREEN}GPU detected successfully${NC}"

# Check Docker & Docker Compose
echo -e "${YELLOW}Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker not found. Installing...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
fi

# Check NVIDIA Docker runtime
echo -e "${YELLOW}Checking NVIDIA Docker runtime...${NC}"
if ! docker info 2>/dev/null | grep -q nvidia; then
    echo -e "${YELLOW}Installing NVIDIA Docker runtime...${NC}"
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -
    curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | tee /etc/apt/sources.list.d/nvidia-docker.list
    apt-get update && apt-get install -y nvidia-docker2
    systemctl restart docker
fi

# Build and deploy
echo -e "${YELLOW}Building Docker image...${NC}"
docker-compose build --no-cache

echo -e "${YELLOW}Starting services...${NC}"
docker-compose up -d

# Wait for health check
echo -e "${YELLOW}Waiting for service to be healthy...${NC}"
for i in {1..30}; do
    if curl -f http://localhost:8001/api/health 2>/dev/null; then
        echo -e "${GREEN}✓ Service is healthy!${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

# Show logs
echo -e "${YELLOW}Recent logs:${NC}"
docker-compose logs --tail=20

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${GREEN}API available at: http://localhost:8001${NC}"
echo -e "${GREEN}=========================================${NC}"

# Show service status
docker-compose ps