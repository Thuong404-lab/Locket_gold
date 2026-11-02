"""Offline checks for credential handling in both login examples."""

import io
import json
import runpy
import tempfile
import unittest
import warnings
from contextlib import redirect_stdout
from getpass import GetPassWarning
from pathlib import Path
from unittest.mock import Mock, patch

from locketlam import SessionManager
from locketlam.exceptions import AuthenticationError


ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("vi", "en")
EMAIL = "offline-test@example.invalid"
PASSWORD = "  test password with spaces  "
ID_TOKEN = "fake-id-token-" + "t" * 40
REFRESH_TOKEN = "fake-refresh-token-" + "r" * 40


class TestLoginExamples(unittest.TestCase):
    def load_example(self, language):
        client = Mock()
        client.is_authenticated.return_value = False
        client.session.get_valid_token.return_value = ID_TOKEN
        client.login.return_value = {"idToken": ID_TOKEN, "refreshToken": REFRESH_TOKEN}
        with patch("locketlam.LocketClient", return_value=client) as factory:
            namespace = runpy.run_path(str(ROOT / "examples" / language / "01_login_and_session.py"))
        # Importing an example must not instantiate a client or save a session.
        factory.assert_not_called()
        globals_dict = namespace["main"].__globals__
        globals_dict["LocketClient"] = factory
        return namespace["main"], globals_dict, client, factory

    def assert_no_credentials(self, output):
        for value in (EMAIL, PASSWORD, ID_TOKEN[:20], REFRESH_TOKEN[:20]):
            self.assertNotIn(value, output)

    def test_login_hides_credentials_and_preserves_password_spaces(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                main, namespace, client, factory = self.load_example(language)
                output = io.StringIO()
                with patch("builtins.input", return_value=" " + EMAIL + " "), \
                        patch.dict(namespace, {"getpass": Mock(return_value=PASSWORD)}), \
                        redirect_stdout(output):
                    self.assertEqual(main(), 0)
                client.login.assert_called_once_with(email=EMAIL, password=PASSWORD)
                client.session.get_valid_token.assert_called_once_with()
                factory.assert_called_once_with(session_path=str(ROOT / "locketlam_session.json"))
                self.assert_no_credentials(output.getvalue())

    def test_saved_session_does_not_prompt_for_credentials(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                main, namespace, client, _ = self.load_example(language)
                client.is_authenticated.return_value = True
                hidden_input = Mock(side_effect=AssertionError("Unexpected password prompt"))
                output = io.StringIO()
                with patch("builtins.input", side_effect=AssertionError("Unexpected email prompt")), \
                        patch.dict(namespace, {"getpass": hidden_input}), redirect_stdout(output):
                    self.assertEqual(main(), 0)
                client.login.assert_not_called()
                client.session.get_valid_token.assert_called_once_with()
                self.assert_no_credentials(output.getvalue())

    def test_empty_credentials_do_not_attempt_login(self):
        for language in LANGUAGES:
            for email, password in (("   ", PASSWORD), (EMAIL, "")):
                with self.subTest(language=language, empty_email=not email.strip()):
                    main, namespace, client, _ = self.load_example(language)
                    hidden_input = Mock(return_value=password)
                    with patch("builtins.input", return_value=email), \
                            patch.dict(namespace, {"getpass": hidden_input}), redirect_stdout(io.StringIO()):
                        self.assertEqual(main(), 1)
                    client.login.assert_not_called()
                    client.session.get_valid_token.assert_not_called()
                    if not email.strip():
                        hidden_input.assert_not_called()

    def test_visible_password_fallback_is_blocked(self):
        def unsupported_terminal(prompt):
            warnings.warn("Cannot hide input", GetPassWarning)
            self.fail("Password entry must stop before visible fallback")

        for language in LANGUAGES:
            with self.subTest(language=language):
                main, namespace, client, _ = self.load_example(language)
                with patch("builtins.input", return_value=EMAIL), \
                        patch.dict(namespace, {"getpass": unsupported_terminal}), redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), 1)
                client.login.assert_not_called()

    def test_cancelled_input_does_not_attempt_login(self):
        for language in LANGUAGES:
            for error in (EOFError, KeyboardInterrupt):
                with self.subTest(language=language, error=error.__name__):
                    main, namespace, client, _ = self.load_example(language)
                    with patch("builtins.input", return_value=EMAIL), \
                            patch.dict(namespace, {"getpass": Mock(side_effect=error)}), \
                            redirect_stdout(io.StringIO()):
                        self.assertEqual(main(), 1)
                    client.login.assert_not_called()

    def test_authentication_errors_do_not_print_server_response(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                main, namespace, client, _ = self.load_example(language)
                client.login.side_effect = AuthenticationError(EMAIL + PASSWORD + ID_TOKEN)
                output = io.StringIO()
                with patch("builtins.input", return_value=EMAIL), \
                        patch.dict(namespace, {"getpass": Mock(return_value=PASSWORD)}), \
                        redirect_stdout(output):
                    self.assertEqual(main(), 1)
                client.session.get_valid_token.assert_not_called()
                self.assert_no_credentials(output.getvalue())

    def test_expired_session_is_not_reported_as_ready(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                main, _, client, _ = self.load_example(language)
                client.is_authenticated.return_value = True
                client.session.get_valid_token.side_effect = AuthenticationError(ID_TOKEN)
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(main(), 1)
                self.assertNotIn("✅", output.getvalue())
                self.assert_no_credentials(output.getvalue())

    def test_session_persists_tokens_but_not_password(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "localId": "offline-user",
            "email": EMAIL,
            "idToken": ID_TOKEN,
            "refreshToken": REFRESH_TOKEN,
            "expiresIn": "3600",
        }
        with tempfile.TemporaryDirectory() as folder:
            session_path = Path(folder) / "session.json"
            session = SessionManager(session_path=str(session_path))
            with patch("locketlam.session.requests.post", return_value=response):
                session.login(EMAIL, PASSWORD)
            saved_text = session_path.read_text(encoding="utf-8")
            saved = json.loads(saved_text)
            self.assertEqual(saved["idToken"], ID_TOKEN)
            self.assertNotIn("password", saved)
            self.assertNotIn(PASSWORD, saved_text)


if __name__ == "__main__":
    unittest.main()
