# PiBlindHub

An open-source Raspberry Pi hub for motorised blinds, featuring GPIO control, a Web UI, MQTT configuration, and API access.

## Project Overview

This project provides an upper layer management system for motorised store devices. It builds upon an existing Python application that controls store operations through three core methods: Open, Close, and Stop.

## Key Features

- **Web UI**: Complete management interface with device control and configuration
- **MQTT Integration**: Bidirectional communication for device status and commands
- **Secure API**: RESTful API with API key authentication
- **Security**: Default password system with mandatory first-login reset
- **Configuration Management**: Centralized settings for all system components

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web UI        │    │   API Layer     │    │   MQTT Client   │
│   (Frontend)    │◄──►│   (Backend)     │◄──►│   (Messaging)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Security      │    │   Device        │    │   Configuration │
│   Layer         │    │   Controller    │    │   Manager       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                    ┌─────────────────┐
                    │   Raspberry Pi  │
                    │   Device App    │
                    │   (src/raspberryapp) │
                    └─────────────────┘
```

## Core Components

### 1. Device Controller
- **Open**: Opens the motorised store
- **Close**: Closes the motorised store  
- **Stop**: Emergency stop functionality

### 2. Web UI
- Device status monitoring
- Manual control interface
- Configuration management
- User authentication
- API key management

### 3. MQTT Integration
- Device status publishing
- Command reception
- Configuration synchronization
- Real-time monitoring

### 4. API Layer
- RESTful endpoints for all operations
- API key authentication
- Device control endpoints
- Configuration endpoints
- Status and monitoring endpoints

## Security Features

- **Default Password System**: Initial login requires password reset
- **API Key Authentication**: All API calls protected by generated keys
- **Session Management**: Secure user sessions
- **Input Validation**: Comprehensive data validation
- **Access Control**: Role-based permissions

## Technology Stack

- **Backend**: Python (FastAPI/Flask)
- **Frontend**: HTML/CSS/JavaScript (or modern framework)
- **Database**: SQLite/PostgreSQL for configuration and logs
- **MQTT**: paho-mqtt or similar
- **Security**: JWT tokens, bcrypt for password hashing
- **Platform**: Raspberry Pi OS

## Getting Started

1. Clone `https://github.com/capisoft-lib/ok-go-pour-PiBlindHub.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `env.example` to `.env` and replace every security placeholder
4. Copy the files in `src/config/*.example.json` to their matching `*.json` names and customize them
5. Run the web application: `python src/webapp/main.py`
6. Access Web UI at `http://localhost:8080`
7. Login with the configured credentials and reset the password

## Default Credentials

- **Username**: `admin`
- **Password**: `changeme123` (must be changed on first login)

## API Documentation

API endpoints are available at `/api/docs` when running the application.

## Configuration

All configuration files are located in the `src/config/` directory:
- `mqtt_config.json`: MQTT broker settings
- `app_config.json`: Application settings
- `security_config.json`: Security parameters

## Development

See `DEVELOPMENT.md` for detailed development guidelines and rules.

## Open source

PiBlindHub is released under the [MIT License](LICENSE). Its canonical public repository is https://github.com/capisoft-lib/ok-go-pour-PiBlindHub.

Runtime databases, logs, device identifiers, network settings, password hashes, and active secrets are intentionally excluded from version control.
