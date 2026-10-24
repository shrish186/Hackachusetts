# Fathom Team Playbook (step by step)

You are 4 people. Nobody has to do a lot. The trick: **each person owns one lane, pastes the prompts below into Kiro, checks it works, and pushes.** Kiro does the typing.

Lanes (rename the people as you like):

| Lane | Owner | Owns | Main job |
|---|---|---|---|
| **A: Data & Geo** | Person 1 | `/data`, `/config`, `backend/app/ingest`, `backend/app/models`, `backend/app/engine/risk.py` | Get data, build models, whale risk |
| **B: Backend & Agent** | Person 2 | `backend/app/api`, `engine/routing.py`, `backend/app/agent` | API, router, agent |
| **C: Frontend** | Person 3 | `/frontend` | Map and screens |
| **D: Product, QA & Story** (also the **Representative** who submits) | Person 4 | `/mcp`, `backend/tests`, `engine/simulator.py`, `/docs`, README | MCP server, tests, simulator, write-up, video |

Rule of thumb: **only edit files in your lane.** That is what prevents git fights.

---

## PART 0. What the rules require (read once)

From the Hackachusetts rules, your submission needs:
1. Max 4 team members, all added on the submission.
2. Built with Kiro. "Insufficient use of Kiro" = disqualified.
3. Track: Climate Tech & Clean Energy.
4. Text description of features.
5. Demo video **under 3 minutes**, **public** on YouTube/Vimeo/Facebook/Youku, no copyrighted music, no third-party trademarks.
6. **Public GitHub repo** with everything needed to run + instructions.
7. **`.kiro/` folder committed at the repo root.** Never put it in `.gitignore`.
8. Write-up on how you used Kiro: tools (IDE/CLI/Web/Crew), specs, hooks, steering, MCP, property-based testing, powers.
9. A working link for judges to test (free, no restrictions; if private, give login).
10. Everything in English.

Judging: **Potential Value**, **Implementation** (how well you used Kiro), **Quality & Design**. "Best Use of Kiro" is a separate prize ($1,200 value) for the top Implementation score in the top 10%. So **Kiro depth is worth real points**, not just the app.

> I only had the "Submission Requirements / Judging / Prizes" part of the rules PDF. I did not see the **eligibility section** (who can win prizes, e.g. for international students, and the AWS interview conditions) or the **deadline**. Read those in the full rules today and write the deadline at the top of this file.

---

## PART 1. Everyone: one-time setup (about 30 minutes)

1. Install **Kiro** from kiro.dev and sign in (use the account with your 2000 credits).
2. Install: **Git**, **Python 3.11+**, **Node 20+**. Optional but helpful: **uv** (`pip install uv`), because the `fetch` MCP server uses `uvx`.
3. Make sure you have a GitHub account. The repo owner (**shrish186**) must add the other 3: GitHub repo -> **Settings -> Collaborators -> Add people**. Accept the email invites.
4. Clone:
   ```bash
   git clone https://github.com/shrish186/Hackachusetts.git
   cd Hackachusetts
   ```
5. **Only after Person 4 has pushed the starter bundle (Part 2)**, run `git pull` and open the folder in Kiro (File -> Open Folder).
6. In Kiro, check you can see: the **spec** (Specs panel), **steering** files, **hooks**, and **MCP servers** (`fetch` should show connected; `fathom` is disabled for now, that is intended).
7. Take screenshot **#01 and #04** from `docs/kiro-evidence/README.md` right now.

---

## PART 2. Person 4 (Representative): push the starter bundle FIRST (10 minutes)

The bundle is the zip I made: it has the spec, steering, hooks, MCP config, README, `.gitignore`, and write-up skeleton.

1. Unzip `fathom-starter.zip`. **Hidden folders:** the `.kiro` folder starts with a dot. On Mac press `Cmd+Shift+.` in Finder, on Windows turn on View -> Hidden items.
2. Copy **everything inside** `fathom-starter/` (including `.kiro`, `.gitignore`, `.env.example`) into your cloned `Hackachusetts/` folder. Do not copy the outer `fathom-starter` folder itself.
3. Push:
   ```bash
   git add -A
   git status
   ```
   Check that the list includes `.kiro/specs/fathom/requirements.md`, `.kiro/steering/...`, `.kiro/hooks/...`. If `.kiro` is missing, STOP and fix before committing.
   ```bash
   git commit -m "Add Fathom spec, steering, hooks, MCP config"
   git push origin main
   ```
4. Tell the group chat: "Starter is pushed, everyone `git pull`."

---

## PART 3. The git routine (copy this every time)

We all push straight to `main`, each in our own lane. Always pull first.

**Before you start working:**
```bash
git pull --rebase origin main
```
**After Kiro finishes a task and you checked it runs:**
```bash
git add -A
git commit -m "A: whale risk model + property tests (tasks 1.4, 1.4.1)"
git pull --rebase origin main
git push origin main
```
Message format: `A:` / `B:` / `C:` / `D:` + what + task numbers.

Commit **after every finished task**, not at the end of the day. Small and often.

**If git says "rejected" or "conflict":**
- "rejected / non-fast-forward": run `git pull --rebase origin main` then `git push origin main` again.
- Conflict in `tasks.md` (very likely, because Kiro ticks boxes): open the file, keep **both** versions of the checked lines, delete the `<<<<<<<`, `=======`, `>>>>>>>` marker lines, then:
  ```bash
  git add .kiro/specs/fathom/tasks.md
  git rebase --continue
  git push origin main
  ```
- Anything else confusing: paste the error to Kiro chat and say "explain and fix this git problem safely, do not delete my work."

**Never** commit `.env` or any API key. If a key leaks, rotate it.

---

## PART 4. The build, in order, with copy-paste prompts

Time is relative. If you only have a day, do Phases 0 to 2, a thin Phase 3 (one simulator scenario), then Part 7 and Part 8.

How to use Kiro for each prompt:
- **Spec tasks:** open `.kiro/specs/fathom/tasks.md`, click **Start task** next to your task ids. Kiro reads requirements and design itself.
- **Chat prompts below:** paste into the Kiro chat. They tell Kiro to read the spec and steering first.

### Phase 0 (hour 0 to 2): interface first, so nobody is blocked

**Person 1 (A), do this first, it unblocks everyone. Push within 45 minutes:**
> Read `.kiro/specs/fathom/design.md` section 4 and the steering files. Create the pydantic v2 models (Cell, Zone, Sighting, Conditions, TripRequest, RoutePlan, Citation) in `backend/app/models/`. Add `backend/requirements.txt` with fastapi, uvicorn, pydantic, numpy, shapely, geopandas, xarray, httpx, pyyaml, pytest, hypothesis. Add small example JSON for each model in `data/snapshots/examples/`. Do not build anything else yet.

Then Person 1 data reality check (uses the `fetch` MCP, screenshot #07):
> Read design.md section 3. For every data source in the table, use the fetch MCP and web access to check if it is reachable and what format it returns. Save a SMALL snapshot of each (under 5 MB) into `data/snapshots/`. Write `data/snapshots/SOURCES.md` with columns: layer, URL, fetched_at (UTC), status (live / cached / synthetic), notes. If a source is unreachable or too hard, create a small clearly-labeled synthetic version with `"synthetic": true`. Also check the Hackachusetts climate starter zip files if I put them in `data/raw/`. Tell me which layers are real and which are synthetic.

Also Person 1: **download the Climate track starter zip** from the hackathon portal (https://hackachusetts2026.vercel.app/#/climate), unzip into `data/raw/` (gitignored), and tell the group what is inside. I could not open that page's content, so I don't know what it contains.

**Person 2 (B):**
> Read `.kiro/specs/fathom/design.md` and the steering files. Scaffold `backend/` as a FastAPI app (`backend/app/main.py`, folders api, engine, agent, ingest, models per structure.md). Add a `/api/health` and `/api/meta/sources` endpoint that returns the contents of `data/snapshots/SOURCES.md` parsed as JSON (stub if missing). Add CORS for http://localhost:5173. Add a `backend/README` with the run command. Keep it minimal.

**Person 3 (C):**
> Read the spec and steering. Scaffold `frontend/` with Vite + React + TypeScript + Tailwind + MapLibre GL + deck.gl. Create a full-screen dark ocean-themed map centered on Massachusetts Bay, a top bar with a Captain / Manager mode toggle, a "Demo data" badge, and a bottom time slider. Use a free basemap style that requires no API key. Also create `frontend/src/mocks/` with fixture JSON matching the API shapes in design.md section 9, and a switch so the app runs entirely on mocks until the real backend exists.

**Person 4 (D):**
> Read the spec and steering. Create `mcp/fathom_mcp/` as a Python MCP server skeleton (using the official `mcp` Python SDK) with the eight tools from design.md section 7. Each tool should validate input with the pydantic models and return clearly-labeled placeholder data for now. Add `python -m fathom_mcp` as the entry point. Do not enable it in `.kiro/settings/mcp.json` yet.

**Checkpoint 0:** all four pushed, `git pull` works for everyone, app shows a dark map, backend runs.

### Phase 1 (hours 2 to 10): map + zones + risk

**Person 1 (A)**, in Kiro open tasks.md and **Start task** on 1.1, 1.2, 1.3, 1.4, 1.4.1 one at a time. If using chat instead:
> Execute tasks 1.1 to 1.4.1 from `.kiro/specs/fathom/tasks.md`, one task at a time, stopping after each so I can review. Follow design.md sections 4 to 6 and the testing-pbt steering file. Put all risk parameters in `config/risk.yaml`. Write Hypothesis property tests for: risk within [0,1], monotonic in speed, zero on land, adding a sighting never lowers risk. Before presenting the lethality curve parameters, mark them TODO-VERIFY in config comments, because they must be checked against the original paper.

**Person 2 (B):**
> Execute tasks 1.5 from tasks.md. Implement GET `/api/layers/conditions`, `/api/layers/zones`, `/api/layers/risk` reading from `data/snapshots/` and the engine functions Person A has written (import them; if a function is missing, create a thin stub with a TODO and tell me). Honor `FATHOM_DEMO_MODE`. Every response includes source, fetched_at, and a `cached`/`synthetic` flag.

**Person 3 (C):**
> Execute tasks 1.6, 1.7, 1.8 from tasks.md. Layer toggles, wave/wind/SST layers, zone polygons with click popups (name, type, dates, restriction, source link) and dimming when inactive, risk heatmap with a speed slider and a per-cell factor breakdown panel. Start with mock data, then switch to the real API when Person B's endpoints are pushed.

**Person 4 (D):**
> Write the first golden test cases and the Hypothesis strategies shared by tests in `backend/tests/` (a helper that generates random valid cells, sightings, speeds). Then write `docs/DEMO_DATA_PLAN.md`: for the demo, pick one specific date in whale season and one port (Gloucester), list which snapshot files we need, and which are synthetic. Check `docs/kiro-evidence/LOG.md` is getting entries from hooks.

**Checkpoint 1:** map shows conditions, zones, and risk, from real or clearly-labeled synthetic snapshots. Everyone sees it on their own machine.

### Phase 2 (hours 10 to 20): routing + agent

**Person 2 (B):**
> Execute tasks 2.1, 2.2, 2.2.1, 2.2.2, 2.3, 2.4 from tasks.md. A* router on the 8-connected water grid with 3-hour time slices, slow-zone speed caps, prohibited-zone impassability, weather limits, alternates via a risk_pref sweep (0.1, 0.5, 0.9) with de-duplication, and a clear "no legal route, relax X" message. Put the property tests in `backend/tests/`. Never let the route cross land.

Then:
> Execute task 2.6: the agent loop. Tool-calling, max 8 calls, SSE streaming of each tool call and result to POST `/api/trip/plan`. The system prompt must say: advisory only, every factual claim must come from a tool result and be cited as [tool:call_id], say "I don't know" if no tool supports a claim, never say a plan is legally compliant. Use a model client abstraction so we can switch providers by env var. If there is no API key, fall back to a deterministic canned response for the demo prompts so the deployed demo never breaks.

**Person 4 (D):**
> Execute task 2.5: finish the `fathom-mcp` server so each tool calls the real backend engine functions (import from `backend/app/engine`). Then set `"disabled": false` for `fathom` in `.kiro/settings/mcp.json`, and show it works by asking Kiro in chat: "Use the fathom MCP to list the active zones near Stellwagen Bank and write a test that our router avoids them." Take screenshot **#08**.

Then:
> Execute task 2.7: the citation guard. Post-process agent output: any sentence with a number, zone name, or date and no [tool:...] tag is flagged and re-prompted once, else removed. Write 10 canned eval prompts in `backend/tests/evals/` and a test that checks every number in the output appears in a tool result.

**Person 3 (C):**
> Execute tasks 2.8 and 2.9. Captain mode: request panel, live feed of the agent's tool calls, ranked plan cards that draw their route on the map, and a "Why" drawer showing zones crossed, risk summary, weather window, and citations. Show the advisory-only disclaimer on every plan.

**Person 1 (A):**
> Execute tasks 3.1 and 3.2 early (fleet sample and effort proxy). Use real historical vessel-track data only if we actually have it; otherwise generate a synthetic fleet of about 200 anonymous trips seeded from Gloucester, Boston, Plymouth and Provincetown and known fishing grounds. Mark it `synthetic: true` and say so in `SOURCES.md`.

**Checkpoint 2:** type a trip request, see 2 to 3 routes and a cited explanation. This is your core demo. Record a rough screen capture as a backup.

### Phase 3 (hours 20 to 28): simulator + polish (your "wow")

**Person 4 (D):**
> Execute tasks 3.3, 3.4, 3.6. `simulate_zone`: route the fleet sample with and without the candidate zone, report change in risk-weighted vessel-hours, steaming hours, fuel, and effort-proxy access. Compute the Pareto frontier across at least 3 scenarios (full closure extension, dynamic zone around recent sightings, seasonal speed limit). Generate a plain-language summary a board member can read. Cache the baseline. Add Hypothesis property tests: no frontier option is dominated by another.

**Person 3 (C):**
> Execute tasks 3.5, 3.9, 3.11. Manager mode: draw tool, scenario list, trade-off chart (risk reduced vs. livelihood cost) with the efficient options highlighted, and the plain-language summary. "Demo data" and "synthetic" badges everywhere relevant. Make Captain mode usable at phone width.

**Person 2 (B):**
> Execute tasks 3.7, 3.8 (with Person 4), 3.10: Portuguese and Spanish briefs where numbers and zone names are identical across languages (add a property test), one-page printable brief export, and a full demo-mode smoke test that runs the whole flow with the network disabled.

**Person 1 (A):**
> Verify the facts list at the bottom of `docs/pitch.md` (whale population, lethality curve parameters, zone dates, wind lease names) against the original sources. For each, write the source URL and the verified value in `docs/FACT_CHECK.md`. Fix `config/risk.yaml` if a parameter was wrong.

**Checkpoint 3 (FREEZE):** the full demo path works from a fresh clone. After this, **bug fixes only**.

---

## PART 5. Make the Kiro usage obvious (this is where "Best Use of Kiro" is won)

Judges read your write-up and look at `.kiro/`. Do these on purpose, and log them in `docs/kiro-evidence/LOG.md`:

- [ ] **Specs:** at least one more spec created through Kiro's UI on a new feature (for example "Wind construction overlay" or "Brief export"). Multiple specs look better than one.
- [ ] **Vibe vs spec comparison:** pick one small thing (say the brief layout). Do it by vibe chat once, and the routing engine by spec. Note the difference honestly. Screenshot #12.
- [ ] **Multiple Kiro surfaces:** each person uses a different one for at least one task: IDE, **CLI** (`kiro-cli`), and **Web**. The rules list **Crew** too. I do not know what Crew is or how it works, so look it up in the Kiro docs and try it once if you can. Write down how each felt different. Screenshot #10.
- [ ] **Hooks:** four are included. Leave them on all day. Screenshots #05 and #06.
- [ ] **Steering:** show the "before and after" of one steering rule, e.g. Kiro refusing to write "legally compliant".
- [ ] **MCP:** `fetch` for data, your own `fathom` server. Screenshots #07 and #08.
- [ ] **Property-based testing:** let Hypothesis find at least one real counterexample. Keep it. Screenshot #09.
- [ ] **Powers:** open the Powers section in Kiro, install one that is relevant (browse the list and pick honestly), and use it once. Screenshot #11. I can't tell you which powers exist or which are relevant to you, so choose from what the list shows.

At the end, Person 4 fills `KIRO_WRITEUP.md` using real log lines and screenshots. Keep claims true. Judges can read the repo.

---

## PART 6. Credits (2000 each)

I don't know exactly how many credits each kind of Kiro request costs, so watch the meter yourself for the first hour and adjust.
- Do **one task at a time**. Do not ask Kiro to "build the whole app".
- When something is slightly wrong, give a **targeted fix prompt** ("in routing.py the A* heuristic ignores the speed cap, fix only that"). Do not re-run the whole task.
- Use cheap chat for small edits, spec tasks for big pieces.
- Keep **about 300 credits per person in reserve** for the last 6 hours.
- Credits are per person, so if one person is low, hand the next task to a teammate in the same lane.

---

## PART 7. Deploy (judges need a working link)

Simplest path that keeps cost at zero: **one service that serves both the API and the built frontend.**
1. Build the frontend: `cd frontend && npm run build`.
2. Ask Kiro (Person 2):
   > Make FastAPI serve `frontend/dist` as static files at `/` and the API under `/api`. Add a `Dockerfile` and a short DEPLOY.md for deploying to Render (free web service). Demo mode must be the default, so the site works with no API key. If an LLM key is set, enable the live agent but add a simple per-IP rate limit.
3. Deploy to Render (or Railway/Fly). Put the public URL at the top of `README.md`.
4. Test in a **private/incognito window on your phone**. Judges may use the link without you.
5. Make sure the canned demo prompt always works even if the LLM is down.

---

## PART 8. Video + submission

**Video (under 3:00, public):**
1. Use the script in `docs/pitch.md` (story, problem, live demo, how it's built with Kiro, close).
2. Record the screen with the app running on the device it was built for (laptop browser is fine). Also show the phone-width view briefly.
3. One person narrates. Record in demo mode.
4. **No copyrighted music. No third-party logos or trademarks** (keep NOAA/AWS/Kiro logos off your slides; plain text names and map attribution are fine).
5. Upload to **YouTube/Vimeo set to Public**. Test the link while logged out. Cut at 2:50 to be safe, judges don't have to watch past 3:00.

**Submission checklist (Person 4 does it, everyone checks):**
- [ ] All 4 teammates added to the submission
- [ ] Track: Climate Tech & Clean Energy
- [ ] Text description (features and functionality)
- [ ] Video link (public)
- [ ] Public GitHub URL: https://github.com/shrish186/Hackachusetts (repo is public already)
- [ ] `.kiro/` visible on GitHub at repo root, and not in `.gitignore`
- [ ] README has run + test instructions and the live link
- [ ] `KIRO_WRITEUP.md` complete, with screenshots committed
- [ ] Testing instructions in the form (demo URL, "no login needed", the canned demo prompt)
- [ ] Everything in English
- [ ] Fresh-clone test: clone the repo into a new folder and follow the README exactly
- [ ] Submit **before the deadline**. Edits after the Submission Period are not allowed.

---

## PART 9. If you fall behind

- Data layer won't load -> switch to synthetic, label it, move on.
- Routing too slow -> coarser grid, 100 trips instead of 200.
- Agent flaky -> ship the deterministic plan cards first; agent narrative second.
- Behind at the halfway point -> cut Portuguese/Spanish and stretch goals. **Keep the Manager-mode simulator**, it is what makes the project memorable.
- Never leave the repo broken on `main`. If you must push something half-done, put it behind a flag or on a branch.

## Facts I could not verify (check before putting on slides)
- Right whale population number, the speed-lethality curve parameters, current zone names and dates, wind lease names.
- Eligibility details for international students, and the submission deadline.
- Contents of the Climate starter zip and dataset links on the portal.
- Exact current names/features of Kiro Web, Crew and Powers.
