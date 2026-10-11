"""Generate the TGMC-styled UI chrome: one atlas PNG and the chrome.yaml that names its collections.

Every collection is a 24x24 nine-slice tile, so widgets can stretch it to any size. Colours are
our own, picked to suggest a dark TGMC-style HUD: olive-drab and slate panels with amber highlights.
Nothing here is TGMC art.

Outputs in --out:
  chrome.png     atlas, TILE x TILE cells, COLS cells per row
  chrome.yaml    OpenRA chrome collections, each with PanelRegion pointing into chrome.png

Usage: make_chrome.py --out DIR
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

TILE = 24
CORNER = 6    # corner and edge width of the nine-slice
CENTRE = 12   # centre width and height: CORNER + CENTRE + CORNER == TILE
COLS = 8

SLATE = (30, 35, 40, 255)
OLIVE = (76, 92, 64, 255)
OLIVE_HI = (116, 136, 92, 255)
OLIVE_DARK = (42, 52, 38, 255)
AMBER = (209, 154, 43, 255)
AMBER_DIM = (140, 100, 30, 255)
RED = (150, 44, 44, 255)
GREY = (70, 72, 74, 255)
GREY_DIM = (48, 49, 50, 255)

# Collection name -> (fill, border). Names decide the state: hover, pressed, disabled, highlighted.
PANEL_COLLECTIONS = [
    "tgmc-panel", "tgmc-radar-frame", "tgmc-selection", "dialog", "dialog2", "dialog3", "dialog4",
    "dialog5", "mainmenu-border", "sidebar", "tooltip-separator", "separator", "newsbutton",
    "loadscreen-stripe", "textfield", "table", "scrollheader", "observer-scrollheader",
    "observer-scrollitem", "scrollpanel-bg", "slider-track", "observer-scrollpanel-button", "progressbar-bg",
]
BUTTON_COLLECTIONS = [
    "button", "button-hover", "button-pressed", "button-disabled",
    "button-highlighted", "button-highlighted-hover", "button-highlighted-pressed",
    "button-highlighted-disabled",
    "sidebar-button", "sidebar-button-hover", "sidebar-button-pressed", "sidebar-button-disabled",
    "scrollpanel-button", "scrollpanel-button-hover", "scrollpanel-button-pressed",
    "observer-scrollpanel-button-pressed", "slider-thumb",
    "checkbox-toggle", "checkbox-toggle-hover", "checkbox-toggle-pressed",
    "checkbox-toggle-highlighted", "checkbox-pressed", "checkbox-disabled",
]


def style_for(name):
    if name in ("slider-thumb",):
        return OLIVE_HI, AMBER
    if "disabled" in name:
        return GREY_DIM, GREY
    if "highlighted" in name or name.startswith("checkbox-toggle-highlighted"):
        return OLIVE, AMBER
    if "pressed" in name:
        return OLIVE_DARK, AMBER_DIM
    if "hover" in name:
        return OLIVE_HI, OLIVE_HI
    if name.startswith("button") or name.startswith("sidebar-button") or name.startswith("scrollpanel-button") \
            or name.startswith("observer-scrollpanel") or name.startswith("checkbox"):
        return OLIVE, OLIVE_HI
    if name == "tgmc-radar-frame":
        return SLATE, AMBER
    if name == "loadscreen-stripe":
        return OLIVE_DARK, OLIVE_HI
    if name in ("separator", "tooltip-separator"):
        return OLIVE_DARK, OLIVE
    if name in ("mainmenu-border", "newsbutton"):
        return SLATE, OLIVE_HI
    return SLATE, OLIVE


def draw_tile(fill, border):
    img = Image.new("RGBA", (TILE, TILE), fill)
    d = ImageDraw.Draw(img)
    # Two-pixel outer border, a one-pixel bevel highlight on top and left, and a shadow on bottom and right.
    d.rectangle([0, 0, TILE - 1, TILE - 1], outline=border, width=2)
    d.line([(2, 2), (TILE - 3, 2)], fill=tuple(min(255, c + 25) for c in fill[:3]) + (255,))
    d.line([(2, 2), (2, TILE - 3)], fill=tuple(min(255, c + 25) for c in fill[:3]) + (255,))
    d.line([(2, TILE - 3), (TILE - 3, TILE - 3)], fill=tuple(max(0, c - 20) for c in fill[:3]) + (255,))
    d.line([(TILE - 3, 2), (TILE - 3, TILE - 3)], fill=tuple(max(0, c - 20) for c in fill[:3]) + (255,))
    return img


LOGO = 128  # square logo region, placed under the tile grid


def draw_logo():
    """A TGMC-style emblem: amber ring, olive disc, and the word TGMC. Our own drawing, not TGMC art."""
    img = Image.new("RGBA", (LOGO, LOGO), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, LOGO - 3, LOGO - 3], fill=AMBER)
    d.ellipse([10, 10, LOGO - 11, LOGO - 11], fill=OLIVE_DARK)
    d.ellipse([18, 18, LOGO - 19, LOGO - 19], outline=OLIVE_HI, width=2)
    font = ImageFont.load_default(size=26)
    box = d.textbbox((0, 0), "TGMC", font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((LOGO - w) / 2 - box[0], (LOGO - h) / 2 - box[1]), "TGMC", font=font, fill=AMBER)
    return img


# Icon sheets the common chrome reads by name (see mods/common/chrome/*.yaml). Placeholder glyphs, not TGMC art.
ICON_COLLECTIONS = {
    "checkmark-tick": ["checked", "checked-pressed", "unchecked", "unchecked-pressed"],
    "checkmark-cross": ["checked", "checked-pressed", "unchecked", "unchecked-pressed"],
    "checkmark-mute": ["checked", "checked-pressed", "unchecked", "unchecked-pressed"],
    "editor": ["actors", "copy", "erase", "history", "overlays", "paste", "redo", "select", "tiles", "tools", "undo"],
    "lobby-bits": [
        "admin", "admin-anonymous", "admin-registered", "player-anonymous", "player-registered", "kick", "bot",
        "spawn-unclaimed", "spawn-claimed", "spawn-disabled", "colorpicker", "huepicker",
        "protected", "protected-disabled", "authentication", "authentication-disabled",
    ],
    "flags": ["marines", "xenos", "Random"],
    "music": ["next", "pause", "play", "prev", "stop", "fastforward"],
    "reload-icon": ["enabled"] + [f"disabled-{i}" for i in range(12)],
    "sidebar-bits": ["production-tooltip-cost", "production-tooltip-power", "production-tooltip-time", "indicator-muted"],
    "dropdown-decorations": ["marker", "marker-disabled"],
    "dropdown-separators": ["separator", "separator-hover", "separator-pressed", "separator-disabled", "observer-separator"],
    "scrollpanel-decorations": ["up", "up-disabled", "down", "down-disabled", "left", "left-disabled", "right", "right-disabled"],
    "slider": ["tick"],
    "strategic": ["critical_unowned", "enemy_owned", "player_owned"],
}
ICON = 16
ICON_COLS = 16


def draw_icon(name):
    """A 16x16 amber tile with the name's first letter in it."""
    img = Image.new("RGBA", (ICON, ICON), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, ICON - 1, ICON - 1], radius=3, fill=OLIVE, outline=AMBER)
    font = ImageFont.load_default(size=11)
    ch = name[0].upper()
    box = d.textbbox((0, 0), ch, font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((ICON - w) / 2 - box[0], (ICON - h) / 2 - box[1]), ch, font=font, fill=AMBER)
    return img


def all_collections():
    names = PANEL_COLLECTIONS + BUTTON_COLLECTIONS
    seen = set()
    for n in names:
        if n in seen:
            raise SystemExit(f"duplicate chrome collection {n}")
        seen.add(n)
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    names = all_collections()
    rows = (len(names) + COLS - 1) // COLS
    # Pad to a power of two: OpenGL texture uploads reject other sizes.
    logo_y = rows * TILE
    icon_names = [(c, n) for c, names in ICON_COLLECTIONS.items() for n in names]
    icon_y = logo_y + LOGO
    icon_rows = (len(icon_names) + ICON_COLS - 1) // ICON_COLS
    side = 1
    while side < max(COLS * TILE, icon_y + icon_rows * ICON):
        side *= 2
    atlas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    lines = ["# Generated by mod/make_chrome.py. Do not edit."]
    for i, name in enumerate(names):
        x, y = (i % COLS) * TILE, (i // COLS) * TILE
        fill, border = style_for(name)
        atlas.paste(draw_tile(fill, border), (x, y))
        lines.append(f"{name}:")
        lines.append("\tImage: chrome.png")
        lines.append(f"\tPanelRegion: {x}, {y}, {CORNER}, {CORNER}, {CENTRE}, {CENTRE}, {CORNER}, {CORNER}")

    atlas.paste(draw_logo(), (0, logo_y))
    lines += [
        "logos:",
        "\tImage: chrome.png",
        "\tRegions:",
        f"\t\tlogo: 0, {logo_y}, {LOGO}, {LOGO}",
    ]
    for i, (coll, name) in enumerate(icon_names):
        atlas.paste(draw_icon(name), ((i % ICON_COLS) * ICON, icon_y + (i // ICON_COLS) * ICON))
    for coll in ICON_COLLECTIONS:
        lines.append(f"{coll}:")
        lines.append("\tImage: chrome.png")
        lines.append("\tRegions:")
        for i, (c, name) in enumerate(icon_names):
            if c == coll:
                lines.append(f"\t\t{name}: {(i % ICON_COLS) * ICON}, {icon_y + (i // ICON_COLS) * ICON}, {ICON}, {ICON}")

    os.makedirs(args.out, exist_ok=True)
    atlas.save(os.path.join(args.out, "chrome.png"))
    with open(os.path.join(args.out, "chrome.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"chrome: {len(names)} collections in {COLS}x{rows} atlas")


if __name__ == "__main__":
    main()
