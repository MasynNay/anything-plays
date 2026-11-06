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

    def test_shuffle_snaps_into_same_grid_as_enabled_buttons(self):
        # Regression: the old Fit buttons implementation did not move Shuffle.
        for system in ('gb', 'gba', 'snes', 'genesis', 'n64', 'gamecube'):
            with self.subTest(system=system):
                p = default_for(system, BASE)
                p['zones']['Shuffle'] = [.173, .411, .327, .695]
                fit_to_grid(p, system)
                visible = enabled_zones(p, system) + ['Shuffle']
                cells = [tuple(p['zones'][name]) for name in visible]
                self.assertEqual(len(cells), len(set(cells)))
                widths = {round(x2 - x1, 8) for x1, _, x2, _ in cells}
                heights = {round(y2 - y1, 8) for _, y1, _, y2 in cells}
                self.assertEqual(len(widths), 1)
                self.assertEqual(len(heights), 1)
                for i, left in enumerate(cells):
                    for right in cells[i + 1:]:
                        intersection_width = max(0, min(left[2], right[2]) -
                                                 max(left[0], right[0]))
                        intersection_height = max(0, min(left[3], right[3]) -
                                                  max(left[1], right[1]))
                        self.assertLess(intersection_width * intersection_height,
                                        1e-10)

    def test_hidden_shuffle_retains_custom_rectangle(self):
        p = default_for('gba', BASE)
        custom_shuffle = [.17, .29, .45, .65]
        p['zones']['Shuffle'] = custom_shuffle[:]
        p['shuffle_enabled'] = False
        fit_to_grid(p, 'gba')
        self.assertEqual(p['zones']['Shuffle'], custom_shuffle)
        self.assertEqual(
            len({tuple(p['zones'][name]) for name in enabled_zones(p, 'gba')}),
            len(enabled_zones(p, 'gba')),
        )

    def test_grid_handles_only_shuffle_after_disabling_every_button(self):
        p = default_for('nes', BASE)
        for button in p['mapping']:
            p['mapping'][button] = DISABLED_MAPPING
        fit_to_grid(p, 'nes')
        self.assertEqual(p['zones']['Shuffle'], [1 / 3, 0, 2 / 3, 1])

    def test_all_disabled_does_not_crash(self):
        p = default_for('gb', BASE)
        for n in p['mapping']:
            p['mapping'][n] = DISABLED_MAPPING
        self.assertIs(fit_to_grid(p, 'gb'), p)

if __name__ == '__main__':
    unittest.main()
