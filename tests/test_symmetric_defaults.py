import unittest
from system_profiles import default_for, BUTTONS_BY_SYSTEM

BASE = {'zones': {}, 'mapping': {}, 'shuffle_enabled': True}

class SymmetricDefaults(unittest.TestCase):
    def test_grid_cells_equal_and_occupied_symmetric(self):
        for system in BUTTONS_BY_SYSTEM:
            with self.subTest(system=system):
                zones = default_for(system, BASE)['zones']
                widths = {round(v[2]-v[0], 6) for v in zones.values()}
                heights = {round(v[3]-v[1], 6) for v in zones.values()}
                self.assertEqual(len(widths), 1)
                self.assertEqual(len(heights), 1)
                positions = {(round(v[0], 6), round(v[1], 6), round(v[2], 6), round(v[3], 6)) for v in zones.values()}
                for x1,y1,x2,y2 in positions:
                    self.assertIn((round(1-x2,6), y1, round(1-x1,6), y2), positions)

if __name__ == '__main__':
    unittest.main()
