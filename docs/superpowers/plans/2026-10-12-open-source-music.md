# Open-Source Music Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the thin TGMC music (10-20 s stings buried under ambience loops) with 23 full-length, openly licensed songs, played faction- and fight-aware by the existing music script.

**Architecture:** `build_sounds.py` gains a download-and-verify step for Kevin MacLeod's CC BY 4.0 tracks (cached in `build/open-music/`, pinned by sha256 in a committed file), re-encodes them with a new `score` kind, and treats them like any other sound. `music.yaml` lists them with the artist in the title (the in-game music player shows it, which is the CC BY credit). `music.lua` draws them as its main theme and combat pools; the TGMC short themes and the ambience loops move to the "calm" pool, drawn one pick in three instead of one in two.

**Tech Stack:** Python 3 stdlib (`urllib`, `hashlib`, `unittest`), ffmpeg with libvorbis, OpenRA YAML and Lua.

**Spec:** the user's request, "Can we improve the music? Maybe we can pull out some more normal music. Or open source music". No separate spec; the decisions are in this plan.

## Global Constraints

- Source of all new music: `https://incompetech.com/music/royalty-free/mp3-royaltyfree/<Title>.mp3`, Kevin MacLeod, **Creative Commons: By Attribution 4.0**. Credit form: `"Title" Kevin MacLeod (incompetech.com), Licensed under Creative Commons: By Attribution 4.0, https://creativecommons.org/licenses/by/4.0/`.
- Music files stay out of git (`*.ogg`, `*.mp3` are in `.gitignore`); only the pinned hash file `mod/open-music.sha256` is committed.
- Track keys are `score-<slug>`; their `music.yaml` title ends in ` - Kevin MacLeod`.
- `score` kind: stereo, 44100 Hz, peak -9 dB, whole file, Vorbis quality 4. Playlist `VolumeModifier: 0.8`. These levels are chosen by number, not heard.
- `mod/lint_static.py` must pass; `build_mod.sh` runs it first. Python is run with `-I` (isolated), as the existing scripts are.
- The working tree has an unrelated uncommitted change in `mod/make_placeholders.py` and an untracked `TempTerraGov/`: `git add` only the files each task names.

## Review Focus

- A rebuild with no network: the cached, hash-matching file must be used without any request.
- Upstream changes a file, or a download is cut short: the build must fail naming the file and leave nothing in the cache (a half file must never pass the next build).
- Titles with spaces and a hyphen (`Ossuary 7 - Resolve`) must produce a working URL.
- A track added to `music.yaml` without the artist credit must fail lint (CC BY compliance).
- A track in `music.yaml` that no pool plays, or a pool naming a track not in `music.yaml`, must fail lint for the new `score-` keys (the existing check only knows `theme-` and `ambient-`).
- Not tested, accepted: a combat track keeps playing after a fight ends (the script lets it finish). The chosen combat tracks are the shorter ones, 1 to 3 minutes.

---

## Track list (used by Tasks 2 and 3)

| Key | Title (file is `<Title>.mp3`) | Pool |
| --- | --- | --- |
| score-intrepid | Intrepid | marines themes |
| score-rynos-theme | Rynos Theme | marines themes |
| score-decisions | Decisions | marines themes |
| score-prelude-and-action | Prelude and Action | marines themes |
| score-ossuary-resolve | Ossuary 7 - Resolve | marines themes |
| score-heart-of-nowhere | Heart of Nowhere | marines themes |
| score-dark-times | Dark Times | xenos themes |
| score-unseen-horrors | Unseen Horrors | xenos themes |
| score-anguish | Anguish | xenos themes |
| score-the-descent | The Descent | xenos themes |
| score-deep-haze | Deep Haze | xenos themes |
| score-ether-vox | Ether Vox | xenos themes |
| score-frozen-star | Frozen Star | xenos themes |
| score-crypto | Crypto | xenos themes |
| score-aggressor | Aggressor | marines combat |
| score-faceoff | Faceoff | marines combat |
| score-dangerous | Dangerous | marines combat |
| score-failing-defense | Failing Defense | marines combat |
| score-space-fighter-loop | Space Fighter Loop | marines combat |
| score-volatile-reaction | Volatile Reaction | xenos combat |
| score-hot-pursuit | Hot Pursuit | xenos combat |
| score-killing-time | Killing Time | xenos combat |
| score-hitman | Hitman | xenos combat |

All 23 URLs answered HTTP 200 on 2026-10-12 (about 2.4 to 9 MB each, about 120 MB in total). Not used: Kevin MacLeod's other tracks, and the OpenGameArt "Outer Space Music Pack" (CC BY, but its songs are split into intro and loop files that would need joining).

### Task 1: Download and verify (`fetch_open`)

**Files:**
- Modify: `mod/build_sounds.py` (new constants and functions above `spec`)
- Test: `mod/test_open_music.py` (create)

**Interfaces:**
- Produces: `OPEN_MUSIC_BASE: str`, `CACHE: str` (`build/open-music` under the repo root), `HASHES: str` (path of `mod/open-music.sha256`), `read_hashes(path: str = HASHES) -> dict[str, str]` (file name to sha256; file lines are `<sha256>  <file name>`, a missing file gives `{}`), `fetch_open(filename: str, hashes: dict[str, str], base: str = OPEN_MUSIC_BASE, cache: str = CACHE) -> str` (path of the verified cached file).

- [ ] **Step 1: Write the failing tests** in `mod/test_open_music.py`, a `unittest.TestCase` that serves files with a `file://` base (`pathlib.Path(tmp).as_uri() + "/"`), sys.path set up like `lint_static.py` does. Tests:
  - `test_downloads_and_verifies`: source dir holds `Ossuary 7 - Resolve.mp3` (bytes `b"abc"`); `fetch_open("Ossuary 7 - Resolve.mp3", {name: sha256(b"abc")}, base, cache)` returns `os.path.join(cache, name)` and the file holds `b"abc"`.
  - `test_cached_file_needs_no_network`: after the first call, calling again with `base="file:///does/not/exist/"` returns the same path.
  - `test_hash_mismatch_fails_and_leaves_no_cache`: with a wrong hash, `assertRaises(RuntimeError)`, the message contains the file name, and `os.listdir(cache)` is empty (no `.part` either).
  - `test_unpinned_file_fails`: `fetch_open("X.mp3", {}, ...)` raises `RuntimeError` whose message contains `--pin-music`.
  - `test_read_hashes`: a file with two `<hash>  <name>` lines (one name with spaces) reads into the right dict; a missing path gives `{}`.

- [ ] **Step 2: Run to verify failure**

Run: `python -I mod/test_open_music.py`
Expected: FAIL with `AttributeError: module 'build_sounds' has no attribute 'fetch_open'` (or import error).

- [ ] **Step 3: Implement** `read_hashes` and `fetch_open` in `mod/build_sounds.py`. `fetch_open`: if `cache/filename` exists and its sha256 equals the pinned one, return it with no request; otherwise download `base + urllib.parse.quote(filename)` with `urllib.request.urlopen` to `cache/filename.part`, compare sha256, `os.replace` to the final name on a match, and on a mismatch delete the `.part` and raise `RuntimeError(f"{filename}: sha256 {got} does not match the pinned {want}")`. A name missing from `hashes` raises `RuntimeError` saying to run `build_sounds.py --pin-music`. Create the cache directory with `os.makedirs(exist_ok=True)`.

- [ ] **Step 4: Run to verify pass**

Run: `python -I mod/test_open_music.py`
Expected: `Ran 5 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add mod/build_sounds.py mod/test_open_music.py
git commit -m "feat: download and hash-verify openly licensed music for the build"
```

### Task 2: Wire the tracks into the sound build

**Files:**
- Modify: `mod/build_sounds.py` (`KINDS`, docstring table, `OPEN_MUSIC`, `SOUNDS`, `main`)
- Create: `mod/open-music.sha256` (generated by `--pin-music`)

**Interfaces:**
- Consumes: `fetch_open`, `read_hashes`, `HASHES` from Task 1.
- Produces: `KINDS["score"] = (2, 44100, -9.0, None, 4)`; `OPEN_MUSIC: dict[str, str]` (key to title, the 23 rows of the track list); every key in `SOUNDS` as `(f"{OPEN_PREFIX}{title}.mp3", "score")` with `OPEN_PREFIX = "open-music/"`; CLI flags `--only PREFIX` (build only sounds whose name starts with PREFIX) and `--pin-music` (download every track unverified and write `mod/open-music.sha256`, sorted, then exit). `--tgmc` becomes optional and is required only when a selected sound is not an open-music one.

- [ ] **Step 1: Add the `score` kind, the `OPEN_MUSIC` table and the `SOUNDS` entries.** In `main`, resolve a source starting with `OPEN_PREFIX` through `fetch_open(filename, read_hashes())`, any other through `os.path.join(args.tgmc, source)`. Add `--only` and `--pin-music` as described; `--pin-music` reuses a download helper split out of `fetch_open` so there is one download code path. Update the docstring's kind table with the `score` row.

- [ ] **Step 2: Pin the hashes** (downloads about 120 MB from incompetech.com, once)

Run: `python -I mod/build_sounds.py --pin-music`
Expected: prints `pinned 23 tracks`; `mod/open-music.sha256` has 23 lines, each `<64 hex>  <Title>.mp3`.

- [ ] **Step 3: Build only the scores**

Run: `python -I mod/build_sounds.py --only score- --out build/score-test`
Expected: prints `23 sounds, <N> KiB -> build/score-test`; 23 `.ogg` files plus `sounds.json`; every entry in `sounds.json` has `kind: "score"`, `gain_db` between -24 and 24, and `seconds` between 60 and 260.

- [ ] **Step 4: Re-run offline.** Disconnect or set `HTTPS_PROXY=http://127.0.0.1:9`, run the Step 3 command again.
Expected: same output, no network error (cache hit).

- [ ] **Step 5: Commit**

```bash
git add mod/build_sounds.py mod/open-music.sha256
git commit -m "feat: build 23 Kevin MacLeod tracks as stereo score music"
```

### Task 3: Playlist, pools and lint

**Files:**
- Modify: `mod/lint_static.py:54-60` (music cross-reference), `tgmc/audio/music.yaml`, `tgmc/scripts/music.lua`

**Interfaces:**
- Consumes: the keys and titles of the track list; `build_sounds.SOUNDS` (lint already reads it).
- Produces: `music.yaml` entries `score-*`; `TGMCMusic.Config.calmEvery = 3`; pools below.

- [ ] **Step 1: Extend the lint (the test).** In `mod/lint_static.py`, change the `scripted` regex to `(?:theme|ambient|score)-` and add one error: every `music.yaml` entry whose key starts with `score-` must have a title (the text after `key: `) ending in ` - Kevin MacLeod`, else `f"music track {key} has no artist credit in its title (CC BY)"`.

- [ ] **Step 2: Add the 23 entries to `tgmc/audio/music.yaml`** in the existing format (`<key>: <Title> - Kevin MacLeod`, then `Filename: <key>`, `Extension: ogg`, `VolumeModifier: 0.8`), placed after the `theme-*` entries. Replace the header comment with one that says what the file now holds (full-length Kevin MacLeod songs, CC BY 4.0, credited in the titles and the README; TGMC themes and ambience as the calm backdrop).

- [ ] **Step 3: Run lint, expect failure**

Run: `python -I mod/lint_static.py`
Expected: FAIL, 23 lines like `music track score-intrepid is in audio/music.yaml but no pool in scripts/music.lua plays it`; no credit errors.

- [ ] **Step 4: Update `tgmc/scripts/music.lua` pools.** In `TGMCMusic.Pools`: `marines.themes` and `xenos.themes` become the `score-*` keys of their rows in the track list (marines: 6, xenos: 8). `calm` gains the TGMC short themes, keeping the ambience: marines add `theme-hopeful-1`, `theme-hopeful-2`, `theme-lobby`, `theme-elevator`; xenos add `theme-melancholy-1`, `theme-melancholy-2`, `theme-dread`. `combat` becomes the faction's `score-*` combat rows plus its existing `theme-tense-*` entries (xenos keep `theme-dread` there too, which stays in `calm` as well). The observer pool in `StartMusic` takes `themes` from three marine and three xenos `score-*` keys, `calm` from `TGMCMusic.Pools.marines.calm`, `combat` from both factions' combat score keys. Add `calmEvery = 3` to `Config` and change `NextTrack` so a pick is calm when `turn % TGMCMusic.Config.calmEvery == 0` and a theme otherwise. Update the header comment (themes are now full songs; ambience every third pick).

- [ ] **Step 5: Run lint, expect pass**

Run: `python -I mod/lint_static.py`
Expected: exit 0, no output errors.

- [ ] **Step 6: Pin the credit check.** Temporarily remove ` - Kevin MacLeod` from one title in `music.yaml`, run `python -I mod/lint_static.py`.
Expected: FAIL with `music track score-... has no artist credit in its title (CC BY)`. Restore the title and re-run: exit 0.

- [ ] **Step 7: Commit**

```bash
git add mod/lint_static.py tgmc/audio/music.yaml tgmc/scripts/music.lua
git commit -m "feat: play the Kevin MacLeod songs as themes and combat music"
```

### Task 4: Credits, docs and a real run

**Files:**
- Modify: `README.md` (lines 93, 107, 122-123, the Music paragraph at 204-213, and the licence note near the top of the inputs table)

- [ ] **Step 1: Update `README.md`.** Describe the new music (23 full-length songs by Kevin MacLeod, themes for each faction, shorter ones for fights, TGMC themes and ambience as a calm backdrop every third pick); mention `mod/open-music.sha256`, `--pin-music` and the `build/open-music/` cache; add a **Music credits** section with the credit line from Global Constraints plus the list of titles, noting that this music is CC BY 4.0 while the rest of `build/` stays TGMC non-commercial. Fix the sound counts ("about 200") and the `build_sounds.py` row in the layout table.

- [ ] **Step 2: Rebuild and lint everything**

Run: `sh mod/build_mod.sh` (needs `TGMC` set to a checkout, as `setup.sh` does)
Expected: ends with `built .../build/mod/tgmc`; `build/mod/tgmc/audio/` holds the 23 `score-*.ogg`.

- [ ] **Step 3: Run the engine checks and a game**

Run: `sh mod/check_mod.sh` then `sh mod/smoke.sh`
Expected: `tgmc: checks passed`; the smoke run exits 0 with no engine exception. Then `mod/play.sh landing-zone` and confirm by ear that a theme starts, the in-game music player shows the titles with "Kevin MacLeod", a fight switches to a combat track, and a full 3-4 minute song plays without a stall.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: credit the Kevin MacLeod music and describe the new playlist"
```

---

## Self-review

- **Coverage:** open-source music (Tasks 1-2), played in game (3), credit and docs (4). Faction/fight behaviour is kept; only pool contents and the calm cadence change.
- **Types:** `fetch_open(filename, hashes, base, cache)`, `read_hashes`, `HASHES`, `OPEN_PREFIX` are named identically in Tasks 1-2; the `score` kind tuple matches `KINDS`' shape.
- **Proportion:** the plan is longer than the code it describes only in the track table; no function bodies are given.
