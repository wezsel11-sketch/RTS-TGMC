#!/usr/bin/env python3
"""One-command bootstrap for every platform: fetch OpenRA and the TGMC art, build the mod, check it.

    python mod/bootstrap.py            (Windows: setup.cmd, Linux and macOS: mod/setup.sh does the same in shell)

Everything lands in build/ (git-ignored), exactly as mod/setup.sh does:
  build/OpenRA                    OpenRA at the commit this mod was tested against, built
  build/terragov-marine-corps     sparse, blob-less clone of TGMC holding only the files the converters read
  build/mod/tgmc                  the assembled mod, linked (copied on Windows without a junction) into build/OpenRA/mods/tgmc
  build/tools/dotnet              .NET 10 SDK, installed only if there is none on the machine

Needs git, Python 3 with Pillow and ffmpeg (with libvorbis) on the PATH. On Linux and macOS it also needs make; on Windows OpenRA's
own make.cmd builds the engine, so no make is needed. Safe to re-run; finished steps are skipped.
The TGMC art and sound are CC-BY-NC(-SA): the result is for your own use, never to be shared.
"""
import os
import shutil
import subprocess
import sys
import urllib.request

import buildlib as b

OPENRA_URL = "https://github.com/OpenRA/OpenRA.git"
OPENRA_COMMIT = "e7e9e4ad270221d7fb9725b348c75504d48c1ebd"
TGMC_URL = "https://github.com/tgstation/terragov-marine-corps.git"
TGMC_REF = os.environ.get("TGMC_REF", "37eb19c8710ac8a07115f2132f802ca106896ea2")
DOTNET_CHANNEL = os.environ.get("DOTNET_CHANNEL", "10.0")


def prerequisites():
    b.step("Checking prerequisites")
    hint = {"linux": "sudo apt install git python3-pil ffmpeg make   (or your distribution's equivalents)",
            "darwin": "brew install git python pillow ffmpeg make",
            "windows": "run mod\\windows-prereqs.ps1 in PowerShell (installs git, Python and ffmpeg with winget), then python -m pip install pillow"}[b.os_name()]
    missing = [t for t in ["git", "ffmpeg", "ffprobe"] + ([] if b.is_windows() else ["make"]) if shutil.which(t) is None]
    if missing:
        b.die("missing: " + " ".join(missing) + "\n  try: " + hint)
    try:
        import PIL  # noqa: F401
    except ImportError:
        b.die(f"Python Pillow is missing. try: {sys.executable} -m pip install pillow")
    encoders = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    if "libvorbis" not in encoders:
        b.die("this ffmpeg has no libvorbis encoder; install a full ffmpeg build" + (" (winget install Gyan.FFmpeg)" if b.is_windows() else ""))
    print("git, ffmpeg (libvorbis), Python with Pillow" + ("" if b.is_windows() else ", make") + ": ok")


def dotnet():
    b.step(".NET SDK")
    b.use_local_dotnet()
    if b.dotnet_version().startswith("10."):
        print(f"dotnet {b.dotnet_version()}: ok")
        return
    print(f"No .NET 10 SDK found; installing it into {b.DOTNET_DIR} (nothing outside build/ is touched)")
    tools = os.path.join(b.BUILD, "tools")
    os.makedirs(tools, exist_ok=True)
    try:
        if b.is_windows():
            script = os.path.join(tools, "dotnet-install.ps1")
            urllib.request.urlretrieve("https://dot.net/v1/dotnet-install.ps1", script)
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script, "-Channel", DOTNET_CHANNEL, "-InstallDir", b.DOTNET_DIR]
        else:
            script = os.path.join(tools, "dotnet-install.sh")
            urllib.request.urlretrieve("https://dot.net/v1/dotnet-install.sh", script)
            cmd = ["bash", script, "--channel", DOTNET_CHANNEL, "--install-dir", b.DOTNET_DIR]
    except OSError as e:
        b.die(f"could not download the .NET installer ({e}). Install the SDK by hand: https://dotnet.microsoft.com/download")
    subprocess.run(cmd, check=True)
    b.use_local_dotnet()
    if not b.dotnet_version().startswith("10."):
        b.die("the installed SDK is not .NET 10")


def openra():
    b.step("OpenRA " + OPENRA_COMMIT[:7])
    os.makedirs(b.OPENRA_DIR, exist_ok=True)
    if not os.path.isdir(os.path.join(b.OPENRA_DIR, ".git")):
        b.git(b.OPENRA_DIR, "init", "-q")
        b.git(b.OPENRA_DIR, "remote", "add", "origin", OPENRA_URL)
    if b.head(b.OPENRA_DIR) != OPENRA_COMMIT:
        b.git(b.OPENRA_DIR, "fetch", "--depth", "1", "origin", OPENRA_COMMIT)
        b.git(b.OPENRA_DIR, "checkout", "-q", "--force", "FETCH_HEAD")
    marker = os.path.join(b.BUILD, ".openra-built")
    if not os.path.isfile(marker) or open(marker).read().strip() != OPENRA_COMMIT:
        if b.is_windows():
            subprocess.run(["cmd", "/c", "make.cmd", "all"], cwd=b.OPENRA_DIR, check=True)
        else:
            subprocess.run(["make", "all"], cwd=b.OPENRA_DIR, check=True)
        with open(marker, "w") as f:
            f.write(OPENRA_COMMIT + "\n")
    else:
        print("already built")


def tgmc():
    b.step("TGMC art (sparse clone, only the files the converters read)")
    paths = subprocess.run([sys.executable, "-I", os.path.join(b.HERE, "tgmc_paths.py")], capture_output=True, text=True, check=True).stdout
    with open(os.path.join(b.BUILD, "tgmc-paths.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(paths)
    os.environ["GIT_LFS_SKIP_SMUDGE"] = "1"
    os.makedirs(b.TGMC, exist_ok=True)
    if not os.path.isdir(os.path.join(b.TGMC, ".git")):
        b.git(b.TGMC, "init", "-q")
        b.git(b.TGMC, "remote", "add", "origin", TGMC_URL)
    b.git(b.TGMC, "config", "core.sparseCheckout", "true")
    if b.is_windows():
        b.git(b.TGMC, "config", "core.longpaths", "true")  # some TGMC paths are long
    subprocess.run(["git", "-C", b.TGMC, "sparse-checkout", "init", "--no-cone"], capture_output=True)
    b.git(b.TGMC, "sparse-checkout", "set", "--no-cone", "--stdin", input=paths)
    if b.head(b.TGMC) != TGMC_REF:
        b.git(b.TGMC, "fetch", "--depth", "1", "--filter=blob:none", "origin", TGMC_REF)
        b.git(b.TGMC, "checkout", "-q", "--force", "FETCH_HEAD")
    else:
        b.git(b.TGMC, "checkout", "-q", "--force", "HEAD")  # picks up files added to the path list since last time
    wanted = [p for p in paths.splitlines() if p.strip()]
    absent = [p for p in wanted if not os.path.isfile(os.path.join(b.TGMC, p))]
    for p in absent:
        print("missing in TGMC checkout:", p)
    if absent:
        b.die(f"TGMC no longer has the files above at {TGMC_REF}. Set TGMC_REF to an older commit.")
    print(len(wanted), "files present")


def main():
    os.makedirs(b.BUILD, exist_ok=True)
    prerequisites()
    dotnet()
    openra()
    tgmc()
    b.step("Building the mod")
    b.build_mod()
    b.step("Checking the mod with OpenRA's own lint")
    b.check_mod()
    play = "play.cmd" if b.is_windows() else "mod/play.sh"
    print(f"""
Done. Start the game with:

    {play}                 main menu (Skirmish: Landing Zone, Hold the Line)
    {play} landing-zone    straight into a map

The mod is for your own use only; the TGMC art and sound are non-commercial licences, so do not share build/.""")


if __name__ == "__main__":
    main()
