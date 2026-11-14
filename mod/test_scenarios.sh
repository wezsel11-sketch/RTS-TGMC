#!/bin/sh
# Run the scripted scenario maps (build/dev-maps/scenario-*) headless and check that each prints "TEST <name> PASS".
#
#   OPENRA_DIR=/path/to/OpenRA  mod/test_scenarios.sh [seconds-per-scenario] [name-part ...]
#
# With name parts only the maps whose name contains one of them run: `mod/test_scenarios.sh 150 ability veterancy`.
# Each scenario is a map built by make_placeholders.py (into build/dev-maps, out of the game's menus) with a Lua script from
# mod/scenarios. TGMC_FAST=1 (the default here) runs the sim as fast as the CPU allows and draws nothing; TGMC_FAST=0 runs it at
# game speed (25 ticks a second at best). Each run stops once it prints PASS or FAIL, or at the ceiling in seconds (default 150).
# Uses xvfb-run when installed, else SDL's offscreen driver. SCENARIO_JOBS (default 4) caps how many run at once. DEV_MAPS points at
# another dev-maps folder (default build/dev-maps).
# The slow AI-vs-AI match is balance-aivai, run by mod/balance.sh instead.
set -u

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
OPENRA_DIR=${OPENRA_DIR:?set OPENRA_DIR to a built OpenRA checkout}
OUT=${SMOKE_OUT:-"$ROOT/build/scenarios"}
MAPS=${DEV_MAPS:-"$ROOT/build/dev-maps"}
export LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy TGMC_FAST=${TGMC_FAST:-1}
[ -d "$ROOT/build/tools/dotnet" ] && export PATH="$ROOT/build/tools/dotnet:$PATH" DOTNET_ROOT="$ROOT/build/tools/dotnet"
export DOTNET_CLI_TELEMETRY_OPTOUT=1

# One scenario, in its own support dir (its own copy of the map, logs and settings): --one <map-name> <ceiling-seconds>
if [ "${1:-}" = "--one" ]; then
	name=$2
	wait_s=$3
	support="$OUT/$name/support"
	mkdir -p "$support/maps/tgmc/{DEV_VERSION}"
	cp -r "$MAPS/$name" "$support/maps/tgmc/{DEV_VERSION}/"
	uid=$(cd "$OPENRA_DIR" && sh utility.sh tgmc --map-hash "$support/maps/tgmc/{DEV_VERSION}/$name" | tail -1)
	cmd="cd '$OPENRA_DIR' && exec dotnet bin/OpenRA.dll Engine.EngineDir=.. Engine.SupportDir='$support' \
		Game.Mod=tgmc Game.ViewportEdgeScroll=False Launch.Map=$uid > '$OUT/$name/game.log' 2>&1"
	if command -v xvfb-run >/dev/null 2>&1; then
		xvfb-run -a -s "-screen 0 1280x800x24" sh -c "$cmd" >/dev/null 2>&1 &
	else
		SDL_VIDEODRIVER=offscreen sh -c "$cmd" >/dev/null 2>&1 &
	fi
	runner=$!
	# Stop as soon as the script reports (a loaded machine runs the game slower than real time), or at the ceiling.
	waited=0
	while [ "$waited" -lt "$wait_s" ]; do
		if grep -qE "TEST .* (PASS|FAIL)|Fatal Lua Error|LuaException" "$OUT/$name/game.log" 2>/dev/null; then
			# Scripts with several cases print them together: give the rest a moment to land.
			sleep 1
			break
		fi
		# The game quit or crashed on its own (an exception at start-up): nothing more will come.
		kill -0 "$runner" 2>/dev/null || break
		sleep 1
		waited=$((waited + 1))
	done
	pkill -f "Engine.SupportDir=$support" 2>/dev/null
	kill "$runner" 2>/dev/null
	wait "$runner" 2>/dev/null
	exit 0
fi

WAIT=${1:-150}
[ $# -gt 0 ] && shift
rm -rf "$OUT"
mkdir -p "$OUT"

names=""
for dir in "$MAPS"/scenario-*/; do
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
[ -n "$names" ] || { echo "no scenario maps in $MAPS match: run mod/build_mod.sh first"; exit 1; }

start=$(date +%s)
# shellcheck disable=SC2086
printf '%s\n' $names | xargs -P "${SCENARIO_JOBS:-4}" -I{} sh "$0" --one {} "$WAIT"

# Timing-sensitive scenarios (the AI ones) can fail when four run at once on a loaded machine: one that failed without an
# exception runs once more, alone, and its result line says so.
retried=""
for name in $names; do
	ls "$OUT/$name"/support/Logs/exception* >/dev/null 2>&1 && continue
	lines=$(grep -h "TEST " "$OUT/$name/game.log" 2>/dev/null)
	if [ -z "$lines" ] || echo "$lines" | grep -q " FAIL"; then
		cp "$OUT/$name/game.log" "$OUT/$name/game-first-try.log" 2>/dev/null
		sh "$0" --one "$name" "$WAIT"
		retried="$retried $name "
	fi
done

fail=0
passed=0
total=0
for name in $names; do
	total=$((total + 1))
	lines=$(grep -h "TEST " "$OUT/$name/game.log" 2>/dev/null | sed 's/^Lua debug: //')
	badsound=$(grep -hE "does not exist|not a valid sound" "$OUT/$name/support/Logs/sound.log" "$OUT/$name/game.log" 2>/dev/null | head -2)
	if [ -n "$badsound" ]; then
		echo "FAIL  $name: a sound did not load"
		echo "$badsound"
		fail=1
	elif ls "$OUT/$name"/support/Logs/exception* >/dev/null 2>&1; then
		# A missing sprite sequence only throws when it renders, which can be after the script printed PASS
		echo "FAIL  $name: the engine logged an exception"
		sed -n 7,10p "$OUT/$name"/support/Logs/exception*
		fail=1
	elif [ -n "$lines" ] && ! echo "$lines" | grep -q " FAIL"; then
		case "$retried" in *" $name "*) lines="$lines (second try, alone)" ;; esac
		echo "pass  $name: $(echo "$lines" | head -1)"
		passed=$((passed + 1))
	else
		echo "FAIL  $name: ${lines:-no TEST line printed}"
		grep -h "Lua\|Error\|Exception" "$OUT/$name/game.log" | grep -v "^Lua debug: TEST" | head -5
		fail=1
	fi
done
echo "$passed of $total passed in $(( $(date +%s) - start )) s (TGMC_FAST=$TGMC_FAST, logs in $OUT)"
exit $fail
