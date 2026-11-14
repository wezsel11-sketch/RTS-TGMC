#!/bin/sh
# Lint the built mod with OpenRA's own checkers. Run build_mod.sh first (with OPENRA_DIR set so the mod is linked).
#
#   OPENRA_DIR=/path/to/OpenRA  mod/check_mod.sh
#
# Checks the rules (--check-yaml), the sprite references (--check-missing-sprites), and every built map.
# Exits non-zero on any error. Needs the .NET SDK, like OpenRA itself.
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
OPENRA_DIR=${OPENRA_DIR:?set OPENRA_DIR to a built OpenRA checkout}
MAPS="$ROOT/build/mod/tgmc/maps"

# A voice set with Prefixes must name every faction: a marine owned by a faction that is not listed asks for the bare
# clip name (scream-1.ogg), which does not exist, and dies silent.
python3 -I - "$ROOT/tgmc" <<'EOF'
import re, sys
root = sys.argv[1]
factions = set(re.findall(r"^\t\tInternalName: (\S+)", open(root + "/rules/world.yaml").read(), re.M))
bad = 0
for block in re.split(r"^(?=\S)", open(root + "/audio/voices.yaml").read(), flags=re.M):
    m = re.search(r"^\tPrefixes:\n((?:\t\t.*\n)+)", block, re.M)
    if m:
        missing = factions - set(re.findall(r"^\t\t(\S+):", m.group(1), re.M))
        if missing:
            bad += 1
            print(f"voices.yaml {block.split(':')[0]}: no prefix for {sorted(missing)}")
sys.exit(bad and 1)
EOF

cd "$OPENRA_DIR"
sh utility.sh tgmc --check-yaml
sh utility.sh tgmc --check-missing-sprites
for map in "$MAPS"/*/; do
	sh utility.sh tgmc --check-yaml "${map%/}"
done
echo "tgmc: checks passed"
