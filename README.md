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

## License
MIT

