# Contributing to AuraSaaS

Thanks for helping improve AuraSaaS, an open-source AI business intelligence agent platform.

## Development Setup

1. Copy environment variables:
   ```bash
   cp .env.example .env
   ```
2. Start backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   python -m app.scripts.generate_mock_data
   python -m app.scripts.ingest_knowledge
   uvicorn app.main:app --reload --port 8000
   ```
3. Start frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Contribution Ideas

- Add a new SOP document under `docs/knowledge/`.
- Add a dashboard chart or API endpoint.
- Add a LangChain-style Agent Tool.
- Improve Agent Trace / Replay visualization.
- Add a new demo prompt or example scenario.

## Code Style

- Match surrounding code style and naming.
- Keep demo defaults runnable without a live LLM key.
- Preserve existing frontend API compatibility when adding new endpoints.
- Prefer small, focused pull requests.
