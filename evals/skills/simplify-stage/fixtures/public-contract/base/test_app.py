import inspect
import unittest

import app


class FetchContractTests(unittest.TestCase):
    def test_keeps_keyword_only_timeout_contract(self):
        signature = inspect.signature(app.fetch)
        self.assertEqual(str(signature), "(resource, *, timeout=30)")
        self.assertEqual(
            app.fetch("users", timeout=5),
            {"resource": "users", "timeout": 5},
        )


if __name__ == "__main__":
    unittest.main()
