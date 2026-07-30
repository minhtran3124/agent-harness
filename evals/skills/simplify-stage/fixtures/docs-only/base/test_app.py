import unittest

import app


class StatusTests(unittest.TestCase):
    def test_status(self):
        self.assertEqual(app.status(), "ready")


if __name__ == "__main__":
    unittest.main()
