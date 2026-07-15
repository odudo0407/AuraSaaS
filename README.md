# AuraSaaS

[中文版](README.zh.md)

Open-source AI-powered Business Intelligence Agent platform for multi-store operations.

AuraSaaS integrates LangGraph agent orchestration, RAG knowledge retrieval, a 5-tier tool-calling system, human-in-the-loop (HITL) approval, and full execution traceability — all exposed through a Vue 3 dashboard and FastAPI backend.

![AuraSaaS Dashboard](assets/readme/01-dashboard-overview.png)

## Features

### Agent Workflow

- **Dual-mode execution** — a unified `/api/agent/stream` endpoint classifies user queries into **11 intent types** via LLM + keyword fallback, then auto-routes to either a LangGraph pipeline (for high-risk operations with HITL) or a ReAct agent (for fast autonomous tool-calling).
- **10-node LangGraph pipeline** — `intent_router → data_analyst → fetch_context → rag_strategist → risk_controller → human_approval` (Phase 1), followed by `copywriter → report_generator` (Phase 2, post-approval). Conditional edges skip irrelevant nodes based on intent.
- **ReAct agent loop** — think-act-observe pattern with up to 12 iterations, autonomous tool selection, and multi-turn conversation history.

![Agent Pipeline](assets/readme/02-agent-pipeline.png)

### RAG Knowledge Retrieval

- **Three-tier architecture**: public SOP documents (8 built-in markdown files), tenant-private uploads (PDF/DOCX/TXT/MD), and codebase indexing (tree-sitter AST chunking for Python, JavaScript, Java).
- **Dual-channel search**: ChromaDB vector similarity + keyword-based fallback, ensuring retrieval works even without embeddings or network access.
- **Automatic chunking**: 900-character windows with 120-character overlap for public documents; configurable for tenant documents.

### Tool Calling System

- **22 tools** across **5 privilege tiers**:

| Tier | Level | Scope | Example Tools |
|------|-------|-------|---------------|
| Read-only | 1 | Query existing data | `get_daily_summary`, `list_all_stores`, `get_store_detail` |
| Analysis | 2 | Detect & forecast | `detect_anomalies`, `forecast_metric`, `compare_periods`, `rank_stores` |
| Retrieval | 3 | Search knowledge | `search_knowledge_base`, `search_agent_memory` |
| Generation | 4 | Create content (gated) | `generate_marketing_strategy`, `generate_campaign_copy`, `evaluate_strategy_risk` |
| Write | 5 | Mutate data (gated) | `add_product`, `create_anomaly_tasks`, `save_agent_memory` |

- **Privilege enforcement**: the ReAct agent defaults to tier 3; tiers 4–5 require escalation through the LangGraph HITL path. Execution attempts above the current ceiling raise `PrivilegeEscalationError`.

### Human-in-the-Loop Approval

- **Pause–persist–resume**: when the agent generates a high-risk proposal, the LangGraph pipeline pauses at the `human_approval` node, serializes its full state into the database, and yields an `approval_required` SSE event.
- **Three decision types**: approve, reject, or request revision. Approval automatically creates a `MarketingCampaign` draft and resumes Phase 2 (copywriting → final report) via a dedicated SSE endpoint.
- **Memory persistence**: approval decisions and analysis conclusions are written to `AgentMemory` for future reasoning context.

### Execution Traceability

- Every agent run produces a structured `AgentTrace` record containing node-level events, tool call arguments, per-node duration, and the final answer.
- **SSE streaming**: the frontend receives real-time node-status events and renders them in a pipeline timeline (`AgentPipeline` component).
- **Trace replay**: saved traces are replayable by `trace_id`, displaying the original step-by-step execution.
- **Performance metrics**: token usage, cumulative cost (with budget guard), and RAG hit rate are logged per run.

### BI Dashboard

- KPI overview cards with period-over-period change indicators.
- Revenue trend chart (ECharts) with configurable date ranges.
- Top-SKU heatmap, store ranking table, anomaly alert list.
- Management pages: Stores, Products (SKU), Staff, Marketing Campaigns, Finance, Reports.

### Platform

- **Auth**: JWT with access/refresh token rotation and automatic 401 interception.
- **Rate limiting**: per-endpoint request throttling.
- **Cost guard**: cumulative LLM token budget (`AGENT_BUDGET_YUAN`); requests are intercepted before exceeding the limit.
- **Consistent API**: all responses follow `{code, data, message}` envelope; SSE uses typed event streams.

![AI Analysis Page](assets/readme/03-ai-analysis-page.png)

## Architecture

```text
User Query
    │
    ▼
┌──────────────────────────────────────────┐
│   POST /api/agent/stream  (auto-route)   │
│                                          │
│   Keyword intent classification          │
│        │                      │          │
│    high-risk                quick        │
│        ▼                      ▼          │
│   LangGraph Pipeline     ReAct Agent     │
│   (10 nodes + HITL)    (think-act loop)  │
└──────────────────────────────────────────┘

LangGraph Phase 1:
  intent_router → data_analyst → fetch_context
    → rag_strategist → risk_controller → human_approval
                                              │
                                       ┌──────┴──────┐
                                       │  PAUSE       │
                                       │  save state  │
                                       │  → AgentTrace│
                                       └──────┬──────┘
                                              │ User approves
                                              ▼
LangGraph Phase 2 (via /stream-resume):
  copywriter → report_generator → END
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Vue 3, Vite 6, Pinia, Vue Router, ECharts, UnoCSS, Marked |
| Backend | FastAPI (Python), LangGraph, SQLAlchemy 2, Pydantic v2, Alembic |
| AI / LLM | DeepSeek API (OpenAI-compatible), with demo-mode fallback |
| RAG | ChromaDB, sentence-transformers, tree-sitter (code parsing) |
| Database | SQLite (local / demo), Alembic migrations |
| Auth | JWT (python-jose + passlib), rate limiting |
| DevOps | GitHub Actions CI |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- (Optional) DeepSeek or OpenAI-compatible API key for live LLM features

### 1. Clone and configure

```bash
git clone https://github.com/Enndme-KK/AuraSaaS.git && cd AuraSaaS
cp .env.example .env
```

Edit `.env` and set `DEEPSEEK_API_KEY` to your API key. Leave it as the placeholder for demo mode — the agent will serve template-based fallback responses.

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
python -m app.scripts.ingest_knowledge    # Index SOP documents into ChromaDB
uvicorn app.main:app --reload --port 8000
```

The first startup automatically seeds demo data (4 stores, 90 days of metrics, SKUs, external factors) if the database is empty.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`, register an account, and start exploring.

> After upgrading, delete `backend/aura.db` to ensure schema migrations apply cleanly.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | `your-deepseek-api-key` | LLM API key; placeholder enables demo mode |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | LLM API base URL |
| `OPENAI_API_BASE` | `https://api.deepseek.com` | Alternative API base |
| `DATABASE_URL` | `sqlite:///./aura.db` | SQLAlchemy database URL |
| `CHROMA_DIR` | `./data/chroma` | ChromaDB persistence directory |
| `CODE_EMBEDDING_CACHE_DIR` | `./data/huggingface` | HuggingFace model cache |
| `JWT_SECRET` | `change-me-in-production` | JWT signing key |
| `ENVIRONMENT` | `local` | `local`, `development`, `test`, or production |
| `SEED_DEMO_ON_STARTUP` | `true` | Auto-seed demo data on first run |
| `FORCE_RESEED_DEMO` | `false` | Force reseed even if data exists |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated allowed origins |
| `LLM_TIMEOUT_SECONDS` | `30` | LLM request timeout |
| `LLM_MAX_RETRIES` | `2` | Max retry attempts for transient errors |
| `AGENT_BUDGET_YUAN` | `0.02` | Per-session LLM cost ceiling |

## Project Structure

```text
AuraSaaS/
├── backend/
│   ├── app/
│   │   ├── agents/              # LangGraph workflow, ReAct agent, tools
│   │   │   ├── nodes/           # data_analysis node (BI signal collection)
│   │   │   └── toolkit/         # 9 modules: bi, analytics, marketing, etc.
│   │   ├── api/                 # 14 FastAPI routers
│   │   ├── core/                # config, security, rate-limit, observability
│   │   ├── models/              # 14 SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/            # RAG, LLM client, data cleaning, agent forms
│   │   └── tests/               # pytest suites (tools, graph, privilege, API)
│   ├── alembic/                 # Database migration scripts
│   ├── data/chroma/             # ChromaDB vector store
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # AgentPipeline, ThoughtStream, StatCard, etc.
│   │   ├── composables/         # useAgentAnalysis (SSE streaming + state)
│   │   ├── views/               # 12 pages (AIAnalysis, Dashboard, Stores, …)
│   │   ├── stores/              # Pinia stores (auth, dashboard)
│   │   └── utils/               # HTTP client, SSE parser, markdown renderer
│   └── package.json
├── docs/knowledge/              # 8 built-in SOP / strategy markdown files
├── sample_imports/              # Sample CSV import data
├── docker-compose.yml
└── .env.example
```

## API Reference — Agent Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/agent/stream` | Unified entry: auto-routes to LangGraph or ReAct based on intent |
| `GET` | `/api/agent/stream-diagnose` | LangGraph SSE (direct invocation, bypasses auto-route) |
| `POST` | `/api/agent/stream-react` | ReAct Agent SSE (direct invocation) |
| `GET` | `/api/agent/stream-resume` | Resume Phase 2 after HITL approval |
| `POST` | `/api/agent/approve` | Approve / reject / revise a HITL proposal |
| `GET` | `/api/agent/approvals` | List pending and historical approval requests |
| `GET` | `/api/agent/traces` | List recent agent traces |
| `GET` | `/api/agent/traces/{trace_id}` | Trace detail with timeline steps |
| `POST` | `/api/agent/replay/{trace_id}` | Replay a saved trace |
| `DELETE` | `/api/agent/traces/{trace_id}` | Delete a single trace |
| `DELETE` | `/api/agent/traces` | Clear all traces |
| `POST` | `/api/agent/forms/preview` | Generate a fillable business-operation form |
| `POST` | `/api/agent/forms/submit` | Validate and execute a submitted agent form |

Additional routers: `/api/auth/*`, `/api/dashboard/*`, `/api/rag/*`, `/api/tenant-knowledge/*`, `/api/import/*`, `/api/sku/*`, `/api/staff/*`, `/api/finance/*`, `/api/system/*`, `/api/tasks/*`.

## Testing

```bash
# Backend — all suites
cd backend
pytest app/tests/ -v

# Run specific suites
pytest app/tests/test_tools.py -v       # 19 tests — tool execution at all privilege levels
pytest app/tests/test_graph_nodes.py -v # 26 tests — graph, routing, RAG, SSE
pytest app/tests/test_privilege.py -v   # 14 tests — 5-tier permission gating

# Frontend
cd frontend
npm run build    # type-check + production build
npm run lint
```

## FAQ

**Q: The agent shows "demo mode" — how do I enable live AI?**

Set `DEEPSEEK_API_KEY` in `.env` to a valid DeepSeek or OpenAI-compatible API key. The platform works with any OpenAI-compatible endpoint.

**Q: Why does the agent pause and ask for approval?**

Queries routed to the LangGraph pipeline (marketing plans, anomaly diagnosis, reports, data management) include a risk assessment step. If the proposal exceeds the risk threshold, it pauses for human review. Quick data queries go through the ReAct agent and do not require approval.

**Q: How do I add custom knowledge documents?**

Place markdown files in `docs/knowledge/` and re-run `python -m app.scripts.ingest_knowledge`. Or upload PDF/DOCX/TXT/MD files via the frontend RAG panel or `POST /api/rag/upload`.

**Q: The database column error on startup?**

Delete `backend/aura.db` to force a clean schema creation, or the app will auto-patch missing columns on startup via `ensure_demo_schema()`.

## Contributing

Contributions are welcome. Please open an issue to discuss proposed changes before submitting a pull request. See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines and [GOOD_FIRST_ISSUES.md](GOOD_FIRST_ISSUES.md) for beginner-friendly tasks.

## License

MIT License. See [LICENSE](LICENSE).

## Screenshots

![Reports Page](assets/readme/05-reports.png)

![Products Page](assets/readme/06-products.png)

![Stores Page](assets/readme/07-stores.png)

![Marketing Page](assets/readme/08-marketing.png)

![Finance Page](assets/readme/09-finance.png)
