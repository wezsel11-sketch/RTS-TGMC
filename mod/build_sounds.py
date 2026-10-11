"""Convert the TGMC sounds the mod uses into OpenRA-ready Vorbis .ogg files.

OpenRA's OggLoader plays Vorbis in an .ogg container directly. TGMC files come in mixed channel counts, rates and
loudness, so each one is re-encoded and level-matched:

  kind    encoding              peak after normalising   trimmed to
  fx      mono 22050 Hz         -3 dB                    4 s
  voice   mono 22050 Hz         -3 dB                    3 s
  ui      mono 22050 Hz         -9 dB                    2.5 s
  speech  mono 22050 Hz         -6 dB                    7 s    (the ARES announcer)
  amb     mono 22050 Hz         -16 dB                   8 s
  music   stereo 44100 Hz       -6 dB                    whole file

A sound is (source path under the TGMC checkout, kind) or (source, kind, max seconds). Each file is scaled so its
loudest sample sits at the kind's peak, which keeps weapons, voices and the interface at sensible levels relative to
one another. The levels are chosen by number, not by ear: nobody has listened to the mix yet.

SOUNDS maps the name used in the rules to its spec. Marine voices exist twice, as marine-m-<clip> and marine-f-<clip>;
the voice sets in tgmc/audio/voices.yaml pick one per marine through Prefixes.

Output (default build/mod/tgmc/audio): <name>.ogg, plus sounds.json listing sources, kinds, lengths and peaks.

Usage: build_sounds.py --tgmc CHECKOUT [--out DIR]
"""
import argparse
import json
import os
import re
import subprocess

KINDS = {
    #          channels, rate,  peak dB, default max seconds, vorbis quality
    "fx": (1, 22050, -3.0, 4.0, 4),
    "voice": (1, 22050, -3.0, 3.0, 4),
    "ui": (1, 22050, -9.0, 2.5, 4),
    "speech": (1, 22050, -6.0, 7.0, 4),
    "amb": (1, 22050, -16.0, 8.0, 4),
    "music": (2, 44100, -6.0, None, 5),
}

W = "sound/weapons"
G = "sound/weapons/guns/fire"
V = "sound/voice"
A = "sound/voice/alien"
EF = "sound/effects"

SOUNDS = {
    # Weapons: rifle (three T-18/M41A shots), sentry, claws, acid
    "rifle-fire-1": (f"{G}/t18.ogg", "fx"),
    "rifle-fire-2": (f"{G}/m41a_1.ogg", "fx"),
    "rifle-fire-3": (f"{G}/m41a_2.ogg", "fx"),
    "sentry-fire": (f"{G}/smartgun1.ogg", "fx"),
    "claw-swipe-1": (f"{W}/alien_claw_flesh1.ogg", "fx"),
    "claw-swipe-2": (f"{W}/alien_claw_flesh2.ogg", "fx"),
    "claw-swipe-3": (f"{W}/alien_claw_flesh3.ogg", "fx"),
    "acid-spit-1": (f"{A}/spitacid.ogg", "fx"),
    "acid-spit-2": (f"{A}/spitacid2.ogg", "fx"),
    "acid-impact": ("sound/bullets/acid_impact1.ogg", "fx", 2.0),
    "heal": ("sound/items/hypospray.ogg", "fx"),
    "repair": ("sound/items/welder.ogg", "fx"),
    "resin-build": (f"{EF}/alien/resin_build1.ogg", "fx"),
    # Impacts
    "hit-bullet-1": ("sound/bullets/bullet_impact1.ogg", "fx", 1.0),
    "hit-bullet-2": ("sound/bullets/bullet_impact2.ogg", "fx", 1.0),
    "hit-bullet-3": ("sound/bullets/bullet_impact3.ogg", "fx", 1.0),
    "hit-bullet-4": ("sound/bullets/bullet_impact4.ogg", "fx", 1.0),
    "hit-armor-1": ("sound/bullets/bullet_armor1.ogg", "fx", 1.0),
    "hit-armor-2": ("sound/bullets/bullet_armor2.ogg", "fx", 1.0),
    "hit-armor-3": ("sound/bullets/bullet_armor3.ogg", "fx", 1.0),
    # Explosions and structure deaths
    "explosion-1": (f"{EF}/explosion/medium1.ogg", "fx"),
    "explosion-2": (f"{EF}/explosion/medium2.ogg", "fx"),
    "explosion-3": (f"{EF}/explosion/medium3.ogg", "fx"),
    "explosion-big": (f"{EF}/explosion/large1.ogg", "fx"),
    "turret-death": (f"{EF}/alien/turret_death.ogg", "fx"),
    "resin-break-1": (f"{EF}/alien/resin_break1.ogg", "fx"),
    "resin-break-2": (f"{EF}/alien/resin_break2.ogg", "fx"),
    # Xeno voices. Runner: small and quick; Hunter: heavy roars; Sentinel: hisses and spits; Drone: chatter and cries.
    "xeno-roar-1": (f"{A}/roar1.ogg", "voice"),
    "xeno-roar-2": (f"{A}/roar2.ogg", "voice"),
    "xeno-roar-3": (f"{A}/roar3.ogg", "voice"),
    "xeno-roar-4": (f"{A}/roar4.ogg", "voice"),
    "xeno-roar-5": (f"{A}/roar5.ogg", "voice"),
    "xeno-roar-6": (f"{A}/roar6.ogg", "voice"),
    "xeno-roar-7": (f"{A}/roar7.ogg", "voice"),
    "xeno-roar-8": (f"{A}/roar8.ogg", "voice"),
    "xeno-roar-9": (f"{A}/roar9.ogg", "voice"),
    "xeno-roar-10": (f"{A}/roar10.ogg", "voice"),
    "xeno-roar-11": (f"{A}/roar11.ogg", "voice"),
    "xeno-roar-12": (f"{A}/roar12.ogg", "voice"),
    "xeno-growl-1": (f"{A}/growl1.ogg", "voice"),
    "xeno-growl-2": (f"{A}/growl2.ogg", "voice"),
    "xeno-growl-4": (f"{A}/growl4.ogg", "voice"),
    "xeno-hiss-1": (f"{A}/hiss1.ogg", "voice", 1.8),
    "xeno-hiss-2": (f"{A}/hiss2.ogg", "voice", 1.8),
    "xeno-hiss-3": (f"{A}/hiss3.ogg", "voice", 1.8),
    "xeno-pounce-1": (f"{A}/pounce.ogg", "voice"),
    "xeno-pounce-2": (f"{A}/pounce2.ogg", "voice"),
    "xeno-larva-1": (f"{A}/roar_larva1.ogg", "voice"),
    "xeno-larva-2": (f"{A}/roar_larva2.ogg", "voice"),
    "xeno-larva-3": (f"{A}/roar_larva3.ogg", "voice"),
    "xeno-larva-4": (f"{A}/roar_larva4.ogg", "voice"),
    "xeno-talk-1": (f"{A}/talk.ogg", "voice"),
    "xeno-talk-2": (f"{A}/talk2.ogg", "voice"),
    "xeno-talk-3": (f"{A}/talk3.ogg", "voice"),
    "xeno-help-1": (f"{A}/help1.ogg", "voice"),
    "xeno-help-2": (f"{A}/help2.ogg", "voice"),
    "xeno-yell": (f"{A}/yell_alt.ogg", "voice"),
    "xeno-death-1": (f"{A}/death.ogg", "voice"),
    "xeno-death-2": (f"{A}/death2.ogg", "voice"),
    "xeno-death-small": (f"{A}/facehugger_dies.ogg", "voice"),
    # Interface and alerts
    "ui-click": (f"{EF}/menu_click.ogg", "ui"),
    "ui-deny": ("sound/machines/buzz-two.ogg", "ui"),
    "ui-ping": ("sound/machines/ping.ogg", "ui"),
    "ui-confirm": ("sound/machines/terminal_prompt_confirm.ogg", "ui"),
    "alert": (f"{EF}/alert.ogg", "ui"),
    "siren": (f"{EF}/siren.ogg", "ui", 2.5),
    # ARES, the ship's AI, as the announcer
    "ares-online": ("sound/AI/ares_online.ogg", "speech"),
    "ares-code-red": ("sound/AI/code_red_elevated.ogg", "speech"),
    "ares-distress": ("sound/AI/distressbeacon.ogg", "speech"),
    "ares-power-off": ("sound/AI/poweroff.ogg", "speech"),
    # Ambience, played from structures
    "amb-hum": ("sound/ambience/ambienthum.ogg", "amb"),
    "amb-generator": ("sound/machines/generator/generator_mid1.ogg", "amb"),
    "amb-hive": ("sound/ambience/ambicave.ogg", "amb"),
    # Music: TGMC's theme tracks, and the stings played when a game is won or lost
    "theme-hopeful-1": ("sound/theme/neutral_hopeful1.ogg", "music"),
    "theme-hopeful-2": ("sound/theme/neutral_hopeful2.ogg", "music"),
    "theme-melancholy-1": ("sound/theme/neutral_melancholy1.ogg", "music"),
    "theme-melancholy-2": ("sound/theme/neutral_melancholy2.ogg", "music"),
    "sting-win-1": ("sound/theme/winning_triumph1.ogg", "music"),
    "sting-win-2": ("sound/theme/winning_triumph2.ogg", "music"),
    "sting-loss-1": ("sound/theme/sad_loss1.ogg", "music"),
    "sting-loss-2": ("sound/theme/sad_loss2.ogg", "music"),
}

# Marine voices come in a male and a female recording of each clip, under the same clip name in both. A clip name that
# does not exist in both would leave half the marines silent, so only names present in both are listed.
MARINE_CLIPS = {
    "warcry": range(1, 20),      # male has 29, female 19
    "scream": range(1, 6),       # male 7, female 5
    "pain": range(1, 4),         # male 11, female 3
    "gored": range(1, 3),
    "grenadethrow": range(1, 4),
}
for _clip, _numbers in MARINE_CLIPS.items():
    for _n in _numbers:
        for _tag, _dir in (("m", "male"), ("f", "female")):
            SOUNDS[f"marine-{_tag}-{_clip}-{_n}"] = (f"{V}/human/{_dir}/{_clip}_{_n}.ogg", "voice")
for _tag, _dir in (("m", "male"), ("f", "female")):
    SOUNDS[f"marine-{_tag}-medic-1"] = (f"{V}/human/{_dir}/medic.ogg", "voice")


def spec(name):
    """Return (source, kind, max seconds) for a sound, applying the kind's default length."""
    entry = SOUNDS[name]
    source, kind = entry[0], entry[1]
    limit = entry[2] if len(entry) > 2 else KINDS[kind][3]
    return source, kind, limit


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def peak_db(path, seconds):
    """Loudest sample in the first `seconds` of the file, in dB, from ffmpeg's volumedetect."""
    cmd = ["ffmpeg", "-v", "info", "-i", path]
    if seconds:
        cmd += ["-t", str(seconds)]
    cmd += ["-af", "volumedetect", "-f", "null", "-"]
    text = subprocess.run(cmd, capture_output=True, text=True).stderr
    found = re.search(r"max_volume:\s*(-?[\d.]+) dB", text)
    return float(found.group(1)) if found else 0.0


def reencode(src, dst, kind, limit):
    channels, rate, target, _, quality = KINDS[kind]
    length = probe(src)
    if limit:
        length = min(length, limit)
    gain = max(-24.0, min(24.0, target - peak_db(src, limit)))
    filters = [f"volume={gain:.2f}dB"]
    if limit and probe(src) > limit:
        filters.append(f"afade=t=out:st={max(0.0, length - 0.05):.3f}:d=0.05")  # avoid a click where the clip is cut
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", src]
    if limit:
        cmd += ["-t", str(limit)]
    cmd += ["-af", ",".join(filters), "-ac", str(channels), "-ar", str(rate), "-c:a", "libvorbis", "-q:a", str(quality), dst]
    subprocess.run(cmd, check=True)
    return length, gain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tgmc", required=True, help="path to a terragov-marine-corps checkout")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "mod", "tgmc", "audio"))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    report = []
    for name in sorted(SOUNDS):
        source, kind, limit = spec(name)
        src = os.path.join(args.tgmc, source)
        dst = os.path.join(args.out, f"{name}.ogg")
        seconds, gain = reencode(src, dst, kind, limit)
        report.append({"name": name, "source": source, "kind": kind, "seconds": round(seconds, 2),
                       "gain_db": round(gain, 1), "bytes": os.path.getsize(dst)})
    total = sum(r["bytes"] for r in report)
    print(f"{len(report)} sounds, {total // 1024} KiB -> {args.out}")
    with open(os.path.join(args.out, "sounds.json"), "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
