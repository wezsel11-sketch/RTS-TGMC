# Eight-hour run: plan

Agreed with the user on 2026-11-24. The run is unattended: it goes from one phase to the next without asking.

## Rules

- Commit each finished task on `ccr-c31f20d2-inlmko`, and push it (the user asked for push; each push runs the install CI). No release.
- At most 4 game instances at once. Drop to 2 when free memory is under 4 GiB (`free -g`), because the freqtrade fleet shares the box.
- Always the full build (`mod/build_mod.sh` with dotnet on PATH). Never an rsync overlay.
- A phase that breaks a scenario that passed before is not done: fix or revert before the commit.
- Log every round, decision and number in `.superpowers/sdd/eight-hour-run/progress.md`, and write a summary for the user at the end.

## Phases, in priority order

No time cap (the user, 2026-11-24: "if it takes longer, go on"). Phases run in this order until all are done, then the final check.

**Final check** (last, always): full build, `mod/check_mod.sh`, the full `mod/test_scenarios.sh`, all 42 aimap maps, a 60-minute soak,
headless menu click-through (`TGMC_MENU_SHOT`), the desync check (two clients, same match) and a whole-branch code review. Every bug
found is fixed with a failing test first, then the whole suite is rerun. The summary lists what passed, what was fixed and what remains.
The TGMC checkout in `build/terragov-marine-corps` is partial (no xeno or game-mode code), so the TGMC systems below are rebuilt
from how TGMC plays, not ported line by line. Each new system is a lobby option where that makes sense, so a broken one can be switched off.

1. **Review minors** (`2026-11-18-review-minors.md`): finish Task 5 (bot tests, 42 aimap maps), then Task 6 (build, lint, full suite). Commit and push.
2. **Downed, revive, cocoon (TGMC's core loop).** A marine at zero health is downed, not dead, for a bleed-out timer. A Corpsman (defib) revives him. A xeno drags a downed marine to the hive and cocoons him: psy points for the hive and a larva. Both bots use it. Tests: downed, revive, cocoon, bleed-out. Then an aimap run against the phase 1 baseline.
3. **Distress objective.** Disk computers on each map that marines capture by holding them; carried disks arm a nuke at a fixed spot; xenos win by stopping it in time. A lobby win condition next to annihilation. Bots attack and defend the objective. Tests and an aimap run.
4. **Map upgrades.**
   - Default weather per map, as TGMC sets it (snowstorm on Ice Colony, sandstorm on Desert Dam, acid rain on LV-624, and so on). Storms cut sight range.
   - Landing setup time: the marine landing zone is closed off for the first minutes (TGMC's fog walls), so the hive can set up.
   - Power and lights: generators light the colony; xenos cut the power and the map goes dark; flares light it.
   - Hazards: lava, chasms, and doors that xenos pry open.
   - Disk computers and the nuke placed on every map (needed by phase 3).
5. **Crash mode.** The ship crashes into the colony, and marines must nuke the hive before a timer runs out. A second skirmish mode built on phase 3.
6. **Campaign (SOM vs TGMC).** A strategic map of missions in a chain, with assets carried over. The first mission is the evac mission in the 2026-11-07 spec.
7. **Xeno AI balance loop**, after the new mechanics have changed the economy. Baseline: the 42 `aimap-*` maps at 4 at a time, recording the winner, the decided tick, the fields each side holds and the xeno weed nodes. The 2026-11-17 score was 21–9 to the marines. Each round changes one thing in the xeno bot (silo defence, drone economy, attack timing, upgrade order), reruns the maps and keeps the change only if it moves the score toward even without breaking a bot test. Stop at about 50/50 or after about an hour.
8. **Upgrade ladders** (`PLAN-upgrades.md`): settle which building unlocks which upgrade, add the armour, SMG and shotgun ladders, and write tests for the carapace and claws bonuses.
9. **Soak.** AI matches of 60 minutes or more: crashes, memory growth (the `TgmcVoiced` world-leak fix) and frame time late in a match.
10. **More new content** (the user picked these):
   - New skirmish maps in the existing themes, each played through by the AI-vs-AI runner.
   - Immersion: weather (rain, snow, sandstorm by map theme), more effects, and other ambient touches found while playing.
