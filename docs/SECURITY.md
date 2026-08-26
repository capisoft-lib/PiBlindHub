# Security Documentation

## Overview

This document outlines the security measures, requirements, and implementation details for PiBlindHub.

## Security Architecture

### Authentication & Authorization

#### User Authentication
- **Default Credentials**: System ships with default admin credentials that MUST be changed on first login
- **Password Policy**: Enforced minimum requirements for password complexity
- **Session Management**: JWT-based sessions with configurable expiration
- **Account Lockout**: Protection against brute force attacks

#### API Authentication
- **API Key System**: All API endpoints require valid API keys
- **Key Generation**: API keys generated through Web UI only
- **Key Storage**: API keys hashed and stored securely
- **Rate Limiting**: Per-key rate limiting to prevent abuse

### Data Protection

#### Encryption
- **Passwords**: Bcrypt hashing with salt
- **API Keys**: SHA-256 hashing with salt
- **Sensitive Data**: AES-256-GCM encryption for data at rest
- **Transport**: TLS/SSL for all network communications

#### Data Validation
- **Input Sanitization**: All user inputs validated and sanitized
- **SQL Injection Prevention**: Parameterized queries and ORM usage
- **XSS Protection**: Output encoding and CSP headers
- **CSRF Protection**: Token-based CSRF protection

## Security Implementation

### Password Security

#### Password Policy
```json
{
  "min_length": 8,
  "require_uppercase": true,
  "require_lowercase": true,
  "require_numbers": true,
  "require_special_chars": true,
  "max_age_days": 90
}
```

#### Password Hashing
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

### API Key Security

#### Key Generation
```python
import secrets
import hashlib

def generate_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(32)

def hash_api_key(api_key: str) -> str:
    """Hash API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()
```

#### Key Validation
```python
def validate_api_key(api_key: str, hashed_key: str) -> bool:
    """Validate API key against stored hash"""
    return hash_api_key(api_key) == hashed_key
```

### JWT Token Security

#### Token Generation
```python
from jose import JWTError, jwt
from datetime import datetime, timedelta

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

#### Token Validation
```python
def verify_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception
```

## Security Headers

### HTTP Security Headers
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

## Input Validation

### Pydantic Models
```python
from pydantic import BaseModel, validator, EmailStr
from typing import Optional
import re

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', v):
            raise ValueError('Username must be 3-20 characters, alphanumeric and underscores only')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
```

## Rate Limiting

### API Rate Limiting
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/login")
@limiter.limit("5/minute")
async def login(request: Request, user_data: UserLogin):
    # Login logic
    pass

@app.get("/api/device/status")
@limiter.limit("60/minute")
async def get_device_status(request: Request, api_key: str = Header(...)):
    # Device status logic
    pass
```

## Database Security

### SQL Injection Prevention
```python
from sqlalchemy.orm import Session
from sqlalchemy import text

# Good: Using ORM
def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

# Good: Using parameterized queries
def get_user_by_username_raw(db: Session, username: str):
    result = db.execute(text("SELECT * FROM users WHERE username = :username"), 
                       {"username": username})
    return result.fetchone()

# Bad: String concatenation (NEVER DO THIS)
def get_user_by_username_bad(db: Session, username: str):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return db.execute(text(query))
```

## MQTT Security

### Connection Security
```python
import paho.mqtt.client as mqtt
import ssl

def create_secure_mqtt_client():
    client = mqtt.Client()
    
    # SSL/TLS Configuration
    if MQTT_SSL_ENABLED:
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations(MQTT_CA_CERT)
        context.load_cert_chain(MQTT_CLIENT_CERT, MQTT_CLIENT_KEY)
        client.tls_set_context(context)
    
    # Authentication
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    return client
```

### Message Validation
```python
from pydantic import BaseModel, validator
from typing import Literal

class DeviceCommand(BaseModel):
    device_id: str
    command: Literal["open", "close", "stop"]
    timestamp: datetime
    user_id: str
    
    @validator('device_id')
    def validate_device_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]{1,50}$', v):
            raise ValueError('Invalid device ID format')
        return v
```

## Logging and Monitoring

### Security Event Logging
```python
import logging
import json
from datetime import datetime

security_logger = logging.getLogger('security')

def log_security_event(event_type: str, user_id: str, details: dict):
    """Log security-related events"""
    event = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'user_id': user_id,
        'details': details,
        'ip_address': request.client.host if request else None
    }
    security_logger.warning(json.dumps(event))

# Usage examples
log_security_event('login_failed', user_id, {'attempts': 3})
log_security_event('api_key_used', user_id, {'endpoint': '/api/device/status'})
log_security_event('password_changed', user_id, {})
```

### Audit Trail
```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
```

## Security Best Practices

### Development
1. **Never commit secrets**: Use environment variables for sensitive data
2. **Input validation**: Validate all inputs at API boundaries
3. **Error handling**: Don't expose sensitive information in error messages
4. **Dependencies**: Keep dependencies updated and scan for vulnerabilities
5. **Code review**: Security-focused code reviews for sensitive changes

### Deployment
1. **HTTPS only**: Use TLS/SSL for all communications
2. **Firewall**: Restrict network access to necessary ports only
3. **Updates**: Regular security updates for OS and dependencies
4. **Monitoring**: Continuous monitoring of security events
5. **Backups**: Secure backup procedures with encryption

### Operations
1. **Access control**: Principle of least privilege
2. **Monitoring**: Real-time monitoring of security events
3. **Incident response**: Documented procedures for security incidents
4. **Regular audits**: Periodic security assessments
5. **Training**: Security awareness training for operators

## Security Checklist

### Initial Setup
- [ ] Change default admin password
- [ ] Configure secure JWT secret
- [ ] Set up HTTPS/TLS certificates
- [ ] Configure firewall rules
- [ ] Enable security logging

### Regular Maintenance
- [ ] Update dependencies monthly
- [ ] Review access logs weekly
- [ ] Rotate API keys quarterly
- [ ] Update passwords as per policy
- [ ] Review security configurations

### Incident Response
- [ ] Document security incidents
- [ ] Implement immediate containment
- [ ] Conduct post-incident review
- [ ] Update security measures
- [ ] Notify stakeholders if required

## Compliance

### Data Protection
- **GDPR**: If handling EU data, ensure GDPR compliance
- **Data Retention**: Implement appropriate data retention policies
- **Right to Erasure**: Provide mechanisms for data deletion
- **Data Portability**: Allow data export in standard formats

### Industry Standards
- **OWASP Top 10**: Address all OWASP security risks
- **ISO 27001**: Consider ISO 27001 compliance for enterprise deployments
- **NIST Framework**: Align with NIST Cybersecurity Framework

## Security Testing

### Automated Testing
```python
import pytest
from fastapi.testclient import TestClient

def test_authentication_required():
    """Test that protected endpoints require authentication"""
    response = client.get("/api/device/status")
    assert response.status_code == 401

def test_rate_limiting():
    """Test rate limiting on login endpoint"""
    for i in range(6):
        response = client.post("/api/login", json={"username": "test", "password": "wrong"})
    assert response.status_code == 429

def test_input_validation():
    """Test input validation on user creation"""
    response = client.post("/api/users", json={"username": "a", "password": "123"})
    assert response.status_code == 422
```

### Manual Testing
1. **Penetration Testing**: Regular penetration testing
2. **Social Engineering**: Test user awareness
3. **Physical Security**: Assess physical access controls
4. **Network Security**: Test network segmentation
5. **Application Security**: Manual security testing of application features
