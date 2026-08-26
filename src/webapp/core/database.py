"""
Database initialization and management
"""

import logging
from src.webapp.services import get_database_service

logger = logging.getLogger(__name__)


async def init_database():
    """Initialize the database"""
    try:
        db_service = get_database_service()
        await db_service.initialize()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
