"""Autopilot — main entry point.

Orchestrates: brain -> research -> script -> voice -> visuals ->
render -> upload, for Shorts (2/day) and long-form (every 2 days).
Logs to logs/. Dry-run does everything except YouTube upload / voiceover.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOGS / "autopilot.log"), logging.StreamHandler()])
log = logging.getLogger("autopilot")


def _load_memory():
    from brain_optimizer import load_strategy_memory
    return load_strategy_memory()


def _pick_topic(cfg: dict, memory: dict) -> str:
    losing = set(memory.get("losing_topics", []))
    candidates = [t for t in cfg.get("sub_topics", []) if t not in losing]
    if not candidates:
        candidates = cfg.get("sub_topics", ["trending topic"])
    return random.choice(candidates)


def run_once(mode: str, niche: str | None = None, dry_run: bool = False) -> dict:
    """Run one video end-to-end. mode: 'short' or 'long'."""
    from channel_customizer import load_niche
    from brain_optimizer import score_videos, evolve_strategy, save_strategy_memory, SAMPLE_VIDEOS
    from pipeline import (generate_hooks, generate_script, generate_seo,
                          generate_thumbnail, write_captions, upload_video,
                          route_to_playlist, ffmpeg_command, check_ffmpeg)

    niche = niche or os.environ.get("NICHE", "finance")
    cfg = load_niche(niche)
    memory = _load_memory()

    # 1) Brain: learn from past performance before producing anything new.
    if dry_run:
        scored = score_videos(SAMPLE_VIDEOS, memory.get("thresholds"))
    else:
        scored = {"scored": [], "winners": [], "losers": [], "avg_ctr": 0.0, "avg_retention": 0.0}
    memory = evolve_strategy(memory, scored)
    save_strategy_memory(memory)
    log.info("Brain: %d winners, %d losers, losing topics=%s",
             len(scored["winners"]), len(scored["losers"]), memory.get("losing_topics"))

    # 2) Research / hooks / script / SEO
    topic = _pick_topic(cfg, memory)
    hooks = generate_hooks(topic, cfg["hook_styles"])
    duration = "short" if mode == "short" else "long"
    script = generate_script(topic, niche, duration)
    seo = generate_seo(topic, cfg, duration)
    log.info("Topic: %s | hook: %s | title: %s", topic, hooks[0] if hooks else "", seo["title"])

    # 3) Visuals + captions
    thumb = generate_thumbnail(f"{topic}, bold YouTube thumbnail, high contrast",
                               ROOT / "assets" / f"thumbnail_{mode}.jpg")
    total = 55 if mode == "short" else 420
    caps = write_captions(script, ROOT / "assets" / f"captions_{mode}.srt", total_seconds=total)

    # 4) Voiceover (skipped in dry-run; needs edge-tts + network)
    audio = ROOT / "assets" / f"voiceover_{mode}.mp3"
    if not dry_run:
        from pipeline import generate_voiceover, VOICES
        generate_voiceover(script, VOICES["male"], audio)
    else:
        log.info("Dry-run: voiceover skipped (would use edge-tts %s)", "en-US-ChristopherNeural")

    # 5) Render (FFmpeg command; actual render needs ffmpeg + assets)
    out = ROOT / "output" / f"{mode}.mp4"
    out.parent.mkdir(exist_ok=True)
    cmd = ffmpeg_command([str(thumb)], str(audio), str(out),
                         vertical=(mode == "short"), duration=total)
    log.info("FFmpeg: %s (ffmpeg installed: %s)", " ".join(cmd), check_ffmpeg())
    if not dry_run and check_ffmpeg():
        import subprocess
        subprocess.run(cmd, check=False)

    # 6) Upload + playlist routing
    playlist = route_to_playlist(cfg, duration)
    log.info("Routing to playlist: %s", playlist.get("title"))
    yt = None
    if not dry_run:
        from auth import get_authenticated_service
        yt = get_authenticated_service()
    result = upload_video(yt, str(out), seo,
                          playlist_id=playlist.get("id") if not dry_run else "dry-run-playlist",
                          dry_run=dry_run)
    log.info("Upload result: %s", result)
    return {"mode": mode, "niche": niche, "topic": topic, "title": seo["title"],
            "thumbnail": str(thumb), "captions": str(caps), "upload": result,
            "timestamp": datetime.now(timezone.utc).isoformat()}


def run_shorts(niche: str | None = None, dry_run: bool = False, count: int = 2):
    return [run_once("short", niche, dry_run) for _ in range(count)]


def run_longform(niche: str | None = None, dry_run: bool = False):
    return run_once("long", niche, dry_run)


def main(argv=None):
    ap = argparse.ArgumentParser(description="yt-empire-autopilot")
    ap.add_argument("--mode", choices=["short", "long", "shorts", "longform", "once"],
                    default="short")
    ap.add_argument("--niche", default=os.environ.get("NICHE", "finance"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    mode = args.mode
    if mode == "shorts":
        results = run_shorts(args.niche, args.dry_run, count=2)
    elif mode in ("long", "longform"):
        results = [run_longform(args.niche, args.dry_run)]
    else:
        results = [run_once("short" if mode != "once" else "short", args.niche, args.dry_run)]
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
