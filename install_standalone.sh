#!/bin/bash
# PiBlindHub - Standalone Installation Script
# Run this script in WSL to copy files to Raspberry Pi

set -e  # Exit on any error

# Configuration
RASPBERRY_IP="${RASPBERRY_IP:-}"
RASPBERRY_USER="${RASPBERRY_USER:-}"
INSTALL_DIR="${INSTALL_DIR:-piblindhub}"
SOURCE_DIR="src/raspberryapp"

if [ -z "$RASPBERRY_IP" ] || [ -z "$RASPBERRY_USER" ]; then
    echo "Set RASPBERRY_IP and RASPBERRY_USER before running this script."
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}PiBlindHub - Standalone Installer${NC}"
echo -e "${BLUE}================================================${NC}"
echo

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo -e "${RED}[ERROR]${NC} Source directory $SOURCE_DIR not found"
    echo -e "${YELLOW}[INFO]${NC} Please run this script from the project root directory"
    exit 1
fi

# Check if required files exist
echo -e "${BLUE}[INFO]${NC} Checking required files..."
required_files=(
    "standalone_runner.py"
    "device_service.py"
    "models.py"
    "safety_monitor.py"
    "start_device_service.py"
    "cli_control.py"
    "run.sh"
    "simple_run.sh"
    "control.sh"
    "install.sh"
    "requirements.txt"
    "README.md"
    "MIGRATION_GUIDE.md"
    "EMERGENCY_PROCEDURES.md"
    "ULTRA_RESILIENT_ARCHITECTURE.md"
    "RASPBERRY_PI_DEPLOYMENT.md"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$SOURCE_DIR/$file" ]; then
        echo -e "${RED}[ERROR]${NC} $file not found in $SOURCE_DIR/"
        exit 1
    fi
done

echo -e "${GREEN}[SUCCESS]${NC} All required files found"
echo

# Test SSH connection
echo -e "${BLUE}[INFO]${NC} Testing SSH connection to Raspberry Pi..."
echo -e "${BLUE}[INFO]${NC} Target: $RASPBERRY_USER@$RASPBERRY_IP"
echo -e "${BLUE}[INFO]${NC} Install directory: $INSTALL_DIR"
echo

if ! ssh -o ConnectTimeout=10 -o BatchMode=yes $RASPBERRY_USER@$RASPBERRY_IP exit 2>/dev/null; then
    echo -e "${YELLOW}[WARNING]${NC} SSH key authentication not configured"
    echo -e "${YELLOW}[INFO]${NC} You will be prompted for password during file transfer"
    echo
fi

# Create directory and copy all files in one SSH session
echo -e "${BLUE}[INFO]${NC} Creating directory and copying all files..."
echo -e "${YELLOW}[INFO]${NC} You will be prompted for password once for all operations"
echo

# Use rsync over SSH to copy all files at once (only one password prompt)
rsync -avz --progress \
    $SOURCE_DIR/standalone_runner.py \
    $SOURCE_DIR/device_service.py \
    $SOURCE_DIR/models.py \
    $SOURCE_DIR/safety_monitor.py \
    $SOURCE_DIR/start_device_service.py \
    $SOURCE_DIR/cli_control.py \
    $SOURCE_DIR/simple_run.sh \
    $SOURCE_DIR/control.sh \
    $SOURCE_DIR/install.sh \
    $SOURCE_DIR/requirements.txt \
    $RASPBERRY_USER@$RASPBERRY_IP:/home/$RASPBERRY_USER/$INSTALL_DIR/

echo -e "${GREEN}[SUCCESS]${NC} All files copied successfully"
echo

echo -e "${GREEN}[SUCCESS]${NC} All files copied successfully!"
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}PiBlindHub - Files Copied${NC}"
echo -e "${BLUE}================================================${NC}"
echo
echo -e "${GREEN}[INFO]${NC} Installation location: /home/$RASPBERRY_USER/$INSTALL_DIR/"
echo
echo -e "${BLUE}[INFO]${NC} Next steps:"
echo -e "${YELLOW}  1. SSH to your Raspberry Pi${NC}"
echo -e "${YELLOW}  2. cd $INSTALL_DIR${NC}"
echo -e "${YELLOW}  3. chmod +x install.sh${NC}"
echo -e "${YELLOW}  4. ./install.sh${NC}"
echo
echo -e "${BLUE}[INFO]${NC} The install.sh script will:"
echo -e "${YELLOW}  - Install system dependencies${NC}"
echo -e "${YELLOW}  - Create Python virtual environment${NC}"
echo -e "${YELLOW}  - Install Python requirements${NC}"
echo -e "${YELLOW}  - Configure GPIO permissions${NC}"
echo -e "${YELLOW}  - Create systemd service${NC}"
echo -e "${YELLOW}  - Set up startup scripts${NC}"
echo
echo -e "${GREEN}[SUCCESS]${NC} After installation, you can start the service with:"
echo -e "${YELLOW}  ./start_standalone.sh${NC}"
echo -e "${YELLOW}  OR${NC}"
echo -e "${YELLOW}  ./run.sh start${NC}"
echo
