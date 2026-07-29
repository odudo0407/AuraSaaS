"""Database engine & session factory for AuraSaaS — SQLite (dev) and PostgreSQL (prod)."""

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import get_settings

settings = get_settings()
SQLALCHEMY_DATABASE_URL = settings.database_url

_is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_demo_schema():
    """Create all tables if missing; apply SQLite-specific compatibility patches."""

    from app.models.models import TenantKnowledgeDocument

    Base.metadata.create_all(bind=engine, tables=[TenantKnowledgeDocument.__table__])

    if not _is_sqlite:
        return

    with engine.begin() as conn:
        user_columns = {row[1] for row in conn.execute(text("PRAGMA table_info(users)")).fetchall()}
        if user_columns and "avatar_url" not in user_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500) DEFAULT ''"))

        trace_columns = {row[1] for row in conn.execute(text("PRAGMA table_info(agent_traces)")).fetchall()}
        if trace_columns and "graph_state" not in trace_columns:
            conn.execute(text("ALTER TABLE agent_traces ADD COLUMN graph_state TEXT"))

        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_metrics_store_date ON business_metrics_daily(store_id, date)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_sku_store_date ON sku_performance(store_id, date)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_external_store_date ON external_factors(store_id, date)"
        ))


def get_db():
    """FastAPI dependency — yields a DB session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
