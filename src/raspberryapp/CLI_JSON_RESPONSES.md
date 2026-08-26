# CLI JSON Responses - REST API Style

## Overview

The new CLI now returns structured JSON responses similar to REST API responses, making it easier to integrate with other systems and parse programmatically.

## Response Structure

All CLI responses follow this base structure:

```json
{
  "success": boolean,
  "message": string,
  "timestamp": string (ISO format),
  "data": object (optional),
  "error": string (optional)
}
```

## Command Examples

### 1. Help Command

```bash
python3 new_cli_control.py help
```

**Response:**
```json
{
  "success": true,
  "message": "CLI Help",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "commands": {
      "up": "Move store to TOP (0% - fully open)",
      "down": "Move store to BOTTOM (100% - fully closed)",
      "to X": "Move store to specific position (0-100%)",
      "stop": "Stop motor",
      "status": "Show current status with position",
      "calibrate": "Start position calibration",
      "help": "Show this help"
    },
    "examples": [
      "python3 new_cli_control.py up",
      "python3 new_cli_control.py down",
      "python3 new_cli_control.py to 50",
      "python3 new_cli_control.py stop",
      "python3 new_cli_control.py status",
      "python3 new_cli_control.py calibrate"
    ]
  }
}
```

### 2. Status Command

```bash
python3 new_cli_control.py status
```

**Normal Response:**
```json
{
  "success": true,
  "message": "Status retrieved successfully",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "state": "stopped",
    "position": 45.0,
    "is_moving": false,
    "target_position": null,
    "calibration_in_progress": false,
    "power_loss_recovery": null
  }
}
```

**Status with Power Loss Recovery:**
```json
{
  "success": true,
  "message": "Status retrieved successfully",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "state": "stopped",
    "position": 40.0,
    "is_moving": false,
    "target_position": null,
    "calibration_in_progress": false,
    "power_loss_recovery": {
      "recovery_needed": true,
      "last_direction": "up",
      "estimated_position": 40.0,
      "recommendation": "Please verify position manually and recalibrate if needed"
    }
  }
}
```

**Status During Movement:**
```json
{
  "success": true,
  "message": "Status retrieved successfully",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "state": "moving_up",
    "position": 45.0,
    "is_moving": true,
    "target_position": 30.0,
    "calibration_in_progress": false,
    "power_loss_recovery": null
  }
}
```

### 3. Move Up Command

```bash
python3 new_cli_control.py up
```

**Success Response:**
```json
{
  "success": true,
  "message": "Store moved up successfully",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "action": "move_up",
    "target_position": 0.0,
    "estimated_duration": null,
    "current_position": 0.0
  }
}
```

### 4. Move Down Command

```bash
python3 new_cli_control.py down
```

**Success Response:**
```json
{
  "success": true,
  "message": "Store moved down successfully",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "action": "move_down",
    "target_position": 100.0,
    "estimated_duration": null,
    "current_position": 100.0
  }
}
```

### 5. Move to Position Command

```bash
python3 new_cli_control.py to 50
```

**Success Response:**
```json
{
  "success": true,
  "message": "Store moved to position 50% successfully",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "action": "move_to_position",
    "target_position": 50.0,
    "estimated_duration": null,
    "current_position": 50.0
  }
}
```

### 6. Stop Command

```bash
python3 new_cli_control.py stop
```

**Success Response:**
```json
{
  "success": true,
  "message": "Store movement stopped successfully",
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

### 7. Calibrate Command

```bash
python3 new_cli_control.py calibrate
```

**Success Response:**
```json
{
  "success": true,
  "message": "Store calibration completed successfully",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "action": "calibrate",
    "estimated_duration": 30.0,
    "current_position": 0.0
  }
}
```

## Error Responses

### 1. No Command Provided

```bash
python3 new_cli_control.py
```

**Error Response:**
```json
{
  "success": false,
  "message": "No command provided",
  "timestamp": "2024-01-01T12:00:00.000000",
  "error": "Usage: python3 new_cli_control.py <command>"
}
```

### 2. Unknown Command

```bash
python3 new_cli_control.py invalid
```

**Error Response:**
```json
{
  "success": false,
  "message": "Unknown command: invalid",
  "timestamp": "2024-01-01T12:00:00.000000",
  "error": "Use 'help' command to see available commands"
}
```

### 3. Invalid Position

```bash
python3 new_cli_control.py to 150
```

**Error Response:**
```json
{
  "success": false,
  "message": "Position must be between 0 and 100",
  "timestamp": "2024-01-01T12:00:00.000000",
  "error": "Invalid position: 150"
}
```

### 4. Missing Position Argument

```bash
python3 new_cli_control.py to
```

**Error Response:**
```json
{
  "success": false,
  "message": "'to' command requires a position argument",
  "timestamp": "2024-01-01T12:00:00.000000",
  "error": "Usage: python3 new_cli_control.py to <position>"
}
```

### 5. Invalid Position Value

```bash
python3 new_cli_control.py to abc
```

**Error Response:**
```json
{
  "success": false,
  "message": "Invalid position value",
  "timestamp": "2024-01-01T12:00:00.000000",
  "error": "Could not parse position: abc"
}
```

### 6. Execution Error

```bash
python3 new_cli_control.py status
```

**Error Response (if store service not running):**
```json
{
  "success": false,
  "message": "CLI execution failed",
  "timestamp": "2024-01-01T12:00:00.000000",
  "error": "Store service not available"
}
```

## Data Models

### StatusData
```json
{
  "state": "stopped|moving_up|moving_down|calibrating|error",
  "position": 0.0-100.0 (or null),
  "is_moving": boolean,
  "target_position": 0.0-100.0 (or null),
  "calibration_in_progress": boolean,
  "power_loss_recovery": PowerLossRecoveryData (or null)
}
```

### MovementData
```json
{
  "action": "move_up|move_down|move_to_position",
  "target_position": 0.0-100.0 (or null),
  "estimated_duration": number (or null),
  "current_position": 0.0-100.0 (or null)
}
```

### CalibrationData
```json
{
  "action": "calibrate",
  "estimated_duration": 30.0,
  "current_position": 0.0-100.0 (or null)
}
```

### PowerLossRecoveryData
```json
{
  "recovery_needed": boolean,
  "last_direction": "up|down" (or null),
  "estimated_position": 0.0-100.0 (or null),
  "recommendation": string
}
```

## Integration Examples

### Python Integration
```python
import subprocess
import json

def call_cli(command):
    result = subprocess.run(
        ["python3", "new_cli_control.py", command],
        capture_output=True,
        text=True
    )
    return json.loads(result.stdout)

# Get status
status = call_cli("status")
if status["success"]:
    print(f"Position: {status['data']['position']}%")
else:
    print(f"Error: {status['error']}")

# Move to position
result = call_cli("to 50")
if result["success"]:
    print("Movement completed successfully")
else:
    print(f"Movement failed: {result['error']}")
```

### Shell Integration
```bash
#!/bin/bash

# Get status and extract position
POSITION=$(python3 new_cli_control.py status | jq -r '.data.position')
echo "Current position: $POSITION%"

# Move to 75% if position is less than 50%
if (( $(echo "$POSITION < 50" | bc -l) )); then
    echo "Moving to 75%..."
    python3 new_cli_control.py to 75
fi
```

### Node.js Integration
```javascript
const { exec } = require('child_process');
const util = require('util');
const execAsync = util.promisify(exec);

async function callCLI(command) {
    try {
        const { stdout } = await execAsync(`python3 new_cli_control.py ${command}`);
        return JSON.parse(stdout);
    } catch (error) {
        return JSON.parse(error.stdout);
    }
}

// Usage
async function main() {
    const status = await callCLI('status');
    if (status.success) {
        console.log(`Position: ${status.data.position}%`);
    } else {
        console.error(`Error: ${status.error}`);
    }
}
```

## Benefits

1. **Structured Data**: Easy to parse and process programmatically
2. **Consistent Format**: All responses follow the same structure
3. **Error Handling**: Clear error messages with structured format
4. **Integration Friendly**: Easy to integrate with other systems
5. **REST API Style**: Familiar format for web developers
6. **Timestamped**: All responses include timestamps
7. **Extensible**: Easy to add new fields to responses

## Migration from Old CLI

The old CLI returned plain text output. The new CLI returns JSON:

**Old (Plain Text):**
```
Store Status:
  State: stopped
  Position: 45.0%
  Moving: false
```

**New (JSON):**
```json
{
  "success": true,
  "message": "Status retrieved successfully",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "state": "stopped",
    "position": 45.0,
    "is_moving": false,
    "target_position": null,
    "calibration_in_progress": false,
    "power_loss_recovery": null
  }
}
```

This makes the CLI much more suitable for automation and integration with other systems.
