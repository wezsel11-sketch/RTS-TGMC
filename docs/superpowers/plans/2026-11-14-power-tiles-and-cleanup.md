# Power tiles (HUD A6) and code cleanup

Written 2026-11-14. Two parts: the support power tiles, built now, and a cleanup round, planned here and not started.
Details item A6 and Track E of `2026-11-11-fable-week-roadmap.md`.

## Part 1: support power tiles

### What is wrong today

The marines have 22 support powers (`tgmc/rules/structures.yaml`): 9 Condor close air support runs, 5 orbital
strikes, 5 drops, smoke, sensor sweep and the recall bell. The engine already shows one icon per power type, so the
count is not a duplication fault. The fault is the layout: the engine's `SupportPowersWidget` draws one column, 38 px
a row, starting at Y 242. Twenty-two rows need 836 px and run off an 800 px screen. Five orbital powers share one icon.

(An earlier note said "one tile per type with a count". That was wrong: the engine does that already.)

### Design

One tile per **family**, in one short column under the minimap:

| Family | Powers | Rule |
|---|---|---|
| Air | the Condor runs | `OrderName` starts with `Cas` |
| Orbital | orbital strikes, railgun | `OrderName` starts with `Orbital` or is `RailgunOrder` |
| Drops | pod, sentry, mortar, supply, mech | trait is `DropPodPower` |
| Support | smoke, sensor, bell, and every xeno power | the rest |

A tile shows the icon of the family's power that is ready or will be ready soonest, a count "ready / total", and that
power's timer. A tile with a ready power pulses amber.

Click a tile: a family of one power fires it. A larger family opens a row of its powers to the left of the tile; click
one to target it, and the row closes. The hovered power's name and timer are written above the row. Keys
`SupportPower01` to `06` act on the first six tiles.

### Code

- New `tgmc/code/PowerTiles.cs`: `PowerTilesWidget : Widget`. Reads `SupportPowerManager.Powers` each tick (cheap: at
  most 27 entries), groups, lays out, draws with `WidgetUtils.DrawPanel` and `DrawSpriteCentered`, the same calls the
  engine widget uses. Clicking uses `SupportPowerInstance.Target()` and the engine's "not active" sound, as
  `SupportPowersWidget.ClickIcon` does.
- `tgmc/chrome/ingame-player.yaml`: `Container@SUPPORT_POWERS` holds one `PowerTiles@POWER_TILES`; the
  `SupportPowerBinLogic`, `PALETTE_BACKGROUND` and `SUPPORT_PALETTE` entries go.
- `tgmc/code/Events.cs` `FactionSkinLogic`: one more case, so the tiles take the xeno and SOM skins.
- Later, not in this piece: a different icon for each of the five orbital strikes (`mod/build_icons.py`).

### Proof

- A shot scenario with every power unlocked, marines and xenos: the column ends above the command card, nothing
  covers the minimap.
- A scenario that fires one power through the widget's own click path is not possible from Lua; the click path is
  checked by hand in one windowed run, and `scenario-*` tests that use powers through orders must still pass.
- Lint and the full suite.

## Part 2: cleanup (planned, not started)

Each item is its own commit, with the full suite before and after. None changes behaviour.

1. **Find dead code with a real tool.** A first grep-based scan was unreliable. Write `mod/find_unused.py`: every
   `*Info`, `*Logic`, `*Widget`, `*Warhead` class in `tgmc/code` against the merged rules, weapons and chrome YAML;
   every sequence and image against the rules; every `.ogg` against the rules and voices; every fluent key against
   YAML and C#. Delete what it finds. Lint already reports two unused fluent attributes
   (`actor-hugger-trap.description`, `actor-miner-field.description`) and one unused condition (`apc` grants `loading`).
2. **`mod/make_placeholders.py` (2,316 lines).** It makes placeholder art, writes maps, holds 193 scenario and shot map
   definitions, and runs the TGMC map conversion. Split into `maps.py` (writer and generator), `scenario_maps.py`
   (the table) and the art that is left. Its name no longer says what it does.
3. **`tgmc/code/Bots.cs` (1,641 lines).** One file per bot module, as the roadmap's D5 already asks.
4. **`tgmc/code/Events.cs` (864 lines)** holds the event log, the command card, selection keys and the faction skin.
   One file each; `Hud.cs` keeps the selection card.
5. **`tgmc/chrome/ingame-player.yaml` (1,420 lines).** Eight `GRP_ICON_n` cells, six `EVENT_n` lines and the command
   slots are copies. Build them from one template in the logic class, as `SupportPowerBinLogic` does, and drop the copies.
6. **Rules.** `units.yaml` is 3,698 lines. Look for blocks repeated across units that belong in a `^Template`
   (armour tiers, the per-role Jaeger bodies, voice and death sets). Measure before and after with the lint's merged output.
7. **Two flood fills and one Dijkstra in `write_tgmc_map`** now do the same reachability job three times. One helper.
8. **Docs.** `PLAN-upgrades.md` and the README "Known gaps" describe an older state (four castes, the sidebar HUD).
   Rewrite "Known gaps" from the tree; fold what is still open in `PLAN-upgrades.md` into the roadmap and delete the file.
9. **Stale build inputs.** `test-field` and other dev maps ship in the package (`build/mod/tgmc/maps` has 74). List
   which are for tests only and keep them out of `mod/package.sh`.
10. **Determinism (roadmap E1)** is a correctness job, not cleanup, but belongs in the same round: the 13
    `LocalRandom` uses and the missing `[Sync]` fields.

Order: 1, 9, 8 (small, low risk), then 7, 5, 4, 3, 2, 6, then 10.
