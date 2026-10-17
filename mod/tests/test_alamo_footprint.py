import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import alamo_footprint  # noqa: E402

ALAMO = os.path.join(os.path.dirname(__file__), "..", "..", "build", "terragov-marine-corps", "_maps", "shuttles", "alamo.dmm")


class AlamoFootprint(unittest.TestCase):
    def test_footprint_is_eleven_wide_and_twenty_one_tall(self):
        cells = alamo_footprint.footprint(ALAMO)
        self.assertEqual(max(x for x, _ in cells) + 1, 11)
        self.assertEqual(max(y for _, y in cells) + 1, 21)

    def test_footprint_has_thirty_nine_cells(self):
        self.assertEqual(len(alamo_footprint.footprint(ALAMO)), 39)

    def test_hatch_is_on_the_footprint_at_one_nine(self):
        cells = set(alamo_footprint.footprint(ALAMO))
        self.assertEqual(alamo_footprint.hatch(ALAMO), (1, 9))
        self.assertIn((1, 9), cells)


if __name__ == "__main__":
    unittest.main()
