# API Documentation

## Overview

PiBlindHub provides a RESTful API for programmatic access to device control, configuration management, and system monitoring. All API endpoints require authentication via API keys.

## Base URL

```
http://localhost:8080/api/v1
```

## Authentication

All API endpoints (except authentication endpoints) require a valid API key in the request header:

```
X-API-Key: your-api-key-here
```

### API Key Management

API keys are generated through the Web UI and can be managed by administrators. Each API key has:
- Unique identifier
- Expiration date
- Associated user
- Usage statistics

## Response Format

All API responses follow a consistent format:

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data here
  },
  "message": "Operation completed successfully",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      // Additional error details
    }
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required or invalid
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

## Rate Limiting

API requests are rate limited to prevent abuse:
- **Default**: 60 requests per minute per API key
- **Burst**: 10 requests per burst window
- **Headers**: Rate limit information included in response headers

## Endpoints

### Authentication

#### Login
```http
POST /api/v1/auth/login
```

**Request Body:**
```json
{
  "username": "admin",
  "password": "your-password"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "id": "user-123",
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin"
    }
  }
}
```

#### Refresh Token
```http
POST /api/v1/auth/refresh
```

**Request Body:**
```json
{
  "refresh_token": "your-refresh-token"
}
```

#### Logout
```http
POST /api/v1/auth/logout
```

**Headers:**
```
Authorization: Bearer your-access-token
```

### Device Control

#### Get Device Status
```http
GET /api/v1/device/status
```

**Headers:**
```
X-API-Key: your-api-key
```

**Response:**
```json
{
  "success": true,
  "data": {
    "device_id": "store_001",
    "status": "closed",
    "position": 0,
    "last_updated": "2024-01-01T12:00:00Z",
    "is_online": true,
    "error_code": null
  }
}
```

#### Open Device
```http
POST /api/v1/device/open
```

**Headers:**
```
X-API-Key: your-api-key
```

**Request Body:**
```json
{
  "device_id": "store_001",
  "timeout": 30
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "command_id": "cmd-123",
    "status": "sent",
    "estimated_duration": 15
  }
}
```

#### Close Device
```http
POST /api/v1/device/close
```

**Headers:**
```
X-API-Key: your-api-key
```

**Request Body:**
```json
{
  "device_id": "store_001",
  "timeout": 30
}
```

#### Stop Device
```http
POST /api/v1/device/stop
```

**Headers:**
```
X-API-Key: your-api-key
```

**Request Body:**
```json
{
  "device_id": "store_001"
}
```

#### Get Device History
```http
GET /api/v1/device/history?device_id=store_001&limit=50&offset=0
```

**Headers:**
```
X-API-Key: your-api-key
```

**Query Parameters:**
- `device_id` (required): Device identifier
- `limit` (optional): Number of records to return (default: 50, max: 100)
- `offset` (optional): Number of records to skip (default: 0)
- `start_date` (optional): Start date filter (ISO 8601 format)
- `end_date` (optional): End date filter (ISO 8601 format)

**Response:**
```json
{
  "success": true,
  "data": {
    "history": [
      {
        "id": "hist-123",
        "device_id": "store_001",
        "action": "open",
        "status": "completed",
        "timestamp": "2024-01-01T12:00:00Z",
        "duration": 15.5,
        "user_id": "user-123"
      }
    ],
    "total": 150,
    "limit": 50,
    "offset": 0
  }
}
```

### Configuration Management

#### Get System Configuration
```http
GET /api/v1/config/system
```

**Headers:**
```
X-API-Key: your-api-key
```

**Response:**
```json
{
  "success": true,
  "data": {
    "device_settings": {
      "default_timeout": 30,
      "retry_attempts": 3,
      "auto_close_enabled": true,
      "auto_close_delay": 300
    },
    "mqtt_settings": {
      "broker_host": "localhost",
      "broker_port": 1883,
      "client_id": "store_manager"
    },
    "security_settings": {
      "session_timeout": 3600,
      "max_login_attempts": 5,
      "password_policy": {
        "min_length": 8,
        "require_uppercase": true,
        "require_lowercase": true,
        "require_numbers": true,
        "require_special_chars": true
      }
    }
  }
}
```

#### Update System Configuration
```http
PUT /api/v1/config/system
```

**Headers:**
```
X-API-Key: your-api-key
```

**Request Body:**
```json
{
  "device_settings": {
    "default_timeout": 45,
    "auto_close_enabled": false
  }
}
```

#### Get Device Configuration
```http
GET /api/v1/config/device/{device_id}
```

**Headers:**
```
X-API-Key: your-api-key
```

**Response:**
```json
{
  "success": true,
  "data": {
    "device_id": "store_001",
    "name": "Main Store",
    "location": "Building A",
    "settings": {
      "open_speed": 50,
      "close_speed": 50,
      "safety_limits": {
        "max_open_time": 60,
        "max_close_time": 60
      }
    },
    "mqtt_topics": {
      "command": "store/device/store_001/command",
      "status": "store/device/store_001/status"
    }
  }
}
```

#### Update Device Configuration
```http
PUT /api/v1/config/device/{device_id}
```

**Headers:**
```
X-API-Key: your-api-key
```

**Request Body:**
```json
{
  "name": "Updated Store Name",
  "settings": {
    "open_speed": 75,
    "close_speed": 75
  }
}
```

### MQTT Management

#### Get MQTT Status
```http
GET /api/v1/mqtt/status
```

**Headers:**
```
X-API-Key: your-api-key
```

**Response:**
```json
{
  "success": true,
  "data": {
    "connected": true,
    "broker_host": "localhost",
    "broker_port": 1883,
    "client_id": "store_manager",
    "last_connected": "2024-01-01T12:00:00Z",
    "messages_sent": 1250,
    "messages_received": 3420,
    "subscriptions": [
      "store/device/+/status",
      "store/device/+/config",
      "store/system/alerts"
    ]
  }
}
```

#### Publish MQTT Message
```http
POST /api/v1/mqtt/publish
```

**Headers:**
```
X-API-Key: your-api-key
```

**Request Body:**
```json
{
  "topic": "store/device/store_001/command",
  "message": {
    "command": "status",
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "qos": 1,
  "retain": false
}
```

#### Subscribe to MQTT Topic
```http
POST /api/v1/mqtt/subscribe
```

**Headers:**
```
X-API-Key: your-api-key
```

**Request Body:**
```json
{
  "topic": "store/device/+/status",
  "qos": 1
}
```

### User Management

#### Get Users
```http
GET /api/v1/users
```

**Headers:**
```
X-API-Key: your-api-key
```

**Response:**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "id": "user-123",
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
        "created_at": "2024-01-01T12:00:00Z",
        "last_login": "2024-01-01T12:00:00Z",
        "is_active": true
      }
    ],
    "total": 1
  }
}
```

#### Create User
```http
POST /api/v1/users
```

**Headers:**
```
X-API-Key: your-api-key
```

**Request Body:**
```json
{
  "username": "operator1",
  "email": "operator1@example.com",
  "password": "SecurePassword123!",
  "role": "operator"
}
```

#### Update User
```http
PUT /api/v1/users/{user_id}
```

**Headers:**
```
X-API-Key: your-api-key
```

**Request Body:**
```json
{
  "email": "newemail@example.com",
  "role": "admin",
  "is_active": true
}
```

#### Delete User
```http
DELETE /api/v1/users/{user_id}
```

**Headers:**
```
X-API-Key: your-api-key
```

### API Key Management

#### Get API Keys
```http
GET /api/v1/api-keys
```

**Headers:**
```
X-API-Key: your-api-key
```

**Response:**
```json
{
  "success": true,
  "data": {
    "api_keys": [
      {
        "id": "key-123",
        "name": "Mobile App Key",
        "user_id": "user-123",
        "created_at": "2024-01-01T12:00:00Z",
        "expires_at": "2025-01-01T12:00:00Z",
        "last_used": "2024-01-01T12:00:00Z",
        "is_active": true,
        "usage_count": 1250
      }
    ],
    "total": 1
  }
}
```

#### Create API Key
```http
POST /api/v1/api-keys
```

**Headers:**
```
X-API-Key: your-api-key
```

**Request Body:**
```json
{
  "name": "New API Key",
  "expires_days": 365,
  "user_id": "user-123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "key-456",
    "api_key": "sk-1234567890abcdef...",
    "name": "New API Key",
    "expires_at": "2025-01-01T12:00:00Z",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

#### Revoke API Key
```http
DELETE /api/v1/api-keys/{key_id}
```

**Headers:**
```
X-API-Key: your-api-key
```

### System Monitoring

#### Get System Health
```http
GET /api/v1/system/health
```

**Headers:**
```
X-API-Key: your-api-key
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "uptime": 86400,
    "services": {
      "database": "healthy",
      "mqtt": "healthy",
      "device_controller": "healthy"
    },
    "metrics": {
      "cpu_usage": 15.5,
      "memory_usage": 256.7,
      "disk_usage": 45.2
    }
  }
}
```

#### Get System Logs
```http
GET /api/v1/system/logs?level=ERROR&limit=100
```

**Headers:**
```
X-API-Key: your-api-key
```

**Query Parameters:**
- `level` (optional): Log level filter (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `limit` (optional): Number of log entries to return (default: 100, max: 1000)
- `start_date` (optional): Start date filter (ISO 8601 format)
- `end_date` (optional): End date filter (ISO 8601 format)

## Error Codes

| Code | Description |
|------|-------------|
| `INVALID_API_KEY` | API key is missing or invalid |
| `API_KEY_EXPIRED` | API key has expired |
| `RATE_LIMIT_EXCEEDED` | Rate limit exceeded |
| `DEVICE_NOT_FOUND` | Device not found |
| `DEVICE_OFFLINE` | Device is offline |
| `DEVICE_BUSY` | Device is currently busy |
| `INVALID_COMMAND` | Invalid device command |
| `CONFIGURATION_ERROR` | Configuration error |
| `MQTT_CONNECTION_ERROR` | MQTT connection error |
| `VALIDATION_ERROR` | Request validation error |
| `PERMISSION_DENIED` | Insufficient permissions |
| `INTERNAL_ERROR` | Internal server error |

## WebSocket API

For real-time updates, the system provides WebSocket connections:

### Connection
```
ws://localhost:8080/ws?token=your-jwt-token
```

### Message Format
```json
{
  "type": "device_status",
  "data": {
    "device_id": "store_001",
    "status": "opening",
    "position": 25,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### Message Types
- `device_status` - Device status updates
- `device_command_result` - Command execution results
- `system_alert` - System alerts and notifications
- `mqtt_message` - MQTT message notifications

## SDK Examples

### Python
```python
import requests

class StoreManagerAPI:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
    
    def get_device_status(self, device_id):
        response = requests.get(
            f"{self.base_url}/api/v1/device/status",
            headers=self.headers
        )
        return response.json()
    
    def open_device(self, device_id, timeout=30):
        response = requests.post(
            f"{self.base_url}/api/v1/device/open",
            headers=self.headers,
            json={"device_id": device_id, "timeout": timeout}
        )
        return response.json()

# Usage
api = StoreManagerAPI("http://localhost:8080", "your-api-key")
status = api.get_device_status("store_001")
result = api.open_device("store_001")
```

### JavaScript
```javascript
class StoreManagerAPI {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.headers = {
            'X-API-Key': apiKey,
            'Content-Type': 'application/json'
        };
    }
    
    async getDeviceStatus(deviceId) {
        const response = await fetch(`${this.baseUrl}/api/v1/device/status`, {
            headers: this.headers
        });
        return await response.json();
    }
    
    async openDevice(deviceId, timeout = 30) {
        const response = await fetch(`${this.baseUrl}/api/v1/device/open`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({ device_id: deviceId, timeout })
        });
        return await response.json();
    }
}

// Usage
const api = new StoreManagerAPI('http://localhost:8080', 'your-api-key');
const status = await api.getDeviceStatus('store_001');
const result = await api.openDevice('store_001');
```

## Testing

### Postman Collection

A Postman collection is available for testing the API endpoints. Import the collection and configure the following variables:

- `base_url`: http://localhost:8080
- `api_key`: Your API key
- `device_id`: store_001

### cURL Examples

#### Get Device Status
```bash
curl -X GET "http://localhost:8080/api/v1/device/status" \
  -H "X-API-Key: your-api-key"
```

#### Open Device
```bash
curl -X POST "http://localhost:8080/api/v1/device/open" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "store_001", "timeout": 30}'
```

#### Create API Key
```bash
curl -X POST "http://localhost:8080/api/v1/api-keys" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Key", "expires_days": 30}'
```
