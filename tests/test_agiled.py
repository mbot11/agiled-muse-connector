"""Offline smoke tests for the Agiled connector client.

No network access and no credentials are required: these tests exercise
path validation, parameter/body parsing, brand resolution/validation,
the standalone credential URL builder, the placeholder-brand guard, and
the healthcheck's response-shape strictness.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""

import importlib.util
import os
import pathlib
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BIN = ROOT / "custom.agiled-api" / "bin"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, BIN / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


agiled = load("agiled", "agiled.py")
healthcheck = load("agiled_healthcheck", "healthcheck.py")


class TestNormalizePath(unittest.TestCase):
    def test_plain_and_relative_paths(self):
        self.assertEqual(agiled.normalize_path("/contacts"), "/contacts")
        self.assertEqual(agiled.normalize_path("contacts"), "/contacts")
        self.assertEqual(agiled.normalize_path("/projects/123"), "/projects/123")

    def test_traversal_refused_raw_and_encoded(self):
        for bad in ("/../developers", "/a/../b", "/%2e%2e/developers", "/.."):
            with self.assertRaises(agiled.AgiledError, msg=bad):
                agiled.normalize_path(bad)

    def test_host_query_fragment_space_refused(self):
        for bad in ("//evil.example/x", "https://evil.example/x",
                    "/contacts?page=2", "/contacts#frag", "/a b", "/a\tb"):
            with self.assertRaises(agiled.AgiledError, msg=bad):
                agiled.normalize_path(bad)

    def test_empty_and_root_refused(self):
        for bad in ("", "/", "   "):
            with self.assertRaises(agiled.AgiledError, msg=repr(bad)):
                agiled.normalize_path(bad)


class TestParseParams(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(agiled.parse_params(["page=2", "q=a b"]),
                         {"page": "2", "q": "a b"})

    def test_missing_equals_is_an_error(self):
        with self.assertRaises(agiled.AgiledError):
            agiled.parse_params(["page2"])


class TestLoadBody(unittest.TestCase):
    def args(self, json_body=None, body_file=None):
        return types.SimpleNamespace(json_body=json_body, body_file=body_file)

    def test_object_ok(self):
        self.assertEqual(agiled.load_body(self.args('{"a": 1}')), {"a": 1})

    def test_no_body_ok(self):
        self.assertIsNone(agiled.load_body(self.args()))

    def test_both_options_refused(self):
        with self.assertRaises(agiled.AgiledError):
            agiled.load_body(self.args("{}", "x.json"))

    def test_empty_and_malformed_refused(self):
        for bad in ("", "  ", "{not json"):
            with self.assertRaises(agiled.AgiledError, msg=repr(bad)):
                agiled.load_body(self.args(bad))

    def test_non_object_refused(self):
        for bad in ("[1, 2]", '"text"', "42"):
            with self.assertRaises(agiled.AgiledError, msg=bad):
                agiled.load_body(self.args(bad))

    def test_missing_file_refused(self):
        with self.assertRaises(agiled.AgiledError):
            agiled.load_body(self.args(None, "/nonexistent/definitely-missing.json"))


class TestBrand(unittest.TestCase):
    def test_valid_hosts(self):
        for good in ("your-workspace.agiled.app", "acme.agiled.app"):
            self.assertEqual(agiled.validate_brand(good), good)

    def test_invalid_brands(self):
        for bad in ("", "acme", "bad brand", "a\r\nb.com", "http://x.com"):
            with self.assertRaises(agiled.AgiledError, msg=repr(bad)):
                agiled.validate_brand(bad)

    def test_resolution_precedence(self):
        old = os.environ.pop("AGILED_BRAND", None)
        try:
            self.assertEqual(agiled.resolve_brand(None), agiled.DEFAULT_BRAND)
            os.environ["AGILED_BRAND"] = "env.agiled.app"
            self.assertEqual(agiled.resolve_brand(None), "env.agiled.app")
            self.assertEqual(agiled.resolve_brand("flag.agiled.app"), "flag.agiled.app")
        finally:
            os.environ.pop("AGILED_BRAND", None)
            if old is not None:
                os.environ["AGILED_BRAND"] = old


class TestPlaceholderGuard(unittest.TestCase):
    def test_unconfigured_client_sends_nothing(self):
        old = os.environ.pop("AGILED_BRAND", None)
        try:
            with self.assertRaises(agiled.AgiledError) as ctx:
                agiled.call("GET", "/users")
            self.assertEqual(ctx.exception.code, "config")
        finally:
            if old is not None:
                os.environ["AGILED_BRAND"] = old


class TestBuildUrlFallback(unittest.TestCase):
    def setUp(self):
        self._surrogate = agiled._HAVE_SURROGATE
        agiled._HAVE_SURROGATE = False
        os.environ.pop("AGILED_API_TOKEN", None)

    def tearDown(self):
        agiled._HAVE_SURROGATE = self._surrogate
        os.environ.pop("AGILED_API_TOKEN", None)

    def test_no_credential_is_a_clean_config_error(self):
        with self.assertRaises(agiled.AgiledError) as ctx:
            agiled.build_url("/users", {})
        self.assertEqual(ctx.exception.code, "config")

    def test_env_token_appended_and_caller_token_stripped(self):
        os.environ["AGILED_API_TOKEN"] = "dummy-token-for-tests"
        url = agiled.build_url("/contacts", {"api_token": "caller-value", "page": "2"})
        self.assertTrue(url.startswith("https://my.agiled.app/api/v1/contacts"))
        self.assertIn("page=2", url)
        self.assertIn("api_token=dummy-token-for-tests", url)
        self.assertNotIn("caller-value", url)


class _FakeMod:
    def __init__(self, result):
        self._result = result

    def call(self, method, path):
        return self._result


class TestHealthcheckShapes(unittest.TestCase):
    def test_list_and_envelope_counts(self):
        self.assertEqual(healthcheck.count_of(_FakeMod({"data": [1, 2, 3]}), "/x"), 3)
        envelope = {"data": {"data": [1], "total": 7}}
        self.assertEqual(healthcheck.count_of(_FakeMod(envelope), "/x"), 7)

    def test_degraded_shapes_fail(self):
        for bad in ({"status": 200, "body": ""}, {"data": {"unexpected": 1}},
                    {"nope": []}, {"data": None}):
            with self.assertRaises(Exception, msg=str(bad)):
                healthcheck.count_of(_FakeMod(bad), "/x")


if __name__ == "__main__":
    unittest.main()
