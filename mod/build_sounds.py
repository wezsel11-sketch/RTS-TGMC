"""Copy TGMC .ogg sounds into the OpenRA mod as mono Vorbis .ogg files.

OpenRA's OggLoader plays Vorbis in an .ogg container directly. TGMC files
come in mixed channel counts and rates, so each one is re-encoded to mono,
22050 Hz, and (optionally) trimmed to --max-seconds to keep the mod light.

  SOUNDS maps the sound name used in the rules to a TGMC path under the checkout.

Output (default build/mod/tgmc/audio): <name>.ogg, plus sounds.json listing the sources.

Usage: build_sounds.py --tgmc CHECKOUT [--out DIR] [--max-seconds N]
"""
import argparse
import json
import os
import subprocess

SOUNDS = {
    # Weapons and hits
    "rifle-fire": "sound/weapons/guns/fire/t18.ogg",
    "sentry-fire": "sound/weapons/guns/fire/smartgun1.ogg",
    "claw-hit": "sound/weapons/alien_claw_flesh1.ogg",
    "acid-spit": "sound/voice/alien/spitacid.ogg",
    "heal": "sound/items/hypospray.ogg",
    "repair": "sound/items/welder.ogg",
    # Xeno voices
    "runner-hiss": "sound/voice/alien/hiss1.ogg",
    "xeno-roar-1": "sound/voice/alien/roar1.ogg",
    "xeno-roar-2": "sound/voice/alien/roar2.ogg",
    "xeno-death": "sound/voice/alien/death2.ogg",
    # Marine voices
    "marine-warcry": "sound/voice/human/male/warcry_1.ogg",
    "marine-medic": "sound/voice/human/male/medic.ogg",
    "marine-pain-1": "sound/voice/human/male/pain_1.ogg",
    "marine-pain-2": "sound/voice/human/male/pain_2.ogg",
    "marine-scream-1": "sound/voice/human/male/scream_1.ogg",
    "marine-scream-2": "sound/voice/human/male/scream_2.ogg",
    # Structures and interface
    "resin-build": "sound/effects/alien/resin_build1.ogg",
    "explosion": "sound/effects/explosion/medium1.ogg",
    "turret-death": "sound/effects/alien/turret_death.ogg",
    "ui-click": "sound/effects/menu_click.ogg",
    "ui-deny": "sound/machines/buzz-two.ogg",
    "ui-ping": "sound/machines/ping.ogg",
}


def reencode(src, dst, max_seconds):
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", src, "-t", str(max_seconds),
           "-ac", "1", "-ar", "22050", "-c:a", "libvorbis", "-q:a", "4", dst]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tgmc", required=True, help="path to a terragov-marine-corps checkout")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "mod", "tgmc", "audio"))
    ap.add_argument("--max-seconds", type=float, default=4.0)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    report = []
    for name, rel in sorted(SOUNDS.items()):
        src = os.path.join(args.tgmc, rel)
        dst = os.path.join(args.out, f"{name}.ogg")
        reencode(src, dst, args.max_seconds)
        report.append({"name": name, "source": rel, "bytes": os.path.getsize(dst)})
        print(f"{name}.ogg <- {rel}")
    with open(os.path.join(args.out, "sounds.json"), "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
