"""
Application settings and configuration management
"""

import json
import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = Field(default="PiBlindHub", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8080, env="PORT")
    workers: int = Field(default=1, env="WORKERS")
    
    # Database
    database_url: str = Field(default="sqlite:///data/store_manager.db", env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Security
    jwt_secret_key: str = Field(default="your-secret-key-change-in-production", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=60, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Default admin credentials
    default_admin_username: str = Field(default="admin", env="DEFAULT_ADMIN_USERNAME")
    default_admin_password: str = Field(default="admin", env="DEFAULT_ADMIN_PASSWORD")
    
    # MQTT
    mqtt_broker_host: str = Field(default="localhost", env="MQTT_BROKER_HOST")
    mqtt_broker_port: int = Field(default=1883, env="MQTT_BROKER_PORT")
    mqtt_username: Optional[str] = Field(default=None, env="MQTT_USERNAME")
    mqtt_password: Optional[str] = Field(default=None, env="MQTT_PASSWORD")
    mqtt_client_id: str = Field(default="store_manager", env="MQTT_CLIENT_ID")
    mqtt_keepalive: int = Field(default=60, env="MQTT_KEEPALIVE")
    mqtt_ssl_enabled: bool = Field(default=False, env="MQTT_SSL_ENABLED")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/app.log", env="LOG_FILE")
    log_max_size: str = Field(default="10MB", env="LOG_MAX_SIZE")
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    # Device
    device_default_id: str = Field(default="store_001", env="DEVICE_DEFAULT_ID")
    device_timeout: int = Field(default=30, env="DEVICE_TIMEOUT")
    device_retry_attempts: int = Field(default=3, env="DEVICE_RETRY_ATTEMPTS")
    
    # API
    api_rate_limit_requests_per_minute: int = Field(default=60, env="API_RATE_LIMIT_REQUESTS_PER_MINUTE")
    api_rate_limit_burst_size: int = Field(default=10, env="API_RATE_LIMIT_BURST_SIZE")
    
    # CORS
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    cors_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE"], env="CORS_METHODS")
    
    # Session
    session_timeout: int = Field(default=3600, env="SESSION_TIMEOUT")
    max_login_attempts: int = Field(default=5, env="MAX_LOGIN_ATTEMPTS")
    lockout_duration: int = Field(default=300, env="LOCKOUT_DURATION")
    
    # Hotspot
    hotspot_enabled: bool = Field(default=True, env="HOTSPOT_ENABLED")
    hotspot_default_port: int = Field(default=15001, env="HOTSPOT_DEFAULT_PORT")
    hotspot_password: str = Field(default="MSM123456", env="HOTSPOT_PASSWORD")
    hotspot_channel: int = Field(default=7, env="HOTSPOT_CHANNEL")
    hotspot_dhcp_range_start: int = Field(default=2, env="HOTSPOT_DHCP_RANGE_START")
    hotspot_dhcp_range_end: int = Field(default=254, env="HOTSPOT_DHCP_RANGE_END")
    hotspot_auto_start_on_no_wifi: bool = Field(default=True, env="HOTSPOT_AUTO_START_ON_NO_WIFI")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class MQTTSettings:
    """MQTT-specific settings loaded from JSON config"""
    
    def __init__(self, config_path: str = "src/config/mqtt_config.json"):
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load MQTT configuration from JSON file"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}
    
    @property
    def broker(self) -> dict:
        return self._config.get("broker", {})
    
    @property
    def topics(self) -> dict:
        return self._config.get("topics", {})
    
    @property
    def qos(self) -> dict:
        return self._config.get("qos", {})
    
    @property
    def retain(self) -> dict:
        return self._config.get("retain", {})
    
    @property
    def ssl(self) -> dict:
        return self._config.get("ssl", {})


class SecuritySettings:
    """Security-specific settings loaded from JSON config"""
    
    def __init__(self, config_path: str = "src/config/security_config.json"):
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load security configuration from JSON file"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}
    
    @property
    def authentication(self) -> dict:
        return self._config.get("authentication", {})
    
    @property
    def password_policy(self) -> dict:
        return self._config.get("password_policy", {})
    
    @property
    def api_keys(self) -> dict:
        return self._config.get("api_keys", {})
    
    @property
    def encryption(self) -> dict:
        return self._config.get("encryption", {})
    
    @property
    def rate_limiting(self) -> dict:
        return self._config.get("rate_limiting", {})


# Global settings instance
_settings: Optional[Settings] = None
_mqtt_settings: Optional[MQTTSettings] = None
_security_settings: Optional[SecuritySettings] = None


def get_settings() -> Settings:
    """Get application settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_mqtt_settings() -> MQTTSettings:
    """Get MQTT settings singleton"""
    global _mqtt_settings
    if _mqtt_settings is None:
        _mqtt_settings = MQTTSettings()
    return _mqtt_settings


def get_security_settings() -> SecuritySettings:
    """Get security settings singleton"""
    global _security_settings
    if _security_settings is None:
        _security_settings = SecuritySettings()
    return _security_settings


def reload_settings():
    """Reload all settings (useful for testing)"""
    global _settings, _mqtt_settings, _security_settings
    _settings = None
    _mqtt_settings = None
    _security_settings = None
