#!/bin/sh
# Ready-to-play packages: the OpenRA engine with its own .NET runtime, the TGMC mod and its converted art and sound, and a launcher.
# A player unzips one archive and starts the game; nothing else to install.
#
#   OPENRA_DIR=build/OpenRA  mod/package.sh [version]
#
# Needs a built mod (mod/setup.sh or mod/build_mod.sh) and the .NET SDK. Cross-builds both platforms from Linux:
#   build/package/TGMC-<version>-windows-x64.zip       unzip, run TGMC.exe
#   build/package/TGMC-<version>-linux-x64.tar.gz      untar, run ./TGMC.sh
# The packages hold TGMC-derived art and sound, which are under TGMC's non-commercial licences: see PLAYING.txt in each.
# Not -u: OpenRA's packaging helpers loop on unset positional parameters.
set -e

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
OPENRA_DIR=$(cd "${OPENRA_DIR:-$ROOT/build/OpenRA}" && pwd)
VERSION=${1:-$(git -C "$ROOT" describe --tags --always)}
MOD="$ROOT/build/mod/tgmc"
DLL="$ROOT/build/tgmc-dll/Tgmc.dll"
OUT="$ROOT/build/package"
[ -d "$ROOT/build/tools/dotnet" ] && export PATH="$ROOT/build/tools/dotnet:$PATH" DOTNET_ROOT="$ROOT/build/tools/dotnet"
[ -f "$MOD/mod.yaml" ] && [ -f "$DLL" ] || { echo "package: build the mod first (mod/setup.sh)"; exit 1; }

. "$OPENRA_DIR/packaging/functions.sh"
rm -rf "$OUT"
mkdir -p "$OUT"

for PLATFORM in win-x64 linux-x64; do
	NAME=TGMC-$VERSION-$( [ "$PLATFORM" = win-x64 ] && echo windows-x64 || echo linux-x64 )
	DEST="$OUT/$NAME"
	echo "==> $NAME"
	install_assemblies "$OPENRA_DIR" "$DEST" "$PLATFORM" True False False
	install_data "$OPENRA_DIR" "$DEST"
	cp "$DLL" "$DEST/"
	# A real copy: in the build tree mods/tgmc is a link to build/mod/tgmc.
	cp -rL "$MOD" "$DEST/mods/tgmc"
	rm -rf "$DEST/mods/tgmc/code"
	set_engine_version "$VERSION" "$DEST"
	set_mod_version "$VERSION" "$DEST/mods/tgmc/mod.yaml"
	sed "s/@VERSION@/$VERSION/" "$HERE/packaging/PLAYING.txt" > "$DEST/PLAYING.txt"
	if [ "$PLATFORM" = win-x64 ]; then
		install_windows_launcher "$OPENRA_DIR" "$DEST" "$PLATFORM" tgmc TGMC "TGMC: Marines vs Xenos" \
			"https://github.com/wezsel11-sketch/RTS-TGMC" "$VERSION"
		(cd "$OUT" && rm -f "$NAME.zip" && zip -qr9 "$NAME.zip" "$NAME")
	else
		cp "$HERE/packaging/TGMC.sh" "$DEST/TGMC.sh"
		chmod +x "$DEST/TGMC.sh"
		(cd "$OUT" && tar -czf "$NAME.tar.gz" "$NAME")
	fi
done
ls -lh "$OUT"/*.zip "$OUT"/*.tar.gz
