# Deploying Fathom

- **API:** Render free web service from `backend/Dockerfile`. Production URL: https://hackachusetts.onrender.com
- **Frontend:** Vercel. Production URL: https://fathom-six-vert.vercel.app

## API on Render

### First-time setup

1. In Render, choose **New → Blueprint**, pick the `shrish186/Hackachusetts` repo, and accept `render.yaml`. To set it up by hand instead, choose **New → Web Service** with these settings:
   - Runtime: **Docker**
   - Dockerfile path: `./backend/Dockerfile`
   - Docker build context: `.` (the repo root, so `config/` and `data/snapshots/` are included)
   - Health check path: `/api/health`
   - Plan: Free
2. Under **Environment**, set these variables:

| Key | Value | Notes |
|---|---|---|
| `FATHOM_ALLOWED_ORIGINS` | `https://fathom-six-vert.vercel.app` | Comma-separated. Trailing slashes and spaces are removed. Add more origins such as `http://localhost:5173` if needed. |
| `FATHOM_TRUST_PROXY` | `true` | Uses Render's last `X-Forwarded-For` hop for the rate limit and turns on HSTS for HTTPS requests. |
| `FATHOM_DEMO_MODE` | `true` | Serves only the bundled snapshots, with no live network calls. |
| `ANTHROPIC_API_KEY` | *(optional, secret)* | Lets an LLM rewrite the narrative, which still goes through the citation guard. Leave it unset for the deterministic templates. Never commit it. |
| `FATHOM_ENABLE_DOCS` | *(leave unset)* | `/docs`, `/redoc` and `/openapi.json` return 404 unless this is `true`. Keep them off in production. |

3. Click **Save, rebuild, and deploy**.

### Redeploying after a push

1. Open the service in Render and choose **Manual Deploy → Deploy latest commit**. Auto-deploy from `main` also works if it is enabled.
2. Wait for the deploy to show **Live**.
3. Check the API:
   ```bash
   curl -s https://hackachusetts.onrender.com/api/health   # {"status":"ok"}, answers right away
   curl -s https://hackachusetts.onrender.com/api/ready    # 200 {"status":"ready",...} after warm-up; 503 before
   curl -si -X OPTIONS https://hackachusetts.onrender.com/api/trip/plan \
     -H "Origin: https://fathom-six-vert.vercel.app" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: content-type" | grep -i access-control-allow-origin
   ```
   The last command must print `access-control-allow-origin: https://fathom-six-vert.vercel.app`.

### Startup

On boot the app answers `/api/health` right away. A background thread then loads the snapshots, builds the grid and risk surfaces, and runs one demo plan. `/api/ready` returns 200 when that is done, which took about 0.5 s locally. The Render health check stays on `/api/health`, so a slow warm-up can never fail a deploy.

## Frontend on Vercel

1. Project root: `frontend/`. Build command: `npm run build`. Output directory: `dist`.
2. Environment variable for Production and Preview: `VITE_API_URL=https://hackachusetts.onrender.com` (no trailing slash and no `/api`; the client adds `/api/...`).
3. Redeploy after changing the variable, because Vite bakes it in at build time.

## Keep the free server warm

Render's free plan sleeps after about 15 minutes without traffic, and waking takes up to a minute. Before the judging window, set up a free monitor that pings the health endpoint every 10 minutes:

- **UptimeRobot:** create an HTTP(s) monitor for `https://hackachusetts.onrender.com/api/health` with a 10-minute interval.
- **cron-job.org:** create a job that sends `GET https://hackachusetts.onrender.com/api/health` every 10 minutes.

`/api/health` is exempt from the rate limit, so the pings never use up user quota.

## Local Docker check

```bash
docker build -f backend/Dockerfile -t fathom-backend .
docker run --rm -p 8000:8000 -e FATHOM_ALLOWED_ORIGINS=http://localhost:5173 fathom-backend
curl -s localhost:8000/api/ready
```
