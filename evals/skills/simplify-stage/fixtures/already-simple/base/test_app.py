import unittest

import app


class ArithmeticTests(unittest.TestCase):
    def test_total_and_mean(self):
        self.assertEqual(app.total([2, 4]), 6)
        self.assertEqual(app.mean([2, 4]), 3)


if __name__ == "__main__":
    unittest.main()
