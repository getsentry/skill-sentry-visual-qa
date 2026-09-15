"""Mirror Sentry auth cookies onto the dev-ui domain. Called by scripts/sync-cookies.

Reads `agent-browser cookies get --json` on stdin. Cookie values are passed
straight to `agent-browser cookies set` and are never printed or persisted.
"""

import json
import os
import subprocess
import sys


def main() -> int:
    want = set(os.environ["SENTRY_QA_NAMES"].split())
    dest = os.environ["SENTRY_QA_DEST"]
    session = os.environ["SENTRY_QA_SESSION_NAME"]

    try:
        payload = json.load(sys.stdin)
    except Exception:
        print("could not read cookies; is the QA session open on sentry.io?", file=sys.stderr)
        return 3

    cookies = payload
    if isinstance(payload, dict):
        data = payload.get("data") or {}
        cookies = payload.get("cookies") or data.get("cookies") or data or []

    copied = []
    missing = set(want)
    for cookie in cookies:
        name = cookie.get("name")
        if name not in want or not cookie.get("domain", "").endswith("sentry.io"):
            continue
        missing.discard(name)
        cmd = [
            "agent-browser", "--session", session, "--restore", session,
            "cookies", "set", name, cookie["value"],
            "--domain", dest, "--path", cookie.get("path", "/"),
        ]
        if cookie.get("secure"):
            cmd.append("--secure")
        if cookie.get("httpOnly"):
            cmd.append("--httpOnly")
        if cookie.get("sameSite") in ("Strict", "Lax", "None"):
            cmd += ["--sameSite", cookie["sameSite"]]
        result = subprocess.run(cmd, capture_output=True, text=True)
        # Never echo cmd or its output: argv carries the cookie value.
        status = "ok" if result.returncode == 0 else "FAILED"
        print(f"  {name:20} -> {dest}  {status}")
        if result.returncode == 0:
            copied.append(name)

    if not copied:
        print("no auth cookies found on sentry.io; sign in there first", file=sys.stderr)
        return 2
    if missing:
        print(f"note: not present on sentry.io: {', '.join(sorted(missing))}", file=sys.stderr)
    print(f"copied {len(copied)} cookie(s) to {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
