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

    # Sounds named with a .ogg extension in the rules (Report, ImpactSounds, AmbientSound). The audio folder is its own
    # package, so a sound is its bare file name.
    sound_refs = set(re.findall(r"(?<![\w/])([a-z][\w-]*\w)\.ogg", all_rules))
    for name in sorted(sound_refs - set(build_sounds.SOUNDS)):
        errors.append(f"sound {name}.ogg is used by a rule but build_sounds.py does not make it")

    # Notification pools and music files are bare names (the extension comes from DefaultVariant and Extension)
    for line in read("audio", "notifications.yaml").splitlines():
        m = re.match(r"^\t\t([A-Za-z]+): ([a-z][\w, -]*)$", line)
        if m:
            for clip in (c.strip() for c in m.group(2).split(",")):
                if clip not in build_sounds.SOUNDS:
                    errors.append(f"notification {m.group(1)}: {clip} is not made by build_sounds.py")
    for clip in re.findall(r"^\tFilename: (\S+)", read("audio", "music.yaml"), re.M):
        if clip not in build_sounds.SOUNDS:
            errors.append(f"music track {clip} is not made by build_sounds.py")

    # Voice clips that sit behind a Prefixes list: <prefix><clip> must exist for every prefix of the set
    current, section, prefixes, clips = None, None, [], {}
    for raw in read("audio", "voices.yaml").splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if not line.startswith("\t"):
            current, section, prefixes = line.rstrip(":"), None, []
            continue
        key = line.strip()
        if line.startswith("\t\t"):
            name, _, value = key.partition(":")
            if section == "Prefixes":
                prefixes = [v.strip() for v in value.split(",")]
            elif section == "Voices":
                for clip in (v.strip() for v in value.split(",")):
                    for prefix in (prefixes or [""]):
                        full = prefix + clip
                        if full not in build_sounds.SOUNDS:
                            errors.append(f"voice set {current} {name}: {full} is not made by build_sounds.py")
            continue
        section = key.rstrip(":")

    # Every Speech and Sounds notification name used by a rule must be defined
    notifications = read("audio", "notifications.yaml")
    defined = set(re.findall(r"^\t\t([A-Za-z]+):", notifications, re.M))
    used = set(re.findall(r"(?:Audio|Notification): ([A-Za-z]+)$", all_rules, re.M))
    used |= set(re.findall(r"(?:WinNotification|LoseNotification|LeaveNotification): ([A-Za-z]+)$", all_rules, re.M))
    for n in sorted(used - defined):
        errors.append(f"notification {n} is used by a rule but not defined in audio/notifications.yaml")

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
