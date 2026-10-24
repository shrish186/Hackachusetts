---
inclusion: always
---
# Structure and ownership
/backend/app/{api,engine,agent,ingest,models}   backend code
/backend/tests                                  pytest + hypothesis
/mcp/fathom_mcp                                 MCP server exposing the tools
/frontend/src/{map,captain,manager,components}  React app
/data/snapshots                                 bundled demo data (committed, small)
/config                                         risk.yaml, vessels.yaml, languages.yaml
/docs                                           pitch, KIRO_WRITEUP evidence, screenshots

## Lanes (to avoid git conflicts, only edit your own lane)
- Lane A (Data & Geo): /backend/app/ingest, /backend/app/models, /data, /config/risk.yaml, whale risk model in /backend/app/engine/risk.py
- Lane B (Backend & Agent): /backend/app/api, /backend/app/engine/routing.py, /backend/app/agent
- Lane C (Frontend): /frontend
- Lane D (Product/QA/MCP/Story): /mcp, /backend/tests, /backend/app/engine/simulator.py, /docs, README.md
If you need a change in someone else's lane, ask them or open a small PR.
