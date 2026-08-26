# New Motorised Store Architecture

## Overview

The new architecture provides a clean, maintainable, and efficient solution for motorised store control with clear separation of concerns and better threading model.

## Key Improvements

### 1. **Clean Separation of Concerns**
- **`GPIOController`**: Handles all GPIO operations with precise timing
- **`PositionTracker`**: Manages position tracking and calibration
- **`StoreCore`**: Main state management and coordination
- **External Interfaces**: Clean APIs for CLI and webapp integration

### 2. **Better Threading Model**
- **Single Main Thread**: One control loop instead of multiple threads
- **Command Queue**: Thread-safe communication for external commands
- **Callback System**: Clean event handling for status changes

### 3. **GPIO Button Priority**
- **Physical buttons have absolute priority** over automated movements
- **Button press immediately stops** any automated movement
- **Hold-to-move behavior**: Buttons stay pressed, release stops movement
- **Automatic power cut handling**: When button is released, power is cut

### 4. **Precise Timing**
- **Movement timing starts/stops closest to GPIO operations**
- **Real-time position tracking** during movement
- **Accurate position calculation** based on movement time

### 5. **Multiple Integration Options**

#### **Option A: Direct Import (Same Process)**
```python
from new_device_service import get_store_core

store = get_store_core()
store.start()
store.move_up()
```

#### **Option B: CLI Interface (Subprocess)**
```bash
python3 new_cli_control.py up
python3 new_cli_control.py status
```

#### **Option C: Webapp Integration (Same Process)**
```python
from new_webapp_integration import get_webapp_integration

integration = get_webapp_integration()
result = await integration.open_device("user123")
```

## Architecture Components

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GPIOController │    │  PositionTracker  │    │    StoreCore     │
│                 │    │                  │    │                 │
│ • GPIO setup    │    │ • Position calc  │    │ • State mgmt    │
│ • Motor control │    │ • Calibration    │    │ • Command queue │
│ • Button read   │    │ • File I/O       │    │ • Main loop     │
│ • Timing        │    │ • Target tracking│    │ • Callbacks     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ External APIs   │
                    │                 │
                    │ • CLI Control   │
                    │ • Webapp Int.   │
                    │ • Direct Import │
                    └─────────────────┘
```

### State Management

```python
class StoreState(Enum):
    STOPPED = "stopped"
    MOVING_UP = "moving_up"
    MOVING_DOWN = "moving_down"
    CALIBRATING = "calibrating"
    ERROR = "error"
```

### Command System

```python
@dataclass
class Command:
    type: CommandType
    target_position: Optional[float] = None
    callback: Optional[Callable] = None
```

## Usage Examples

### 1. Standalone Mode
```bash
# Start the core service
python3 new_standalone_runner.py

# In another terminal, control via CLI
python3 new_cli_control.py status
python3 new_cli_control.py up
python3 new_cli_control.py to 50
```

### 2. Direct Integration
```python
from new_device_service import get_store_core

# Get the global store instance
store = get_store_core()
store.start()

# Control the store
store.move_up()
store.move_to_position(75.0)
store.stop_movement()

# Get status
def status_callback(status):
    print(f"Position: {status.position}%")

store.get_status(status_callback)
```

### 3. Webapp Integration
```python
from new_webapp_integration import get_webapp_integration

# Get integration instance
integration = get_webapp_integration()

# Control via webapp API
result = await integration.open_device("user123")
status = await integration.get_device_status()
```

## Key Features

### 1. **Button Priority System**
- Physical buttons **always** take priority over automated commands
- Button press **immediately stops** any automated movement
- **Hold-to-move**: Press and hold to move, release to stop
- **Automatic power cut**: When button released, motor stops immediately

### 2. **Precise Timing**
- Movement timing starts **exactly** when GPIO is activated
- Movement timing stops **exactly** when GPIO is deactivated
- **Real-time position updates** during movement
- **Accurate position calculation** based on actual movement time

### 3. **Clean State Management**
- **Single source of truth** for store state
- **Thread-safe** state updates
- **Callback system** for status changes
- **Clear state transitions**

### 4. **Multiple Integration Options**
- **Same process**: Direct import for maximum performance
- **Subprocess**: CLI interface for external control
- **Webapp**: Async API for web applications

## File Structure

```
src/raspberryapp/
├── new_device_service.py      # Core service with clean architecture
├── new_cli_control.py         # CLI interface
├── new_standalone_runner.py   # Standalone runner
├── new_webapp_integration.py  # Webapp integration
└── NEW_ARCHITECTURE.md        # This documentation
```

## Migration from Old Architecture

### Benefits of New Architecture:
1. **Cleaner Code**: Clear separation of concerns
2. **Better Performance**: Single main thread, no file IPC
3. **More Reliable**: Direct method calls instead of file-based communication
4. **Easier to Maintain**: Modular design with clear interfaces
5. **Better Threading**: Single control loop instead of multiple threads
6. **GPIO Priority**: Physical buttons always take priority
7. **Precise Timing**: Movement timing closest to GPIO operations

### Migration Steps:
1. **Test the new architecture** alongside the old one
2. **Update webapp integration** to use new_webapp_integration.py
3. **Replace CLI calls** to use new_cli_control.py
4. **Update standalone runner** to use new_standalone_runner.py
5. **Remove old files** once migration is complete

## Testing

### Test the Core Service:
```bash
python3 new_device_service.py
```

### Test CLI Interface:
```bash
python3 new_cli_control.py status
python3 new_cli_control.py up
python3 new_cli_control.py down
python3 new_cli_control.py to 50
```

### Test Webapp Integration:
```bash
python3 new_webapp_integration.py
```

### Test Standalone Runner:
```bash
python3 new_standalone_runner.py
```

## Conclusion

The new architecture provides a much cleaner, more maintainable, and more efficient solution for motorised store control. It addresses all the issues with the old architecture while providing multiple integration options for different use cases.

The key improvements are:
- **Clean separation of concerns**
- **Better threading model**
- **GPIO button priority**
- **Precise timing control**
- **Multiple integration options**
- **Easier maintenance and testing**
