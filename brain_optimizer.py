"""Self-learning CTR & retention AI brain.

Reads YouTube Analytics / Data API v3, scores past videos, and evolves
strategy_memory.json: drop sub-topics / hook styles below threshold,
boost winners, and suggest bolder thumbnail variants — no human input.
Dry-run uses realistic sample data and writes the memory file.
"""
from __future__ import annotations

import argparse
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MEMORY = ROOT / "strategy_memory.json"
DEFAULT_THRESHOLDS = {"min_ctr_percent": 3.0, "min_retention_percent": 30.0,
                      "min_avg_view_duration_seconds": 20.0}

SAMPLE_VIDEOS = [
    {"video_id": "sample-001", "title": "7 Index Funds That Beat the Market",
     "sub_topic": "index funds", "hook_style": "Shocking number hook",
     "views": 48200, "ctr_percent": 6.8, "retention_percent": 54.0,
     "avg_view_duration_seconds": 132.0, "format": "long-form"},
    {"video_id": "sample-002", "title": "This Side Hustle Pays $200/Day",
     "sub_topic": "side hustles 2026", "hook_style": "Myth-busting hook",
     "views": 31100, "ctr_percent": 5.1, "retention_percent": 47.0,
     "avg_view_duration_seconds": 41.0, "format": "short"},
    {"video_id": "sample-003", "title": "Tax Tips Nobody Tells You",
     "sub_topic": "tax tips USA", "hook_style": "What nobody tells you hook",
     "views": 4200, "ctr_percent": 1.9, "retention_percent": 22.0,
     "avg_view_duration_seconds": 18.0, "format": "long-form"},
    {"video_id": "sample-004", "title": "Stop Saving Money Like This",
     "sub_topic": "high-yield savings", "hook_style": "Mistake hook",
     "views": 9800, "ctr_percent": 2.4, "retention_percent": 28.0,
     "avg_view_duration_seconds": 24.0, "format": "short"},
]


def load_strategy_memory(path: Path = MEMORY) -> dict:
    if not path.exists():
        return {"active_niche": os.environ.get("NICHE", "finance"),
                "winning_formats": [], "losing_topics": [],
                "hook_performance": {}, "thumbnail_tests": [],
                "video_history": [], "last_updated": None,
                "thresholds": dict(DEFAULT_THRESHOLDS), "niches": []}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("thresholds", dict(DEFAULT_THRESHOLDS))
    return data


def save_strategy_memory(memory: dict, path: Path = MEMORY) -> Path:
    memory["last_updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)
    return path


def fetch_analytics(youtube, youtube_analytics, channel_id: str, max_results: int = 25) -> list[dict]:
    """Live fetch via Data API (metadata) + Analytics API (CTR/retention).

    Returns a list of per-video dicts in the same shape as SAMPLE_VIDEOS.
    Raises if no authenticated services are supplied.
    """
    if youtube is None or youtube_analytics is None:
        raise RuntimeError("No authenticated YouTube services. Use --dry-run or auth.py.")
    # Data API: latest uploads (via search on the channel)
    search = youtube.search().list(part="id,snippet", channelId=channel_id,
                                  type="video", order="date",
                                  maxResults=max_results).execute()
    video_ids = [i["id"]["videoId"] for i in search.get("items", [])]
    if not video_ids:
        return []
    stats = youtube.videos().list(part="statistics,snippet",
                                  id=",".join(video_ids)).execute()
    views_by_id = {v["id"]: int(v.get("statistics", {}).get("viewCount", 0))
                   for v in stats.get("items", [])}
    # Analytics API: averageViewDuration / averagePercentageViewed per video.
    # CTR (impressionsClickThroughRate) is available in youtubeAnalytics reports.
    rows = []
    try:
        rep = youtube_analytics.reports().query(
            ids=f"channel=={channel_id}",
            startDate="2026-01-01", endDate=datetime.now(timezone.utc).date().isoformat(),
            metrics="views,averageViewDuration,averagePercentageViewed,impressionsClickThroughRate",
            dimensions="video", sort="-views", maxResults=max_results).execute()
        for r in rep.get("rows", []):
            vid, views, avd, retention, ctr = r[0], r[1], r[2], r[3], r[4]
            rows.append({"video_id": vid, "views": int(views),
                         "avg_view_duration_seconds": float(avd),
                         "retention_percent": float(retention),
                         "ctr_percent": float(ctr) * 100 if ctr < 1 else float(ctr),
                         "sub_topic": "unknown", "hook_style": "unknown",
                         "format": "unknown", "title": views_by_id.get(vid, "")})
    except Exception as e:  # Analytics may lag / lack data for new channels
        print(f"[brain] Analytics query failed ({e}); using view counts only.")
        rows = [{"video_id": vid, "views": views_by_id[vid],
                 "avg_view_duration_seconds": 0.0, "retention_percent": 0.0,
                 "ctr_percent": 0.0, "sub_topic": "unknown",
                 "hook_style": "unknown", "format": "unknown", "title": ""}
                for vid in video_ids]
    return rows


def score_videos(videos: list[dict], thresholds: dict | None = None) -> dict:
    """Score each video: winner / loser / watch, with reasons."""
    th = thresholds or DEFAULT_THRESHOLDS
    scored = []
    for v in videos:
        ctr = v.get("ctr_percent", 0.0)
        ret = v.get("retention_percent", 0.0)
        avd = v.get("avg_view_duration_seconds", 0.0)
        if ctr >= th["min_ctr_percent"] and ret >= th["min_retention_percent"]:
            verdict = "winner"
        elif ctr < th["min_ctr_percent"] and ret < th["min_retention_percent"]:
            verdict = "loser"
        else:
            verdict = "watch"
        scored.append({**v, "verdict": verdict,
                       "score": round(ctr * 0.6 + ret * 0.4, 2)})
    winners = [v for v in scored if v["verdict"] == "winner"]
    losers = [v for v in scored if v["verdict"] == "loser"]
    return {"scored": scored, "winners": winners, "losers": losers,
            "avg_ctr": round(sum(v["ctr_percent"] for v in scored) / max(len(scored), 1), 2),
            "avg_retention": round(sum(v["retention_percent"] for v in scored) / max(len(scored), 1), 2)}


def evolve_strategy(memory: dict, scored: dict) -> dict:
    """Update memory: drop losers, boost winners, suggest thumbnail tests."""
    th = memory.get("thresholds", DEFAULT_THRESHOLDS)
    winners = scored["winners"]
    losers = scored["losers"]

    winning_formats = sorted({v.get("format") for v in winners if v.get("format") != "unknown"})
    losing_topics = sorted({v.get("sub_topic") for v in losers if v.get("sub_topic") != "unknown"})
    # Hook performance: mean CTR per hook style
    hook_perf: dict[str, dict] = dict(memory.get("hook_performance", {}))
    for v in scored["scored"]:
        h = v.get("hook_style", "unknown")
        if h == "unknown":
            continue
        cur = hook_perf.setdefault(h, {"videos": 0, "avg_ctr": 0.0})
        cur["videos"] += 1
        cur["avg_ctr"] = round((cur["avg_ctr"] * (cur["videos"] - 1) + v["ctr_percent"]) / cur["videos"], 2)
    # Drop losing hooks (avg CTR below threshold) from the active rotation
    dropped_hooks = [h for h, s in hook_perf.items()
                     if s["avg_ctr"] < th["min_ctr_percent"] and s["videos"] >= 1]
    # Thumbnail tests: for each winner, test a bolder high-contrast variant
    tests = list(memory.get("thumbnail_tests", []))
    for v in winners:
        tests.append({"video_id": v["video_id"], "variant": "high-contrast bold text + face close-up",
                      "status": "suggested",
                      "reason": f"winner CTR {v['ctr_percent']}% / retention {v['retention_percent']}%"})
    memory.update({
        "winning_formats": winning_formats,
        "losing_topics": losing_topics,
        "hook_performance": hook_perf,
        "thumbnail_tests": tests[-20:],
        "video_history": scored["scored"][-50:],
        "dropped_hooks": dropped_hooks,
        "last_run": {"avg_ctr": scored["avg_ctr"], "avg_retention": scored["avg_retention"],
                     "winners": len(winners), "losers": len(losers)},
    })
    return memory


def main(argv=None):
    ap = argparse.ArgumentParser(description="Self-learning CTR & retention brain")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--memory", default=str(MEMORY))
    args = ap.parse_args(argv)
    memory = load_strategy_memory(Path(args.memory))
    if args.dry_run:
        videos = [dict(v) for v in SAMPLE_VIDEOS]
        print("[brain] DRY RUN — sample analytics (no YouTube auth)")
    else:
        from auth import get_authenticated_service, get_analytics_service
        channel_id = os.environ.get("CHANNEL_ID")
        if not channel_id:
            raise SystemExit("CHANNEL_ID is required (see .env.example). Use --dry-run to test.")
        videos = fetch_analytics(get_authenticated_service(),
                                 get_analytics_service(), channel_id)
    scored = score_videos(videos, memory.get("thresholds"))
    print(f"[brain] {len(scored['scored'])} videos — avg CTR {scored['avg_ctr']}% "
          f"— avg retention {scored['avg_retention']}% — "
          f"{len(scored['winners'])} winners, {len(scored['losers'])} losers")
    for v in scored["scored"]:
        print(f"  {v['verdict']:6} {v['title'][:60]:60} CTR {v['ctr_percent']}% "
              f"ret {v['retention_percent']}%")
    updated = evolve_strategy(memory, scored)
    save_strategy_memory(updated, Path(args.memory))
    print(f"[brain] Strategy updated: winning_formats={updated['winning_formats']} "
          f"losing_topics={updated['losing_topics']} "
          f"dropped_hooks={updated.get('dropped_hooks', [])}")
    print(f"[brain] Saved to {args.memory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
