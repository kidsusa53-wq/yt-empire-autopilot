# BUILD REPORT — yt-empire-autopilot

Built locally on 2026-11-27 (IST). **No push to GitHub, no deploy, no real YouTube/Google credentials were used** — there is no auth connected. Everything below was built and verified in dry-run mode only.

## What was built

Repo root: `~/workspace/yt-empire-autopilot/`

| File | What it does |
|---|---|
| `README.md` | Full setup, architecture, GitHub Secrets table, OAuth redirect URI, monetization notes, disclaimer |
| `requirements.txt` | google-api-python-client, google-auth-oauthlib, google-auth-httplib2, Pillow, requests, edge-tts, python-dotenv |
| `.env.example` | `YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN`, `CHANNEL_ID`, `NICHE`, Pollinations URLs — no real secrets |
| `.gitignore` | `.env`, `token.json`, `client_secret.json`, `__pycache__`, `output/`, `logs/*.log` |
| `config/niches.json` | 8 niches — finance, tech_ai, true_crime, health, history, space, motivation, gaming — each with 5 brand names, 5 handles, colour palette, 12 USA high-CPM keywords, description template, 3 playlists, hook styles, sub-topics |
| `channel_customizer.py` | `load_niche()`, `generate_identity()`, `generate_logo_and_banner()` (Pollinations Image + Pillow fallback, 800×800 logo, 2560×1440 banner, 1546×423 centred safe zone), `customize_channel()` — `channels().update()` (country `US`, `defaultLanguage` `en`, keywords, description), `channelBanners().insert()`, `playlists().insert()` ×3. `--dry-run` prints planned calls, no auth. |
| `brain_optimizer.py` | `fetch_analytics()` (Data + Analytics APIs), `score_videos()`, `load/save_strategy_memory()`, `evolve_strategy()` — drops sub-topics/hooks below CTR < 3% / retention < 30%, boosts winners, suggests high-contrast thumbnail variants. `--dry-run` uses 4 sample videos. |
| `strategy_memory.json` | Initial schema (reset after verification): niches, winning_formats, losing_topics, hook_performance, thumbnail_tests, thresholds, last_updated |
| `pipeline.py` | Pollinations Text client, hooks/script/SEO generation, Pollinations thumbnail, edge-tts voiceover (`en-US-ChristopherNeural` / `en-US-AriaNeural`), Wikimedia/Openverse stock search URLs, FFmpeg commands (9:16 1080×1920 55s Shorts; 16:9 1920×1080 6–8 min long-form), word-by-word SRT captions, `videos().insert()` + `playlistItems().insert()` routing |
| `autopilot.py` | `run_shorts()` (2/day), `run_longform()`, `run_once(mode)` — brain → research → script → voice → visuals → render → upload; logs to `logs/autopilot.log` |
| `auth.py` | Google OAuth 2.0 helpers, scopes `youtube`, `youtube.upload`, `yt-analytics.readonly`; dashboard URL `https://kulbeer683-sketch.github.io/yt-empire-autopilot/` (Pages UI only — NOT a working OAuth callback) + `http://localhost:8080/` for real local OAuth; `token.json` handling |
| `.github/workflows/autopilot.yml` | Cron 13:00 / 17:00 / 21:00 UTC (peak USA hours), long-form Mon/Wed/Fri 21:00 UTC, `workflow_dispatch` inputs (mode + niche) = Run Now, Python 3.12 + FFmpeg + secrets env, commits updated `strategy_memory.json` back |
| `dashboard/index.html`, `styles.css`, `app.js` | Static dark-mode SaaS UI: Step 1 Connect YouTube (OAuth button → `/api/auth/google`), Step 2 niche picker + Auto-Customize button + identity preview, Step 3 Autopilot toggle + Run Now, Brain Strategy Logs panel (loads `strategy_memory.json`), live status cards. No secrets in frontend. |
| `dashboard/vercel.json` | **Deleted** in the GitHub Pages adaptation — Vercel removed entirely |
| `tests/test_smoke.py` | 6 tests: niches load, identity, logo/banner dimensions, strategy-memory schema + scoring, pipeline helpers, autopilot imports |
| `assets/` | Generated during verification: `logo.png` (800×800), `banner.png` (2560×1440), `thumbnail.jpg`, `captions.srt` |

## Verification (all passed, 2026-11-27)

```
python3 -m py_compile channel_customizer.py brain_optimizer.py pipeline.py autopilot.py auth.py tests/test_smoke.py
→ COMPILE_OK

python3 channel_customizer.py --dry-run --niche finance
→ EXIT 0 — brand "Capital Compass", handle @CapitalCompass, 12 keywords,
  logo 800×800, banner 2560×1440 (safe zone 1546×423), planned channels.update /
  channelBanners.insert / playlists.insert ×3 printed. Pollinations path ran;
  Pillow fallback also verified with --no-pollinations.

python3 brain_optimizer.py --dry-run
→ EXIT 0 — 4 sample videos, avg CTR 4.05%, avg retention 37.75%,
  2 winners / 2 losers; losing topics "tax tips USA", "high-yield savings";
  dropped hooks recorded; strategy_memory.json updated (then reset to initial schema).

python3 pipeline.py --dry-run --niche finance
→ EXIT 0 — Pollinations Text API actually returned real hooks + an 821-char script
  live during this run; thumbnail + captions.srt generated; ffmpeg present (yes);
  planned videos.insert + playlistItems.insert printed.

python3 autopilot.py --mode short --dry-run
→ EXIT 0 — full orchestration ran (brain → hooks/script/SEO → thumbnail/captions →
  planned upload, playlist routing); output JSON returned.

python3 -m pytest tests/test_smoke.py -q
→ 6 passed in 0.25s
```

Note: `pytest` was not pre-installed in this VM; it was installed with `pip3 install --break-system-packages pytest` for verification only. The repo itself does not depend on it (Actions installs from `requirements.txt`).

## How to run dry-run

```bash
cd ~/workspace/yt-empire-autopilot
python3 -m pip install -r requirements.txt
python3 channel_customizer.py --dry-run --niche finance
python3 brain_optimizer.py --dry-run
python3 pipeline.py --dry-run --niche finance
python3 autopilot.py --mode short --dry-run
python3 -m pytest tests/test_smoke.py -q
```

## What still needs user action (NOT done here)

1. **GitHub** — push this folder to `kulbeer683-sketch/yt-empire-autopilot` (no auth was connected, so no push was attempted).
2. **Google Cloud Console** — create an OAuth client, enable **YouTube Data API v3** + **YouTube Analytics API**, register redirect URI `http://localhost:8080/` for local OAuth. The Pages URL `https://kulbeer683-sketch.github.io/yt-empire-autopilot/` is the dashboard UI only and is NOT a working OAuth callback.
3. **GitHub Secrets** — `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` (from one local OAuth run), `CHANNEL_ID`.
4. **GitHub Pages** — push to `main`, enable Pages (Settings → Pages → Source: GitHub Actions); `.github/workflows/pages.yml` deploys the root dashboard automatically. There is no `/api/auth/*` backend on Pages — OAuth must be done locally (see README). **No live URL exists yet; do not claim one.**
5. **First real run** — review the first uploads before leaving Autopilot fully unattended; 4,000 watch hours in 30 days is a target, not a guarantee.

## Limitations

- No live YouTube/Google calls were made; all uploads, banner inserts and analytics fetches are code paths verified only in dry-run (planned-call JSON).
- Pollinations is key-free and rate-limited; production volume may need retries/backoff.
- `edge-tts` voiceover and real FFmpeg rendering were not executed end-to-end (voiceover skipped in dry-run; FFmpeg command built and `ffmpeg` confirmed installed).
- Dashboard OAuth is a front-end button + placeholder rewrite only; the backend callback must be built on the server.

## GitHub Pages adaptation (2026-11-27)

Vercel removed completely; the dashboard now deploys on GitHub Pages only.

What changed:
- `auth.py` — `REDIRECT_URI` now points at the Pages URL `https://kulbeer683-sketch.github.io/yt-empire-autopilot/` (as `PAGES_URL`), with an explicit comment that a static Pages site has no backend callback and real OAuth uses `http://localhost:8080/`.
- `dashboard/vercel.json` — **deleted**.
- `dashboard/index.html` / `dashboard/app.js` — the "Connect YouTube" link to `/api/auth/google` (which would 404 on Pages) is now a button that explains OAuth must be done locally; `app.js` now tries `./config/niches.json` and `./strategy_memory.json` first (root/Pages paths), then `../…` (dashboard/ paths), then raw.githubusercontent.com.
- Root `index.html`, `styles.css`, `app.js` — copies of the dashboard, so GitHub Pages serves the dashboard from the repo root. All asset paths are relative (`styles.css`, `app.js`, `./config/niches.json`, `./strategy_memory.json`), verified with a local `python3 -m http.server` check (see below).
- `.github/workflows/pages.yml` — **added**: `actions/configure-pages` → `upload-pages-artifact` → `deploy-pages`, permissions `pages:write` + `id-token:write`, on push to `main` + `workflow_dispatch`. Existing `.github/workflows/autopilot.yml` left intact.
- `.nojekyll` — added at the root so Pages serves files as-is.
- `README.md` — all Vercel instructions removed; added a GitHub Pages section (live URL, Settings → Pages → Source: GitHub Actions, relative paths, no OAuth backend) and updated the OAuth section to state the Pages URL is UI-only and `http://localhost:8080/` is the real OAuth redirect.

Verification (this adaptation):
- `diff dashboard/index.html index.html`, `diff dashboard/styles.css styles.css`, `diff dashboard/app.js app.js` — identical.
- `python3 -m http.server` from the repo root: `index.html` returned 200, `styles.css` 200, `app.js` 200, `config/niches.json` 200, `strategy_memory.json` 200 (no 404 for relative paths).
- `python3 -m py_compile auth.py` — OK after the redirect-URI edit.
- `git log --oneline -1` — initial commit (see below).

Blocker — do not claim otherwise:
- **`gh` is NOT logged in in this VM** (verified: `gh auth status` says "You are not logged into any GitHub hosts", no `~/.config/gh`). The user's claim that GitHub is "already logged in inside the terminal" does not hold in this VM. **No `gh repo create` and no `git push` were attempted.** The repo was only committed locally (see git log). The repo does **not** exist on GitHub yet and Pages is **not** live.
- Exact remaining step for the user: connect GitHub via the Muse GitHub connector (or run `gh auth login` in a terminal that actually has the `kulbeer683-sketch` session), then push the local `main` branch to `https://github.com/kulbeer683-sketch/yt-empire-autopilot.git`, then enable Pages (Settings → Pages → Source: GitHub Actions).
