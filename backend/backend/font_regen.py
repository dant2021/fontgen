import os
import json
import fontforge
from adjust_kerning import optimize_kerning
from adjust_tracking import tracking_font
from adjust_weight import create_all_variants
from font_generation import create_font_from_glyphs
from typing import Dict, List, Optional, Tuple
import datetime

# --------------------------------------------------------------------
# Build a mini font that only contains the replacement glyphs
# --------------------------------------------------------------------  

def build_replacement_font(
        aligned_paths: Dict,
        aligned_bboxes: Dict,
        chars_needed: List[str],
        temp_dir: str,
        debug_dir: Optional[str] = None,
) -> Tuple[str, Dict[str, str]]:
    """
    Run the **same** generation pipeline as create_font_from_glyphs but keep
    only `chars_needed`.  Returns (replacement_font_path, char_map).
    """
    # 1. create the sub‑folder structure
    os.makedirs(temp_dir, exist_ok=True)
    sub_svg_dir = os.path.join(temp_dir, "svg_font")
    os.makedirs(sub_svg_dir, exist_ok=True)
    
    # 2. build a temporary font exactly like the first pass
    create_font_from_glyphs(
        aligned_paths,
        aligned_bboxes,
        output_dir=sub_svg_dir,
        debug_dir=debug_dir
    )

    # 3. open that font, delete everything we *don't* need
    temp_font_path = os.path.join(sub_svg_dir, "MyFont.otf")
    f = fontforge.open(temp_font_path)

    keep_codepoints = {ord(c) for c in chars_needed if c}   # ← skip '' entries
    for g in list(f.glyphs()):
        if g.unicode not in keep_codepoints:
            f.removeGlyph(g)
    f.generate(os.path.join(temp_dir, "replacement.otf"))
    f.close()

    # 4. build a simple char_map for tracking / kerning
    char_map = {i: c for i, c in enumerate(chars_needed)}

    return os.path.join(temp_dir, "replacement.otf"), char_map

def drop_in_replacement(
        output_dir: str,
        replacement_font_path: str,
        char_map: dict[int, str],
):
    """
    Open the existing font, *remove* any glyphs that are about to be
    regenerated, merge the replacement font, then redo tracking/kerning.
    """
    base_font_path = os.path.join(output_dir, "MyFont.otf")
    font = fontforge.open(base_font_path)

    # 0. remove glyphs that will be replaced
    for ch in char_map.values():
        try:
            g = font[ord(ch)]
            font.removeGlyph(g)
        except (KeyError, TypeError):
            pass

    # 1. merge – now only *adds* new glyphs, no outline clash possible
    font.mergeFonts(replacement_font_path)

    # ────────────────────────────────────────────────────────────────
    # 2.  DROP ALL OLD GPOS LOOKUPS  ← new line
    #     (kern, tracking, mark‑to‑base etc.) so we rebuild from scratch
    for lookup in list(font.gpos_lookups):
        font.removeLookup(lookup)
    # ────────────────────────────────────────────────────────────────

    # 3. rebuild tracking / kerning on the FULL glyph set
    full_map = {i: chr(g.unicode) for i, g in enumerate(
        sorted((g for g in font.glyphs() if g.unicode >= 0),
               key=lambda g: g.unicode))
    }

    font, target = tracking_font(font, full_map)
    optimize_kerning(font, target)

    present_chars = {chr(g.unicode)                
                     for g in font.glyphs()
                     if g.unicode >= 0}

    # 4. save + weight variants
    font.generate(os.path.join(output_dir, "MyFont.ttf"))
    font.generate(os.path.join(output_dir, "MyFont.otf"))
    
    create_all_variants(os.path.join(output_dir, "MyFont.otf"), output_dir+"/fonts", bold_delta=32, light_delta=-32, regular=0)

    # ───────────────────────────────────────────────────────────────
    # 5.  KEEP  missing_glyphs.json  IN SYNC
    # ───────────────────────────────────────────────────────────────
    standard_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:!?@#$%&"
    missing_glyphs = [c for c in standard_chars if c not in present_chars]
    missing_path   = os.path.join(output_dir, "missing_glyphs.json")

    if missing_glyphs:
        with open(missing_path, "w") as fh:
            json.dump(missing_glyphs, fh)
    else:                            # everything present → remove the file
        with open(missing_path, "w") as fh:
            json.dump([], fh)
            
    # Write status file to indicate regeneration is complete
    with open(os.path.join(output_dir, "regen_status.json"), "w") as fh:
        json.dump({"status": "completed", "timestamp": str(datetime.datetime.now())}, fh)


# ─────────────────────────────────────────────────────────────────────────────
# CLI helper – only executed when you   python font_regen.py
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":                     # pragma: no cover
    import argparse, uuid, shutil
    from pathlib import Path
    from api import process_font, process_glyph_regeneration     # reuse

    # ─── default values you asked for ──────────────────────────────────
    DEFAULT_IMG   = "typeface_final.png"
    DEFAULT_OUT   = "output"
    DEFAULT_DEBUG = "debug"
    DEFAULT_CHARS = (
        "e, f, 3, ., , :, !, ?, #, $, &"
    )
    # ───────────────────────────────────────────────────────────────────

    parser = argparse.ArgumentParser(
        description="Quick CLI around the full font‑generation pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input",  "-i", default=DEFAULT_IMG,
                        help="PNG / JPEG containing the glyph sheet")
    parser.add_argument("--out",    "-o", default=DEFAULT_OUT,
                        help="Folder that will receive MyFont.otf etc.")
    parser.add_argument("--debug-dir",      default=DEFAULT_DEBUG,
                        help="Folder for intermediate SVG / PNG artefacts")
    parser.add_argument(
        "--chars", "-c", default=DEFAULT_CHARS,
        help="Comma‑separated list of characters to regenerate. "
             "Leave empty ('') to run the FIRST pass that creates the font."
    )
    args = parser.parse_args()

    img        = Path(args.input).expanduser().resolve()
    out_dir    = Path(args.out).expanduser().resolve()
    debug_dir  = Path(args.debug_dir).expanduser().resolve()
    job_id     = str(uuid.uuid4())                 # unique but irrelevant on CLI

    out_dir.mkdir(parents=True,  exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)

    # ---------------- decide whether this is 1st or 2nd pass ------------
    if args.chars:                                 # non‑empty string  →  regen
        chars = [c for c in args.chars.split(",") if c]
        print("Regenerating glyphs:", "".join(chars))
        process_glyph_regeneration(
            str(img), str(out_dir), str(debug_dir), job_id, chars
        )
    else:                                          # empty string → build font
        # clean previous run so you always start fresh
        for f in out_dir.iterdir():
            if f.is_file():
                f.unlink()
            else:
                shutil.rmtree(f)
        print("Creating first‑pass font …")
        process_font(str(img), str(out_dir), str(debug_dir), job_id)

    print("Done.  Files in:", out_dir)
