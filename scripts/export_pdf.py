#!/usr/bin/env python3
import argparse
import json
import random
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from PIL import Image


def parse_size(value: str) -> Tuple[int, int]:
    w, h = value.lower().split("x")
    return int(w), int(h)


def page_pixels(paper: str, dpi: int, bleed: str) -> Tuple[int, int]:
    if paper not in {"letter", "a4"}:
        raise ValueError("paper must be 'letter' or 'a4'")
    if bleed not in {"none", "3mm"}:
        raise ValueError("bleed must be 'none' or '3mm'")

    if paper == "letter":
        width_in, height_in = 8.5, 11.0
    else:  # a4
        width_in, height_in = 8.27, 11.69

    # Optional bleed: add 3mm (~0.1181 in) on each side
    if bleed == "3mm":
        bleed_in = 0.11811
        width_in += 2 * bleed_in
        height_in += 2 * bleed_in

    return int(round(width_in * dpi)), int(round(height_in * dpi))


def fit_canvas(img: Image.Image, size: Tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    # Preserve aspect ratio, then paste onto white canvas
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h
    if img_ratio > target_ratio:
        new_w = target_w
        new_h = int(new_w / img_ratio)
    else:
        new_h = target_h
        new_w = int(new_h * img_ratio)
    img_resized = img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("L", (target_w, target_h), color=255)  # white background
    x = (target_w - new_w) // 2
    y = (target_h - new_h) // 2
    canvas.paste(img_resized, (x, y))
    return canvas


def select_images(folder: Path, shuffle: bool, count: int | None) -> List[Path]:
    exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    imgs = sorted([p for p in folder.iterdir() if p.suffix.lower() in exts])
    if shuffle:
        random.shuffle(imgs)
    if count is not None:
        imgs = imgs[:count]
    return imgs


def export_pdf(images: List[Path], pdf_path: Path, dpi: int, paper: str, bleed: str) -> None:
    w, h = page_pixels(paper, dpi, bleed)
    pages: List[Image.Image] = []
    for p in images:
        with Image.open(p) as im:
            im = im.convert("L")
            page = fit_canvas(im, (w, h))
            pages.append(page)

    if not pages:
        raise ValueError("No input images to export")

    first, rest = pages[0], pages[1:]
    # resolution sets PDF DPI so physical page size matches
    first.save(pdf_path, save_all=True, append_images=rest, resolution=dpi)


def write_manifest(dest: Path, *, images: List[Path], pdf_path: Path, paper: str, dpi: int, bleed: str) -> Path:
    manifest = {
        "created_at": datetime.utcnow().isoformat() + "Z",
        "paper": paper,
        "dpi": dpi,
        "bleed": bleed,
        "page_count": len(images),
        "output_pdf": str(pdf_path.name),
        "images": [str(p.name) for p in images],
    }
    with dest.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return dest


def main():
    ap = argparse.ArgumentParser(description="Combine images into a print-ready PDF for KDP")
    ap.add_argument("--input", default="output", help="folder with processed images")
    ap.add_argument("--paper", choices=["letter", "a4"], default="letter", help="page size")
    ap.add_argument("--dpi", type=int, default=300, help="PDF resolution (DPI)")
    ap.add_argument("--bleed", choices=["none", "3mm"], default="none", help="add 3mm bleed on all sides")
    ap.add_argument("--shuffle", action="store_true", help="shuffle page order")
    ap.add_argument("--count", type=int, help="limit number of pages included")
    ap.add_argument("--output", default=None, help="output PDF path (defaults to exports/book-<paper>-<timestamp>.pdf)")
    args = ap.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    input_dir = (project_root / args.input).resolve()
    exports_dir = (project_root / "exports").resolve()
    logs_dir = (project_root / "logs").resolve()
    exports_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    images = select_images(input_dir, shuffle=bool(args.shuffle), count=args.count)
    if not images:
        raise SystemExit(f"No images found in {input_dir}")

    # Validate page count (30–120)
    page_count = len(images)
    if page_count < 30 or page_count > 120:
        raise SystemExit(f"Page count must be between 30 and 120; got {page_count}")

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    pdf_path = Path(args.output) if args.output else exports_dir / f"book-{args.paper}-{ts}.pdf"

    export_pdf(images, pdf_path, dpi=args.dpi, paper=args.paper, bleed=args.bleed)

    manifest_path = logs_dir / f"export-{ts}.json"
    write_manifest(manifest_path, images=images, pdf_path=pdf_path, paper=args.paper, dpi=args.dpi, bleed=args.bleed)

    print(f"✔ Exported PDF: {pdf_path}")
    print(f"✔ Manifest: {manifest_path}")


if __name__ == "__main__":
    main()

