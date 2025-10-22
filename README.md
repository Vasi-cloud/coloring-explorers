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
- Environment config: scripts auto-load a `.env` at the project root if present.
  - Create a file named `.env` next to the `scripts/` folder with:
    
    OPENAI_API_KEY=sk-...your-key...

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
- Set your OpenAI API key in the environment: `OPENAI_API_KEY` (or place it in a project `.env` and it will be auto-loaded)
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
$env:OPENAI_API_KEY="sk-..."  # or put it into .env at project root

# macOS/Linux
export OPENAI_API_KEY="sk-..."  # or put it into .env at project root

# Generate 10 line-art images and convert to 8.5"x11" pages
python scripts/generate_coloring_pages.py --prompt "cute forest animals" --count 10 \
  --size 1024x1024 --resize 2550x3300 --thicken 2 --threshold 160 \
  --dpi 300 --trim-margins --max_concurrency 3

# Only generate (skip conversion)
python scripts/generate_coloring_pages.py --prompt "forest cabins" --skip-process

# Force an alternative model (fallback for access issues)
python scripts/generate_coloring_pages.py --prompt "cute forest animals" --model dall-e-3
```

## Export to PDF for KDP
Combine processed images from `output/` into a print-ready PDF.

```
# Letter (8.5x11") at 300 DPI, no bleed, shuffled order, 60 pages
python scripts/export_pdf.py --paper letter --dpi 300 --bleed none --shuffle --count 60

# A4 at 300 DPI with 3mm bleed, first 40 pages
python scripts/export_pdf.py --paper a4 --dpi 300 --bleed 3mm --count 40
```

Details:
- Input folder: `output/` (processed PNGs). Use `--input` to override.
- Page count must be between 30 and 120 (inclusive).
- Outputs: `exports/book-<paper>-<timestamp>.pdf` and a manifest JSON in `logs/`.

### KDP Upload Steps
1. Interior: choose Black & White, select bleed to match your export, and upload the generated PDF.
2. Trim size: choose `US Letter` (8.5" x 11") or `A4` to match your PDF.
3. Print settings: black on white; target 300 DPI.
4. Cover: create/upload a separate cover (interior PDF does not include the cover).
5. Preview: ensure important content stays clear of the trim/bleed area.

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
Create a 2560x1600 PNG front cover with either an AI-generated background or a local background image, then overlay title/subtitle/brand text.

Requirements:
- Install dependencies: `pip install -r scripts/requirements.txt`
- For AI background generation only: set `OPENAI_API_KEY` (env var or via `.env` at project root)

Examples:
```
# Light, playful cover with title/subtitle
python scripts/generate_cover.py \
  --title "Forest Buddies" \
  --subtitle "Cute Creatures to Color" \
  --theme "whimsical forest scene, clean space for title" \
  --bg light --style playful --dpi 300 --size 1536x1024 --model dall-e-3 --preview

# Dark elegant cover without subtitle
python scripts/generate_cover.py \
  --title "Nighttime Explorers" \
  --theme "starry forest sky, tasteful minimal composition" \
  --bg dark --style elegant --size 1024x1536 --model dall-e-3

# Solid background (no API call)
python scripts/generate_cover.py \
  --title "Forest Buddies" \
  --bg light --style playful --no-bg

# Use a local background image (no API call)
python scripts/generate_cover.py \
  --title "Forest Buddies" \
  --bg-image input/my-forest-photo.jpg --bg light --style playful

# Custom colors: white background, near-black title text
python scripts/generate_cover.py \
  --title "Forest Buddies" \
  --bg-image input/my-forest-photo.jpg \
  --bg-color "#FFFFFF" --title-color "#141820"
```

Flags:
- `--title` (required) and `--subtitle` (optional)
- `--theme` background image theme prompt (required when using AI generation)
- `--brand` footer brand (default: "Coloring Explorers")
- `--bg` `light|dark` controls background brightness and text color defaults
- `--style` `playful|elegant|cute` adjusts prompt styling
- `--dpi` PNG DPI metadata (default 300)
- `--preview` shows a small preview window before saving
- `--model` image model (default `dall-e-3`); e.g. `dall-e-3`, `gpt-image-1`
- `--size` generation size for the Images API (default `1536x1024`); supported: `1024x1024`, `1024x1536`, `1536x1024`
- `--no-bg` skip AI background and use a solid canvas (still overlays title/subtitle/brand)
- `--bg-image <path>` use a local image as the cover background (no API call)
- `--bg-color "#RRGGBB"` solid background color override; defaults align with `--bg`
- `--title-color "#RRGGBB"` text color for title/subtitle/brand; default is near-black on light backgrounds

Output:
- Saves to `exports/covers/<slug>-cover.png`

Behavior:
- The script never requests `2560x1600` from the API. It generates at a supported size and then upscales/fits to `2560x1600` with aspect preserved and padding letterboxed on a canvas.
- When `--bg-image` is used, the image is scaled and centered (letterboxed) onto a 2560x1600 canvas, then text is overlaid.
- On 403/access or API failure, it automatically falls back to `--no-bg` and logs a warning.
- `OPENAI_API_KEY` is only required when using AI background generation; `--bg-image` and `--no-bg` modes do not require it.

## License
MIT

## One-click launch

- Double-click `start-ui.bat` to launch the Streamlit UI with UTF-8 and the project virtual environment.
- Or run the desktop shortcut generator and then double-click the shortcut:
  - In PowerShell from the project root: `powershell -File .\scripts\make_desktop_shortcut.ps1`
  - This creates `Coloring Explorers.lnk` on your Desktop that launches the app.
