"""
Security middleware and utilities
"""

from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
import logging

logger = logging.getLogger(__name__)


def setup_security_middleware(app: FastAPI):
    """Setup security middleware for the application"""
    try:
        # Add trusted host middleware
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # In production, specify actual hosts
        )
        
        # Add HTTPS redirect middleware (only in production)
        # app.add_middleware(HTTPSRedirectMiddleware)
        
        logger.info("Security middleware configured")
        
    except Exception as e:
        logger.error(f"Failed to setup security middleware: {e}")
        raise
