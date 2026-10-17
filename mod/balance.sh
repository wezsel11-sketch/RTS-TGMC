#!/bin/sh
# Run several matches of a balance map in parallel and summarise who won and when. The game seed is random, so a set of
# runs shows the spread, not one lucky result.
#
#   OPENRA_DIR=/path/to/OpenRA  mod/balance.sh [runs] [ceiling-seconds] [map]
#
# The map is balance-aivai (default: the Skirmish AI on both sides) or balance-holdline (the marine bot defending against
# the six waves). Prints one line per run (result and tick) and then the counts. Per-run logs, with a STAT line every 500 ticks, go to
# $BALANCE_OUT (default build/balance). Needs Xvfb and a built OpenRA with the mod linked.
set -u

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
OPENRA_DIR=${OPENRA_DIR:?set OPENRA_DIR to a built OpenRA checkout}
RUNS=${1:-4}
CEILING=${2:-400}
MAP=${3:-balance-aivai}
OUT=${BALANCE_OUT:-"$ROOT/build/balance"}

rm -rf "$OUT"
export LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy SDL_VIDEODRIVER=offscreen
export PATH="$ROOT/build/tools/dotnet:$PATH" DOTNET_ROOT="$ROOT/build/tools/dotnet" DOTNET_CLI_TELEMETRY_OPTOUT=1
mkdir -p "$OUT/maps/tgmc/{DEV_VERSION}"; cp -r "$ROOT/build/dev-maps/$MAP" "$OUT/maps/tgmc/{DEV_VERSION}/$MAP"; uid=$(cd "$OPENRA_DIR" && sh utility.sh tgmc --map-hash "$OUT/maps/tgmc/{DEV_VERSION}/$MAP" | tail -1)

run_one() {
	n=$1
	support="$OUT/run$n/support"
	mkdir -p "$support/maps/tgmc/{DEV_VERSION}"; cp -r "$ROOT/build/dev-maps/$MAP" "$support/maps/tgmc/{DEV_VERSION}/$MAP"
	sh -c "
		cd '$OPENRA_DIR'
		exec dotnet bin/OpenRA.dll Engine.EngineDir=.. Engine.SupportDir='$support' \\
			Game.Mod=tgmc Launch.Map=$uid > '$OUT/run$n/game.log' 2>&1
	" >/dev/null 2>&1 &
	runner=$!
	waited=0
	while [ "$waited" -lt "$CEILING" ]; do
		grep -qE "TEST (aivai|holdline)|Fatal Lua Error|LuaException" "$OUT/run$n/game.log" 2>/dev/null && break
		sleep 3
		waited=$((waited + 3))
	done
	pkill -f "Engine.SupportDir=$support" 2>/dev/null
	kill "$runner" 2>/dev/null
	wait "$runner" 2>/dev/null
}

n=1
while [ "$n" -le "$RUNS" ]; do
	run_one "$n" &
	n=$((n + 1))
done
wait

marines=0
xenos=0
other=0
n=1
while [ "$n" -le "$RUNS" ]; do
	line=$(grep -hE "TEST (aivai|holdline)" "$OUT/run$n/game.log" | sed 's/^Lua debug: //' | head -1)
	last=$(grep -h "STAT" "$OUT/run$n/game.log" | tail -1 | sed 's/^Lua debug: //')
	echo "run $n: ${line:-no result}"
	echo "        last: $last"
	case "$line" in
		*"marines won"*) marines=$((marines + 1)) ;;
		*"xenos won"* | *"marines lost"*) xenos=$((xenos + 1)) ;;
		*) other=$((other + 1)) ;;
	esac
	n=$((n + 1))
done
echo "$MAP: marines won $marines, xenos won $xenos, other $other"
