"""Zero-API-key production pipeline.

Research / hooks / scripts / SEO: Pollinations Text API (key-free).
Thumbnails & visuals: Pollinations Image API + Wikimedia / Openverse
public stock (no key). Voiceover: edge-tts (en-US-ChristopherNeural /
en-US-AriaNeural). Video: FFmpeg notes/commands, 9:16 Shorts (55s)
and 16:9 long-form (6-8 min), karaoke-style word captions (SRT/ASS).
Upload: videos().insert() + playlistItems().insert() routing.

Dry-run works with no YouTube auth and no network (falls back to
local templates / Pillow placeholders).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, urlencode

try:
    import requests
except ImportError:
    requests = None

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
OUTPUT = ROOT / "output"
POLLINATIONS_TEXT = os.environ.get("POLLINATIONS_TEXT_URL", "https://text.pollinations.ai/")
POLLINATIONS_IMAGE = os.environ.get("POLLINATIONS_IMAGE_URL", "https://image.pollinations.ai/prompt/")
VOICES = {"male": "en-US-ChristopherNeural", "female": "en-US-AriaNeural"}


# --- Research / script -------------------------------------------------------
def pollinations_text(prompt: str, timeout: int = 60) -> str | None:
    """Key-free Pollinations Text API. Returns None on failure."""
    if requests is None:
        return None
    try:
        r = requests.get(POLLINATIONS_TEXT + quote(prompt), timeout=timeout)
        if r.status_code == 200 and r.text.strip():
            return r.text.strip()
    except Exception as e:
        print(f"[pipeline] Pollinations text failed: {e}", file=sys.stderr)
    return None


def generate_hooks(topic: str, hook_styles: list[str], n: int = 5) -> list[str]:
    prompt = (f"Write {n} viral YouTube hooks for a video about '{topic}'. "
              f"Use these styles: {', '.join(hook_styles)}. "
              "One hook per line, punchy, under 15 words each, no numbering.")
    text = pollinations_text(prompt)
    if text:
        hooks = [re.sub(r"^\d+[\.\)]\s*", "", ln).strip()
                 for ln in text.splitlines() if ln.strip()]
        return hooks[:n] or [text]
    return [f"{style}: {topic}" for style in hook_styles[:n]]


def generate_script(topic: str, niche: str, duration: str = "short") -> str:
    """Generate a script. Short = ~55s (~130 words), long = 6-8 min (~900 words)."""
    target = "about 130 words, 55 seconds spoken" if duration == "short" \
        else "about 900 words, 6-8 minutes spoken"
    prompt = (f"Write a YouTube {duration} video script about '{topic}' "
              f"for a {niche} channel. {target}. "
              "Start with a strong hook, use short sentences, add a clear call to action "
              "to subscribe. Plain text, no stage directions.")
    text = pollinations_text(prompt)
    if text:
        return text
    return (f"Hook: {topic} — here's what nobody tells you.\n\n"
            f"In this video we break down {topic} step by step, "
            f"with real examples you can use today.\n\n"
            f"Subscribe for more {niche} videos every week.")


def generate_seo(topic: str, niche_cfg: dict, duration: str = "short") -> dict:
    keywords = niche_cfg.get("keywords", [])[:8]
    title = f"{topic} — {niche_cfg.get('display_name', niche_cfg)}" if duration == "long" \
        else f"{topic} (In 60 Seconds!)"
    return {
        "title": title[:100],
        "description": (f"{topic} explained simply. "
                        f"Subscribe for daily {niche_cfg.get('display_name', '')} videos.\n\n"
                        f"Keywords: {', '.join(keywords)}"),
        "tags": [topic.lower(), niche_cfg.get("display_name", "").lower()] + keywords[:10],
        "category_id": "27" if duration == "long" else "24",
    }


# --- Visuals -----------------------------------------------------------------
def generate_thumbnail(prompt: str, out: Path, width: int = 1280, height: int = 720) -> Path:
    """Pollinations image -> file, Pillow fallback on failure."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if requests is not None:
        try:
            url = (f"{POLLINATIONS_IMAGE}{quote(prompt)}"
                   f"?width={width}&height={height}&nologo=true&model=flux")
            r = requests.get(url, timeout=60)
            if r.status_code == 200 and r.content:
                out.write_bytes(r.content)
                return out
        except Exception as e:
            print(f"[pipeline] Thumbnail fetch failed: {e}", file=sys.stderr)
    # Pillow fallback: bold high-contrast placeholder
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (width, height), (11, 18, 32))
    d = ImageDraw.Draw(img)
    d.rectangle([0, height - 160, width, height], fill=(245, 158, 11))
    d.text((40, height // 2 - 40), prompt[:40].upper(), fill=(255, 255, 255))
    img.save(out)
    return out


def search_stock(query: str, source: str = "openverse") -> list[str]:
    """Return stock-footage search URLs (no API key). Callers fetch/choose."""
    if source == "wikimedia":
        return ["https://commons.wikimedia.org/w/api.php?" + urlencode({
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": f"filetype:video {query}", "gsrlimit": "10",
            "prop": "imageinfo", "iiprop": "url"})]
    return ["https://api.openverse.org/v1/images/?" + urlencode({"q": query, "page_size": "10"})]


# --- Voiceover ---------------------------------------------------------------
async def _tts_async(text: str, voice: str, out: Path):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out))


def generate_voiceover(text: str, voice: str = VOICES["male"], out: Path | None = None) -> Path:
    """edge-tts voiceover. Raises if edge-tts is not installed."""
    out = out or (ASSETS / "voiceover.mp3")
    out.parent.mkdir(parents=True, exist_ok=True)
    import asyncio
    asyncio.run(_tts_async(text, voice, out))
    return out


# --- Captions (karaoke-style word-by-word) -----------------------------------
def words_to_srt(text: str, total_seconds: float = 55.0) -> str:
    """Rough word-timed SRT: words spread evenly across the duration."""
    words = text.split()
    if not words:
        return ""
    per = total_seconds / len(words)
    def ts(s: float) -> str:
        h, m = int(s // 3600), int((s % 3600) // 60)
        sec = s % 60
        return f"{h:02d}:{m:02d}:{sec:05.2f}".replace(".", ",")
    lines = []
    for i, w in enumerate(words):
        start, end = i * per, (i + 1) * per
        lines.append(f"{i+1}\n{ts(start)} --> {ts(end)}\n{w}\n")
    return "\n".join(lines)


def write_captions(text: str, out: Path, total_seconds: float = 55.0) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(words_to_srt(text, total_seconds), encoding="utf-8")
    return out


# --- Video assembly (FFmpeg) -------------------------------------------------
def ffmpeg_command(images: list[str], audio: str, out: str,
                   vertical: bool = True, duration: int = 55) -> list[str]:
    """Build the FFmpeg command for a slideshow-style video with zoompan.

    Vertical Shorts: 1080x1920, 55s. Long-form: 1920x1080, 6-8 min.
    Real rendering needs FFmpeg installed (see README / GitHub Actions).
    """
    w, h = (1080, 1920) if vertical else (1920, 1080)
    # zoompan on a single image + audio, 3s scene cuts are achieved by
    # concatenating per-image segments in the full autopilot render step.
    return ["ffmpeg", "-y", "-loop", "1", "-i", images[0], "-i", audio,
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                   f"crop={w}:{h},zoompan=z='min(zoom+0.0015,1.5)':d={duration*30}:s={w}x{h}",
            "-c:v", "libx264", "-t", str(duration), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", out]


def check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


# --- Upload ------------------------------------------------------------------
def upload_video(youtube, file_path: str, seo: dict, playlist_id: str | None = None,
                 dry_run: bool = False) -> dict:
    planned = {"videos.insert": {"file": file_path, "title": seo["title"],
                                 "description": seo["description"], "tags": seo["tags"],
                                 "privacyStatus": "public"},
               "playlistItems.insert": {"playlistId": playlist_id} if playlist_id else None}
    if dry_run:
        print(json.dumps(planned, indent=2))
        return {"dry_run": True, "planned": planned, "video_id": "dry-run-video-id"}
    if youtube is None:
        raise RuntimeError("No authenticated YouTube service.")
    from googleapiclient.http import MediaFileUpload
    body = {"snippet": {"title": seo["title"], "description": seo["description"],
                        "tags": seo["tags"], "categoryId": seo.get("category_id", "27")},
            "status": {"privacyStatus": "public"}}
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    res = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    video_id = res["id"]
    if playlist_id:
        youtube.playlistItems().insert(
            part="snippet",
            body={"snippet": {"playlistId": playlist_id,
                              "resourceId": {"kind": "youtube#video", "videoId": video_id}}}).execute()
    return {"dry_run": False, "video_id": video_id}


def route_to_playlist(niche_cfg: dict, duration: str) -> dict:
    """Pick the matching playlist for a new video (by duration/format)."""
    playlists = niche_cfg.get("playlists", [])
    want = "Shorts" if duration == "short" else "Documentaries"
    for p in playlists:
        if want.lower() in p["title"].lower():
            return p
    return playlists[0] if playlists else {}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Zero-API-key production pipeline")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--topic", default="7 Index Funds That Beat the Market")
    ap.add_argument("--niche", default="finance")
    args = ap.parse_args(argv)

    from channel_customizer import load_niche
    cfg = load_niche(args.niche)
    print(f"[pipeline] topic={args.topic!r} niche={args.niche} ffmpeg={'yes' if check_ffmpeg() else 'no (install ffmpeg to render)'}")
    hooks = generate_hooks(args.topic, cfg["hook_styles"])
    print("[pipeline] hooks:")
    for h in hooks:
        print(f"  - {h}")
    script = generate_script(args.topic, args.niche, "short")
    print(f"[pipeline] script ({len(script)} chars): {script[:200]}...")
    seo = generate_seo(args.topic, cfg, "short")
    print(f"[pipeline] SEO title: {seo['title']}")
    thumb = generate_thumbnail(f"{args.topic}, bold YouTube thumbnail, high contrast",
                               ASSETS / "thumbnail.jpg")
    print(f"[pipeline] thumbnail: {thumb}")
    caps = write_captions(script, ASSETS / "captions.srt", total_seconds=55)
    print(f"[pipeline] captions: {caps}")
    print(f"[pipeline] stock search: {search_stock(args.topic)}")
    print(f"[pipeline] ffmpeg cmd: {' '.join(ffmpeg_command([str(thumb)], 'assets/voiceover.mp3', 'output/short.mp4'))}")
    if args.dry_run:
        upload_video(None, "output/short.mp4", seo,
                     playlist_id="dry-run-playlist", dry_run=True)
    print("[pipeline] DRY RUN OK — no YouTube upload, no voiceover rendered (needs edge-tts + network).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
