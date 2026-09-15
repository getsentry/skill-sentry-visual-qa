# Sources

## Adapted Skill

- Repository: `getsentry/junior`
- Path: `packages/junior-agent-browser/skills/visual-web-qa`
- Fetched: September 10, 2026, from `main`
- Trust: first-party Sentry repository
- Related upstream file consulted: `packages/junior-agent-browser/skills/agent-browser/SKILL.md`

## Fidelity Boundary

Preserved from upstream:
- Evidence model: screenshots for stable states, short video for temporal behavior, DOM checks as support only
- Target-resolution priority and the refusal to pass off production as an unmerged change
- Representative-scope rule over an exhaustive matrix
- Report shape: target, evidence, result, findings, limitations
- Constraints on recording lifecycle, sensitive capture, and unsupported delivery claims

## Local Adaptations

- Replaced junior's `sendFiles` tool with the local harness file-send plus GitHub user-attachment upload for PR evidence, under the user's standing rule against posting to GitHub conversations without an explicit ask
- Added `scripts/sqa`, because `agent-browser` requires `--session` and `--restore` on every invocation and dropping them silently captures a logged-out page
- Added the `ready` gate (`READY` / `LOGIN_REQUIRED` / `UNREACHABLE`) so a login or error page cannot be captured and reported as QA evidence
- Added identity reporting via `window.__initialData` (`isAuthenticated`, `user.email`, `lastOrganization`), verified against `static/app/types/system.tsx`
- Added a dedicated QA session and auth-vault profile, explicitly separate from the user's Chrome profile, with a second-session recipe for running as another account
- Replaced the generic target list with Sentry's: full devserver `:8000`, UI-only devserver `:7999` (local `static/` against production APIs), preview, sentry.io
- Replaced `wait --load networkidle` as the default with text and URL waits, because Sentry polls in the background
- Added Sentry-specific capture knowledge: theme resolution via `user.options.theme` and `useColorscheme`, feature-flag gating through `~/.sentry/sentry.conf.py`, and `.artifacts/dev.log` for backend tracebacks
- Sharpened the sensitive-data rule to the repo's customer-information policy: the `:7999` server and sentry.io render real customer data

## Omitted

- Upstream `spec.md` behavior-contract format, replaced by this repo's `SPEC.md` template
- `spec_hash` frontmatter and junior's Skillet packaging fields, which have no local consumer
- The general `agent-browser` skill's routing boundary; the locally installed CLI ships its own `skills get core`

## Verified Locally

- `agent-browser 0.37.1` at `/opt/homebrew/bin/agent-browser`
- `open`, `eval`, `screenshot`, `--session`, `--restore` round-tripped in a scratch session
- `sqa ready` classification confirmed on a down devserver (exit 3) and unauthenticated sentry.io (exit 2)

## Revision — September 10, 2026 (dev-ui only)

Narrowed to a single target after an end-to-end test run:

- Dropped the full devserver, preview, and sentry.io targets. QA runs only against `pnpm run dev-ui`, on the org subdomain `https://sentry-sdks.dev.getsentry.net:7999` (`SENTRY_QA_ORG` overrides). The bare `sentry.` host has no org in scope.
- Removed the auth-vault password login. It targeted the local devserver, which is no longer a target.
- Added `scripts/sync-cookies`: dev-ui proxies `/api` to sentry.io server-side (`rspack.config.ts` `cookieDomainRewrite`), so the browser needs Sentry cookies on the dev origin, and SSO cannot complete through the `:7999` origin. Login is now sign in on sentry.io, then mirror `session`, `sentry-sc`, `sentry_react_auth` onto `.dev.getsentry.net`. `sentry-sudo` is opt-in via `--with-sudo`.
- Inverted the sensitive-data guidance: with dev-ui the only target, every capture is production data rather than seeded local data.
- Added build-failure diagnosis after a live run hit `Loading a $#!%-ton of JavaScript…` caused by `@sentry/conventions` 0.21.0 installed against a `^0.22.0` requirement. The skill now checks the compiler and entrypoint before blaming the component.

## Revision — scraps story coverage

- Added the rule that a changed component's scraps story is captured alongside in-app surfaces, not instead of them.
- Story URL shape verified against `static/app/router/routes.tsx` (`/scraps/*`, `/stories/*` is a legacy redirect), `static/app/stories/view/index.tsx` (`/scraps/:category/:slug`), and `storyTree.tsx:690` (link construction). Categories from `storyTree.tsx:108`; slug from the mdx frontmatter `title`, confirmed with `components/core/button/button.mdx`.

## Revision — headless default

- `scripts/sqa` now passes `--headed false` on every call, with `SENTRY_QA_HEADED=1` as a debugging opt-in. Headed/headless is fixed at browser launch, so `sqa login` closes any running browser before opening the sign-in window and `sqa sync` closes it afterwards.
- Verified that closing the browser does not lose the session: `--restore` reloads the mirrored cookies and `sqa ready` returns `READY` without a new sign-in.

## Revision — dedicated QA dev-ui server

- Added `scripts/dev-ui` (`sqa serve`): starts, reuses, or stops a QA dev-ui server on port 7900, so QA never collides with the everyday server on 7999.
- Port is set with `SENTRY_WEBPACK_PROXY_PORT`, not a flag: `scripts/dev-ui-server.ts` never reads argv, so a `--port` argument is silently ignored. It also scans up to +10 when the port is taken, so the QA default is kept far below 7999 and the bound port is verified after start.
- `NO_TS_FORK` is not used: it does not exist in this repo. Type checking is `SHOULD_CHECK_TYPES = DEV_MODE && Boolean(env.ENABLE_TS_CHECKER)` (`rspack.config.ts:81`), opt-in and already off.
- Readiness probe distinguishes curl exit 0 (serving), 7 (nothing listening), and 28 (listening, still bundling), because rspack-dev-middleware blocks requests to `/` until the first bundle finishes; a short timeout otherwise looks identical to a dead server.
- `ready` now asserts the browser landed on the requested host and port: `agent-browser open` exits 0 even on `ERR_CONNECTION_REFUSED`, so the gate could previously validate a stale page and report `READY` for a server that was not running.

- `ready` additionally waits for the loading shell to clear: hydration sets `__initialData` before React mounts, so the gate previously reported `READY` while the page still showed the loading screen, and a capture taken then was the spinner.
- `dev-ui stop` kills the recorded pid, its descendants, and the port listener. Killing only the recorded pid left the server running: pnpm spawns node which spawns rspack, and macOS has no `setsid`, so the process-group kill never applied.
- Checkout resolution takes `SENTRY_QA_REPO`, else walks up from `$PWD`, else the repo remembered from a previous start, because the skill is usually invoked from its own directory.
- `dev-ui stop` filters to live pids: an OOM-killed server leaves a stale pidfile, and killing a dead pid otherwise reported a successful stop. Observed after a QA server was OOM-killed while the everyday server kept running.
