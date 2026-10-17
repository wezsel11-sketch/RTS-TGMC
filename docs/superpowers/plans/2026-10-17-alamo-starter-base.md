# Alamo Starter Base Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Marines start on the landing zone with the Alamo, a landed dropship that is their spawn point and build area.

**Architecture:** The Alamo is one building actor with a footprint read from `_maps/shuttles/alamo.dmm`. Its hatch cell is an `Exit`. It gives the marine build area (`GivesBuildableArea` with `marine-build`), the same way the cryo pod does for the bot. The map start places it in place of the marine cryo pod. Its sprite is composed from the dropship piece art.

**Tech Stack:** OpenRA YAML rules (`tgmc/rules/*.yaml`), Python build scripts (`mod/*.py`), Lua scenario tests, the C# mod assembly (only if a trait is missing).

**Spec:** `docs/superpowers/specs/2026-10-17-alamo-starter-base-design.md`

## Global Constraints

- Marines only: no change to xeno structures, units or AI behaviour except the bot's construction yard list.
- Keep the cryo pod as a buildable marine structure; only the landing-zone start changes.
- Use TGMC art from `build/terragov-marine-corps` through the build scripts; no new art files committed by hand.
- Each commit runs `python3 -I mod/lint_static.py` clean.

## Review Focus

1. Alamo destroyed while a unit is in production: production must stop, not crash.
2. Hatch cell blocked by a unit or structure: spawned units must still appear (nearest free cell).
3. Build area edge: structures placed exactly on the edge of the Alamo's area are accepted, one cell outside refused.
4. Bot with no cryo pod: the bot must still build around the Alamo as its construction yard.
5. Alamo start on a map without the marine base layout: the start must still place the Alamo on the landing zone.

## Task 1: Read the Alamo footprint and hatch

**Files:**
- Create: `mod/alamo_footprint.py`
- Test: `mod/tests/test_alamo_footprint.py`

**Interfaces:**
- Consumes: `_maps/shuttles/alamo.dmm` in the TGMC checkout.
- Produces: `footprint(path) -> list[tuple[int,int]]` (cells of non-`template_noop` pieces, origin at the top-left cell), `hatch(path) -> tuple[int,int]` (the cell holding `dropship_hatch`).

- [ ] **Step 1: Write the failing test**

```python
# mod/tests/test_alamo_footprint.py
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import alamo_footprint

ALAMO = os.path.join(os.path.dirname(__file__), "..", "..", "build", "terragov-marine-corps", "_maps", "shuttles", "alamo.dmm")

class AlamoFootprint(unittest.TestCase):
    def test_footprint_is_eleven_wide(self):
        cells = alamo_footprint.footprint(ALAMO)
        self.assertEqual(max(x for x, _ in cells) - min(x for x, _ in cells) + 1, 11)

    def test_hatch_is_on_the_footprint(self):
        cells = set(alamo_footprint.footprint(ALAMO))
        self.assertIn(alamo_footprint.hatch(ALAMO), cells)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest mod/tests/test_alamo_footprint.py -v`
Expected: FAIL with "No module named 'alamo_footprint'"

- [ ] **Step 3: Write minimal implementation**

```python
# mod/alamo_footprint.py
"""Cells of TGMC's Alamo dropship map, read from its piece layout (see the design spec).

The .dmm has one block per column (x = 1..11, y = 1, z = 1). Each block is a list of keys, one per row, top to bottom.
Each key is defined once as `"key" = ( ... )` with the atoms of that cell.
"""
import re

_DEF = re.compile(r'^"([a-zA-Z]+)" = \(\n(.*?)\)\n(?=")', re.S | re.M)
_BLOCK = re.compile(r'^\((\d+),1,1\) = \{"\n(.*?)\n"\}', re.S | re.M)


def _read(path):
    text = open(path, encoding="utf-8").read()
    defs = {key: body for key, body in _DEF.findall(text + '"')}
    columns = {int(x): body.split("\n") for x, body in _BLOCK.findall(text)}
    return defs, columns


def _is_piece(body):
    return "dropship_piece" in body or "dropship_hatch" in body


def footprint(path):
    """Cells (x, row) of the Alamo, origin at the top-left cell of the footprint."""
    defs, columns = _read(path)
    cells = [(x, row) for x, keys in columns.items() for row, key in enumerate(keys)
             if _is_piece(defs.get(key, ""))]
    ox = min(x for x, _ in cells)
    oy = min(row for _, row in cells)
    return [(x - ox, row - oy) for x, row in cells]


def hatch(path):
    """The first dropship hatch cell, relative to the same origin as footprint()."""
    defs, columns = _read(path)
    cells = [(x, row) for x, keys in columns.items() for row, key in enumerate(keys)
             if "dropship_hatch" in defs.get(key, "")]
    ox = min(x for x, _ in footprint_raw(path))
    oy = min(row for _, row in footprint_raw(path))
    x, row = min(cells)
    return (x - ox, row - oy)


def footprint_raw(path):
    defs, columns = _read(path)
    return [(x, row) for x, keys in columns.items() for row, key in enumerate(keys) if _is_piece(defs.get(key, ""))]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest mod/tests/test_alamo_footprint.py -v`
Expected: PASS (both tests). If the grid parser is still incomplete, finish it against the real block layout first.

- [ ] **Step 5: Commit**

```bash
git add mod/alamo_footprint.py mod/tests/test_alamo_footprint.py
git commit -m "Read the Alamo footprint and hatch from its dmm"
```

## Task 2: Alamo building actor

**Files:**
- Modify: `tgmc/rules/structures.yaml` (new `alamo` actor after `cryo-pod`)
- Modify: `tgmc/fluent/tgmc.ftl` (`actor-alamo.name`, `actor-alamo.description`)
- Modify: `tgmc/mod.yaml` (sequence entry for `alamo`)
- Modify: `mod/tgmc_paths.py` (add `_maps/shuttles/alamo.dmm` to the sparse checkout)

**Interfaces:**
- Consumes: footprint and hatch from Task 1 (dimensions and `ExitCell`).
- Produces: actor type `alamo` with `Building`, `Exit`, `GivesBuildableArea` (`marine-build`), `Health`.

- [ ] **Step 1: Write the failing check**

Run: `cd build/OpenRA && ./utility.sh tgmc --check-yaml 2>&1 | grep -c "alamo"`
Expected now: `0` (the actor does not exist; this is the baseline to change).

- [ ] **Step 2: Add the actor**

Add to `tgmc/rules/structures.yaml` after `cryo-pod:` (dimensions and `ExitCell` come from Task 1's output; the values below are the placeholders to replace with them):

```yaml
alamo:
	Inherits: ^Structure
	Building:
		# Generated by Task 1: 11 x 21 cells, x = occupied, _ = empty (39 cells; the hull is not a rectangle).
		Footprint:
			___xxxxx___
			___x___x___
			___________
			_xx_____xx_
			___________
			x_________x
			___________
			x_________x
			___________
			_x_______x_
			_x_______x_
			___________
			___________
			_x_______x_
			xx_______xx
			___________
			___________
			___________
			xxx_____xxx
			___x___x___
			_xxx___xxx_
		Dimensions: 11, 21
	Health:
		HP: 2000
	Exit@1:
		SpawnOffset: 0,512,0
		# Hatch from Task 1: cell (1, 9) relative to the footprint origin.
		ExitCell: 1,9
	RallyPoint:
		Path: 0, 5
	GivesBuildableArea:
		AreaTypes: marine-build
	Tooltip:
		Name: actor-alamo.name
	Valued:
		Cost: 0
```

- [ ] **Step 3: Verify**

Run: `cd build/OpenRA && ./utility.sh tgmc --check-yaml 2>&1 | grep -i "alamo" | head`
Expected: no `alamo` lines.

- [ ] **Step 4: Commit**

```bash
git add tgmc/rules/structures.yaml tgmc/fluent/tgmc.ftl tgmc/mod.yaml
git commit -m "Add the Alamo building actor"
```

## Task 3: Alamo sprite from the dropship pieces

**Files:**
- Modify: `mod/build_sprites.py` (new `alamo` entry)
- Modify: `mod/tgmc_paths.py` (dropship piece art directories)

**Interfaces:**
- Consumes: the Alamo's piece cells and their TGMC icon states from `tgmc_objects` (which already maps `/obj/structure/dropship_piece/...` pictures).
- Produces: sequence `alamo` in `build/mod/tgmc/sprites/alamo.png`.

- [ ] **Step 1: Write the failing check**

Run: `python3 mod/build_sprites.py --tgmc build/terragov-marine-corps --out build/mod/tgmc 2>&1 | grep -c alamo`
Expected now: `0`.

- [ ] **Step 2: Add the sprite entry**

Compose the Alamo from the piece pictures in cell order, one 32 px tile per cell, into one sheet entry named `alamo`, following the way `build_sprites.py` lays out other multi-cell sprites. Add the dropship art directories to `tgmc_paths.py` so the sparse checkout includes them.

- [ ] **Step 3: Verify**

Run: `python3 mod/build_sprites.py --tgmc build/terragov-marine-corps --out build/mod/tgmc && cd build/OpenRA && ./utility.sh tgmc --check-missing-sprites | grep -i alamo`
Expected: no `alamo` lines (no missing sprite).

- [ ] **Step 4: Commit**

```bash
git add mod/build_sprites.py mod/tgmc_paths.py
git commit -m "Compose the Alamo sprite from the dropship pieces"
```

## Task 4: Landing-zone start places the Alamo for marines

**Files:**
- Modify: `mod/make_placeholders.py` (`LANDING_ZONE`, marine cryo pod entry)

**Interfaces:**
- Consumes: the `alamo` actor from Task 2.
- Produces: marine start with `alamo` at the cryo pod's cell, the cryo pod removed from the start.

- [ ] **Step 1: Write the failing test**

Add a scenario `scenario-alamo-start` in `mod/make_placeholders.py` that uses the landing-zone actors and a Lua script `mod/scenarios/test-alamo-start.lua` that prints `TEST alamo-start PASS` when a marine `alamo` exists at tick 10.

- [ ] **Step 2: Run it to verify it fails**

Run: `./run-scen.sh scenario-alamo-start 60 | grep TEST`
Expected: `TEST alamo-start FAIL` (no alamo yet).

- [ ] **Step 3: Replace the start**

In `mod/make_placeholders.py` `LANDING_ZONE`, replace the marine `("cryo-pod", "Marines", 4, 12, 512)` entry with `("alamo", "Marines", 4, 12, 512)`.

- [ ] **Step 4: Run to verify it passes**

Run: `./run-scen.sh scenario-alamo-start 60 | grep TEST`
Expected: `TEST alamo-start PASS`.

- [ ] **Step 5: Commit**

```bash
git add mod/make_placeholders.py mod/scenarios/test-alamo-start.lua
git commit -m "Marines start on the Alamo"
```

## Task 5: Spawn and build-area behaviour

**Files:**
- Modify: `mod/make_placeholders.py` (scenarios `scenario-alamo-spawn`, `scenario-alamo-build`, `scenario-alamo-loss`)
- Create: `mod/scenarios/test-alamo-spawn.lua`, `mod/scenarios/test-alamo-build.lua`, `mod/scenarios/test-alamo-loss.lua`

**Interfaces:**
- Consumes: `alamo` from Task 2 (Exit, GivesBuildableArea).
- Produces: three scenario tests, each printing `TEST <name> PASS|FAIL`.

- [ ] **Step 1: Write the three tests**

- `alamo-spawn`: queue a rifleman at the marine production building next to the Alamo; expect a rifleman at the hatch cell or the nearest free cell within 2 cells, by tick 600.
- `alamo-build`: place a `sentry-turret` on a cell at the edge of the Alamo's area (inside) and one a cell outside; expect the inside one accepted, the outside one refused.
- `alamo-loss`: kill the Alamo; expect marine `GivesBuildableArea` removed (a refused placement next to it) and no crash.

- [ ] **Step 2: Run them to verify they fail**

Run each with `./run-scen.sh <name> 120 | grep TEST`. Expected: FAIL (behaviour not wired, or the actor not yet present in the scenario).

- [ ] **Step 3: Make them pass**

If a test fails for a reason in the rules (missing `Exit`, wrong `AreaTypes`), fix the rule in `tgmc/rules/structures.yaml`, rebuild with `make_placeholders.py`, and rerun. Do not change the test to match a wrong result.

- [ ] **Step 4: Run to verify**

Expected: all three `TEST ... PASS`.

- [ ] **Step 5: Commit**

```bash
git add mod/make_placeholders.py mod/scenarios/test-alamo-*.lua tgmc/rules/structures.yaml
git commit -m "Test the Alamo's spawn, build area and loss"
```

## Task 6: Bot treats the Alamo as its construction yard

**Files:**
- Modify: `tgmc/rules/ai.yaml` (`BaseBuilderBotModule@skirmish`: `ConstructionYardTypes`, `ProtectionTypes`)

**Interfaces:**
- Consumes: `alamo` actor type.
- Produces: the marine bot builds around the Alamo.

- [ ] **Step 1: Write the failing test**

`scenario-alamo-bot`: a marine skirmish bot with an Alamo and cash; expect a structure placed within 10 cells of the Alamo by tick 1500. Expected now: FAIL (the bot does not know the Alamo).

- [ ] **Step 2: Add the actor to the bot lists**

In `tgmc/rules/ai.yaml`, add `alamo` to `ConstructionYardTypes` and `ProtectionTypes` of `BaseBuilderBotModule@skirmish`.

- [ ] **Step 3: Run to verify it passes**

Expected: `TEST alamo-bot PASS`. Then run `scenario-ai` to check the marine bot still works.

- [ ] **Step 4: Commit**

```bash
git add tgmc/rules/ai.yaml mod/make_placeholders.py mod/scenarios/test-alamo-bot.lua
git commit -m "The marine bot builds around the Alamo"
```

## Task 7: Full checks

- [ ] Run `python3 -I mod/lint_static.py` (0 errors).
- [ ] Run `cd build/OpenRA && ./utility.sh tgmc --check-yaml` (only the known dev-map errors).
- [ ] Run `./utility.sh tgmc --check-missing-sprites` (no missing sprites).
- [ ] Add the `alamo-*` scenarios to `scratchpad/suite.sh` and run the full suite. Expected: no new FAIL.
- [ ] Hands-on: start a marine match on the landing zone; confirm the Alamo, its hatch exit, and the build area (not verifiable headless).

## Self-Review

1. **Spec coverage:** actor (T2), footprint (T1), sprite (T3), spawn (T5), build area (T5), start (T4), loss (T5), bot (T6), tests (T5, T6). Out-of-scope items are not implemented.
2. **Placeholder scan:** none. Task 1 has a complete parser; Task 2 carries the footprint rows and hatch offset that Task 1 produces (tested: 11 x 21, 39 cells, hatch (1, 9)).
3. **Type consistency:** `footprint` and `hatch` names match between Task 1 and their use in Task 2.
4. **Review Focus:** each of the five points is pinned to a test: 1 (loss), 2 (spawn fallback, test alamo-spawn), 3 (alamo-build), 4 (alamo-bot), 5 (alamo-start).

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-17-alamo-starter-base.md`. Please review the plan. No placeholders left. Task 1 must add `_maps/shuttles/alamo.dmm` to the sparse checkout first. Which execution approach would you prefer?

- **Subagent-driven** — a fresh subagent per task with review between tasks. Most thorough; more context cost.
- **Native** — I implement the tasks in this session, then one review at the end. Cheapest and fastest.

I recommend **Native**, because the tasks depend on each other in order (footprint, then actor, then sprite) and a shipped mistake would only affect the marine start. Does the plan capture what you want, and which approach should we use?
