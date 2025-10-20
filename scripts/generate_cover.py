#!/usr/bin/env python3
import argparse
import base64
import os
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

try:
    from openai import OpenAI
except Exception as e:  # pragma: no cover
    raise SystemExit("The 'openai' package is required. Install with: pip install -r scripts/requirements.txt") from e


TARGET_SIZE = (2560, 1600)  # width x height


def slugify(text: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"
    text = text.strip().lower().replace(" ", "-")
    return "".join(ch if ch in allowed else "-" for ch in text)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def find_font() -> Optional[str]:
    candidates = [
        # Common cross‑platform font fallbacks
        "C:/Windows/Fonts/SegoeUI-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return None


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = find_font()
    try:
        if path:
            return ImageFont.truetype(path, size=size)
        # Fallback to DejaVuSans if installed via PIL package data
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except Exception:
        return ImageFont.load_default()


def compose_cover(bg_img: Image.Image, title: str, subtitle: Optional[str], brand: str, theme_style: str, bg_mode: str, dpi: int) -> Image.Image:
    # Ensure size and mode
    bg_img = bg_img.convert("RGB")
    # Fit background image to target while preserving aspect ratio
    target_w, target_h = TARGET_SIZE
    img_ratio = bg_img.width / bg_img.height
    target_ratio = target_w / target_h
    if img_ratio > target_ratio:
        new_w = target_w
        new_h = int(new_w / img_ratio)
    else:
        new_h = target_h
        new_w = int(new_h * img_ratio)
    bg_resized = bg_img.resize((new_w, new_h), Image.LANCZOS)
    canvas_bg = (255, 255, 255) if bg_mode == "light" else (20, 24, 32)
    canvas = Image.new("RGB", TARGET_SIZE, color=canvas_bg)
    x = (target_w - new_w) // 2
    y = (target_h - new_h) // 2
    canvas.paste(bg_resized, (x, y))

    # Overlay a subtle dark/light vignette for readability (top area)
    overlay = Image.new("RGBA", TARGET_SIZE, (0, 0, 0, 0))
    draw_o = ImageDraw.Draw(overlay)
    if bg_mode == "light":
        draw_o.rectangle([0, 0, target_w, int(target_h * 0.35)], fill=(255, 255, 255, 90))
    else:
        draw_o.rectangle([0, 0, target_w, int(target_h * 0.35)], fill=(0, 0, 0, 110))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")

    # Text colors
    fg = (20, 24, 32) if bg_mode == "light" else (245, 247, 250)
    shadow = (0, 0, 0) if bg_mode == "light" else (0, 0, 0)

    draw = ImageDraw.Draw(canvas)

    # Title sizing
    title_font_size = 140
    font = load_font(title_font_size)
    max_width = int(TARGET_SIZE[0] * 0.88)

    def shrink_to_fit(text: str, size: int, min_size: int = 64) -> ImageFont.ImageFont:
        s = size
        while s >= min_size:
            f = load_font(s)
            bbox = draw.textbbox((0, 0), text, font=f)
            if bbox[2] - bbox[0] <= max_width:
                return f
            s -= 6
        return load_font(min_size)

    title_font = shrink_to_fit(title, title_font_size)
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]
    title_x = (TARGET_SIZE[0] - title_w) // 2
    title_y = int(TARGET_SIZE[1] * 0.10)

    # Draw shadow
    for dx, dy in [(2, 2), (0, 0)]:
        color = shadow if (dx,dy)!=(0,0) else fg
        draw.text((title_x + dx, title_y + dy), title, font=title_font, fill=color)

    # Subtitle
    if subtitle:
        sub_font = load_font(max(48, int(title_font.size * 0.4)))
        sub_bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
        sub_w = sub_bbox[2] - sub_bbox[0]
        sub_h = sub_bbox[3] - sub_bbox[1]
        sub_x = (TARGET_SIZE[0] - sub_w) // 2
        sub_y = title_y + title_h + 20
        for dx, dy in [(1, 1), (0, 0)]:
            color = shadow if (dx,dy)!=(0,0) else fg
            draw.text((sub_x + dx, sub_y + dy), subtitle, font=sub_font, fill=color)

    # Brand footer
    brand_text = theme_style + (f" • {brand}" if brand else "")
    brand_font = load_font(50)
    b_bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
    b_w = b_bbox[2] - b_bbox[0]
    b_h = b_bbox[3] - b_bbox[1]
    b_x = (TARGET_SIZE[0] - b_w) // 2
    b_y = TARGET_SIZE[1] - b_h - 40
    draw.text((b_x + 1, b_y + 1), brand_text, font=brand_font, fill=shadow)
    draw.text((b_x, b_y), brand_text, font=brand_font, fill=fg)

    return canvas


def main():
    ap = argparse.ArgumentParser(description="Generate a KDP cover image with OpenAI + Pillow text overlay")
    ap.add_argument("--title", required=True, help="book title text")
    ap.add_argument("--subtitle", help="optional subtitle text")
    ap.add_argument("--theme", required=True, help="visual theme prompt for background image")
    ap.add_argument("--brand", default="Coloring Explorers", help="brand or series name")
    ap.add_argument("--bg", choices=["light", "dark"], default="light", help="overall background brightness")
    ap.add_argument("--style", choices=["playful", "elegant", "cute"], default="playful", help="design style")
    ap.add_argument("--dpi", type=int, default=300, help="DPI metadata for saved PNG")
    ap.add_argument("--preview", action="store_true", help="show a preview window before saving")
    args = ap.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY. Set it in your environment before running.")

    client = OpenAI(api_key=api_key)

    style_words = {
        "playful": "playful, friendly, vibrant composition",
        "elegant": "minimal, tasteful, refined composition",
        "cute": "cute, friendly, kid-appeal composition",
    }[args.style]
    bg_phrase = "light background" if args.bg == "light" else "dark background"

    # Prompt for background art; ask for clean area for title
    prompt = (
        f"Front book cover background art, {TARGET_SIZE[0]}x{TARGET_SIZE[1]} px. "
        f"Children's coloring book. {style_words}. {bg_phrase}. "
        f"Leave clean space for title. Avoid any text or watermarks. "
        f"Theme: {args.theme}."
    )

    resp = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size=f"{TARGET_SIZE[0]}x{TARGET_SIZE[1]}",
    )
    b64 = resp.data[0].b64_json
    img_bytes = base64.b64decode(b64)
    from io import BytesIO
    bg_img = Image.open(BytesIO(img_bytes))

    composed = compose_cover(bg_img, args.title, args.subtitle, args.brand, args.style, args.bg, args.dpi)

    if args.preview:
        try:
            composed.resize((int(TARGET_SIZE[0] / 3), int(TARGET_SIZE[1] / 3))).show()
        except Exception:
            pass

    out_dir = Path(__file__).resolve().parents[1] / "exports" / "covers"
    ensure_dir(out_dir)
    slug = slugify(args.title or args.theme) or "cover"
    out_path = out_dir / f"{slug}-cover.png"
    composed.save(out_path, format="PNG", dpi=(args.dpi, args.dpi))
    print(f"✔ Saved cover: {out_path}")


if __name__ == "__main__":
    main()

