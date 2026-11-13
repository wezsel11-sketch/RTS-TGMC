#!/bin/sh
# Start TGMC: Marines vs Xenos from the unpacked Linux package. Extra arguments go to OpenRA (for example Launch.Map=<map hash>).
cd "$(dirname "$0")" || exit 1
exec ./OpenRA Game.Mod=tgmc Engine.EngineDir=. "$@"
