"""
Mock device controller for Windows development
This provides a fallback when RPi.GPIO is not available
"""

import json
import logging
import os
import random
import threading
import time
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class MockDeviceController:
    """Mock device controller for development on non-Raspberry Pi systems"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize mock device controller with optional config file
        
        Args:
            config_file: Path to mock config JSON file. If None, uses default config.
        """
        self.config = self._load_config(config_file)
        self.device_id = self.config["device"]["device_id"]
        self.current_state = self.config["device"]["initial_state"]
        self.current_position = self.config["device"]["initial_position"]
        self.is_moving = False
        self.target_position = None
        self.calibration_in_progress = False
        self.power_loss_recovery_needed = False
        self.movement_thread = None
        
        # Load current scenario settings
        self.scenario = self.config["scenarios"][self.config["current_scenario"]]
        
        logger.info(f"Mock device controller initialized with scenario: {self.config['current_scenario']}")
        logger.info(f"Initial position: {self.current_position}%, State: {self.current_state}")
        
    def _load_config(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """Load mock configuration from JSON file"""
        if config_file is None:
            # Default config file path
            config_file = Path(__file__).parent / "mock_config.json"
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded mock config from: {config_file}")
            return config
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_file}, using default config")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}, using default config")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if config file is not available"""
        return {
            "device": {
                "device_id": "store-001",
                "initial_position": 35.0,
                "initial_state": "partial",
                "movement_speed": 2.0,
                "calibration_time": 3.0
            },
            "scenarios": {
                "normal_operation": {
                    "movement_delay": 2.0,
                    "calibration_delay": 3.0,
                    "error_rate": 0.0
                }
            },
            "current_scenario": "normal_operation",
            "debug_mode": True,
            "log_level": "INFO"
        }
    
    def _should_simulate_error(self) -> bool:
        """Check if we should simulate an error based on error rate"""
        return random.random() < self.scenario.get("error_rate", 0.0)
    
    def _simulate_power_loss(self) -> bool:
        """Check if we should simulate power loss"""
        if not self.scenario.get("power_loss_after_movement", False):
            return False
        return random.random() < self.scenario.get("power_loss_probability", 0.0)
    
    def get_device_status(self) -> Dict[str, Any]:
        """Get mock device status"""
        return {
            "state": self.current_state,
            "position": self.current_position,
            "is_moving": self.is_moving,
            "target_position": self.target_position,
            "calibration_in_progress": self.calibration_in_progress,
            "power_loss_recovery": {
                "recovery_needed": self.power_loss_recovery_needed,
                "last_direction": "up" if self.power_loss_recovery_needed else None,
                "estimated_position": 50.0 if self.power_loss_recovery_needed else None,
                "recommendation": "Please calibrate the device" if self.power_loss_recovery_needed else None
            } if self.power_loss_recovery_needed else None,
            "config": {
                "scenario": self.config["current_scenario"],
                "debug_mode": self.config.get("debug_mode", False)
            }
        }
    
    def open_device(self) -> Dict[str, Any]:
        """Mock open device command - move to 0% (fully opened)"""
        if self._should_simulate_error():
            return {
                "success": False,
                "error": "Simulated error: Device communication failed"
            }
        
        logger.info("Mock: Opening device")
        self.current_state = "moving"
        self.is_moving = True
        self.target_position = 0.0  # 0% = fully opened
        
        # Stop any existing movement
        if self.movement_thread and self.movement_thread.is_alive():
            self.movement_thread.join(timeout=0.1)
        
        # Simulate movement completion after a delay
        def complete_movement():
            time.sleep(self.scenario["movement_delay"])
            self.current_state = "open"
            self.current_position = 0.0  # 0% = fully opened
            self.is_moving = False
            self.target_position = None
            
            # Simulate power loss if configured
            if self._simulate_power_loss():
                self.power_loss_recovery_needed = True
                logger.warning("Mock: Simulated power loss during movement")
        
        self.movement_thread = threading.Thread(target=complete_movement, daemon=True)
        self.movement_thread.start()
        
        return {
            "success": True,
            "action": "open",
            "target_position": 0.0,  # 0% = fully opened
            "estimated_duration": self.scenario["movement_delay"],
            "current_position": self.current_position
        }
    
    def close_device(self) -> Dict[str, Any]:
        """Mock close device command - move to 100% (fully closed)"""
        if self._should_simulate_error():
            return {
                "success": False,
                "error": "Simulated error: Device communication failed"
            }
        
        logger.info("Mock: Closing device")
        self.current_state = "moving"
        self.is_moving = True
        self.target_position = 100.0  # 100% = fully closed
        
        # Stop any existing movement
        if self.movement_thread and self.movement_thread.is_alive():
            self.movement_thread.join(timeout=0.1)
        
        # Simulate movement completion after a delay
        def complete_movement():
            time.sleep(self.scenario["movement_delay"])
            self.current_state = "closed"
            self.current_position = 100.0  # 100% = fully closed
            self.is_moving = False
            self.target_position = None
            
            # Simulate power loss if configured
            if self._simulate_power_loss():
                self.power_loss_recovery_needed = True
                logger.warning("Mock: Simulated power loss during movement")
        
        self.movement_thread = threading.Thread(target=complete_movement, daemon=True)
        self.movement_thread.start()
        
        return {
            "success": True,
            "action": "close",
            "target_position": 100.0,  # 100% = fully closed
            "estimated_duration": self.scenario["movement_delay"],
            "current_position": self.current_position
        }
    
    def stop_device(self) -> Dict[str, Any]:
        """Mock stop device command"""
        logger.info("Mock: Stopping device")
        self.is_moving = False
        self.target_position = None
        if self.current_state == "moving":
            self.current_state = "stopped"
        
        # Stop movement thread
        if self.movement_thread and self.movement_thread.is_alive():
            self.movement_thread.join(timeout=0.1)
        
        return {
            "success": True,
            "action": "stop",
            "current_position": self.current_position
        }
    
    def calibrate_device(self) -> Dict[str, Any]:
        """Mock calibrate device command"""
        logger.info("Mock: Calibrating device")
        self.calibration_in_progress = True
        self.current_position = 0.0  # Calibrate to 0% (fully opened)
        self.current_state = "calibrated"
        
        # Simulate calibration completion
        def complete_calibration():
            time.sleep(self.scenario["calibration_delay"])
            self.calibration_in_progress = False
            self.power_loss_recovery_needed = False
        
        threading.Thread(target=complete_calibration, daemon=True).start()
        
        return {
            "success": True,
            "action": "calibrate",
            "estimated_duration": self.scenario["calibration_delay"],
            "current_position": self.current_position
        }
    
    def set_scenario(self, scenario_name: str) -> bool:
        """Change the current test scenario"""
        if scenario_name in self.config["scenarios"]:
            self.config["current_scenario"] = scenario_name
            self.scenario = self.config["scenarios"][scenario_name]
            logger.info(f"Changed scenario to: {scenario_name}")
            return True
        else:
            logger.error(f"Unknown scenario: {scenario_name}")
            return False
    
    def get_available_scenarios(self) -> Dict[str, str]:
        """Get list of available test scenarios"""
        return {name: config.get("description", "No description") 
                for name, config in self.config["scenarios"].items()}
    
    def set_position(self, position: float) -> bool:
        """Manually set device position for testing"""
        if 0.0 <= position <= 100.0:
            self.current_position = position
            if position == 0.0:
                self.current_state = "open"
            elif position == 100.0:
                self.current_state = "closed"
            else:
                self.current_state = "partial"
            logger.info(f"Mock: Set position to {position}%")
            return True
        else:
            logger.error(f"Invalid position: {position}. Must be between 0.0 and 100.0")
            return False
