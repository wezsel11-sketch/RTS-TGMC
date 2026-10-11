#!/bin/sh
# Assemble the TGMC OpenRA mod into build/mod/tgmc.
#
#   TGMC=/path/to/terragov-marine-corps  mod/build_mod.sh
#   OPENRA_DIR=/path/to/OpenRA           mod/build_mod.sh   (also links the result into $OPENRA_DIR/mods/tgmc)
#   INSTALL_TO=/path/to/mods/tgmc        mod/build_mod.sh   (also copies the result there; used by package_windows.sh)
#
# build/ is git-ignored. It holds TGMC-derived art and audio. The prebuilt copy
# under game/mods/tgmc is committed on purpose (private repo, personal use).
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
TGMC=${TGMC:?set TGMC to a terragov-marine-corps checkout}
OUT="$ROOT/build/mod/tgmc"
PY=${PYTHON:-python3}

rm -rf "$OUT"
mkdir -p "$OUT"
cp -R "$ROOT/tgmc/." "$OUT/"

"$PY" -I "$HERE/build_sprites.py" --tgmc "$TGMC" --out "$OUT"
"$PY" -I "$HERE/build_sounds.py" --tgmc "$TGMC" --out "$OUT/audio"
"$PY" -I "$HERE/make_placeholders.py" --out "$OUT"
"$PY" -I "$HERE/make_chrome.py" --out "$OUT"

if [ -n "${OPENRA_DIR:-}" ]; then
	mkdir -p "$OPENRA_DIR/mods"
	ln -sfn "$OUT" "$OPENRA_DIR/mods/tgmc"
	echo "linked $OPENRA_DIR/mods/tgmc -> $OUT"
fi

if [ -n "${INSTALL_TO:-}" ]; then
	rm -rf "$INSTALL_TO"
	mkdir -p "$INSTALL_TO"
	cp -R "$OUT/." "$INSTALL_TO/"
	echo "copied $OUT -> $INSTALL_TO"
fi
echo "built $OUT"
