# Units, controls and deaths Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the requested xeno castes and marine units, make marines fall instead of becoming husks, add move-click feedback, and smooth the camera with a C# trait.

**Architecture:** YAML rules and `mod/build_sprites.py` add units from TGMC art. Placeholder art (`mod/make_placeholders.py`) covers effects with no TGMC source. A small C# assembly in the mod adds the smooth camera widget logic, loaded through `Assemblies:` in `tgmc/mod.yaml` and built against the pinned OpenRA in `build/OpenRA`.

**Tech Stack:** OpenRA YAML rules, Python 3 with Pillow (sprite pipeline), Lua scenario scripts, C# (.NET SDK installed by `mod/setup.sh`).

**Spec:** none written yet. This plan is the working spec for this batch; `docs/superpowers/specs/` has no file for it.

## Global Constraints

- TGMC art pinned at commit `37eb19c8710ac8a07115f2132f802ca106896ea2` (`mod/setup.sh`, `TGMC_REF`). Art paths must exist at that commit.
- OpenRA pinned at commit `e7e9e4ad270221d7fb9725b348c75504d48c1ebd` (`mod/setup.sh`, `OPENRA_COMMIT`).
- Non-commercial use only. Never commit `build/` or any TGMC-derived art.
- `mod/lint_static.py` must report 0 errors after every task.
- Nothing is committed until the user approves.

## Review Focus

Inputs and conditions a player will meet that no task above exercises by default:

1. A fast Runner or Shrike ordered to move across a cell that a slow unit occupies: the move must not stall the scroll or the click flash.
2. Camera smoothing at map edges and with edge scroll off: the view must stop at the map border and must not drift when the mouse leaves the window.
3. A marine killed while a builder is placing a structure: the fallen sprite must not block placement (fallen units keep no collision).
4. A machine gunner or sniper ordered onto a cell with no line of sight: the order must still be accepted and must not crash the weapon.
5. Two orders in the same tick (move click plus attack-move key): the click flash must show once, at the final target cell.

Each line is pinned by a test in the owning task's step style (Tasks 8 and 9).

---

## File Structure

- Modify: `mod/build_sprites.py` — unit sprite entries, `fall_frames`, `fallen`, marine death rule.
- Modify: `mod/make_placeholders.py` — `write_move_flash` (done).
- Modify: `tgmc/rules/units.yaml` — new unit actors, speed changes (speed done).
- Modify: `tgmc/rules/weapons.yaml` — new weapons (`TGMCMG60` done).
- Modify: `tgmc/rules/structures.yaml` — production prerequisites for new units if needed.
- Modify: `tgmc/rules/world.yaml` — `OrderEffects` (done).
- Modify: `tgmc/sequences/misc.yaml` — `moveflsh` (done).
- Modify: `tgmc/mod.yaml` — sequence registrations and `Assemblies:`.
- Modify: `tgmc/fluent/tgmc.ftl` — unit names and descriptions.
- Create: `tgmc/code/TgmcCamera.csproj`, `tgmc/code/SmoothScroll.cs` — C# camera logic.
- Modify: the chrome yaml under `tgmc/chrome` that holds `ViewportScrollController` — point the widget at the new logic.
- Create: `mod/scenarios/test-units.lua` and register it in `mod/test_scenarios.sh`.
- Modify: `README.md` — Known gaps (husk line, unit list, controls).

---

### Task 1: Speed and click feedback (done, verify)

**Files:**
- Modify: `tgmc/rules/units.yaml` (Speed lines)
- Modify: `tgmc/rules/world.yaml` (`OrderEffects`)
- Modify: `tgmc/sequences/misc.yaml` (`moveflsh`)
- Modify: `mod/make_placeholders.py` (`write_move_flash`)

**Interfaces:**
- Consumes: placeholder generator output `moveflsh.png` (128x32, 4 frames).
- Produces: `OrderEffects.TerrainFlashImage: moveflsh` read by OpenRA on every order.

- [ ] **Step 1: Test the click flash sheet**

Run: `python3 -I mod/make_placeholders.py --out build/ph-test && python3 -c "from PIL import Image; im=Image.open('build/ph-test/moveflsh.png'); assert im.size==(128,32); print('ok')"`
Expected: `ok`

- [ ] **Step 2: Lint**

Run: `python3 mod/lint_static.py`
Expected: `lint_static: 0 error(s)`

- [ ] **Step 3: Scenario check in game**

Run: `mod/test_scenarios.sh` (after `mod/setup.sh` has built OpenRA)
Expected: all existing scenarios pass. The `scenario-units` check for the click effect is added in Task 9.

---

### Task 2: Marine death topples (done, verify)

**Files:**
- Modify: `mod/build_sprites.py` (`fall_frames`, `fallen`, marine death rule)

**Interfaces:**
- Consumes: marine `stand` layer stack from `marine()`.
- Produces: `die` sequence for every marine unit with 6 frames, 90 ms each, facing-major.

- [ ] **Step 1: Test the fall frames**

Add to `mod/test_effects.py`:

```python
def test_fall_frames_end_on_side():
    img = Image.new("RGBA", (32, 32), (255, 0, 0, 255))
    frames = build_sprites.fall_frames(img, 6)
    assert len(frames) == 6
    assert frames[0].tobytes() == img.tobytes()
    assert frames[-1].size == (32, 32)
```

- [ ] **Step 2: Run it**

Run: `python3 -I mod/test_effects.py`
Expected: passes.

- [ ] **Step 3: Check the rule applies**

Run: `python3 -I mod/build_sprites.py --tgmc build/terragov-marine-corps --out build/mod/tgmc && grep -A5 "die:" build/mod/tgmc/sequences/rifleman.yaml`
Expected: a `die:` entry with `Length: 6` and `Tick: 90`.

- [ ] **Step 4: Visual check**

Open `build/mod/tgmc/sprites/rifleman.png` and confirm the last six cells of the die row show the figure turning on its side.

- [ ] **Step 5: Lint**

Run: `python3 mod/lint_static.py`
Expected: 0 errors.

---

### Task 3: Machine gunner (done, verify)

**Files:**
- Modify: `mod/build_sprites.py` (`machinegunner`, `MG60`)
- Modify: `tgmc/rules/weapons.yaml` (`TGMCMG60`)
- Modify: `tgmc/rules/units.yaml` (`machinegunner`)
- Modify: `tgmc/mod.yaml` (`tgmc|sequences/machinegunner.yaml`)
- Modify: `tgmc/fluent/tgmc.ftl` (`actor-machinegunner`)

**Interfaces:**
- Consumes: `icons/mob/inhands/guns/machineguns_right_64.dmi`, state `t60`, fitted to 32x32.
- Produces: actor `machinegunner`, buildable from `Infantry` queue, prerequisite `armory`.

- [ ] **Step 1: Build sprites**

Run: `python3 -I mod/build_sprites.py --tgmc build/terragov-marine-corps --out build/mod/tgmc`
Expected: a `machinegunner:` line with a cell count and no traceback.

- [ ] **Step 2: Lint**

Run: `python3 mod/lint_static.py`
Expected: 0 errors.

- [ ] **Step 3: Scenario**

Add a scenario in Task 9 that trains a `machinegunner` from an Infantry production building with an armory and checks it fires `TGMCMG60`.

---

### Task 4: Xeno castes (new)

Thirteen castes: spitter, praetorian, crusher, ravager, defiler, boiler, carrier, warlock, shrike, widow, wraith, bull, behemoth. Art: `icons/Xeno/castes/<name>.dmi` at the pinned commit.

**Files:**
- Modify: `mod/build_sprites.py` (one `UNITS` entry per caste, `XENO_UNITS` extended)
- Modify: `tgmc/rules/units.yaml` (one actor per caste, `Inherits: ^Xeno`)
- Modify: `tgmc/rules/weapons.yaml` only if a caste needs a weapon not in the set (`TGMCSpit`, `TGMCClaws`, `TGMCSlam`, `TGMCAcid`)
- Modify: `tgmc/mod.yaml` (sequence registration per caste)
- Modify: `tgmc/fluent/tgmc.ftl` (name and description per caste)

**Interfaces:**
- Consumes: DMI state names per caste (verified at the pinned commit):
  - spitter: `Spitter Walking`, `Spitter Running`, `Spitter Dead`, `gibbed-a`
  - praetorian: `Praetorian Walking`, `Praetorian Running`, `Praetorian Dead`, `gibbed-a`
  - crusher: `Crusher Walking`, `Crusher Running`, `Crusher Dead`, `gibbed-a`
  - ravager: `Ravager Walking`, `Ravager Running`, `Ravager Dead`, `gibbed-a`
  - defiler: `Defiler Walking`, `Defiler Running`, `Defiler Dead`, `gibbed-a`
  - boiler: `Boiler Walking`, `Boiler Running`, `Boiler Dead`, `gibbed-a-boiler`
  - carrier: `Carrier Walking`, `Carrier Running`, `Carrier Dead`, `gibbed-a`
  - warlock: `Warlock Walking` (3 frames), `Warlock Running` (3 frames), `Warlock Dead`, `gibbed-a`
  - shrike: `Shrike Walking`, `Shrike Running`, `Shrike Dead`, `gibbed-a`
  - widow: `Widow Walking`, `Widow Running`, `Widow Dead`, `gibbed-a`
  - wraith: `Wraith Walking`, `Wraith Running`, `Wraith Dead`, `gibbed-a`
  - bull: `Bull Walking`, `Bull Running`, `Bull Dead`, `gibbed-a`
  - behemoth: `Behemoth Walking`, `Behemoth Running`, `Behemoth Dead`, no gib (use `die`)
- Produces: actors with these stats (HP / speed / cost / weapon / prerequisite / palette order):
  - spitter 100 / 60 / 100 / TGMCSpit / evolution-tower / 40
  - praetorian 180 / 55 / 150 / TGMCClaws / evolution-tower / 60
  - crusher 280 / 40 / 250 / TGMCSlam / maturity-tower / 70
  - ravager 150 / 90 / 140 / TGMCClaws / evolution-tower / 80
  - defiler 200 / 45 / 220 / TGMCAcid / maturity-tower / 90
  - boiler 160 / 60 / 160 / TGMCAcid / evolution-tower / 100
  - carrier 200 / 65 / 180 / TGMCClaws / maturity-tower / 110
  - warlock 170 / 55 / 170 / TGMCSpit / maturity-tower / 120
  - shrike 140 / 100 / 130 / TGMCClaws / evolution-tower / 130
  - widow 150 / 45 / 150 / TGMCAcid / evolution-tower / 140
  - wraith 140 / 95 / 160 / TGMCClaws / maturity-tower / 150
  - bull 240 / 70 / 200 / TGMCSlam / maturity-tower / 160
  - behemoth 400 / 30 / 350 / TGMCSlam / maturity-tower / 170

These stats are placeholders for tuning. They are not balanced.

- [ ] **Step 1: Write the failing test**

Add to `mod/test_effects.py`:

```python
def test_every_xeno_caste_has_sprites():
    for caste in ["spitter", "praetorian", "crusher", "ravager", "defiler", "boiler",
                  "carrier", "warlock", "shrike", "widow", "wraith", "bull", "behemoth"]:
        assert caste in build_sprites.UNITS, caste
```

- [ ] **Step 2: Run it to see it fail**

Run: `python3 -I mod/test_effects.py`
Expected: FAIL with `AssertionError: spitter`

- [ ] **Step 3: Add the sprite entries**

For each caste add a `UNITS` entry in the same shape as `runner`, for example:

```python
"spitter": {
    "sequences": {
        "walk": [(SPITTER, "Spitter Walking")],
        "run": [(SPITTER, "Spitter Running")],
        "stand": "walk#1",
        "die": [(SPITTER, "Spitter Dead")],
        "die-gib": [(SPITTER, "gibbed-a", None, {"tick": 70})],
        "attack": "stand",
        "icon": "stand:S",
    },
},
```

with `SPITTER = "icons/Xeno/castes/spitter.dmi"` defined next to the other `icons/Xeno` constants. Behemoth uses `"die-gib": "die"`, as `warrior` does.

Add all thirteen names to `XENO_UNITS`.

- [ ] **Step 4: Run the test**

Run: `python3 -I mod/test_effects.py`
Expected: passes.

- [ ] **Step 5: Add the actors**

For each caste, add to `tgmc/rules/units.yaml`:

```yaml
spitter:
	Inherits: ^Xeno
	Voiced:
		VoiceSet: HunterVoice
	Health:
		HP: 100
	Selectable:
		Bounds: 768, 768, -384, -512
	Mobile:
		Speed: 60
	Armament@PRIMARY:
		Weapon: TGMCSpit
	Tooltip:
		Name: actor-spitter.name
	Valued:
		Cost: 100
	Buildable:
		Queue: Xeno
		BuildPaletteOrder: 40
		Prerequisites: evolution-tower
		Description: actor-spitter.description
```

Use the values from the stats list. `^Xeno` already supplies `Targetable@ALIEN` and `WithInfantryBody`, so no per-caste change is needed for those.

- [ ] **Step 6: Add the names**

Add to `tgmc/fluent/tgmc.ftl`, one pair per caste, for example:

```
actor-spitter =
    .name = Xeno Spitter
    .description = Ranged acid spitter. Needs an Evolution Tower. Costs 100 requisition.
```

- [ ] **Step 7: Register the sequences**

Add `tgmc|sequences/<caste>.yaml` lines to `tgmc/mod.yaml` after `tgmc|sequences/warrior.yaml`, one per caste.

- [ ] **Step 8: Lint and check the build**

Run: `python3 -I mod/build_sprites.py --tgmc build/terragov-marine-corps --out build/mod/tgmc && python3 mod/lint_static.py`
Expected: 0 errors. The lint fails if a sequence file is missing from `mod.yaml`, so this also checks Step 7.

---

### Task 5: Marine mech (new)

Art: `icons/mecha/mech_medium.dmi`, `mech_assault.dmi`, `mech_recon.dmi`, `mech_vanguard.dmi` at the pinned commit. These are vehicle sheets. The sprite pipeline builds only infantry sequences (`walk`/`run`/`stand`/`die`), so this task needs a vehicle sprite path first.

**Files:**
- Modify: `mod/build_sprites.py` (mech sequences: 4 facings, no walk cycle)
- Modify: `tgmc/rules/units.yaml` (actor with a vehicle body instead of `WithInfantryBody`)
- Modify: `tgmc/rules/weapons.yaml` (a heavy weapon for the mech)
- Modify: `tgmc/mod.yaml`, `tgmc/fluent/tgmc.ftl`

**Interfaces:**
- Consumes: mech states from `mech_medium.dmi` (confirmed in Step 1).
- Produces: actor `mech`, buildable from a production building. The mod has no vehicle factory yet; Step 1 picks one.

- [ ] **Step 1: Inspect the mech states and decide the production building**

Run: `python3 -I -c "import sys; sys.path.insert(0,'mod'); import tgmc_dmi; d=tgmc_dmi.Dmi('build/terragov-marine-corps/icons/mecha/mech_medium.dmi'); print([(s['name'],s.get('dirs'),s.get('frames')) for s in d.states])"`
Expected: a list of states with direction and frame counts. Pick the walking and dead states and the production building. Record both before Step 2.

- [ ] **Step 2: Write the failing test**

Add to `mod/test_effects.py`:

```python
def test_mech_has_sequences():
    assert "mech" in build_sprites.UNITS
    assert "stand" in build_sprites.UNITS["mech"]["sequences"]
```

- [ ] **Step 3–6:** Add the sprite entry, the actor, the weapon, the names and the sequence registration, following Task 4 Steps 3–7. Use a vehicle locomotor only if lint and the smoke test accept it; otherwise keep `foot` and record the gap in the README.

- [ ] **Step 7: Lint and check**

Run: `python3 mod/lint_static.py`
Expected: 0 errors.

---

### Task 6: Marine sniper (new)

Art: marksman inhands (`icons/mob/inhands/guns/marksman_right_64.dmi`, state to confirm in Step 1).

**Files:**
- Modify: `mod/build_sprites.py` (`sniper` entry, same shape as `machinegunner`)
- Modify: `tgmc/rules/weapons.yaml` (`TGMCSniper`: long range, single shot, high damage)
- Modify: `tgmc/rules/units.yaml` (`sniper` actor, Infantry queue, prerequisite armory)
- Modify: `tgmc/mod.yaml`, `tgmc/fluent/tgmc.ftl`

**Interfaces:**
- Consumes: the marksman inhand state name (confirmed in Step 1).
- Produces: actor `sniper`, `Range: 12c0`, long `ReloadDelay`.

- [ ] **Step 1: Confirm the state name**

Run: `python3 -I -c "import sys; sys.path.insert(0,'mod'); import tgmc_dmi; d=tgmc_dmi.Dmi('build/terragov-marine-corps/icons/mob/inhands/guns/marksman_right_64.dmi'); print([s['name'] for s in d.states])"`
Expected: a list including the marksman rifle state.

- [ ] **Step 2–5:** Test, sprite entry, weapon, actor, names and sequence registration, following Task 3.

- [ ] **Step 6: Scenario**

Add to Task 9 a scenario that a sniper hits a Runner at 10 cells.

---

### Task 7: Marine mortar, SADAR and Vali melee (blocked on art)

No art found yet at the pinned commit for SADAR, mortar man, or Vali melee. TGMC has mortar code (`code/game/objects/machinery/artillery/mortar.dm`) and mortar ammo (`code/modules/projectiles/ammo_types/mortar_ammo.dm`), but no sprite has been located.

- [ ] **Step 1: Find the art**

Search the TGMC tree at the pinned commit for SADAR, mortar and Vali sprite names. Start with `icons/obj/items/guns`, `icons/obj/machines/artillery`, `icons/obj/items/weapons` and `icons/mob/inhands`.

- [ ] **Step 2: Report back**

If art is found, plan each unit the same way as Task 6. If not, report which of the three have no art and ask the user whether to use a placeholder or drop the unit.

---

### Task 8: Smooth camera (C#)

**Files:**
- Create: `tgmc/code/TgmcCamera.csproj`
- Create: `tgmc/code/SmoothScroll.cs`
- Modify: `tgmc/mod.yaml` (`Assemblies: TgmcCamera.dll`)
- Modify: the chrome yaml under `tgmc/chrome` that defines `ViewportScrollController` (found by grep)

**Interfaces:**
- Consumes: `OpenRA.Widgets.ViewportScrollControllerWidget` from `build/OpenRA` (pinned commit).
- Produces: a `SmoothScrollController` logic class that eases the viewport toward the scroll target each frame, clamped to the map bounds.

- [ ] **Step 1: Write the failing check**

The mod has no C# test project. Add a headless check to `mod/smoke.sh` that loads the mod and fails if the `SmoothScrollController` logic cannot be created. Expected before the change: `unknown logic class SmoothScrollController`.

- [ ] **Step 2: Create the project**

`tgmc/code/TgmcCamera.csproj` references `OpenRA.Game.dll` and `OpenRA.Mods.Common.dll` from the built engine in `build/OpenRA`. Match the target framework in `build/OpenRA/global.json`; read it before writing the project file.

- [ ] **Step 3: Implement the logic**

`SmoothScroll.cs` defines `SmoothScrollController` deriving from the engine's viewport scroll logic, with:
- an exponential ease toward the scroll target, with rate from `Settings.ViewportEdgeScrollStep` (present in `OpenRA.Game/Settings.cs` at the pinned commit);
- clamp to the map's projected bounds;
- no movement while the window is unfocused.

- [ ] **Step 4: Point the chrome at it**

Change the `Logic:` of the scroll widget in the chrome yaml from `ViewportScrollController` to `SmoothScrollController`.

- [ ] **Step 5: Build and check**

Run: `dotnet build tgmc/code/TgmcCamera.csproj -c Release -o build/mod/tgmc/bin`, then `mod/smoke.sh`.
Expected: smoke test passes; the logic loads.

- [ ] **Step 6: Edge cases (Review Focus 2)**

Add a smoke check that the camera stops at the map border with edge scroll on and off.

---

### Task 9: Scenario tests

**Files:**
- Create: `mod/scenarios/test-units.lua`
- Modify: `mod/test_scenarios.sh` (register `scenario-units`)

**Interfaces:**
- Consumes: the unit actors from Tasks 3–6 and the `moveflsh` effect from Task 1.
- Produces: scenario checks for each new unit's production, firing and death, and the click effect.

- [ ] **Step 1: Write the scenario**

`test-units.lua` checks, in order:
1. A `machinegunner`, a `sniper`, and each new xeno caste can be produced from its queue once the prerequisite is built.
2. A marine killed in a scenario leaves a `die` sequence, not `husk`.
3. A move order creates one `moveflsh` effect at the target cell (Review Focus 5).
4. An order to a cell with no line of sight is accepted and does not error (Review Focus 4).

- [ ] **Step 2: Run it to see it fail**

Run: `mod/test_scenarios.sh scenario-units`
Expected: FAIL until Tasks 3–6 and Task 1 are in place.

- [ ] **Step 3: Run it after the tasks are done**

Run: `mod/test_scenarios.sh`
Expected: all scenarios pass, including `scenario-units`.

---

### Task 10: Airstrike (blocked on art)

An airstrike needs an aircraft sprite. None has been found at the pinned commit. OpenRA supports the power through `SupportPower` with `AirstrikePower`.

- [ ] **Step 1: Find an aircraft sprite**

Search `icons/obj/machines`, `icons/mecha` and `icons/Xeno` at the pinned commit for a plane or dropship sprite.

- [ ] **Step 2: Report back**

If found, plan `AirstrikePower` on a marine structure with a cooldown. If not, ask the user whether to use a placeholder aircraft or skip the power.

---

### Task 11: README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update Known gaps**

Replace the husk line with a note that marines topple on death (`fallen` in `mod/build_sprites.py`). Add the new units to the How to play tables. Add the controls note: camera smoothing lives in `tgmc/code/`.

- [ ] **Step 2: Lint**

Run: `python3 mod/lint_static.py`
Expected: 0 errors.

---

## Self-Review

1. **Spec coverage:** No spec file exists, so coverage is against the user's requests in order: xeno castes (Task 4), marines SADAR/mortar/mech/sniper/Vali (Tasks 5–7), machine gunner (Task 3), marine deaths (Task 2), click feedback (Task 1), camera smoothing (Task 8), airstrike (Task 10), speed (Task 1, done), README (Task 11). Tasks 7 and 10 are blocked on art, and Task 5 needs a vehicle sprite path that does not exist yet.
2. **Placeholder scan:** Tasks 5 and 6 point to Task 4 and Task 3 for some steps and do not repeat the YAML. Tasks 7 and 10 have no implementation steps by design (blocked). Task 5 needs its production building chosen in Step 1 before execution.
3. **Type consistency:** unit actor names (`machinegunner`, `sniper`, `mech`, the 13 castes), weapon names (`TGMCMG60`, `TGMCSniper`) and sequence names (`moveflsh`, `die`) match across tasks.
4. **Review Focus:** Lines 1–5 are pinned by Task 9 steps 1 and 3–4 and Task 8 step 6.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-12-units-controls-deaths.md`. Please review the plan. Two tasks are blocked on art (Task 7 and Task 10), and Task 5 needs a vehicle sprite path. Which execution approach would you prefer?

- **Subagent-driven:** A fresh subagent implements each task and a fresh reviewer checks it before the next one starts, then a whole-branch review at the end. Most thorough; costs a fresh context per task and per review.
- **Native:** I implement every task myself in this session, then one fresh reviewer checks the whole branch. Cheapest and fastest; no independent review until the end.

For this plan I recommend Native, because the tasks share the same unit files and YAML, and a shipped mistake in `units.yaml` is easy to catch in lint and scenario tests. Does the plan capture what you want, and which approach should we use?

---

## Status as built (2026-10-13)

The plan above predates most of this work; it was done directly in this session instead of task by task. Everything below is
uncommitted and covered by `mod/scenarios/test-*.lua` (run headless with `SDL_VIDEODRIVER=offscreen`, see `README.md`).

- Units: rifleman (random T-12, T-18 or M412), corpsman (SMG), engineer (shotgun), smartgunner, grenadier, machine gunner, sniper,
  rocketeer, blademan, mortarman, flamer, B18 heavy gunner, B17 demolitionist, Durand mech; 13 xeno castes, facehugger, larva.
- C# in `tgmc/code`: fire while moving, spread out, smooth scroll, flamer cone, weeds, facehugger infestation, evolve and devolve,
  pounce, damage variation, maturity, evasion, hugger egg, lobby options, tile-step movement, snapping building ghost, selection ring,
  ammo/infection/cooldown/maturity bars, selection card.
- Mechanics: magazines and reloads, armour classes, explosive friendly fire, stun, CAS strike support power, bullet-miss dust,
  screen shake.
- Buildings: medbay, ammo station, workshop, recovery pylon, gargoyle, hugger egg.

Not done, or only built and never used by hand: the Alamo HQ, the facing swap for diagonal moves, real sound output (no `ffmpeg` here),
and everything that needs a mouse (tile-step movement, ghost snapping, the lobby options, the support power click).
