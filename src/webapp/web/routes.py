"""
Simplified Web UI routes for PiBlindHub
Uses direct status checking instead of background services
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import logging

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.webapp.services import (
    get_security_service, get_action_service,
    get_logging_service, get_action_logging_service
)
from src.webapp.services.security_service import UserRole
from src.webapp.utils.network_status_checker import get_network_status_checker

logger = logging.getLogger(__name__)

router = APIRouter()

# Templates will be set by the main app
templates = None


def set_templates(templates_instance):
    """Set templates instance from main app"""
    global templates
    templates = templates_instance


async def get_current_user(request: Request):
    """Get current authenticated user from session"""
    security_service = get_security_service()
    
    # Check for session token
    session_token = request.cookies.get("session_token")
    if not session_token:
        return None
    
    try:
        user = security_service.validate_session_token(session_token)
        return user
    except Exception as e:
        logger.warning(f"Invalid session token: {e}")
        return None


async def require_auth(request: Request, current_user = Depends(get_current_user)):
    """Require authentication for protected routes"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Check if password change is required
    security_service = get_security_service()
    if security_service.is_password_change_required(current_user):
        return RedirectResponse(url="/change-password", status_code=status.HTTP_302_FOUND)
    
    return current_user


async def require_admin(request: Request, current_user = Depends(require_auth)):
    """Require admin role for protected routes"""
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    if current_user.role.value != 'admin':
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Access Denied",
            "details": "Admin privileges required"
        })
    return current_user


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, current_user = Depends(require_auth)):
    """Main dashboard page with simplified status checking"""
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    try:
        # Get services
        state_service = get_state_service()
        action_service = get_action_service()
        
        # Get dashboard data
        devices_dict = state_service.get_all_devices()
        devices = list(devices_dict.values())  # Convert dict to list of DeviceInfo objects
        recent_actions = await action_service.get_recent_actions(limit=10)
        
        # Get network status using simplified checker
        network_checker = get_network_status_checker()
        network_status = await network_checker.get_all_status()
        
        # Create simplified system health from network status to match template expectations
        wifi_data = network_status.get("wifi", {})
        lan_data = network_status.get("lan", {})
        hotspot_data = network_status.get("hotspot", {})
        
        system_health = {
            "overall": "healthy" if all([
                wifi_data.get("status") not in ["error"],
                lan_data.get("status") not in ["error"],
                hotspot_data.get("status") not in ["Error"]
            ]) else "warning",
            "services": {
                "wifi": {
                    "status": "healthy" if wifi_data.get("status") not in ["error"] else "unhealthy",
                    "details": {
                        "connected": wifi_data.get("connected", False),
                        "ssid": wifi_data.get("ssid"),
                        "signal_strength": wifi_data.get("signal_strength"),
                        "ip": wifi_data.get("ip_address")
                    }
                },
                "lan": {
                    "status": "healthy" if lan_data.get("status") not in ["error"] else "unhealthy",
                    "details": {
                        "connected": lan_data.get("connected", False),
                        "interface": lan_data.get("interface"),
                        "ip": lan_data.get("ip_address")
                    }
                },
                "hotspot": {
                    "status": "healthy" if hotspot_data.get("status") not in ["Error"] else "unhealthy",
                    "details": {
                        "active": hotspot_data.get("active", False),
                        "ssid": hotspot_data.get("ssid"),
                        "ip": hotspot_data.get("ip_address")
                    }
                }
            }
        }
        
        # Get system statistics
        stats = {
            "total_devices": len(devices),
            "online_devices": len([d for d in devices if d.is_online]),
            "recent_actions": len(recent_actions),
            "system_health": system_health["overall"]
        }
        
        # Transform network_status to match template expectations
        template_network_status = {
            "wifi_connected": wifi_data.get("connected", False),
            "current_ssid": wifi_data.get("ssid"),
            "lan_connected": lan_data.get("connected", False),
            "lan_interface": lan_data.get("interface"),
            "hotspot_active": hotspot_data.get("active", False),
            "hotspot_info": {
                "hotspot_name": hotspot_data.get("ssid"),
                "hotspot_ip": hotspot_data.get("ip_address"),
                "hotspot_port": "8080",  # Default port
                "access_url": f"http://{hotspot_data.get('ip_address', 'localhost')}:8080" if hotspot_data.get("ip_address") else None
            } if hotspot_data.get("active") else None
        }
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": current_user,
            "devices": devices,
            "recent_actions": recent_actions,
            "system_health": system_health,
            "stats": stats,
            "network_status": template_network_status
        })
        
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load dashboard",
            "details": str(e)
        })


@router.get("/devices", response_class=HTMLResponse)
async def devices_page(request: Request, current_user = Depends(require_auth)):
    """Devices management page"""
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    try:
        return templates.TemplateResponse("devices.html", {
            "request": request,
            "user": current_user
        })
    except Exception as e:
        logger.error(f"Error loading devices page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load devices page",
            "details": str(e)
        })


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, current_user = Depends(require_auth)):
    """Logs and monitoring page"""
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    try:
        logging_service = get_logging_service()
        
        # Get recent logs
        recent_logs = logging_service.get_recent_logs(limit=100)
        
        return templates.TemplateResponse("logs.html", {
            "request": request,
            "user": current_user,
            "logs": recent_logs
        })
        
    except Exception as e:
        logger.error(f"Error loading logs page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load logs",
            "details": str(e)
        })


@router.get("/action-logs", response_class=HTMLResponse)
async def action_logs_page(request: Request, current_user = Depends(require_admin)):
    """Action logs page (Admin only)"""
    try:
        return templates.TemplateResponse("action_logs.html", {
            "request": request,
            "user": current_user
        })
        
    except Exception as e:
        logger.error(f"Error loading action logs page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load action logs",
            "details": str(e)
        })


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, current_user = Depends(require_admin)):
    """Settings and configuration page (Admin only)"""
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    try:
        # Get network status using simplified checker
        network_checker = get_network_status_checker()
        network_status = await network_checker.get_all_status()
        
        # Create simplified system health from network status
        system_health = {
            "overall": "healthy" if all([
                network_status.get("wifi", {}).get("status") not in ["error"],
                network_status.get("lan", {}).get("status") not in ["error"],
                network_status.get("hotspot", {}).get("status") not in ["Error"]
            ]) else "warning",
            "services": {
                "wifi": {
                    "status": "healthy" if network_status.get("wifi", {}).get("status") not in ["error"] else "unhealthy",
                    "details": network_status.get("wifi", {})
                },
                "lan": {
                    "status": "healthy" if network_status.get("lan", {}).get("status") not in ["error"] else "unhealthy",
                    "details": network_status.get("lan", {})
                },
                "hotspot": {
                    "status": "healthy" if network_status.get("hotspot", {}).get("status") not in ["Error"] else "unhealthy",
                    "details": network_status.get("hotspot", {})
                }
            }
        }
        
        # Load current application configuration
        import json
        config_path = "src/config/app_config.json"
        app_config = {}
        try:
            with open(config_path, 'r') as f:
                app_config = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load app config: {e}")
            app_config = {"application": {"port": 8080, "version": "1.0.0"}}
        
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "user": current_user,
            "system_health": system_health,
            "app_config": app_config
        })
        
    except Exception as e:
        logger.error(f"Error loading settings page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load settings",
            "details": str(e)
        })


@router.get("/api/network-status")
async def get_network_status_api(current_user = Depends(require_auth)):
    """Get current network status (API endpoint)"""
    try:
        network_checker = get_network_status_checker()
        network_status = await network_checker.get_all_status()
        return network_status
    except Exception as e:
        logger.error(f"Error getting network status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get network status")


@router.get("/api/wifi-status")
async def wifi_status_api(current_user = Depends(require_auth)):
    """Get WiFi status (API endpoint)"""
    try:
        network_checker = get_network_status_checker()
        wifi_status = await network_checker.get_wifi_status()
        return wifi_status
    except Exception as e:
        logger.error(f"Error getting WiFi status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get WiFi status")


@router.get("/api/lan-status")
async def lan_status_api(current_user = Depends(require_auth)):
    """Get LAN status (API endpoint)"""
    try:
        network_checker = get_network_status_checker()
        lan_status = await network_checker.get_lan_status()
        return lan_status
    except Exception as e:
        logger.error(f"Error getting LAN status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get LAN status")


@router.get("/api/hotspot-status")
async def hotspot_status_api(current_user = Depends(require_auth)):
    """Get hotspot status (API endpoint)"""
    try:
        network_checker = get_network_status_checker()
        hotspot_status = await network_checker.get_hotspot_status()
        return hotspot_status
    except Exception as e:
        logger.error(f"Error getting hotspot status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get hotspot status")


@router.post("/api/hotspot/start")
async def start_hotspot_api(current_user = Depends(require_admin)):
    """Start WiFi hotspot (Admin only)"""
    try:
        wifi_service = get_wifi_service()
        action_logging_service = get_action_logging_service()
        success = await wifi_service.create_hotspot()
        
        # Log hotspot action
        action_logging_service.log_config_change(
            config_type="hotspot",
            user_id=current_user.id,
            success=success,
            parameters={"action": "start"}
        )
        
        if success:
            hotspot_info = wifi_service.get_hotspot_info()
            return {"success": True, "hotspot_info": hotspot_info}
        else:
            raise HTTPException(status_code=500, detail="Failed to start hotspot")
    except Exception as e:
        logger.error(f"Error starting hotspot: {e}")
        
        # Log failed hotspot action
        try:
            action_logging_service = get_action_logging_service()
            action_logging_service.log_config_change(
                config_type="hotspot",
                user_id=current_user.id,
                success=False,
                parameters={"action": "start", "error": str(e)}
            )
        except:
            pass
        
        raise HTTPException(status_code=500, detail="Failed to start hotspot")


@router.post("/api/hotspot/stop")
async def stop_hotspot_api(current_user = Depends(require_admin)):
    """Stop WiFi hotspot (Admin only)"""
    try:
        wifi_service = get_wifi_service()
        action_logging_service = get_action_logging_service()
        success = await wifi_service.stop_hotspot()
        
        # Log hotspot action
        action_logging_service.log_config_change(
            config_type="hotspot",
            user_id=current_user.id,
            success=success,
            parameters={"action": "stop"}
        )
        
        return {"success": success}
    except Exception as e:
        logger.error(f"Error stopping hotspot: {e}")
        
        # Log failed hotspot action
        try:
            action_logging_service = get_action_logging_service()
            action_logging_service.log_config_change(
                config_type="hotspot",
                user_id=current_user.id,
                success=False,
                parameters={"action": "stop", "error": str(e)}
            )
        except:
            pass
        
        raise HTTPException(status_code=500, detail="Failed to stop hotspot")


@router.post("/api/admin/change-password")
async def change_admin_password_api(request: Request, current_user = Depends(require_admin)):
    """Change admin password (Admin only)"""
    try:
        data = await request.json()
        current_password = data.get("current_password")
        new_password = data.get("new_password")
        
        if not current_password or not new_password:
            return {"success": False, "error": "Current password and new password are required"}
        
        if len(new_password) < 8:
            return {"success": False, "error": "New password must be at least 8 characters long"}
        
        # Get security service
        security_service = get_security_service()
        action_logging_service = get_action_logging_service()
        client_ip = request.client.host if request.client else None
        
        # Verify current password by attempting authentication
        if not security_service.authenticate_user(current_user.username, current_password):
            # Log failed password change attempt
            action_logging_service.log_password_change(
                user_id=current_user.id,
                username=current_user.username,
                success=False,
                ip_address=client_ip
            )
            return {"success": False, "error": "Current password is incorrect"}
        
        # Change password using the security service
        logger.info(f"Admin password change requested by user: {current_user.username}")
        
        if security_service.change_password(current_user, current_password, new_password):
            # Log successful password change
            action_logging_service.log_password_change(
                user_id=current_user.id,
                username=current_user.username,
                success=True,
                ip_address=client_ip
            )
            return {"success": True, "message": "Admin password changed successfully"}
        else:
            # Log failed password change attempt
            action_logging_service.log_password_change(
                user_id=current_user.id,
                username=current_user.username,
                success=False,
                ip_address=client_ip
            )
            return {"success": False, "error": "Failed to change password"}
        
    except Exception as e:
        logger.error(f"Error changing admin password: {e}")
        return {"success": False, "error": "Failed to change admin password"}


@router.get("/network-config", response_class=HTMLResponse)
async def network_config_page(request: Request, current_user = Depends(require_admin)):
    """Network configuration page (Admin only)"""
    try:
        network_config_service = get_network_config_service()
        wifi_service = get_wifi_service()
        
        # Get current configuration and status
        config = network_config_service.get_config()
        network_status = await wifi_service.get_network_status()
        
        return templates.TemplateResponse("network_config.html", {
            "request": request,
            "user": current_user,
            "config": config,
            "network_status": network_status
        })
        
    except Exception as e:
        logger.error(f"Error loading network configuration page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load network configuration",
            "details": str(e)
        })


@router.get("/api/network-config")
async def get_network_config_api(current_user = Depends(require_admin)):
    """Get network configuration (Admin only)"""
    try:
        network_config_service = get_network_config_service()
        config = network_config_service.get_config()
        status = network_config_service.get_network_status()
        
        return {
            "config": {
                "mode": config.mode,
                "wifi_networks": [
                    {
                        "ssid": wifi.ssid,
                        "password": "***" if wifi.password else "",  # Hide password
                        "priority": wifi.priority,
                        "hidden": wifi.hidden
                    } for wifi in config.wifi_networks
                ],
                "hotspot": {
                    "enabled": config.hotspot.enabled,
                    "ssid": config.hotspot.ssid,
                    "password": "***" if config.hotspot.password else "",  # Hide password
                    "channel": config.hotspot.channel,
                    "ip_address": config.hotspot.ip_address,
                    "dhcp_start": config.hotspot.dhcp_start,
                    "dhcp_end": config.hotspot.dhcp_end
                },
                "broadcast_discovery": {
                    "enabled": config.broadcast_discovery.enabled,
                    "auto_start": config.broadcast_discovery.auto_start,
                    "discovery_port": config.broadcast_discovery.discovery_port,
                    "response_port": config.broadcast_discovery.response_port
                }
            },
            "status": status
        }
    except Exception as e:
        logger.error(f"Error getting network configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to get network configuration")


@router.post("/api/network-config")
async def update_network_config_api(config_data: dict, current_user = Depends(require_admin)):
    """Update network configuration (Admin only)"""
    try:
        network_config_service = get_network_config_service()
        action_logging_service = get_action_logging_service()
        success = network_config_service.update_config(config_data)
        
        # Log configuration change
        action_logging_service.log_config_change(
            config_type="network",
            user_id=current_user.id,
            success=success,
            parameters={"config_keys": list(config_data.keys()) if config_data else []}
        )
        
        if success:
            return {"success": True, "message": "Configuration updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update configuration")
            
    except Exception as e:
        logger.error(f"Error updating network configuration: {e}")
        
        # Log failed configuration change
        try:
            action_logging_service = get_action_logging_service()
            action_logging_service.log_config_change(
                config_type="network",
                user_id=current_user.id,
                success=False,
                parameters={"error": str(e)}
            )
        except:
            pass
        
        raise HTTPException(status_code=500, detail="Failed to update network configuration")


@router.post("/api/network-config/apply")
async def apply_network_config_api(current_user = Depends(require_admin)):
    """Apply network configuration (Admin only)"""
    try:
        network_config_service = get_network_config_service()
        results = await network_config_service.apply_config()
        
        return results
        
    except Exception as e:
        logger.error(f"Error applying network configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to apply network configuration")


@router.get("/api/network-config/scan")
async def scan_wifi_networks_api(current_user = Depends(require_admin)):
    """Scan for available WiFi networks (Admin only)"""
    try:
        network_config_service = get_network_config_service()
        networks = await network_config_service.scan_wifi_networks()
        
        return {"networks": networks}
        
    except Exception as e:
        logger.error(f"Error scanning WiFi networks: {e}")
        raise HTTPException(status_code=500, detail="Failed to scan WiFi networks")


@router.get("/api/broadcast-discovery/status")
async def get_broadcast_discovery_status_api(current_user = Depends(require_admin)):
    """Get broadcast discovery service status (Admin only)"""
    try:
        broadcast_discovery_service = get_broadcast_discovery_service()
        status = broadcast_discovery_service.get_status()
        return status
    except Exception as e:
        logger.error(f"Error getting broadcast discovery status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get broadcast discovery status")


@router.post("/api/broadcast-discovery/start")
async def start_broadcast_discovery_api(current_user = Depends(require_admin)):
    """Start broadcast discovery service (Admin only)"""
    try:
        broadcast_discovery_service = get_broadcast_discovery_service()
        success = await broadcast_discovery_service.start_listening()
        
        if success:
            return {"success": True, "message": "Broadcast discovery started"}
        else:
            raise HTTPException(status_code=500, detail="Failed to start broadcast discovery")
            
    except Exception as e:
        logger.error(f"Error starting broadcast discovery: {e}")
        raise HTTPException(status_code=500, detail="Failed to start broadcast discovery")


@router.post("/api/broadcast-discovery/stop")
async def stop_broadcast_discovery_api(current_user = Depends(require_admin)):
    """Stop broadcast discovery service (Admin only)"""
    try:
        broadcast_discovery_service = get_broadcast_discovery_service()
        success = await broadcast_discovery_service.stop_listening()
        
        if success:
            return {"success": True, "message": "Broadcast discovery stopped"}
        else:
            raise HTTPException(status_code=500, detail="Failed to stop broadcast discovery")
            
    except Exception as e:
        logger.error(f"Error stopping broadcast discovery: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop broadcast discovery")


@router.post("/api/broadcast-discovery/send-request")
async def send_discovery_request_api(target_ip: str = "255.255.255.255", current_user = Depends(require_admin)):
    """Send a discovery request to find other devices (Admin only)"""
    try:
        broadcast_discovery_service = get_broadcast_discovery_service()
        result = await broadcast_discovery_service.send_discovery_request(target_ip)
        return result
    except Exception as e:
        logger.error(f"Error sending discovery request: {e}")
        raise HTTPException(status_code=500, detail="Failed to send discovery request")


# Device API Endpoints
@router.get("/api/device/status")
async def get_device_status_api(current_user = Depends(require_auth)):
    """Get device status"""
    try:
        from ..services.device_controller import DeviceController
        
        device_controller = DeviceController(username=current_user.username)
        status = device_controller.get_device_status_sync()
        
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"Error getting device status: {e}")
        return {
            "success": False,
            "message": str(e)
        }


@router.post("/api/device/open")
async def open_device_api(current_user = Depends(require_auth)):
    """Open the device"""
    try:
        from ..services.device_controller import DeviceController
        
        device_controller = DeviceController(username=current_user.username)
        result = device_controller.open_device_sync()
        
        return {
            "success": True,
            "message": "Device open command sent successfully",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error opening device: {e}")
        return {
            "success": False,
            "message": str(e)
        }


@router.post("/api/device/close")
async def close_device_api(current_user = Depends(require_auth)):
    """Close the device"""
    try:
        from ..services.device_controller import DeviceController
        
        device_controller = DeviceController(username=current_user.username)
        result = device_controller.close_device_sync()
        
        return {
            "success": True,
            "message": "Device close command sent successfully",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error closing device: {e}")
        return {
            "success": False,
            "message": str(e)
        }


@router.post("/api/device/stop")
async def stop_device_api(current_user = Depends(require_auth)):
    """Stop the device"""
    try:
        from ..services.device_controller import DeviceController
        
        device_controller = DeviceController(username=current_user.username)
        result = device_controller.stop_device_sync()
        
        return {
            "success": True,
            "message": "Device stop command sent successfully",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error stopping device: {e}")
        return {
            "success": False,
            "message": str(e)
        }


@router.post("/api/device/calibrate")
async def calibrate_device_api(current_user = Depends(require_auth)):
    """Calibrate the device"""
    try:
        from ..services.device_controller import DeviceController
        
        device_controller = DeviceController(username=current_user.username)
        result = device_controller.calibrate_device_sync()
        
        return {
            "success": True,
            "message": "Device calibration started successfully",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error calibrating device: {e}")
        return {
            "success": False,
            "message": str(e)
        }


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {
        "request": request
    })


@router.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request, current_user = Depends(get_current_user)):
    """Password change page"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Check if password change is actually required
    security_service = get_security_service()
    if not security_service.is_password_change_required(current_user):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("change_password.html", {
        "request": request,
        "user": current_user
    })


@router.post("/login")
async def login_submit(request: Request):
    """Handle login form submission"""
    try:
        form_data = await request.form()
        username = form_data.get("username")
        password = form_data.get("password")
        
        if not username or not password:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Username and password are required"
            })
        
        security_service = get_security_service()
        action_logging_service = get_action_logging_service()
        user = security_service.authenticate_user(username, password)
        
        # Get client IP and user agent for logging
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        if user:
            # Log successful login
            action_logging_service.log_user_login(
                user_id=user.id,
                username=username,
                success=True,
                ip_address=client_ip,
                user_agent=user_agent
            )
            
            # Create session token
            session_token = security_service.create_session_token(user)
            
            # Check if password change is required
            if security_service.is_password_change_required(user):
                # Redirect to password change page
                response = RedirectResponse(url="/change-password", status_code=status.HTTP_302_FOUND)
            else:
                # Redirect to dashboard
                response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
            
            response.set_cookie(
                key="session_token",
                value=session_token,
                httponly=True,
                secure=True,
                samesite="lax"
            )
            return response
        else:
            # Log failed login attempt
            action_logging_service.log_user_login(
                user_id=None,
                username=username,
                success=False,
                ip_address=client_ip,
                user_agent=user_agent
            )
            
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Invalid username or password"
            })
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Login failed. Please try again."
        })


@router.post("/change-password")
async def change_password_submit(request: Request, current_user = Depends(get_current_user)):
    """Handle password change form submission"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    try:
        form_data = await request.form()
        current_password = form_data.get("current_password")
        new_password = form_data.get("new_password")
        confirm_password = form_data.get("confirm_password")
        
        # Validation
        if not current_password or not new_password or not confirm_password:
            return templates.TemplateResponse("change_password.html", {
                "request": request,
                "user": current_user,
                "error": "All fields are required"
            })
        
        if new_password != confirm_password:
            return templates.TemplateResponse("change_password.html", {
                "request": request,
                "user": current_user,
                "error": "New password and confirm password do not match"
            })
        
        if len(new_password) < 8:
            return templates.TemplateResponse("change_password.html", {
                "request": request,
                "user": current_user,
                "error": "New password must be at least 8 characters long"
            })
        
        # Password strength validation
        has_upper = any(c.isupper() for c in new_password)
        has_lower = any(c.islower() for c in new_password)
        has_digit = any(c.isdigit() for c in new_password)
        has_special = any(c in "!@#$%^&*(),.?\":{}|<>" for c in new_password)
        
        if not (has_upper and has_lower and has_digit and has_special):
            return templates.TemplateResponse("change_password.html", {
                "request": request,
                "user": current_user,
                "error": "Password must contain uppercase, lowercase, numbers, and special characters"
            })
        
        # Change password
        security_service = get_security_service()
        action_logging_service = get_action_logging_service()
        client_ip = request.client.host if request.client else None
        
        if security_service.change_password(current_user, current_password, new_password):
            # Log successful password change
            action_logging_service.log_password_change(
                user_id=current_user.id,
                username=current_user.username,
                success=True,
                ip_address=client_ip
            )
            
            # Password changed successfully, redirect to dashboard
            return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        else:
            # Log failed password change attempt
            action_logging_service.log_password_change(
                user_id=current_user.id,
                username=current_user.username,
                success=False,
                ip_address=client_ip
            )
            
            return templates.TemplateResponse("change_password.html", {
                "request": request,
                "user": current_user,
                "error": "Current password is incorrect"
            })
            
    except Exception as e:
        logger.error(f"Password change error: {e}")
        return templates.TemplateResponse("change_password.html", {
            "request": request,
            "user": current_user,
            "error": "Password change failed. Please try again."
        })


@router.get("/logout")
async def logout(request: Request):
    """Logout and clear session"""
    try:
        session_token = request.cookies.get("session_token")
        security_service = get_security_service()
        action_logging_service = get_action_logging_service()
        
        # Get user info before invalidating session
        user = None
        if session_token:
            try:
                user = security_service.validate_session_token(session_token)
            except:
                pass
        
        if session_token:
            security_service.invalidate_session_token(session_token)
        
        # Log logout action
        if user:
            client_ip = request.client.host if request.client else None
            action_logging_service.log_user_logout(
                user_id=user.id,
                username=user.username,
                ip_address=client_ip
            )
        
        response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        response.delete_cookie("session_token")
        return response
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@router.get("/api/device/{device_id}/control")
async def device_control_api(device_id: str, action: str, current_user = Depends(require_auth)):
    """API endpoint for device control"""
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        action_service = get_action_service()
        action_logging_service = get_action_logging_service()
        
        if action == "open":
            action_id = await action_service.open_device(device_id, user_id=current_user.id)
        elif action == "close":
            action_id = await action_service.close_device(device_id, user_id=current_user.id)
        elif action == "stop":
            action_id = await action_service.stop_device(device_id, user_id=current_user.id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action"
            )
        
        # Log device action
        action_logging_service.log_device_action(
            device_id=device_id,
            action=action,
            user_id=current_user.id,
            success=True,
            parameters={"action_id": action_id}
        )
        
        return {"success": True, "action_id": action_id}
        
    except Exception as e:
        logger.error(f"Device control error: {e}")
        
        # Log failed device action
        try:
            action_logging_service = get_action_logging_service()
            action_logging_service.log_device_action(
                device_id=device_id,
                action=action,
                user_id=current_user.id,
                success=False,
                parameters={"error": str(e)}
            )
        except:
            pass  # Don't let logging errors affect the main error response
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/device/{device_id}/status")
async def device_status_api(device_id: str, current_user = Depends(require_auth)):
    """API endpoint for device status"""
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        state_service = get_state_service()
        device = state_service.get_device(device_id)
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        
        return {
            "device_id": device.id,
            "status": "online" if device.is_online else "offline",
            "state": device.state.value if hasattr(device.state, 'value') else str(device.state),
            "last_updated": device.last_updated.isoformat() if device.last_updated else None
        }
        
    except Exception as e:
        logger.error(f"Device status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/system/health")
async def system_health_api(current_user = Depends(require_auth)):
    """API endpoint for system health"""
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service_manager = get_service_manager()
        health = await service_manager.health_check()
        return health
        
    except Exception as e:
        logger.error(f"System health error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/action-logs")
async def get_action_logs_api(
    limit: int = 100,
    offset: int = 0,
    action_type: str = None,
    user_id: str = None,
    device_id: str = None,
    status: str = None,
    current_user = Depends(require_auth)
):
    """Get action logs (Admin only)"""
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Only admin users can view action logs
    if current_user.role.value != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    try:
        action_logging_service = get_action_logging_service()
        
        # Get recent actions from memory
        recent_actions = action_logging_service.get_recent_actions(limit=limit)
        
        # Get action statistics
        statistics = action_logging_service.get_action_statistics()
        
        return {
            "actions": recent_actions,
            "statistics": statistics,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(recent_actions)
            }
        }
        
    except Exception as e:
        logger.error(f"Action logs error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/api/settings/update-port")
async def update_server_port_api(request: Request, current_user = Depends(require_admin)):
    """Update server port configuration (Admin only)"""
    try:
        data = await request.json()
        new_port = data.get("port")
        
        if not new_port:
            return {"success": False, "error": "Port is required"}
        
        # Validate port range
        try:
            port_int = int(new_port)
            if port_int < 1024 or port_int > 65535:
                return {"success": False, "error": "Port must be between 1024 and 65535"}
        except ValueError:
            return {"success": False, "error": "Port must be a valid number"}
        
        # Import here to avoid circular imports
        import json
        import os
        
        # Get the config file path
        config_path = "src/config/app_config.json"
        
        # Read current config
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error reading config file: {e}")
            return {"success": False, "error": "Failed to read configuration file"}
        
        # Update port in config
        old_port = config.get("application", {}).get("port", 8080)
        config["application"]["port"] = port_int
        
        # Write updated config
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing config file: {e}")
            return {"success": False, "error": "Failed to write configuration file"}
        
        # Log the configuration change
        action_logging_service = get_action_logging_service()
        action_logging_service.log_config_change(
            config_type="application",
            user_id=current_user.id,
            success=True,
            parameters={
                "setting": "port",
                "old_value": old_port,
                "new_value": port_int
            }
        )
        
        logger.info(f"Server port updated from {old_port} to {port_int} by user {current_user.username}")
        
        return {
            "success": True, 
            "message": f"Port updated from {old_port} to {port_int}",
            "old_port": old_port,
            "new_port": port_int
        }
        
    except Exception as e:
        logger.error(f"Error updating server port: {e}")
        
        # Log failed configuration change
        try:
            action_logging_service = get_action_logging_service()
            action_logging_service.log_config_change(
                config_type="application",
                user_id=current_user.id,
                success=False,
                parameters={"setting": "port", "error": str(e)}
            )
        except:
            pass
        
        return {"success": False, "error": "Failed to update server port"}


async def _get_filtered_service_health(service_manager):
    """Get health status for only the required services: Database, Hotspot, WiFi, LAN"""
    try:
        # Get full system health including threaded services
        full_health = await service_manager.health_check()
        
        # Create filtered service health
        filtered_health = {
            "overall": "healthy",
            "timestamp": full_health.get("timestamp", ""),
            "services": {}
        }
        
        # Get threaded services health
        threaded_services = full_health.get("threaded_services", {})
        
        # Database service
        if "database" in threaded_services:
            filtered_health["services"]["database"] = threaded_services["database"]
        else:
            filtered_health["services"]["database"] = {
                "status": "unknown",
                "details": {"message": "Database service not found"}
            }
        
        # Hotspot service
        if "hotspot" in threaded_services:
            filtered_health["services"]["hotspot"] = threaded_services["hotspot"]
        else:
            filtered_health["services"]["hotspot"] = {
                "status": "unknown",
                "details": {"message": "Hotspot service not found"}
            }
        
        # WiFi service
        if "wifi" in threaded_services:
            filtered_health["services"]["wifi"] = threaded_services["wifi"]
        else:
            filtered_health["services"]["wifi"] = {
                "status": "unknown",
                "details": {"message": "WiFi service not found"}
            }
        
        # LAN service
        if "lan" in threaded_services:
            filtered_health["services"]["lan"] = threaded_services["lan"]
        else:
            filtered_health["services"]["lan"] = {
                "status": "unknown",
                "details": {"message": "LAN service not found"}
            }
        
        # Determine overall health
        service_statuses = [service["status"] for service in filtered_health["services"].values()]
        if "error" in service_statuses:
            filtered_health["overall"] = "unhealthy"
        elif "unknown" in service_statuses:
            filtered_health["overall"] = "warning"
        
        return filtered_health
        
    except Exception as e:
        logger.error(f"Error getting filtered service health: {e}")
        return {
            "overall": "error",
            "timestamp": "",
            "services": {
                "database": {"status": "error", "details": {"error": str(e)}},
                "hotspot": {"status": "error", "details": {"error": str(e)}},
                "wifi": {"status": "error", "details": {"error": str(e)}},
                "lan": {"status": "error", "details": {"error": str(e)}}
            }
        }


# Threaded Services Management API Endpoints

@router.get("/api/services/threaded/status")
async def get_threaded_services_status(current_user = Depends(require_auth)):
    """Get status of all threaded services"""
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        from src.webapp.services.global_status_registry import get_all_service_status
        services_status = get_all_service_status()
        return {"success": True, "services": services_status}
        
    except Exception as e:
        logger.error(f"Error getting threaded services status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get services status: {str(e)}"
        )


@router.get("/api/services/threaded/{service_name}/status")
async def get_threaded_service_status(service_name: str, current_user = Depends(require_auth)):
    """Get status of a specific threaded service"""
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        from src.webapp.services.global_status_registry import get_service_status
        service_status = get_service_status(service_name)
        
        if not service_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service '{service_name}' not found"
            )
        
        return {"success": True, "service": service_status}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting service status for {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service status: {str(e)}"
        )


@router.post("/api/services/threaded/{service_name}/start")
async def start_threaded_service(service_name: str, current_user = Depends(require_admin)):
    """Start a specific threaded service"""
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        from src.webapp.services.global_status_registry import get_global_status_registry
        registry = get_global_status_registry()
        
        success = registry.start_service(service_name)
        
        if success:
            return {"success": True, "message": f"Service '{service_name}' started successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to start service '{service_name}'"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting service {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start service: {str(e)}"
        )


@router.post("/api/services/threaded/{service_name}/stop")
async def stop_threaded_service(service_name: str, current_user = Depends(require_admin)):
    """Stop a specific threaded service"""
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        from src.webapp.services.global_status_registry import get_global_status_registry
        registry = get_global_status_registry()
        
        success = registry.stop_service(service_name)
        
        if success:
            return {"success": True, "message": f"Service '{service_name}' stopped successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to stop service '{service_name}'"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping service {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop service: {str(e)}"
        )


@router.post("/api/services/threaded/{service_name}/restart")
async def restart_threaded_service(service_name: str, current_user = Depends(require_admin)):
    """Restart a specific threaded service"""
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        from src.webapp.services.global_status_registry import get_global_status_registry
        registry = get_global_status_registry()
        
        success = registry.restart_service(service_name)
        
        if success:
            return {"success": True, "message": f"Service '{service_name}' restarted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to restart service '{service_name}'"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restarting service {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart service: {str(e)}"
        )


@router.get("/api/services/threaded/overall-health")
async def get_overall_health(current_user = Depends(require_auth)):
    """Get overall system health from threaded services"""
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        from src.webapp.services.global_status_registry import get_overall_health
        overall_health = get_overall_health()
        return {"success": True, "health": overall_health}
        
    except Exception as e:
        logger.error(f"Error getting overall health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get overall health: {str(e)}"
        )


@router.get("/api/services/status")
async def get_services_status(current_user = Depends(require_auth)):
    """Get simplified service status for dashboard JavaScript"""
    # Handle redirect response
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        from datetime import datetime
        network_checker = get_network_status_checker()
        network_status = await network_checker.get_all_status()
        
        # Transform to format expected by dashboard JavaScript
        wifi_data = network_status.get("wifi", {})
        lan_data = network_status.get("lan", {})
        hotspot_data = network_status.get("hotspot", {})
        
        services_status = {
            "wifi": {
                "status": "running" if wifi_data.get("connected") else "stopped",
                "last_seen": datetime.now().isoformat(),
                "details": f"Connected to {wifi_data.get('ssid', 'Unknown')}" if wifi_data.get("connected") else "No WiFi connection"
            },
            "lan": {
                "status": "running" if lan_data.get("connected") else "stopped", 
                "last_seen": datetime.now().isoformat(),
                "details": f"IP: {lan_data.get('ip_address', 'Not assigned')}" if lan_data.get("connected") else "No LAN connection"
            },
            "hotspot": {
                "status": "running" if hotspot_data.get("active") else "stopped",
                "last_seen": datetime.now().isoformat(),
                "details": f"SSID: {hotspot_data.get('ssid', 'Not configured')}" if hotspot_data.get("active") else "Hotspot is disabled"
            }
        }
        
        # Remove complex log parsing - simplified version uses direct network status
        overall_status = "healthy" if any(s["status"] == "running" for s in services_status.values()) else "warning"
        
        return {
            "success": True,
            "services": services_status,
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status
        }
        
    except Exception as e:
        logger.error(f"Simplified services status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# End of routes.py - simplified version
