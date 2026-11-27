# yt-empire-autopilot

**100% autonomous, self-learning Cloud YouTube Automation SaaS — built locally, dry-run verified.**

A complete Python + static-dashboard project that turns a blank YouTube channel into a branded USA media brand, then publishes 2 Shorts/day + 1 long-form video every 2 days on GitHub Actions, while an AI brain learns from CTR / retention and evolves the strategy — with **no paid API keys** for research, scripts, thumbnails or voiceover.

> **Status in this repo:** local build only. Nothing here has been pushed to GitHub, deployed, or connected to a real YouTube/Google account. No Vercel — the dashboard deploys on **GitHub Pages**. See [What still needs you](#what-still-needs-you).

---

## Architecture

```
index.html / styles.css / app.js
                         Root copy of the dashboard, served by GitHub Pages
dashboard/                 Source copy of the same static dark-mode SaaS UI
channel_customizer.py      Identity -> logo/banner -> channels().update() (US/en/keywords)
                           -> channelBanners().insert() -> playlists().insert() x3
brain_optimizer.py         Analytics -> score_videos() -> evolve_strategy()
                           -> strategy_memory.json
pipeline.py                Pollinations Text/Image (key-free) + edge-tts + Wikimedia/Openverse
                           + FFmpeg render + SRT karaoke captions + videos().insert()
autopilot.py               Main entry: brain -> research -> script -> voice -> visuals
                           -> render -> upload; logs to logs/
auth.py                    Google OAuth 2.0 (youtube, youtube.upload, yt-analytics.readonly)
config/niches.json         8 niches: finance, tech_ai, true_crime, health, history,
                           space, motivation, gaming
.github/workflows/         GitHub Actions cron (peak USA hours) + workflow_dispatch (Run Now)
  autopilot.yml            24/7 automation backend
  pages.yml                GitHub Pages deploy (no Vercel)
strategy_memory.json       AI-brain state: winners, losers, hooks, thumbnail tests
```

### How Autopilot works

1. **Brain first** — before every run, `brain_optimizer` scores past videos (CTR, retention, avg. view duration). Sub-topics/hooks below threshold (default CTR < 3%, retention < 30%) are dropped; winners are boosted; a bolder high-contrast thumbnail variant is suggested per winner.
2. **Research & script** — Pollinations Text API (key-free) generates hooks, a script and SEO (title/description/tags).
3. **Voice & visuals** — `edge-tts` (`en-US-ChristopherNeural` / `en-US-AriaNeural`), Pollinations Image thumbnails, Wikimedia/Openverse public stock.
4. **Render** — FFmpeg, 9:16 1080×1920 Shorts (55s, 3s scene cuts via zoompan segments) and 16:9 1920×1080 long-form (6–8 min), with word-by-word SRT captions.
5. **Upload & route** — `videos().insert()` + `playlistItems().insert()` into the matching niche playlist.
6. **Schedule** — GitHub Actions cron at 13:00, 17:00 and 21:00 UTC (peak USA hours); 21:00 Mon/Wed/Fri runs long-form, the other slots run Shorts. Manual **Run Now** via Actions → workflow_dispatch.

### Channel customizer (1-click)

`channel_customizer.py` generates a brand identity from `config/niches.json` (5 brand names, 5 handles, palette, 10+ USA high-CPM keywords, description template, 3 playlists), creates an 800×800 logo and a 2560×1440 banner (1546×423 centre safe zone, centred text) via Pollinations Image + Pillow fallback, then calls:

- `channels().update()` with `brandingSettings.channel.country="US"`, `defaultLanguage="en"`, keywords and description
- `channelBanners().insert()` for the banner
- `playlists().insert()` ×3 (e.g. Trending Shorts / Deep Dive Documentaries / Must-Watch Guides)

---

## Quick start (dry-run — no auth needed)

```bash
python3 -m pip install -r requirements.txt   # Pillow + requests needed for dry-run images
python3 -m py_compile channel_customizer.py brain_optimizer.py pipeline.py autopilot.py auth.py

# 1-click customizer (dry-run: prints planned API calls, generates assets/logo.png + banner.png)
python3 channel_customizer.py --dry-run --niche finance

# AI brain (dry-run: sample analytics -> strategy_memory.json)
python3 brain_optimizer.py --dry-run

# Full pipeline (dry-run: hooks/script/SEO/thumbnail/captions, no upload)
python3 pipeline.py --dry-run --niche finance

# Autopilot, one Short (dry-run)
python3 autopilot.py --mode short --dry-run
python3 autopilot.py --mode long --dry-run

# Smoke tests (needs pytest, or run: python3 -m pytest tests/ -q)
python3 -m pytest tests/test_smoke.py -q
```

## Live setup (needs you — see below)

```bash
cp .env.example .env   # fill in YOUTUBE_CLIENT_ID / SECRET / REFRESH_TOKEN / CHANNEL_ID
python3 auth.py        # via get_authenticated_service() — first run opens local OAuth on :8080
python3 channel_customizer.py --niche finance          # real customise (no --dry-run)
python3 autopilot.py --mode short                       # real run
```

## Required GitHub Secrets (Actions → Settings → Secrets)

| Secret | Source |
|---|---|
| `YOUTUBE_CLIENT_ID` | Google Cloud Console → OAuth client |
| `YOUTUBE_CLIENT_SECRET` | Google Cloud Console → OAuth client |
| `YOUTUBE_REFRESH_TOKEN` | From the first local OAuth run (`token.json`) |
| `CHANNEL_ID` | Your YouTube channel ID |

Optional variable: `NICHE` (default `finance`).

## Google OAuth — Redirect URI

**Dashboard (GitHub Pages, UI only):**

```
https://kulbeer683-sketch.github.io/yt-empire-autopilot/
```

> **Important — no working Pages OAuth callback:** GitHub Pages is a static site with no backend, so it cannot receive an OAuth callback at `/api/auth/callback`. Do **not** register the Pages URL as an OAuth redirect expecting it to complete sign-in — it will not work. The Pages URL is for the dashboard UI only.
>
> For a real OAuth run, use the local redirect below (also in `auth.py` as `LOCAL_REDIRECT_URI`):
>
> ```
> http://localhost:8080/
> ```
>
> Register `http://localhost:8080/` in Google Cloud Console → APIs & Services → Credentials → OAuth client → Authorized redirect URIs, run `get_authenticated_service()` locally once, and store the resulting refresh token as the `YOUTUBE_REFRESH_TOKEN` GitHub Secret. A small backend (or a GitHub Actions secret flow) would be needed for a true web callback — that backend is **not** in this repo.

Enable in Google Cloud: **YouTube Data API v3** and **YouTube Analytics API**. OAuth scopes: `youtube`, `youtube.upload`, `yt-analytics.readonly`.

## Dashboard deployment — GitHub Pages (no Vercel)

Live URL (after push + Pages deploy):

```
https://kulbeer683-sketch.github.io/yt-empire-autopilot/
```

- The dashboard is static: `index.html`, `styles.css`, `app.js` at the repo root (source copy in `dashboard/`). All asset paths are relative (`./styles.css`, `./app.js`, `./config/niches.json`, `./strategy_memory.json`) so they work under the `/yt-empire-autopilot/` subpath.
- Deploy is automatic via `.github/workflows/pages.yml` (GitHub Actions: `actions/configure-pages` → `upload-pages-artifact` → `deploy-pages`). It runs on every push to `main` and on manual dispatch.
- Enable Pages once in the repo: **Settings → Pages → Build and deployment → Source: GitHub Actions** (not "Deploy from a branch").
- **OAuth is not implemented in this static build** — there is no `/api/auth/google` or `/api/auth/callback` on Pages. See "Google OAuth" above: run OAuth locally and store the refresh token as a GitHub Secret. No secrets are in the frontend.
- The 24/7 automation backend runs in GitHub Actions (`.github/workflows/autopilot.yml`), not on Pages.

## Monetization notes

- Target: 2 Shorts/day for subscriber growth + long-form every 2 days toward 4,000 watch hours. This is a goal, not a guarantee — watch hours depend on real audience retention.
- Content is generated with original scripts, human-style voiceover and edited visuals; follow YouTube's original/high-effort and reused-content policies, review uploads before they go public if in doubt, and keep the channel's About/disclaimer honest.
- Pollinations is key-free but rate-limited; for production volume, add retries/backoff or a paid provider.

## Disclaimer

YouTube OAuth credentials and API access are user-provided via env / GitHub Secrets. This project never ships real credentials, never stores them in the repo (`.env`, `token.json`, `client_secret.json` are gitignored), and makes no uploads in dry-run mode. You are responsible for complying with YouTube's Terms of Service, API policies and monetization policies.

## Files

| Path | Purpose |
|---|---|
| `channel_customizer.py` | 1-click branding, logo/banner, USA SEO, playlists |
| `brain_optimizer.py` | CTR/retention learning, `strategy_memory.json` |
| `pipeline.py` | Pollinations text/image, edge-tts, FFmpeg, captions, upload |
| `autopilot.py` | Orchestrator + logging |
| `auth.py` | Google OAuth 2.0 |
| `config/niches.json` | 8 niches |
| `index.html` / `styles.css` / `app.js` | Dashboard served by GitHub Pages (root copy; source in `dashboard/`) |
| `.github/workflows/autopilot.yml` | 24/7 cloud schedule + Run Now |
| `.github/workflows/pages.yml` | GitHub Pages deploy (no Vercel) |
| `tests/test_smoke.py` | Smoke tests |
| `BUILD_REPORT.md` | What was built and verified |

## What still needs you

1. Connect GitHub (`kulbeer683-sketch`) and push this repo — not done here (no auth connected in this VM; see BUILD_REPORT).
2. Enable GitHub Pages: Settings → Pages → Source: GitHub Actions. The `pages.yml` workflow deploys on push to `main`.
3. Create a Google Cloud OAuth client, enable YouTube Data API v3 + Analytics API, register `http://localhost:8080/` as the redirect URI (see "Google OAuth" — the Pages URL is UI-only, not a callback).
4. Run local OAuth once to obtain `YOUTUBE_REFRESH_TOKEN`, add the 4 GitHub Secrets above.
5. Review the first real uploads before leaving Autopilot fully unattended.
