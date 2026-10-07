#!/usr/bin/env python3
"""
apply_normal_pal_to_backs.py

For every species subfolder of a graphics/pokemon root directory that
contains back.png, normal.pal, and shiny.pal, replaces the back sprite's
embedded shiny palette colors with the normal.pal colors via a direct
index-for-index substitution. Pixel indices are unchanged; only the
palette itself is swapped.

This is the right approach because pokeemerald-expansion back sprites are
conventionally exported with shiny.pal's colors baked in, but their pixel
indices mean the same logical slots as normal.pal (the two files are
index-aligned 1:1). Replacing the palette without touching indices gives
a correctly normal-colored back sprite.

Only subfolders containing a normal.pal are considered species folders;
anything else is silently skipped. If shiny.pal is missing for a species,
that species is skipped with a warning (the fixup needs it to know which
colors to replace).

USAGE
-----
    python3 apply_normal_pal_to_backs.py ROOT_DIR

Example:
    python3 apply_normal_pal_to_backs.py graphics/pokemon

Back sprites are overwritten in place. Use version control (git) or a
backup if you want to preserve originals.
"""

import argparse
import io
import struct
import sys
from pathlib import Path

from PIL import Image


# ---------------------------------------------------------------------------
# PNG helpers (strip ancillary metadata chunks that can confuse Pillow)
# ---------------------------------------------------------------------------

_PNG_KEEP_CHUNK_TYPES = {b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"IEND"}
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _strip_ancillary_png_chunks(raw: bytes) -> bytes:
    if raw[:8] != _PNG_SIGNATURE:
        return raw
    pos = 8
    n = len(raw)
    out_parts = [raw[:8]]
    while pos + 8 <= n:
        length = struct.unpack(">I", raw[pos:pos + 4])[0]
        ctype = raw[pos + 4:pos + 8]
        chunk_end = pos + 8 + length + 4
        if chunk_end > n:
            return raw
        if ctype in _PNG_KEEP_CHUNK_TYPES:
            out_parts.append(raw[pos:chunk_end])
        pos = chunk_end
        if ctype == b"IEND":
            break
    return b"".join(out_parts)


def safe_open_png(path) -> Image.Image:
    with open(path, "rb") as f:
        raw = f.read()
    cleaned = _strip_ancillary_png_chunks(raw)
    img = Image.open(io.BytesIO(cleaned))
    img.load()
    return img


# ---------------------------------------------------------------------------
# JASC-PAL I/O
# ---------------------------------------------------------------------------

def read_jasc_pal(path) -> list[tuple[int, int, int]]:
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines or lines[0] != "JASC-PAL":
        raise ValueError(f"{path}: not a JASC-PAL file.")
    if len(lines) < 3:
        raise ValueError(f"{path}: truncated JASC-PAL file.")
    try:
        count = int(lines[2])
    except ValueError:
        raise ValueError(f"{path}: malformed color count '{lines[2]}'.")
    colors = []
    for line in lines[3:3 + count]:
        parts = line.split()
        if len(parts) < 3:
            raise ValueError(f"{path}: malformed color line '{line}'.")
        colors.append((int(parts[0]), int(parts[1]), int(parts[2])))
    if len(colors) != count:
        raise ValueError(f"{path}: declared {count} colors but found {len(colors)}.")
    return colors


# ---------------------------------------------------------------------------
# Core fixup
# ---------------------------------------------------------------------------

def apply_normal_pal_to_back(
    back_img: Image.Image,
    normal_colors: list[tuple[int, int, int]],
    shiny_colors: list[tuple[int, int, int]],
) -> Image.Image:
    """Return a copy of back_img with its embedded palette replaced by
    normal_colors (index-for-index). Pixel indices are not touched.

    shiny_colors is accepted for length-matching validation only — we don't
    need to know the shiny colors to do the swap, only that shiny.pal and
    normal.pal have the same number of slots (which they always should for
    a well-formed species).
    """
    if back_img.mode != "P":
        raise ValueError(f"back.png is not indexed (mode={back_img.mode}).")

    n = min(len(normal_colors), len(shiny_colors), 256)

    # Build the new flat palette: normal.pal colors for the first n slots,
    # zeros for the rest (Pillow requires a 768-entry flat list for mode P).
    flat = []
    for r, g, b in normal_colors[:n]:
        flat += [r, g, b]
    while len(flat) < 768:
        flat.append(0)

    w, h = back_img.size
    px = back_img.load()
    out = Image.new("P", (w, h))
    out.putpalette(flat)
    out_px = out.load()

    for y in range(h):
        for x in range(w):
            out_px[x, y] = px[x, y]  # indices unchanged

    # Preserve transparency index (pokeemerald convention: always 0).
    info_transp = back_img.info.get("transparency")
    out.info["transparency"] = info_transp if isinstance(info_transp, int) else 0

    return out


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def process_root(root: str) -> None:
    root_path = Path(root)
    if not root_path.is_dir():
        sys.exit(f"Error: '{root}' is not a directory.")

    species_dirs = sorted(
        p for p in root_path.iterdir()
        if p.is_dir() and (p / "normal.pal").exists()
    )

    if not species_dirs:
        sys.exit(f"Error: no subfolders of '{root}' contain a normal.pal file.")

    print(f"Found {len(species_dirs)} species folder(s) under '{root}'.\n")

    succeeded, skipped, failed = [], [], []

    for species_dir in species_dirs:
        name = species_dir.name
        back_path   = species_dir / "back.png"
        normal_path = species_dir / "normal.pal"
        shiny_path  = species_dir / "shiny.pal"

        # back.png absent — nothing to do, not a warning
        if not back_path.exists():
            continue

        if not shiny_path.exists():
            print(f"  SKIP  {name}: shiny.pal not found (needed for fixup).")
            skipped.append(name)
            continue

        try:
            normal_colors = read_jasc_pal(normal_path)
            shiny_colors  = read_jasc_pal(shiny_path)
            back_img      = safe_open_png(back_path)

            if len(normal_colors) != len(shiny_colors):
                print(f"  WARN  {name}: normal.pal has {len(normal_colors)} colors "
                      f"but shiny.pal has {len(shiny_colors)} — proceeding with "
                      f"min({len(normal_colors)}, {len(shiny_colors)}) slots.")

            out_img = apply_normal_pal_to_back(back_img, normal_colors, shiny_colors)
            out_img.save(back_path, transparency=out_img.info.get("transparency", 0))

            print(f"  OK    {name}/back.png")
            succeeded.append(name)

        except Exception as e:
            print(f"  FAIL  {name}: {e}")
            failed.append((name, str(e)))

    print(f"\nDone: {len(succeeded)} updated, {len(skipped)} skipped "
          f"(no shiny.pal), {len(failed)} failed.")
    if failed:
        print("\nFailed species:")
        for name, msg in failed:
            print(f"  - {name}: {msg}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply normal.pal colors to back.png sprites across all species folders.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("root", help="Root folder containing species subfolders "
                                     "(e.g. graphics/pokemon).")
    args = parser.parse_args()
    process_root(args.root)


if __name__ == "__main__":
    main()
