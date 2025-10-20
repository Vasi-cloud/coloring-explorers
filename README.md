# Coloring Explorers

Generate simple, bold, KDP-ready coloring pages from prompts or images.

## Overview
- Goal: produce high-contrast, thick-outline, print-friendly pages.
- Output target (KDP-friendly): 8.5" x 11" at 300 DPI, black on white.

## Folders
- `input/`  — drop source images here (JPG/PNG/SVG).
- `output/` — processed coloring pages are written here.
- `scripts/` — helper scripts and utilities.

## Requirements
- Python 3.10+
- `pip install -r scripts/requirements.txt`

## Usage
1) Convert existing images to coloring pages
```
python scripts/process_images.py --input input --output output \
  --resize 2550x3300 --thicken 2 --threshold 160
```
- `--resize 2550x3300` fits to 8.5"x11" at 300DPI with white padding.
- `--thicken` controls line thickening (dilation in pixels).
- `--threshold` binarization cutoff (0-255).

2) From prompts (optional, future)
- Connect your preferred text-to-image tool (e.g., local Stable Diffusion, web API) to generate base images into `input/`, then run step 1.

## Notes for KDP
- Keep backgrounds simple and avoid gray fills.
- Ensure strong, closed outlines; adjust `--thicken` as needed.
- Leave margin safety for trim; the script pads to full page by default.

## Generate From Prompts (OpenAI)
This script uses OpenAI's Images API to create clean line-art, then auto-converts them into bold, print-ready pages.

Requirements:
- Set your OpenAI API key in the environment: `OPENAI_API_KEY`
- Install deps: `pip install -r scripts/requirements.txt`

Key options:
- `--count` number of images to generate (default 10)
- `--size` generation size, e.g. `1024x1024`
- `--resize` output page size, e.g. `2550x3300` (8.5"x11" @ 300DPI)
- `--thicken` line thickening radius in px
- `--threshold` binarization cutoff 0–255
- `--dpi` output PNG DPI (default 300)
- `--trim-margins` auto-trim white margins before resizing
- `--max_concurrency` parallelism for generation/processing (default 3)
- `--model` force a model (default `auto`). Try `gpt-image-1` or `dall-e-3`.
- `--debug` dump raw image API responses to `logs/debug-*.json` for support.

Examples:
```
# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-..."

# macOS/Linux
export OPENAI_API_KEY="sk-..."

# Generate 10 line-art images and convert to 8.5"x11" pages
python scripts/generate_coloring_pages.py --prompt "cute forest animals" --count 10 \
  --size 1024x1024 --resize 2550x3300 --thicken 2 --threshold 160 \
  --dpi 300 --trim-margins --max_concurrency 3

# Only generate (skip conversion)
python scripts/generate_coloring_pages.py --prompt "forest cabins" --skip-process

# Force an alternative model (fallback for access issues)
python scripts/generate_coloring_pages.py --prompt "cute forest animals" --model dall-e-3
```

Notes:
- The script shows progress bars for generation and processing.
- Generation calls use retries with exponential backoff (up to 3 attempts).
- Failures are logged to `logs/run-YYYYMMDD_HHMM.txt`; the script skips bad items and continues.
- A final summary prints generated, processed, skipped, and elapsed time.

Troubleshooting:
- If you see 403/invalid access for `gpt-image-1`, either pass `--model dall-e-3` or verify your organization at `https://platform.openai.com/settings/organization/general`. After verification, access can take up to ~15 minutes to propagate.
- If you see `NoneType` or `No b64_json` errors, try `--model dall-e-3` and re-run. Also include `--debug` to capture the raw API responses for support.
- Ensure `OPENAI_API_KEY` is set in the same terminal session before running.

## Generate a Cover for KDP
Create a 2560x1600 PNG front cover with AI background and text overlay.

Requirements:
- Set `OPENAI_API_KEY` and install dependencies: `pip install -r scripts/requirements.txt`

Examples:
```
# Light, playful cover with title/subtitle
python scripts/generate_cover.py \
  --title "Forest Buddies" \
  --subtitle "Cute Creatures to Color" \
  --theme "whimsical forest scene, clean space for title" \
  --bg light --style playful --dpi 300 --preview

# Dark elegant cover without subtitle
python scripts/generate_cover.py \
  --title "Nighttime Explorers" \
  --theme "starry forest sky, tasteful minimal composition" \
  --bg dark --style elegant
```

Flags:
- `--title` (required) and `--subtitle` (optional)
- `--theme` (required) background image theme prompt
- `--brand` footer brand (default: "Coloring Explorers")
- `--bg` `light|dark` controls background brightness and text color defaults
- `--style` `playful|elegant|cute` adjusts prompt styling
- `--dpi` PNG DPI metadata (default 300)
- `--preview` shows a small preview window before saving

Output:
- Saves to `exports/covers/<slug>-cover.png`

## License
MIT
