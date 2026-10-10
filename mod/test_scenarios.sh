#!/bin/sh
# Run the scripted scenario maps (heal, repair, mend, victory, combat) headless and check that each prints "TEST <name> PASS".
#
#   OPENRA_DIR=/path/to/OpenRA  mod/test_scenarios.sh [seconds-per-scenario]
#
# Each scenario is a map built by make_placeholders.py with a Lua script from mod/scenarios. The game runs in real
# time (25 ticks a second), so the default of 45 seconds covers the longest script. Needs Xvfb and a built OpenRA.
set -u

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
OPENRA_DIR=${OPENRA_DIR:?set OPENRA_DIR to a built OpenRA checkout}
WAIT=${1:-45}
OUT=${SMOKE_OUT:-"$ROOT/build/scenarios"}
fail=0

rm -rf "$OUT"
for dir in "$ROOT"/build/mod/tgmc/maps/scenario-*/; do
	name=$(basename "$dir")
	uid=$(cd "$OPENRA_DIR" && sh utility.sh tgmc --map-hash "${dir%/}" | tail -1)
	mkdir -p "$OUT/$name/support"
	export LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy
	xvfb-run -a -s "-screen 0 1280x800x24" sh -c "
		cd '$OPENRA_DIR'
		timeout $WAIT dotnet bin/OpenRA.dll Engine.EngineDir=.. Engine.SupportDir='$OUT/$name/support' \
			Game.Mod=tgmc Game.ViewportEdgeScroll=False Launch.Map=$uid > '$OUT/$name/game.log' 2>&1
	" >/dev/null 2>&1
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
