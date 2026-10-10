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
    "rifle-fire": "sound/weapons/guns/fire/autorifle-1.ogg",
    "runner-hiss": "sound/voice/alien/hiss1.ogg",
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
