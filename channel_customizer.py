"""Channel customizer — 1-click YouTube channel branding.

Turns a blank/new channel into a branded USA media brand:
identity -> logo/banner (Pollinations + Pillow) -> channels().update()
(country=US, defaultLanguage=en, keywords, description)
-> channelBanners().insert() -> playlists().insert() x3.

No hardcoded credentials. All YouTube auth comes from auth.py / env.
Dry-run prints planned API calls and generates images locally
(Pillow fallback if Pollinations is unreachable).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    Image = None  # type: ignore

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config" / "niches.json"
ASSETS = ROOT / "assets"
LOGO_SIZE = (800, 800)
BANNER_SIZE = (2560, 1440)
# YouTube safe area: 1546 x 423 centred (visible on all devices)
SAFE_W, SAFE_H = 1546, 423


def load_niche(niche: str) -> dict:
    """Load one niche definition from config/niches.json."""
    with open(CONFIG, encoding="utf-8") as f:
        data = json.load(f)
    key = niche.strip().lower().replace(" ", "_").replace("-", "_")
    # Allow display-name lookup too, e.g. "Tech & AI" -> tech_ai
    if key not in data:
        for k, v in data.items():
            if v.get("display_name", "").lower() == niche.strip().lower():
                return v
        raise ValueError(f"Unknown niche '{niche}'. Available: {sorted(data)}")
    return data[key]


def list_niches() -> list[str]:
    with open(CONFIG, encoding="utf-8") as f:
        return sorted(json.load(f))


def generate_identity(niche: str, seed: int | None = None) -> dict:
    """Suggest brand name, handle and palette for a niche."""
    cfg = load_niche(niche)
    rng = random.Random(seed) if seed is not None else random
    name = rng.choice(cfg["brand_name_ideas"])
    handle = rng.choice(cfg["handle_ideas"])
    return {
        "niche": niche,
        "brand_name": name,
        "handle": handle,
        "palette": cfg["color_palette"],
        "keywords": cfg["keywords"],
        "description": cfg["description_template"].format(brand=name),
        "playlists": cfg["playlists"],
        "hook_styles": cfg["hook_styles"],
        "sub_topics": cfg["sub_topics"],
    }


def _hex_to_rgb(hexstr: str) -> tuple[int, int, int]:
    h = hexstr.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _font(size: int):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(path):
            try:
                from PIL import ImageFont
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    from PIL import ImageFont
    return ImageFont.load_default()


def _pillow_logo(brand: str, palette: dict, out: Path) -> Path:
    img = Image.new("RGB", LOGO_SIZE, _hex_to_rgb(palette["primary"]))
    d = ImageDraw.Draw(img)
    # accent ring / circle
    d.ellipse([120, 120, 680, 680], outline=_hex_to_rgb(palette["accent"]), width=18)
    d.ellipse([300, 300, 500, 500], fill=_hex_to_rgb(palette["accent"]))
    initials = "".join(w[0] for w in brand.split() if w).upper()[:2]
    f = _font(180)
    bbox = d.textbbox((0, 0), initials, font=f)
    d.text(((800 - (bbox[2] - bbox[0])) / 2 - bbox[0], 300),
           initials, font=f, fill=_hex_to_rgb(palette["text"]))
    f2 = _font(52)
    bbox2 = d.textbbox((0, 0), brand, font=f2)
    d.text(((800 - (bbox2[2] - bbox2[0])) / 2 - bbox2[0], 560),
           brand, font=f2, fill=_hex_to_rgb(palette["text"]))
    img.save(out)
    return out


def _pillow_banner(brand: str, palette: dict, niche: str, out: Path) -> Path:
    img = Image.new("RGB", BANNER_SIZE, _hex_to_rgb(palette["primary"]))
    d = ImageDraw.Draw(img)
    # subtle accent band
    d.rectangle([0, 1080, 2560, 1120], fill=_hex_to_rgb(palette["accent"]))
    # safe-zone guide (dashed-ish rectangle, for the creator's reference;
    # the centred text itself is inside the safe area)
    sx, sy = (2560 - SAFE_W) // 2, (1440 - SAFE_H) // 2
    d.rectangle([sx, sy, sx + SAFE_W, sy + SAFE_H],
                outline=_hex_to_rgb(palette["accent"]), width=4)
    f = _font(150)
    bbox = d.textbbox((0, 0), brand, font=f)
    d.text(((2560 - (bbox[2] - bbox[0])) / 2 - bbox[0], sy + 90),
           brand, font=f, fill=_hex_to_rgb(palette["text"]))
    f2 = _font(56)
    tag = load_niche(niche).get("display_name", niche).upper() + "  •  NEW VIDEOS EVERY WEEK"
    bbox2 = d.textbbox((0, 0), tag, font=f2)
    d.text(((2560 - (bbox2[2] - bbox2[0])) / 2 - bbox2[0], sy + 280),
           tag, font=f2, fill=_hex_to_rgb(palette["accent"]))
    img.save(out)
    return out


def _pollinations_image(prompt: str, width: int, height: int, out: Path) -> bool:
    """Try Pollinations (key-free). Return False on any failure."""
    if requests is None:
        return False
    try:
        from urllib.parse import quote
        url = (f"https://image.pollinations.ai/prompt/{quote(prompt)}"
               f"?width={width}&height={height}&nologo=true&model=flux")
        r = requests.get(url, timeout=60)
        if r.status_code == 200 and r.content:
            out.write_bytes(r.content)
            # verify it is a real image
            with Image.open(out) as im:
                im.verify()
            return True
    except Exception as e:
        print(f"[customizer] Pollinations image failed ({e}); Pillow fallback.", file=sys.stderr)
    return False


def generate_logo_and_banner(brand_name: str, palette: dict, niche: str,
                             use_pollinations: bool = True) -> dict:
    """Generate 800x800 logo + 2560x1440 banner into assets/. Returns paths."""
    if Image is None:
        raise RuntimeError("Pillow is required (pip install -r requirements.txt)")
    ASSETS.mkdir(exist_ok=True)
    logo_path = ASSETS / "logo.png"
    banner_path = ASSETS / "banner.png"
    logo_ok = False
    if use_pollinations:
        logo_ok = _pollinations_image(
            f"minimal flat vector logo for a YouTube channel called {brand_name}, "
            f"{niche} niche, {palette['accent']} accent on dark background, centred, no text",
            800, 800, logo_path)
    if not logo_ok:
        _pillow_logo(brand_name, palette, logo_path)
    banner_ok = False
    if use_pollinations:
        banner_ok = _pollinations_image(
            f"wide YouTube channel banner for {brand_name}, {niche} niche, "
            f"cinematic dark background, centred title space, no text",
            2560, 1440, banner_path)
    if not banner_ok:
        _pillow_banner(brand_name, palette, niche, banner_path)
    else:
        # Overlay centred brand text inside the safe zone on the AI banner.
        with Image.open(banner_path).convert("RGB") as im:
            im = im.resize(BANNER_SIZE)
            d = ImageDraw.Draw(im)
            sx, sy = (2560 - SAFE_W) // 2, (1440 - SAFE_H) // 2
            f = _font(150)
            bbox = d.textbbox((0, 0), brand_name, font=f)
            # dark scrim behind text for legibility
            d.rectangle([sx, sy + 70, sx + SAFE_W, sy + 360], fill=(0, 0, 0))
            d.text(((2560 - (bbox[2] - bbox[0])) / 2 - bbox[0], sy + 90),
                   brand_name, font=f, fill=(255, 255, 255))
            im.save(banner_path)
    return {"logo": str(logo_path), "banner": str(banner_path),
            "logo_size": LOGO_SIZE, "banner_size": BANNER_SIZE,
            "safe_zone": (SAFE_W, SAFE_H)}


def customize_channel(youtube_service, niche: str, brand: dict,
                      banner_path: str | None = None, dry_run: bool = False) -> dict:
    """Apply branding via YouTube Data API v3. Dry-run only prints the calls."""
    cfg = load_niche(niche)
    description = cfg["description_template"].format(brand=brand["brand_name"])
    channel_body = {
        "id": os.environ.get("CHANNEL_ID", "<CHANNEL_ID>"),
        "brandingSettings": {
            "channel": {
                "country": "US",
                "defaultLanguage": "en",
                "keywords": ", ".join(cfg["keywords"]),
                "description": description,
                "title": brand["brand_name"],
            }
        },
    }
    planned = {
        "channels.update": channel_body,
        "channelBanners.insert": {"banner_path": banner_path or "assets/banner.png",
                                  "channelId": os.environ.get("CHANNEL_ID", "<CHANNEL_ID>")},
        "playlists.insert": [
            {"snippet": {"title": p["title"], "description": p["description"],
                         "tags": p.get("tags", []), "defaultLanguage": "en"},
             "status": {"privacyStatus": "public"}}
            for p in cfg["playlists"]
        ],
    }
    if dry_run:
        print(json.dumps(planned, indent=2))
        return {"dry_run": True, "planned": planned}
    if youtube_service is None:
        raise RuntimeError("No authenticated YouTube service. Run auth.py first.")
    # 1) Channel metadata / USA SEO
    youtube_service.channels().update(part="brandingSettings", body=channel_body).execute()
    # 2) Banner upload
    if banner_path:
        from googleapiclient.http import MediaFileUpload
        media = MediaFileUpload(banner_path, mimetype="image/png")
        youtube_service.channelBanners().insert(
            media_body=media,
            channelId=os.environ.get("CHANNEL_ID")).execute()
    # 3) Playlists
    created = []
    for p in cfg["playlists"]:
        res = youtube_service.playlists().insert(
            part="snippet,status",
            body={"snippet": {"title": p["title"], "description": p["description"],
                             "tags": p.get("tags", []), "defaultLanguage": "en"},
                  "status": {"privacyStatus": "public"}}).execute()
        created.append(res.get("id"))
    return {"dry_run": False, "planned": planned, "playlist_ids": created}


def main(argv=None):
    ap = argparse.ArgumentParser(description="1-click YouTube channel customizer")
    ap.add_argument("--niche", default=os.environ.get("NICHE", "finance"))
    ap.add_argument("--brand", default=None, help="Brand name override")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-pollinations", action="store_true")
    args = ap.parse_args(argv)

    identity = generate_identity(args.niche)
    if args.brand:
        identity["brand_name"] = args.brand
        identity["description"] = load_niche(args.niche)["description_template"].format(brand=args.brand)
    print(f"Brand: {identity['brand_name']}  Handle: {identity['handle']}")
    print(f"Palette: {identity['palette']}")
    print(f"Keywords ({len(identity['keywords'])}): {', '.join(identity['keywords'])}")

    assets = generate_logo_and_banner(identity["brand_name"], identity["palette"],
                                      args.niche, use_pollinations=not args.no_pollinations)
    print(f"Logo: {assets['logo']} {assets['logo_size']}")
    print(f"Banner: {assets['banner']} {assets['banner_size']} "
          f"safe zone {assets['safe_zone'][0]}x{assets['safe_zone'][1]} centred")

    if args.dry_run:
        print("\n[DRY RUN] Planned YouTube API calls (no auth, no upload):")
        customize_channel(None, args.niche, identity,
                          banner_path=assets["banner"], dry_run=True)
        return 0

    from auth import get_authenticated_service
    yt = get_authenticated_service()
    result = customize_channel(yt, args.niche, identity,
                               banner_path=assets["banner"], dry_run=False)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
