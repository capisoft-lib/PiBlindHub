"""
Security service for authentication, authorization, and security management
"""

import hashlib
import secrets
import jwt
import bcrypt
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from enum import Enum
import logging
from dataclasses import dataclass
from pathlib import Path
from src.webapp.config.settings import get_settings, get_security_settings

logger = logging.getLogger(__name__)


class UserRole(Enum):
    """User roles for authorization"""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    GUEST = "guest"


class Permission(Enum):
    """System permissions"""
    # Device permissions
    DEVICE_OPEN = "device:open"
    DEVICE_CLOSE = "device:close"
    DEVICE_STOP = "device:stop"
    DEVICE_STATUS = "device:status"
    
    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # System management
    SYSTEM_CONFIG = "system:config"
    SYSTEM_LOGS = "system:logs"
    SYSTEM_BACKUP = "system:backup"
    
    # API access
    API_READ = "api:read"
    API_WRITE = "api:write"


@dataclass
class User:
    """User data model"""
    id: str
    username: str
    email: str
    role: UserRole
    is_active: bool = True
    created_at: datetime = None
    last_login: datetime = None
    failed_login_attempts: int = 0
    locked_until: datetime = None
    password_hash: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class Session:
    """User session data model"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    is_active: bool = True
    ip_address: str = None
    user_agent: str = None


class SecurityService:
    """Security service for authentication and authorization"""
    
    def __init__(self):
        self.settings = get_settings()
        self.security_settings = get_security_settings()
        self._role_permissions = self._initialize_role_permissions()
        self._active_sessions: Dict[str, Session] = {}
        self._login_attempts: Dict[str, List[datetime]] = {}
        self._security_config_path = Path("src/config/security_config.json")
        self._admin_password_hash = self._load_admin_password_hash()
        
    def _initialize_role_permissions(self) -> Dict[UserRole, List[Permission]]:
        """Initialize role-based permissions"""
        return {
            UserRole.ADMIN: list(Permission),  # Admin has all permissions
            UserRole.OPERATOR: [
                Permission.DEVICE_OPEN,
                Permission.DEVICE_CLOSE,
                Permission.DEVICE_STOP,
                Permission.DEVICE_STATUS,
                Permission.USER_READ,
                Permission.API_READ,
                Permission.API_WRITE,
                Permission.SYSTEM_LOGS
            ],
            UserRole.VIEWER: [
                Permission.DEVICE_STATUS,
                Permission.USER_READ,
                Permission.API_READ,
                Permission.SYSTEM_LOGS
            ],
            UserRole.GUEST: [
                Permission.DEVICE_STATUS,
                Permission.API_READ
            ]
        }
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def generate_jwt_token(self, user: User, token_type: str = "access") -> str:
        """Generate JWT token for user"""
        now = datetime.utcnow()
        
        if token_type == "access":
            expires_delta = timedelta(minutes=self.settings.jwt_access_token_expire_minutes)
        else:  # refresh token
            expires_delta = timedelta(days=self.settings.jwt_refresh_token_expire_days)
        
        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role.value,
            "iat": now,
            "exp": now + expires_delta,
            "type": token_type
        }
        
        token = jwt.encode(
            payload,
            self.settings.jwt_secret_key,
            algorithm=self.settings.jwt_algorithm
        )
        
        return token
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            return None
    
    def create_session(self, user: User, ip_address: str = None, user_agent: str = None) -> Session:
        """Create a new user session"""
        session_id = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=self.settings.session_timeout)
        
        session = Session(
            session_id=session_id,
            user_id=user.id,
            created_at=now,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self._active_sessions[session_id] = session
        logger.info(f"Created session {session_id} for user {user.username}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        session = self._active_sessions.get(session_id)
        
        if session and session.is_active:
            if datetime.utcnow() < session.expires_at:
                return session
            else:
                # Session expired
                self.invalidate_session(session_id)
        
        return None
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session"""
        if session_id in self._active_sessions:
            self._active_sessions[session_id].is_active = False
            del self._active_sessions[session_id]
            logger.info(f"Invalidated session {session_id}")
            return True
        return False
    
    def invalidate_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user"""
        count = 0
        sessions_to_remove = []
        
        for session_id, session in self._active_sessions.items():
            if session.user_id == user_id:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            self.invalidate_session(session_id)
            count += 1
        
        logger.info(f"Invalidated {count} sessions for user {user_id}")
        return count
    
    def check_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has a specific permission"""
        user_permissions = self._role_permissions.get(user.role, [])
        return permission in user_permissions
    
    def check_user_permissions(self, user: User, permissions: List[Permission]) -> Dict[Permission, bool]:
        """Check multiple permissions for a user"""
        user_permissions = self._role_permissions.get(user.role, [])
        return {perm: perm in user_permissions for perm in permissions}
    
    def is_user_locked(self, username: str) -> bool:
        """Check if user account is locked due to failed login attempts"""
        attempts = self._login_attempts.get(username, [])
        
        if len(attempts) >= self.settings.max_login_attempts:
            # Check if lockout period has passed
            latest_attempt = max(attempts)
            lockout_until = latest_attempt + timedelta(seconds=self.settings.lockout_duration)
            
            if datetime.utcnow() < lockout_until:
                return True
            else:
                # Lockout period has passed, clear attempts
                self._login_attempts[username] = []
        
        return False
    
    def record_failed_login(self, username: str) -> None:
        """Record a failed login attempt"""
        now = datetime.utcnow()
        
        if username not in self._login_attempts:
            self._login_attempts[username] = []
        
        self._login_attempts[username].append(now)
        
        # Keep only recent attempts (within lockout duration)
        cutoff = now - timedelta(seconds=self.settings.lockout_duration)
        self._login_attempts[username] = [
            attempt for attempt in self._login_attempts[username]
            if attempt > cutoff
        ]
        
        logger.warning(f"Failed login attempt for user {username}")
    
    def clear_failed_logins(self, username: str) -> None:
        """Clear failed login attempts for a user"""
        if username in self._login_attempts:
            del self._login_attempts[username]
            logger.info(f"Cleared failed login attempts for user {username}")
    
    def generate_api_key(self, user: User, name: str = None) -> str:
        """Generate API key for a user"""
        api_key = secrets.token_urlsafe(32)
        # In a real implementation, you would store this in the database
        logger.info(f"Generated API key for user {user.username}")
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[User]:
        """Validate API key and return associated user"""
        # In a real implementation, you would look this up in the database
        # For now, return None (not implemented)
        return None
    
    def create_default_admin_user(self) -> User:
        """Create default admin user if it doesn't exist"""
        admin_user = User(
            id="admin",
            username=self.settings.default_admin_username,
            email="admin@storemanager.local",
            role=UserRole.ADMIN
        )
        
        logger.info(f"Created default admin user: {admin_user.username}")
        return admin_user
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username (placeholder - implement with database)"""
        # This is a placeholder implementation
        # In a real application, you would query the database
        
        if username == self.settings.default_admin_username:
            return self.create_default_admin_user()
        
        return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        if self.is_user_locked(username):
            logger.warning(f"Authentication failed for locked user: {username}")
            return None
        
        user = self.get_user_by_username(username)
        if not user or not user.is_active:
            self.record_failed_login(username)
            return None
        
        # For admin user, check stored password hash first
        if username == self.settings.default_admin_username:
            if self._admin_password_hash:
                if self.verify_password(password, self._admin_password_hash):
                    self.clear_failed_logins(username)
                    user.last_login = datetime.utcnow()
                    return user
                else:
                    self.record_failed_login(username)
                    return None
            else:
                # Fallback to default password if no hash is stored
                if password == self.settings.default_admin_password:
                    self.clear_failed_logins(username)
                    user.last_login = datetime.utcnow()
                    return user
                else:
                    self.record_failed_login(username)
                    return None
        
        # Check if user has a stored password hash
        if hasattr(user, 'password_hash') and user.password_hash:
            if self.verify_password(password, user.password_hash):
                self.clear_failed_logins(username)
                user.last_login = datetime.utcnow()
                return user
            else:
                self.record_failed_login(username)
                return None
        
        self.record_failed_login(username)
        return None
    
    def refresh_token(self, refresh_token: str) -> Optional[str]:
        """Generate new access token from refresh token"""
        payload = self.verify_jwt_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None
        
        user = self.get_user_by_username(payload.get("username"))
        if not user or not user.is_active:
            return None
        
        return self.generate_jwt_token(user, "access")
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions"""
        return len([s for s in self._active_sessions.values() if s.is_active])
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        now = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session in self._active_sessions.items():
            if now >= session.expires_at:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.invalidate_session(session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)
    
    def change_password(self, user: User, current_password: str, new_password: str) -> bool:
        """Change user password"""
        try:
            # Verify current password
            if not self.verify_current_password(user, current_password):
                logger.warning(f"Password change failed for user {user.username}: incorrect current password")
                return False
            
            # Validate new password strength
            if not self.validate_password_strength(new_password):
                logger.warning(f"Password change failed for user {user.username}: weak password")
                return False
            
            # Hash the new password
            new_password_hash = self.hash_password(new_password)
            
            # Save the password hash to the security config file
            if not self._save_admin_password_hash(new_password_hash):
                logger.error(f"Failed to save password hash for user {user.username}")
                return False
            
            # Update the in-memory password hash
            self._admin_password_hash = new_password_hash
            user.password_hash = new_password_hash
            
            # Invalidate all existing sessions for security
            self.invalidate_user_sessions(user.id)
            
            logger.info(f"Password changed successfully for user {user.username}")
            return True
            
        except Exception as e:
            logger.error(f"Error changing password for user {user.username}: {e}")
            return False
    
    def verify_current_password(self, user: User, current_password: str) -> bool:
        """Verify the current password for a user"""
        # For the default admin user, check stored password hash first
        if user.username == self.settings.default_admin_username:
            if self._admin_password_hash:
                return self.verify_password(current_password, self._admin_password_hash)
            else:
                # Fallback to default password if no hash is stored
                return current_password == self.settings.default_admin_password
        
        # For users with stored password hashes, verify against the hash
        if hasattr(user, 'password_hash') and user.password_hash:
            return self.verify_password(current_password, user.password_hash)
        
        # Fallback to default password check
        return current_password == self.settings.default_admin_password
    
    def validate_password_strength(self, password: str) -> bool:
        """Validate password strength"""
        if len(password) < 8:
            return False
        
        # Check for uppercase, lowercase, digit, and special character
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*(),.?\":{}|<>" for c in password)
        
        return has_upper and has_lower and has_digit and has_special
    
    def _load_admin_password_hash(self) -> Optional[str]:
        """Load admin password hash from security config"""
        try:
            if self._security_config_path.exists():
                with open(self._security_config_path, 'r') as f:
                    config = json.load(f)
                    return config.get("authentication", {}).get("admin_password_hash")
        except Exception as e:
            logger.error(f"Error loading admin password hash: {e}")
        return None
    
    def _save_admin_password_hash(self, password_hash: str) -> bool:
        """Save admin password hash to security config"""
        try:
            # Load existing config
            config = {}
            if self._security_config_path.exists():
                with open(self._security_config_path, 'r') as f:
                    config = json.load(f)
            
            # Ensure authentication section exists
            if "authentication" not in config:
                config["authentication"] = {}
            
            # Update password hash
            config["authentication"]["admin_password_hash"] = password_hash
            config["authentication"]["password_changed_at"] = datetime.utcnow().isoformat()
            
            # Save config
            with open(self._security_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info("Admin password hash saved to security config")
            return True
            
        except Exception as e:
            logger.error(f"Error saving admin password hash: {e}")
            return False
    
    def create_session_token(self, user: User) -> str:
        """Create a session token for user"""
        session = self.create_session(user)
        return session.session_id
    
    def validate_session_token(self, token: str) -> Optional[User]:
        """Validate session token and return user"""
        session = self.get_session(token)
        if session:
            # Get user by user_id (which is the username for admin)
            user = self.get_user_by_username(session.user_id)
            if user:
                return user
        return None
    
    def invalidate_session_token(self, token: str) -> bool:
        """Invalidate session token"""
        return self.invalidate_session(token)
    
    def is_password_change_required(self, user: User) -> bool:
        """Check if password change is required for user"""
        # For admin user, check if using default password
        if user.username == self.settings.default_admin_username:
            # If no password hash is stored, password change is required
            return self._admin_password_hash is None
        return False


# Global security service instance
_security_service: Optional[SecurityService] = None


def get_security_service() -> SecurityService:
    """Get security service singleton"""
    global _security_service
    if _security_service is None:
        _security_service = SecurityService()
    return _security_service
