#!/usr/bin/env python3
"""Start the game on any platform (Windows: play.cmd, Linux and macOS: mod/play.sh does the same).

    python mod/play.py                  main menu
    python mod/play.py landing-zone     straight into a map (landing-zone, canyon-run, jungle-crossing, close-quarters, great-plains,
                                        lv-624, big-red, whiskey-outpost, desert-dam, fiorina, hold-the-line, test-field, and the -full versions)
    python mod/play.py landing-zone Game.Mod=...   anything after the map (or after --) goes to OpenRA unchanged

Run bootstrap.py (setup.cmd) first. Settings, logs and replays go to OpenRA's usual support directory, not into this repo.
"""
import os
import subprocess
import sys

import buildlib as b


def main(argv):
    if not os.path.isfile(os.path.join(b.BUILD, ".openra-built")) or not os.path.isdir(os.path.join(b.MOD_OUT, "maps")):
        print("play: the mod is not built yet. Run setup.cmd (or mod/setup.sh) first.", file=sys.stderr)
        return 1
    b.use_local_dotnet()
    map_name = None
    if argv and argv[0] != "--":
        map_name, argv = argv[0], argv[1:]
    if argv[:1] == ["--"]:
        argv = argv[1:]

    args = ["Game.Mod=tgmc"]
    if map_name:
        folder = os.path.join(b.MOD_OUT, "maps", map_name)
        if not os.path.isdir(folder):
            shown = [m for m in sorted(os.listdir(os.path.join(b.MOD_OUT, "maps"))) if not m.startswith(("scenario-", "balance-"))]
            print(f"play: no map '{map_name}'. Available:\n  " + "\n  ".join(shown), file=sys.stderr)
            return 1
        out = b.utility("tgmc", "--map-hash", folder)
        args.append("Launch.Map=" + out.strip().splitlines()[-1])

    launch = os.path.join(b.OPENRA_DIR, "launch-game.cmd" if b.is_windows() else "launch-game.sh")
    cmd = ["dotnet", os.path.join("bin", "OpenRA.dll"), "Engine.EngineDir=..", "Engine.LaunchPath=" + launch, *args, *argv]
    return subprocess.run(cmd, cwd=b.OPENRA_DIR).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
