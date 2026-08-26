# Threaded Services Architecture

## Overview

The MotorisedStoreManager application has been refactored to use a threaded services architecture where critical services (WiFi, LAN, Hotspot, and Database) run in separate threads. This provides better isolation, independent management, and improved reliability.

## Architecture Components

### 1. Base Service Thread (`base_service_thread.py`)

The foundation for all threaded services:

- **ServiceStatus Enum**: Defines service states (STOPPED, STARTING, RUNNING, STOPPING, ERROR, RESTARTING)
- **ServiceInfo Dataclass**: Contains service metadata and status information
- **BaseServiceThread Class**: Abstract base class with common functionality:
  - Thread management (start/stop/restart)
  - Health monitoring
  - Status tracking
  - Callback system for events
  - Statistics collection

### 2. Global Status Registry (`global_status_registry.py`)

Central registry for managing and accessing service status across the application:

- **GlobalServiceStatus**: Standardized status structure
- **GlobalStatusRegistry**: Main registry class with features:
  - Service registration/unregistration
  - Status caching and updates
  - Health monitoring
  - Callback management
  - Overall system health assessment

### 3. Threaded Services

#### WiFi Service Thread (`wifi_service_thread.py`)
- Manages WiFi connectivity monitoring
- Handles hotspot creation and management
- Network interface detection
- Connectivity status tracking
- Auto-hotspot functionality

#### LAN Service Thread (`lan_service_thread.py`)
- Monitors LAN interface status
- Tracks network connectivity
- Interface speed and duplex detection
- Gateway and DNS server discovery
- Connection testing

#### Hotspot Service Thread (`hotspot_service_thread.py`)
- Independent hotspot management
- Client connection tracking
- Service configuration
- Uptime monitoring
- Status reporting

#### Database Service Thread (`database_service_thread.py`)
- Database connection pool management
- Performance monitoring
- Backup scheduling
- Maintenance tasks
- Health checks

### 4. Updated Service Manager (`service_manager.py`)

Enhanced to handle both regular and threaded services:

- **Dual Service Management**: Manages regular services and threaded services separately
- **Lifecycle Management**: Starts/stops services in proper order
- **Health Monitoring**: Comprehensive health checks for all service types
- **Service Discovery**: Unified interface for accessing any service

### 5. API Endpoints (`routes.py`)

New API endpoints for threaded service management:

- `GET /api/services/threaded/status` - Get all threaded services status
- `GET /api/services/threaded/{service_name}/status` - Get specific service status
- `POST /api/services/threaded/{service_name}/start` - Start a service
- `POST /api/services/threaded/{service_name}/stop` - Stop a service
- `POST /api/services/threaded/{service_name}/restart` - Restart a service
- `GET /api/services/threaded/overall-health` - Get overall system health

## Key Features

### 1. Independent Service Management
- Each service runs in its own thread
- Services can be started, stopped, and restarted independently
- Failure in one service doesn't affect others

### 2. Real-time Status Monitoring
- Continuous health monitoring
- Status updates every few seconds
- Detailed service information available

### 3. Global Status Access
- Any page can access service status through the global registry
- Consistent status format across all services
- Real-time updates via callbacks

### 4. Service Lifecycle Management
- Proper startup/shutdown sequences
- Graceful error handling
- Automatic restart capabilities

### 5. Performance Monitoring
- Service uptime tracking
- Performance metrics collection
- Error rate monitoring

## Usage Examples

### Starting a Service
```python
from src.webapp.services.global_status_registry import get_global_status_registry

registry = get_global_status_registry()
success = registry.start_service("wifi")
```

### Getting Service Status
```python
from src.webapp.services.global_status_registry import get_service_status

status = get_service_status("database")
print(f"Database status: {status.status}")
print(f"Health: {status.health_status}")
```

### Getting Overall Health
```python
from src.webapp.services.global_status_registry import get_overall_health

health = get_overall_health()
print(f"Overall status: {health['overall_status']}")
print(f"Healthy services: {health['healthy_services']}")
```

## Benefits

1. **Improved Reliability**: Services are isolated and can recover independently
2. **Better Performance**: Services run concurrently without blocking each other
3. **Enhanced Monitoring**: Real-time status and health information
4. **Flexible Management**: Services can be managed individually
5. **Scalability**: Easy to add new threaded services
6. **Debugging**: Better error isolation and logging

## Migration Notes

- Existing API endpoints continue to work
- Service status is now more detailed and accurate
- New management endpoints provide additional control
- Global status registry provides unified access to all services

## Future Enhancements

- Service dependency management
- Automatic failover capabilities
- Service configuration hot-reloading
- Advanced monitoring and alerting
- Service performance optimization
