#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image, ImageFilter


def parse_size(value: str) -> Tuple[int, int]:
    w, h = value.lower().split("x")
    return int(w), int(h)


def trim_white_margins(img: Image.Image, threshold: int = 250, margin: int = 0) -> Image.Image:
    # Works on L or RGB; convert to L for simplicity
    gray = img.convert("L")
    arr = np.array(gray)
    mask = arr < threshold  # True where content is not white
    if not mask.any():
        return img
    ys, xs = np.where(mask)
    y0, y1 = max(0, ys.min() - margin), min(arr.shape[0], ys.max() + 1 + margin)
    x0, x1 = max(0, xs.min() - margin), min(arr.shape[1], xs.max() + 1 + margin)
    return img.crop((x0, y0, x1, y1))


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


def thicken(binary: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return binary
    # Simple morphological dilation using maximum filter via convolution-like pad/slide
    # Create a square structuring element of size (2*radius+1)
    k = 2 * radius + 1
    pad = radius
    padded = np.pad(binary, pad_width=pad, mode="edge")
    out = np.zeros_like(binary)
    for dy in range(k):
        for dx in range(k):
            window = padded[dy:dy + binary.shape[0], dx:dx + binary.shape[1]]
            out = np.maximum(out, window)
    return out


def to_coloring(img: Image.Image, threshold: int, thicken_radius: int) -> Image.Image:
    # Grayscale
    gray = img.convert("L")
    # Edge detection
    edges = gray.filter(ImageFilter.FIND_EDGES)
    arr = np.array(edges, dtype=np.uint8)
    # Normalize and binarize (black lines on white)
    arr = 255 - arr  # invert: lines become dark
    bin_arr = (arr < threshold).astype(np.uint8) * 255
    # Thicken lines
    if thicken_radius > 0:
        bin_norm = (bin_arr // 255).astype(np.uint8)
        thick = thicken(bin_norm, thicken_radius) * 255
        bin_arr = thick.astype(np.uint8)
    return Image.fromarray(bin_arr, mode="L")


def process_file(src: Path, dst_dir: Path, resize: Tuple[int, int], threshold: int, thicken_radius: int, *, dpi: int = 300, trim_margins: bool = False):
    try:
        with Image.open(src) as im:
            im = im.convert("RGB")
            if trim_margins:
                im = trim_white_margins(im)
            fitted = fit_canvas(im, resize)
            out_img = to_coloring(fitted, threshold=threshold, thicken_radius=thicken_radius)
            dst = dst_dir / (src.stem + "_coloring.png")
            out_img.save(dst, format="PNG", dpi=(dpi, dpi))
            print(f"✔ Wrote {dst}")
    except Exception as e:
        print(f"✖ Failed {src}: {e}")


def main():
    ap = argparse.ArgumentParser(description="Convert images to bold coloring pages")
    ap.add_argument("--input", default="input", help="input folder")
    ap.add_argument("--output", default="output", help="output folder")
    ap.add_argument("--resize", default="2550x3300", help="WxH in pixels (e.g., 2550x3300 for 8.5x11 @ 300DPI)")
    ap.add_argument("--threshold", type=int, default=160, help="binarization threshold 0-255")
    ap.add_argument("--thicken", type=int, default=2, help="line thickening radius in pixels (0 to disable)")
    ap.add_argument("--dpi", type=int, default=300, help="output DPI for saved PNGs")
    ap.add_argument("--trim-margins", action="store_true", help="auto-trim white margins before resize")
    args = ap.parse_args()

    in_dir = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    size = parse_size(args.resize)

    exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    files = [p for p in in_dir.iterdir() if p.suffix.lower() in exts]
    if not files:
        print(f"No images found in {in_dir}. Supported: {sorted(exts)}")
        return
    for f in files:
        process_file(f, out_dir, size, args.threshold, args.thicken, dpi=args.dpi, trim_margins=args.trim_margins)


if __name__ == "__main__":
    main()
