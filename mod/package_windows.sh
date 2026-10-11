#!/bin/sh
# Maintainer script: rebuild the ready-to-run Windows x64 game in game/.
# Players never run this. They clone the repo and double-click PLAY.cmd.
#
#   mod/package_windows.sh
#
# Needs: git, python3 + Pillow, ffmpeg (libvorbis), curl. A .NET 10 SDK is used if
# `dotnet` is on PATH, otherwise one is installed under build/dotnet.
#
# Optional environment:
#   TGMC=/path/to/terragov-marine-corps   use this TGMC checkout instead of cloning one into build/tgmc-src
#   OPENRA_SRC=/path/to/OpenRA            use this OpenRA checkout (must be at mod/OPENRA_REF) instead of build/openra-src
#
# Output: game/ holds the self-contained win-x64 engine, mods/common and mods/tgmc.
# game/Support/ is the portable settings and log folder and is left alone.
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
BUILD="$ROOT/build"
GAME="$ROOT/game"
REF=$(tr -d '[:space:]' < "$HERE/OPENRA_REF")
OPENRA_SRC=${OPENRA_SRC:-$BUILD/openra-src}
STAGE="$BUILD/win-x64"

mkdir -p "$BUILD"

# 1. .NET SDK
if ! command -v dotnet >/dev/null 2>&1; then
	if [ ! -x "$BUILD/dotnet/dotnet" ]; then
		curl -sSL -o "$BUILD/dotnet-install.sh" https://dot.net/v1/dotnet-install.sh
		bash "$BUILD/dotnet-install.sh" --channel 10.0 --install-dir "$BUILD/dotnet"
	fi
	PATH="$BUILD/dotnet:$PATH"
	export PATH
fi
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1

# 2. OpenRA source at the pinned commit
if [ ! -d "$OPENRA_SRC/.git" ]; then
	git init -q "$OPENRA_SRC"
	git -C "$OPENRA_SRC" remote add origin https://github.com/OpenRA/OpenRA
fi
if [ "$(git -C "$OPENRA_SRC" rev-parse HEAD 2>/dev/null || true)" != "$REF" ]; then
	git -C "$OPENRA_SRC" fetch -q --depth 1 origin "$REF"
	git -C "$OPENRA_SRC" checkout -q FETCH_HEAD
fi

# 3. Self-contained win-x64 engine. Same publish call as OpenRA's packaging/functions.sh,
#    minus the C&C and Dune 2000 assemblies, which this mod does not use.
rm -rf "$STAGE"
(
	cd "$OPENRA_SRC"
	dotnet publish -c Release -r win-x64 --self-contained true \
		-p:TargetPlatform=win-x64 -p:CopyGenericLauncher=True \
		-p:CopyCncDll=False -p:CopyD2kDll=False \
		-p:Deterministic=true -p:PathMap="$OPENRA_SRC=." \
		-p:PublishDir="$STAGE"
)

# 4. Lay out game/ (keep Support/)
mkdir -p "$GAME/Support"
find "$GAME" -mindepth 1 -maxdepth 1 ! -name Support -exec rm -rf {} +
cp -R "$STAGE/." "$GAME/"
find "$GAME" -name '*.pdb' -delete
rm -f "$GAME/createdump.exe"
for f in AUTHORS COPYING "global mix database.dat"; do
	cp "$OPENRA_SRC/$f" "$GAME/"
done
cp -R "$OPENRA_SRC/glsl" "$GAME/glsl"
mkdir -p "$GAME/mods"
cp -R "$OPENRA_SRC/mods/common" "$GAME/mods/common"
printf '%s\n' "$REF" > "$GAME/VERSION"
cat > "$GAME/OPENRA_SOURCE.txt" <<EOF
The engine in this folder is OpenRA (GPL-3.0), built unmodified from
https://github.com/OpenRA/OpenRA/commit/$REF
with: dotnet publish -c Release -r win-x64 --self-contained true
EOF

# 5. The mod: build from TGMC and copy it in
if [ -z "${TGMC:-}" ]; then
	TGMC="$BUILD/tgmc-src"
	if [ ! -d "$TGMC/.git" ]; then
		GIT_LFS_SKIP_SMUDGE=1 git clone -q --depth 1 https://github.com/tgstation/terragov-marine-corps "$TGMC"
	fi
fi
TGMC="$TGMC" INSTALL_TO="$GAME/mods/tgmc" sh "$HERE/build_mod.sh"

echo "game/ ready: $(du -sh "$GAME" | cut -f1). Commit it and run PLAY.cmd on Windows."
