#!/bin/sh
# Launch the built mod headless on one map, screenshot it, and fail if the engine wrote an exception log.
#
#   OPENRA_DIR=/path/to/OpenRA  mod/smoke.sh [map-folder-name] [seconds-to-wait]
#
# Needs Xvfb (xvfb-run), ImageMagick (import) and a built OpenRA with the mod linked by build_mod.sh.
# Mesa software GL and a dummy audio driver stand in for a GPU and a sound card. Edge scrolling is off because
# Xvfb parks the pointer at the top-left corner, which would scroll the camera away from the base. The screenshot and logs
# go to $SMOKE_OUT (default build/smoke). Exits non-zero on an exception log.
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
OPENRA_DIR=${OPENRA_DIR:?set OPENRA_DIR to a built OpenRA checkout}
MAP=${1:-landing-zone}
WAIT=${2:-30}
OUT=${SMOKE_OUT:-"$ROOT/build/smoke"}

rm -rf "$OUT"
mkdir -p "$OUT/support"
UID_HASH=$(cd "$OPENRA_DIR" && sh utility.sh tgmc --map-hash "$ROOT/build/mod/tgmc/maps/$MAP" | tail -1)

export LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy
xvfb-run -a -s "-screen 0 1280x800x24" sh -c "
	cd '$OPENRA_DIR'
	timeout $((WAIT + 20)) dotnet bin/OpenRA.dll Engine.EngineDir=.. Engine.SupportDir='$OUT/support' \
		Game.Mod=tgmc Game.ViewportEdgeScroll=False Launch.Map=$UID_HASH > '$OUT/game.log' 2>&1 &
	sleep $WAIT
	import -window root '$OUT/$MAP.png'
" || true

if ls "$OUT"/support/Logs/exception*.log >/dev/null 2>&1; then
	echo "smoke: engine exception on $MAP"
	sed -n 7,12p "$OUT"/support/Logs/exception*.log
	exit 1
fi
echo "smoke: $MAP ran for ${WAIT}s without an exception; screenshot $OUT/$MAP.png"
