"""
Database Session Management

PostgreSQL connection for metadata storage.
Uses SQLAlchemy async with connection pooling.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from voyant.core.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


_engine = None
_session_factory = None


def get_engine():
    """Get async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        # Convert postgresql:// to postgresql+asyncpg://
        db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
        _engine = create_async_engine(
            db_url,
            echo=settings.debug,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
        logger.info("Database engine created")
    return _engine


def get_session_factory():
    """Get async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session context manager."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Initialize database tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")
