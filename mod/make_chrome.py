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

# A glass look: dark navy panels with a thin blue edge and rounded corners (the names keep their old olive-drab meaning so the
# style table below still reads the same). Fills are a little see-through, so the map shows faintly through a panel.
SLATE = (20, 30, 44, 215)
OLIVE = (30, 46, 68, 235)
OLIVE_HI = (52, 86, 128, 245)
OLIVE_DARK = (14, 22, 34, 235)
AMBER = (79, 179, 255, 255)
AMBER_DIM = (60, 110, 170, 255)
RED = (150, 44, 44, 255)
GREY = (70, 72, 74, 255)
GREY_DIM = (48, 49, 50, 255)
# TGUI-style window tones: a darker body than SLATE, so cards and rails read as raised panels.
TGUI_BODY = (12, 18, 28, 222)
TGUI_RAIL = (10, 15, 24, 230)
TGUI_TAB = (24, 36, 54, 240)
TGUI_EDGE = (92, 150, 220, 150)
TGUI_TRACK = (8, 12, 18, 240)

# Collection name -> (fill, border). Names decide the state: hover, pressed, disabled, highlighted.
PANEL_COLLECTIONS = [
    "tgmc-panel", "tgmc-radar-frame", "tgmc-selection", "dialog", "dialog2", "dialog3", "dialog4",
    "dialog5", "mainmenu-border", "sidebar", "tooltip-separator", "separator", "newsbutton",
    "loadscreen-stripe", "textfield", "table", "scrollheader", "observer-scrollheader",
    "observer-scrollitem", "scrollpanel-bg", "slider-track",
    "tgui-window", "tgui-titlebar", "tgui-rail", "tgui-card", "tgui-card-header", "tgui-bar-track",
    "tgui-bar-fill",
    # The terminal main menu's own window and tab (the tgui-* ones above belong to the in-game HUD).
    "term-window", "term-titlebar",
    # States and panels the stock settings, music, lobby and observer widgets look up by name.
    "scrollitem", "scrollitem-nohover", "scrollitem-nohover-highlighted", "progressbar-bg", "progressbar-thumb",
    "panel-bg", "panel-header", "panel-rule", "panel-thinborder", "panel-thinborder-light",
    "textfield-hover", "textfield-focused", "textfield-disabled",
]
BUTTON_COLLECTIONS = [
    "button", "button-hover", "button-pressed", "button-disabled",
    "button-highlighted", "button-highlighted-hover", "button-highlighted-pressed",
    "button-highlighted-disabled",
    "sidebar-button", "sidebar-button-hover", "sidebar-button-pressed", "sidebar-button-disabled",
    "sidebar-button-highlighted", "sidebar-button-highlighted-hover", "sidebar-button-highlighted-pressed",
    "sidebar-button-highlighted-disabled",
    "scrollpanel-button", "scrollpanel-button-hover", "scrollpanel-button-pressed",
    "observer-scrollpanel-button-pressed", "slider-thumb",
    "checkbox-toggle", "checkbox-toggle-hover", "checkbox-toggle-pressed",
    "checkbox-toggle-highlighted", "checkbox-pressed", "checkbox-disabled",
    "tgui-tab", "tgui-tab-hover", "tgui-tab-pressed", "tgui-tab-disabled", "tgui-tab-active",
    "term-tab", "term-tab-hover", "term-tab-pressed", "term-tab-disabled", "term-tab-active",
    "scrollitem-hover", "scrollitem-pressed", "scrollitem-highlighted", "scrollheader-highlighted",
    "observer-scrollitem-hover", "observer-scrollitem-pressed", "observer-scrollitem-highlighted",
    "observer-scrollheader-highlighted", "observer-scrollpanel-button", "observer-scrollpanel-button-hover",
    "observer-scrollpanel-button-disabled", "scrollpanel-button-disabled",
    "slider-thumb-hover", "slider-thumb-pressed", "slider-thumb-disabled",
    "checkbox", "checkbox-hover", "checkbox-highlighted", "checkbox-highlighted-hover",
    "checkbox-highlighted-pressed", "checkbox-highlighted-disabled",
    "checkbox-toggle-highlighted-hover", "checkbox-toggle-highlighted-pressed",
    "button-highlighted-thin", "button-highlighted-thin-hover", "button-highlighted-thin-pressed",
    "button-highlighted-thin-disabled",
]


# The menus, lobby, settings and dialogs wear a green terminal look: near-black panels with square corners and a thin green edge. The in-game HUD
# (sidebar, tgmc-*, bars) keeps the blue glass above.
T_BODY = (5, 14, 8, 238)
T_BODY_HI = (14, 44, 24, 245)
T_BODY_DARK = (3, 9, 5, 240)
T_EDGE = (45, 138, 69, 255)
T_EDGE_HI = (125, 255, 154, 255)
T_EDGE_DIM = (30, 84, 46, 255)
T_OFF = (10, 18, 12, 235)
T_OFF_EDGE = (36, 56, 42, 255)
HUD_PREFIXES = ("sidebar", "tgmc-", "tgui-", "progressbar", "tooltip-separator", "separator")


def is_hud(name):
    return name.startswith(HUD_PREFIXES)


def term_style(name):
    """Fill and edge for a menu or dialog collection."""
    if "disabled" in name:
        return T_OFF, T_OFF_EDGE
    if name in ("term-window", "dialog", "dialog2", "dialog3", "dialog4", "dialog5", "panel-bg", "scrollpanel-bg", "mainmenu-border"):
        return T_BODY, T_EDGE
    if name in ("term-titlebar", "tgui-rail", "panel-header", "scrollheader", "tgui-card-header"):
        return T_BODY_DARK, T_EDGE_DIM
    if "highlighted" in name or name.endswith("active"):
        return T_BODY_HI, T_EDGE_HI
    if "pressed" in name:
        return T_BODY_DARK, T_EDGE
    if "hover" in name:
        return T_BODY_HI, T_EDGE_HI
    if name.startswith("textfield"):
        return T_BODY_DARK, T_EDGE
    return T_BODY, T_EDGE


# Soft glass (the translucent concept): white at low alpha over the map, a faint white edge, and an accent-blue state for
# highlighted buttons. Applies to the in-game HUD panels and sidebar buttons only.
GLASS_PANELS = ("tgui-window", "tgui-card", "tgui-card-header", "tgmc-radar-frame", "tgmc-selection")


def glass_style(name):
    if name.startswith("sidebar-button") or name.startswith("tgui-tab"):
        if "disabled" in name:
            return (255, 255, 255, 10), (255, 255, 255, 40)
        if "highlighted" in name or name.endswith("active"):
            return (79, 179, 255, 80), (150, 210, 255, 220)
        if "pressed" in name:
            return (255, 255, 255, 45), (255, 255, 255, 130)
        if "hover" in name:
            return (255, 255, 255, 62), (210, 235, 255, 170)
        return (255, 255, 255, 24), (255, 255, 255, 80)
    if name == "tgui-card-header":
        return (255, 255, 255, 34), (255, 255, 255, 90)
    if name == "tgmc-radar-frame":
        return (255, 255, 255, 18), (79, 179, 255, 150)
    return (255, 255, 255, 22), (255, 255, 255, 76)


def style_for(name):
    if name in GLASS_PANELS or name.startswith("sidebar-button") or name.startswith("tgui-tab"):
        return glass_style(name)
    if name == "progressbar-thumb":
        return (64, 196, 104, 255), (140, 235, 165, 255)
    if name == "progressbar-bg":
        return TGUI_TRACK, TGUI_EDGE
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


def flat_tile(fill):
    """A bar's track or fill: a plain block, so a bar only a few pixels high still reads as a bar."""
    return Image.new("RGBA", (TILE, TILE), fill)


def draw_tile(fill, border, square=False):
    """A rounded glass tile: a one pixel edge, a faint lighter line along the top, no heavy bevel. Terminal tiles (square) have sharp corners and no sheen."""
    img = Image.new("RGBA", (TILE, TILE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if square:
        d.rectangle([0, 0, TILE - 1, TILE - 1], fill=fill, outline=border, width=1)
        return img
    d.rounded_rectangle([0, 0, TILE - 1, TILE - 1], radius=CORNER - 1, fill=fill, outline=border, width=1)
    sheen = tuple(min(255, c + 22) for c in fill[:3]) + (min(255, fill[3] + 10),)
    d.line([(CORNER, 1), (TILE - CORNER - 1, 1)], fill=sheen)
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


# Icons the common chrome and widget code look up by collection and image name (mods/ra/chrome.yaml lists the same
# set). Each is (width, height, draw function); the glyphs are our own simple shapes, not TGMC art.
def _canvas(w, h):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _letter(d, w, h, ch, fill, size=11):
    font = ImageFont.load_default(size=size)
    box = d.textbbox((0, 0), ch, font=font)
    d.text(((w - (box[2] - box[0])) / 2 - box[0], (h - (box[3] - box[1])) / 2 - box[1]), ch, font=font, fill=fill)


def glyph_tile(name, w=16, h=16):
    """The old placeholder: a rounded tile with the name's first letter. -disabled is grey, -alert is amber."""
    img, d = _canvas(w, h)
    fill, outline, glyph = OLIVE, AMBER, AMBER
    if name.endswith("-disabled"):
        fill, outline, glyph = GREY_DIM, GREY, GREY
    elif name.endswith("-alert"):
        fill, outline, glyph = AMBER_DIM, AMBER, SLATE
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=3, fill=fill, outline=outline)
    _letter(d, w, h, name[0].upper(), glyph)
    return img


def tick(colour):
    img, d = _canvas(16, 16)
    d.line([(3, 8), (6, 12), (13, 3)], fill=colour, width=2)
    return img


def blank(w=16, h=16):
    return _canvas(w, h)[0]


def arrow(direction, colour):
    img, d = _canvas(16, 16)
    pts = {"up": [(8, 4), (3, 11), (13, 11)], "down": [(8, 12), (3, 5), (13, 5)],
           "left": [(4, 8), (11, 3), (11, 13)], "right": [(12, 8), (5, 3), (5, 13)]}[direction]
    d.polygon(pts, fill=colour)
    return img


def media(kind, colour=AMBER):
    img, d = _canvas(16, 16)
    tri = lambda x: [(x, 3), (x, 13), (x + 7, 8)]  # noqa: E731
    if kind == "play":
        d.polygon(tri(5), fill=colour)
    elif kind == "pause":
        d.rectangle([4, 3, 6, 12], fill=colour)
        d.rectangle([9, 3, 11, 12], fill=colour)
    elif kind == "stop":
        d.rectangle([4, 4, 11, 11], fill=colour)
    elif kind == "next":
        d.polygon(tri(3), fill=colour)
        d.rectangle([11, 3, 12, 12], fill=colour)
    elif kind == "prev":
        d.polygon([(12, 3), (12, 13), (5, 8)], fill=colour)
        d.rectangle([3, 3, 4, 12], fill=colour)
    elif kind == "fastforward":
        d.polygon(tri(1), fill=colour)
        d.polygon(tri(8), fill=colour)
    return img


def ring(w, h, outline, fill=None, width=2):
    img, d = _canvas(w, h)
    d.ellipse([1, 1, w - 2, h - 2], outline=outline, fill=fill, width=width)
    return img


def cross(w, h, colour):
    img, d = _canvas(w, h)
    d.line([(1, 1), (w - 2, h - 2)], fill=colour, width=2)
    d.line([(1, h - 2), (w - 2, 1)], fill=colour, width=2)
    return img


def padlock(colour):
    img, d = _canvas(12, 13)
    d.arc([3, 0, 8, 7], 180, 360, fill=colour, width=1)
    d.rectangle([1, 6, 10, 12], fill=colour)
    return img


def diamond(colour):
    img, d = _canvas(22, 22)
    d.polygon([(11, 1), (20, 11), (11, 20), (2, 11)], fill=colour, outline=SLATE)
    return img


def flag(letter, colour):
    img, d = _canvas(30, 15)
    d.rectangle([0, 0, 29, 14], fill=colour, outline=AMBER)
    _letter(d, 30, 15, letter, AMBER if colour != AMBER else SLATE, size=10)
    return img


def speaker_muted():
    img, d = _canvas(26, 24)
    d.polygon([(5, 9), (10, 9), (15, 4), (15, 20), (10, 15), (5, 15)], fill=GREY)
    d.line([(17, 8), (23, 16)], fill=RED, width=2)
    d.line([(17, 16), (23, 8)], fill=RED, width=2)
    return img


def tick_mark():
    img, d = _canvas(2, 4)
    d.rectangle([0, 0, 1, 3], fill=AMBER)
    return img


def vline(colour, h=19):
    img, d = _canvas(1, h)
    d.line([(0, 0), (0, h - 1)], fill=colour)
    return img


# Production tab pictograms, drawn at 16x16 in the sidebar's light ink. They are our own shapes, not TGMC art.
PARCHMENT = (226, 222, 196, 255)


def rifle(colour):
    img, d = _canvas(16, 16)
    d.polygon([(1, 6), (4, 6), (4, 11), (2, 11)], fill=colour)  # stock
    d.rectangle([4, 7, 13, 8], fill=colour)  # barrel
    d.rectangle([11, 5, 12, 6], fill=colour)  # sight
    d.polygon([(7, 9), (9, 9), (9, 13), (7, 13)], fill=colour)  # magazine
    return img


def claw(colour):
    img, d = _canvas(16, 16)
    for start, end in (((3, 2), (6, 13)), ((7, 2), (9, 14)), ((11, 3), (13, 12))):
        d.line([start, end], fill=colour, width=2)
    return img


def hammer(colour):
    img, d = _canvas(16, 16)
    d.line([(4, 14), (10, 7)], fill=colour, width=2)  # handle
    d.polygon([(7, 3), (13, 4), (12, 8), (6, 7)], fill=colour)  # head
    return img


def chevrons(colour):
    img, d = _canvas(16, 16)
    for y in (3, 8):
        d.line([(3, y + 5), (8, y), (13, y + 5)], fill=colour, width=2)
    return img


PICTOGRAMS = {"infantry": rifle, "xeno": claw, "build": hammer, "upgrade": chevrons}


def production_icon(name):
    """infantry/xeno/build in the light ink; -disabled is grey (the tab is locked), -alert amber (something is ready)."""
    base = name.split("-")[0]
    colour = PARCHMENT
    if name.endswith("-disabled"):
        colour = GREY
    elif name.endswith("-alert"):
        colour = AMBER
    return PICTOGRAMS[base](colour)


ICONS = {
    "checkmark-tick": {
        "checked": lambda: tick(AMBER), "checked-pressed": lambda: tick(AMBER_DIM),
        "unchecked": blank, "unchecked-pressed": lambda: tick(AMBER_DIM),
    },
    "checkmark-cross": {
        "checked": lambda: cross(11, 11, RED), "checked-pressed": lambda: cross(11, 11, AMBER_DIM),
        "unchecked": blank, "unchecked-pressed": lambda: cross(11, 11, AMBER_DIM),
    },
    "checkmark-mute": {
        "checked": speaker_muted, "checked-pressed": speaker_muted,
        "unchecked": blank, "unchecked-pressed": speaker_muted,
    },
    "editor": {n: (lambda n=n: glyph_tile(n)) for n in
               ["actors", "copy", "erase", "history", "overlays", "paste", "redo", "select", "tiles", "tools", "undo"]},
    "lobby-bits": {
        "admin": lambda: ring(6, 5, AMBER, width=1), "admin-registered": lambda: glyph_tile("admin"),
        "admin-anonymous": lambda: glyph_tile("admin-disabled"), "authentication": lambda: padlock(AMBER),
        "authentication-disabled": lambda: padlock(GREY), "bot": lambda: glyph_tile("bot"),
        "colorpicker": lambda: ring(22, 22, AMBER, width=2), "huepicker": lambda: _huepicker(),
        "kick": lambda: cross(11, 11, RED), "player-anonymous": lambda: glyph_tile("player-disabled"),
        "player-registered": lambda: glyph_tile("player"), "protected": lambda: padlock(AMBER),
        "protected-disabled": lambda: padlock(GREY), "spawn-claimed": lambda: ring(22, 22, AMBER, fill=OLIVE),
        "spawn-disabled": lambda: ring(22, 22, GREY, fill=GREY_DIM), "spawn-unclaimed": lambda: ring(22, 22, OLIVE_HI),
    },
    "music": {n: (lambda n=n: media(n)) for n in ["pause", "stop", "play", "next", "prev", "fastforward"]},
    "reload-icon": {"enabled": lambda: ring(16, 16, AMBER, width=2),
                    **{f"disabled-{i}": (lambda: ring(16, 16, GREY, width=2)) for i in range(12)}},
    "sidebar-bits": {
        "production-tooltip-cost": lambda: glyph_tile("cost"), "production-tooltip-power": lambda: glyph_tile("power"),
        "production-tooltip-time": lambda: glyph_tile("time"), "indicator-muted": speaker_muted,
    },
    "dropdown-decorations": {"marker": lambda: arrow("down", AMBER), "marker-disabled": lambda: arrow("down", GREY)},
    "dropdown-separators": {
        "separator": lambda: vline(OLIVE_HI), "separator-hover": lambda: vline(AMBER),
        "separator-pressed": lambda: vline(AMBER_DIM), "separator-disabled": lambda: vline(GREY),
        "observer-separator": lambda: vline(OLIVE),
    },
    "scrollpanel-decorations": {
        **{d: (lambda d=d: arrow(d, AMBER)) for d in ("up", "down", "left", "right")},
        **{f"{d}-disabled": (lambda d=d: arrow(d, GREY)) for d in ("up", "down", "left", "right")},
    },
    "slider": {"tick": tick_mark},
    "strategic": {"unowned": lambda: diamond(GREY), "critical_unowned": lambda: diamond(AMBER),
                  "enemy_owned": lambda: diamond(RED), "player_owned": lambda: diamond(OLIVE_HI)},
    "flags": {"marines": lambda: flag("M", OLIVE_DARK), "xenos": lambda: flag("X", (90, 30, 40, 255)), "som": lambda: flag("S", (150, 30, 30, 255)),
              "Random": lambda: flag("?", SLATE), "spectator": lambda: flag("O", SLATE)},
    "production-icons": {n: (lambda n=n: production_icon(n)) for n in
                         ["infantry", "infantry-disabled", "infantry-alert", "xeno", "xeno-disabled", "xeno-alert",
                          "build", "build-disabled", "build-alert", "upgrade", "upgrade-disabled", "upgrade-alert"]},
}

# The highlighted checkbox state looks up its own mark collection; it reuses the plain one.
for _mark in ("tick", "cross", "mute"):
    ICONS[f"checkmark-{_mark}-highlighted"] = ICONS[f"checkmark-{_mark}"]


def _huepicker():
    img, d = _canvas(7, 15)
    d.rectangle([0, 0, 6, 14], outline=AMBER)
    return img


def pack(images, width):
    """Shelf-pack (key, image) pairs into rows `width` wide; returns {key: (x, y)} and the height used."""
    placed, x, y, row_h = {}, 0, 0, 0
    for key, img in sorted(images, key=lambda kv: -kv[1].height):
        w, h = img.size
        if x + w > width:
            x, y, row_h = 0, y + row_h + 1, 0
        placed[key] = (x, y)
        x += w + 1
        row_h = max(row_h, h)
    return placed, y + row_h


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
    logo_y = rows * TILE
    icons = [((coll, name), draw()) for coll, items in ICONS.items() for name, draw in items.items()]
    icon_y = logo_y + LOGO + 1
    side = 1  # pad to a power of two: OpenGL texture uploads reject other sizes
    while True:
        placed, icon_h = pack(icons, side)
        if side >= COLS * TILE and icon_y + icon_h <= side:
            break
        side *= 2
    atlas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    lines = ["# Generated by mod/make_chrome.py. Do not edit."]
    for i, name in enumerate(names):
        x, y = (i % COLS) * TILE, (i // COLS) * TILE
        square = not is_hud(name)
        fill, border = term_style(name) if square else style_for(name)
        atlas.paste(flat_tile(fill) if name.startswith('progressbar') else draw_tile(fill, border, square), (x, y))
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
    for (coll, name), img in icons:
        x, y = placed[(coll, name)]
        atlas.paste(img, (x, icon_y + y))
    for coll, items in ICONS.items():
        lines.append(f"{coll}:")
        lines.append("\tImage: chrome.png")
        lines.append("\tRegions:")
        for name in items:
            x, y = placed[(coll, name)]
            w, h = next(img.size for (c, n), img in icons if (c, n) == (coll, name))
            lines.append(f"\t\t{name}: {x}, {icon_y + y}, {w}, {h}")

    os.makedirs(args.out, exist_ok=True)
    atlas.save(os.path.join(args.out, "chrome.png"))
    with open(os.path.join(args.out, "chrome.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"chrome: {len(names)} collections in {COLS}x{rows} atlas")


if __name__ == "__main__":
    main()
