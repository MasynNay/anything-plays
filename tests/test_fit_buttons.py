import copy
import unittest
from anything_plays.system_profiles import default_for, normalize, fit_to_grid, enabled_zones, DISABLED_MAPPING

BASE = {'zones': {}, 'mapping': {}}

class FitButtonTests(unittest.TestCase):
    def test_disabled_mapping_survives_normalization(self):
        p = default_for('gba', BASE)
        p['mapping']['L'] = DISABLED_MAPPING
        self.assertEqual(normalize('gba', p, BASE)['mapping']['L'], DISABLED_MAPPING)

    def test_grid_excludes_disabled_and_preserves_disabled_rectangles(self):
        p = default_for('gba', BASE)
        old_l = copy.deepcopy(p['zones']['L'])
        p['mapping']['L'] = DISABLED_MAPPING
        p['mapping']['R'] = DISABLED_MAPPING
        fit_to_grid(p, 'gba')
        self.assertEqual(p['zones']['L'], old_l)
        self.assertEqual(len(enabled_zones(p, 'gba')), 8)
        rectangles = [p['zones'][n] for n in enabled_zones(p, 'gba')]
        self.assertEqual(len({tuple(r) for r in rectangles}), 8)
        widths = [round(r[2]-r[0], 8) for r in rectangles]
        heights = [round(r[3]-r[1], 8) for r in rectangles]
        self.assertEqual(len(set(widths)), 1)
        self.assertEqual(len(set(heights)), 1)

    def test_all_disabled_does_not_crash(self):
        p = default_for('gb', BASE)
        for n in p['mapping']:
            p['mapping'][n] = DISABLED_MAPPING
        self.assertIs(fit_to_grid(p, 'gb'), p)

if __name__ == '__main__':
    unittest.main()
