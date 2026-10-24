---
inclusion: always
---
# Data and safety
- When a data source is unavailable, fall back to /data/snapshots and show a "cached <timestamp>" badge.
- When data is synthetic, show a "synthetic" badge and mention it in any summary.
- Never expose real vessel identities; use anonymized IDs in the simulator.
- Numbers and zone names must be identical across English, Portuguese, and Spanish outputs.
- Never commit secrets. Keys go in .env (gitignored). Use .env.example for names only.
- Do not fabricate regulatory facts. If you do not have a source URL for a zone, mark it `synthetic: true`.
