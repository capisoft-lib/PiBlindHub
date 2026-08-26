# MSM Broadcast Discovery Protocol

## Overview

The legacy MSM broadcast discovery protocol used by PiBlindHub enables automatic discovery of devices on the local network. This protocol allows devices to announce their presence and respond to discovery requests from other devices or management tools.

## Protocol Version

Current Version: **1.0**

## Network Configuration

- **Discovery Port**: 15002 (UDP)
- **Response Port**: 15003 (UDP)
- **Transport**: UDP Broadcast
- **Encoding**: JSON over UTF-8

## Message Format

All messages are JSON objects with the following common structure:

```json
{
    "protocol": "MSM_DISCOVERY",
    "version": "1.0",
    "request_id": "uuid-string",
    "type": "message_type",
    "timestamp": "ISO-8601-timestamp",
    "data": { ... }
}
```

### Common Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `protocol` | string | Yes | Always "MSM_DISCOVERY" |
| `version` | string | Yes | Protocol version (e.g., "1.0") |
| `request_id` | string | Yes | Unique identifier for request/response pairing |
| `type` | string | Yes | Message type (see types below) |
| `timestamp` | string | Yes | ISO-8601 timestamp of message creation |

## Message Types

### 1. Discovery Request

Sent by clients to discover MSM devices on the network.

```json
{
    "protocol": "MSM_DISCOVERY",
    "version": "1.0",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "discovery",
    "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Fields:**
- No additional fields required

**Behavior:**
- Broadcast to `255.255.255.255:15002`
- All MSM devices listening will respond
- Response sent to `client_ip:15003`

### 2. Discovery Response

Sent by MSM devices in response to discovery requests.

```json
{
    "protocol": "MSM_DISCOVERY",
    "version": "1.0",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "discovery_response",
    "device_info": {
        "device_id": "12345678-1234-1234-1234-123456789abc",
        "device_name": "PiBlindHub",
        "device_type": "store_manager",
        "version": "1.0.0",
        "capabilities": [
            "motor_control",
            "web_interface",
            "mqtt_communication",
            "hotspot_mode"
        ],
        "status": "online"
    },
    "network_status": {
        "wifi_connected": true,
        "hotspot_active": false,
        "current_ssid": "MyHomeNetwork",
        "device_ip": "192.168.1.100"
    },
    "timestamp": "2024-01-15T10:30:00.100Z"
}
```

**Fields:**

#### device_info
| Field | Type | Description |
|-------|------|-------------|
| `device_id` | string | Unique device identifier (UUID) |
| `device_name` | string | Human-readable device name |
| `device_type` | string | Device type identifier |
| `version` | string | Device firmware/software version |
| `capabilities` | array | List of device capabilities |
| `status` | string | Device status ("online", "offline", "error") |

#### network_status
| Field | Type | Description |
|-------|------|-------------|
| `wifi_connected` | boolean | Whether device is connected to WiFi |
| `hotspot_active` | boolean | Whether device is running hotspot |
| `current_ssid` | string | Current WiFi network name (if connected) |
| `device_ip` | string | Device's IP address |

### 3. Ping Request

Simple ping to check if a device is alive.

```json
{
    "protocol": "MSM_DISCOVERY",
    "version": "1.0",
    "request_id": "550e8400-e29b-41d4-a716-446655440001",
    "type": "ping",
    "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### 4. Ping Response

Response to ping request.

```json
{
    "protocol": "MSM_DISCOVERY",
    "version": "1.0",
    "request_id": "550e8400-e29b-41d4-a716-446655440001",
    "type": "ping_response",
    "status": "ok",
    "timestamp": "2024-01-15T10:30:00.050Z"
}
```

## Device Capabilities

The following capabilities may be reported by MSM devices:

| Capability | Description |
|------------|-------------|
| `motor_control` | Device can control motorised store mechanisms |
| `web_interface` | Device provides web-based management interface |
| `mqtt_communication` | Device supports MQTT communication |
| `hotspot_mode` | Device can operate as WiFi hotspot |
| `broadcast_discovery` | Device supports broadcast discovery protocol |
| `remote_control` | Device supports remote control operations |
| `sensor_monitoring` | Device has sensor monitoring capabilities |

## Implementation Examples

### Python Client Example

```python
import socket
import json
import uuid
from datetime import datetime

def discover_msm_devices():
    # Create discovery request
    request = {
        "protocol": "MSM_DISCOVERY",
        "version": "1.0",
        "request_id": str(uuid.uuid4()),
        "type": "discovery",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Send broadcast request
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    request_data = json.dumps(request).encode('utf-8')
    sock.sendto(request_data, ('255.255.255.255', 15002))
    
    # Listen for responses
    sock.bind(('', 15003))
    sock.settimeout(5.0)  # 5 second timeout
    
    devices = []
    try:
        while True:
            data, addr = sock.recvfrom(1024)
            response = json.loads(data.decode('utf-8'))
            
            if (response.get('protocol') == 'MSM_DISCOVERY' and 
                response.get('type') == 'discovery_response'):
                devices.append({
                    'address': addr[0],
                    'device_info': response.get('device_info'),
                    'network_status': response.get('network_status')
                })
    except socket.timeout:
        pass
    finally:
        sock.close()
    
    return devices

# Usage
devices = discover_msm_devices()
for device in devices:
    print(f"Found device: {device['device_info']['device_name']} at {device['address']}")
```

### JavaScript Client Example

```javascript
const dgram = require('dgram');

function discoverMSMDevices() {
    return new Promise((resolve, reject) => {
        const client = dgram.createSocket('udp4');
        const devices = [];
        
        // Create discovery request
        const request = {
            protocol: 'MSM_DISCOVERY',
            version: '1.0',
            request_id: require('crypto').randomUUID(),
            type: 'discovery',
            timestamp: new Date().toISOString()
        };
        
        // Send broadcast
        const requestData = Buffer.from(JSON.stringify(request));
        client.send(requestData, 15002, '255.255.255.255', (err) => {
            if (err) {
                reject(err);
                return;
            }
            
            // Listen for responses
            client.bind(15003);
            client.setTimeout(5000); // 5 second timeout
            
            client.on('message', (data, rinfo) => {
                try {
                    const response = JSON.parse(data.toString());
                    
                    if (response.protocol === 'MSM_DISCOVERY' && 
                        response.type === 'discovery_response') {
                        devices.push({
                            address: rinfo.address,
                            device_info: response.device_info,
                            network_status: response.network_status
                        });
                    }
                } catch (e) {
                    console.error('Invalid response:', e);
                }
            });
            
            client.on('timeout', () => {
                client.close();
                resolve(devices);
            });
        });
    });
}

// Usage
discoverMSMDevices().then(devices => {
    devices.forEach(device => {
        console.log(`Found device: ${device.device_info.device_name} at ${device.address}`);
    });
});
```

## Security Considerations

1. **Network Scope**: Discovery is limited to the local network segment
2. **No Authentication**: Protocol does not include authentication (by design for local discovery)
3. **Information Disclosure**: Responses include device capabilities and network status
4. **Firewall**: Ensure UDP ports 15002 and 15003 are open for discovery to work

## Error Handling

### Invalid Messages
- Devices should ignore malformed JSON
- Devices should ignore messages with unsupported protocol versions
- Devices should ignore messages with unknown types

### Network Errors
- Implement appropriate timeouts for discovery requests
- Handle network unreachable scenarios gracefully
- Log discovery failures for debugging

## Future Extensions

### Version 1.1 (Planned)
- Device status queries (battery, temperature, etc.)
- Configuration parameter requests
- Remote command execution (with authentication)

### Version 1.2 (Planned)
- Multicast support for larger networks
- Device grouping and management
- Encrypted communication for sensitive operations

## Troubleshooting

### Common Issues

1. **No devices found**
   - Check firewall settings
   - Verify network connectivity
   - Ensure devices have discovery enabled

2. **Partial responses**
   - Check for network congestion
   - Verify UDP port availability
   - Check device power and network status

3. **Invalid responses**
   - Verify protocol version compatibility
   - Check JSON formatting
   - Ensure proper encoding (UTF-8)

### Debug Mode

Enable debug logging to see detailed discovery traffic:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show all discovery requests and responses for troubleshooting.
