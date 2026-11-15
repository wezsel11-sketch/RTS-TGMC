# Main menu and lobby: command deck over an Alamo landing, with a map picker

## Context

The menu and lobby still wear the green TACNET terminal (mockup m3), which covers the screen and looks nothing like
the in-game HUD (design C: dark glass, amber). The backdrop is a small grass field with a few marines. The user chose:

- **Layout:** command deck (mockup m2, `docs/menu-designs/m2-menu.png`, `m2-lobby.png`): big title, a row of mode
  cards, a news strip; dark glass and amber.
- **Backdrop:** an Alamo landing in a jungle clearing, in place of today's field.
- **Extra:** a map picker.

Not chosen, so not in this plan: faction cards in the lobby, debrief screen.

## What exists (reuse)

- `tgmc/chrome/mainmenu.yaml` (384 lines, `MainMenuLogic`), `tgmc/chrome/lobby.yaml`, `tgmc/chrome/lobby-players.yaml`;
  the rest of the lobby and the map chooser come from OpenRA's `common|chrome/*.yaml` (`tgmc/mod.yaml` `ChromeLayout`).
- Chrome atlas and panels (`tgui-window`, `tgui-card`, button states) from `mod/make_chrome.py`; the HUD already uses them.
- Shellmap: `test-field` (`write_map(... "Lobby, Shellmap" ...)` in `mod/make_placeholders.py`).
- Landing intro: `FactionStart` + `alamo-drop` (`tgmc/code/FactionStart.cs`), on by default.
- Menu text: `menu-*` keys in `tgmc/fluent/tgmc.ftl`. Menu screenshot hook: `MenuShotLogic` in `tgmc/code/Events.cs`.
- Map facts for the picker: the generator already knows size, bases and ore fields per map (`write_tgmc_map`).

## Steps

### 1. Backdrop: "shell-landing" map
- New shellmap written by `mod/make_placeholders.py`: a jungle clearing (grass, tree line, dirt track), one marine
  bot base and one xeno bot hive some distance off, `FactionStart` so the Alamo lands at tick 0, night off.
- A short Lua script: camera sits on the landing zone, then follows the squad; after about two minutes the xenos
  probe the line; when one side dies the match restarts, so the menu never shows an empty field.
- `test-field` loses `Shellmap` and its `Lobby` visibility (it stays for tests and `mod/play.sh`).
- The backdrop is dimmed by a dark gradient panel under the menu widgets, so text stays readable.

### 2. Main menu: command deck
- Rewrite the top level of `tgmc/chrome/mainmenu.yaml`: remove the terminal border, header and intel box.
  Title block top left ("OPERATION", "MARINES VS XENOS", one line of pitch), version top right.
- Bottom row of five cards: Skirmish, Hold the Line, Campaign, Codex, Settings. Each card: name, one line, its
  number key. Quit as a small button at the right end. Cards are `Button` widgets with a new `tgui-menucard`
  panel (normal, hover, pressed) added to `mod/make_chrome.py`; the first card carries the amber accent.
- News strip above the cards: three `menu-news-*` lines (what is new in this version).
- The existing sub-menus (singleplayer, extras, content) keep their logic ids, restyled as one glass panel.
- Hotkeys 1 to 5 on the cards (`Key:` on each button).

### 3. Lobby
- `tgmc/chrome/lobby.yaml` and `lobby-players.yaml`: same widgets and ids (the engine's `LobbyLogic` needs them),
  new layout and panels: players on the left, map preview and the option list on the right, chat along the bottom,
  Back bottom left, a large amber Start bottom right. Glass panels over the same dimmed backdrop.
- Options panel shows the mod's own options first (requisition, night, weather, landing intro), then the rest.

### 4. Map picker
- A mod copy of OpenRA's map chooser layout (`tgmc/chrome/map-chooser.yaml`, replacing the `common|` entry in
  `mod.yaml`), same logic ids: larger preview on the right, list on the left.
- Under the preview: size, bases, ore fields and one line of description. The generator writes these beside each
  map; a small `ChromeLogic` in `tgmc/code` fills four labels from the selected map.
- Filter tabs by the categories the maps already carry (Conquest, Survival, missions) plus small / full size.
- Map previews: check each built `map.png` is the real terrain render; regenerate where it is a placeholder.

### 5. Text and cleanup
- New fluent keys; delete the unused `menu-intel-*` and terminal keys.
- README: menu section and one screenshot. `docs/menu-designs/` stays as the record of the three options.

## Verification
- `MenuShotLogic` screenshots of the menu, the singleplayer sub-menu, the lobby and the map picker at 1280x720
  and 1920x1080; each read once, cropped.
- A scripted click-through: menu to skirmish lobby to map picker, pick a map, start; the match must start
  (`mod/smoke.sh` already launches through the menu).
- Shellmap runs 10 minutes headless without an exception log and restarts at least once.
- Lint (`mod/check_mod.sh`) and the full scenario suite.
- Windows package under Wine: menu opens, a skirmish starts.

## Then
Release 0.2.3 with this, the power tiles, the munition icons, the landing intro and the pod fix.

## Could add later (not in this plan)
Faction cards in the lobby, debrief screen with graphs, rotating backdrops (station siege, hive interior),
menu music per faction, a "continue last setup" card, mod settings page (hotkey profile, UI scale, colour-blind colours).
