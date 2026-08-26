#!/bin/bash
# PiBlindHub - Standalone Installation Script
# This script installs and configures the standalone application on Raspberry Pi

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="slm_standalone"
RASPBERRY_USER="slm"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}PiBlindHub - Standalone Installation${NC}"
echo -e "${BLUE}================================================${NC}"
echo

# Check if we're in the right directory
if [ ! -f "standalone_runner.py" ]; then
    echo -e "${RED}[ERROR]${NC} standalone_runner.py not found in current directory"
    echo -e "${YELLOW}[INFO]${NC} Please run this script from the installation directory"
    exit 1
fi

echo -e "${BLUE}[INFO]${NC} Starting installation process..."
echo -e "${BLUE}[INFO]${NC} Current directory: $(pwd)"
echo

# Install system dependencies
echo -e "${BLUE}[INFO]${NC} Installing system dependencies..."
sudo apt update && sudo apt install -y python3 python3-pip python3-venv
echo -e "${GREEN}[SUCCESS]${NC} System dependencies installed"
echo

# Create virtual environment
echo -e "${BLUE}[INFO]${NC} Creating Python virtual environment..."
python3 -m venv venv
echo -e "${GREEN}[SUCCESS]${NC} Virtual environment created in venv/"
echo

# Activate virtual environment and install dependencies
echo -e "${BLUE}[INFO]${NC} Activating virtual environment and installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}[SUCCESS]${NC} Dependencies installed in virtual environment"
echo

# Add user to GPIO group
echo -e "${BLUE}[INFO]${NC} Adding user to GPIO group..."
sudo usermod -a -G gpio $USER
echo -e "${GREEN}[SUCCESS]${NC} User added to GPIO group"
echo

# Create logs directory
echo -e "${BLUE}[INFO]${NC} Creating logs directory..."
mkdir -p logs
echo -e "${GREEN}[SUCCESS]${NC} Logs directory created"
echo

# Make scripts executable
echo -e "${BLUE}[INFO]${NC} Making scripts executable..."
chmod +x *.sh
chmod +x *.py
echo -e "${GREEN}[SUCCESS]${NC} Scripts made executable"
echo

# Create systemd service file
echo -e "${BLUE}[INFO]${NC} Creating systemd service..."
sudo tee /etc/systemd/system/motorised-store.service > /dev/null << EOF
[Unit]
Description=PiBlindHub - Standalone Mode
After=network.target

[Service]
Type=simple
User=$RASPBERRY_USER
WorkingDirectory=/home/$RASPBERRY_USER/$INSTALL_DIR
Environment=PATH=/home/$RASPBERRY_USER/$INSTALL_DIR/venv/bin
ExecStart=/home/$RASPBERRY_USER/$INSTALL_DIR/venv/bin/python /home/$RASPBERRY_USER/$INSTALL_DIR/standalone_runner.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo -e "${BLUE}[INFO]${NC} Reloading systemd..."
sudo systemctl daemon-reload
echo -e "${GREEN}[SUCCESS]${NC} Systemd reloaded"
echo

# Create startup script
echo -e "${BLUE}[INFO]${NC} Creating startup script..."
cat > start_standalone.sh << 'EOF'
#!/bin/bash
echo "Starting PiBlindHub - Standalone Mode"
echo "=================================================="
echo "Ultra-resilient replacement for original run.py"
echo "Physical buttons are active for manual control"
echo "Press Ctrl+C to quit"
echo "=================================================="
echo
source venv/bin/activate
python standalone_runner.py
EOF
chmod +x start_standalone.sh
echo -e "${GREEN}[SUCCESS]${NC} Startup script created"
echo

# Create README
echo -e "${BLUE}[INFO]${NC} Creating README..."
cat > README.txt << 'EOF'
PiBlindHub - Standalone Mode
=========================================

Quick Start:
  ./start_standalone.sh    - Start standalone mode (with venv)
  ./simple_run.sh          - Direct replacement for run.py (with venv)
  ./run.sh start           - Start as service
  ./run.sh status          - Check status
  ./run.sh stop            - Stop service
  ./run.sh logs            - View logs

Command Line Interface (activate venv first):
  source venv/bin/activate
  python3 cli_control.py status
  python3 cli_control.py up
  python3 cli_control.py down
  python3 cli_control.py stop

System Service:
  sudo systemctl start motorised-store.service
  sudo systemctl stop motorised-store.service
  sudo systemctl status motorised-store.service

Features:
  - Ultra-resilient GPIO control
  - Automatic error recovery
  - Motor safety timeouts (30 seconds)
  - Emergency stop procedures
  - Comprehensive logging
  - Service management

Logs:
  logs/standalone.log - Operation logs
  ./run.sh logs       - View live logs
EOF
echo -e "${GREEN}[SUCCESS]${NC} README created"
echo

echo -e "${GREEN}[SUCCESS]${NC} Installation completed successfully!"
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}PiBlindHub - Installation Complete${NC}"
echo -e "${BLUE}================================================${NC}"
echo
echo -e "${GREEN}[INFO]${NC} To start the service:"
echo -e "${YELLOW}  ./start_standalone.sh${NC}"
echo -e "${YELLOW}  OR${NC}"
echo -e "${YELLOW}  ./run.sh start${NC}"
echo -e "${YELLOW}  OR${NC}"
echo -e "${YELLOW}  sudo systemctl start motorised-store.service${NC}"
echo
echo -e "${GREEN}[SUCCESS]${NC} Your motorised store device is now ultra-resilient!"
echo -e "${GREEN}[SUCCESS]${NC} Same functionality as original run.py with enhanced safety features."
echo
