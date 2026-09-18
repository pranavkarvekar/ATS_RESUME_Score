# -*- coding: utf-8 -*-
"""
Database Engine & Session Management.

Provides async SQLAlchemy engine, session factory, and table creation.
Supports both SQLite (local dev) and PostgreSQL (production) via DATABASE_URL.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import config
from models.db_models import Base

log = logging.getLogger("ats.db")

# ─────────────────────────────────────────────
# Engine & Session Factory
# ─────────────────────────────────────────────

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_engine() -> AsyncEngine:
    """Creates or returns the singleton async engine."""
    global _engine
    if _engine is None:
        db_url = config.DATABASE_URL
        log.info("Creating database engine: %s", db_url.split("///")[0] + "///...")

        connect_args = {}
        if "sqlite" in db_url:
            connect_args["check_same_thread"] = False

        _engine = create_async_engine(
            db_url,
            echo=False,
            connect_args=connect_args,
        )
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Creates or returns the singleton session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides an async database session with automatic commit/rollback."""
    factory = _get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def create_tables() -> None:
    """Creates all database tables (idempotent)."""
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Database tables created/verified")


async def close_engine() -> None:
    """Disposes the engine (call on shutdown)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        log.info("Database engine disposed")
