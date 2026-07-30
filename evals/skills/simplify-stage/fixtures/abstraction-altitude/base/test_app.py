import unittest

import app


class GreetingTests(unittest.TestCase):
    def test_greets_by_name(self):
        self.assertEqual(app.greeting("Ada"), "Hello, Ada!")


if __name__ == "__main__":
    unittest.main()
