import unittest

import app


class NormalizeTests(unittest.TestCase):
    def test_normalizes_every_value(self):
        self.assertEqual(app.normalize_all([" A ", "B "]), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
