#!/bin/sh
# Run many AI-vs-AI matches of a balance map and report who won, with a 95% interval on the marines' win rate. The game seed is
# random, so only a set of runs says anything; one match is an anecdote.
#
#   OPENRA_DIR=/path/to/OpenRA  mod/balance.sh [runs] [ceiling-seconds] [map] [extra-rules.yaml ...]
#
# The map is a dev map: balance-aivai (default: the Skirmish AI on both sides on Landing Zone), balance-holdline (the marine bot
# defending against the six waves) or any aimap-* (the same AI match on a full-size map). Each extra rules file is an arm of its own:
# its rules are added to the map's for those runs, and the summary sets each arm's win rate against the plain map's, so an upgrade or
# a tweak can be judged by `mod/balance.sh 40 400 balance-aivai tweak.yaml`. All arms share one job pool, interleaved.
#
# TGMC_FAST=1 (the default here) runs each match as fast as the CPU allows, drawing nothing. BALANCE_JOBS (default 4) caps how many
# run at once: each match takes a core. Per-run logs, with a STAT line every 500 or 1000 ticks, go to $BALANCE_OUT (default build/balance).
set -u

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
OPENRA_DIR=${OPENRA_DIR:?set OPENRA_DIR to a built OpenRA checkout}
OUT=${BALANCE_OUT:-"$ROOT/build/balance"}
export LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy SDL_VIDEODRIVER=offscreen TGMC_FAST=${TGMC_FAST:-1}
[ -d "$ROOT/build/tools/dotnet" ] && export PATH="$ROOT/build/tools/dotnet:$PATH" DOTNET_ROOT="$ROOT/build/tools/dotnet"
export DOTNET_CLI_TELEMETRY_OPTOUT=1

# One match: --one <map> <arm-number> <run-number> <ceiling-seconds> [rules-file]. Arm 0 is the plain map.
if [ "${1:-}" = "--one" ]; then
	map=$2 arm=$3 n=$4 ceiling=$5 rules=${6:-}
	dir="$OUT/arm$arm-run$n"
	support="$dir/support"
	copy="$support/maps/tgmc/{DEV_VERSION}/$map"
	mkdir -p "$(dirname "$copy")"
	cp -r "$ROOT/build/dev-maps/$map" "$copy"
	[ -n "$rules" ] && { printf '\n'; cat "$rules"; } >> "$copy/rules.yaml"
	uid=$(cd "$OPENRA_DIR" && sh utility.sh tgmc --map-hash "$copy" | tail -1)
	sh -c "cd '$OPENRA_DIR' && exec dotnet bin/OpenRA.dll Engine.EngineDir=.. Engine.SupportDir='$support' Game.Mod=tgmc Launch.Map=$uid" \
		> "$dir/game.log" 2>&1 &
	runner=$!
	waited=0
	while [ "$waited" -lt "$ceiling" ]; do
		grep -qE "TEST (aivai|holdline|aimap)|Fatal Lua Error|LuaException" "$dir/game.log" 2>/dev/null && break
		kill -0 "$runner" 2>/dev/null || break
		sleep 2
		waited=$((waited + 2))
	done
	pkill -f "Engine.SupportDir=$support" 2>/dev/null
	kill "$runner" 2>/dev/null
	wait "$runner" 2>/dev/null
	exit 0
fi

RUNS=${1:-8}
CEILING=${2:-400}
MAP=${3:-balance-aivai}
[ $# -gt 3 ] && shift 3 || set --
[ -d "$ROOT/build/dev-maps/$MAP" ] || { echo "no dev map $MAP: run mod/build_mod.sh first"; exit 1; }
for f in "$@"; do [ -f "$f" ] || { echo "no rules file $f"; exit 1; }; done

rm -rf "$OUT"
mkdir -p "$OUT"
# The job list, interleaved: run 1 of every arm, then run 2 of every arm, so a cut-short set stays even.
n=1
while [ "$n" -le "$RUNS" ]; do
	echo "$MAP 0 $n $CEILING"
	arm=1
	for f in "$@"; do
		echo "$MAP $arm $n $CEILING $(cd "$(dirname "$f")" && pwd)/$(basename "$f")"
		arm=$((arm + 1))
	done
	n=$((n + 1))
done > "$OUT/jobs"
start=$(date +%s)
xargs -P "${BALANCE_JOBS:-4}" -L 1 sh "$0" --one < "$OUT/jobs"

python3 -I - "$OUT" "$MAP" "$@" <<'EOF'
import glob, math, os, re, sys

out, mapname, rules = sys.argv[1], sys.argv[2], sys.argv[3:]
arms = ["plain map"] + [os.path.basename(r) for r in rules]


def wilson(k, n, z=1.96):
    """95% Wilson score interval for k successes in n."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


results = {}
for log in sorted(glob.glob(os.path.join(out, "arm*-run*", "game.log"))):
    arm, run = map(int, re.search(r"arm(\d+)-run(\d+)", log).groups())
    text = open(log, encoding="utf-8", errors="replace").read()
    line = next((l.replace("Lua debug: ", "") for l in text.splitlines() if re.search(r"TEST (aivai|holdline|aimap)", l)), "")
    tick = re.search(r"at tick (\d+)", line)
    if re.search(r"marines (won|at)|xenos lost", line):
        winner = "marines"
    elif re.search(r"xenos (won|at)|marines lost", line):
        winner = "xenos"
    else:
        winner = "none"
    results.setdefault(arm, []).append((run, winner, int(tick.group(1)) if tick else None, line or "no result (ceiling or crash)"))

rates = {}
for arm, name in enumerate(arms):
    runs = sorted(results.get(arm, []))
    print(f"== {name}")
    for run, winner, tick, line in runs:
        print(f"  run {run:2}: {line}")
    m = sum(1 for r in runs if r[1] == "marines")
    x = sum(1 for r in runs if r[1] == "xenos")
    ticks = sorted(r[2] for r in runs if r[1] != "none" and r[2] is not None)
    lo, hi = wilson(m, m + x)
    rates[arm] = (m, m + x, lo, hi)
    median = ticks[len(ticks) // 2] if ticks else "-"
    print(f"  marines won {m}, xenos won {x}, no result {len(runs) - m - x}; marine win rate "
          f"{(m / (m + x) if m + x else 0):.0%} (95% {lo:.0%} to {hi:.0%}), median end tick {median}")

# Each arm against the plain map: Newcombe's interval for the difference of two proportions.
k0, n0, l0, u0 = rates[0]
for arm in range(1, len(arms)):
    k1, n1, l1, u1 = rates[arm]
    if n0 == 0 or n1 == 0:
        continue
    p0, p1 = k0 / n0, k1 / n1
    d = p1 - p0
    lo = d - math.sqrt((p1 - l1) ** 2 + (u0 - p0) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p0 - l0) ** 2)
    verdict = "a real change" if lo > 0 or hi < 0 else "not distinguishable from no change"
    print(f"{arms[arm]} vs plain map: marine win rate {d:+.0%} (95% {lo:+.0%} to {hi:+.0%}): {verdict}")
EOF
echo "$MAP: $(wc -l < "$OUT/jobs") matches in $(( $(date +%s) - start )) s (TGMC_FAST=$TGMC_FAST, logs in $OUT)"
