import unittest

import app


class FormatterTests(unittest.TestCase):
    def test_formats_users_and_owners(self):
        self.assertEqual(app.format_user(" ada lovelace "), "Ada Lovelace")
        self.assertEqual(app.format_owner(" grace hopper "), "Grace Hopper")


if __name__ == "__main__":
    unittest.main()
