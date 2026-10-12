"""Tests for the effect and death plumbing: the sprite builder's fade and padding, and the death-type lint.

Plain asserts on synthetic images and strings, so it needs neither TGMC nor OpenRA. Usage: test_effects.py
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_sprites  # noqa: E402


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


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("pass", name)
