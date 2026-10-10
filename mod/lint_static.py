"""Cross-reference check for the mod's YAML, with no OpenRA needed.

It catches dangling names that OpenRA's own lint would also report: sounds that build_sounds.py does not make,
weapons and voice sets that are not defined, Fluent keys missing from tgmc.ftl, and sequence names that
build_sprites.py does not produce. It does not replace `mod/check_mod.sh`; it is the check you can run anywhere.

Usage: lint_static.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
MOD = os.path.join(ROOT, "tgmc")
sys.path.insert(0, HERE)
import build_sounds  # noqa: E402
import build_sprites  # noqa: E402


def read(*parts):
    with open(os.path.join(MOD, *parts), encoding="utf-8") as f:
        return f.read()


def top_level_keys(text):
    return set(re.findall(r"^([^\s#][^:]*):", text, re.M))


def main():
    errors = []
    rules = {n: read("rules", n) for n in os.listdir(os.path.join(MOD, "rules"))}
    all_rules = "\n".join(rules.values())
    ftl = read("fluent", "tgmc.ftl")
    chrome = "\n".join(read("chrome", n) for n in os.listdir(os.path.join(MOD, "chrome")))

    # Sounds: bare name, with or without .ogg, under audio/
    sound_refs = set(re.findall(r"audio/([\w-]+)(?:\.ogg)?", all_rules + read("audio", "notifications.yaml") + read("audio", "voices.yaml")))
    for name in sorted(sound_refs - set(build_sounds.SOUNDS)):
        errors.append(f"sound audio/{name} is used but build_sounds.py does not make it")

    # Weapons
    weapons = top_level_keys(rules["weapons.yaml"])
    for w in sorted(set(re.findall(r"^\s*Weapon: (\S+)", all_rules, re.M)) - weapons):
        errors.append(f"weapon {w} is not defined in weapons.yaml")

    # Voice sets
    voices = top_level_keys(read("audio", "voices.yaml"))
    for v in sorted(set(re.findall(r"VoiceSet: (\S+)", all_rules)) - voices):
        errors.append(f"voice set {v} is not defined in audio/voices.yaml")

    # Fluent keys: `Name: actor-x.name`, `Description: actor-x.description`, hud-*, bot-*, faction-*
    ftl_keys = set()
    cur = None
    for line in ftl.splitlines():
        m = re.match(r"^([\w-]+) =\s*(.*)$", line)
        if m:
            cur = m.group(1)
            if m.group(2):
                ftl_keys.add(cur)
        elif cur and (m := re.match(r"^\s+\.([\w-]+) =", line)):
            ftl_keys.add(f"{cur}.{m.group(1)}")
    refs = set(re.findall(r"(?:Name|Description|Text): ((?:actor|bot|faction|hud|tileset)-[\w.-]+)", all_rules + chrome))
    for k in sorted(refs - ftl_keys):
        errors.append(f"Fluent key {k} is not in tgmc.ftl")

    # Sequences: the actors that build_sprites.py makes, and the sequence names the rules ask for
    seqs = {u: set(spec["sequences"]) for u, spec in build_sprites.UNITS.items()}
    actor = None
    for line in all_rules.splitlines():
        if re.match(r"^\^?[A-Za-z][\w-]*:\s*$", line):
            actor = line.rstrip(": \t")
        m = re.match(r"^\s+(?:Sequence|MoveSequence|StandSequences|DefaultAttackSequence|DeathSequence|Sequences): ([\w, ]+)$", line)
        if m and actor in seqs:
            for s in (x.strip() for x in m.group(1).split(",")):
                if s not in seqs[actor]:
                    errors.append(f"{actor} asks for sequence {s}, which build_sprites.py does not make for it")

    # Every Buildable actor needs an icon sequence
    for m in re.finditer(r"^([a-z][\w-]*):\n((?:\t.*\n|\n)*)", all_rules, re.M):
        if "Buildable:" in m.group(2) and "icon" not in seqs.get(m.group(1), ()):
            errors.append(f"{m.group(1)} is Buildable but has no icon sequence")

    for e in errors:
        print("error:", e)
    print(f"lint_static: {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
