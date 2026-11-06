import tempfile
import unittest
from pathlib import Path
from anything_plays.system_profiles import ProfileStore, default_for, normalize, BUTTONS_BY_SYSTEM

BASE = {'zones': {'A': [0, 0, .3, .3]}, 'mapping': {'A': 'A'}, 'zone_font_size': 44}

class SystemProfilesTests(unittest.TestCase):
    def test_button_sets(self):
        self.assertNotIn('X', BUTTONS_BY_SYSTEM['gb'])
        self.assertIn('X', BUTTONS_BY_SYSTEM['snes'])
        self.assertIn('L', BUTTONS_BY_SYSTEM['gba'])
    def test_independent_profiles_persist(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'profiles.json'
            store = ProfileStore(p, BASE)
            gb = store.get('gb')
            gb['zones']['A'] = [.1, .2, .3, .4]
            store.put('gb', gb)
            self.assertNotEqual(store.get('gba')['zones']['A'], gb['zones']['A'])
            self.assertEqual(ProfileStore(p, BASE).get('gb')['zones']['A'], [.1, .2, .3, .4])
    def test_legacy_upgrade(self):
        old = {'zones': {'A': [.2, .2, .6, .6]}, 'mapping': {'A': 'B'}}
        new = normalize('snes', old, BASE)
        self.assertEqual(new['zones']['A'], [.2, .2, .6, .6])
        self.assertIn('X', new['zones'])
        self.assertEqual(new['mapping']['A'], 'B')
    def test_invalid_rectangle_replaced(self):
        cfg = normalize('gb', {'zones': {'A': [4, 0, 5, 1]}}, BASE)
        self.assertNotEqual(cfg['zones']['A'], [4, 0, 5, 1])

if __name__ == '__main__':
    unittest.main()
