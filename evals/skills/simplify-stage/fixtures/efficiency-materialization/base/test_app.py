import unittest

import app


class TotalTests(unittest.TestCase):
    def test_totals_only_positive_values(self):
        self.assertEqual(app.total_positive([-3, 2, 4]), 6)


if __name__ == "__main__":
    unittest.main()
