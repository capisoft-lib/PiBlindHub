# Motorised Store Device Service

A hybrid device service that can operate both standalone and integrated with the webapp, providing GPIO control for motorised store devices.

## Architecture Overview

The device service is designed with a modular architecture that supports two operational modes:

1. **Standalone Mode**: Direct GPIO control with physical button monitoring (maintains original `run.py` functionality)
2. **Integrated Mode**: Webapp-controlled via API calls while maintaining local button functionality

## Components

### Core Components

- **`device_service.py`**: Main device service with GPIO control and state management
- **`models.py`**: Data models and enums (DeviceState, MotorDirection)
- **`standalone_runner.py`**: Standalone application that maintains original functionality
- **`cli_control.py`**: Command-line interface for external control
- **`start_device_service.py`**: Service startup script for webapp integration

### Key Classes

#### `DeviceService`
- Main service class that manages GPIO control
- Handles motor control (up, down, stop)
- Monitors physical buttons
- Manages device state and status
- Provides callback system for external integration

#### `MotorController`
- Controls motor hardware via GPIO pins
- Handles motor direction (up/down/stop)
- Ensures safe motor operation

#### `ButtonMonitor`
- Monitors physical buttons for manual control
- Handles button debouncing and state tracking
- Provides action callbacks


## Usage

### Standalone Mode

Run the device service independently with physical button control:

```bash
# Using the standalone runner (recommended)
python src/raspberryapp/standalone_runner.py

# Using the command-line interface
python3 src/raspberryapp/cli_control.py status
```

### Service Mode

Start the device service for external control:

```bash
# Start device service
python src/raspberryapp/start_device_service.py --device-id store_001

# Use the command-line interface (requires running service)
python3 src/raspberryapp/cli_control.py up
```

### Command-Line Interface

The `cli_control.py` script provides external control interface:

```bash
# Open device (move up)
python3 src/raspberryapp/cli_control.py up

# Close device (move down)
python3 src/raspberryapp/cli_control.py down

# Stop device
python3 src/raspberryapp/cli_control.py stop

# Get device status
python3 src/raspberryapp/cli_control.py status

# Move to specific position
python3 src/raspberryapp/cli_control.py to 50

# Calibrate timing
python3 src/raspberryapp/cli_control.py calibrate
```

## GPIO Configuration

The device service uses the following GPIO pins:

- **GPIO 23**: Motor UP control (output)
- **GPIO 24**: Motor DOWN control (output)
- **GPIO 25**: UP button (input, pull-down)
- **GPIO 27**: DOWN button (input, pull-down)

## Device States

The device can be in the following states:

- `STOPPED`: Motor is stopped
- `OPENING`: Motor is moving up (opening)
- `CLOSING`: Motor is moving down (closing)
- `OPEN`: Device is fully open
- `CLOSED`: Device is fully closed
- `ERROR`: Device is in error state

## Integration with Webapp

The webapp uses subprocess communication with `cli_control.py`:

```python
from src.webapp.services.device_controller import DeviceController

controller = DeviceController()
result = await controller.open_device("store_001")
```

The device controller calls `python3 cli_control.py up` for opening, `python3 cli_control.py down` for closing, etc.

## Configuration

### Environment Variables

- `DEVICE_ID`: Device identifier (default: "store_001")
- `MQTT_BROKER`: MQTT broker host (default: "localhost")
- `MQTT_PORT`: MQTT broker port (default: 1883)

### Settings

The device service can be configured through the webapp settings:

```python
# In webapp config
device_default_id = "store_001"
device_timeout = 30
```

## Error Handling

The device service includes comprehensive error handling:

- **GPIO Errors**: Automatic cleanup and error reporting
- **Communication Errors**: Fallback mechanisms and retry logic
- **State Errors**: Error state management and recovery
- **Timeout Errors**: Operation timeout handling

## Logging

The device service provides detailed logging:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

Log levels:
- `DEBUG`: Detailed operation information
- `INFO`: General operation information
- `WARNING`: Non-critical issues
- `ERROR`: Critical errors

## Safety Features

- **Emergency Stop**: Physical buttons provide immediate stop functionality
- **GPIO Cleanup**: Automatic cleanup on shutdown
- **State Validation**: State consistency checks
- **Timeout Protection**: Operation timeouts prevent hanging

## Development

### Adding New Features

1. **New Motor Commands**: Add methods to `MotorController`
2. **New Button Actions**: Extend `ButtonMonitor`
3. **New States**: Add to `DeviceState` enum
4. **New Callbacks**: Extend callback system in `DeviceService`

### Testing

```bash
# Test standalone mode
python src/raspberryapp/standalone_runner.py

# Test webapp integration
python src/raspberryapp/start_device_service.py --verbose

# Test command-line interface
python3 src/raspberryapp/cli_control.py status
```

## Migration from Original run.py

The new architecture maintains full compatibility with the original `run.py` functionality:

1. **Physical Buttons**: Same GPIO pins and behavior
2. **Motor Control**: Same motor control logic
3. **State Management**: Enhanced state tracking
4. **Error Handling**: Improved error handling and recovery

## Troubleshooting

### Common Issues

1. **GPIO Permission Errors**: Ensure user has GPIO access
2. **Import Errors**: Check Python path and dependencies
3. **MQTT Connection Issues**: Verify broker configuration
4. **Button Not Working**: Check GPIO pin configuration

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
python3 src/raspberryapp/cli_control.py status
```

## Dependencies

- `RPi.GPIO`: GPIO control for Raspberry Pi
- `asyncio`: Asynchronous operations
- `threading`: Thread management
- `logging`: Logging system
- `json`: JSON serialization
- `datetime`: Timestamp handling

## License

This device service is part of PiBlindHub.
