import unittest

import app


class SquareTests(unittest.TestCase):
    def test_rejects_negative_values(self):
        with self.assertRaisesRegex(ValueError, "negative values are forbidden"):
            app.square(-1)

    def test_squares_positive_values(self):
        self.assertEqual(app.square(4), 16)


if __name__ == "__main__":
    unittest.main()
