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

## License
MIT
