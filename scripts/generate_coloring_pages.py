#!/usr/bin/env python3
import argparse
import base64
import os
import sys
from pathlib import Path
from typing import List
import subprocess

try:
    from openai import OpenAI
except Exception as e:  # pragma: no cover
    raise SystemExit("The 'openai' package is required. Install with: pip install -r scripts/requirements.txt") from e


def slugify(text: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"
    text = text.strip().lower().replace(" ", "-")
    return "".join(ch if ch in allowed else "-" for ch in text)


def generate_images(prompt: str, count: int, size: str, input_dir: Path) -> List[Path]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY. Set it in your environment before running.")

    client = OpenAI(api_key=api_key)
    input_dir.mkdir(parents=True, exist_ok=True)

    saved: List[Path] = []
    style_prompt = (
        "Black-and-white line art coloring page. Clean, thick outlines, no shading, no gray. "
        "High contrast, white background, centered subject, kid-friendly, printable. "
    )
    full_prompt = f"{style_prompt}{prompt}"
    slug = slugify(prompt) or "page"

    for i in range(1, count + 1):
        # Generate one image at a time for consistency
        resp = client.images.generate(
            model="gpt-image-1",
            prompt=full_prompt,
            size=size,
        )
        b64 = resp.data[0].b64_json
        img_bytes = base64.b64decode(b64)
        out_path = input_dir / f"{slug}-{i:02d}.png"
        out_path.write_bytes(img_bytes)
        print(f"✔ Generated {out_path}")
        saved.append(out_path)

    return saved


def run_postprocess(project_root: Path, output_dir: Path, resize: str, thicken: int, threshold: int) -> None:
    script = project_root / "scripts" / "process_images.py"
    cmd = [
        sys.executable,
        str(script),
        "--input",
        str(project_root / "input"),
        "--output",
        str(output_dir),
        "--resize",
        resize,
        "--thicken",
        str(thicken),
        "--threshold",
        str(threshold),
    ]
    print("→ Converting to bold, print-ready pages...")
    subprocess.run(cmd, check=False)


def main():
    ap = argparse.ArgumentParser(description="Generate line-art via OpenAI and convert to KDP-ready coloring pages")
    ap.add_argument("--prompt", required=True, help="text prompt, e.g. 'cute forest animals'")
    ap.add_argument("--count", type=int, default=10, help="number of images to generate")
    ap.add_argument("--size", default="1024x1024", help="generation size WxH, e.g. 1024x1024")
    ap.add_argument("--resize", default="2550x3300", help="final page size for processing (8.5x11 @300DPI)")
    ap.add_argument("--thicken", type=int, default=2, help="line thickening radius in pixels")
    ap.add_argument("--threshold", type=int, default=160, help="binarization threshold 0-255")
    ap.add_argument("--skip-process", action="store_true", help="only generate images, skip conversion")
    args = ap.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    input_dir = project_root / "input"
    output_dir = project_root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    generate_images(args.prompt, args.count, args.size, input_dir)

    if not args.skip_process:
        run_postprocess(project_root, output_dir, args.resize, args.thicken, args.threshold)


if __name__ == "__main__":
    main()

