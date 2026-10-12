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


def check_death_types(rules, weapons, seqs):
    """WithDeathAnimation picks `die` + a suffix by the killing warhead's damage type, and plays nothing when the type is
    not listed. So every actor with that trait (own or inherited) must list each DamageTypes value a weapon uses, and
    must have the sequence each entry names."""
    blocks = {m.group(1): m.group(2)
              for m in re.finditer(r"^(\^?[A-Za-z][\w-]*):[ \t]*\n((?:[ \t]+.*\n|[ \t]*\n|#.*\n)*)", rules + "\n", re.M)}

    def chain(name):  # the actor, then its ancestors, nearest first
        out, todo = [], [name]
        while todo:
            n = todo.pop(0)
            if n in blocks and n not in out:
                out.append(n)
                todo += re.findall(r"^\tInherits(?:@\w+)?: (\S+)", blocks[n], re.M)
        return out

    used = set()
    for m in re.finditer(r"^\s+DamageTypes: (.+)$", weapons, re.M):
        used |= {t.strip() for t in m.group(1).split(",")}
    errors = []
    for actor in sorted(seqs):
        bodies = [blocks[n] for n in chain(actor)]
        if not any("WithDeathAnimation" in b for b in bodies):
            continue
        listed = {}
        for b in reversed(bodies):  # farthest ancestor first, so the nearest entry wins
            m = re.search(r"^\t\tDeathTypes:\n((?:\t\t\t.*\n)*)", b, re.M)
            if m:
                listed.update(re.findall(r"^\t\t\t(\w+): (\S+)", m.group(1), re.M))
        for t, suffix in listed.items():
            if "die" + suffix not in seqs[actor]:
                errors.append(f"{actor} maps {t} to sequence die{suffix}, which build_sprites.py does not make for it")
        for t in sorted(used - set(listed)):
            errors.append(f"{actor} has no DeathTypes entry for damage type {t}, so a kill by it plays no death animation")
    return errors


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

    # The music script names tracks by their music.yaml key, and every track in the playlist should be in one of its pools
    keys = top_level_keys(read("audio", "music.yaml"))
    scripted = set(re.findall(r'"((?:theme|ambient)-[a-z0-9-]+)"', read("scripts", "music.lua")))
    for track in sorted(scripted - keys):
        errors.append(f"scripts/music.lua plays {track}, which is not in audio/music.yaml")
    for track in sorted(keys - scripted):
        errors.append(f"music track {track} is in audio/music.yaml but no pool in scripts/music.lua plays it")

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
    # Effect actors drawn without TGMC art (make_placeholders.py) are declared in tgmc/sequences/*.yaml: each top-level
    # key is an actor and each tab-indented key under it is one of its sequences.
    seq_dir = os.path.join(MOD, "sequences")
    for fn in sorted(os.listdir(seq_dir)):
        if not fn.endswith(".yaml"):
            continue
        actor = None
        for line in read("sequences", fn).splitlines():
            if re.match(r"^[A-Za-z][\w-]*:\s*$", line):
                actor = line.split(":")[0]
                seqs.setdefault(actor, set())
            elif actor and (m := re.match(r"^	([A-Za-z][\w-]*):\s*$", line)):
                seqs[actor].add(m.group(1))
    actor = None
    for line in all_rules.splitlines():
        if re.match(r"^\^?[A-Za-z][\w-]*:\s*$", line):
            actor = line.rstrip(": \t")
        m = re.match(r"^\s+(?:Sequence|MoveSequence|StandSequences|DefaultAttackSequence|DeathSequence|Sequences): ([\w, ]+)$", line)
        if m and actor in seqs:
            for s in (x.strip() for x in m.group(1).split(",")):
                if s not in seqs[actor]:
                    errors.append(f"{actor} asks for sequence {s}, which build_sprites.py does not make for it")

    errors += check_death_types(all_rules, rules["weapons.yaml"], seqs)

    # Muzzle flashes come from the actor's own sheet, so the actor must make the sequence its Armament names
    actor = None
    for line in all_rules.splitlines():
        if re.match(r"^\^?[A-Za-z][\w-]*:\s*$", line):
            actor = line.rstrip(": \t")
        m = re.match(r"^\s+MuzzleSequence: (\S+)$", line)
        if m and m.group(1) not in seqs.get(actor, ()):
            errors.append(f"{actor} has MuzzleSequence {m.group(1)}, which build_sprites.py does not make for it")

    # Weapon images: a projectile's Image and Sequences, and a CreateEffect's Image and Explosions, must be sequences
    # that build_sprites.py makes (a projectile with no Sequences plays "idle"; an effect with no Image would play "explosion")
    weapon, block, image, names = None, None, None, None

    def check_block():
        if block is None or (image is None and names is None):
            return
        if block == "Projectile" and image is None:
            return
        if image is None and block != "Projectile":
            errors.append(f"{weapon} {block} names Explosions but no Image, so it looks in the engine's own 'explosion' image")
        elif image not in seqs:
            errors.append(f"{weapon} {block} uses image {image}, which build_sprites.py does not make")
        else:
            for n in (names if names is not None else (["idle"] if block == "Projectile" else [])):
                if n not in seqs[image]:
                    errors.append(f"{weapon} {block} asks for {image} sequence {n}, which build_sprites.py does not make")

    for line in read("rules", "weapons.yaml").splitlines() + ["X:"]:
        if re.match(r"^[A-Za-z^][\w-]*:", line) or re.match(r"^\t(Warhead@\S+|Projectile):", line):
            check_block()
            block, image, names = None, None, None
            if line[0] != "\t":
                weapon = line.split(":")[0]
            else:
                block = line.strip().split(":")[0]
        m = re.match(r"^\t\t(Image|Explosions|Sequences): (.+)$", line)
        if m and block:
            if m.group(1) == "Image":
                image = m.group(2).strip()
            else:
                names = [x.strip() for x in m.group(2).split(",")]

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
