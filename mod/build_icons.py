"""Cut the command card's ability icons out of TGMC's action and item sheets.

Each ability (an ActiveAbility in tgmc/rules) shows the icon named by its Icon field, or by its OrderName when it has none. ICONS maps
that name to a TGMC sheet and state; the first frame, facing south, is used. Abilities without an entry keep their text label.

Outputs in --out:
  ability-icons.png    every icon, 32x32, packed in rows of COLS (padded to a power-of-two height)
  ability-icons.yaml   the OpenRA chrome collection "ability-icons", one region per icon

Usage: build_icons.py --tgmc TGMC_CHECKOUT --out MOD_DIR
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageOps, PngImagePlugin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tgmc_dmi  # noqa: E402

SIZE = 32
COLS = 16

XA = "icons/Xeno/actions"
ACT = "icons/mob/actions.dmi"
MECH = "icons/mob/actions/actions_mecha.dmi"
ART = "icons/obj/items/ammo/artillery.dmi"
ROCKET = "icons/obj/items/ammo/rocket.dmi"
NADE = "icons/obj/items/grenade.dmi"

ICONS = {
    # Marine leaders and infantry
    "AbilityOrderMove": (ACT, "rally"),
    "AbilityOrderHold": (ACT, "defend"),
    "AbilityOrderFocus": (ACT, "attack"),
    "AbilityMark": (ACT, "signal_transmit"),
    "AbilitySmokeCloak": (NADE, "grenade_cloak"),
    "AbilityMirage": (f"{XA}/hunter.dmi", "mirror_image"),
    "AbilityFrag": (NADE, "grenade"),
    "AbilityGrenadeFrag": (NADE, "grenade"),
    "AbilityGrenadeIncendiary": (NADE, "grenade_fire"),
    "AbilityGrenadeSmoke": (NADE, "grenade_smoke"),
    "AbilityStim": (ACT, "stim_menu"),
    "AbilityBuildCade": (ACT, "build_designator"),
    "AbilityRepairBurst": (MECH, "repair"),
    "AbilityAimedShot": (ACT, "sniper_zoom"),
    "AbilityOverdrive": (ACT, "fmode_burst_auto"),
    "AbilityDeploy": (ACT, "aim_mode"),
    "AbilityFireWall": (NADE, "grenade_fire"),
    "AbilityLunge": (ACT, "sword_lunge"),
    "AbilitySprint": (ACT, "retreat"),
    "AbilityPlantCharge": (NADE, "grenade_hefa"),
    "AbilityDetonate": (NADE, "grenade_ex_active"),
    "AbilityScoutCloak": (NADE, "grenade_cloak_som"),
    # Shells (mortar; the howitzer's own pictures by its Icon field) and rockets
    "AbilityShellHE": (ART, "mortar_he"),
    "AbilityShellIncendiary": (ART, "mortar_inc"),
    "AbilityShellSmoke": (ART, "mortar_smk"),
    "AbilityShellPlasma": (ART, "howitzer_plasmaloss"),
    "AbilityShellWP": (ART, "howitzer_wp"),
    "AbilityFlare": (ART, "mortar_flr"),
    "HowitzerHE": (ART, "howitzer"),
    "HowitzerIncendiary": (ART, "howitzer_incend"),
    "HowitzerPlasma": (ART, "howitzer_plasmaloss"),
    "AbilityRocketHEAT": (ROCKET, "rocket_he"),
    "AbilityRocketAP": (ROCKET, "rocket_ap"),
    "AbilityRocketWP": (ROCKET, "rocket_wp"),
    "AbilityRocketSmoke": (ROCKET, "shell_smoke"),
    "SomThermobaric": (ROCKET, "rpg_thermobaric"),
    "SomRadiation": (ROCKET, "rpg_rad"),
    # The mech's modules
    "AbilityOverboost": (MECH, "overboost_on"),
    "AbilityAssaultArmor": (MECH, "assaultarmor"),
    "AbilityMechCloak": (MECH, "cloak_on"),
    "AbilityPulseArmor": (MECH, "pulsearmor"),
    "AbilityLegOverload": (MECH, "mech_overload_on"),
    "AbilityMechSmoke": (MECH, "mech_smoke"),
    "AbilityBarrage": (ROCKET, "quad_rocket"),
    # Xenos
    "AbilityEvasion": (f"{XA}/runner.dmi", "evasion_on"),
    "AbilityRunnerPounce": (f"{XA}/runner.dmi", "pounce"),
    "AbilityHunterPounce": (f"{XA}/runner.dmi", "pounce"),
    "AbilityLeap": (f"{XA}/runner.dmi", "pounce_savage_on"),
    "AbilityAcidMissile": (f"{XA}/boiler.dmi", "corrosive_glob"),
    "AbilityStealth": (f"{XA}/hunter.dmi", "hunter_invisibility"),
    "AbilityHuntersMark": (f"{XA}/hunter.dmi", "hunter_mark"),
    "AbilitySilence": (f"{XA}/hunter.dmi", "silence"),
    "AbilitySalve": (f"{XA}/drone.dmi", "heal_xeno"),
    "AbilityEnhance": (f"{XA}/drone.dmi", "enhancement"),
    "AbilityBombardAcid": (f"{XA}/boiler.dmi", "bombard"),
    "AbilityBombardNeuro": (f"{XA}/boiler.dmi", "neurotoxin_glob"),
    "AbilityGlobAcid": (f"{XA}/boiler.dmi", "corrosive_glob"),
    "AbilityGlobNeuro": (f"{XA}/boiler.dmi", "neurotoxin_glob"),
    "AbilityAcidShroud": (f"{XA}/boiler.dmi", "acid_shroud"),
    "AbilityAcidSpray": (f"{XA}/boiler.dmi", "spray_acid"),
    "AbilityPlowCharge": (f"{XA}/bull.dmi", "bull_charge"),
    "AbilityHeadbuttCharge": (f"{XA}/bull.dmi", "bull_headbutt"),
    "AbilityGoreCharge": (f"{XA}/bull.dmi", "bull_gore"),
    "AbilityNeurotoxin": (f"{XA}/sentinel.dmi", "neuro_sting"),
    "AbilityToxicGrenade": (f"{XA}/sentinel.dmi", "gas mine"),
    "AbilityPunch": (f"{XA}/warrior.dmi", "punch"),
    "AbilityWarriorLunge": (f"{XA}/warrior.dmi", "lunge"),
    "AbilityAgility": (f"{XA}/warrior.dmi", "agility_on"),
    "AbilityFling": (f"{XA}/shrike.dmi", "fling"),
    "AbilityAcidBurst": (f"{XA}/spitter.dmi", "scatter_spit"),
    "AbilityAcidGrenade": (f"{XA}/spitter.dmi", "glob_grenade"),
    "AbilityAcidMine": (f"{XA}/spitter.dmi", "acid_mine"),
    "AbilityCry": (f"{XA}/queen.dmi", "screech"),
    "AbilityHealScreech": (f"{XA}/queen.dmi", "heal_screech"),
    "AbilityFrenzyScreech": (f"{XA}/queen.dmi", "frenzy_screech"),
    "AbilityGivePlasma": (f"{XA}/queen.dmi", "queen_give_plasma"),
    "AbilityQueenHeal": (f"{XA}/drone.dmi", "heal_xeno"),
    "AbilityEgg": (f"{XA}/carrier.dmi", "call_younger"),
    "AbilityHugger": (f"{XA}/carrier.dmi", "throw_hugger"),
    "AbilityDodge": (f"{XA}/praetorian.dmi", "dodge"),
    "AbilityStomp": (f"{XA}/crusher.dmi", "stomp"),
    "AbilityRage": (f"{XA}/ravager.dmi", "rage"),
    "AbilityEndure": (f"{XA}/ravager.dmi", "ignore_pain"),
    "AbilityEmitGas": (f"{XA}/defiler.dmi", "emit_neurogas"),
    "AbilityBlast": (f"{XA}/warlock.dmi", "psy_blast"),
    "AbilityCure": (f"{XA}/shrike.dmi", "psychic_whisper"),
    "AbilityWeb": (f"{XA}/widow.dmi", "web_spit"),
    "AbilityTimestop": (f"{XA}/wraith.dmi", "time_stop"),
    "AbilityPortal": (f"{XA}/wraith.dmi", "portal"),
    "AbilityCentrifugalForce": (f"{XA}/defender.dmi", "centrifugal_force"),
    "AbilityFlurry": (f"{XA}/warrior.dmi", "flurry"),
    "AbilityPrimalWrath": (f"{XA}/behemoth.dmi", "primal_wrath"),
    "AbilityZeroFormBeam": (f"{XA}/king.dmi", "zero_form_beam"),
    "AbilityPsychicVortex": (f"{XA}/shrike.dmi", "vortex"),
    "AbilityRecall": (f"{XA}/wraith.dmi", "Recall"),
    "AbilityBurrow": (f"{XA}/widow.dmi", "burrow"),
    "AbilityReagentSlash": (f"{XA}/defiler.dmi", "reagent_slash"),
    "AbilityGrab": (f"{XA}/dragon.dmi", "grab"),
    "AbilityOrganicBomb": (f"{XA}/puppeteer.dmi", "organic_bomb"),
    "AbilityRewind": (f"{XA}/wraith.dmi", "rewind"),
    "AbilityDrain": (f"{XA}/gorger.dmi", "drain"),
    "AbilityTransfusion": (f"{XA}/gorger.dmi", "transfusion"),
    "AbilityCarnage": (f"{XA}/gorger.dmi", "carnage"),
    "AbilityToxicSlash": (f"{XA}/sentinel.dmi", "neuroclaws_on"),
    "AbilityDrainSting": (f"{XA}/shrike.dmi", "drone_sting"),
    "AbilityDefile": (f"{XA}/defiler.dmi", "defiler_sting"),
    "AbilityNightfall": (f"{XA}/king.dmi", "nightfall"),
    "AbilityOffGuard": (f"{XA}/king.dmi", "off_guard"),
    "AbilityBackhand": (f"{XA}/dragon.dmi", "backhand"),
    "AbilityEarthRiser": (f"{XA}/behemoth.dmi", "earth_riser"),
    "AbilityLeashBall": (f"{XA}/widow.dmi", "leash_ball"),
    "AbilityUnrelentingForce": (f"{XA}/shrike.dmi", "vortex"),
    "AbilityCrestDefense": (f"{XA}/defender.dmi", "crest_defense"),
    "AbilityRegenerateSkin": (f"{XA}/defender.dmi", "regenerate_skin"),
    "AbilityGrappleToss": (f"{XA}/warrior.dmi", "grapple_toss"),
    "AbilityBulwark": (f"{XA}/queen.dmi", "bulwark"),
    "AbilityDreadfulPresence": (f"{XA}/puppeteer.dmi", "dreadful_presence"),
    "AbilityResinWalker": (f"{XA}/hivelord.dmi", "toggle_speed"),
    "AbilityBlink": (f"{XA}/wraith.dmi", "blink"),
    "AbilityPlantWeeds": (f"{XA}/general.dmi", "xenohide"),
}


SHIP = "icons/obj/structures/prop/mainship.dmi"
SHIP64 = "icons/obj/structures/prop/mainship_64.dmi"

# Support power icons: TGMC's own sprite of the munition (the crate or rocket a pilot loads, the warhead the orbital
# cannon fires) with a short name under it. One sheet a family, frames in this order (tgmc/sequences/misc.yaml).
POWER_ICONS = {
    "cas-icon.png": [
        (SHIP64, "keeper", "BOMBS"), (SHIP, "30mm_crate", "30MM"), (SHIP, "minirocket", "MINI"), (SHIP, "minirocket_ilm", "FLARE"),
        (SHIP64, "single", "AGM"), (SHIP, "laser_battery", "LASER"), (SHIP64, "napalm", "NAPALM"), (SHIP64, "fatty", "FATTY"),
        (SHIP64, "monarch", "MOAB"),
    ],
    "orbital-icon.png": [
        (SHIP, "ob_warhead_1", "HE"), (SHIP, "ob_warhead_2", "FIRE"), (SHIP, "ob_warhead_3", "CLUSTER"),
        (SHIP, "ob_warhead_4", "PLASMA"), (SHIP, "30mm_crate_hv", "RAIL"),
    ],
}
POWER_SIZE = (46, 34)


def write_power_icons(tgmc, out):
    """One 46x34 frame a power: the sprite's drawn part scaled to fit above the name. No card: the HUD tile is the card."""
    w, h = POWER_SIZE
    for sheet, frames in POWER_ICONS.items():
        img = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for i, (dmi, state, label) in enumerate(frames):
            art = tgmc_dmi.Dmi(os.path.join(tgmc, dmi)).frames(state)[0][0].convert("RGBA")
            art = art.crop(art.getbbox())
            scale = min((w - 4) / art.width, (h - 12) / art.height)
            size = (max(1, round(art.width * scale)), max(1, round(art.height * scale)))
            art = art.resize(size, Image.BOX) if scale < 1 else tgmc_dmi.nearest(art, size)
            img.alpha_composite(art, (i * w + (w - size[0]) // 2, (h - 12 - size[1]) // 2))
            d.text((i * w + (w - d.textlength(label)) // 2, h - 12), label, fill=(240, 240, 230, 255))
        meta = PngImagePlugin.PngInfo()
        meta.add_text("FrameSize", f"{w},{h}")
        meta.add_text("FrameAmount", str(len(frames)))
        img.save(os.path.join(out, sheet), pnginfo=meta)


def paths():
    """The TGMC files this script reads, for the sparse checkout (tgmc_paths.py)."""
    return sorted({sheet for sheet, _ in ICONS.values()} | {SHIP, SHIP64})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tgmc", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    sheets = {}
    icons = []
    missing = []
    for name, (sheet, state) in ICONS.items():
        if sheet not in sheets:
            path = os.path.join(args.tgmc, sheet)
            sheets[sheet] = tgmc_dmi.Dmi(path) if os.path.exists(path) else None
        dmi = sheets[sheet]
        if dmi is None or not dmi.has_state(state):
            missing.append(f"{name} ({sheet} {state})")
            continue
        icon = dmi.frames(state)[0][0].convert("RGBA")
        if icon.size != (SIZE, SIZE):
            icon = tgmc_dmi.nearest(icon, (SIZE, SIZE))
        icons.append((name, icon))

    # A greyed, darker copy the card shows while the ability cannot be used (cooldown, no plasma, silenced).
    for name, icon in list(icons):
        grey = ImageOps.grayscale(icon).point(lambda v: v * 45 // 100).convert("RGBA")
        grey.putalpha(icon.getchannel("A"))
        icons.append((f"{name}-off", grey))

    # OpenRA sheets must be a power of two on each side.
    rows = (len(icons) + COLS - 1) // COLS
    height = 1
    while height < max(1, rows) * SIZE:
        height *= 2
    atlas = Image.new("RGBA", (COLS * SIZE, height), (0, 0, 0, 0))
    lines = ["# Generated by mod/build_icons.py from TGMC art. Do not edit.", "ability-icons:", "\tImage: ability-icons.png", "\tRegions:"]
    for i, (name, icon) in enumerate(icons):
        x, y = (i % COLS) * SIZE, (i // COLS) * SIZE
        atlas.paste(icon, (x, y))
        lines.append(f"\t\t{name}: {x}, {y}, {SIZE}, {SIZE}")

    atlas.save(os.path.join(args.out, "ability-icons.png"))
    with open(os.path.join(args.out, "ability-icons.yaml"), "w") as f:
        f.write("\n".join(lines) + "\n")

    write_power_icons(args.tgmc, args.out)
    for m in missing:
        print(f"build_icons: no icon for {m}")
    print(f"build_icons: {len(icons) // 2} icons")


if __name__ == "__main__":
    main()
