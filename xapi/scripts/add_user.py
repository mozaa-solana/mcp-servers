"""3-legged OAuth 1.0a onboarding for the xapi MCP server (PIN flow).

Run this ONE TIME per X user you want to post as. Hands you the
``X_ACCESS_TOKEN`` and ``X_ACCESS_TOKEN_SECRET`` to drop into a goclaw
MCP server config (Cách 1).

Prereqs in developer.x.com → your app → User authentication settings:
- App permissions: Read+Write (or Read+Write+DM for x_send_dm)
- Type of App:    Native App         ← required for PIN flow
- Callback URI:   http://localhost   ← required to exist, value unused

Usage:
    .venv/bin/python scripts/add_user.py
    # paste API Key / Secret when asked, open URL in browser as the
    # TARGET user, click Authorize, paste the 7-digit PIN back.
"""
from __future__ import annotations

import sys
import webbrowser

import tweepy


def prompt(label: str, hide: bool = False) -> str:
    if hide:
        import getpass
        return getpass.getpass(f"{label}: ").strip()
    return input(f"{label}: ").strip()


def main() -> int:
    print("=== xapi onboarding — 3-legged OAuth 1.0a (PIN flow) ===\n")
    print("Step 1: enter the developer-app credentials (constant per app).")
    api_key = prompt("X_API_KEY")
    api_secret = prompt("X_API_SECRET", hide=True)

    if not api_key or not api_secret:
        print("ERROR: API key/secret are required.", file=sys.stderr)
        return 1

    # callback="oob" → out-of-band → X will display a PIN instead of redirecting.
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, callback="oob")

    try:
        authorize_url = auth.get_authorization_url()
    except tweepy.TweepyException as exc:
        print(f"ERROR: could not get request token: {exc}", file=sys.stderr)
        print("\nHints:")
        print("  - App must be type 'Native App' in developer.x.com")
        print("  - At least one Callback URI must be configured (any URL is fine)")
        print("  - API Key/Secret must match the app exactly")
        return 2

    print("\nStep 2: open this URL in your browser as the TARGET X user")
    print("(the account you want to post AS — NOT necessarily the app owner):\n")
    print(f"  {authorize_url}\n")
    try:
        webbrowser.open(authorize_url)
    except Exception:
        pass

    print("After clicking Authorize, X will display a 7-digit PIN.")
    pin = prompt("PIN")
    if not pin.isdigit():
        print("ERROR: PIN must be numeric.", file=sys.stderr)
        return 3

    try:
        access_token, access_token_secret = auth.get_access_token(pin)
    except tweepy.TweepyException as exc:
        print(f"ERROR: could not exchange PIN: {exc}", file=sys.stderr)
        return 4

    # tweepy v4 also exposes the resolved user id/handle.
    me_handle: str | None = None
    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )
        me = client.get_me()
        if me and me.data:
            me_handle = f"@{me.data.username}"
    except Exception:
        pass

    print("\n=== SUCCESS ===")
    print(f"Authorized as: {me_handle or '(unknown)'}\n")
    print("Drop these into the goclaw MCP server config for THIS user:\n")
    print(f"  X_API_KEY={api_key}")
    print(f"  X_API_SECRET={api_secret}")
    print(f"  X_ACCESS_TOKEN={access_token}")
    print(f"  X_ACCESS_TOKEN_SECRET={access_token_secret}")
    if me_handle:
        print(f"  X_HANDLE={me_handle}")
    print("\nThese tokens are PERMANENT (until the user revokes the app at")
    print("https://x.com/settings/connected_apps). Treat them as secrets.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
