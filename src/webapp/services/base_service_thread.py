"""
Base service thread class for running services in separate threads
"""

import asyncio
import threading
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service status enumeration"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    RESTARTING = "restarting"


@dataclass
class ServiceInfo:
    """Service information structure"""
    name: str
    status: ServiceStatus
    last_updated: datetime
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None
    restart_count: int = 0
    health_status: str = "unknown"
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class BaseServiceThread(ABC):
    """Base class for services that run in separate threads"""
    
    def __init__(self, name: str, update_interval: float = 5.0):
        self.name = name
        self.update_interval = update_interval
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._status = ServiceStatus.STOPPED
        self._error_message: Optional[str] = None
        self._start_time: Optional[datetime] = None
        self._stop_time: Optional[datetime] = None
        self._restart_count = 0
        self._health_status = "unknown"
        self._details: Dict[str, Any] = {}
        self._status_lock = threading.Lock()
        self._callbacks: Dict[str, Callable] = {}
        
        logger.info(f"Initialized {self.name} service thread")
    
    @abstractmethod
    async def _service_initialize(self) -> bool:
        """Initialize the service - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def _service_start(self) -> bool:
        """Start the service - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def _service_stop(self) -> bool:
        """Stop the service - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def _service_health_check(self) -> Dict[str, Any]:
        """Perform health check - must be implemented by subclasses"""
        pass
    
    async def _service_update(self) -> None:
        """Update service status - can be overridden by subclasses"""
        pass
    
    def start(self) -> bool:
        """Start the service thread"""
        with self._status_lock:
            if self._status in [ServiceStatus.RUNNING, ServiceStatus.STARTING]:
                logger.warning(f"{self.name} service is already running or starting")
                return True
            
            self._status = ServiceStatus.STARTING
            self._error_message = None
            self._stop_event.clear()
        
        try:
            self._thread = threading.Thread(target=self._run_service, daemon=True)
            self._thread.start()
            logger.info(f"Started {self.name} service thread")
            return True
        except Exception as e:
            with self._status_lock:
                self._status = ServiceStatus.ERROR
                self._error_message = str(e)
            logger.error(f"Failed to start {self.name} service thread: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the service thread"""
        with self._status_lock:
            if self._status in [ServiceStatus.STOPPED, ServiceStatus.STOPPING]:
                logger.warning(f"{self.name} service is already stopped or stopping")
                return True
            
            self._status = ServiceStatus.STOPPING
        
        try:
            self._stop_event.set()
            
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=10.0)
                if self._thread.is_alive():
                    logger.warning(f"{self.name} service thread did not stop gracefully")
            
            with self._status_lock:
                self._status = ServiceStatus.STOPPED
                self._stop_time = datetime.utcnow()
            
            logger.info(f"Stopped {self.name} service thread")
            return True
        except Exception as e:
            with self._status_lock:
                self._status = ServiceStatus.ERROR
                self._error_message = str(e)
            logger.error(f"Failed to stop {self.name} service thread: {e}")
            return False
    
    def restart(self) -> bool:
        """Restart the service thread"""
        logger.info(f"Restarting {self.name} service")
        
        with self._status_lock:
            self._status = ServiceStatus.RESTARTING
            self._restart_count += 1
        
        # Stop the service
        if not self.stop():
            logger.error(f"Failed to stop {self.name} service during restart")
            return False
        
        # Wait a moment before restarting
        time.sleep(1.0)
        
        # Start the service
        if not self.start():
            logger.error(f"Failed to start {self.name} service during restart")
            return False
        
        logger.info(f"Successfully restarted {self.name} service")
        return True
    
    def _run_service(self):
        """Main service thread loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Initialize the service
            with self._status_lock:
                self._status = ServiceStatus.STARTING
            
            if not loop.run_until_complete(self._service_initialize()):
                with self._status_lock:
                    self._status = ServiceStatus.ERROR
                    self._error_message = "Failed to initialize service"
                logger.error(f"{self.name} service failed to initialize")
                return
            
            # Start the service
            if not loop.run_until_complete(self._service_start()):
                with self._status_lock:
                    self._status = ServiceStatus.ERROR
                    self._error_message = "Failed to start service"
                logger.error(f"{self.name} service failed to start")
                return
            
            # Service is now running
            with self._status_lock:
                self._status = ServiceStatus.RUNNING
                self._start_time = datetime.utcnow()
                self._error_message = None
            
            logger.info(f"{self.name} service is now running")
            
            # Main service loop
            while not self._stop_event.is_set():
                try:
                    # Update service status
                    loop.run_until_complete(self._service_update())
                    
                    # Perform health check
                    health_data = loop.run_until_complete(self._service_health_check())
                    with self._status_lock:
                        self._health_status = health_data.get("status", "unknown")
                        self._details.update(health_data.get("details", {}))
                    
                    # Notify callbacks
                    self._notify_callbacks("update", health_data)
                    
                except Exception as e:
                    logger.error(f"Error in {self.name} service update: {e}")
                    with self._status_lock:
                        self._error_message = str(e)
                
                # Wait for next update or stop event
                self._stop_event.wait(self.update_interval)
            
        except Exception as e:
            logger.error(f"Fatal error in {self.name} service thread: {e}")
            with self._status_lock:
                self._status = ServiceStatus.ERROR
                self._error_message = str(e)
        finally:
            # Cleanup
            try:
                loop.run_until_complete(self._service_stop())
            except Exception as e:
                logger.error(f"Error stopping {self.name} service: {e}")
            
            with self._status_lock:
                if self._status != ServiceStatus.STOPPING:
                    self._status = ServiceStatus.STOPPED
                self._stop_time = datetime.utcnow()
            
            loop.close()
            logger.info(f"{self.name} service thread ended")
    
    def get_status(self) -> ServiceInfo:
        """Get current service status"""
        with self._status_lock:
            return ServiceInfo(
                name=self.name,
                status=self._status,
                last_updated=datetime.utcnow(),
                error_message=self._error_message,
                start_time=self._start_time,
                stop_time=self._stop_time,
                restart_count=self._restart_count,
                health_status=self._health_status,
                details=self._details.copy()
            )
    
    def is_running(self) -> bool:
        """Check if service is running"""
        with self._status_lock:
            return self._status == ServiceStatus.RUNNING
    
    def is_healthy(self) -> bool:
        """Check if service is healthy"""
        with self._status_lock:
            return (self._status == ServiceStatus.RUNNING and 
                   self._health_status in ["healthy", "ok", "connected"])
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status"""
        status = self.get_status()
        return {
            "status": status.health_status,
            "details": status.details,
            "error": status.error_message,
            "uptime": self._get_uptime(),
            "restart_count": status.restart_count
        }
    
    def _get_uptime(self) -> Optional[float]:
        """Get service uptime in seconds"""
        with self._status_lock:
            if self._start_time and self._status == ServiceStatus.RUNNING:
                return (datetime.utcnow() - self._start_time).total_seconds()
            return None
    
    def add_callback(self, event: str, callback: Callable):
        """Add callback for service events"""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)
    
    def remove_callback(self, event: str, callback: Callable):
        """Remove callback for service events"""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
    
    def _notify_callbacks(self, event: str, data: Any = None):
        """Notify all callbacks for an event"""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(self.name, event, data)
                except Exception as e:
                    logger.error(f"Error in callback for {self.name} service: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics"""
        status = self.get_status()
        uptime = self._get_uptime()
        
        return {
            "name": self.name,
            "status": status.status.value,
            "health_status": status.health_status,
            "uptime_seconds": uptime,
            "restart_count": status.restart_count,
            "last_error": status.error_message,
            "details": status.details,
            "thread_alive": self._thread.is_alive() if self._thread else False
        }
