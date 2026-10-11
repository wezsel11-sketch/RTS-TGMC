#!/bin/sh
# Run every scripted scenario map (build/mod/tgmc/maps/scenario-*) headless and check that each prints "TEST <name> PASS".
#
#   OPENRA_DIR=/path/to/OpenRA  mod/test_scenarios.sh [seconds-per-scenario]
#
# Each scenario is a map built by make_placeholders.py with a Lua script from mod/scenarios. The game runs in real
# time at best (25 ticks a second), so each one is stopped once it prints PASS or FAIL, or after the ceiling in seconds
# (default 150). Needs Xvfb and a built OpenRA. The slow AI-vs-AI match is balance-aivai, run by mod/balance.sh instead.
set -u

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
OPENRA_DIR=${OPENRA_DIR:?set OPENRA_DIR to a built OpenRA checkout}
WAIT=${1:-150}
OUT=${SMOKE_OUT:-"$ROOT/build/scenarios"}
fail=0

rm -rf "$OUT"
export LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy

# Each scenario runs in its own Xvfb and support dir, several at once. SCENARIO_JOBS (default 4) caps the parallelism.
JOBS=${SCENARIO_JOBS:-4}
run_one() {
	name=$1
	support="$OUT/$name/support"
	uid=$(cd "$OPENRA_DIR" && sh utility.sh tgmc --map-hash "$ROOT/build/mod/tgmc/maps/$name" | tail -1)
	mkdir -p "$support"
	xvfb-run -a -s "-screen 0 1280x800x24" sh -c "
		cd '$OPENRA_DIR'
		exec dotnet bin/OpenRA.dll Engine.EngineDir=.. Engine.SupportDir='$support' \
			Game.Mod=tgmc Game.ViewportEdgeScroll=False Launch.Map=$uid > '$OUT/$name/game.log' 2>&1
	" >/dev/null 2>&1 &
	runner=$!
	# Stop as soon as the script reports (a loaded machine runs the game slower than real time), or at the ceiling.
	waited=0
	while [ "$waited" -lt "$WAIT" ]; do
		if grep -qE "TEST .* (PASS|FAIL)|Fatal Lua Error|LuaException" "$OUT/$name/game.log" 2>/dev/null; then
			break
		fi
		sleep 2
		waited=$((waited + 2))
	done
	pkill -f "Engine.SupportDir=$support" 2>/dev/null
	kill "$runner" 2>/dev/null
	wait "$runner" 2>/dev/null
}

running=0
for dir in "$ROOT"/build/mod/tgmc/maps/scenario-*/; do
	run_one "$(basename "$dir")" &
	running=$((running + 1))
	if [ "$running" -ge "$JOBS" ]; then
		wait
		running=0
	fi
done
wait

for dir in "$ROOT"/build/mod/tgmc/maps/scenario-*/; do
	name=$(basename "$dir")
	line=$(grep -h "TEST " "$OUT/$name/game.log" | sed 's/^Lua debug: //' | head -3)
	if echo "$line" | grep -q "PASS"; then
		echo "pass  $name: $(echo "$line" | grep PASS | head -1)"
	else
		echo "FAIL  $name: ${line:-no TEST line printed}"
		grep -h "Lua\|Error\|Exception" "$OUT/$name/game.log" | head -5
		ls "$OUT/$name"/support/Logs/exception* >/dev/null 2>&1 && sed -n 7,10p "$OUT/$name"/support/Logs/exception*
		fail=1
	fi
done
exit $fail
