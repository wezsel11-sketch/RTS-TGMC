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
  ambient stereo 44100 Hz       -12 dB                   75 s   (TGMC's ambience loops, played as calm music)
  score   stereo 44100 Hz       -9 dB                    whole file  (Kevin MacLeod's full-length songs, CC BY 4.0, downloaded at build time)

A sound is (source path under the TGMC checkout, kind) or (source, kind, max seconds). Each file is scaled so its
loudest sample sits at the kind's peak, which keeps weapons, voices and the interface at sensible levels relative to
one another. The levels are chosen by number, not by ear: nobody has listened to the mix yet.

SOUNDS maps the name used in the rules to its spec. Marine voices exist twice, as marine-m-<clip> and marine-f-<clip>;
the voice sets in tgmc/audio/voices.yaml pick one per marine through Prefixes.

Output (default build/mod/tgmc/audio): <name>.ogg, plus sounds.json listing sources, kinds, lengths and peaks.

Usage: build_sounds.py --tgmc CHECKOUT [--out DIR] [--only PREFIX]
       build_sounds.py --pin-music        (download the open music once and record its hashes in mod/open-music.sha256)
"""
import argparse
import json
import os
import hashlib
import re
import subprocess
import urllib.parse
import urllib.request

KINDS = {
    #          channels, rate,  peak dB, default max seconds, vorbis quality
    "fx": (1, 22050, -3.0, 4.0, 4),
    "voice": (1, 22050, -3.0, 3.0, 4),
    "ui": (1, 22050, -9.0, 2.5, 4),
    "speech": (1, 22050, -6.0, 7.0, 4),
    "amb": (1, 22050, -16.0, 8.0, 4),
    "music": (2, 44100, -6.0, None, 5),
    "ambient": (2, 44100, -12.0, 75.0, 4),
    "score": (2, 44100, -9.0, None, 4),
}

# Kevin MacLeod's music (incompetech.com), Creative Commons: By Attribution 4.0. It is downloaded at build time into build/open-music,
# checked against the hashes pinned in mod/open-music.sha256, and credited in the music titles and the README. Never committed.
OPEN_MUSIC_BASE = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/"
OPEN_PREFIX = "open-music/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "build", "open-music")
HASHES = os.path.join(ROOT, "mod", "open-music.sha256")


def read_hashes(path=HASHES):
    """File name -> sha256, from lines of `<sha256>  <file name>`. A missing file gives {}."""
    if not os.path.isfile(path):
        return {}
    found = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            digest, _, name = line.rstrip("\n").partition("  ")
            if digest and name:
                found[name] = digest
    return found


def _download(filename, base, cache):
    """Download base + filename into the cache as <filename>.part and return that path and its sha256."""
    os.makedirs(cache, exist_ok=True)
    part = os.path.join(cache, filename + ".part")
    digest = hashlib.sha256()
    with urllib.request.urlopen(base + urllib.parse.quote(filename)) as response, open(part, "wb") as out:
        while True:
            chunk = response.read(1 << 16)
            if not chunk:
                break
            digest.update(chunk)
            out.write(chunk)
    return part, digest.hexdigest()


def _file_sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_open(filename, hashes, base=OPEN_MUSIC_BASE, cache=CACHE):
    """The verified local copy of an open-music file, downloading it if the cache has no matching one."""
    want = hashes.get(filename)
    if want is None:
        raise RuntimeError(f"{filename} is not pinned in mod/open-music.sha256; run build_sounds.py --pin-music")
    final = os.path.join(cache, filename)
    if os.path.isfile(final) and _file_sha(final) == want:
        return final
    part, got = _download(filename, base, cache)
    if got != want:
        os.remove(part)
        raise RuntimeError(f"{filename}: sha256 {got} does not match the pinned {want}")
    os.replace(part, final)
    return final

W = "sound/weapons"
G = "sound/weapons/guns/fire"
V = "sound/voice"
A = "sound/voice/alien"
EF = "sound/effects"
M = "sound/weapons/guns/misc"

SOUNDS = {
    # Weapons: rifle (three T-18/M41A shots), sentry, claws, acid
    "rifle-fire-1": (f"{G}/t18.ogg", "fx"),
    "rifle-fire-2": (f"{G}/m41a_1.ogg", "fx"),
    "rifle-fire-3": (f"{G}/m41a_2.ogg", "fx"),
    "sentry-fire": (f"{G}/smartgun1.ogg", "fx"),
    # One firing sound per weapon, from TGMC's own gun sounds
    "rifle-fire-4": (f"{G}/m41a_3.ogg", "fx"),
    "rifle-fire-5": (f"{G}/m41a_4.ogg", "fx"),
    "mg60-fire-1": (f"{G}/tgmc/kinetic/gun_mg60.ogg", "fx"),
    "mg60-fire-2": (f"{G}/tgmc/kinetic/gun_mg60_low.ogg", "fx"),
    "minigun-fire": (f"{G}/minigun.ogg", "fx"),
    "sniper-fire-1": (f"{G}/svd1.ogg", "fx"),
    "sniper-fire-2": (f"{G}/svd2.ogg", "fx"),
    "sniper-fire-3": (f"{G}/svd3.ogg", "fx"),
    "sadar-fire-1": (f"{G}/rpg_1.ogg", "fx"),
    "sadar-fire-2": (f"{G}/rpg_2.ogg", "fx"),
    "sadar-fire-3": (f"{G}/rpg_3.ogg", "fx"),
    "mortar-fire": (f"{G}/mortar_fire.ogg", "fx"),
    "flamer-fire-1": (f"{G}/flamethrower1.ogg", "fx"),
    "flamer-fire-2": (f"{G}/flamethrower2.ogg", "fx"),
    "flamer-fire-3": (f"{G}/flamethrower3.ogg", "fx"),
    "smartgun-fire-1": (f"{G}/smartgun1.ogg", "fx"),
    "smartgun-fire-2": (f"{G}/smartgun2.ogg", "fx"),
    "smartgun-fire-3": (f"{G}/smartgun3.ogg", "fx"),
    "rifle-fire-m412": (f"{G}/M412.ogg", "fx"),
    "shotgun-fire-1": (f"{G}/shotgun.ogg", "fx"),
    "shotgun-fire-2": (f"{G}/shotgun_heavy.ogg", "fx"),
    "smg-fire-1": (f"{G}/mp7.ogg", "fx"),
    "smg-fire-2": (f"{G}/smg_light.ogg", "fx"),
    # Reloads
    "reload-rifle": ("sound/weapons/guns/interact/t18_reload.ogg", "fx"),
    "reload-mg": ("sound/weapons/guns/interact/v41_reload.ogg", "fx"),
    "reload-minigun": ("sound/weapons/guns/interact/minigun_reload.ogg", "fx"),
    "reload-sniper": ("sound/weapons/guns/interact/sniper_reload.ogg", "fx"),
    "reload-launcher": ("sound/weapons/guns/interact/launcher_reload.ogg", "fx"),
    "reload-mortar": ("sound/weapons/guns/interact/mortar_reload.ogg", "fx"),
    "reload-shotgun": ("sound/weapons/guns/interact/shotgun_reload.ogg", "fx"),
    "reload-smg": ("sound/weapons/guns/interact/smg_reload.ogg", "fx"),
    "reload-flamer": ("sound/weapons/guns/interact/flamethrower_reload.ogg", "fx"),
    "claw-swipe-1": (f"{W}/alien_claw_flesh1.ogg", "fx"),
    "claw-swipe-2": (f"{W}/alien_claw_flesh2.ogg", "fx"),
    "claw-swipe-3": (f"{W}/alien_claw_flesh3.ogg", "fx"),
    "slam-1": (f"{EF}/slam1.ogg", "fx"),
    "slam-2": (f"{EF}/slam2.ogg", "fx"),
    "grenade-launch": (f"{G}/grenadelauncher.ogg", "fx", 2.5),
    "spark-1": (f"{EF}/sparks1.ogg", "fx", 1.5),
    "spark-2": (f"{EF}/sparks2.ogg", "fx", 1.5),
    "splat": (f"{EF}/splat.ogg", "fx", 1.5),
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
    # Infestation and evolving
    "chestburst-1": (f"{A}/chestburst.ogg", "fx"),
    "chestburst-2": (f"{A}/chestburst2.ogg", "fx"),
    "preburst-1": ("sound/voice/human/male/preburst1.ogg", "voice"),
    "preburst-2": ("sound/voice/human/male/preburst2.ogg", "voice"),
    "preburst-3": ("sound/voice/human/male/preburst3.ogg", "voice"),
    "egg-burst": (f"{EF}/alien/egg_burst.ogg", "fx"),
    "evolve-ready": (f"{EF}/alien/evolve_ready.ogg", "fx"),
    "new-larva": (f"{EF}/alien/new_larva.ogg", "fx"),
    # The Condor's CAS strike
    "condor-flyby": (f"{EF}/casplane_flyby.ogg", "fx", 2.0),
    "bomb-fall": (f"{EF}/bomb_fall.ogg", "fx"),
    "laser-rifle": ("sound/weapons/guns/fire/Laser Rifle Standard.ogg", "fx", 1.0),
    "door-open": ("sound/machines/airlock.ogg", "fx", 1.5),
    "door-close": ("sound/machines/door_close.ogg", "fx", 1.5),
    "smoke-bomb": (f"{EF}/smoke_bomb.ogg", "fx", 3.0),
    "ob-incoming": (f"{EF}/OB_incoming.ogg", "fx", 4.0),
    # Shells and rockets in flight, and the big guns that fire them
    "mortar-whistle": (f"{M}/mortar_whistle.ogg", "fx", 3.0),
    "mortar-travel": (f"{M}/mortar_travel.ogg", "fx", 3.0),
    "mortar-long-whistle": (f"{M}/mortar_long_whistle.ogg", "fx", 4.0),
    "howitzer-whistle": (f"{M}/howitzer_whistle.ogg", "fx", 4.0),
    "howitzer-fire": (f"{G}/howitzer_fire.ogg", "fx"),
    "rocket-whistle": (f"{M}/rocket_whistle.ogg", "fx", 3.0),
    "rocket-incoming": ("sound/weapons/rocket_incoming.ogg", "fx", 3.0),
    "rocket-arty-fire": (f"{G}/rocket_arty.ogg", "fx"),
    "sonic-boom": (f"{EF}/dropship_sonic_boom.ogg", "fx"),
    # CAS ammo types: the Condor pilot's call-outs, a laser zap, a flare pop and a bigger blast for the heavy bombs
    "cas-voice-missile": (f"{V}/plane_vws/shot_missile.ogg", "fx"),
    "cas-voice-bomb": (f"{V}/plane_vws/shot_bomb.ogg", "fx"),
    "cas-voice-flare": (f"{V}/plane_vws/shot_flare.ogg", "fx"),
    "laser-zap": (f"{EF}/pred_vision.ogg", "fx"),
    "flare-pop": ("sound/items/flare.ogg", "fx"),
    "explosion-huge": (f"{EF}/explosion/large2.ogg", "fx", 1.5),
    "xeno-screech": (f"{EF}/screech.ogg", "fx"),
    # Unit abilities (the command card): cloaks, the mech's boosts and overload, stims, shields, charges and screeches
    "cloak-on": (f"{EF}/pred_cloakon.ogg", "fx"),
    "cloak-off": (f"{EF}/pred_cloakoff.ogg", "fx"),
    "scout-cloak-on": (f"{EF}/cloak_scout_on.ogg", "fx"),
    "scout-cloak-off": (f"{EF}/cloak_scout_off.ogg", "fx"),
    "overboost": ("sound/mecha/overboost_chargeup.ogg", "fx"),
    "overload-start": ("sound/mecha/overload_start.ogg", "fx"),
    "mech-step": ("sound/mecha/mechstep.ogg", "fx", 1.0),
    "hypospray": ("sound/items/hypospray.ogg", "fx"),
    "bang": (f"{EF}/bang.ogg", "fx"),
    "lightning-charge": ("sound/magic/lightning_chargeup.ogg", "fx", 2.0),
    "shield-up": ("sound/items/eshield_recharge.ogg", "fx", 2.0),
    "xeno-charge": (f"{EF}/alien/footstep_charge1.ogg", "fx"),
    "xeno-prepare": (f"{EF}/alien/prepare.ogg", "fx", 2.0),
    "tail-swipe": (f"{EF}/alien/tail_swipe1.ogg", "fx"),
    "xeno-screech-2": (f"{EF}/screech2.ogg", "fx"),
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
    "sting-win-1": ("sound/theme/winning_triumph1.ogg", "music"),
    "sting-win-2": ("sound/theme/winning_triumph2.ogg", "music"),
    "sting-loss-1": ("sound/theme/sad_loss1.ogg", "music"),
    "sting-loss-2": ("sound/theme/sad_loss2.ogg", "music"),
    # The rest of TGMC's music: two tense nuclear-alarm themes, a zombie-loss theme, the elevator track and the lobby theme
}

# TGMC's ambience loops, played as a calm backdrop in the playlist. Name -> source file under sound/ambience.
AMBIENT = {
    **{f"ambient-station-{n}": f"ambigen{n}.ogg" for n in range(1, 15)},
    **{f"ambient-chapel-{n}": f"ambicha{n}.ogg" for n in range(1, 5)},
    **{f"ambient-signal-{n}": f"ambisin{n}.ogg" for n in range(1, 5)},
    "ambient-moon-1": "ambimo1.ogg",
    "ambient-moon-2": "ambimo2.ogg",
    "ambient-tech-1": "ambitech.ogg",
    "ambient-tech-2": "ambitech2.ogg",
    "ambient-space": "ambispace.ogg",
    "ambient-lava-1": "ambilava1.ogg",
    "ambient-lava-2": "ambilava2.ogg",
    "ambient-lava-3": "ambilava3.ogg",
    "ambient-mine": "ambimine.ogg",
    "ambient-malf": "ambimalf.ogg",
    "ambient-atmos-1": "ambiatmos.ogg",
    "ambient-atmos-2": "ambiatmos2.ogg",
    "ambient-atmos-3": "ambiatm1.ogg",
    "ambient-cave": "ambicave2.ogg",
    "ambient-ship": "shipambience.ogg",
    "ambient-jungle": "jungle_amb1.ogg",
    "ambient-wind": "windambient.ogg",
}
for _name, _file in AMBIENT.items():
    SOUNDS[_name] = (f"sound/ambience/{_file}", "ambient")

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


OPEN_MUSIC = {
    "score-intrepid": "Intrepid",
    "score-rynos-theme": "Rynos Theme",
    "score-decisions": "Decisions",
    "score-prelude-and-action": "Prelude and Action",
    "score-ossuary-resolve": "Ossuary 7 - Resolve",
    "score-heart-of-nowhere": "Heart of Nowhere",
    "score-dark-times": "Dark Times",
    "score-unseen-horrors": "Unseen Horrors",
    "score-anguish": "Anguish",
    "score-the-descent": "The Descent",
    "score-deep-haze": "Deep Haze",
    "score-ether-vox": "Ether Vox",
    "score-frozen-star": "Frozen Star",
    "score-crypto": "Crypto",
    "score-aggressor": "Aggressor",
    "score-faceoff": "Faceoff",
    "score-dangerous": "Dangerous",
    "score-failing-defense": "Failing Defense",
    "score-space-fighter-loop": "Space Fighter Loop",
    "score-volatile-reaction": "Volatile Reaction",
    "score-hot-pursuit": "Hot Pursuit",
    "score-killing-time": "Killing Time",
    "score-hitman": "Hitman",
}
for _key, _title in OPEN_MUSIC.items():
    SOUNDS[_key] = (f"{OPEN_PREFIX}{_title}.mp3", "score")


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
    # -vn: a music file can carry a video stream (score-frozen-star did), which would make an Ogg Theora file the game cannot play.
    cmd += ["-vn", "-af", ",".join(filters), "-ac", str(channels), "-ar", str(rate), "-c:a", "libvorbis", "-q:a", str(quality), dst]
    subprocess.run(cmd, check=True)
    return length, gain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tgmc", help="path to a terragov-marine-corps checkout (not needed for the open music alone)")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "mod", "tgmc", "audio"))
    ap.add_argument("--only", default="", help="build only the sounds whose name starts with this")
    ap.add_argument("--pin-music", action="store_true", help="download the open music once and write mod/open-music.sha256")
    args = ap.parse_args()

    if args.pin_music:
        pinned = {}
        for title in sorted(OPEN_MUSIC.values()):
            filename = title + ".mp3"
            part, digest = _download(filename, OPEN_MUSIC_BASE, CACHE)
            os.replace(part, os.path.join(CACHE, filename))
            pinned[filename] = digest
            print(f"pinned {filename}")
        with open(HASHES, "w", encoding="utf-8", newline="\n") as f:
            for filename in sorted(pinned):
                f.write(f"{pinned[filename]}  {filename}\n")
        print(f"pinned {len(pinned)} tracks")
        return

    names = [n for n in sorted(SOUNDS) if n.startswith(args.only)]
    if not args.tgmc and any(not SOUNDS[n][0].startswith(OPEN_PREFIX) for n in names):
        ap.error("--tgmc is required unless only the open music is built (--only score-)")
    hashes = read_hashes()
    os.makedirs(args.out, exist_ok=True)
    report = []
    for name in names:
        source, kind, limit = spec(name)
        if source.startswith(OPEN_PREFIX):
            src = fetch_open(source[len(OPEN_PREFIX):], hashes)
        else:
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
