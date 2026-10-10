"""Read BYOND .dmi icon files: per-state metadata and frame slicing.

A .dmi is a PNG whose zTXt "Description" chunk holds the icon metadata: the
icon size and, for each state, its dir count and frame count. Icons are packed
state by state, then frame by frame, then direction by direction, laid out
row-major in a grid that is (sheet width / icon width) columns wide.

Direction order inside a state is BYOND's: S, N, E, W for a 4-dir state.
Adapted from the extractor in the Aliens-vs-Predators Doom mod.
"""
import re
import struct
import zlib

from PIL import Image

# BYOND direction ids in packing order for a 4-dir state (SOUTH=2, NORTH=1, EAST=4, WEST=8).
DIRS4 = ["S", "N", "E", "W"]


def read_description(path):
    with open(path, "rb") as f:
        data = f.read()
    i = 8
    while i < len(data):
        (n,) = struct.unpack(">I", data[i:i + 4])
        kind = data[i + 4:i + 8]
        body = data[i + 8:i + 8 + n]
        if kind == b"zTXt":
            key, _, rest = body.partition(b"\0")
            if key == b"Description":
                return zlib.decompress(rest[1:]).decode("utf-8", errors="replace")
        i += 12 + n
    return None


def parse_meta(text):
    """Return (icon_width, icon_height, states) where each state is {name, dirs, frames, first}.

    `first` is the index of the state's first icon in the packed sheet.
    """
    width = height = None
    states = []
    cur = None
    index = 0
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("width"):
            width = int(line.split("=")[1])
        elif line.startswith("height"):
            height = int(line.split("=")[1])
        elif line.startswith("state"):
            if cur is not None:
                index += cur["dirs"] * cur["frames"]
            name = re.search(r'"(.*)"', line).group(1)
            cur = {"name": name, "dirs": 1, "frames": 1, "first": index}
            states.append(cur)
        elif cur is not None and line.startswith("dirs"):
            cur["dirs"] = int(line.split("=")[1])
        elif cur is not None and line.startswith("frames"):
            cur["frames"] = int(line.split("=")[1])
    return width or 32, height or 32, states


class Dmi:
    """A loaded .dmi. `frames(state)` returns frames[f][d] as RGBA images, d in BYOND 4-dir order when dirs == 4."""

    def __init__(self, path):
        text = read_description(path)
        if text is None:
            raise ValueError(f"{path}: no DMI metadata")
        self.path = path
        self.icon_w, self.icon_h, self.states = parse_meta(text)
        self.sheet = Image.open(path).convert("RGBA")
        self.cols = self.sheet.width // self.icon_w
        # BYOND uses the first state with a given name. Some TGMC castes (hunter) repeat a name.
        self._by_name = {}
        for s in self.states:
            self._by_name.setdefault(s["name"], s)

    def has_state(self, name):
        return name in self._by_name

    def state(self, name):
        if name not in self._by_name:
            raise KeyError(f"{self.path}: no state {name!r}")
        return self._by_name[name]

    def frames(self, name):
        s = self.state(name)
        out = []
        for f in range(s["frames"]):
            row = []
            for d in range(s["dirs"]):
                index = s["first"] + f * s["dirs"] + d
                x = (index % self.cols) * self.icon_w
                y = (index // self.cols) * self.icon_h
                row.append(self.sheet.crop((x, y, x + self.icon_w, y + self.icon_h)))
            out.append(row)
        return out
