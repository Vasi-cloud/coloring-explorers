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
PLANS = ROOT / "plans"

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
PLANS.mkdir(parents=True, exist_ok=True)

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
############################################################
# Book Planner
############################################################
st.subheader("Book Planner")

# Presets (30 lines each)
PRESETS = {
    "New Year": [
        "fireworks over city skyline",
        "champagne glasses clinking",
        "countdown clock striking midnight",
        "party hats and confetti",
        "new year parade balloons",
        "kids watching fireworks",
        "festive table setting",
        "calendar turning to january 1",
        "city skyline with confetti",
        "sparkler writing in the air",
        "street celebration crowd",
        "fireworks reflected on river",
        "new year banner and streamers",
        "balloon drop at midnight",
        "party masks and noise makers",
        "fireworks behind big clock tower",
        "friends celebrating at home",
        "city plaza countdown stage",
        "confetti shower close-up",
        "kids wearing party hats",
        "couple watching fireworks",
        "festive doorway decorations",
        "fireworks and crescent moon",
        "giant digital countdown",
        "street lanterns and confetti",
        "sparkling skyline panorama",
        "fireworks across mountains",
        "party table with snacks",
        "confetti poppers and ribbons",
        "fireworks over clock tower",
    ],
    "Cozy Houses": [
        "cozy forest cabin",
        "treehouse among tall pines",
        "cottage in the snow",
        "lakeside house with dock",
        "tiny house with garden",
        "mountain cabin with chimney",
        "mushroom cottage",
        "beach hut near waves",
        "storybook cottage with flowers",
        "row of quaint townhouses",
        "lantern-lit front porch",
        "cabin in autumn forest",
        "hobbit-like round door house",
        "cottage with picket fence",
        "treehouse rope bridge",
        "cliffside cottage with lighthouse",
        "snowy village street",
        "farmhouse with windmill",
        "lake cabin with canoe",
        "garden shed with tools",
        "river cottage on stilts",
        "A-frame cabin in pines",
        "cozy attic window scene",
        "cottage with ivy walls",
        "tiny cabin in meadow",
        "house with wraparound porch",
        "cabin by campfire",
        "storybook village square",
        "cottage in flower field",
        "treehouse with lanterns",
    ],
    "Dinosaurs": [
        "t-rex near volcano",
        "triceratops in jungle",
        "stegosaurus with ferns",
        "brachiosaurus by river",
        "raptors in tall grass",
        "pterodactyls over canyon",
        "ankylosaurus in forest",
        "parasaurolophus at lake",
        "iguanodon on hillside",
        "allosaurus roaring",
        "spinosaurus near water",
        "ceratosaurus on rocks",
        "oviraptor with eggs",
        "dilophosaurus by trees",
        "compy pack exploring",
        "pachycephalosaurus duo",
        "styracosaurus grazing",
        "dracorex in brush",
        "euoplocephalus wandering",
        "kentrosaurus among palms",
        "therizinosaurus with claws",
        "microraptor in branches",
        "edmontosaurus herd",
        "corythosaurus trumpeting",
        "maiasaura with nest",
        "diplodocus tail swish",
        "giganotosaurus silhouette",
        "ouranosaurus by dunes",
        "cryolophosaurus in snow",
        "troodon watching stars",
    ],
    "Vehicles": [
        "race car on track",
        "fire truck with ladder",
        "excavator at construction",
        "sailboat on waves",
        "hot air balloon",
        "steam locomotive",
        "bulldozer moving dirt",
        "bicycle by park",
        "helicopter over city",
        "submarine under sea",
        "rocket launching",
        "airplane over clouds",
        "scooter on street",
        "bus at bus stop",
        "police car lights",
        "ambulance speeding",
        "tractor on farm",
        "dump truck unloading",
        "crane lifting load",
        "tow truck towing",
        "canoe on lake",
        "kayak in river",
        "snowmobile ride",
        "motorcycle cruiser",
        "forklift in warehouse",
        "race boat splash",
        "rowboat fishing",
        "spaceship cockpit",
        "glider above hills",
        "blimp over stadium",
    ],
}

# Keep plan text in session
default_plan = st.session_state.get("plan_text", "")
plan_text = st.text_area("One prompt per line", value=default_plan, height=300)
st.session_state["plan_text"] = plan_text

colp1, colp2 = st.columns([2, 2])
with colp1:
    preset_name = st.selectbox("Preset", list(PRESETS.keys()))
    if st.button("Load preset"):
        st.session_state["plan_text"] = "\n".join(PRESETS[preset_name])
        st.experimental_rerun()
with colp2:
    # Save / Load plan files
    fname_default = f"plan-{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    plan_filename = st.text_input("Plan filename", value=fname_default)
    if st.button("Save plan"):
        try:
            dest = PLANS / plan_filename
            dest.write_text(st.session_state.get("plan_text", ""), encoding="utf-8")
            st.success(f"Saved plan: {dest.name}")
        except Exception as e:
            st.error(f"Failed to save: {e}")

plan_files = sorted([p for p in PLANS.glob("*.txt")], key=lambda p: p.stat().st_mtime, reverse=True)
colp3, colp4 = st.columns([3, 1])
with colp3:
    load_choice = st.selectbox("Load plan", [p.name for p in plan_files]) if plan_files else None
with colp4:
    if st.button("Load plan") and load_choice:
        try:
            data = (PLANS / load_choice).read_text(encoding="utf-8")
            st.session_state["plan_text"] = data
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Failed to load: {e}")

# Parse plan lines
lines = [ln.strip() for ln in st.session_state.get("plan_text", "").splitlines() if ln.strip()]
st.caption(f"Detected pages: {len(lines)}")

def generate_single_page(idx: int, prompt_line: str) -> bool:
    """Generate one page then rename input/output to page-XXXX."""
    before_in = set(INPUT.glob("*.png"))
    before_out = set(OUTPUT.glob("*.png"))
    ok = py(
        "generate_coloring_pages.py",
        "--prompt", prompt_line,
        "--count", "1",
        "--model", model,
    )
    if not ok:
        return False
    after_in = set(INPUT.glob("*.png"))
    after_out = set(OUTPUT.glob("*.png"))
    new_in = sorted(list(after_in - before_in), key=lambda p: p.stat().st_mtime)
    new_out = sorted(list(after_out - before_out), key=lambda p: p.stat().st_mtime)
    src_in = new_in[-1] if new_in else None
    src_out = new_out[-1] if new_out else None
    if not src_in:
        return False
    tgt_in = INPUT / f"page-{idx:04d}.png"
    tgt_out = OUTPUT / f"page-{idx:04d}_coloring.png"
    try:
        if tgt_in.exists(): tgt_in.unlink()
        src_in.rename(tgt_in)
        if src_out:
            if tgt_out.exists(): tgt_out.unlink()
            src_out.rename(tgt_out)
        return True
    except Exception:
        return True

colg1, colg2 = st.columns([2, 2])
with colg1:
    go_plan = st.button("Generate from plan")
with colg2:
    if lines:
        sel_idx = st.selectbox("Regenerate page #", list(range(1, len(lines)+1)))
        go_regen = st.button("Regenerate selected page")
    else:
        sel_idx, go_regen = None, False

if go_plan and lines:
    t0 = datetime.now()
    made = skipped = 0
    prog = st.progress(0)
    for i, text in enumerate(lines, start=1):
        ok = generate_single_page(i, text)
        if ok:
            made += 1
        else:
            skipped += 1
        prog.progress(min(i/len(lines), 1.0))
    dt = (datetime.now() - t0).total_seconds()
    st.success(f"Done. Generated {made}, skipped {skipped}, elapsed {dt:.1f}s")

if go_regen and sel_idx is not None and 1 <= sel_idx <= len(lines):
    t0 = datetime.now()
    ok = generate_single_page(sel_idx, lines[sel_idx-1])
    dt = (datetime.now() - t0).total_seconds()
    if ok:
        st.success(f"Regenerated page {sel_idx} in {dt:.1f}s")
    else:
        st.error(f"Failed to regenerate page {sel_idx}")

############################################################
# 2) Process
############################################################
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
