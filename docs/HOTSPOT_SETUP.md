# WiFi Hotspot Setup Guide

This guide explains how to set up and use the PiBlindHub Wi-Fi hotspot functionality on Raspberry Pi.

## Overview

When the Raspberry Pi device is not connected to WiFi, it will automatically create a hotspot named `MSM_<DeviceGUID>` that allows users to connect and configure the device.

## Features

- **Automatic Detection**: Checks for WiFi connectivity on startup
- **Auto-Hotspot**: Creates hotspot automatically when no WiFi is detected
- **Unique Device ID**: Each device has a unique GUID for the hotspot name
- **Random IP**: Uses a random IP address (XXX.YYY.ZZZ.1) to avoid conflicts
- **Static Port**: Uses port 15001 (configurable) for the web interface
- **Secure**: WPA2 encryption with configurable password

## Prerequisites

### Required Packages

Install the following packages on your Raspberry Pi:

```bash
sudo apt update
sudo apt install -y hostapd dnsmasq
```

### Run Setup Script

Execute the setup script to configure the system:

```bash
chmod +x setup_hotspot.sh
./setup_hotspot.sh
```

## Configuration

### Environment Variables

Configure the hotspot settings in your `.env` file:

```env
# Hotspot Configuration
HOTSPOT_ENABLED=true
HOTSPOT_DEFAULT_PORT=15001
HOTSPOT_PASSWORD=MSM123456
HOTSPOT_CHANNEL=7
HOTSPOT_DHCP_RANGE_START=2
HOTSPOT_DHCP_RANGE_END=254
HOTSPOT_AUTO_START_ON_NO_WIFI=true
```

### Configuration File

The hotspot settings are also available in `src/config/app_config.json`:

```json
{
  "hotspot": {
    "enabled": true,
    "default_port": 15001,
    "password": "MSM123456",
    "channel": 7,
    "dhcp_range_start": 2,
    "dhcp_range_end": 254,
    "auto_start_on_no_wifi": true
  }
}
```

## Usage

### Automatic Mode

1. Start the device application:
   ```bash
   python run_device_with_hotspot.py
   ```

2. The application will:
   - Check for WiFi connectivity
   - If no WiFi is detected, automatically create a hotspot
   - Display hotspot information in the console

### Manual Mode

You can also start the web application which includes hotspot functionality:

```bash
python run_webapp.py
```

### Connecting to the Hotspot

1. Look for a WiFi network named `MSM_<DeviceGUID>` (e.g., `MSM_12345678-1234-1234-1234-123456789abc`)
2. Connect using the password `MSM123456` (or your configured password)
3. Open a web browser and navigate to the displayed IP address and port
4. The web interface will be available for device configuration

## Device GUID

Each device generates a unique GUID that is:
- Stored in `data/device_guid.txt`
- Used in the hotspot name: `MSM_<GUID>`
- Persistent across reboots
- Used for device identification

## Network Configuration

### Hotspot IP Range

The hotspot uses a random IP address in the format `XXX.YYY.ZZZ.1` where:
- XXX: Random number between 10-192
- YYY: Random number between 1-254
- ZZZ: Random number between 1-254

### DHCP Range

Client devices will receive IP addresses in the range:
- Start: `XXX.YYY.ZZZ.2` (configurable)
- End: `XXX.YYY.ZZZ.254` (configurable)

### Port Configuration

The web application runs on port 15001 by default when in hotspot mode, which is:
- Above 15000 as requested
- Configurable via `HOTSPOT_DEFAULT_PORT`
- Different from the normal port 8080

## Web Interface

### Dashboard

The dashboard shows:
- WiFi connection status
- Hotspot status (active/inactive)
- Hotspot information when active
- Access URL for easy connection

### API Endpoints

- `GET /api/wifi-status` - Get current WiFi and hotspot status
- `POST /api/hotspot/start` - Start hotspot (Admin only)
- `POST /api/hotspot/stop` - Stop hotspot (Admin only)

## Troubleshooting

### Hotspot Not Starting

1. Check if `hostapd` and `dnsmasq` are installed
2. Verify the setup script was run successfully
3. Check system logs for errors:
   ```bash
   sudo journalctl -u hostapd
   sudo journalctl -u dnsmasq
   ```

### Cannot Connect to Hotspot

1. Verify the hotspot is active:
   ```bash
   sudo systemctl status hostapd
   ```

2. Check the network interface:
   ```bash
   ip addr show wlan0
   ```

3. Verify DHCP is working:
   ```bash
   sudo systemctl status dnsmasq
   ```

### Permission Issues

Ensure the application has the necessary permissions:

```bash
sudo usermod -a -G netdev $USER
```

You may need to add the user to the sudoers file for network configuration:

```bash
echo "$USER ALL=(ALL) NOPASSWD: /usr/sbin/ip, /usr/sbin/systemctl" | sudo tee /etc/sudoers.d/msm-hotspot
```

## Security Considerations

- The hotspot uses WPA2 encryption
- Default password should be changed in production
- Consider using a stronger password
- The hotspot automatically stops when WiFi is restored
- Access to hotspot controls is restricted to admin users

## Development

### Testing

To test the hotspot functionality:

1. Disconnect from WiFi
2. Start the application
3. Verify hotspot creation
4. Connect a device to the hotspot
5. Access the web interface

### Customization

The hotspot configuration can be customized by:
- Modifying the `WiFiService` class
- Updating configuration files
- Changing environment variables
- Modifying the hostapd and dnsmasq configurations

## Support

For issues or questions regarding the hotspot functionality:
1. Check the application logs
2. Verify system requirements
3. Review the troubleshooting section
4. Check the main project documentation
