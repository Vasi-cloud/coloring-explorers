#!/usr/bin/env python3
import argparse
import base64
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import subprocess

try:
    from openai import OpenAI
except Exception as e:  # pragma: no cover
    raise SystemExit("The 'openai' package is required. Install with: pip install -r scripts/requirements.txt") from e

try:
    from tqdm import tqdm
except Exception as e:  # pragma: no cover
    raise SystemExit("The 'tqdm' package is required. Install with: pip install -r scripts/requirements.txt") from e


def slugify(text: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"
    text = text.strip().lower().replace(" ", "-")
    return "".join(ch if ch in allowed else "-" for ch in text)


def ensure_logs_dir(project_root: Path) -> Path:
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def log_error(logfile: Path, message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logfile.parent.mkdir(parents=True, exist_ok=True)
    with logfile.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def backoff_sleep(attempt: int) -> None:
    # attempt: 1..N
    delay = 2 ** (attempt - 1)  # 1, 2, 4 ... seconds
    time.sleep(delay)


def generate_one(client: OpenAI, full_prompt: str, size: str, out_path: Path, logfile: Path) -> bool:
    tries = 3
    for attempt in range(1, tries + 1):
        try:
            resp = client.images.generate(
                model="gpt-image-1",
                prompt=full_prompt,
                size=size,
            )
            b64 = resp.data[0].b64_json
            img_bytes = base64.b64decode(b64)
            out_path.write_bytes(img_bytes)
            return True
        except Exception as e:  # pragma: no cover (network)
            log_error(logfile, f"generate failed ({out_path.name}) attempt {attempt}: {e}")
            if attempt < tries:
                backoff_sleep(attempt)
            else:
                return False


def generate_images(prompt: str, count: int, size: str, input_dir: Path, max_workers: int, logfile: Path) -> Tuple[List[Path], List[str]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY. Set it in your environment before running.")

    client = OpenAI(api_key=api_key)
    input_dir.mkdir(parents=True, exist_ok=True)

    saved: List[Path] = []
    failed: List[str] = []
    style_prompt = (
        "Black-and-white line art coloring page. Clean, thick outlines, no shading, no gray. "
        "High contrast, white background, centered subject, kid-friendly, printable. "
    )
    full_prompt = f"{style_prompt}{prompt}"
    slug = slugify(prompt) or "page"

    tasks = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for i in range(1, count + 1):
            out_path = input_dir / f"{slug}-{i:02d}.png"
            fut = pool.submit(generate_one, client, full_prompt, size, out_path, logfile)
            tasks.append((i, out_path, fut))

        for i, out_path, fut in tqdm(tasks, desc="Generating", unit="img"):
            ok = fut.result()
            if ok:
                saved.append(out_path)
            else:
                failed.append(out_path.name)

    return saved, failed


def run_postprocess_parallel(project_root: Path, files: List[Path], output_dir: Path, resize: str, thicken: int, threshold: int, dpi: int, trim_margins: bool, max_workers: int, logfile: Path) -> Tuple[int, List[str]]:
    sys.path.append(str(project_root / "scripts"))
    try:
        import process_images as proc
    except Exception as e:
        log_error(logfile, f"failed to import process_images: {e}")
        return 0, [f"import_error: {e}"]

    processed = 0
    failures: List[str] = []

    def _wrap(f: Path) -> bool:
        try:
            proc.process_file(f, output_dir, parse_size(resize), threshold, thicken, dpi=dpi, trim_margins=trim_margins)
            return True
        except Exception as e:  # pragma: no cover
            log_error(logfile, f"process failed ({f.name}): {e}")
            return False

    # local copy of parse_size to avoid circular import
    def parse_size(value: str) -> Tuple[int, int]:
        w, h = value.lower().split("x")
        return int(w), int(h)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = {pool.submit(_wrap, f): f for f in files}
        for fut in tqdm(as_completed(futs), total=len(futs), desc="Processing", unit="img"):
            ok = fut.result()
            if ok:
                processed += 1
            else:
                failures.append(futs[fut].name)

    return processed, failures


def main():
    ap = argparse.ArgumentParser(description="Generate line-art via OpenAI and convert to KDP-ready coloring pages")
    ap.add_argument("--prompt", required=True, help="text prompt, e.g. 'cute forest animals'")
    ap.add_argument("--count", type=int, default=10, help="number of images to generate")
    ap.add_argument("--size", default="1024x1024", help="generation size WxH, e.g. 1024x1024")
    ap.add_argument("--resize", default="2550x3300", help="final page size for processing (8.5x11 @300DPI)")
    ap.add_argument("--thicken", type=int, default=2, help="line thickening radius in pixels")
    ap.add_argument("--threshold", type=int, default=160, help="binarization threshold 0-255")
    ap.add_argument("--dpi", type=int, default=300, help="output DPI for saved PNGs")
    ap.add_argument("--trim-margins", action="store_true", help="auto-trim white margins before resize")
    ap.add_argument("--max_concurrency", type=int, default=3, help="parallelism for generation/processing")
    ap.add_argument("--skip-process", action="store_true", help="only generate images, skip conversion")
    args = ap.parse_args()

    t0 = time.time()
    project_root = Path(__file__).resolve().parents[1]
    input_dir = project_root / "input"
    output_dir = project_root / "output"
    logs_dir = ensure_logs_dir(project_root)
    logfile = logs_dir / ("run-" + datetime.now().strftime("%Y%m%d_%H%M") + ".txt")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate
    saved, gen_failed = generate_images(args.prompt, args.count, args.size, input_dir, args.max_concurrency, logfile)

    processed = 0
    proc_failed: List[str] = []
    if not args.skip_process and saved:
        p_count, failures = run_postprocess_parallel(
            project_root,
            saved,
            output_dir,
            args.resize,
            args.thicken,
            args.threshold,
            dpi=args.dpi,
            trim_margins=args.trim_margins,
            max_workers=args.max_concurrency,
            logfile=logfile,
        )
        processed = p_count
        proc_failed = failures

    elapsed = time.time() - t0
    print("\nSummary:")
    print(f"  Generated: {len(saved)}")
    if gen_failed:
        print(f"  Generation skipped/failed: {len(gen_failed)} => {gen_failed}")
    if not args.skip_process:
        print(f"  Processed: {processed}")
        if proc_failed:
            print(f"  Processing skipped/failed: {len(proc_failed)} => {proc_failed}")
    print(f"  Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
