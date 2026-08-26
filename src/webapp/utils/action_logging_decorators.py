"""
Action logging decorators and middleware for automatic change tracking
"""

import time
import functools
import asyncio
from typing import Dict, Any, Optional, Callable, Union
from datetime import datetime
import logging
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from src.webapp.services.action_logging_service import (
    get_action_logging_service, ActionType
)
from src.webapp.services.action_service import ActionStatus

logger = logging.getLogger(__name__)


def log_action(
    action_type: ActionType,
    description: str = None,
    include_parameters: bool = True,
    include_result: bool = True,
    log_errors: bool = True
):
    """
    Decorator to automatically log function calls as actions
    
    Args:
        action_type: Type of action being performed
        description: Custom description (defaults to function name)
        include_parameters: Whether to include function parameters in log
        include_result: Whether to include function result in log
        log_errors: Whether to log errors as failed actions
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            action_logging_service = get_action_logging_service()
            start_time = time.time()
            
            # Extract user info from request if available
            user_id = None
            ip_address = None
            user_agent = None
            
            # Look for request object in args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request:
                # Try to get user from request state or dependencies
                if hasattr(request.state, 'user') and request.state.user:
                    user_id = request.state.user.id
                elif hasattr(request.state, 'current_user') and request.state.current_user:
                    user_id = request.state.current_user.id
                
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get("user-agent")
            
            # Prepare parameters for logging
            log_parameters = {}
            if include_parameters:
                # Filter out sensitive parameters
                sensitive_keys = {'password', 'token', 'secret', 'key', 'auth'}
                for key, value in kwargs.items():
                    if not any(sensitive in key.lower() for sensitive in sensitive_keys):
                        log_parameters[key] = str(value)[:100]  # Truncate long values
            
            # Log action start
            action_desc = description or f"{func.__name__} executed"
            action_id = action_logging_service.log_action(
                action_type=action_type,
                description=action_desc,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                parameters=log_parameters,
                status=ActionStatus.IN_PROGRESS
            )
            
            try:
                # Execute the function
                result = await func(*args, **kwargs)
                
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log successful completion
                log_result = {}
                if include_result and result is not None:
                    if isinstance(result, dict):
                        log_result = {k: str(v)[:100] for k, v in result.items() if k not in sensitive_keys}
                    else:
                        log_result = {"result": str(result)[:100]}
                
                action_logging_service.log_action(
                    action_type=action_type,
                    description=f"{action_desc} - completed successfully",
                    user_id=user_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    parameters=log_parameters,
                    result=log_result,
                    status=ActionStatus.SUCCESS,
                    duration_ms=duration_ms
                )
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)
                
                if log_errors:
                    # Log failed action
                    action_logging_service.log_action(
                        action_type=action_type,
                        description=f"{action_desc} - failed: {str(e)}",
                        user_id=user_id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        parameters=log_parameters,
                        status=ActionStatus.FAILED,
                        error_message=str(e),
                        duration_ms=duration_ms
                    )
                
                # Re-raise the exception
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            action_logging_service = get_action_logging_service()
            start_time = time.time()
            
            # Extract user info from request if available
            user_id = None
            ip_address = None
            user_agent = None
            
            # Look for request object in args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request:
                # Try to get user from request state or dependencies
                if hasattr(request.state, 'user') and request.state.user:
                    user_id = request.state.user.id
                elif hasattr(request.state, 'current_user') and request.state.current_user:
                    user_id = request.state.current_user.id
                
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get("user-agent")
            
            # Prepare parameters for logging
            log_parameters = {}
            if include_parameters:
                # Filter out sensitive parameters
                sensitive_keys = {'password', 'token', 'secret', 'key', 'auth'}
                for key, value in kwargs.items():
                    if not any(sensitive in key.lower() for sensitive in sensitive_keys):
                        log_parameters[key] = str(value)[:100]  # Truncate long values
            
            # Log action start
            action_desc = description or f"{func.__name__} executed"
            action_id = action_logging_service.log_action(
                action_type=action_type,
                description=action_desc,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                parameters=log_parameters,
                status=ActionStatus.IN_PROGRESS
            )
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log successful completion
                log_result = {}
                if include_result and result is not None:
                    if isinstance(result, dict):
                        log_result = {k: str(v)[:100] for k, v in result.items() if k not in sensitive_keys}
                    else:
                        log_result = {"result": str(result)[:100]}
                
                action_logging_service.log_action(
                    action_type=action_type,
                    description=f"{action_desc} - completed successfully",
                    user_id=user_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    parameters=log_parameters,
                    result=log_result,
                    status=ActionStatus.SUCCESS,
                    duration_ms=duration_ms
                )
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)
                
                if log_errors:
                    # Log failed action
                    action_logging_service.log_action(
                        action_type=action_type,
                        description=f"{action_desc} - failed: {str(e)}",
                        user_id=user_id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        parameters=log_parameters,
                        status=ActionStatus.FAILED,
                        error_message=str(e),
                        duration_ms=duration_ms
                    )
                
                # Re-raise the exception
                raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class ActionLoggingMiddleware:
    """FastAPI middleware for automatic API action logging"""
    
    def __init__(self, app):
        self.app = app
        self.action_logging_service = get_action_logging_service()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        start_time = time.time()
        
        # Extract request information
        method = request.method
        url = str(request.url)
        path = request.url.path
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Determine action type based on path and method
        action_type = self._determine_action_type(path, method)
        
        # Get user info if available
        user_id = None
        if hasattr(request.state, 'user') and request.state.user:
            user_id = request.state.user.id
        elif hasattr(request.state, 'current_user') and request.state.current_user:
            user_id = request.state.current_user.id
        
        # Prepare parameters
        parameters = {
            "method": method,
            "path": path,
            "query_params": dict(request.query_params)
        }
        
        # For POST/PUT requests, try to get body (but be careful with sensitive data)
        if method in ["POST", "PUT", "PATCH"]:
            try:
                # Only log non-sensitive endpoints
                sensitive_paths = ["/login", "/change-password", "/api/admin/change-password"]
                if not any(sensitive in path for sensitive in sensitive_paths):
                    body = await request.body()
                    if body:
                        # Try to parse as JSON, but limit size
                        if len(body) < 1000:
                            try:
                                import json
                                body_data = json.loads(body.decode())
                                # Filter sensitive fields
                                filtered_body = {k: v for k, v in body_data.items() 
                                               if not any(sensitive in k.lower() for sensitive in 
                                                        ['password', 'token', 'secret', 'key', 'auth'])}
                                parameters["body"] = filtered_body
                            except:
                                parameters["body_size"] = len(body)
            except:
                pass
        
        # Log action start
        action_id = self.action_logging_service.log_action(
            action_type=action_type,
            description=f"API {method} {path}",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            parameters=parameters,
            status=ActionStatus.IN_PROGRESS
        )
        
        # Process request
        response_data = None
        status_code = None
        error_message = None
        
        async def send_wrapper(message):
            nonlocal response_data, status_code
            
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                if response_data is None:
                    response_data = message.get("body", b"").decode()[:500]  # Limit response size
            
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Determine if request was successful
            success = status_code and 200 <= status_code < 400
            status = ActionStatus.SUCCESS if success else ActionStatus.FAILED
            
            # Log completion
            result = {
                "status_code": status_code,
                "duration_ms": duration_ms
            }
            
            if response_data and len(response_data) < 200:
                result["response_preview"] = response_data
            
            self.action_logging_service.log_action(
                action_type=action_type,
                description=f"API {method} {path} - {status_code}",
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                parameters=parameters,
                result=result,
                status=status,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)
            
            # Log error
            self.action_logging_service.log_action(
                action_type=action_type,
                description=f"API {method} {path} - error: {error_message}",
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                parameters=parameters,
                status=ActionStatus.FAILED,
                error_message=error_message,
                duration_ms=duration_ms
            )
            
            # Re-raise the exception
            raise
    
    def _determine_action_type(self, path: str, method: str) -> ActionType:
        """Determine action type based on path and method"""
        # Authentication actions
        if "/login" in path:
            return ActionType.USER_LOGIN
        elif "/logout" in path:
            return ActionType.USER_LOGOUT
        elif "/change-password" in path:
            return ActionType.PASSWORD_CHANGE
        
        # Device actions
        elif "/device/" in path and "/control" in path:
            return ActionType.DEVICE_OPEN  # Will be refined based on action parameter
        elif "/device/" in path and "/status" in path:
            return ActionType.DEVICE_STATUS_CHANGE
        
        # Network configuration
        elif "/network-config" in path:
            if method in ["POST", "PUT", "PATCH"]:
                return ActionType.NETWORK_CONFIG_UPDATE
            else:
                return ActionType.API_CALL
        elif "/hotspot" in path:
            if "start" in path:
                return ActionType.HOTSPOT_START
            elif "stop" in path:
                return ActionType.HOTSPOT_STOP
            else:
                return ActionType.API_CALL
        
        # System actions
        elif "/settings" in path:
            return ActionType.SYSTEM_CONFIG_UPDATE
        elif "/admin" in path:
            return ActionType.SYSTEM_CONFIG_UPDATE
        
        # Default to API call
        else:
            return ActionType.API_CALL


# Convenience decorators for common action types
def log_user_action(description: str = None):
    """Decorator for user-related actions"""
    return log_action(ActionType.USER_LOGIN, description)

def log_device_action(description: str = None):
    """Decorator for device-related actions"""
    return log_action(ActionType.DEVICE_OPEN, description)

def log_config_action(description: str = None):
    """Decorator for configuration-related actions"""
    return log_action(ActionType.SYSTEM_CONFIG_UPDATE, description)

def log_security_action(description: str = None):
    """Decorator for security-related actions"""
    return log_action(ActionType.PASSWORD_CHANGE, description)
