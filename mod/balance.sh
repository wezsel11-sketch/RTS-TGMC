#!/bin/sh
# Run several AI-vs-AI matches of scenario-aivai in parallel and summarise who won and when. The game seed is random, so
# a set of runs shows the spread, not one lucky result.
#
#   OPENRA_DIR=/path/to/OpenRA  mod/balance.sh [runs] [ceiling-seconds]
#
# Prints one line per run (winner and tick) and then the win counts. Per-run logs, with a STAT line every 500 ticks, go to
# $BALANCE_OUT (default build/balance). Needs Xvfb and a built OpenRA with the mod linked.
set -u

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
OPENRA_DIR=${OPENRA_DIR:?set OPENRA_DIR to a built OpenRA checkout}
RUNS=${1:-4}
CEILING=${2:-400}
OUT=${BALANCE_OUT:-"$ROOT/build/balance"}

rm -rf "$OUT"
export LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy
uid=$(cd "$OPENRA_DIR" && sh utility.sh tgmc --map-hash "$ROOT/build/mod/tgmc/maps/balance-aivai" | tail -1)

run_one() {
	n=$1
	support="$OUT/run$n/support"
	mkdir -p "$support"
	xvfb-run -a -s "-screen 0 640x400x24" sh -c "
		cd '$OPENRA_DIR'
		exec dotnet bin/OpenRA.dll Engine.EngineDir=.. Engine.SupportDir='$support' \\
			Game.Mod=tgmc Launch.Map=$uid > '$OUT/run$n/game.log' 2>&1
	" >/dev/null 2>&1 &
	runner=$!
	waited=0
	while [ "$waited" -lt "$CEILING" ]; do
		grep -qE "TEST aivai|Fatal Lua Error" "$OUT/run$n/game.log" 2>/dev/null && break
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
	line=$(grep -h "TEST aivai" "$OUT/run$n/game.log" | sed 's/^Lua debug: //' | head -1)
	last=$(grep -h "STAT" "$OUT/run$n/game.log" | tail -1 | sed 's/^Lua debug: //')
	echo "run $n: ${line:-no result}"
	echo "        last: $last"
	case "$line" in
		*"marines won"*) marines=$((marines + 1)) ;;
		*"xenos won"*) xenos=$((xenos + 1)) ;;
		*) other=$((other + 1)) ;;
	esac
	n=$((n + 1))
done
echo "marines $marines, xenos $xenos, other $other"
