"""Shared helpers for bootstrap.py, play.py and rebuild.py: paths, git, .NET, building and checking the mod on Linux, macOS and Windows."""
import os
import platform
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, "build")
OPENRA_DIR = os.environ.get("OPENRA_DIR", os.path.join(BUILD, "OpenRA"))
TGMC = os.environ.get("TGMC", os.path.join(BUILD, "terragov-marine-corps"))
DOTNET_DIR = os.path.join(BUILD, "tools", "dotnet")
MOD_OUT = os.path.join(BUILD, "mod", "tgmc")


def os_name():
    return {"Windows": "windows", "Darwin": "darwin"}.get(platform.system(), "linux")


def is_windows():
    return os.name == "nt"


def step(text):
    print(f"\n==> {text}", flush=True)


def die(text):
    print(f"setup: {text}", file=sys.stderr)
    sys.exit(1)


def git(repo, *args, input=None):
    subprocess.run(["git", "-C", repo, *args], check=True, input=input, text=True if input is not None else None)


def head(repo):
    r = subprocess.run(["git", "-C", repo, "rev-parse", "-q", "--verify", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def use_local_dotnet():
    """Prefer the SDK that bootstrap installed into build/tools/dotnet, and keep .NET quiet."""
    exe = os.path.join(DOTNET_DIR, "dotnet.exe" if is_windows() else "dotnet")
    if os.path.isfile(exe):
        os.environ["DOTNET_ROOT"] = DOTNET_DIR
        os.environ["PATH"] = DOTNET_DIR + os.pathsep + os.environ["PATH"]
    os.environ["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    os.environ["DOTNET_NOLOGO"] = "1"


def dotnet_version():
    try:
        r = subprocess.run(["dotnet", "--version"], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""
    except OSError:
        return ""


def utility(*args):
    """OpenRA.Utility, the same command utility.sh and utility.cmd run."""
    env = dict(os.environ, ENGINE_DIR="..")
    return subprocess.run(["dotnet", os.path.join("bin", "OpenRA.Utility.dll"), *args], cwd=OPENRA_DIR, env=env, check=True, capture_output=True, text=True).stdout


def py(script, *args):
    subprocess.run([sys.executable, "-I", os.path.join(HERE, script), *args], check=True)


def link_mod():
    """Make build/mod/tgmc show up as OpenRA's mods/tgmc: a symlink, a junction on Windows, or a copy if neither is possible."""
    mods = os.path.join(OPENRA_DIR, "mods")
    os.makedirs(mods, exist_ok=True)
    link = os.path.join(mods, "tgmc")
    if os.path.islink(link):
        os.unlink(link)
    elif os.path.isdir(link):
        if is_windows() and subprocess.run(["cmd", "/c", "fsutil", "reparsepoint", "query", link], capture_output=True).returncode == 0:
            os.rmdir(link)  # a junction: remove the link, not what it points at
        else:
            shutil.rmtree(link)
    if is_windows():
        r = subprocess.run(["cmd", "/c", "mklink", "/J", link, MOD_OUT], capture_output=True, text=True)
        if r.returncode != 0:
            print("could not make a junction; copying the mod instead (run bootstrap or rebuild again after changing it)")
            shutil.copytree(MOD_OUT, link)
    else:
        os.symlink(MOD_OUT, link)
    print(f"linked {link} -> {MOD_OUT}")


def build_mod():
    """Assemble the mod into build/mod/tgmc (what mod/build_mod.sh does)."""
    py("lint_static.py")
    py("test_effects.py")
    shutil.rmtree(MOD_OUT, ignore_errors=True)
    os.makedirs(os.path.dirname(MOD_OUT), exist_ok=True)
    shutil.copytree(os.path.join(ROOT, "tgmc"), MOD_OUT, ignore=shutil.ignore_patterns("bin", "obj", "__pycache__"))

    # The mod's C# traits compile against the built engine, so the DLL is built only once OpenRA has bin/.
    if os.path.isdir(os.path.join(OPENRA_DIR, "bin")) and dotnet_version():
        dll_dir = os.path.join(BUILD, "tgmc-dll")
        subprocess.run(["dotnet", "build", os.path.join(ROOT, "tgmc", "code", "Tgmc.csproj"), "-c", "Release", "-o", dll_dir,
                        "-p:OPENRA_BIN=" + os.path.join(OPENRA_DIR, "bin"), "-nologo"], check=True)
        shutil.copy(os.path.join(dll_dir, "Tgmc.dll"), os.path.join(OPENRA_DIR, "bin", "Tgmc.dll"))

    py("build_sprites.py", "--tgmc", TGMC, "--out", MOD_OUT)
    py("build_sounds.py", "--tgmc", TGMC, "--out", os.path.join(MOD_OUT, "audio"))
    py("build_tileset.py", "--tgmc", TGMC, "--out", MOD_OUT)
    py("make_placeholders.py", "--tgmc", TGMC, "--out", MOD_OUT)
    py("make_chrome.py", "--out", MOD_OUT)
    link_mod()
    print("built", MOD_OUT)


def check_mod():
    """Lint the built mod with OpenRA's own checkers (what mod/check_mod.sh does)."""
    for args in (("--check-yaml",), ("--check-missing-sprites",)):
        out = utility("tgmc", *args)
        sys.stdout.write(out)
    maps = os.path.join(MOD_OUT, "maps")
    for name in sorted(os.listdir(maps)):
        full = os.path.join(maps, name)
        if os.path.isdir(full):
            sys.stdout.write(utility("tgmc", "--check-yaml", full))
    print("tgmc: checks passed")
