#!/usr/bin/env bash
#
# move-surf-sprites.sh
#
# Moves files from:
#   graphics/object_events/pics/pokemon/surfable/0007_squirtle.png  -> graphics/pokemon/squirtle/surf.png
#   graphics/object_events/pics/pokemon/surfable/araquanid.png      -> graphics/pokemon/araquanid/surf.png
#   graphics/object_events/pics/pokemon/surfable/gastrodon_east.png -> graphics/pokemon/gastrodon/east/surf.png
#
# Tries "<number>_<species>.png" first; if that doesn't match, falls back to
# treating the whole filename (minus .png) as the species/folder name.
# Special-cased forms that live in nested subfolders are listed explicitly below.
# Skips shiny variants (e.g. *_shiny.png).
#
# Usage:
#   Dry run (default):  ./move-surf-sprites.sh
#   Actually move:       ./move-surf-sprites.sh --apply

set -euo pipefail

ROOT="/mnt/c/Users/Jari/Documents/Github/pokeemerald"
SOURCE_DIR="$ROOT/graphics/object_events/pics/pokemon/surfable"
DEST_ROOT="$ROOT/graphics/pokemon"
DEST_FILENAME="surf.png"

declare -A SPECIAL_CASES
SPECIAL_CASES["kyogre_primal"]="kyogre/primal"
SPECIAL_CASES["basculin_blue_striped"]="basculin/blue_striped"
SPECIAL_CASES["basculin_white_striped"]="basculin/white_striped"
SPECIAL_CASES["gastrodon_east"]="gastrodon/east"
SPECIAL_CASES["shellos_east"]="shellos/east"

APPLY=false
if [[ "${1:-}" == "--apply" ]]; then
    APPLY=true
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "Error: Source folder not found: $SOURCE_DIR" >&2
    exit 1
fi

moved_count=0
skipped_count=0
shiny_skipped_count=0

shopt -s nullglob

for file in "$SOURCE_DIR"/*.png; do
    filename=$(basename "$file")
    basename_noext="${filename%.png}"

    if [[ "$basename_noext" == *_shiny ]]; then
        ((++shiny_skipped_count))
        continue
    fi

    if [[ "$basename_noext" == *" copy" ]]; then
        echo "WARNING: Skipping '$filename' - looks like a stray duplicate file, handle manually"
        ((++skipped_count))
        continue
    fi

    if [[ "$basename_noext" =~ ^[0-9]+_(.+)$ ]]; then
        lookup_key="${BASH_REMATCH[1],,}"
    else
        lookup_key="${basename_noext,,}"
    fi

    if [[ -n "${SPECIAL_CASES[$lookup_key]+x}" ]]; then
        rel_path="${SPECIAL_CASES[$lookup_key]}"
    else
        rel_path="$lookup_key"
    fi

    dest_dir="$DEST_ROOT/$rel_path"
    dest_path="$dest_dir/$DEST_FILENAME"

    if [[ ! -d "$dest_dir" ]]; then
        echo "WARNING: Skipping '$filename' - destination folder does not exist: $dest_dir"
        ((++skipped_count))
        continue
    fi

    if [[ -f "$dest_path" ]]; then
        echo "WARNING: Skipping '$filename' - $dest_path already exists (won't overwrite)"
        ((++skipped_count))
        continue
    fi

    if $APPLY; then
        mv "$file" "$dest_path"
        echo "Moved: $filename  ->  $rel_path/$DEST_FILENAME"
    else
        echo "[DRY RUN] Would move: $filename  ->  $rel_path/$DEST_FILENAME"
    fi

    ((++moved_count))
done

echo ""
echo "Done. $moved_count file(s) processed, $skipped_count skipped, $shiny_skipped_count shiny file(s) ignored."
if ! $APPLY; then
    echo "This was a dry run - nothing was actually moved. Re-run with --apply to perform the move."
fi
