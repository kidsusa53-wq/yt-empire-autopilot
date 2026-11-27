"""Smoke tests — import modules, validate config, dimensions, memory schema."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import brain_optimizer
import channel_customizer
import pipeline
import autopilot


def test_niches_load():
    data = json.loads((ROOT / "config" / "niches.json").read_text())
    assert len(data) >= 8, f"expected >=8 niches, got {len(data)}"
    for key, n in data.items():
        assert len(n["brand_name_ideas"]) >= 5, key
        assert len(n["handle_ideas"]) >= 5, key
        assert len(n["keywords"]) >= 10, key
        assert len(n["playlists"]) == 3, key
        assert n["color_palette"]["primary"] and n["color_palette"]["accent"], key


def test_identity():
    ident = channel_customizer.generate_identity("finance")
    assert ident["brand_name"]
    assert ident["handle"].startswith("@")
    assert len(ident["keywords"]) >= 10


def test_dimensions_constants():
    assert channel_customizer.LOGO_SIZE == (800, 800)
    assert channel_customizer.BANNER_SIZE == (2560, 1440)
    assert channel_customizer.SAFE_W == 1546 and channel_customizer.SAFE_H == 423


def test_strategy_memory_schema():
    mem = brain_optimizer.load_strategy_memory()
    for k in ("winning_formats", "losing_topics", "hook_performance",
              "thumbnail_tests", "last_updated"):
        assert k in mem, k
    scored = brain_optimizer.score_videos(brain_optimizer.SAMPLE_VIDEOS)
    assert len(scored["winners"]) >= 1 and len(scored["losers"]) >= 1
    updated = brain_optimizer.evolve_strategy(dict(mem), scored)
    assert updated["losing_topics"]


def test_pipeline_dry_run_helpers():
    from channel_customizer import load_niche
    cfg = load_niche("finance")
    seo = pipeline.generate_seo("Test Topic", cfg, "short")
    assert seo["title"] and seo["tags"]
    srt = pipeline.words_to_srt("hello world test", total_seconds=3.0)
    assert "hello" in srt and "-->" in srt
    cmd = pipeline.ffmpeg_command(["thumb.jpg"], "voice.mp3", "out.mp4", vertical=True)
    assert "1080:1920" in " ".join(cmd) or "1080" in " ".join(cmd)


def test_autopilot_imports():
    assert callable(autopilot.run_once)
    assert callable(autopilot.run_shorts)
    assert callable(autopilot.run_longform)
