#!/usr/bin/env python3
"""
Move gObjectEventPicSurfing_<Species> lines from the bottom of pokemon.h
to just after the matching gObjectEventPic_<Species> line for each species.

The surfing line is inserted inside the existing #if OW_POKEMON_OBJECT_EVENTS
block, immediately after the gObjectEventPic_ line it belongs to.

Usage: python3 move_surfing.py pokemon.h [output.h]
       (if no output file given, overwrites the input)
"""

import re
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: move_surfing.py <input.h> [output.h]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) >= 3 else input_path

    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # -----------------------------------------------------------------------
    # 1. Collect all surfing lines from the bottom of the file.
    #    Build a dict: species_name -> (surfing_line_text, original_line_index)
    #    A surfing line looks like:
    #      [optional spaces]const u32 gObjectEventPicSurfing_<Name>[] = ...
    # -----------------------------------------------------------------------
    surfing_pattern = re.compile(
        r"^\s*const\s+u32\s+gObjectEventPicSurfing_(\w+)\[\]"
    )

    # Map species name -> surfing line text (stripped of leading/trailing newline,
    # we'll re-add a newline when inserting).
    surfing_map = {}   # name -> line text (with original trailing newline)
    surfing_indices = set()  # line indices to remove later

    for i, line in enumerate(lines):
        m = surfing_pattern.match(line)
        if m:
            name = m.group(1)
            surfing_map[name] = line
            surfing_indices.add(i)

    if not surfing_map:
        print("No gObjectEventPicSurfing_ lines found. Nothing to do.")
        sys.exit(0)

    print(f"Found {len(surfing_map)} surfing entries: {', '.join(sorted(surfing_map))}")

    # -----------------------------------------------------------------------
    # 2. Find where to insert each surfing line.
    #    Target: the gObjectEventPic_<Species>[] line (not commented out,
    #    not a Surfing/F/Alola/etc. variant — exact base name match).
    #    We insert AFTER that line.
    # -----------------------------------------------------------------------
    # Pattern: active (non-commented) gObjectEventPic_<Name>[] line
    ow_pic_pattern = re.compile(
        r"^(\s*)const\s+u32\s+gObjectEventPic_(\w+)\[\]"
    )

    # Build insertion map: line_index -> list of surfing lines to insert after it
    insertions = {}  # line_index -> [line_text, ...]
    placed = set()

    for i, line in enumerate(lines):
        if i in surfing_indices:
            continue  # skip the surfing lines themselves
        m = ow_pic_pattern.match(line)
        if not m:
            continue
        indentation = m.group(1)
        name = m.group(2)
        if name in surfing_map and name not in placed:
            # Build the new surfing line with the same indentation as gObjectEventPic_
            original_surfing = surfing_map[name].rstrip("\n")
            # Strip any leading whitespace from the original surfing line, then
            # re-indent to match gObjectEventPic_'s indentation.
            stripped = original_surfing.lstrip()
            new_surfing_line = indentation + stripped + "\n"
            insertions.setdefault(i, []).append(new_surfing_line)
            placed.add(name)
            print(f"  Will insert gObjectEventPicSurfing_{name} after line {i+1}")

    unplaced = set(surfing_map) - placed
    if unplaced:
        print(f"\nWARNING: Could not find a gObjectEventPic_ target for: {', '.join(sorted(unplaced))}")
        print("  These lines will be removed from the bottom but NOT re-inserted.")
        print("  Check that the species name matches exactly (case-sensitive).")

    # -----------------------------------------------------------------------
    # 3. Rebuild the file:
    #    - Skip lines in surfing_indices
    #    - After each line that has an insertion, inject the new surfing line(s)
    #    - Also remove the blank line(s) before the surfing block at the bottom
    #      to avoid leaving a dangling blank line.
    # -----------------------------------------------------------------------

    # Find the blank line immediately before the first surfing line at the bottom,
    # so we can drop it too (keeps the file tidy).
    first_surfing_idx = min(surfing_indices)
    extra_blank_indices = set()
    j = first_surfing_idx - 1
    while j >= 0 and lines[j].strip() == "":
        extra_blank_indices.add(j)
        j -= 1

    output_lines = []
    for i, line in enumerate(lines):
        if i in surfing_indices or i in extra_blank_indices:
            continue  # drop the original surfing lines (and preceding blank)
        output_lines.append(line)
        if i in insertions:
            output_lines.extend(insertions[i])

    # -----------------------------------------------------------------------
    # 4. Write output
    # -----------------------------------------------------------------------
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    print(f"\nDone. Output written to: {output_path}")
    print(f"  Lines before: {len(lines)}")
    print(f"  Lines after:  {len(output_lines)}")


if __name__ == "__main__":
    main()
