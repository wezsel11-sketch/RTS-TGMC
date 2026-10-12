#!/bin/sh
# Start the game.
#
#   mod/play.sh                  main menu
#   mod/play.sh landing-zone     go straight into a map (landing-zone, canyon-run, jungle-crossing, close-quarters, great-plains, hold-the-line, test-field)
#   mod/play.sh landing-zone Game.Mod=...   anything after the map (or after --) goes to OpenRA unchanged
#
# Run mod/setup.sh first. Settings, logs and replays go to OpenRA's usual support directory, not into this repo.
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
OPENRA_DIR=${OPENRA_DIR:-"$ROOT/build/OpenRA"}

if [ ! -f "$ROOT/build/.openra-built" ] || [ ! -d "$ROOT/build/mod/tgmc/maps" ]; then
	echo "play: the mod is not built yet. Run mod/setup.sh first." >&2
	exit 1
fi
if [ -x "$ROOT/build/tools/dotnet/dotnet" ]; then
	DOTNET_ROOT="$ROOT/build/tools/dotnet"
	export DOTNET_ROOT PATH="$DOTNET_ROOT:$PATH"
fi
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1

map=
if [ $# -gt 0 ] && [ "$1" != "--" ]; then
	map=$1
	shift
fi
[ "${1:-}" != "--" ] || shift

cd "$OPENRA_DIR"
if [ -n "$map" ]; then
	dir="$ROOT/build/mod/tgmc/maps/$map"
	if [ ! -d "$dir" ]; then
		echo "play: no map '$map'. Available:" >&2
		ls "$ROOT/build/mod/tgmc/maps" | grep -v '^\(scenario\|balance\)-' | sed 's/^/  /' >&2
		exit 1
	fi
	hash=$(sh utility.sh tgmc --map-hash "$dir" | tail -1)
	exec sh launch-game.sh Game.Mod=tgmc "Launch.Map=$hash" "$@"
fi
exec sh launch-game.sh Game.Mod=tgmc "$@"
