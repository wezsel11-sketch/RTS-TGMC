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

from PIL import Image, ImageDraw

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
# TGUI-style window tones: a darker body than SLATE, so cards and rails read as raised panels.
TGUI_BODY = (24, 27, 30, 255)
TGUI_RAIL = (18, 21, 23, 255)
TGUI_TAB = (34, 40, 32, 255)
TGUI_EDGE = (60, 70, 52, 255)
TGUI_TRACK = (16, 18, 20, 255)

# Collection name -> (fill, border). Names decide the state: hover, pressed, disabled, highlighted.
PANEL_COLLECTIONS = [
    "tgmc-panel", "tgmc-radar-frame", "tgmc-selection", "dialog", "dialog2", "dialog3", "dialog4",
    "dialog5", "mainmenu-border", "sidebar", "tooltip-separator", "separator", "newsbutton",
    "loadscreen-stripe", "textfield", "table", "scrollheader", "observer-scrollheader",
    "observer-scrollitem", "scrollpanel-bg", "slider-track",
    "tgui-window", "tgui-titlebar", "tgui-rail", "tgui-card", "tgui-card-header", "tgui-bar-track",
    "tgui-bar-fill",
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
    "tgui-tab", "tgui-tab-hover", "tgui-tab-pressed", "tgui-tab-disabled", "tgui-tab-active",
]


def style_for(name):
    if name == "tgui-window":
        return TGUI_BODY, TGUI_EDGE
    if name == "tgui-titlebar":
        return OLIVE_DARK, AMBER_DIM
    if name == "tgui-rail":
        return TGUI_RAIL, OLIVE_DARK
    if name in ("tgui-card", "tgui-card-header"):
        return (OLIVE_DARK if name == "tgui-card-header" else SLATE), OLIVE
    if name == "tgui-bar-track":
        return TGUI_TRACK, GREY
    if name == "tgui-bar-fill":
        return OLIVE_HI, OLIVE_HI
    if name == "tgui-tab":
        return TGUI_TAB, TGUI_EDGE
    if name == "tgui-tab-hover":
        return OLIVE, OLIVE_HI
    if name == "tgui-tab-pressed":
        return OLIVE_DARK, AMBER_DIM
    if name == "tgui-tab-disabled":
        return GREY_DIM, GREY
    if name == "tgui-tab-active":
        return OLIVE, AMBER
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
    atlas = Image.new("RGBA", (COLS * TILE, rows * TILE), (0, 0, 0, 0))
    lines = ["# Generated by mod/make_chrome.py. Do not edit."]
    for i, name in enumerate(names):
        x, y = (i % COLS) * TILE, (i // COLS) * TILE
        fill, border = style_for(name)
        atlas.paste(draw_tile(fill, border), (x, y))
        lines.append(f"{name}:")
        lines.append("\tImage: chrome.png")
        lines.append(f"\tPanelRegion: {x}, {y}, {CORNER}, {CORNER}, {CENTRE}, {CENTRE}, {CORNER}, {CORNER}")

    os.makedirs(args.out, exist_ok=True)
    atlas.save(os.path.join(args.out, "chrome.png"))
    with open(os.path.join(args.out, "chrome.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"chrome: {len(names)} collections in {COLS}x{rows} atlas")


if __name__ == "__main__":
    main()
