# Local development

## Prereqs
- Docker + Docker Compose (v2)
- `uv` installed

## Start Temporal + UI
1. Start infra:
   - `docker compose up -d`
2. Open Temporal UI:
   - http://localhost:8233

Ports:
- Temporal gRPC: `localhost:7233`
- Temporal UI: `localhost:8233`

## Reset local state (destructive)
- `docker compose down -v`

## Next: run worker + client
Once milestone 2 is implemented, the intended loop is:
- `uv run python -m apps.worker`
- `uv run python -m apps.client ...`

