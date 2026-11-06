"""Plain and JSON IPC replies must agree on whether a real error exists."""
import unittest
from support import configure_imports
configure_imports()
from hyprland_errors import parse_config_errors


class ConfigErrorsTests(unittest.TestCase):
    def test_empty_or_whitespace_plain_and_json_replies(self):
        for text in ('', '\n', '   \n', '[]', '[""]', '["", "\\n", "  "]', 'null', '{}', '""'):
            with self.subTest(stdout=text):
                self.assertEqual(parse_config_errors(text), [])

    def test_nonempty_errors_are_preserved_in_both_formats(self):
        for text in ('Config error ...\n', '["", "Config error ...", "   "]', '"Config error ..."'):
            with self.subTest(stdout=text):
                self.assertEqual(parse_config_errors(text), ['Config error ...'])

    def test_multiple_errors_and_unexpected_nonempty_json_are_not_hidden(self):
        self.assertEqual(parse_config_errors('First error\n\nSecond error\n'), ['First error', 'Second error'])
        self.assertTrue(parse_config_errors('{"error": "Config error"}'))
