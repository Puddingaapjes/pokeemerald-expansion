#!/usr/bin/env python3
"""
match_palette.py

Re-indexes PNGs to use colors from one "source" PNG's palette (e.g. a
Pokemon's front sprite), so the whole species' graphics — front sprite,
overworld/follower sprite, icon, etc. — share one consistent palette.

Designed for pokeemerald-expansion style indexed PNGs, where:
  - Images are palette (indexed) mode.
  - Index 0 is conventionally the transparent color and should stay that way.
  - Colors with no good match are still mapped to their closest equivalent
    (flagged in the report if the match is a poor one, but never skipped).
  - Each distinct target color is assigned to a *distinct* source palette
    slot whenever possible (a global, mutually-exclusive assignment), rather
    than each color picking its closest match independently. This avoids
    collapsing two different colors onto the same source index just because
    they both happened to be nearest to it.

=======================
 USAGE 1: single pair
=======================
    python3 match_palette.py SOURCE.png TARGET.png OUTPUT.png

Example:
    python3 match_palette.py anim_front.png icon.png icon_matched.png

=======================
 USAGE 2: folder mode
=======================
    python3 match_palette.py --folder SPECIES_DIR [--out OUT_DIR]

Looks inside SPECIES_DIR for a source sprite (anim_front.png, front.png) and
re-indexes anim_back.png, back.png, overworld.png, follower.png, and icon.png
(whichever are present) against it. Outputs are written in place unless
--out is given, in which case the species folder structure is mirrored
there.

Example:
    python3 match_palette.py --folder graphics/pokemon/torchic
    python3 match_palette.py --folder graphics/pokemon/torchic --out /tmp/preview
"""

import argparse
import io
import struct
import sys
from pathlib import Path

from PIL import Image

# Filenames to look for, in priority order, for each role.
SOURCE_CANDIDATES = ["anim_front.png", "front.png"]
TARGET_CANDIDATES = ["anim_back.png", "back.png", "overworld.png", "follower.png", "icon.png"]

# PNG chunk types that actually matter for a simple indexed sprite. Anything
# else (zTXt/tEXt/iTXt comments, iCCP color profiles, bKGD, pHYs, tIME, etc.)
# is ancillary metadata that's safe to drop. Some image editors (old
# ImageMagick/GIMP exports in particular) embed large/oddly-formed metadata
# chunks — e.g. a multi-KB "Raw profile type exif" blob wrapped in a zTXt
# chunk — that certain Pillow/libpng builds fail to parse during format
# detection, even though the file is otherwise perfectly valid PNG. Stripping
# everything but these essential chunks sidesteps that without touching any
# actual pixel/palette data.
_PNG_KEEP_CHUNK_TYPES = {b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"IEND"}
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _strip_ancillary_png_chunks(raw: bytes) -> bytes:
    """Return a copy of a PNG's bytes containing only the chunks needed to
    decode a simple indexed image (IHDR/PLTE/tRNS/IDAT/IEND). Returns `raw`
    unchanged if it doesn't look like a PNG or can't be walked cleanly."""
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
            # Malformed/truncated chunk table; bail and return original
            # bytes so the caller's error (if any) reflects the real file.
            return raw
        if ctype in _PNG_KEEP_CHUNK_TYPES:
            out_parts.append(raw[pos:chunk_end])
        pos = chunk_end
        if ctype == b"IEND":
            break

    return b"".join(out_parts)


def safe_open_png(path) -> Image.Image:
    """Open a PNG via Pillow, transparently stripping ancillary metadata
    chunks first so oversized/malformed eXIf, iCCP, or text chunks can't
    cause a spurious UnidentifiedImageError on an otherwise-valid file.
    Always loads the image immediately so any real decode error surfaces
    here rather than later on first pixel access."""
    with open(path, "rb") as f:
        raw = f.read()
    cleaned = _strip_ancillary_png_chunks(raw)
    img = Image.open(io.BytesIO(cleaned))
    img.load()
    return img

# Distance (squared RGB) above which a match is flagged as "poor" in reports.
# 15*15*3 ~= a per-channel difference of roughly 15/255, a reasonable
# eyeballing threshold for "this might look a bit off."
POOR_MATCH_THRESHOLD = 15 * 15 * 3


def get_palette_colors(img: Image.Image, num_colors: int = 16) -> list[tuple[int, int, int]]:
    """Return list of (r,g,b) tuples for the image's declared palette.

    Reads up to `num_colors` entries (16 by GBA convention) rather than only
    colors actually used by pixels, since the full palette should be
    available for matching even if not every color appears on screen."""
    if img.mode != "P":
        raise ValueError("Image is not in indexed (palette) mode.")

    pal = img.getpalette()
    if pal is None:
        raise ValueError("Image has no palette.")

    declared_entries = len(pal) // 3
    n = min(num_colors, declared_entries)

    return [tuple(pal[i * 3:i * 3 + 3]) for i in range(n)]


def closest_color_index(target: tuple[int, int, int],
                         palette: list[tuple[int, int, int]],
                         exclude_indices: set[int] = frozenset()) -> tuple[int, int]:
    """Return (index, squared_distance) of the closest color in `palette`,
    skipping any indices in `exclude_indices` (e.g. the transparent slot,
    which shouldn't be offered as a match for a real, opaque color, or
    slots already claimed by another color in the global assignment)."""
    best_idx = None
    best_dist = None
    tr, tg, tb = target
    for i, (r, g, b) in enumerate(palette):
        if i in exclude_indices:
            continue
        dist = (r - tr) ** 2 + (g - tg) ** 2 + (b - tb) ** 2
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_idx = i
    if best_idx is None:
        # Every candidate was excluded; fall back to index 0 rather than crash.
        return 0, 0
    return best_idx, best_dist


def assign_unique_matches(colors: list[tuple[int, tuple[int, int, int]]],
                           palette: list[tuple[int, int, int]],
                           reserved_indices: set[int] = frozenset()
                           ) -> dict[int, tuple[int, int]]:
    """Globally assign each (old_idx, color) in `colors` to a distinct index
    in `palette`, greedily by closest distance first.

    This is the key fix: rather than letting each color independently pick
    its nearest palette entry (which can cause two different colors to both
    land on the same slot), every (color, candidate-slot) pair is considered
    together. The single globally-closest pair is assigned first, that slot
    is then taken off the table, and so on. This is the standard greedy
    approximation to bipartite optimal assignment — not provably optimal in
    every case, but it guarantees no slot is reused while still favoring the
    best matches first.

    If there are more colors than available (non-reserved) palette slots,
    leftover colors are forced to reuse the closest already-taken slot
    (unique assignment is impossible at that point) and a "poor match"-style
    situation is unavoidable for the overflow.

    Returns: {old_idx: (new_idx, squared_distance)}
    """
    available = [i for i in range(len(palette)) if i not in reserved_indices]

    # Build every (distance, old_idx, color, slot_idx) candidate pair.
    candidates = []
    for old_idx, color in colors:
        tr, tg, tb = color
        for slot_idx in available:
            sr, sg, sb = palette[slot_idx]
            dist = (sr - tr) ** 2 + (sg - tg) ** 2 + (sb - tb) ** 2
            candidates.append((dist, old_idx, slot_idx))

    candidates.sort(key=lambda c: c[0])

    result: dict[int, tuple[int, int]] = {}
    used_slots: set[int] = set()
    unassigned_colors = {old_idx for old_idx, _ in colors}

    for dist, old_idx, slot_idx in candidates:
        if old_idx not in unassigned_colors:
            continue  # this color already got a slot
        if slot_idx in used_slots:
            continue  # this slot already went to another color
        result[old_idx] = (slot_idx, dist)
        used_slots.add(slot_idx)
        unassigned_colors.discard(old_idx)
        if not unassigned_colors:
            break

    # Overflow: more distinct colors than free slots. Fall back to nearest
    # match regardless of reuse (collisions here are unavoidable, not a bug).
    if unassigned_colors:
        color_by_idx = dict(colors)
        for old_idx in unassigned_colors:
            slot_idx, dist = closest_color_index(
                color_by_idx[old_idx], palette, exclude_indices=reserved_indices
            )
            result[old_idx] = (slot_idx, dist)

    return result


def get_transparent_index(img: Image.Image) -> int | None:
    """Return the index used for transparency, if any."""
    info_idx = img.info.get("transparency")
    if isinstance(info_idx, int):
        return info_idx
    return None


def match_image_to_palette(source_palette: list[tuple[int, int, int]],
                            target_img: Image.Image,
                            transparent_index_default: int = 0,
                            label: str = "") -> Image.Image:
    """Core re-indexing step: remap `target_img`'s used colors to their
    closest match in `source_palette`, preserving shape/alpha. Returns a new
    Image in mode 'P' using `source_palette` (padded to 16 entries).

    Matching is done as a single global, mutually-exclusive assignment (see
    `assign_unique_matches`) so that two different used colors don't both
    collapse onto the same source palette slot."""
    if target_img.mode != "P":
        raise ValueError(f"{label}: image is not indexed (mode={target_img.mode}).")

    target_palette = get_palette_colors(target_img)

    transparent_idx = get_transparent_index(target_img)
    if transparent_idx is None:
        transparent_idx = transparent_index_default

    used_indices = {idx for _, idx in target_img.getcolors()}

    print(f"  [{label}] palette: {len(target_palette)} colors "
          f"({len(used_indices)} used by pixels), transparent idx={transparent_idx}")

    # Gather all used, non-transparent colors that need a slot.
    colors_to_match = [
        (old_idx, target_palette[old_idx])
        for old_idx in sorted(used_indices)
        if old_idx != transparent_idx
    ]

    # Source index 0 is reserved for transparency, so it's never offered as
    # a match for an opaque color.
    assignment = assign_unique_matches(
        colors_to_match, source_palette, reserved_indices={0}
    )

    old_to_new_index = {}
    match_report = []
    for old_idx, color in colors_to_match:
        new_idx, dist = assignment[old_idx]
        old_to_new_index[old_idx] = new_idx
        match_report.append((old_idx, color, new_idx, source_palette[new_idx], dist))

    # Transparent index always maps to source palette's index 0 (pokeemerald
    # convention: index 0 is the transparent/background slot).
    old_to_new_index[transparent_idx] = 0

    new_palette = list(source_palette)
    while len(new_palette) < 16:
        new_palette.append((0, 0, 0))

    px = target_img.load()
    w, h = target_img.size
    out_img = Image.new("P", (w, h))

    flat_palette = []
    for (r, g, b) in new_palette[:256]:
        flat_palette.extend([r, g, b])
    out_img.putpalette(flat_palette)

    out_px = out_img.load()
    for y in range(h):
        for x in range(w):
            old_idx = px[x, y]
            out_px[x, y] = old_to_new_index.get(old_idx, 0)

    out_img.info["transparency"] = 0

    # Report in old-index order for readability.
    for old_idx, old_color, new_idx, new_color, dist in sorted(match_report):
        flag = "  <-- poor match" if dist > POOR_MATCH_THRESHOLD else ""
        print(f"      idx {old_idx:>2} {old_color} -> idx {new_idx:>2} {new_color}{flag}")

    return out_img


def process_pair(source_path: str, target_path: str, output_path: str) -> None:
    source_img = safe_open_png(source_path)
    target_img = safe_open_png(target_path)

    if source_img.mode != "P":
        sys.exit(f"Error: source image '{source_path}' is not indexed (mode={source_img.mode}).")

    source_palette = get_palette_colors(source_img)
    print(f"Source: {source_path} ({len(source_palette)} colors)")

    out_img = match_image_to_palette(
        source_palette, target_img, label=Path(target_path).name
    )
    out_img.save(output_path, transparency=0)
    print(f"Saved: {output_path}")


def process_folder(folder: str, out_dir: str | None, skip: set[str] = frozenset()) -> None:
    folder_path = Path(folder)
    if not folder_path.is_dir():
        sys.exit(f"Error: '{folder}' is not a directory.")

    source_file = None
    for candidate in SOURCE_CANDIDATES:
        candidate_path = folder_path / candidate
        if candidate_path.exists():
            source_file = candidate_path
            break

    if source_file is None:
        sys.exit(f"Error: no source sprite found in '{folder}' "
                  f"(looked for {', '.join(SOURCE_CANDIDATES)}).")

    source_img = safe_open_png(source_file)
    if source_img.mode != "P":
        sys.exit(f"Error: source sprite '{source_file}' is not indexed (mode={source_img.mode}).")

    source_palette = get_palette_colors(source_img)
    print(f"Source palette: {source_file.name} ({len(source_palette)} colors)\n")

    dest_dir = Path(out_dir) if out_dir else folder_path
    dest_dir.mkdir(parents=True, exist_ok=True)

    found_any = False
    for candidate in TARGET_CANDIDATES:
        if candidate in skip:
            continue
        target_path = folder_path / candidate
        if not target_path.exists():
            continue
        found_any = True

        target_img = safe_open_png(target_path)
        try:
            out_img = match_image_to_palette(
                source_palette, target_img, label=candidate
            )
        except ValueError as e:
            print(f"  Skipping {candidate}: {e}")
            continue

        out_path = dest_dir / candidate
        out_img.save(out_path, transparency=0)
        print(f"  Saved: {out_path}\n")

    if not found_any:
        print(f"No target files found in '{folder}' "
              f"(looked for {', '.join(TARGET_CANDIDATES)}).")


def main():
    parser = argparse.ArgumentParser(
        description="Re-index PNGs to share one source palette (pokeemerald-expansion style).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--folder", help="Species folder to process (folder mode).")
    parser.add_argument("--out", help="Output directory for folder mode (default: overwrite in place).")
    parser.add_argument("--skip", help="Comma-separated target filenames to skip, e.g. --skip icon.png "
                                        "or --skip icon.png,follower.png")
    parser.add_argument("positional", nargs="*", help="SOURCE.png TARGET.png OUTPUT.png (single-pair mode).")

    args = parser.parse_args()

    skip = set()
    if args.skip:
        skip = {name.strip() for name in args.skip.split(",") if name.strip()}

    if args.folder:
        process_folder(args.folder, args.out, skip=skip)
    elif len(args.positional) == 3:
        source_path, target_path, output_path = args.positional
        process_pair(source_path, target_path, output_path)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
