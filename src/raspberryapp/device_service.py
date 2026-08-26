#!/usr/bin/env python3
"""
Simple Motorised Store Device Service
Minimalistic GPIO control for motorised store
"""

import RPi.GPIO as GPIO
import time
import threading
import logging
import os
import json
from typing import Optional
from models import DeviceState, MotorDirection

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleDeviceService:
    """Simple, reliable device service for motorised store"""
    
    def __init__(self):
        # GPIO pins
        self.motor_up_pin = 23
        self.motor_down_pin = 24
        self.button_up_pin = 25
        self.button_down_pin = 27
        
        # State
        self.state = DeviceState.STOPPED
        self.running = True  # Start running immediately
        self.motor_lock = threading.Lock()
        
        # External command handling
        self.external_command_active = False
        self.external_command_lock = threading.Lock()
        self.external_command_timeout = 25.0  # 25 seconds failsafe timeout
        self.external_command_timer = None
        
        # GPIO override handling
        self.gpio_override_active = False
        self.gpio_override_lock = threading.Lock()
        
        # Files for inter-process communication
        self.status_file = "/tmp/motorised_store_status.json"
        self.command_file = "/tmp/motorised_store_command.txt"
        self.position_file = "/tmp/motorised_store_position.txt"
        
        # Position tracking
        self.current_position = None  # 0-100, None = unknown
        self.position_lock = threading.Lock()
        self.movement_start_time = None
        self.movement_start_position = None
        self.target_position = None  # Target position for position-based movements
        self.calibration_in_progress = False
        self.position_file_mtime = 0  # Track position file modification time
        
        # Initialize GPIO
        self._setup_gpio()
        
        # Start monitoring threads
        self.monitor_thread = threading.Thread(target=self._monitor_buttons, daemon=True)
        self.monitor_thread.start()
        logger.info("Button monitoring thread started")
        
        # Start status update thread
        self.status_thread = threading.Thread(target=self._update_status_file, daemon=True)
        self.status_thread.start()
        logger.info("Status update thread started")
        
        # Start command monitoring thread
        self.command_thread = threading.Thread(target=self._monitor_commands, daemon=True)
        self.command_thread.start()
        logger.info("Command monitoring thread started")
        
        # Load or initialize position
        self._load_position()
        
        # Start position calibration if needed
        if self.current_position is None:
            self._start_position_calibration()
        
        logger.info("Simple device service initialized and running")
    
    def _setup_gpio(self):
        """Setup GPIO pins"""
        try:
            GPIO.setmode(GPIO.BCM)
            
            # Motor pins (output) - matching working run.py
            GPIO.setup(self.motor_up_pin, GPIO.OUT)
            GPIO.setup(self.motor_down_pin, GPIO.OUT)
            
            # Button pins (input with pull-down) - matching working run.py
            GPIO.setup(self.button_up_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(self.button_down_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            
            # Start with motor stopped
            self._stop_motor()
            
            logger.info("GPIO setup completed")
            
        except Exception as e:
            logger.error(f"GPIO setup failed: {e}")
            raise
    
    def _load_position(self):
        """Load position from file"""
        try:
            if os.path.exists(self.position_file):
                # Get file modification time
                current_mtime = os.path.getmtime(self.position_file)
                
                with open(self.position_file, 'r') as f:
                    position_str = f.read().strip()
                    position = float(position_str)
                    if 0 <= position <= 100:
                        with self.position_lock:
                            self.current_position = position
                        self.position_file_mtime = current_mtime
                        logger.info(f"Position loaded from file: {position}%")
                    else:
                        logger.warning(f"Invalid position in file: {position}, will calibrate")
                        with self.position_lock:
                            self.current_position = None
                        self.position_file_mtime = current_mtime
            else:
                logger.info("No position file found, will calibrate")
                with self.position_lock:
                    self.current_position = None
                self.position_file_mtime = 0
        except Exception as e:
            logger.error(f"Error loading position: {e}, will calibrate")
            with self.position_lock:
                self.current_position = None
            self.position_file_mtime = 0
    
    def _save_position(self):
        """Save position to file"""
        try:
            with self.position_lock:
                if self.current_position is not None:
                    with open(self.position_file, 'w') as f:
                        f.write(str(self.current_position))
                    # Update our modification time tracking
                    if os.path.exists(self.position_file):
                        self.position_file_mtime = os.path.getmtime(self.position_file)
        except Exception as e:
            logger.error(f"Error saving position: {e}")
    
    def _check_position_file_updated(self):
        """Check if position file has been updated externally and reload if needed"""
        try:
            if os.path.exists(self.position_file):
                current_mtime = os.path.getmtime(self.position_file)
                if current_mtime > self.position_file_mtime:
                    logger.info("Position file updated externally, reloading...")
                    self._load_position()
                    return True
            elif self.position_file_mtime > 0:
                # File was deleted
                logger.info("Position file was deleted externally")
                with self.position_lock:
                    self.current_position = None
                self.position_file_mtime = 0
                return True
        except Exception as e:
            logger.error(f"Error checking position file: {e}")
        return False
    
    def _start_position_calibration(self):
        """Start automatic position calibration"""
        logger.info("Starting position calibration - assuming we'll reach top position")
        self.calibration_in_progress = True
        
        # Immediately set position to 0% since we're going UP to find top
        with self.position_lock:
            self.current_position = 0.0
        self._save_position()
        logger.info("Position set to 0% (fully up) - calibration movement will confirm this")
        
        # Get max time for calibration movement
        try:
            max_time_file = "/tmp/motorised_store_max_time.txt"
            if os.path.exists(max_time_file):
                with open(max_time_file, 'r') as f:
                    max_time = float(f.read().strip())
            else:
                max_time = 30.0  # Default
        except:
            max_time = 30.0
        
        # Start calibration movement to ensure we reach top
        self._start_calibration_movement(max_time)
    
    def _start_calibration_movement(self, max_time):
        """Start calibration movement in separate thread"""
        def calibration_thread():
            try:
                logger.info(f"Calibration: Moving UP for {max_time} seconds to ensure top position")
                self._move_up()
                
                # Wait for max_time or until GPIO override
                start_time = time.time()
                while time.time() - start_time < max_time:
                    with self.gpio_override_lock:
                        if self.gpio_override_active:
                            logger.info("Calibration movement stopped by GPIO button press")
                            self.calibration_in_progress = False
                            return
                    time.sleep(0.1)
                
                # Calibration movement completed - we should now be at top
                self._stop_motor()
                self.calibration_in_progress = False
                logger.info("Calibration movement completed - confirmed at top position (0%)")
                
            except Exception as e:
                logger.error(f"Calibration error: {e}")
                self.calibration_in_progress = False
        
        calibration_thread_obj = threading.Thread(target=calibration_thread, daemon=True)
        calibration_thread_obj.start()
    
    def _update_position_during_movement(self, direction, elapsed_time, max_time):
        """Update position based on movement time"""
        if self.current_position is None:
            return
        
        # Calculate movement percentage (0-100% of total range)
        movement_percentage = (elapsed_time / max_time) * 100
        
        with self.position_lock:
            old_position = self.current_position
            if direction == "up":
                # Moving up decreases position (towards 0)
                new_position = max(0, self.current_position - movement_percentage)
            else:  # down
                # Moving down increases position (towards 100)
                new_position = min(100, self.current_position + movement_percentage)
            
            self.current_position = new_position
        
        self._save_position()
        
        # Final position update with newline
        print(f'\rPosition: {old_position:.1f}% → {self.current_position:.1f}% | Movement: {direction.upper()} | {elapsed_time:.1f}s elapsed', flush=True)
        print()  # Add newline after movement completes
    
    def _start_movement_tracking(self):
        """Start tracking movement for position updates"""
        with self.position_lock:
            self.movement_start_time = time.time()
            self.movement_start_position = self.current_position
    
    def _stop_movement_tracking(self, direction):
        """Stop tracking movement and update final position"""
        if self.movement_start_time is None:
            return
        
        try:
            # Get max time for calculation
            max_time_file = "/tmp/motorised_store_max_time.txt"
            if os.path.exists(max_time_file):
                with open(max_time_file, 'r') as f:
                    max_time = float(f.read().strip())
            else:
                max_time = 30.0
            
            elapsed_time = time.time() - self.movement_start_time
            self._update_position_during_movement(direction, elapsed_time, max_time)
            
            with self.position_lock:
                self.movement_start_time = None
                self.movement_start_position = None
                logger.info(f"Position updated to {self.current_position:.1f}%")
                
        except Exception as e:
            logger.error(f"Error updating position: {e}")
    
    def _stop_motor(self):
        """Stop the motor"""
        with self.motor_lock:
            GPIO.output(self.motor_up_pin, GPIO.LOW)
            GPIO.output(self.motor_down_pin, GPIO.LOW)
            self.state = DeviceState.STOPPED
            logger.info("Motor stopped")
    
    def _move_up(self):
        """Move motor up (open store)"""
        with self.motor_lock:
            GPIO.output(self.motor_up_pin, GPIO.HIGH)
            GPIO.output(self.motor_down_pin, GPIO.LOW)
            self.state = DeviceState.OPENING
            if not self.calibration_in_progress:
                self._start_movement_tracking()
            logger.info("Motor moving up")
    
    def _move_down(self):
        """Move motor down (close store)"""
        with self.motor_lock:
            GPIO.output(self.motor_up_pin, GPIO.LOW)
            GPIO.output(self.motor_down_pin, GPIO.HIGH)
            self.state = DeviceState.CLOSING
            if not self.calibration_in_progress:
                self._start_movement_tracking()
            logger.info("Motor moving down")
    
    def _move_up_button(self):
        """Move motor up (button press)"""
        self._move_up()
    
    def _move_down_button(self):
        """Move motor down (button press)"""
        self._move_down()
    
    def _stop_motor_button(self):
        """Stop motor (button release)"""
        # Update position based on movement
        if self.state == DeviceState.OPENING:
            self._stop_movement_tracking("up")
        elif self.state == DeviceState.CLOSING:
            self._stop_movement_tracking("down")
        
        # Reset external command flag when button stops motor
        self._reset_external_command_flag()
        self._stop_motor()
    
    def _move_up_external(self):
        """Move motor up (external command)"""
        # Check if GPIO override is active
        with self.gpio_override_lock:
            if self.gpio_override_active:
                logger.info("External UP command ignored - GPIO button override active")
                return
        
        with self.external_command_lock:
            self.external_command_active = True
            # Cancel any existing timeout timer when starting new movement
            if self.external_command_timer:
                self.external_command_timer.cancel()
                self.external_command_timer = None
        
        # Clear target position for regular movements
        with self.position_lock:
            self.target_position = None
        
        # Start failsafe timeout (25 seconds)
        self._start_external_command_timeout()
        logger.info("External command active - GPIO buttons disabled until STOP received")
        self._move_up()
    
    def _move_down_external(self):
        """Move motor down (external command)"""
        # Check if GPIO override is active
        with self.gpio_override_lock:
            if self.gpio_override_active:
                logger.info("External DOWN command ignored - GPIO button override active")
                return
        
        with self.external_command_lock:
            self.external_command_active = True
            # Cancel any existing timeout timer when starting new movement
            if self.external_command_timer:
                self.external_command_timer.cancel()
                self.external_command_timer = None
        
        # Clear target position for regular movements
        with self.position_lock:
            self.target_position = None
        
        # Start failsafe timeout (25 seconds)
        self._start_external_command_timeout()
        logger.info("External command active - GPIO buttons disabled until STOP received")
        self._move_down()
    
    def _stop_motor_external(self):
        """Stop motor (external command)"""
        logger.info("Stopping motor due to external command")
        
        # Check if this is a position-based movement
        with self.position_lock:
            target_pos = self.target_position
        
        if target_pos is not None:
            # Position-based movement - set position to target
            with self.position_lock:
                self.current_position = target_pos
                self.target_position = None  # Clear target
            self._save_position()
            logger.info(f"Position set to target: {target_pos}%")
        elif self.movement_start_time is not None:
            # Regular movement - calculate position based on elapsed time
            if self.state == DeviceState.OPENING:
                self._stop_movement_tracking("up")
            elif self.state == DeviceState.CLOSING:
                self._stop_movement_tracking("down")
        
        self._reset_external_command_flag()
        self._stop_motor()
        logger.info("External stop command completed")
    
    def _move_to_position_external(self, target_position, preferred_direction):
        """Move to specific position (external command)"""
        # Check if GPIO override is active
        with self.gpio_override_lock:
            if self.gpio_override_active:
                logger.info(f"External position command ignored - GPIO button override active")
                return
        
        with self.position_lock:
            current_pos = self.current_position
        
        if current_pos is None:
            logger.warning("Cannot move to position - current position unknown (calibration needed)")
            return
        
        # Determine direction based on target vs current position
        if target_position < current_pos:
            direction = "up"
        elif target_position > current_pos:
            direction = "down"
        else:
            logger.info(f"Already at target position {target_position}%")
            return
        
        # Calculate movement time needed
        try:
            max_time_file = "/tmp/motorised_store_max_time.txt"
            if os.path.exists(max_time_file):
                with open(max_time_file, 'r') as f:
                    max_time = float(f.read().strip())
            else:
                max_time = 30.0
            
            position_diff = abs(target_position - current_pos)
            movement_time = (position_diff / 100) * max_time
            movement_time = max(0.1, min(movement_time, max_time))
            
        except:
            movement_time = 30.0
        
        # Start movement
        with self.external_command_lock:
            self.external_command_active = True
            if self.external_command_timer:
                self.external_command_timer.cancel()
                self.external_command_timer = None
        
        logger.info(f"Moving {direction} to position {target_position}% (estimated {movement_time:.1f}s)")
        
        # Store target position for stop command handling
        with self.position_lock:
            self.target_position = target_position
        
        # Start motor without automatic movement tracking (we handle position manually)
        with self.motor_lock:
            if direction == "up":
                GPIO.output(self.motor_up_pin, GPIO.HIGH)
                GPIO.output(self.motor_down_pin, GPIO.LOW)
                self.state = DeviceState.OPENING
            else:
                GPIO.output(self.motor_up_pin, GPIO.LOW)
                GPIO.output(self.motor_down_pin, GPIO.HIGH)
                self.state = DeviceState.CLOSING
            logger.info(f"Motor moving {direction} (position-controlled)")
        
        # Start position-based timer with real-time position updates
        def position_timer():
            start_time = time.time()
            start_position = current_pos  # Store initial position
            
            while True:
                elapsed = time.time() - start_time
                
                # Check if we should stop
                with self.external_command_lock:
                    if not self.external_command_active:
                        return  # Command was cancelled
                
                # Calculate current position based on progress
                progress = min(1.0, elapsed / movement_time)
                new_position = start_position + (target_position - start_position) * progress
                
                with self.position_lock:
                    self.current_position = max(0, min(100, new_position))
                self._save_position()
                
                # Real-time position logging (same line)
                print(f'\rPosition: {self.current_position:.1f}% → Target: {target_position}% | Progress: {progress*100:.1f}% | {elapsed:.1f}s elapsed', end='', flush=True)
                
                # Check if we've reached target or time limit
                if elapsed >= movement_time:
                    # Ensure we're exactly at target position
                    with self.position_lock:
                        self.current_position = target_position
                    self._save_position()
                    
                    # Final position update and newline
                    print(f'\rPosition: {target_position:.1f}% → Target: {target_position}% | Progress: 100.0% | {elapsed:.1f}s elapsed', flush=True)
                    print()  # Add newline after completion
                    logger.info(f"Position-based movement completed - reached {target_position}% after {elapsed:.1f}s")
                    self._stop_motor_external()
                    return
                
                time.sleep(0.1)  # Update every 100ms
        
        timer_thread = threading.Thread(target=position_timer, daemon=True)
        timer_thread.start()
    
    def _reset_external_command_flag(self):
        """Reset external command flag and cancel timer"""
        with self.external_command_lock:
            self.external_command_active = False
            if self.external_command_timer:
                self.external_command_timer.cancel()
                self.external_command_timer = None
            logger.info("External command flag reset - GPIO buttons re-enabled")
    
    def _cancel_external_commands(self):
        """Cancel any active external commands due to GPIO override"""
        with self.external_command_lock:
            if self.external_command_active:
                # Cancel external command timer
                if self.external_command_timer:
                    self.external_command_timer.cancel()
                    self.external_command_timer = None
                self.external_command_active = False
                # Stop the motor to cancel any ongoing external movement
                self._stop_motor()
                logger.info("External commands cancelled due to GPIO button press")
    
    def _start_external_command_timeout(self):
        """Start timeout timer for external command"""
        with self.external_command_lock:
            # Cancel existing timer if any
            if self.external_command_timer:
                self.external_command_timer.cancel()
            
            # Start new timer
            self.external_command_timer = threading.Timer(
                self.external_command_timeout, 
                self._reset_external_command_flag
            )
            self.external_command_timer.start()
            logger.info(f"External command failsafe timeout started ({self.external_command_timeout}s)")
    
    def _monitor_buttons(self):
        """Monitor physical buttons using the exact working logic from sml/run.py"""
        logger.info("Button monitoring started")
        logger.info(f"Monitoring GPIO pins: UP={self.button_up_pin}, DOWN={self.button_down_pin}")
        
        up_count = 0
        down_count = 0
        
        while True:
            try:
                # Check if service is still running
                if not self.running:
                    logger.info("Button monitoring stopped - service not running")
                    break
                
                # Skip button monitoring if external command is active
                with self.external_command_lock:
                    if self.external_command_active:
                        time.sleep(0.1)
                        continue
                
                # Debug logging removed to reduce log pollution
                
                # Read current button states
                up_button = GPIO.input(self.button_up_pin)
                down_button = GPIO.input(self.button_down_pin)
                
                # Check if any GPIO button is pressed
                any_button_pressed = (up_button == GPIO.HIGH) or (down_button == GPIO.HIGH)
                
                # Handle GPIO override activation/deactivation
                with self.gpio_override_lock:
                    if any_button_pressed and not self.gpio_override_active:
                        # GPIO button just pressed - activate override
                        self.gpio_override_active = True
                        self._cancel_external_commands()
                        logger.info("GPIO override activated - external commands cancelled and blocked")
                    elif not any_button_pressed and self.gpio_override_active:
                        # No GPIO buttons pressed - deactivate override
                        self.gpio_override_active = False
                        logger.info("GPIO override deactivated - external commands re-enabled")
                
                # Handle UP button - modified for continuously pressed buttons
                if up_button == GPIO.HIGH and up_count == 0:
                    # Button just became pressed - start motor
                    up_count = 1
                    logger.info("UP button pressed - starting motor UP")
                    self._move_up_button()
                elif up_button == GPIO.LOW and up_count == 1:
                    # Button just became released - stop motor
                    up_count = 0
                    logger.info("UP button released - stopping motor")
                    self._stop_motor_button()
                
                # Handle DOWN button - modified for continuously pressed buttons  
                if down_button == GPIO.HIGH and down_count == 0:
                    # Button just became pressed - start motor
                    down_count = 1
                    logger.info("DOWN button pressed - starting motor DOWN")
                    self._move_down_button()
                elif down_button == GPIO.LOW and down_count == 1:
                    # Button just became released - stop motor
                    down_count = 0
                    logger.info("DOWN button released - stopping motor")
                    self._stop_motor_button()
                
                time.sleep(0.1)  # 100ms polling
                
            except Exception as e:
                logger.error(f"Button monitoring error: {e}")
                time.sleep(1)
    
    def _update_status_file(self):
        """Update status file for inter-process communication"""
        while True:
            try:
                # Check if position file has been updated externally
                self._check_position_file_updated()
                
                # Get full status including position
                status = self.get_status()
                status["timestamp"] = time.time()
                
                with open(self.status_file, 'w') as f:
                    json.dump(status, f)
                time.sleep(1)  # Update every second
            except Exception as e:
                logger.error(f"Status file update error: {e}")
                time.sleep(5)
    
    def _monitor_commands(self):
        """Monitor command file for external commands"""
        while True:
            try:
                if os.path.exists(self.command_file):
                    with open(self.command_file, 'r') as f:
                        command = f.read().strip()
                    
                    # Remove command file
                    os.remove(self.command_file)
                    
                    # Parse command (may include position)
                    if ":" in command:
                        cmd_parts = command.split(":", 1)
                        base_command = cmd_parts[0]
                        try:
                            target_position = float(cmd_parts[1])
                            target_position = max(0, min(100, target_position))  # Clamp to 0-100
                        except:
                            target_position = None
                    else:
                        base_command = command
                        target_position = None
                    
                    # Execute external command - process STOP with highest priority
                    if base_command == "stop":
                        logger.info("External command: STOP (priority)")
                        self._stop_motor_external()
                    elif base_command == "up":
                        if target_position is not None:
                            logger.info(f"External command: UP to position {target_position}%")
                            self._move_to_position_external(target_position, "up")
                        else:
                            logger.info("External command: UP")
                            self._move_up_external()
                    elif base_command == "down":
                        if target_position is not None:
                            logger.info(f"External command: DOWN to position {target_position}%")
                            self._move_to_position_external(target_position, "down")
                        else:
                            logger.info("External command: DOWN")
                            self._move_down_external()
                
                time.sleep(0.1)  # Check every 100ms
            except Exception as e:
                logger.error(f"Command monitoring error: {e}")
                time.sleep(1)
    
    def start(self):
        """Start the device service"""
        self.running = True
        logger.info("Device service started")
    
    def stop(self):
        """Stop the device service"""
        self.running = False
        self._reset_external_command_flag()  # Cancel any pending timers
        self._stop_motor()
        # Remove status and command files when stopping
        try:
            if os.path.exists(self.status_file):
                os.remove(self.status_file)
            if os.path.exists(self.command_file):
                os.remove(self.command_file)
        except Exception as e:
            logger.error(f"Error removing status/command files: {e}")
        logger.info("Device service stopped")
    
    def cleanup(self):
        """Cleanup GPIO resources"""
        try:
            self.stop()
            GPIO.cleanup()
            logger.info("GPIO cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def get_status(self):
        """Get current device status"""
        with self.position_lock:
            position = self.current_position
        
        status = {
            "state": self.state.value,
            "running": self.running,
            "position": position,
            "calibration_in_progress": self.calibration_in_progress
        }
        
        # Add movement progress if moving
        if self.movement_start_time is not None and position is not None:
            elapsed = time.time() - self.movement_start_time
            try:
                max_time_file = "/tmp/motorised_store_max_time.txt"
                if os.path.exists(max_time_file):
                    with open(max_time_file, 'r') as f:
                        max_time = float(f.read().strip())
                else:
                    max_time = 30.0
                
                progress_percentage = min(100, (elapsed / max_time) * 100)
                status["movement_progress"] = progress_percentage
                status["movement_elapsed"] = elapsed
                status["movement_max_time"] = max_time
            except:
                pass
        
        return status


# Global device service instance
_device_service = None

def get_device_service():
    """Get the global device service instance"""
    global _device_service
    if _device_service is None:
        _device_service = SimpleDeviceService()
    return _device_service


def cleanup_device_service():
    """Cleanup the global device service"""
    global _device_service
    if _device_service:
        _device_service.cleanup()
        _device_service = None