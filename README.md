# sentry-visual-qa

An [agent skill](https://code.claude.com/docs/en/skills) that makes a coding agent verify
user-visible [Sentry](https://github.com/getsentry/sentry) UI changes in a real browser, and
report only what the captured screenshots, videos, and DOM checks actually support.

The problem it solves: agents are happy to call a CSS change "correct" from the diff alone.
This skill makes the agent open the rendered surface, gate on the page having really loaded,
capture the smallest evidence set that answers the question, and say plainly which surfaces it
did not check.

## What it does

- Runs a dedicated UI-only devserver (`pnpm run dev-ui`) on its own port, so a QA run never
  collides with the devserver you are working in.
- Drives a dedicated headless browser session with its own Sentry login — never your personal
  browser profile.
- Gates every capture behind a readiness check (`READY` / `LOGIN_REQUIRED` / `UNREACHABLE` /
  `REFUSED` / `BUILD_BROKEN`), so a login page or a loading spinner can't be reported as evidence.
- Picks evidence by request type: screenshots for stable states, short video for timing and
  motion, DOM checks as support.
- Captures before/after pairs by switching the checkout to the merge-base on the same server.
- Covers the component's scraps story (Sentry's component-story system) alongside the
  in-app surface when one exists.

## Requirements

- A local `getsentry/sentry` checkout (the dev-ui server is started from it)
- The [`agent-browser`](https://agent-browser.dev/) CLI on `PATH` — `brew install agent-browser` (developed against 0.37.1)
- `python3` — used only to mirror auth cookies onto the dev origin
- `curl`, `bash`
- `ffmpeg`, for video capture only

## Install

The repository root *is* the skill, so clone it straight into your agent's skills directory
and `git pull` updates the skill in place:

```bash
# Claude Code (personal skills)
git clone https://github.com/<you>/sentry-visual-qa.git ~/.claude/skills/sentry-visual-qa
```

If you keep your checkouts elsewhere, clone there and symlink the clone in under the same
name instead.

## Configuration

Everything is environment variables; there is no config file.

| Variable | Default | Purpose |
|----------|---------|---------|
| `SENTRY_QA_ORG` | `sentry-sdks` | Org subdomain QA runs against |
| `SENTRY_QA_URL` | `https://$SENTRY_QA_ORG.dev.getsentry.net:$SENTRY_QA_PORT` | Full target URL override |
| `SENTRY_QA_PORT` | `7900` | Port for the QA devserver, kept clear of the everyday `7999` |
| `SENTRY_QA_REPO` | walks up from `$PWD` | Path to the Sentry checkout |
| `SENTRY_QA_SESSION` | `sentry-qa` | Browser session name |
| `SENTRY_QA_HEADED` | unset (headless) | Set to `1` to watch a run while debugging |
| `SENTRY_QA_FORBIDDEN_ORGS` | `sentry` | Orgs that are refused outright |
| `SENTRY_QA_COOKIE_DOMAIN` | `.dev.getsentry.net` | Destination domain for the cookie mirror |
| `SENTRY_QA_START_TIMEOUT` | `300` | Seconds to wait for a cold devserver build |
| `SENTRY_QA_PROBE_TIMEOUT` | `60` | Seconds for a single readiness probe |
| `SENTRY_QA_RENDER_TIMEOUT` | `120` | Seconds to wait for the app shell to render |

Server state (pid, port, remembered checkout) lives in
`${XDG_CACHE_HOME:-~/.cache}/sentry-visual-qa`.

## Safety

The dev-ui server builds local `static/` but proxies **every API call to production
sentry.io**, so every pixel captured is production data. Two rules follow from that, and the
skill enforces both:

- Sentry's own `sentry` org is never a target. `scripts/sqa` refuses those URLs outright
  (exit 4), and the skill instructs the agent never to route around that refusal.
- Nothing captured goes into a PR, commit, or issue without a human confirming the frame is
  clean. The skill also never posts to a GitHub conversation on its own.

Backend (`src/`) changes are *not* live on this server — the skill reports such a request as
blocked rather than implying it was verified.

## Layout

```
SKILL.md                      workflow, evidence model, capture rules, reporting contract
SPEC.md                       behavior contract: scope, runtime contract, known limitations
SOURCES.md                    provenance, upstream fidelity boundary, revision log
references/
  session-and-login.md        session isolation, first-time login, account switching
  sentry-capture.md           SPA waits, theme forcing, feature flags, failure diagnosis
scripts/
  sqa                         session-pinned agent-browser wrapper + ready/login/sync/serve
  dev-ui                      start/stop/status for the QA devserver on its own port
  sync-cookies, _sync_cookies.py   mirror sentry.io auth cookies onto the dev origin
```

## Provenance

Adapted for personal local use from `getsentry/junior`'s `visual-web-qa` skill. `SOURCES.md`
records what was preserved from upstream, what was adapted, and what was dropped.

## License

[MIT](LICENSE)
