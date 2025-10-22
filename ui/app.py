import subprocess, sys, os
from pathlib import Path
from datetime import datetime
import zipfile
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]  # project root: coloring-explorers
SCRIPTS = ROOT / "scripts"
INPUT = ROOT / "input"
OUTPUT = ROOT / "output"
EXPORTS = ROOT / "exports"
COVERS = EXPORTS / "covers"

st.set_page_config(page_title="Coloring Explorers", layout="centered")
st.title("🎨 Coloring Explorers – Book Maker")

# --- helpers -------------------------------------------------------------
def run(cmd: list[str]):
    st.write("```powershell\n" + " ".join(cmd) + "\n```")
    proc = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    if proc.stdout: st.text(proc.stdout)
    if proc.stderr: st.error(proc.stderr)
    return proc.returncode == 0

def py(script: str, *args: str):
    # use current python
    return run([sys.executable, str(SCRIPTS / script), *args])

EXPORTS.mkdir(parents=True, exist_ok=True)
COVERS.mkdir(parents=True, exist_ok=True)

# --- sidebar: quick links -----------------------------------------------
st.sidebar.header("Folders")
if st.sidebar.button("Open exports"):
    os.startfile(EXPORTS)
if st.sidebar.button("Open covers"):
    os.startfile(COVERS)
if st.sidebar.button("Open output pages"):
    os.startfile(OUTPUT)

# --- 1) Generate pages ---------------------------------------------------
st.subheader("1) Generate pages")
prompt = st.text_input("Prompt (theme)", value="cute forest animals")
count = st.number_input("How many pages", min_value=1, max_value=120, value=10, step=1)
model = st.selectbox("Image model", ["dall-e-3", "gpt-image-1"], index=0)
go_gen = st.button("🚀 Generate")

if go_gen:
    ok = py("generate_coloring_pages.py",
            "--prompt", prompt,
            "--count", str(count),
            "--model", model)
    if ok: st.success("Generation finished ✅")

# --- 2) Process pages ----------------------------------------------------
st.subheader("2) Process to bold, KDP-ready")
resize = st.text_input("Resize (pixels W x H)", value="2550x3300")
thicken = st.slider("Thicken lines", 0, 6, 2)
threshold = st.slider("B/W threshold", 80, 220, 160)
dpi = st.number_input("DPI", 72, 600, 300, 1)
trim = st.checkbox("Trim white margins", value=False)
go_proc = st.button("🛠️ Process")

if go_proc:
    args = ["--input", str(INPUT), "--output", str(OUTPUT), "--resize", resize,
            "--thicken", str(thicken), "--threshold", str(threshold), "--dpi", str(dpi)]
    if trim: args.append("--trim-margins")
    ok = py("process_images.py", *args)
    if ok: st.success("Processing finished ✅")

# --- 3) Export PDF -------------------------------------------------------
st.subheader("3) Export interior PDF")
paper = st.selectbox("Paper size", ["letter", "a4"], index=0)
bleed = st.selectbox("Bleed", ["none", "3mm"], index=0)
 count_pdf = st.number_input("Page count in PDF", 1, 120, min(count, 60))
 preview = st.checkbox("Preview (allow fewer than 30 pages)", value=False)
shuffle = st.checkbox("Shuffle pages", value=False)
go_pdf = st.button("📄 Export PDF")

if go_pdf:
    args = ["--input", str(OUTPUT), "--paper", paper, "--bleed", bleed, "--count", str(count_pdf)]
    if shuffle: args.append("--shuffle")
    if preview: args.append("--preview")
    ok = py("export_pdf.py", *args)
    if ok:
        # Show latest cover download (by modified time)
        try:
            candidates = sorted(
                [p for p in COVERS.glob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg"}],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except Exception:
            candidates = []
        if candidates:
            latest_cover = candidates[0]
            try:
                with open(latest_cover, "rb") as f:
                    st.download_button(
                        label="Download latest cover",
                        data=f.read(),
                        file_name=latest_cover.name,
                        mime="image/png" if latest_cover.suffix.lower() == ".png" else "image/jpeg",
                        key="download_latest_cover",
                    )
            except Exception:
                pass
        # Track the most recently exported PDF
        try:
            candidates = sorted(EXPORTS.glob(f"book-{paper}-*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
            if candidates:
                st.session_state["last_pdf_path"] = str(candidates[0])
        except Exception:
            pass
        # Show download button for interior PDF when available
        last_pdf = st.session_state.get("last_pdf_path")
        if last_pdf and Path(last_pdf).exists():
            with open(last_pdf, "rb") as f:
                st.download_button(
                    label="Download interior PDF",
                    data=f.read(),
                    file_name=Path(last_pdf).name,
                    mime="application/pdf",
                    key="download_interior_pdf",
                )
        st.success("PDF exported ✅")
        os.startfile(EXPORTS)

# Optional: download pages as ZIP (flat .png files, no subdirs)
create_zip = st.button("Download pages as ZIP")
if create_zip:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = EXPORTS / f"pages-{ts}.zip"
    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(OUTPUT.glob("*.png")):
                zf.write(p, arcname=p.name)
        if zip_path.exists():
            with open(zip_path, "rb") as f:
                st.download_button(
                    label="Download pages ZIP",
                    data=f.read(),
                    file_name=zip_path.name,
                    mime="application/zip",
                    key="download_pages_zip",
                )
    except Exception as e:
        st.error(f"Failed to create ZIP: {e}")

# --- 4) Cover maker ------------------------------------------------------
st.subheader("4) Make a cover")
title = st.text_input("Title", value="Cute Forest Animals")
subtitle = st.text_input("Subtitle", value="60 Fun Coloring Pages")
brand = st.text_input("Brand", value="Coloring Explorers")
style = st.selectbox("Style", ["playful", "elegant", "cute"], index=0)
use_ai = st.checkbox("Use AI background (requires verified access)", value=False)

col1, col2 = st.columns(2)
bg_color = col1.text_input("Solid BG hex (no AI)", value="#FFFFFF")
title_color = col2.text_input("Title color", value="#111111")
bg_image = st.file_uploader("Or choose a local background image (no AI)", type=["png","jpg","jpeg"])

go_cover = st.button("🎆 Generate Cover")

if go_cover:
    args = ["--title", title, "--brand", brand, "--style", style]
    if subtitle: args += ["--subtitle", subtitle]
    if use_ai:
        args += ["--theme", prompt, "--model", model, "--size", "1536x1024"]
    elif bg_image:
        # Save uploaded file to covers folder
        buf = COVERS / bg_image.name
        with open(buf, "wb") as f: f.write(bg_image.getbuffer())
        args += ["--bg-image", str(buf)]
    else:
        args += ["--no-bg", "--bg-color", bg_color]
    args += ["--title-color", title_color]

    ok = py("generate_cover.py", *args)
    if ok:
        st.success("Cover generated ✅")
        os.startfile(COVERS)
