#!/bin/sh
# Assemble the TGMC OpenRA mod into build/mod/tgmc.
#
#   TGMC=/path/to/terragov-marine-corps  mod/build_mod.sh
#   OPENRA_DIR=/path/to/OpenRA           mod/build_mod.sh   (also links the result into $OPENRA_DIR/mods/tgmc)
#
# build/ is git-ignored. It holds TGMC-derived art and audio; never commit it.
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
TGMC=${TGMC:?set TGMC to a terragov-marine-corps checkout}
OUT="$ROOT/build/mod/tgmc"
PY=${PYTHON:-python3}

"$PY" -I "$HERE/lint_static.py"
"$PY" -I "$HERE/test_effects.py"

rm -rf "$OUT"
mkdir -p "$OUT"
cp -R "$ROOT/tgmc/." "$OUT/"

# The mod's C# traits (tgmc/code) compile against the built engine, so the mod DLL is built only when OPENRA_DIR has bin/.
if [ -n "${OPENRA_DIR:-}" ] && [ -d "$OPENRA_DIR/bin" ] && command -v dotnet >/dev/null 2>&1; then
	dotnet build "$ROOT/tgmc/code/Tgmc.csproj" -c Release -o "$ROOT/build/tgmc-dll" -p:OPENRA_BIN="$OPENRA_DIR/bin" -nologo
	cp "$ROOT/build/tgmc-dll/Tgmc.dll" "$OPENRA_DIR/bin/Tgmc.dll"
fi

"$PY" -I "$HERE/build_sprites.py" --tgmc "$TGMC" --out "$OUT"
"$PY" -I "$HERE/build_sounds.py" --tgmc "$TGMC" --out "$OUT/audio"
"$PY" -I "$HERE/build_tileset.py" --tgmc "$TGMC" --out "$OUT"
"$PY" -I "$HERE/make_placeholders.py" --tgmc "$TGMC" --out "$OUT"
"$PY" -I "$HERE/make_chrome.py" --out "$OUT"

if [ -n "${OPENRA_DIR:-}" ]; then
	mkdir -p "$OPENRA_DIR/mods"
	ln -sfn "$OUT" "$OPENRA_DIR/mods/tgmc"
	echo "linked $OPENRA_DIR/mods/tgmc -> $OUT"
fi
echo "built $OUT"
