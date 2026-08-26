#!/usr/bin/env python3
"""
New CLI Control for Motorised Store
Simple interface to the new store core
"""

import sys
import time
import json
import threading
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from new_device_service import get_store_core, StoreStatus
from models import CLIResponse, StatusData, MovementData, CalibrationData, PowerLossRecoveryData


class CLIControl:
    """Simple CLI interface to the store core"""
    
    def __init__(self):
        self.store = get_store_core()
        self.store.start()
        
        # Status callback for real-time updates
        self.store.add_status_callback(self._on_status_change)
        
        # Wait for store to be ready
        time.sleep(0.1)
    
    def _on_status_change(self, status: StoreStatus):
        """Handle status changes"""
        # Could be used for real-time updates if needed
        pass
    
    def move_up(self) -> CLIResponse:
        """Move store up"""
        try:
            # Get current position for response
            current_position = None
            def get_current_position(status: StoreStatus):
                nonlocal current_position
                current_position = status.position
            
            self.store.get_status(get_current_position)
            time.sleep(0.1)
            
            # Start movement
            self.store.move_up()
            self._wait_for_movement_complete()
            
            # Get final position
            final_position = None
            def get_final_position(status: StoreStatus):
                nonlocal final_position
                final_position = status.position
            
            self.store.get_status(get_final_position)
            time.sleep(0.1)
            
            movement_data = MovementData(
                action="move_up",
                target_position=0.0,
                estimated_duration=None,
                current_position=final_position
            )
            
            return CLIResponse(
                success=True,
                message="Store moved up successfully",
                timestamp=datetime.now().isoformat(),
                data=movement_data.__dict__
            )
            
        except Exception as e:
            return CLIResponse(
                success=False,
                message="Failed to move store up",
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    def move_down(self) -> CLIResponse:
        """Move store down"""
        try:
            # Get current position for response
            current_position = None
            def get_current_position(status: StoreStatus):
                nonlocal current_position
                current_position = status.position
            
            self.store.get_status(get_current_position)
            time.sleep(0.1)
            
            # Start movement
            self.store.move_down()
            self._wait_for_movement_complete()
            
            # Get final position
            final_position = None
            def get_final_position(status: StoreStatus):
                nonlocal final_position
                final_position = status.position
            
            self.store.get_status(get_final_position)
            time.sleep(0.1)
            
            movement_data = MovementData(
                action="move_down",
                target_position=100.0,
                estimated_duration=None,
                current_position=final_position
            )
            
            return CLIResponse(
                success=True,
                message="Store moved down successfully",
                timestamp=datetime.now().isoformat(),
                data=movement_data.__dict__
            )
            
        except Exception as e:
            return CLIResponse(
                success=False,
                message="Failed to move store down",
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    def move_to_position(self, position: float) -> CLIResponse:
        """Move to specific position"""
        try:
            # Get current position for response
            current_position = None
            def get_current_position(status: StoreStatus):
                nonlocal current_position
                current_position = status.position
            
            self.store.get_status(get_current_position)
            time.sleep(0.1)
            
            # Start movement
            self.store.move_to_position(position)
            self._wait_for_movement_complete()
            
            # Get final position
            final_position = None
            def get_final_position(status: StoreStatus):
                nonlocal final_position
                final_position = status.position
            
            self.store.get_status(get_final_position)
            time.sleep(0.1)
            
            movement_data = MovementData(
                action="move_to_position",
                target_position=position,
                estimated_duration=None,
                current_position=final_position
            )
            
            return CLIResponse(
                success=True,
                message=f"Store moved to position {position}% successfully",
                timestamp=datetime.now().isoformat(),
                data=movement_data.__dict__
            )
            
        except Exception as e:
            return CLIResponse(
                success=False,
                message=f"Failed to move store to position {position}%",
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    def stop(self) -> CLIResponse:
        """Stop movement"""
        try:
            self.store.stop_movement()
            time.sleep(0.5)  # Brief wait for stop
            
            return CLIResponse(
                success=True,
                message="Store movement stopped successfully",
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            return CLIResponse(
                success=False,
                message="Failed to stop store movement",
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    def get_status(self) -> CLIResponse:
        """Get current status"""
        try:
            status_result = {}
            
            def status_callback(status: StoreStatus):
                nonlocal status_result
                status_result = {
                    "state": status.state.value,
                    "position": status.position,
                    "is_moving": status.is_moving,
                    "target_position": status.target_position,
                    "calibration_in_progress": status.calibration_in_progress,
                    "last_updated": status.last_updated.isoformat()
                }
            
            self.store.get_status(status_callback)
            time.sleep(0.1)  # Wait for callback
            
            # Check for power loss recovery
            if self.store.is_power_loss_recovery_needed():
                power_loss_info = self.store.get_power_loss_info()
                status_result["power_loss_recovery"] = power_loss_info
            
            status_data = StatusData(
                state=status_result["state"],
                position=status_result["position"],
                is_moving=status_result["is_moving"],
                target_position=status_result["target_position"],
                calibration_in_progress=status_result["calibration_in_progress"],
                power_loss_recovery=status_result.get("power_loss_recovery")
            )
            
            return CLIResponse(
                success=True,
                message="Status retrieved successfully",
                timestamp=datetime.now().isoformat(),
                data=status_data.__dict__
            )
            
        except Exception as e:
            return CLIResponse(
                success=False,
                message="Failed to get store status",
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    def calibrate(self) -> CLIResponse:
        """Start calibration"""
        try:
            # Get current position for response
            current_position = None
            def get_current_position(status: StoreStatus):
                nonlocal current_position
                current_position = status.position
            
            self.store.get_status(get_current_position)
            time.sleep(0.1)
            
            # Start calibration
            self.store.calibrate()
            self._wait_for_movement_complete()
            
            # Get final position
            final_position = None
            def get_final_position(status: StoreStatus):
                nonlocal final_position
                final_position = status.position
            
            self.store.get_status(get_final_position)
            time.sleep(0.1)
            
            calibration_data = CalibrationData(
                action="calibrate",
                estimated_duration=30.0,
                current_position=final_position
            )
            
            return CLIResponse(
                success=True,
                message="Store calibration completed successfully",
                timestamp=datetime.now().isoformat(),
                data=calibration_data.__dict__
            )
            
        except Exception as e:
            return CLIResponse(
                success=False,
                message="Failed to calibrate store",
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    def _wait_for_movement_complete(self):
        """Wait for movement to complete"""
        start_time = time.time()
        max_wait = 60  # 60 seconds max wait
        
        while time.time() - start_time < max_wait:
            # Get status without printing
            status_result = {}
            def status_callback(status: StoreStatus):
                nonlocal status_result
                status_result = {
                    "is_moving": status.is_moving,
                    "position": status.position
                }
            
            self.store.get_status(status_callback)
            time.sleep(0.1)
            
            if not status_result.get("is_moving", False):
                return
            
            time.sleep(0.5)
        
        # Timeout reached
        raise Exception("Timeout waiting for movement completion")




def main():
    """Main function"""
    if len(sys.argv) < 2:
        help_response = CLIResponse(
            success=False,
            message="No command provided",
            timestamp=datetime.now().isoformat(),
            error="Usage: python3 new_cli_control.py <command>"
        )
        print(json.dumps(help_response.__dict__, indent=2))
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "help":
        help_response = CLIResponse(
            success=True,
            message="CLI Help",
            timestamp=datetime.now().isoformat(),
            data={
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
        )
        print(json.dumps(help_response.__dict__, indent=2))
        sys.exit(0)
    
    try:
        cli = CLIControl()
        
        if command == "status":
            response = cli.get_status()
            print(json.dumps(response.__dict__, indent=2))
        
        elif command == "up":
            response = cli.move_up()
            print(json.dumps(response.__dict__, indent=2))
        
        elif command == "down":
            response = cli.move_down()
            print(json.dumps(response.__dict__, indent=2))
        
        elif command == "stop":
            response = cli.stop()
            print(json.dumps(response.__dict__, indent=2))
        
        elif command == "calibrate":
            response = cli.calibrate()
            print(json.dumps(response.__dict__, indent=2))
        
        elif command == "to":
            if len(sys.argv) != 3:
                error_response = CLIResponse(
                    success=False,
                    message="'to' command requires a position argument",
                    timestamp=datetime.now().isoformat(),
                    error="Usage: python3 new_cli_control.py to <position>"
                )
                print(json.dumps(error_response.__dict__, indent=2))
                sys.exit(1)
            
            try:
                position = float(sys.argv[2])
                if not (0 <= position <= 100):
                    error_response = CLIResponse(
                        success=False,
                        message="Position must be between 0 and 100",
                        timestamp=datetime.now().isoformat(),
                        error=f"Invalid position: {position}"
                    )
                    print(json.dumps(error_response.__dict__, indent=2))
                    sys.exit(1)
                
                response = cli.move_to_position(position)
                print(json.dumps(response.__dict__, indent=2))
            except ValueError:
                error_response = CLIResponse(
                    success=False,
                    message="Invalid position value",
                    timestamp=datetime.now().isoformat(),
                    error=f"Could not parse position: {sys.argv[2]}"
                )
                print(json.dumps(error_response.__dict__, indent=2))
                sys.exit(1)
        
        else:
            error_response = CLIResponse(
                success=False,
                message=f"Unknown command: {command}",
                timestamp=datetime.now().isoformat(),
                error="Use 'help' command to see available commands"
            )
            print(json.dumps(error_response.__dict__, indent=2))
            sys.exit(1)
    
    except Exception as e:
        error_response = CLIResponse(
            success=False,
            message="CLI execution failed",
            timestamp=datetime.now().isoformat(),
            error=str(e)
        )
        print(json.dumps(error_response.__dict__, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
