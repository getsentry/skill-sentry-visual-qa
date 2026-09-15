# QA Session And Login

Open when `sqa ready` reports `LOGIN_REQUIRED`, when setting up QA for the first time, or when switching which Sentry account QA runs as.

## Why A Dedicated Session

QA runs in the named agent-browser session `sentry-qa`, never in the user's everyday Chrome profile. That keeps the agent out of personal cookies and lets QA run as a chosen account — typically a bot account, not the user's own.

- Cookies and localStorage persist at `~/.agent-browser/sessions/<session>-<restore>.json`.
- `--session` and `--restore` must be passed on **every** invocation. `scripts/sqa` does this; bare `agent-browser` does not.
- Never pass `--profile` or `--auto-connect`. Both attach to the user's real Chrome and its live Sentry login.

## Why Login Takes Two Steps

The dev-ui server proxies `/api` to sentry.io **server-side** (`rspack.config.ts`, `cookieDomainRewrite`). The browser therefore needs Sentry session cookies on the **dev origin**, and cookies set on `.sentry.io` are never sent to `sentry.dev.getsentry.net:7900`.

SSO cannot complete through the dev-ui origin, so signing in at `:7900/auth/login/` does not work. The working flow is sign in on sentry.io, then mirror the cookies across:

```bash
scripts/sqa login     # headed sentry.io sign-in; a human completes SSO
scripts/sqa sync      # mirror session cookies onto .dev.getsentry.net
scripts/sqa ready     # expect READY
```

`sqa login` needs a person at the keyboard. If the user is not present, stop and say a one-time sign-in is needed — never fall back to a profile that belongs to the user.

## Headed Versus Headless

Captures run headless. `scripts/sqa` passes `--headed false` on every call so a config file or stray env cannot open windows mid-run.

The mode is decided when the browser **launches**, not per command, so a session that is already running headed stays headed until it is closed. That is why `sqa login` closes the browser before opening the sign-in window, and `sqa sync` closes it afterwards.

```bash
agent-browser --session sentry-qa close    # then the next sqa command relaunches headless
SENTRY_QA_HEADED=1 scripts/sqa ready       # watch a run while debugging (close first)
```

Closing the browser is safe: `--restore` writes cookies to `~/.agent-browser/sessions/` and reloads them on the next launch, so the login survives. Verified: after a close, `sqa ready` returns `READY` for the same account without a new sign-in.

## What `sync` Copies

`scripts/sync-cookies` copies `session`, `sentry-sc`, and `sentry_react_auth` from sentry.io onto `.dev.getsentry.net`.

- `sentry-sudo` is **skipped** unless `--with-sudo` is passed. Sudo mode grants elevated access that rendering does not need.
- Cookie values are never printed, logged, or written to disk. Do not echo them, and do not dump `cookies get` to a file.
- Re-run `sqa sync` whenever the sentry.io session is refreshed; the mirrored copies do not update themselves.

## Verify Identity Before Capturing

```bash
scripts/sqa whoami
# {"sentryApp":true,"authed":true,"user":"bot@example.com","superuser":false,
#  "org":"my-org","theme":"system","devUi":true,"url":"..."}
```

Report the `user` value alongside the target URL. A screenshot proves nothing if it was taken as the wrong account: permissions, feature flags, and org access all vary per account. Expect `"devUi":true` on every run; if it is false, the target is not the dev-ui server.

## Run As A Second Account

Session name is the account boundary. Give each account its own session:

```bash
SENTRY_QA_SESSION=sentry-qa-member scripts/sqa login
SENTRY_QA_SESSION=sentry-qa-member scripts/sqa sync
SENTRY_QA_SESSION=sentry-qa-member scripts/sqa ready
```

Use this to compare member-versus-owner rendering. Never log a second account into an existing session; the saved state becomes a mix of both.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `LOGIN_REQUIRED` on dev-ui, but sentry.io works in the same session | cookies live on `.sentry.io` only | `scripts/sqa sync` |
| `LOGIN_REQUIRED` right after a successful login | flags dropped on a later call | run everything through `scripts/sqa` |
| `LOGIN_REQUIRED` on a previously working session | sentry.io session expired | `scripts/sqa login`, then `sync` |
| `sync` reports no cookies found | session never signed in to sentry.io | `scripts/sqa login` first |
| `UNREACHABLE` | dev-ui not running | `pnpm run dev-ui` in the sentry checkout |
| TLS failure on `:7900` | local cert not trusted by the QA browser | add `--ignore-https-errors` to the `sqa` call |
| Logged in as the wrong account | shared session state | delete `~/.agent-browser/sessions/<session>-*.json`, log in again |

## Never

- Never capture or share the login form mid-entry, auth cookies, session tokens, or an API token.
- Never write credentials into the skill, the repo, a screenshot, a commit, or a report.
- Never reuse the user's personal Sentry session to reach data the QA account cannot see.
