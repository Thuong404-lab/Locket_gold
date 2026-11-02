#!/usr/bin/env python3
"""Log in to Locket with terminal prompts and reuse the saved session.

The password is not written to source code. The session file contains plaintext
tokens: keep it on your own computer and do not upload it to GitHub.
"""

import os
import sys
import warnings
from getpass import GetPassWarning, getpass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from requests.exceptions import RequestException

from locketlam import LocketClient
from locketlam.exceptions import AuthenticationError, LocketError

SESSION_FILE = os.path.join(REPO_ROOT, "locketlam_session.json")


def main():
    print("🔑 LOCKET LOGIN AND SESSION MANAGEMENT")
    client = LocketClient(session_path=SESSION_FILE)

    # Keep the saved device configuration. New clients use the defaults.
    # For custom settings, call client.set_device(auto_emulate=False, ...).
    try:
        if client.is_authenticated():
            print("Found a saved session. Checking its token...")
        else:
            print("Enter credentials in the terminal; do not put passwords in Python files.")
            email = input("Locket email: ").strip()
            if not email:
                print("Email must not be empty.")
                return 1

            # Stop if the terminal cannot hide input instead of allowing
            # getpass to fall back to visible password entry.
            with warnings.catch_warnings():
                warnings.simplefilter("error", GetPassWarning)
                password = getpass("Locket password (characters are hidden): ")
            if not password:
                print("Password must not be empty.")
                return 1

            try:
                client.login(email=email, password=password)
            finally:
                del password

        # Check/refresh the token synchronously before reporting success.
        client.session.get_valid_token()
    except GetPassWarning:
        print("Cannot hide password input. Run in an interactive VS Code terminal or PowerShell.")
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nLogin cancelled.")
        return 1
    except AuthenticationError:
        print("Authentication failed. Check your credentials or saved session.")
        return 1
    except RequestException:
        print("Cannot reach the login server. Check your network connection and try again.")
        return 1
    except LocketError:
        print("Could not complete login. Check your configuration and try again.")
        return 1

    print("✅ Session ready. Tokens are not displayed.")
    print(f"💾 Session file: {SESSION_FILE}")
    print("This file contains plaintext login tokens. Do not share it or upload it to GitHub.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
