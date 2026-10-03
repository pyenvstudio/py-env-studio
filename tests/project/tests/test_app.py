import unittest

import app


class AppTests(unittest.TestCase):
    def test_returns_dependency_value(self) -> None:
        self.assertEqual(app.get_value(), "available")
