#!/usr/bin/env python3
"""Dev aid: make a screenshot copy of a built map, with the fog off and the camera at the given cell, so a map's look can be checked headless.

    python mod/shot_map.py big-red-full 90 80          then      run-scen.sh shot-big-red-full   (see the notes in the README on headless runs)

Writes build/mod/tgmc/maps/shot-<map>. Not part of the build; the copy is a dev map.
"""
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(name, x, y):
    src = os.path.join(ROOT, "build", "mod", "tgmc", "maps", name)
    dst = os.path.join(ROOT, "build", "dev-maps", "shot-" + name)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    with open(os.path.join(dst, "shotcam.lua"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"WorldLoaded = function()\n\tCamera.Position = Map.CenterOfCell(CPos.New({x}, {y}))\nend\n")
    # A map with its own rules (a faction start, scripts) keeps them: the shot rules are appended to them.
    old_rules = ""
    if os.path.exists(os.path.join(dst, "rules.yaml")):
        old_rules = open(os.path.join(dst, "rules.yaml"), encoding="utf-8").read().rstrip("\n") + "\n"
    with open(os.path.join(dst, "rules.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(old_rules + "World:\n\tLuaScript:\n\t\tScripts: shotcam.lua\n\tShroud:\n\t\tFogCheckboxEnabled: False\n\t\tExploredMapCheckboxEnabled: True\n"
                "\t\tFogEnabled: False\n\t\tExploredMapEnabled: True\n\tScreenshotAt:\n\t\tTick: 40\nPlayer:\n\t-ConquestVictoryConditions:\n")
    text = open(os.path.join(dst, "map.yaml"), encoding="utf-8").read()
    text = text.replace("Title: ", "Title: shot ", 1)
    # A dev copy: hidden from every menu.
    text = re.sub(r"(?m)^Visibility:.*$", "Visibility:", text)
    if "Rules:" not in text:
        text = text.replace("RequiresMod: tgmc\n", "RequiresMod: tgmc\n\nRules: rules.yaml\n", 1)
    with open(os.path.join(dst, "map.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote", dst)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
