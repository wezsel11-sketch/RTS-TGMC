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

cd "$OPENRA_DIR"
sh utility.sh tgmc --check-yaml
sh utility.sh tgmc --check-missing-sprites
for map in "$MAPS"/*/; do
	sh utility.sh tgmc --check-yaml "${map%/}"
done
echo "tgmc: checks passed"
