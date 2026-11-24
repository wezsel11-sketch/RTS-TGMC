"""Compare the xeno abilities' cooldown and plasma cost in the mod with TGMC's own values.

TGMC: cooldown_duration and ability_cost of each /datum/action/ability/... (inherited from the parent path when a datum does not
set one), and each caste's plasma_max. The mod: Cooldown (ticks, 25 a second) and PlasmaCost of each ActiveAbility; every xeno has
100 plasma there, so costs are compared as a share of the caste's pool. Prints one line per ability in MAP and marks the ones
that are more than twice, or less than half, TGMC's value. Abilities not in MAP are listed at the end.

Usage: audit_abilities.py --tgmc TGMC_CHECKOUT [--rules tgmc/rules]
"""
import argparse
import os
import re
import subprocess

X = "activable/xeno/"
A = "xeno_action/"
# (mod actor, OrderName) -> (TGMC caste folder, datum path under /datum/action/ability/)
MAP = {
    ("runner", "AbilityEvasion"): ("runner", A + "evasion"), ("runner", "AbilityRunnerPounce"): ("runner", X + "pounce/runner"),
    ("hunter", "AbilityHunterPounce"): ("hunter", X + "pounce"), ("hunter", "AbilityHuntersMark"): ("hunter", X + "hunter_mark"),
    ("hunter", "AbilitySilence"): ("hunter", X + "silence"), ("hunter", "AbilityMirage"): ("hunter", A + "mirage"),
    ("sentinel", "AbilityToxicSlash"): ("sentinel", A + "toxic_slash"), ("sentinel", "AbilityDrainSting"): ("sentinel", X + "drain_sting"),
    ("sentinel", "AbilityToxicGrenade"): ("sentinel", X + "toxic_grenade"),
    ("warrior", "AbilityWarriorLunge"): ("warrior", X + "warrior/lunge"), ("warrior", "AbilityFling"): ("warrior", X + "warrior/fling"),
    ("warrior", "AbilityPunch"): ("warrior", X + "warrior/punch"), ("warrior", "AbilityGrappleToss"): ("warrior", X + "warrior/grapple_toss"),
    ("queen", "AbilityCry"): ("queen", X + "screech"), ("queen", "AbilityBulwark"): ("queen", A + "bulwark"),
    ("queen", "AbilityQueenHeal"): ("queen", X + "psychic_cure/queen_give_heal"), ("queen", "AbilityGivePlasma"): ("queen", X + "queen_give_plasma"),
    ("praetorian", "AbilityAcidSpray"): ("praetorian", X + "spray_acid/cone"),
    ("defiler", "AbilityDefile"): ("defiler", X + "defile"), ("defiler", "AbilityEmitGas"): ("defiler", A + "emit_neurogas"),
    ("defiler", "AbilityReagentSlash"): ("defiler", A + "reagent_slash"),
    ("wraith", "AbilityTimestop"): ("wraith", A + "timestop"), ("wraith", "AbilityPortal"): ("wraith", A + "portal"),
    ("wraith", "AbilityRewind"): ("wraith", X + "rewind"),
    ("gorger", "AbilityDrain"): ("gorger", X + "drain"), ("gorger", "AbilityTransfusion"): ("gorger", X + "transfusion"),
    ("gorger", "AbilityCarnage"): ("gorger", X + "carnage"), ("gorger", "AbilityFeast"): ("gorger", X + "feast"),
    ("king", "AbilityNightfall"): ("king", X + "nightfall"), ("king", "AbilityPetrify"): ("king", A + "petrify"),
    ("king", "AbilityOffGuard"): ("king", X + "off_guard"), ("king", "AbilityRoyalRoar"): ("king", X + "shattering_roar"),
    ("dragon", "AbilityBackhand"): ("dragon", X + "backhand"), ("dragon", "AbilityDragonBreath"): ("dragon", X + "backhand/dragon_breath"),
    ("dragon", "AbilityWingGust"): ("dragon", X + "wind_current"), ("dragon", "AbilityGrab"): ("dragon", X + "grab"),
    ("behemoth", "AbilityEarthRiser"): ("behemoth", X + "earth_riser"), ("behemoth", "AbilityLandslide"): ("behemoth", X + "landslide"),
    ("behemoth", "AbilityGeocrush"): ("behemoth", X + "geocrush"),
    ("widow", "AbilityWeb"): ("widow", X + "web_spit"), ("widow", "AbilityLeashBall"): ("widow", X + "leash_ball"),
    ("widow", "AbilitySpiderling"): ("widow", A + "create_spiderling"), ("widow", "AbilityBurrow"): ("widow", A + "burrow"),
    ("shrike", "AbilityFling"): ("shrike", X + "psychic_fling"), ("shrike", "AbilityCure"): ("shrike", X + "psychic_cure"),
    ("shrike", "AbilityUnrelentingForce"): ("shrike", X + "unrelenting_force"),
    ("defender", "AbilityFortify"): ("defender", A + "fortify"), ("defender", "AbilityCrestDefense"): ("defender", A + "toggle_crest_defense"),
    ("defender", "AbilityDefenderCharge"): ("defender", X + "charge/forward_charge"), ("defender", "AbilityTailSweep"): ("defender", A + "tail_sweep"),
    ("defender", "AbilityRegenerateSkin"): ("defender", A + "regenerate_skin"),
    ("puppeteer", "AbilityFlay"): ("puppeteer", X + "flay"), ("puppeteer", "AbilityPincushion"): ("puppeteer", X + "pincushion"),
    ("puppeteer", "AbilityDreadfulPresence"): ("puppeteer", A + "dreadful_presence"), ("puppeteer", "AbilityPuppets"): ("puppeteer", X + "puppet"),
    ("puppeteer", "AbilityOrganicBomb"): ("puppeteer", X + "organic_bomb"),
    ("hivelord", "AbilityHealingInfusion"): ("hivelord", X + "healing_infusion"),
    ("ravager", "AbilityRavagerCharge"): ("ravager", X + "charge"), ("ravager", "AbilityRavage"): ("ravager", X + "ravage"),
    ("ravager", "AbilityRage"): ("ravager", A + "rage"), ("ravager", "AbilityEndure"): ("ravager", A + "endure"),
    ("crusher", "AbilityStomp"): ("crusher", X + "stomp"), ("crusher", "AbilityCrestToss"): ("crusher", X + "cresttoss"),
    ("warlock", "AbilityPsychicShield"): ("warlock", X + "psychic_shield"), ("warlock", "AbilityPsychicCrush"): ("warlock", X + "psy_crush"),
    ("warlock", "AbilityBlast"): ("warlock", X + "psy_blast"),
    ("carrier", "AbilityHugger"): ("carrier", X + "throw_hugger"),
}
ROOT = "/datum/action/ability/"


def git(tgmc, *args):
    return subprocess.run(["git", "-C", tgmc, *args], capture_output=True, text=True, check=False).stdout


def tgmc_values(tgmc):
    """{datum path: {"cost": n, "cd": seconds}} as written, and the #define table for values given by name."""
    defines = {}
    for line in git(tgmc, "grep", "-h", "-E", r"^#define [A-Z_0-9]+ ", "HEAD", "--", "code/__DEFINES").splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3:
            defines[parts[1]] = parts[2].split("//")[0].strip()

    def number(text, seconds):
        text = defines.get(text.strip(), text.strip())
        m = re.match(r"\(?\s*([0-9.]+)\s*(SECONDS|MINUTES)?", text)
        if not m:
            return None
        v = float(m.group(1))
        if seconds:
            v = v * 60 if m.group(2) == "MINUTES" else v if m.group(2) else v / 10   # a bare number is deciseconds
        return v

    out, current = {}, None
    lines = git(tgmc, "grep", "-h", "-E", r"^/datum/action/ability/|^\s+(ability_cost|cooldown_duration) = ", "HEAD", "--", "code")
    for line in lines.splitlines():
        if line.startswith("/"):
            current = line.split("//")[0].strip() if "(" not in line else None
            continue
        if current is None:
            continue
        key, value = line.split("//")[0].split("=", 1)
        v = number(value, "cooldown" in key)
        if v is not None:
            out.setdefault(current[len(ROOT):], {})["cd" if "cooldown" in key else "cost"] = v
    return out


def inherited(values, path, key):
    while path:
        if key in values.get(path, {}):
            return values[path][key]
        path = path.rpartition("/")[0]
    return None


def plasma_max(tgmc, caste):
    text = git(tgmc, "show", f"HEAD:code/modules/mob/living/carbon/xenomorph/castes/{caste}/castedatum_{caste}.dm")
    m = re.search(r"plasma_max = (\d+)", text)
    return int(m.group(1)) if m else None


def mod_abilities(rules):
    """{(actor, OrderName): (cooldown ticks, plasma cost)} from units.yaml and kits.yaml."""
    out = {}
    for name in ("units.yaml", "kits.yaml"):
        actor = block = None
        for line in open(os.path.join(rules, name), encoding="utf-8"):
            if re.match(r"^[\w^-]+:", line):
                actor = line.split(":")[0]
            elif re.match(r"^\t[\w@-]+:", line):
                block = {} if line.startswith("\tActiveAbility") else None
            elif block is not None and line.startswith("\t\t"):
                key, _, value = line.strip().partition(":")
                block[key] = value.strip()
                if key in ("OrderName", "Cooldown", "PlasmaCost", "Toggle") and "OrderName" in block:
                    out[(actor, block["OrderName"])] = (int(block.get("Cooldown", 300)), int(block.get("PlasmaCost", 0)), "Toggle" in block)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tgmc", required=True)
    ap.add_argument("--rules", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tgmc", "rules"))
    args = ap.parse_args()
    values, mod = tgmc_values(args.tgmc), mod_abilities(args.rules)
    assert len(values) > 100, "TGMC's ability datums were not found: is --tgmc a full checkout?"
    flagged = 0
    print(f"{'ability':38} {'cooldown s  mod / TGMC':>24} {'plasma %  mod / TGMC':>22}")
    for (actor, order), (caste, path) in sorted(MAP.items()):
        if (actor, order) not in mod:
            continue
        ticks, cost, toggle = mod[(actor, order)]
        cd, tcost, pool = inherited(values, path, "cd"), inherited(values, path, "cost"), plasma_max(args.tgmc, caste)
        if path not in values and cd is None and tcost is None:
            print(f"{actor + ' ' + order[7:]:38} no TGMC datum {path}")
            continue
        share = None if tcost is None or not pool else tcost * 100 / pool
        marks = []
        if not toggle and cd and not 0.5 <= (ticks / 25) / cd <= 2:
            marks.append("COOLDOWN")
        if share is not None and (share >= 5 or cost >= 5) and not 0.5 <= max(cost, 1) / max(share, 1) <= 2:
            marks.append("COST")
        flagged += bool(marks)
        print(f"{actor + ' ' + order[7:]:38} {'toggle' if toggle else f'{ticks / 25:.0f}':>10} / {'-' if cd is None else f'{cd:.0f}':<11} "
              f"{cost:>8} / {'-' if share is None else f'{share:.0f}':<11} {' '.join(marks)}")
    xenos = {a for a, _ in MAP}
    rest = sorted(f"{a} {o[7:]}" for a, o in mod if a in xenos and (a, o) not in MAP)
    print(f"\n{flagged} flagged. Not compared (no TGMC datum mapped): {', '.join(rest) or 'none'}")


if __name__ == "__main__":
    main()
