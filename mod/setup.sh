#!/bin/sh
# One-command bootstrap: fetch OpenRA and the TGMC art, build the mod, check it. Safe to re-run; finished steps are skipped.
#
#   mod/setup.sh
#
# Everything lands in build/ (git-ignored):
#   build/OpenRA                    OpenRA at the commit this mod was tested against, built with `make all`
#   build/terragov-marine-corps     sparse, blob-less clone of TGMC holding only the files the converters read
#   build/mod/tgmc                  the assembled mod, linked into build/OpenRA/mods/tgmc
#   build/tools/dotnet              .NET 10 SDK, installed only if there is none on the machine
#
# Overrides (environment): OPENRA_DIR, TGMC, TGMC_REF, DOTNET_CHANNEL. Needs git, python3 with Pillow, ffmpeg with libvorbis,
# make, curl (only to install .NET), and a POSIX shell. Linux and macOS work; on Windows run setup.cmd (mod/bootstrap.py).
# The TGMC art and sound are CC-BY-NC(-SA): the result is for your own use, never to be shared.
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
BUILD="$ROOT/build"
OPENRA_DIR=${OPENRA_DIR:-"$BUILD/OpenRA"}
TGMC=${TGMC:-"$BUILD/terragov-marine-corps"}
PY=${PYTHON:-python3}

# Pinned so a later change in either project cannot silently break the mod. Bump after re-running the test scripts.
OPENRA_URL=https://github.com/OpenRA/OpenRA.git
OPENRA_COMMIT=e7e9e4ad270221d7fb9725b348c75504d48c1ebd
TGMC_URL=https://github.com/tgstation/terragov-marine-corps.git
TGMC_REF=${TGMC_REF:-37eb19c8710ac8a07115f2132f802ca106896ea2}
DOTNET_CHANNEL=${DOTNET_CHANNEL:-10.0}

step() { printf '\n==> %s\n' "$1"; }
die() { printf 'setup: %s\n' "$1" >&2; exit 1; }

# ---------------------------------------------------------------- prerequisites
step "Checking prerequisites"
case $(uname -s) in
	Linux) hint_pkg="sudo apt install git python3-pil ffmpeg make   (or your distribution's equivalents)" ;;
	Darwin) hint_pkg="brew install git python pillow ffmpeg make" ;;
	*) hint_pkg="install git, Python 3 with Pillow, ffmpeg and make (on Windows, run setup.cmd instead)" ;;
esac
missing=
for tool in git make bash ffmpeg ffprobe "$PY"; do
	command -v "$tool" >/dev/null 2>&1 || missing="$missing $tool"
done
[ -z "$missing" ] || die "missing:$missing
  try: $hint_pkg"
"$PY" -c 'import PIL' 2>/dev/null || die "Python Pillow is missing. try: $PY -m pip install pillow   ($hint_pkg)"
ffmpeg -hide_banner -encoders 2>/dev/null | grep -q libvorbis || die "this ffmpeg has no libvorbis encoder; install a full ffmpeg build"
echo "git, make, ffmpeg (libvorbis), $PY with Pillow: ok"

# ---------------------------------------------------------------- .NET 10
step ".NET SDK"
if [ -x "$BUILD/tools/dotnet/dotnet" ]; then
	DOTNET_ROOT="$BUILD/tools/dotnet"
	export DOTNET_ROOT PATH="$DOTNET_ROOT:$PATH"
fi
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
if command -v dotnet >/dev/null 2>&1 && dotnet --version 2>/dev/null | grep -q '^10\.'; then
	echo "dotnet $(dotnet --version): ok"
else
	command -v curl >/dev/null 2>&1 || die "no .NET 10 SDK and no curl to install one. Install the SDK from https://dotnet.microsoft.com/download"
	echo "No .NET 10 SDK found; installing it into $BUILD/tools/dotnet (nothing outside build/ is touched)"
	mkdir -p "$BUILD/tools"
	curl -fsSL https://dot.net/v1/dotnet-install.sh -o "$BUILD/tools/dotnet-install.sh" || die "could not download dotnet-install.sh (network blocked?). Install the SDK by hand: https://dotnet.microsoft.com/download"
	bash "$BUILD/tools/dotnet-install.sh" --channel "$DOTNET_CHANNEL" --install-dir "$BUILD/tools/dotnet"
	DOTNET_ROOT="$BUILD/tools/dotnet"
	export DOTNET_ROOT PATH="$DOTNET_ROOT:$PATH"
	dotnet --version | grep -q '^10\.' || die "the installed SDK is not .NET 10"
fi

# ---------------------------------------------------------------- OpenRA
step "OpenRA ${OPENRA_COMMIT%"${OPENRA_COMMIT#???????}"}"
mkdir -p "$OPENRA_DIR"
if [ ! -d "$OPENRA_DIR/.git" ]; then
	git -C "$OPENRA_DIR" init -q
	git -C "$OPENRA_DIR" remote add origin "$OPENRA_URL"
fi
if [ "$(git -C "$OPENRA_DIR" rev-parse -q --verify HEAD 2>/dev/null || true)" != "$OPENRA_COMMIT" ]; then
	git -C "$OPENRA_DIR" fetch --depth 1 origin "$OPENRA_COMMIT"
	git -C "$OPENRA_DIR" checkout -q --force FETCH_HEAD
fi
if [ ! -f "$BUILD/.openra-built" ] || [ "$(cat "$BUILD/.openra-built")" != "$OPENRA_COMMIT" ]; then
	(cd "$OPENRA_DIR" && make all)
	echo "$OPENRA_COMMIT" > "$BUILD/.openra-built"
else
	echo "already built"
fi

# ---------------------------------------------------------------- TGMC art
step "TGMC art (sparse clone, only the files the converters read)"
"$PY" -I "$HERE/tgmc_paths.py" > "$BUILD/tgmc-paths.txt"
export GIT_LFS_SKIP_SMUDGE=1
mkdir -p "$TGMC"
if [ ! -d "$TGMC/.git" ]; then
	git -C "$TGMC" init -q
	git -C "$TGMC" remote add origin "$TGMC_URL"
fi
git -C "$TGMC" config core.sparseCheckout true
git -C "$TGMC" sparse-checkout init --no-cone 2>/dev/null || true
git -C "$TGMC" sparse-checkout set --no-cone --stdin < "$BUILD/tgmc-paths.txt"
if [ "$(git -C "$TGMC" rev-parse -q --verify HEAD 2>/dev/null || true)" != "$TGMC_REF" ]; then
	git -C "$TGMC" fetch --depth 1 --filter=blob:none origin "$TGMC_REF"
	git -C "$TGMC" checkout -q --force FETCH_HEAD
else
	git -C "$TGMC" checkout -q --force HEAD  # picks up files added to the path list since last time
fi
absent=0
while IFS= read -r path; do
	[ -f "$TGMC/$path" ] || { echo "missing in TGMC checkout: $path"; absent=1; }
done < "$BUILD/tgmc-paths.txt"
[ "$absent" = 0 ] || die "TGMC no longer has the files above at $TGMC_REF. Set TGMC_REF to an older commit."
echo "$(wc -l < "$BUILD/tgmc-paths.txt" | tr -d ' ') files present"

# ---------------------------------------------------------------- mod
step "Building the mod"
TGMC="$TGMC" OPENRA_DIR="$OPENRA_DIR" sh "$HERE/build_mod.sh"

step "Checking the mod with OpenRA's own lint"
OPENRA_DIR="$OPENRA_DIR" sh "$HERE/check_mod.sh"

cat <<DONE

Done. Start the game with:

    mod/play.sh                 main menu (Skirmish: Landing Zone, Hold the Line)
    mod/play.sh landing-zone    straight into a map

The mod is for your own use only; the TGMC art and sound are non-commercial licences, so do not share build/.
DONE
