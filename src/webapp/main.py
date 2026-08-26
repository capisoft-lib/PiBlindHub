#!/usr/bin/env python3
"""
Simplified main application entry point for PiBlindHub
Removed all background services - status is checked on-demand only
"""

import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.webapp.config.settings import get_settings
from src.webapp.core.security import setup_security_middleware
from src.webapp.web.routes import router as web_routes, set_templates
from src.webapp.utils.logger import setup_logging
from src.webapp.utils.action_logging_decorators import ActionLoggingMiddleware

# Import minimal required services
from src.webapp.services import (
    get_security_service, get_action_service,
    get_logging_service, get_action_logging_service
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Simplified application lifespan manager - no background services"""
    # Startup
    settings = get_settings()
    setup_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting simplified application without background services...")
    
    # Initialize only essential services (no threaded services)
    try:
        # Core services
        logging_service = get_logging_service()
        
        # Business services
        security_service = get_security_service()
        action_service = get_action_service()
        action_logging_service = get_action_logging_service()
        
        # Store services in app state for access in routes
        app.state.logging_service = logging_service
        app.state.security_service = security_service
        app.state.action_service = action_service
        app.state.action_logging_service = action_logging_service
        
        logger.info("Essential services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down simplified application...")
    
    # Stop only the services we started
    try:
        # Most services don't need explicit shutdown in simplified mode
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    """Create and configure simplified FastAPI application"""
    settings = get_settings()
    
    app = FastAPI(
        title="PiBlindHub (Simplified)",
        description="A lightweight management system for motorised store devices",
        version="1.0.0-simplified",
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=settings.cors_methods,
        allow_headers=["*"],
    )
    
    # Security middleware
    setup_security_middleware(app)
    
    # Action logging middleware
    app.add_middleware(ActionLoggingMiddleware)
    
    # Static files
    app.mount("/static", StaticFiles(directory="src/webapp/web/static"), name="static")
    
    # Templates
    templates = Jinja2Templates(directory="src/webapp/web/templates")
    app.state.templates = templates
    set_templates(templates)
    
    # Web routes
    app.include_router(web_routes, tags=["Web UI"])
    
    # Health check
    @app.get("/health")
    async def health_check():
        """Simplified health check endpoint"""
        return {"status": "healthy", "version": "1.0.0-simplified", "mode": "simplified"}
    
    return app


def main():
    """Main entry point"""
    settings = get_settings()
    
    uvicorn.run(
        "src.webapp.main:create_app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        factory=True
    )


if __name__ == "__main__":
    main()
