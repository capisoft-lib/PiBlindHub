"""
Global status registry for managing and accessing service status across the application
"""

import threading
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from src.webapp.services.base_service_thread import BaseServiceThread, ServiceInfo, ServiceStatus

logger = logging.getLogger(__name__)


@dataclass
class GlobalServiceStatus:
    """Global service status structure"""
    name: str
    status: str
    health_status: str
    last_updated: datetime
    error_message: Optional[str] = None
    uptime_seconds: Optional[float] = None
    restart_count: int = 0
    details: Dict[str, Any] = None
    thread_alive: bool = False
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class GlobalStatusRegistry:
    """Global registry for service status management"""
    
    def __init__(self):
        self._services: Dict[str, BaseServiceThread] = {}
        self._status_cache: Dict[str, GlobalServiceStatus] = {}
        self._callbacks: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        self._update_interval = 2.0  # Update every 2 seconds
        self._last_update = datetime.utcnow()
        
        logger.info("Global status registry initialized")
    
    def register_service(self, service: BaseServiceThread) -> bool:
        """Register a service with the global registry"""
        with self._lock:
            try:
                self._services[service.name] = service
                
                # Add callback for status updates
                service.add_callback("update", self._on_service_update)
                service.add_callback("error", self._on_service_error)
                service.add_callback("status_change", self._on_service_status_change)
                
                # Initialize status cache
                self._update_service_status(service.name)
                
                logger.info(f"Registered service: {service.name}")
                return True
            except Exception as e:
                logger.error(f"Failed to register service {service.name}: {e}")
                return False
    
    def unregister_service(self, service_name: str) -> bool:
        """Unregister a service from the global registry"""
        with self._lock:
            try:
                if service_name in self._services:
                    service = self._services[service_name]
                    
                    # Remove callbacks
                    service.remove_callback("update", self._on_service_update)
                    service.remove_callback("error", self._on_service_error)
                    service.remove_callback("status_change", self._on_service_status_change)
                    
                    # Remove from registry
                    del self._services[service_name]
                    if service_name in self._status_cache:
                        del self._status_cache[service_name]
                    
                    logger.info(f"Unregistered service: {service_name}")
                    return True
                return False
            except Exception as e:
                logger.error(f"Failed to unregister service {service_name}: {e}")
                return False
    
    def get_service_status(self, service_name: str) -> Optional[GlobalServiceStatus]:
        """Get status of a specific service"""
        with self._lock:
            if service_name in self._status_cache:
                return self._status_cache[service_name]
            return None
    
    def get_all_service_status(self) -> Dict[str, GlobalServiceStatus]:
        """Get status of all registered services"""
        with self._lock:
            # Update all service statuses
            for service_name in list(self._services.keys()):
                self._update_service_status(service_name)
            
            return self._status_cache.copy()
    
    def get_services_by_status(self, status: str) -> List[str]:
        """Get list of service names with specific status"""
        with self._lock:
            services = []
            for service_name, service_status in self._status_cache.items():
                if service_status.status == status:
                    services.append(service_name)
            return services
    
    def get_healthy_services(self) -> List[str]:
        """Get list of healthy service names"""
        with self._lock:
            services = []
            for service_name, service_status in self._status_cache.items():
                if service_status.health_status in ["healthy", "ok", "connected"]:
                    services.append(service_name)
            return services
    
    def get_unhealthy_services(self) -> List[str]:
        """Get list of unhealthy service names"""
        with self._lock:
            services = []
            for service_name, service_status in self._status_cache.items():
                if service_status.health_status not in ["healthy", "ok", "connected"]:
                    services.append(service_name)
            return services
    
    def get_service(self, service_name: str) -> Optional[BaseServiceThread]:
        """Get service instance by name"""
        with self._lock:
            return self._services.get(service_name)
    
    def start_service(self, service_name: str) -> bool:
        """Start a service"""
        with self._lock:
            service = self._services.get(service_name)
            if service:
                return service.start()
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """Stop a service"""
        with self._lock:
            service = self._services.get(service_name)
            if service:
                return service.stop()
            return False
    
    def restart_service(self, service_name: str) -> bool:
        """Restart a service"""
        with self._lock:
            service = self._services.get(service_name)
            if service:
                return service.restart()
            return False
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health"""
        with self._lock:
            all_status = self.get_all_service_status()
            
            total_services = len(all_status)
            healthy_services = len(self.get_healthy_services())
            running_services = len(self.get_services_by_status("running"))
            
            overall_status = "healthy"
            if running_services == 0:
                overall_status = "critical"
            elif healthy_services < total_services:
                overall_status = "degraded"
            elif running_services < total_services:
                overall_status = "warning"
            
            return {
                "overall_status": overall_status,
                "total_services": total_services,
                "healthy_services": healthy_services,
                "running_services": running_services,
                "unhealthy_services": total_services - healthy_services,
                "last_updated": self._last_update,
                "services": {name: asdict(status) for name, status in all_status.items()}
            }
    
    def add_status_callback(self, event: str, callback: Callable):
        """Add callback for status events"""
        with self._lock:
            if event not in self._callbacks:
                self._callbacks[event] = []
            self._callbacks[event].append(callback)
    
    def remove_status_callback(self, event: str, callback: Callable):
        """Remove callback for status events"""
        with self._lock:
            if event in self._callbacks and callback in self._callbacks[event]:
                self._callbacks[event].remove(callback)
    
    def _update_service_status(self, service_name: str):
        """Update status for a specific service"""
        try:
            service = self._services.get(service_name)
            if not service:
                return
            
            service_info = service.get_status()
            uptime = service._get_uptime()
            
            self._status_cache[service_name] = GlobalServiceStatus(
                name=service_name,
                status=service_info.status.value,
                health_status=service_info.health_status,
                last_updated=datetime.utcnow(),
                error_message=service_info.error_message,
                uptime_seconds=uptime,
                restart_count=service_info.restart_count,
                details=service_info.details.copy(),
                thread_alive=service._thread.is_alive() if service._thread else False
            )
            
        except Exception as e:
            logger.error(f"Failed to update status for service {service_name}: {e}")
    
    def _on_service_update(self, service_name: str, event: str, data: Any):
        """Handle service update events"""
        with self._lock:
            self._update_service_status(service_name)
            self._last_update = datetime.utcnow()
            self._notify_callbacks("service_update", {
                "service_name": service_name,
                "event": event,
                "data": data
            })
    
    def _on_service_error(self, service_name: str, event: str, data: Any):
        """Handle service error events"""
        with self._lock:
            self._update_service_status(service_name)
            self._notify_callbacks("service_error", {
                "service_name": service_name,
                "event": event,
                "data": data
            })
    
    def _on_service_status_change(self, service_name: str, event: str, data: Any):
        """Handle service status change events"""
        with self._lock:
            self._update_service_status(service_name)
            self._notify_callbacks("service_status_change", {
                "service_name": service_name,
                "event": event,
                "data": data
            })
    
    def _notify_callbacks(self, event: str, data: Any):
        """Notify all callbacks for an event"""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(event, data)
                except Exception as e:
                    logger.error(f"Error in status registry callback: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics"""
        with self._lock:
            all_status = self.get_all_service_status()
            
            return {
                "total_services": len(self._services),
                "cached_statuses": len(self._status_cache),
                "last_update": self._last_update,
                "overall_health": self.get_overall_health(),
                "service_names": list(self._services.keys()),
                "callback_events": list(self._callbacks.keys())
            }


# Global registry instance
_global_registry: Optional[GlobalStatusRegistry] = None


def get_global_status_registry() -> GlobalStatusRegistry:
    """Get global status registry singleton"""
    global _global_registry
    if _global_registry is None:
        _global_registry = GlobalStatusRegistry()
    return _global_registry


def register_service(service: BaseServiceThread) -> bool:
    """Register a service with the global registry"""
    registry = get_global_status_registry()
    return registry.register_service(service)


def unregister_service(service_name: str) -> bool:
    """Unregister a service from the global registry"""
    registry = get_global_status_registry()
    return registry.unregister_service(service_name)


def get_service_status(service_name: str) -> Optional[GlobalServiceStatus]:
    """Get status of a specific service"""
    registry = get_global_status_registry()
    return registry.get_service_status(service_name)


def get_all_service_status() -> Dict[str, GlobalServiceStatus]:
    """Get status of all registered services"""
    registry = get_global_status_registry()
    return registry.get_all_service_status()


def get_overall_health() -> Dict[str, Any]:
    """Get overall system health"""
    registry = get_global_status_registry()
    return registry.get_overall_health()
