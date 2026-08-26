#!/usr/bin/env python3
"""
Command Line Interface for Motorised Store Control
Simple CLI to control the store from command line
"""

import sys
import time
import logging
import os
import json
import signal
import threading
from device_service import get_device_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration file for max process time
MAX_TIME_CONFIG_FILE = "/tmp/motorised_store_max_time.txt"
DEFAULT_MAX_TIME = 30.0  # 30 seconds default

def get_max_process_time():
    """Get maximum process time from config file or return default"""
    try:
        if os.path.exists(MAX_TIME_CONFIG_FILE):
            with open(MAX_TIME_CONFIG_FILE, 'r') as f:
                time_str = f.read().strip()
                max_time = float(time_str)
                if max_time > 0:  # Ensure positive value
                    return max_time
                else:
                    logger.warning(f"Invalid max time in config file: {time_str}, using default")
                    return DEFAULT_MAX_TIME
        else:
            # Create default config file
            with open(MAX_TIME_CONFIG_FILE, 'w') as f:
                f.write(str(DEFAULT_MAX_TIME))
            logger.info(f"Created default max time config file: {DEFAULT_MAX_TIME}s")
            return DEFAULT_MAX_TIME
    except Exception as e:
        logger.warning(f"Error reading max time config: {e}, using default {DEFAULT_MAX_TIME}s")
        return DEFAULT_MAX_TIME

# Progress bar functions removed - CLI now just waits for completion

# Simple signal handler for Ctrl+C
def signal_handler(signum, frame):
    """Handle Ctrl+C (SIGINT) to stop motor immediately"""
    print("\n\n⚠️  Emergency stop requested!")
    
    # Send emergency stop command
    try:
        command_file = "/tmp/motorised_store_command.txt"
        with open(command_file, 'w') as f:
            f.write("stop")
        print("Emergency stop command sent to device service")
    except Exception as e:
        print(f"Error sending emergency stop: {e}")
    
    print("Exiting CLI...")
    sys.exit(0)

# Set up signal handler for Ctrl+C
signal.signal(signal.SIGINT, signal_handler)

def show_help():
    """Show help message"""
    print("Motorised Store CLI Control")
    print("==========================")
    print("Usage: python3 cli_control.py <command>")
    print()
    print("Commands:")
    print("  up           - Move store to TOP (0% - fully open)")
    print("  down         - Move store to BOTTOM (100% - fully closed)")
    print("  to X         - Move store to specific position (0-100%)")
    print("  stop         - Stop motor")
    print("  status       - Show current status with position")
    print("  settime X    - Set maximum runtime to X seconds")
    print("  setpos X     - Manually set current position to X (0-100)")
    print("  calibrate    - Auto-calibrate timing by testing motor movement")
    print("  calibrate 0  - Set current position to TOP (0%) without moving motor")
    print("  calibrate 100 - Set current position to BOTTOM (100%) without moving motor")
    print("  help         - Show this help")
    print()
    max_time = get_max_process_time()
    print("Safety:")
    print("  • Press Ctrl+C during up/down operations to stop motor immediately")
    print(f"  • Motor automatically stops after {max_time} seconds maximum for safety")
    print(f"  • Max time configurable in: {MAX_TIME_CONFIG_FILE}")
    print()
    print("Examples:")
    print("  python3 cli_control.py up       # Move to top (0%)")
    print("  python3 cli_control.py down     # Move to bottom (100%)")
    print("  python3 cli_control.py to 50    # Move to 50% position")
    print("  python3 cli_control.py stop")
    print("  python3 cli_control.py status")
    print("  python3 cli_control.py settime 45")
    print("  python3 cli_control.py calibrate    # Auto-calibrate timing")
    print("  python3 cli_control.py calibrate 0  # Set position to top")
    print("  python3 cli_control.py calibrate 100 # Set position to bottom")

def get_status():
    """Get and display current status"""
    try:
        # Read status from file (inter-process communication)
        status_file = "/tmp/motorised_store_status.json"
        
        if not os.path.exists(status_file):
            print("Store Status:")
            print("  State: unknown")
            print("  Running: False")
            print("  Note: Device service is not running (start with standalone_runner.py)")
            return None
        
        # Read status from file
        with open(status_file, 'r') as f:
            status = json.load(f)
        
        # Check if status is recent (within 5 seconds)
        current_time = time.time()
        if current_time - status.get('timestamp', 0) > 5:
            print("Store Status:")
            print("  State: unknown")
            print("  Running: False")
            print("  Note: Device service appears to be stopped (status file is stale)")
            return None
        
        print("Store Status:")
        print(f"  State: {status['state']}")
        print(f"  Running: {status['running']}")
        
        # Display position information
        if 'position' in status and status['position'] is not None:
            position = status['position']
            print(f"  Position: {position:.1f}% (0=fully up, 100=fully down)")
        else:
            print("  Position: Unknown (calibration needed)")
        
        # Display calibration status
        if status.get('calibration_in_progress', False):
            print("  Status: Calibration in progress...")
        
        # Display movement progress if moving
        if 'movement_progress' in status:
            progress = status['movement_progress']
            elapsed = status.get('movement_elapsed', 0)
            max_time = status.get('movement_max_time', 0)
            remaining = max(0, max_time - elapsed)
            print(f"  Movement: {progress:.1f}% complete ({elapsed:.1f}s elapsed, {remaining:.1f}s remaining)")
        
        return status
    except Exception as e:
        print(f"Error getting status: {e}")
        return None

def wait_for_movement_completion(target_position=None):
    """Wait for movement to complete by monitoring device status"""
    status_file = "/tmp/motorised_store_status.json"
    start_time = time.time()
    max_wait_time = 60  # Maximum 60 seconds wait
    
    print("Movement in progress", end="", flush=True)
    
    while True:
        try:
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                print(f"\nTimeout waiting for movement completion after {max_wait_time}s")
                break
            
            # Check device status
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    status = json.load(f)
                
                state = status.get('state', 'unknown')
                position = status.get('position')
                
                # Show progress dots
                if int(elapsed * 2) % 2 == 0:
                    print(".", end="", flush=True)
                
                # Check if movement is complete
                if state in ['stopped', 'idle']:
                    if target_position is not None and position is not None:
                        print(f"\nMovement completed! Position: {position:.1f}%")
                        if abs(position - target_position) < 0.5:
                            print(f"✅ Successfully reached target position {target_position}%")
                        else:
                            print(f"⚠️  Position {position:.1f}% differs from target {target_position}%")
                    else:
                        print(f"\nMovement completed! Current state: {state}")
                    break
                
            time.sleep(0.5)
            
        except Exception as e:
            print(f"\nError monitoring movement: {e}")
            break
    
    print()  # Final newline

def control_motor(command, target_position=None):
    """Control the motor using file-based communication - wait for completion"""
    try:
        # Check if service is running by looking for status file
        status_file = "/tmp/motorised_store_status.json"
        if not os.path.exists(status_file):
            print("Error: Device service is not running!")
            print("Please start the device service first with: python3 standalone_runner.py")
            return False
        
        # Write command to command file
        command_file = "/tmp/motorised_store_command.txt"
        
        if command in ["up", "down", "stop"]:
            if target_position is not None:
                print(f"Sending command: {command.upper()} to position {target_position}%")
            else:
                print(f"Sending command: {command.upper()}")
            
            # Write command (with position if specified)
            command_str = command
            if target_position is not None:
                command_str = f"{command}:{target_position}"
            
            with open(command_file, 'w') as f:
                f.write(command_str)
            
            # Wait for command completion (like an API call)
            if command in ["up", "down"]:
                print("Waiting for movement to complete...")
                wait_for_movement_completion(target_position)
            else:
                print("Stop command sent")
                time.sleep(0.5)  # Brief wait for stop processing
            
            return True
        else:
            print(f"Unknown command: {command}")
            return False
            
    except Exception as e:
        print(f"Error controlling motor: {e}")
        return False

def set_max_time(time_value):
    """Set maximum process time in config file"""
    try:
        max_time = float(time_value)
        if max_time <= 0:
            print(f"Error: Time must be positive, got: {time_value}")
            return False
        
        with open(MAX_TIME_CONFIG_FILE, 'w') as f:
            f.write(str(max_time))
        
        print(f"Maximum runtime set to {max_time} seconds")
        print(f"Config saved to: {MAX_TIME_CONFIG_FILE}")
        return True
        
    except ValueError:
        print(f"Error: Invalid time value: {time_value}")
        return False
    except Exception as e:
        print(f"Error setting max time: {e}")
        return False

def set_position(position_value):
    """Manually set current position"""
    try:
        position = float(position_value)
        if not (0 <= position <= 100):
            print(f"Error: Position must be between 0 and 100, got: {position_value}")
            return False
        
        # Write position directly to position file
        position_file = "/tmp/motorised_store_position.txt"
        with open(position_file, 'w') as f:
            f.write(str(position))
        
        print(f"Position manually set to {position}%")
        print(f"Position saved to: {position_file}")
        print("Note: This overrides any automatic position tracking.")
        return True
        
    except ValueError:
        print(f"Error: Invalid position value: {position_value}")
        return False
    except Exception as e:
        print(f"Error setting position: {e}")
        return False

def monitor_gpio_buttons():
    """Monitor GPIO buttons for UP press and STOP detection"""
    GPIO = None
    try:
        # Import GPIO here to avoid issues on non-Pi systems during help/other commands
        import RPi.GPIO as GPIO
        
        # GPIO pins (matching device_service.py)
        button_up_pin = 25
        button_down_pin = 27
        
        # Setup GPIO for button monitoring
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(button_up_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(button_down_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        up_count = 0
        down_count = 0
        start_time = None
        
        print("Monitoring GPIO buttons...")
        print("Press the UP button to start timing")
        print("Press the DOWN button to stop timing")
        print("Press Ctrl+C to cancel")
        print()
        
        # Disable the global signal handler temporarily for GPIO monitoring
        original_handler = signal.signal(signal.SIGINT, signal.SIG_DFL)
        
        try:
            while True:
                # Read button states (using exact same logic as working run.py)
                up_button = GPIO.input(button_up_pin)
                down_button = GPIO.input(button_down_pin)
                
                # Handle UP button - exact logic from working run.py
                if (up_button == GPIO.HIGH) & (up_count == 1):
                    up_count = 0
                    if start_time is None:
                        start_time = time.time()
                        print(f"✓ UP button pressed! Timer started at {time.strftime('%H:%M:%S')}")
                        print("Now press the DOWN button when you want to stop timing...")
                elif (up_button == GPIO.HIGH) & (up_count == 0):
                    up_count = 1
                
                # Handle DOWN button - exact logic from working run.py  
                if (down_button == GPIO.HIGH) & (down_count == 1):
                    down_count = 0
                    if start_time is not None:
                        end_time = time.time()
                        measured_time = end_time - start_time
                        print(f"✓ DOWN button pressed! Timer stopped at {time.strftime('%H:%M:%S')}")
                        print(f"⏱️  Measured time: {measured_time:.1f} seconds")
                        return measured_time
                    else:
                        print("! DOWN button pressed, but timer was not started. Press UP first.")
                elif (down_button == GPIO.HIGH) & (down_count == 0):
                    down_count = 1
                
                time.sleep(0.1)  # 100ms polling
                
        except KeyboardInterrupt:
            print("\n\nCalibration cancelled by user")
            return None
        finally:
            # Restore original signal handler
            signal.signal(signal.SIGINT, original_handler)
            
    except ImportError:
        print("Error: RPi.GPIO not available. This command only works on Raspberry Pi.")
        return None
    except Exception as e:
        print(f"Error monitoring GPIO: {e}")
        return None
    finally:
        if GPIO is not None:
            try:
                GPIO.cleanup()
            except:
                pass

def to_position(target_position):
    """Move to specific position, automatically choosing direction"""
    try:
        # Get current position
        status_file = "/tmp/motorised_store_status.json"
        current_pos = 0.0
        
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                status = json.load(f)
            current_pos = status.get('position', 0.0)
            if current_pos is None:
                current_pos = 0.0
        
        print(f"Current position: {current_pos:.1f}%")
        print(f"Target position: {target_position:.1f}%")
        
        # Check if we're already at target
        if abs(current_pos - target_position) < 0.5:
            print(f"Already at target position ({current_pos:.1f}%)")
            return True
        
        # Determine direction
        if target_position > current_pos:
            direction = "down"
            print(f"Moving DOWN from {current_pos:.1f}% to {target_position:.1f}%")
        else:
            direction = "up"
            print(f"Moving UP from {current_pos:.1f}% to {target_position:.1f}%")
        
        # Use control_motor with the target position
        return control_motor(direction, target_position)
        
    except Exception as e:
        logger.error(f"Error in to_position: {e}")
        print(f"Error moving to position: {e}")
        return False

def manual_calibrate_position(position):
    """Manually set current position without moving motor"""
    try:
        position_file = "/tmp/motorised_store_position.txt"
        
        # Validate position
        if position not in [0, 100]:
            print("Error: Manual calibration only supports position 0 (top) or 100 (bottom)")
            return False
        
        # Set the position
        with open(position_file, 'w') as f:
            f.write(str(float(position)))
        
        position_name = "TOP" if position == 0 else "BOTTOM"
        print(f"✅ Manual calibration complete!")
        print(f"Position manually set to {position}% ({position_name})")
        print(f"Position saved to: {position_file}")
        
        # Show current status
        print("\nCurrent Status:")
        get_status()
        
        return True
        
    except Exception as e:
        logger.error(f"Error in manual_calibrate_position: {e}")
        print(f"Error setting position: {e}")
        return False

def calibrate_timing():
    """Auto-configure timing by testing motor movement"""
    try:
        print("=" * 60)
        print("MOTOR TIMING CONFIGURATION")
        print("=" * 60)
        print()
        
        # Check if service is running
        status_file = "/tmp/motorised_store_status.json"
        if not os.path.exists(status_file):
            print("Error: Device service is not running!")
            print("Please start the device service first with: python3 standalone_runner.py")
            return False
        
        # Get current max time
        current_max_time = get_max_process_time()
        print(f"Current maximum time setting: {current_max_time} seconds")
        print()
        
        print("STEP 1: Testing motor movement DOWN")
        print("-" * 40)
        print("The motor will move DOWN for the currently configured time.")
        print("This will help you see how long the current setting takes.")
        print()
        input("Press ENTER to start the DOWN movement test...")
        
        # Send DOWN command
        command_file = "/tmp/motorised_store_command.txt"
        with open(command_file, 'w') as f:
            f.write("down")
        
        print("\nMotor moving DOWN...")
        
        # Use simple loading bar for config (no signal handler interference)
        try:
            show_simple_loading_bar(current_max_time, "Testing DOWN movement")
        finally:
            # Always send stop command
            with open(command_file, 'w') as f:
                f.write("stop")
        
        print("STEP 2: Manual timing calibration")
        print("-" * 40)
        print("Now you will manually time how long it takes for your specific movement.")
        print()
        print("Instructions:")
        print("1. Press the UP button on your device to start the timer")
        print("2. Let the motor complete the movement you want to time")
        print("3. Press the DOWN button on your device to stop the timer")
        print()
        
        # Monitor GPIO buttons for manual timing
        measured_time = monitor_gpio_buttons()
        
        if measured_time is None:
            print("Configuration cancelled or failed.")
            return False
        
        print()
        print("STEP 3: Applying new configuration")
        print("-" * 40)
        print(f"Previous setting: {current_max_time} seconds")
        print(f"Measured time: {measured_time:.1f} seconds")
        
        # Ask for confirmation
        response = input(f"\nDo you want to set the maximum time to {measured_time:.1f} seconds? (y/N): ").lower()
        
        if response in ['y', 'yes']:
            # Update the config file
            with open(MAX_TIME_CONFIG_FILE, 'w') as f:
                f.write(str(measured_time))
            
            print(f"✓ Configuration updated!")
            print(f"✓ New maximum time: {measured_time:.1f} seconds")
            print(f"✓ Config saved to: {MAX_TIME_CONFIG_FILE}")
            print()
            print("Configuration complete! You can now use the new timing.")
            return True
        else:
            print("Configuration cancelled. No changes made.")
            return False
            
    except Exception as e:
        print(f"Error during configuration: {e}")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "help":
        show_help()
        sys.exit(0)
    
    if command == "status":
        get_status()
        sys.exit(0)
    
    if command == "settime":
        if len(sys.argv) != 3:
            print("Error: settime requires a time value")
            print("Usage: python3 cli_control.py settime <seconds>")
            print("Example: python3 cli_control.py settime 45")
            sys.exit(1)
        
        success = set_max_time(sys.argv[2])
        sys.exit(0 if success else 1)
    
    if command == "setpos":
        if len(sys.argv) != 3:
            print("Error: setpos requires a position value")
            print("Usage: python3 cli_control.py setpos <position>")
            print("Example: python3 cli_control.py setpos 0")
            sys.exit(1)
        
        success = set_position(sys.argv[2])
        sys.exit(0 if success else 1)
    
    if command == "calibrate":
        # Handle optional position argument for manual calibration
        if len(sys.argv) == 2:
            # No position argument - do auto-calibration
            success = calibrate_timing()
        elif len(sys.argv) == 3:
            # Position argument provided - do manual calibration
            try:
                position = int(sys.argv[2])
                if position not in [0, 100]:
                    print("Error: Manual calibration only supports position 0 or 100")
                    print("  calibrate 0   - Set current position to TOP (0%)")
                    print("  calibrate 100 - Set current position to BOTTOM (100%)")
                    sys.exit(1)
                success = manual_calibrate_position(position)
            except ValueError:
                print("Error: Invalid position value")
                print("  calibrate 0   - Set current position to TOP (0%)")
                print("  calibrate 100 - Set current position to BOTTOM (100%)")
                sys.exit(1)
        else:
            print("Error: Too many arguments for calibrate command")
            print("Usage:")
            print("  python3 cli_control.py calibrate      # Auto-calibrate timing")
            print("  python3 cli_control.py calibrate 0    # Set position to top")
            print("  python3 cli_control.py calibrate 100  # Set position to bottom")
            sys.exit(1)
        
        sys.exit(0 if success else 1)
    
    if command in ["up", "down"]:
        # up and down commands no longer accept position arguments
        if len(sys.argv) != 2:
            print(f"Error: {command} command takes no arguments")
            print(f"Use 'to X' command for specific positions")
            show_help()
            sys.exit(1)
        
        # up goes to 0%, down goes to 100%
        target_position = 0.0 if command == "up" else 100.0
        
        success = control_motor(command, target_position)
        if success:
            # Show status after command
            print()
            get_status()
        sys.exit(0 if success else 1)
    
    if command == "to":
        # Handle position argument
        if len(sys.argv) != 3:
            print("Error: 'to' command requires a position argument")
            print("Usage: python3 cli_control.py to <position>")
            show_help()
            sys.exit(1)
        
        try:
            target_position = float(sys.argv[2])
            if not (0 <= target_position <= 100):
                print("Error: Position must be between 0 and 100")
                sys.exit(1)
        except ValueError:
            print("Error: Invalid position value")
            sys.exit(1)
        
        success = to_position(target_position)
        if success:
            # Show status after command
            print()
            get_status()
        sys.exit(0 if success else 1)
    
    if command == "stop":
        if len(sys.argv) != 2:
            print("Error: stop command takes no arguments")
            sys.exit(1)
        
        success = control_motor(command)
        if success:
            # Show status after command
            print()
            get_status()
        sys.exit(0 if success else 1)
    
    print(f"Unknown command: {command}")
    show_help()
    sys.exit(1)

if __name__ == "__main__":
    main()
