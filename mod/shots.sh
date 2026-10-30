#!/bin/sh
# Take the screenshots of the shot-* dev maps (each one sets up a view and saves a screenshot at a set tick: see ScreenshotAt in
# tgmc/code/Hud.cs) and copy them to build/shots/<map>.png, to look at the HUD and effects without playing.
#
#   OPENRA_DIR=/path/to/OpenRA  mod/shots.sh [name-part ...]        e.g. mod/shots.sh card hud codex
#
# With no name parts every shot map runs. SHOT_SIZE (default 1280,800) is the window size. Runs at game speed, drawing: TGMC_FAST
# is off here, since a screenshot needs the frame. SHOT_JOBS (default 4) caps how many run at once.
set -u

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
OPENRA_DIR=${OPENRA_DIR:?set OPENRA_DIR to a built OpenRA checkout}
OUT="$ROOT/build/shots"
MAPS="$ROOT/build/dev-maps"
export LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy SDL_VIDEODRIVER=offscreen TGMC_FAST=0
[ -d "$ROOT/build/tools/dotnet" ] && export PATH="$ROOT/build/tools/dotnet:$PATH" DOTNET_ROOT="$ROOT/build/tools/dotnet"
export DOTNET_CLI_TELEMETRY_OPTOUT=1

if [ "${1:-}" = "--one" ]; then
	name=$2
	support="$OUT/run/$name"
	rm -rf "$support"
	mkdir -p "$support/maps/tgmc/{DEV_VERSION}"
	cp -r "$MAPS/$name" "$support/maps/tgmc/{DEV_VERSION}/"
	uid=$(cd "$OPENRA_DIR" && sh utility.sh tgmc --map-hash "$support/maps/tgmc/{DEV_VERSION}/$name" | tail -1)
	sh -c "cd '$OPENRA_DIR' && exec dotnet bin/OpenRA.dll Engine.EngineDir=.. Engine.SupportDir='$support' Game.Mod=tgmc \
		Game.ViewportEdgeScroll=False Graphics.Mode=Windowed Graphics.WindowedSize=${SHOT_SIZE:-1280,800} Launch.Map=$uid" > "$support/game.log" 2>&1 &
	runner=$!
	waited=0
	while [ "$waited" -lt 120 ]; do
		shot=$(find "$support/Screenshots" -name '*.png' 2>/dev/null | head -1)
		if [ -n "$shot" ]; then
			# The file is written by another thread: let it finish.
			sleep 2
			cp "$shot" "$OUT/$name.png"
			echo "shot  $OUT/$name.png"
			break
		fi
		kill -0 "$runner" 2>/dev/null || { echo "FAIL  $name: the game quit before the shot (see $support/game.log)"; break; }
		grep -q "Fatal Lua Error" "$support/game.log" 2>/dev/null && { echo "FAIL  $name: $(grep -m1 "Fatal Lua Error" "$support/game.log")"; break; }
		sleep 1
		waited=$((waited + 1))
	done
	[ "$waited" -ge 120 ] && echo "FAIL  $name: no screenshot in 120 s"
	pkill -f "Engine.SupportDir=$support" 2>/dev/null
	kill "$runner" 2>/dev/null
	wait "$runner" 2>/dev/null
	exit 0
fi

mkdir -p "$OUT"
names=""
for dir in "$MAPS"/shot-*/; do
	name=$(basename "$dir")
	if [ $# -gt 0 ]; then
		keep=0
		for part in "$@"; do
			case "$name" in *"$part"*) keep=1 ;; esac
		done
		[ "$keep" = 1 ] || continue
	fi
	names="$names $name"
done
[ -n "$names" ] || { echo "no shot maps in $MAPS match: run mod/build_mod.sh first"; exit 1; }
# shellcheck disable=SC2086
printf '%s\n' $names | xargs -P "${SHOT_JOBS:-4}" -I{} sh "$0" --one {}
