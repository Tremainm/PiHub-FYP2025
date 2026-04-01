# backend/app/database.py
import os
import time
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

# --- Env file selection --------------------------------------------
# APP_ENV controls which .env file is loaded.
# dev     -> .env.dev      (local, SQLite or local Postgres)
# docker  -> .env.docker   (running inside Docker Compose stack)
# test    -> .env.test     (pytest)
# Defaults to dev if APP_ENV is not set.
envfile = {
    "dev":    ".env.dev",
    "docker": ".env.docker",
    "test":   ".env.test",
}.get(os.getenv("APP_ENV", "dev"), ".env.dev")

load_dotenv(envfile, override=True)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pihub.db")
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"
RETRIES = int(os.getenv("DB_RETRIES", "10"))
DELAY = float(os.getenv("DB_RETRY_DELAY", "1.5"))

# --- connect_args --------------------------------------------
# SQLite requires check_same_thread=False because FastAPI runs
# different threads per request. PostgreSQL doesn't need this
# so we only add it when the URL is a SQLite URL.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# --- Retry loop --------------------------------------------
# PostgreSQL inside Docker can take a few seconds to be ready even
# after the healthcheck passes. The retry loop keeps attempting to
# connect rather than crashing immediately on an error.
# For SQLite this is a no-op, it connects on the first attempt.
for attempt in range(RETRIES):
    try:
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,   # validates the connection before use
            echo=SQL_ECHO,
            connect_args=connect_args,
        )
        with engine.connect():    # smoke test. Fails fast if DB is unreachable
            pass
        logger.info("Database connected on attempt %d", attempt + 1)
        break
    except OperationalError:
        logger.warning("DB not ready, retrying in %.1fs (%d/%d)", DELAY, attempt + 1, RETRIES)
        time.sleep(DELAY)
else:
    # 'else' on a for loop runs only if it completed without 'break'
    # i.e. all retries exhausted, so crash loudly rather than silently fail
    raise RuntimeError(f"Could not connect to database after {RETRIES} attempts")

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # prevents lazy-load errors after commit
)

# --- Base class for models --------------------------------------------
# Using the modern DeclarativeBase (SQLAlchemy 2.x style).
# Import this in models.py: from .database import Base
class Base(DeclarativeBase):
    pass