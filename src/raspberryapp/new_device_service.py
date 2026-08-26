#!/usr/bin/env python3
"""
New Motorised Store Device Service - Clean Architecture
Core service with clear separation of concerns and better threading model
"""

import RPi.GPIO as GPIO
import time
import threading
import logging
import json
import os
from enum import Enum
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import queue
import signal
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StoreState(Enum):
    """Store state enumeration"""
    STOPPED = "stopped"
    MOVING_UP = "moving_up"
    MOVING_DOWN = "moving_down"
    CALIBRATING = "calibrating"
    ERROR = "error"


class CommandType(Enum):
    """Command types for external control"""
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    MOVE_TO_POSITION = "move_to_position"
    STOP = "stop"
    GET_STATUS = "get_status"
    CALIBRATE = "calibrate"


@dataclass
class StoreStatus:
    """Store status data structure"""
    state: StoreState
    position: Optional[float]  # 0-100, None if unknown
    is_moving: bool
    movement_start_time: Optional[float]
    target_position: Optional[float]
    calibration_in_progress: bool
    last_updated: datetime


@dataclass
class Command:
    """Command structure for external control"""
    type: CommandType
    target_position: Optional[float] = None
    callback: Optional[Callable] = None


class GPIOController:
    """Handles all GPIO operations with precise timing"""
    
    def __init__(self):
        # GPIO pins
        self.motor_up_pin = 23
        self.motor_down_pin = 24
        self.button_up_pin = 25
        self.button_down_pin = 27
        
        # Timing tracking
        self.movement_start_time: Optional[float] = None
        self.movement_lock = threading.Lock()
        
        self._setup_gpio()
    
    def _setup_gpio(self):
        """Setup GPIO pins"""
        try:
            GPIO.setmode(GPIO.BCM)
            
            # Motor pins (output)
            GPIO.setup(self.motor_up_pin, GPIO.OUT)
            GPIO.setup(self.motor_down_pin, GPIO.OUT)
            
            # Button pins (input with pull-down)
            GPIO.setup(self.button_up_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(self.button_down_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            
            # Start with motor stopped
            self.stop_motor()
            
            logger.info("GPIO setup completed")
            
        except Exception as e:
            logger.error(f"GPIO setup failed: {e}")
            raise
    
    def start_movement_up(self) -> float:
        """Start moving up and return start time"""
        with self.movement_lock:
            GPIO.output(self.motor_up_pin, GPIO.HIGH)
            GPIO.output(self.motor_down_pin, GPIO.LOW)
            self.movement_start_time = time.time()
            logger.info("Motor started moving UP")
            return self.movement_start_time
    
    def start_movement_down(self) -> float:
        """Start moving down and return start time"""
        with self.movement_lock:
            GPIO.output(self.motor_up_pin, GPIO.LOW)
            GPIO.output(self.motor_down_pin, GPIO.HIGH)
            self.movement_start_time = time.time()
            logger.info("Motor started moving DOWN")
            return self.movement_start_time
    
    def stop_motor(self):
        """Stop motor immediately"""
        with self.movement_lock:
            GPIO.output(self.motor_up_pin, GPIO.LOW)
            GPIO.output(self.motor_down_pin, GPIO.LOW)
            self.movement_start_time = None
            logger.info("Motor stopped")
    
    def get_movement_time(self) -> Optional[float]:
        """Get current movement time in seconds"""
        with self.movement_lock:
            if self.movement_start_time is not None:
                return time.time() - self.movement_start_time
            return None
    
    def is_moving(self) -> bool:
        """Check if motor is currently moving"""
        with self.movement_lock:
            return self.movement_start_time is not None
    
    def read_buttons(self) -> tuple[bool, bool]:
        """Read button states (up_pressed, down_pressed)"""
        up_pressed = GPIO.input(self.button_up_pin) == GPIO.HIGH
        down_pressed = GPIO.input(self.button_down_pin) == GPIO.HIGH
        return up_pressed, down_pressed
    
    def cleanup(self):
        """Cleanup GPIO resources"""
        try:
            self.stop_motor()
            GPIO.cleanup()
            logger.info("GPIO cleanup completed")
        except Exception as e:
            logger.error(f"GPIO cleanup error: {e}")


class PositionTracker:
    """Handles position tracking and calibration"""
    
    def __init__(self, gpio_controller: GPIOController):
        self.gpio = gpio_controller
        self.current_position: Optional[float] = None
        self.target_position: Optional[float] = None
        self.calibration_in_progress = False
        self.position_lock = threading.Lock()
        
        # Power shutdown recovery
        self.last_movement_direction: Optional[str] = None
        self.last_movement_start_time: Optional[float] = None
        self.power_loss_recovery_needed = False
        
        # Load position and recovery data from files
        self._load_position()
        self._check_power_loss_recovery()
    
    def _load_position(self):
        """Load position from file"""
        try:
            position_file = "/tmp/motorised_store_position.txt"
            if os.path.exists(position_file):
                with open(position_file, 'r') as f:
                    position = float(f.read().strip())
                    if 0 <= position <= 100:
                        with self.position_lock:
                            self.current_position = position
                        logger.info(f"Position loaded: {position}%")
                        return
        except Exception as e:
            logger.error(f"Error loading position: {e}")
        
        # No valid position found
        with self.position_lock:
            self.current_position = None
        logger.info("No valid position found, calibration needed")
    
    def _check_power_loss_recovery(self):
        """Check if power loss recovery is needed"""
        try:
            recovery_file = "/tmp/motorised_store_recovery.json"
            if os.path.exists(recovery_file):
                with open(recovery_file, 'r') as f:
                    recovery_data = json.load(f)
                    
                    # Check if we were in the middle of movement
                    if recovery_data.get('movement_in_progress', False):
                        self.power_loss_recovery_needed = True
                        self.last_movement_direction = recovery_data.get('direction')
                        self.last_movement_start_time = recovery_data.get('start_time')
                        
                        logger.warning(f"Power loss detected during {self.last_movement_direction} movement!")
                        logger.warning("Position may be inaccurate - manual verification recommended")
                        
                        # Calculate estimated position based on movement time
                        if self.last_movement_start_time:
                            movement_time = time.time() - self.last_movement_start_time
                            self._estimate_position_after_power_loss(movement_time)
                    
                    # Clean up recovery file
                    os.remove(recovery_file)
                    
        except Exception as e:
            logger.error(f"Error checking power loss recovery: {e}")
    
    def _estimate_position_after_power_loss(self, movement_time: float):
        """Estimate position after power loss during movement"""
        try:
            if self.current_position is None:
                return
            
            # Get max time for calculation
            max_time_file = "/tmp/motorised_store_max_time.txt"
            if os.path.exists(max_time_file):
                with open(max_time_file, 'r') as f:
                    max_time = float(f.read().strip())
            else:
                max_time = 30.0  # Default
            
            # Calculate position change
            movement_percentage = (movement_time / max_time) * 100
            
            with self.position_lock:
                if self.last_movement_direction == "up":
                    self.current_position = max(0, self.current_position - movement_percentage)
                elif self.last_movement_direction == "down":
                    self.current_position = min(100, self.current_position + movement_percentage)
                
                self._save_position()
                logger.warning(f"Estimated position after power loss: {self.current_position:.1f}%")
                logger.warning("Please verify position manually and recalibrate if needed")
                
        except Exception as e:
            logger.error(f"Error estimating position after power loss: {e}")
    
    def _save_recovery_data(self, direction: str, start_time: float):
        """Save recovery data for power loss detection"""
        try:
            recovery_data = {
                "movement_in_progress": True,
                "direction": direction,
                "start_time": start_time,
                "timestamp": time.time()
            }
            
            recovery_file = "/tmp/motorised_store_recovery.json"
            with open(recovery_file, 'w') as f:
                json.dump(recovery_data, f)
                
        except Exception as e:
            logger.error(f"Error saving recovery data: {e}")
    
    def _clear_recovery_data(self):
        """Clear recovery data when movement completes"""
        try:
            recovery_file = "/tmp/motorised_store_recovery.json"
            if os.path.exists(recovery_file):
                os.remove(recovery_file)
        except Exception as e:
            logger.error(f"Error clearing recovery data: {e}")
    
    def _save_position(self):
        """Save position to file"""
        try:
            with self.position_lock:
                if self.current_position is not None:
                    position_file = "/tmp/motorised_store_position.txt"
                    with open(position_file, 'w') as f:
                        f.write(str(self.current_position))
        except Exception as e:
            logger.error(f"Error saving position: {e}")
    
    def start_calibration(self):
        """Start position calibration"""
        with self.position_lock:
            self.calibration_in_progress = True
            self.current_position = 0.0  # Assume we start at top
        self._save_position()
        logger.info("Calibration started - position set to 0%")
    
    def finish_calibration(self):
        """Finish calibration"""
        with self.position_lock:
            self.calibration_in_progress = False
        logger.info("Calibration completed")
    
    def update_position_from_movement(self, direction: str, movement_time: float):
        """Update position based on movement time"""
        if self.calibration_in_progress:
            return
        
        try:
            # Get max time for calculation
            max_time_file = "/tmp/motorised_store_max_time.txt"
            if os.path.exists(max_time_file):
                with open(max_time_file, 'r') as f:
                    max_time = float(f.read().strip())
            else:
                max_time = 30.0  # Default
            
            # Calculate position change
            movement_percentage = (movement_time / max_time) * 100
            
            with self.position_lock:
                if self.current_position is not None:
                    if direction == "up":
                        self.current_position = max(0, self.current_position - movement_percentage)
                    else:  # down
                        self.current_position = min(100, self.current_position + movement_percentage)
                    
                    self._save_position()
                    logger.info(f"Position updated to {self.current_position:.1f}%")
                    
        except Exception as e:
            logger.error(f"Error updating position: {e}")
    
    def set_position(self, position: float):
        """Manually set position"""
        with self.position_lock:
            self.current_position = max(0, min(100, position))
        self._save_position()
        logger.info(f"Position manually set to {position}%")
    
    def get_position(self) -> Optional[float]:
        """Get current position"""
        with self.position_lock:
            return self.current_position
    
    def set_target(self, target: float):
        """Set target position"""
        with self.position_lock:
            self.target_position = max(0, min(100, target))
    
    def get_target(self) -> Optional[float]:
        """Get target position"""
        with self.position_lock:
            return self.target_position
    
    def clear_target(self):
        """Clear target position"""
        with self.position_lock:
            self.target_position = None


class StoreCore:
    """Core store management with clean state handling"""
    
    def __init__(self):
        self.gpio = GPIOController()
        self.position_tracker = PositionTracker(self.gpio)
        
        # State management
        self.state = StoreState.STOPPED
        self.state_lock = threading.Lock()
        
        # Command queue for external control
        self.command_queue = queue.Queue()
        self.command_lock = threading.Lock()
        
        # Button state tracking
        self.button_up_pressed = False
        self.button_down_pressed = False
        self.last_button_check = time.time()
        
        # Threading
        self.running = True
        self.main_thread = None
        
        # Callbacks
        self.status_callbacks: list[Callable[[StoreStatus], None]] = []
        
        logger.info("Store core initialized")
    
    def add_status_callback(self, callback: Callable[[StoreStatus], None]):
        """Add status change callback"""
        self.status_callbacks.append(callback)
    
    def _notify_status_change(self, status: StoreStatus):
        """Notify all status callbacks"""
        for callback in self.status_callbacks:
            try:
                callback(status)
            except Exception as e:
                logger.error(f"Status callback error: {e}")
    
    def _get_status(self) -> StoreStatus:
        """Get current store status"""
        with self.state_lock:
            return StoreStatus(
                state=self.state,
                position=self.position_tracker.get_position(),
                is_moving=self.gpio.is_moving(),
                movement_start_time=self.gpio.movement_start_time,
                target_position=self.position_tracker.get_target(),
                calibration_in_progress=self.position_tracker.calibration_in_progress,
                last_updated=datetime.now()
            )
    
    def _set_state(self, new_state: StoreState):
        """Set new state and notify callbacks"""
        with self.state_lock:
            if self.state != new_state:
                self.state = new_state
                logger.info(f"State changed to: {new_state.value}")
                
                # Notify callbacks
                status = self._get_status()
                self._notify_status_change(status)
    
    def _handle_button_press(self, up_pressed: bool, down_pressed: bool):
        """Handle button press - PRIORITY over automated movements"""
        # If any button is pressed, stop any automated movement
        if (up_pressed or down_pressed) and self.state in [StoreState.MOVING_UP, StoreState.MOVING_DOWN]:
            logger.info("Button pressed - stopping automated movement")
            self._stop_movement()
        
        # Handle button states
        if up_pressed and not self.button_up_pressed:
            # UP button just pressed
            self.button_up_pressed = True
            logger.info("UP button pressed - starting movement")
            self._start_movement_up()
            
        elif not up_pressed and self.button_up_pressed:
            # UP button just released
            self.button_up_pressed = False
            logger.info("UP button released - stopping movement")
            self._stop_movement()
        
        if down_pressed and not self.button_down_pressed:
            # DOWN button just pressed
            self.button_down_pressed = True
            logger.info("DOWN button pressed - starting movement")
            self._start_movement_down()
            
        elif not down_pressed and self.button_down_pressed:
            # DOWN button just released
            self.button_down_pressed = False
            logger.info("DOWN button released - stopping movement")
            self._stop_movement()
    
    def _start_movement_up(self):
        """Start moving up"""
        if self.state == StoreState.MOVING_DOWN:
            self._stop_movement()
        
        start_time = self.gpio.start_movement_up()
        self.position_tracker._save_recovery_data("up", start_time)
        self._set_state(StoreState.MOVING_UP)
    
    def _start_movement_down(self):
        """Start moving down"""
        if self.state == StoreState.MOVING_UP:
            self._stop_movement()
        
        start_time = self.gpio.start_movement_down()
        self.position_tracker._save_recovery_data("down", start_time)
        self._set_state(StoreState.MOVING_DOWN)
    
    def _stop_movement(self):
        """Stop movement and update position"""
        if self.gpio.is_moving():
            movement_time = self.gpio.get_movement_time()
            if movement_time and movement_time > 0:
                # Update position based on movement
                if self.state == StoreState.MOVING_UP:
                    self.position_tracker.update_position_from_movement("up", movement_time)
                elif self.state == StoreState.MOVING_DOWN:
                    self.position_tracker.update_position_from_movement("down", movement_time)
        
        # Clear recovery data when movement completes
        self.position_tracker._clear_recovery_data()
        
        self.gpio.stop_motor()
        self._set_state(StoreState.STOPPED)
    
    def _process_command(self, command: Command):
        """Process external command"""
        try:
            if command.type == CommandType.MOVE_UP:
                if not (self.button_up_pressed or self.button_down_pressed):
                    self._start_movement_up()
                    
            elif command.type == CommandType.MOVE_DOWN:
                if not (self.button_up_pressed or self.button_down_pressed):
                    self._start_movement_down()
                    
            elif command.type == CommandType.MOVE_TO_POSITION:
                if command.target_position is not None:
                    self._move_to_position(command.target_position)
                    
            elif command.type == CommandType.STOP:
                self._stop_movement()
                
            elif command.type == CommandType.GET_STATUS:
                status = self._get_status()
                if command.callback:
                    command.callback(status)
                    
            elif command.type == CommandType.CALIBRATE:
                self._start_calibration()
            
        except Exception as e:
            logger.error(f"Error processing command {command.type}: {e}")
    
    def _move_to_position(self, target: float):
        """Move to specific position"""
        current = self.position_tracker.get_position()
        if current is None:
            logger.warning("Cannot move to position - current position unknown")
            return
        
        if abs(current - target) < 0.5:
            logger.info(f"Already at target position {target}%")
            return
        
        # Set target and start movement
        self.position_tracker.set_target(target)
        
        if target < current:
            self._start_movement_up()
        else:
            self._start_movement_down()
    
    def _start_calibration(self):
        """Start calibration process"""
        self._set_state(StoreState.CALIBRATING)
        self.position_tracker.start_calibration()
        self._start_movement_up()
        
        # Auto-stop calibration after max time
        def calibration_timer():
            time.sleep(30)  # Max calibration time
            if self.state == StoreState.CALIBRATING:
                self._stop_movement()
                self.position_tracker.finish_calibration()
                self._set_state(StoreState.STOPPED)
        
        threading.Thread(target=calibration_timer, daemon=True).start()
    
    def _main_loop(self):
        """Main control loop"""
        logger.info("Store core main loop started")
        
        while self.running:
            try:
                # Check buttons (high priority)
                up_pressed, down_pressed = self.gpio.read_buttons()
                self._handle_button_press(up_pressed, down_pressed)
                
                # Check for target position reached
                if self.state in [StoreState.MOVING_UP, StoreState.MOVING_DOWN]:
                    target = self.position_tracker.get_target()
                    if target is not None:
                        current = self.position_tracker.get_position()
                        if current is not None:
                            if abs(current - target) < 0.5:
                                logger.info(f"Target position {target}% reached")
                                self._stop_movement()
                                self.position_tracker.clear_target()
                
                # Process external commands
                try:
                    command = self.command_queue.get_nowait()
                    self._process_command(command)
                except queue.Empty:
                    pass
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.05)  # 50ms
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(0.1)
        
        logger.info("Store core main loop stopped")
    
    def start(self):
        """Start the store core"""
        if self.main_thread is None or not self.main_thread.is_alive():
            self.running = True
            self.main_thread = threading.Thread(target=self._main_loop, daemon=True)
            self.main_thread.start()
            logger.info("Store core started")
    
    def stop(self):
        """Stop the store core"""
        self.running = False
        self._stop_movement()
        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=2)
        logger.info("Store core stopped")
    
    def cleanup(self):
        """Cleanup resources"""
        self.stop()
        self.gpio.cleanup()
        logger.info("Store core cleanup completed")
    
    # External API methods
    def move_up(self, callback: Optional[Callable] = None):
        """Move up (external command)"""
        command = Command(CommandType.MOVE_UP, callback=callback)
        self.command_queue.put(command)
    
    def move_down(self, callback: Optional[Callable] = None):
        """Move down (external command)"""
        command = Command(CommandType.MOVE_DOWN, callback=callback)
        self.command_queue.put(command)
    
    def move_to_position(self, position: float, callback: Optional[Callable] = None):
        """Move to specific position (external command)"""
        command = Command(CommandType.MOVE_TO_POSITION, target_position=position, callback=callback)
        self.command_queue.put(command)
    
    def stop_movement(self, callback: Optional[Callable] = None):
        """Stop movement (external command)"""
        command = Command(CommandType.STOP, callback=callback)
        self.command_queue.put(command)
    
    def get_status(self, callback: Optional[Callable] = None):
        """Get current status (external command)"""
        command = Command(CommandType.GET_STATUS, callback=callback)
        self.command_queue.put(command)
    
    def calibrate(self, callback: Optional[Callable] = None):
        """Start calibration (external command)"""
        command = Command(CommandType.CALIBRATE, callback=callback)
        self.command_queue.put(command)
    
    def is_power_loss_recovery_needed(self) -> bool:
        """Check if power loss recovery is needed"""
        return self.position_tracker.power_loss_recovery_needed
    
    def get_power_loss_info(self) -> Optional[Dict[str, Any]]:
        """Get power loss recovery information"""
        if self.position_tracker.power_loss_recovery_needed:
            return {
                "recovery_needed": True,
                "last_direction": self.position_tracker.last_movement_direction,
                "estimated_position": self.position_tracker.get_position(),
                "recommendation": "Please verify position manually and recalibrate if needed"
            }
        return None


# Global store core instance
_store_core: Optional[StoreCore] = None


def get_store_core() -> StoreCore:
    """Get the global store core instance"""
    global _store_core
    if _store_core is None:
        _store_core = StoreCore()
    return _store_core


def cleanup_store_core():
    """Cleanup the global store core"""
    global _store_core
    if _store_core:
        _store_core.cleanup()
        _store_core = None


# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    cleanup_store_core()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    # Test the store core
    store = get_store_core()
    store.start()
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        store.cleanup()
