#!/usr/bin/env python3
import argparse
import base64
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv( Path(__file__).resolve().parents[1] / ".env" )
except Exception:
    pass
from typing import List, Optional, Tuple, Set
import subprocess

try:
    from openai import OpenAI
except Exception as e:  # pragma: no cover
    raise SystemExit("The 'openai' package is required. Install with: pip install -r scripts/requirements.txt") from e

# Auto-load .env from project root if present
def _load_dotenv_if_present() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    if env_path.exists():
        try:
            load_dotenv(env_path)
        except Exception:
            pass

_load_dotenv_if_present()

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


def _is_access_error(err: Exception) -> bool:
    msg = str(err).lower()
    # Heuristic: 403s and common access phrases
    return (
        "403" in msg
        or "must be verified" in msg
        or "permission" in msg
        or "access" in msg and "model" in msg
    )


def _dump_debug_response(logs_dir: Path, prefix: str, idx: int, resp_obj) -> Path:
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_path = logs_dir / f"debug-{prefix}-{ts}-{idx:02d}.json"
        # Prefer pydantic model_dump if present
        payload = None
        if hasattr(resp_obj, "model_dump"):
            payload = resp_obj.model_dump()
        elif hasattr(resp_obj, "to_dict"):
            payload = resp_obj.to_dict()
        else:
            # best-effort
            try:
                payload = json.loads(getattr(resp_obj, "json", lambda: "{}")())
            except Exception:
                payload = {"repr": repr(resp_obj)}
        debug_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return debug_path
    except Exception:
        # Best-effort only
        return Path("")


def _generate_with_model(
    client: OpenAI,
    model: str,
    full_prompt: str,
    size: str,
    out_path: Path,
    logfile: Path,
    run_logs_dir: Path,
    idx: int,
    debug: bool,
    tries: int = 3,
) -> bool:
    for attempt in range(1, tries + 1):
        try:
            resp = client.images.generate(
                model=model,
                prompt=full_prompt,
                size=size,
                response_format="b64_json",
            )

            # Extract base64 safely
            try:
                b64 = resp.data[0].b64_json
            except Exception as ex:
                if debug:
                    _dump_debug_response(run_logs_dir, f"{model}", idx, resp)
                log_error(logfile, f"[ERROR] Exception reading b64_json for item {idx} [model={model}] => {ex}")
                # log full resp and retry
                try:
                    payload = resp.model_dump() if hasattr(resp, "model_dump") else repr(resp)
                    log_error(logfile, f"[DEBUG] raw_response(item={idx}): {json.dumps(payload) if isinstance(payload, dict) else payload}")
                except Exception:
                    pass
                raise

            if not b64:
                # Missing/empty b64 is retriable
                keys = []
                try:
                    data0 = resp.data[0]
                    if hasattr(data0, "model_fields"):
                        keys = list(getattr(data0, "model_fields").keys())
                except Exception:
                    pass
                log_error(
                    logfile,
                    f"[ERROR] No b64_json in response for item {idx} [model={model}]; response keys: {keys}",
                )
                if debug:
                    _dump_debug_response(run_logs_dir, f"{model}", idx, resp)
                raise RuntimeError("missing b64_json")

            img_bytes = base64.b64decode(b64)
            out_path.write_bytes(img_bytes)
            return True
        except Exception as e:  # pragma: no cover (network)
            log_error(logfile, f"generate failed ({out_path.name}) attempt {attempt} [model={model}]: {e}")
            if attempt < tries:
                backoff_sleep(attempt)
            else:
                return False


def generate_one(
    client: OpenAI,
    full_prompt: str,
    size: str,
    out_path: Path,
    logfile: Path,
    run_logs_dir: Path,
    idx: int,
    debug: bool,
    prefer_model: str = "auto",
) -> Tuple[bool, str]:
    # Forced model path
    if prefer_model and prefer_model.lower() != "auto":
        ok = _generate_with_model(
            client,
            prefer_model,
            full_prompt,
            size,
            out_path,
            logfile,
            run_logs_dir,
            idx,
            debug,
        )
        return ok, prefer_model

    # Auto path: prefer gpt-image-1, fall back to dall-e-3 only on access errors
    try:
        ok = _generate_with_model(
            client,
            "gpt-image-1",
            full_prompt,
            size,
            out_path,
            logfile,
            run_logs_dir,
            idx,
            debug,
        )
        if ok:
            return True, "gpt-image-1"
        # If it failed after retries, do not automatically fall back unless last error suggested access issues.
        # We didn't keep the last exception here, so only fall back when an immediate access error occurs below.
    except Exception:
        # _generate_with_model swallows exceptions and returns False, so this shouldn't run.
        pass

    # Single immediate probe to detect access error and trigger fallback
    try:
        resp = client.images.generate(model="gpt-image-1", prompt=full_prompt, size=size, response_format="b64_json")
        b64 = getattr(resp.data[0], "b64_json", None)
        if b64:
            out_path.write_bytes(base64.b64decode(b64))
            return True, "gpt-image-1"
        else:
            raise RuntimeError("missing b64_json")
    except Exception as first_err:  # pragma: no cover
        if _is_access_error(first_err):
            log_error(logfile, f"access error for gpt-image-1 on {out_path.name}; falling back to dall-e-3: {first_err}")
            ok_fb = _generate_with_model(
                client,
                "dall-e-3",
                full_prompt,
                size,
                out_path,
                logfile,
                run_logs_dir,
                idx,
                debug,
            )
            return ok_fb, "dall-e-3" if ok_fb else "dall-e-3"
        # Non-access error: honor original behavior (retries already attempted above)
        return False, "gpt-image-1"


def generate_images(
    prompt: str,
    count: int,
    size: str,
    input_dir: Path,
    max_workers: int,
    logfile: Path,
    prefer_model: str = "auto",
    debug: bool = False,
) -> Tuple[List[Path], List[str], Set[str]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY. Set it in your environment before running.")

    # Use modern SDK default env loading
    client = OpenAI()
    input_dir.mkdir(parents=True, exist_ok=True)

    saved: List[Path] = []
    failed: List[str] = []
    models_used: Set[str] = set()
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
            fut = pool.submit(
                generate_one,
                client,
                full_prompt,
                size,
                out_path,
                logfile,
                logfile.parent,
                i,
                debug,
                prefer_model,
            )
            tasks.append((i, out_path, fut))

        for i, out_path, fut in tqdm(tasks, desc="Generating", unit="img"):
            ok, used_model = fut.result()
            models_used.add(used_model)
            if ok:
                saved.append(out_path)
            else:
                failed.append(out_path.name)

    return saved, failed, models_used


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
    ap.add_argument("--model", default="auto", help="force a model name (e.g. 'gpt-image-1', 'dall-e-3'); default 'auto'")
    ap.add_argument("--debug", action="store_true", help="dump raw image API responses to logs/debug-*.json for troubleshooting")
    ap.add_argument("--skip-process", action="store_true", help="only generate images, skip conversion")
    args = ap.parse_args()

    t0 = time.time()
    project_root = Path(__file__).resolve().parents[1]
    input_dir = project_root / "input"
    output_dir = project_root / "output"
    logs_dir = ensure_logs_dir(project_root)
    logfile = logs_dir / ("run-" + datetime.now().strftime("%Y%m%d_%H%M") + ".txt")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Model strategy log
    if args.model and args.model.lower() != "auto":
        strategy_msg = f"Using model: {args.model} (forced)"
    else:
        strategy_msg = "Using model: auto (prefer gpt-image-1, fallback to dall-e-3 on 403/access)"
    print(strategy_msg)
    log_error(logfile, strategy_msg)

    # Generate
    saved, gen_failed, models_used = generate_images(
        args.prompt,
        args.count,
        args.size,
        input_dir,
        args.max_concurrency,
        logfile,
        prefer_model=args.model or "auto",
        debug=args.debug,
    )

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
    # Log models actually used
    if models_used:
        used_str = ", ".join(sorted(models_used))
        log_error(logfile, f"models_used: {used_str}")

    print("\nSummary:")
    print(f"  Generated: {len(saved)}")
    if models_used:
        print(f"  Models used: {', '.join(sorted(models_used))}")
    if gen_failed:
        print(f"  Generation skipped/failed: {len(gen_failed)} => {gen_failed}")
    if not args.skip_process:
        print(f"  Processed: {processed}")
        if proc_failed:
            print(f"  Processing skipped/failed: {len(proc_failed)} => {proc_failed}")
    print(f"  Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
