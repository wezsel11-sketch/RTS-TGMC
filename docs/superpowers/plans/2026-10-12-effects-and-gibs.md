# Effects and Gibs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Marines and the mod's xenos die visibly (a fade, or a gib when an explosion kills them), and the claw and slam attacks get TGMC hit effects.

**Architecture:** OpenRA's `WithDeathAnimation` picks a sequence by the killing warhead's damage type. Explosion warheads carry `DamageTypes: ExplosionDeath`; every unit maps that type to `die-gib`, which is a gib animation from TGMC art, or an alias of `die` for the heavy castes that do not gib. A kill with no damage type falls back to `die`. `build_sprites.py` gains a `fade` layer option and a per-unit `cell` size so the 32px marine sheets can hold TGMC's 64px gib frames. `lint_static.py` gains a check that no kill can end with no animation.

**Tech Stack:** OpenRA (pinned in `mod/setup.sh`), YAML rules, Python 3 with Pillow, Lua scenarios.

**Spec:** `docs/superpowers/specs/2026-10-12-effects-and-gibs-design.md`

## Global Constraints

- TGMC art only. No frame is drawn by hand. A fade is derived from a TGMC frame.
- Nothing TGMC-derived is committed. Built output stays under `build/`.
- Gib rule: a kill by an `ExplosionDeath` warhead gibs Runner, Hunter, Sentinel, Drone and every marine role. Warrior and Queen do not gib (TGMC: bomb armour of about 95% or more). A kill by anything else plays `die`.
- Deaths use the TGMC gib sprites: `icons/mob/human_gib.dmi` state `default` (14 frames, 64x64); `gibbed-a-runner` (10, 64x64) in `runner.dmi`; `Hunter Gibbed` (14, 48x48) in `hunter.dmi`; `gibbed-a-small` (10, 48x48) in `sentinel.dmi` and `drone.dmi`.
- Claw effects: states `claw` and `claw2` (4 frames, 32x32) in `icons/effects/effects.dmi`. Slam: `throw_impact_s` (7 frames, 96x96) in `icons/effects/96x96.dmi`.
- Scenario and lint commands run as in the README. `python3` is `py -3` on this Windows machine. The OpenRA scenarios need Linux (WSL Ubuntu is installed here).
- Commits end with the `Co-Authored-By` trailer from the session's attribution rule.

## Spec deviations (decided while planning)

- **No persistent remains.** An OpenRA death animation ends with its sequence, so a gib leaves no corpse decal. TGMC's `*-corpse` states are not used. Persistent remains would need a spawned actor and is a separate task.
- **No gib particles.** TGMC's particle holder has no OpenRA equivalent. The gib animation frames already show the burst.
- **"Devastating" has no levels in this mod.** Any kill by an `ExplosionDeath` warhead gibs. Only the grenade carries the tag today.

## Review Focus

1. A warhead with a `DamageTypes` value that a unit's `DeathTypes` does not list makes that unit die with no animation at all (OpenRA returns early). Pinned by Task 2's test.
2. Warrior and Queen killed by an explosion must play plain `die`, not nothing. Pinned by Task 3 (alias) and Task 6 (killed with `ExplosionDeath`).
3. A marine killed by a bullet, claw, acid or slam fades and never gibs. Pinned by Task 4's test that only `TGMCGrenade` sets `DamageTypes`.
4. Padding a 32px marine sheet to 64px must not move the sprite. Pinned by Task 1's centring test.
5. A missing death sequence only throws at render time, so a scenario can print PASS and still crash. Pinned by Task 6's exception check.

---

### Task 1: Sprite builder: `fade` option and per-unit `cell`

**Files:**
- Modify: `mod/build_sprites.py` (module docstring option list, `render_sequences`, `build_unit`, new helpers)
- Create: `mod/test_effects.py`

**Interfaces:**
- Produces: `fade_frames(img: Image.Image, count: int) -> list[Image.Image]`, `pad_to(img: Image.Image, size: tuple[int, int]) -> Image.Image`, layer option `"fade": N` (read from the first layer of a sequence), unit key `UNITS[name]["cell"] = (w, h)`, and `render_sequences(tgmc, sequences, cell=None)`.

- [ ] **Step 1: Write the failing tests in `mod/test_effects.py`**

A plain script: each `test_*` function is called from `__main__`, and any failure raises. It imports `build_sprites` and `lint_static` from the `mod` folder, as `lint_static.py` does. Tests, using synthetic Pillow images:
  - `test_fade_frames_alpha`: a 4x4 `(255, 0, 0, 200)` image with `count=4` gives 4 frames whose alpha at `(0, 0)` is `[200, 150, 100, 50]`.
  - `test_pad_to_centres`: a 32x32 opaque red image padded to `(64, 64)` has alpha 255 at `(16, 16)` and `(47, 47)`, and alpha 0 at `(15, 15)` and `(48, 48)`.
  - `test_pad_to_rejects_larger`: `pad_to` of a 32x32 image to `(16, 16)` raises `SystemExit`.

- [ ] **Step 2: Run to verify it fails**

Run: `py -3 -I mod/test_effects.py`
Expected: FAIL with `AttributeError: module 'build_sprites' has no attribute 'fade_frames'`

- [ ] **Step 3: Implement `fade_frames` and `pad_to` in `mod/build_sprites.py`**

Frame `i` of `fade_frames` has its alpha multiplied by `(count - i) / count` (rounded), so the first frame is untouched. `pad_to` pastes the image, unscaled, in the middle of a transparent cell of `size` and raises `SystemExit` naming the sizes if the image is bigger.

- [ ] **Step 4: Run to verify the tests pass**

Run: `py -3 -I mod/test_effects.py`
Expected: PASS (prints one line per test, exit code 0)

- [ ] **Step 5: Wire the options into the builder**

In `render_sequences`, after `sides = composite(layers)`: if the first layer's options contain `"fade"`, replace each side's frames with `fade_frames(frames[0], opts["fade"])`. Add a `cell=None` parameter; when given, pad every frame of every sequence to `cell` with `pad_to` and compare the sequence's size against `cell` instead of the first sequence's size. `build_unit` passes `spec.get("cell")` for the main sheet. Add `fade` and `cell` to the module docstring.
Verify: `py -3 -I mod/build_sprites.py --tgmc $TGMC --out <scratch dir> --units rifleman` still prints `rifleman: ... cells of 32x32px` (no `cell` set yet, so nothing changes).

- [ ] **Step 6: Commit**

```bash
git add mod/build_sprites.py mod/test_effects.py
git commit -m "Add a fade layer option and a per-unit cell size to the sprite builder"
```

### Task 2: Lint: no kill ends without a death animation

**Files:**
- Modify: `mod/lint_static.py` (new function, call it from `main`)
- Modify: `mod/test_effects.py`
- Modify: `mod/build_mod.sh` (run `test_effects.py` after the lint)

**Interfaces:**
- Produces: `check_death_types(rules: str, weapons: str, seqs: dict[str, set[str]]) -> list[str]`. `rules` is all rule files joined; the result is a list of error strings, empty when clean.
- Behaviour: for every concrete actor in `seqs` that inherits (through any chain of `Inherits:` lines) a `WithDeathAnimation` block with `DeathTypes`, each `Type: -suffix` entry needs the sequence `die` + suffix in `seqs[actor]`. Every value in a `DamageTypes:` line of `weapons` must be a key of every such `DeathTypes` block.

- [ ] **Step 1: Add the failing tests to `mod/test_effects.py`**

  - `test_death_types_clean`: a `^Xeno` template with `DeathTypes` entry `ExplosionDeath: -gib`, a `runner` that inherits it, `seqs = {"runner": {"die", "die-gib"}}`, and a weapon with `DamageTypes: ExplosionDeath` gives `[]`.
  - `test_death_types_missing_sequence`: the same with `seqs = {"runner": {"die"}}` gives exactly one error that contains `runner` and `die-gib`.
  - `test_death_types_unlisted_damage_type`: a weapon with `DamageTypes: FireDeath` gives exactly one error that contains `FireDeath`.
  Rules text uses tab indentation like the real files.

- [ ] **Step 2: Run to verify it fails**

Run: `py -3 -I mod/test_effects.py`
Expected: FAIL with `AttributeError: module 'lint_static' has no attribute 'check_death_types'`

- [ ] **Step 3: Implement `check_death_types` and call it from `main`**

Resolve inheritance textually: collect each top-level block's `Inherits:` names, then walk up. Append its errors to `main`'s list, passing `all_rules`, `rules["weapons.yaml"]` and `seqs`. Then add `"$PY" -I "$HERE/test_effects.py"` after the lint line in `mod/build_mod.sh`.

- [ ] **Step 4: Run to verify**

Run: `py -3 -I mod/test_effects.py && py -3 -I mod/lint_static.py`
Expected: tests PASS; `lint_static: 0 error(s)` (no unit has `DeathTypes` yet, so the check has nothing to flag)

- [ ] **Step 5: Commit**

```bash
git add mod/lint_static.py mod/test_effects.py mod/build_mod.sh
git commit -m "Lint death types: every kill needs a death animation"
```

### Task 3: Xeno gibs

**Files:**
- Modify: `mod/build_sprites.py` (`UNITS` for runner, hunter, sentinel, drone, warrior, queen; constants)
- Modify: `tgmc/rules/units.yaml` (`^Xeno`)

**Interfaces:**
- Consumes: Task 2's lint.
- Produces: sequence `die-gib` on every xeno unit; `^Xeno` maps `ExplosionDeath` to `-gib`.

- [ ] **Step 1: Make the lint fail first**

In `tgmc/rules/units.yaml`, extend `^Xeno`'s `WithDeathAnimation` with `DeathTypes:` and the entry `ExplosionDeath: -gib` (two tabs, then three).
Run: `py -3 -I mod/lint_static.py`
Expected: errors that `runner`, `hunter`, `sentinel`, `drone`, `warrior` and `queen` have no sequence `die-gib`.

- [ ] **Step 2: Add the sequences in `UNITS`**

`die-gib` entries: `runner` gets `[(RUNNER, "gibbed-a-runner", None, {"tick": 70})]`; `hunter` gets `[(HUNTER, "Hunter Gibbed", None, {"tick": 70})]`; `sentinel` and `drone` get `[(SENTINEL, "gibbed-a-small", None, {"tick": 70})]` and `[(DRONE, "gibbed-a-small", None, {"tick": 70})]`; `warrior` and `queen` get the string `"die"` (an alias, so they die plainly).
Run: `py -3 -I mod/lint_static.py`
Expected: `lint_static: 0 error(s)`

- [ ] **Step 3: Build and check the sheets**

Run: `py -3 -I mod/build_sprites.py --tgmc $TGMC --out <scratch dir> --units runner hunter sentinel drone warrior queen`
Expected: no `SystemExit` (the gib frames match each sheet's cell size). Open `sequences/runner.yaml` in the scratch dir: `die-gib` has `Length: 10`, and for hunter `Length: 14`. View `sprites/hunter.png` once to confirm the gib frames are not blank.

- [ ] **Step 4: Commit**

```bash
git add mod/build_sprites.py tgmc/rules/units.yaml
git commit -m "Give the xenos TGMC gib animations; Warrior and Queen die plainly"
```

### Task 4: Marine death and gibs; the grenade carries the explosion tag

**Files:**
- Modify: `mod/build_sprites.py` (new constant `HUMAN_GIB`, new `marine_die` helper, `UNITS` for the five marine roles with `"cell": (64, 64)`)
- Modify: `tgmc/rules/units.yaml` (`^Infantry`)
- Modify: `tgmc/rules/weapons.yaml` (`TGMCGrenade` damage warhead)
- Modify: `mod/test_effects.py`

**Interfaces:**
- Consumes: Task 1 (`fade`, `cell`), Task 2 (lint), Task 3.
- Produces: `marine_die(uniform: str, weapon: tuple) -> list` (the same layers as `marine`, each with option `{"side": "S"}` and the first also `"fade": 6, "tick": 70`); sequences `die` and `die-gib` on rifleman, medic, engineer, smartgunner and grenadier.

- [ ] **Step 1: Write the failing test in `mod/test_effects.py`**

`test_only_grenade_tags_explosions`: read `tgmc/rules/weapons.yaml`; the set of weapons whose text has `DamageTypes:` is exactly `{"TGMCGrenade"}`.

- [ ] **Step 2: Run to verify it fails**

Run: `py -3 -I mod/test_effects.py`
Expected: FAIL (the set is empty)

- [ ] **Step 3: Tag the grenade and add the marine rules**

`TGMCGrenade`'s `Warhead@1Dam` gets `DamageTypes: ExplosionDeath`. `^Infantry` gets `WithDeathAnimation` with `DeathSequence: die`, `FallbackSequence: die`, and `DeathTypes` mapping `ExplosionDeath` to `-gib`. Run `py -3 -I mod/test_effects.py`; it passes. Run `py -3 -I mod/lint_static.py`; it reports the five marine roles missing `die` and `die-gib`.

- [ ] **Step 4: Add the marine sequences**

`HUMAN_GIB = "icons/mob/human_gib.dmi"`. Each of the five roles gets `"die": marine_die(<its uniform>, <its weapon>)` and `"die-gib": [(HUMAN_GIB, "default", None, {"tick": 70})]`, and `"cell": (64, 64)` beside `"sequences"`. Add `HUMAN_GIB` to nothing else: `tgmc_paths.py` reads it from `UNITS`.
Run: `py -3 -I mod/lint_static.py` then `py -3 -I mod/build_sprites.py --tgmc $TGMC --out <scratch dir> --units rifleman medic engineer smartgunner grenadier`
Expected: `0 error(s)`; each sheet is built at `64x64px` cells. View `sprites/rifleman.png` once: the `stand` cells look the same as before, only on a larger transparent cell, and the `die` cells fade out.

- [ ] **Step 5: Commit**

```bash
git add mod/build_sprites.py tgmc/rules/units.yaml tgmc/rules/weapons.yaml mod/test_effects.py
git commit -m "Marines fade on death and are gibbed by explosions"
```

### Task 5: Claw and slam hit effects

**Files:**
- Modify: `mod/build_sprites.py` (`fx-impact` gets `claw` and `claw2`; new image `fx-slam-big`)
- Modify: `tgmc/rules/weapons.yaml` (`TGMCClaws`, `TGMCSlam`)

- [ ] **Step 1: Add the new weapon effects so the lint fails**

`TGMCClaws` gets `Warhead@6Slash: CreateEffect` with `Image: fx-impact`, `Explosions: claw, claw2`, `ValidRelationships: Enemy`, `ValidTargets: Human, Structure`. `TGMCSlam` gets `Warhead@4Impact: CreateEffect` with `Image: fx-slam-big`, `Explosions: impact`, `ForceDisplayAtGroundLevel: true`, `ValidTargets: Ground, Water, Structure`.
Run: `py -3 -I mod/lint_static.py`
Expected: errors that `fx-impact` has no `claw` and that `fx-slam-big` is not made.

- [ ] **Step 2: Add the sequences**

`fx-impact`: `claw` from `(FX32, "claw", None, {"tick": 60})` and `claw2` from `(FX32, "claw2", None, {"tick": 60})`. New image `fx-slam-big` with `impact` from `(FX96, "throw_impact_s", None, {"tick": 60})`.
Run: `py -3 -I mod/lint_static.py`
Expected: `0 error(s)`

- [ ] **Step 3: Commit**

```bash
git add mod/build_sprites.py tgmc/rules/weapons.yaml
git commit -m "Add claw and slam hit effects from TGMC art"
```

### Task 6: Scenario that kills every unit by explosion and by other means

**Files:**
- Create: `mod/scenarios/test-gib.lua`
- Modify: `mod/make_placeholders.py` (`SCENARIOS["scenario-gib"]`)
- Modify: `mod/test_scenarios.sh` (fail on an exception log even after PASS)

**Interfaces:**
- Produces: `scenario-gib`, printing `TEST gib PASS` once every listed actor is dead.

- [ ] **Step 1: Add the scenario map and script**

`scenario-gib`: `{"scripts": ("test-gib",), "actors": [...]}` with one each of rifleman, medic, engineer, smartgunner, grenadier (Marines) and runner, hunter, sentinel, drone, warrior, queen (Xenos), a few cells apart, plus the usual far-off `resin-silo`. `test-gib.lua` keeps the first and second halves apart: on `WorldLoaded` it calls `Kill("ExplosionDeath")` on the Marines' first three units and the Xenos' runner, hunter, warrior and queen, and plain `Kill()` on the rest. After 50 ticks it prints `TEST gib PASS` if all are `IsDead`, else `TEST gib FAIL (alive: ...)` naming them.

- [ ] **Step 2: Make `test_scenarios.sh` fail on engine exceptions**

In the final loop, after a PASS line is found, also fail if `$OUT/$name/support/Logs/exception*` exists, printing its first lines. A missing death sequence only throws when the animation renders.
Verify: `OPENRA_DIR=<built OpenRA> sh mod/test_scenarios.sh` (under WSL after `sh mod/setup.sh`).
Expected: `pass  scenario-gib` and every existing scenario still passing.

- [ ] **Step 3: Commit**

```bash
git add mod/scenarios/test-gib.lua mod/make_placeholders.py mod/test_scenarios.sh
git commit -m "Add a scenario that kills every unit by explosion and by other means"
```

### Task 7: README

**Files:**
- Modify: `README.md` (Effects section, Known gaps)

- [ ] **Step 1: Document the work**

Add to the Effects section: the fade and gib deaths and which units gib; the claw and slam hit effects. Remove from Known gaps the line saying the marine has no death sprite, and add the two deviations from this plan's list (no remains, no particles). Run `py -3 -I mod/lint_static.py` and `py -3 -I mod/test_effects.py` once more.
Expected: both clean.

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "Document the death, gib and hit effects"
```
