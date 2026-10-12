"""Tests for the effect and death plumbing: the sprite builder's fade and padding, and the death-type lint.

Plain asserts on synthetic images and strings, so it needs neither TGMC nor OpenRA. Usage: test_effects.py
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_sprites  # noqa: E402
import lint_static  # noqa: E402

# Rule text uses tab indentation, like the real files.
RULES = (
    "^Unit:\n\tHealth:\n\t\tHP: 1\n"
    "^Xeno:\n\tInherits: ^Unit\n\tWithDeathAnimation:\n\t\tDeathSequence: die\n\t\tDeathTypes:\n\t\t\tExplosionDeath: -gib\n"
    "runner:\n\tInherits: ^Xeno\n\tHealth:\n\t\tHP: 2\n"
)
BOOM = "TGMCBoom:\n\tRange: 6c0\n\tWarhead@1Dam: SpreadDamage\n\t\tDamageTypes: ExplosionDeath\n"


def test_fade_frames_alpha():
    out = build_sprites.fade_frames(Image.new("RGBA", (4, 4), (255, 0, 0, 200)), 4)
    assert [f.getpixel((0, 0))[3] for f in out] == [200, 150, 100, 50]


def test_pad_to_centres():
    out = build_sprites.pad_to(Image.new("RGBA", (32, 32), (255, 0, 0, 255)), (64, 64))
    assert out.size == (64, 64)
    assert out.getpixel((16, 16))[3] == 255 and out.getpixel((47, 47))[3] == 255
    assert out.getpixel((15, 15))[3] == 0 and out.getpixel((48, 48))[3] == 0


def test_pad_to_rejects_larger():
    try:
        build_sprites.pad_to(Image.new("RGBA", (32, 32)), (16, 16))
    except SystemExit:
        return
    raise AssertionError("pad_to accepted an image bigger than the cell")


def test_death_types_clean():
    assert lint_static.check_death_types(RULES, BOOM, {"runner": {"die", "die-gib"}}) == []


def test_death_types_missing_sequence():
    errors = lint_static.check_death_types(RULES, BOOM, {"runner": {"die"}})
    assert len(errors) == 1 and "runner" in errors[0] and "die-gib" in errors[0]


def test_death_types_see_past_a_comment_line():
    # A comment at column 0 inside a block is valid MiniYaml and must not end the block
    commented = RULES.replace("\tInherits: ^Unit\n", "\tInherits: ^Unit\n# a comment\n\n")
    errors = lint_static.check_death_types(commented, BOOM, {"runner": {"die"}})
    assert len(errors) == 1 and "die-gib" in errors[0]


def test_death_types_unlisted_damage_type():
    fire = BOOM.replace("ExplosionDeath", "FireDeath")
    errors = lint_static.check_death_types(RULES, fire, {"runner": {"die", "die-gib"}})
    assert len(errors) == 1 and "FireDeath" in errors[0]


def test_only_grenade_tags_explosions():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tgmc", "rules", "weapons.yaml")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    # A blank line separates weapons; comments above one belong to its block, so keep only the name line
    names = set()
    for block in text.split("\n\n"):
        if "DamageTypes:" in block:
            names |= {line.split(":")[0] for line in block.splitlines() if line and line[0].isalpha()}
    assert names == {"TGMCGrenade"}, names


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("pass", name)
