"""AuraSaaS FastAPI application."""

import logging
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.observability import RequestContextMiddleware
from app.core.rate_limit import rate_limit_middleware
from app.core.response import UTF8JSONResponse, api_response
from app.database import SessionLocal
from app.models.models import Store

load_dotenv()
settings = get_settings()
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        encoding=settings.text_encoding,
    )

logger = logging.getLogger(__name__)

app = FastAPI(
    default_response_class=UTF8JSONResponse,
    title=settings.app_name,
    description=(
        "Open-source AI business intelligence agent platform with BI dashboards, "
        "LangGraph orchestration, RAG playbooks, HITL approval, and trace replay."
    ),
    version="0.2.0",
)


app.add_middleware(RequestContextMiddleware)

cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if settings.environment.lower() in {"local", "development", "dev", "test"}:
    cors_origins = cors_origins or ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(rate_limit_middleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return consistent errors without leaking internals to the browser."""

    trace_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    return UTF8JSONResponse(
        status_code=500,
        content=api_response(
            data={"path": request.url.path},
            message="Internal Server Error",
            code=-1,
            trace_id=trace_id,
        ),
        headers={"X-Request-ID": trace_id},
    )


UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


from app.api.admin import router as admin_router
from app.api.agent import router as agent_router
from app.api.agent_import import router as agent_import_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.finance import router as finance_router
from app.api.import_data import router as import_router
from app.api.rag import router as rag_router
from app.api.sku import router as sku_router
from app.api.staff import router as staff_router
from app.api.skills import router as skills_router
from app.api.system import router as system_router
from app.api.tasks import router as tasks_router
from app.api.tenant_knowledge import router as tenant_knowledge_router
from app.api.user import router as user_router

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(dashboard_router)
app.include_router(agent_router)
app.include_router(skills_router)
app.include_router(rag_router)
app.include_router(admin_router)
app.include_router(import_router)
app.include_router(tasks_router)
app.include_router(tenant_knowledge_router)
app.include_router(finance_router)
app.include_router(sku_router)
app.include_router(staff_router)
app.include_router(agent_import_router)
app.include_router(system_router)


def _discover_skills():
    """Auto-discover and register Skill modules from app.skills package."""
    import importlib
    import pkgutil
    import app.skills as skills_pkg

    for _, name, _ in pkgutil.iter_modules(skills_pkg.__path__, skills_pkg.__name__ + "."):
        try:
            importlib.import_module(name)
        except Exception:
            logger.exception("Failed to load skill module: %s", name)


@app.on_event("startup")
def on_startup():
    """Initialize schema compatibility, auto-discover Skills, seed demo data."""

    from app.database import ensure_demo_schema
    from scripts.generate_mock_data import init_mock_data

    # ── Auto-discover Skill modules ─────────────────────────
    _discover_skills()

    # ── Initialize MCP servers ──────────────────────────────
    try:
        from app.mcp.adapter import init_mcp_servers
        mcp_config = {"servers": settings.mcp_servers} if hasattr(settings, "mcp_servers") and settings.mcp_servers else None
        init_mcp_servers(mcp_config)
    except Exception:
        logger.exception("MCP initialization failed")

    ensure_demo_schema()

    if settings.environment.lower() not in {"local", "development", "dev", "test"} and settings.jwt_secret == "change-me-in-production":
        raise RuntimeError("JWT secret must be configured for non-local environments.")

    if not settings.seed_demo_on_startup:
        return

    should_seed = settings.force_reseed_demo
    if not should_seed:
        db = SessionLocal()
        try:
            should_seed = db.query(Store).count() == 0
        except SQLAlchemyError:
            should_seed = True
        finally:
            db.close()

    if should_seed:
        init_mock_data(reset=settings.force_reseed_demo)
    else:
        logger.info("Demo data already exists; startup seed skipped.")


@app.get("/")
def root():
    return api_response(
        data={
            "status": "running",
            "version": app.version,
            "docs": "/docs",
            "health": "/api/health",
            "system": "/api/system/status",
        },
        message="AuraSaaS API",
    )


@app.get("/api/health")
def health():
    return api_response(data={"status": "healthy", "version": app.version})
