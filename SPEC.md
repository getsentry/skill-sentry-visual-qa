# Sentry Visual QA Specification

## Intent

Make the agent verify user-visible Sentry UI changes by opening the rendered surface in a real browser, collecting evidence matched to the behavior in question, and reporting only what that evidence supports. Adapted from `getsentry/junior`'s `visual-web-qa` for personal local use, where the browser is the locally installed `agent-browser` CLI and QA runs as a chosen Sentry account in an isolated session.

## Scope

In scope:
- Visual verification of Sentry frontend changes against the dev-ui server (`pnpm run dev-ui`) on the org subdomain, on its own port (default 7900)
- Screenshot, short video, and DOM-check evidence
- Before/after pairs for changes to surfaces that already existed, captured by switching the checkout to the merge-base on the same QA server rather than standing up a second one
- Scraps story coverage (`/scraps/<category>/<slug>/`) alongside in-app surfaces when the changed component has an `.mdx` story
- Login and identity handling for the dedicated QA browser session, including the sentry.io -> dev-origin cookie mirror

Out of scope:
- General browser automation with no visual-correctness question
- Backend-only, CLI, or test-only changes (dev-ui serves production APIs, so `src/` changes are unverifiable here)
- Jest/RTL and acceptance-test authoring
- Posting evidence to GitHub without an explicit ask

## Users And Trigger Context

- Primary user: one engineer working in a local `getsentry/sentry` checkout
- Common requests: "does this look right", "screenshot this page", "check dark mode", "check mobile width", "record the loading state"
- Should not trigger for: backend diffs, unit tests, scraping or form automation, or when the user opts out of browser verification

## Runtime Contract

- Required first actions: `scripts/sqa serve`, then `scripts/sqa ready` (org subdomain by default), then `scripts/sqa sync` if it reports `LOGIN_REQUIRED`, before any capture
- Required outputs: target URL, account from `whoami`, evidence list, result (`pass` / `issues found` / `blocked`), findings, limitations, whether a scraps story exists and was covered, and — for a change to an existing surface — a before/after pair or the reason there is none
- Non-negotiable constraints: runs are headless except the one-time sign-in window; the `sentry` org is never a target and its refusal is never worked around; no capture on any gate state but `READY`; no visual claim without browser evidence; no personal Chrome profile; no credential capture or cookie values printed; no active recording left running; the checkout is never switched over a dirty tree and never left on a detached HEAD
- Bundled files loaded at runtime: `scripts/sqa` always; references only on their routed condition

## Source And Evidence Model

Authoritative sources:
- `getsentry/junior` `packages/junior-agent-browser/skills/visual-web-qa` (workflow and evidence model)
- `agent-browser` 0.37.1 CLI surface, verified locally
- `getsentry/sentry` `AGENTS.md`, `static/app/utils/useColorscheme.tsx`, `static/app/types/system.tsx`

Data that must not be stored: passwords, session cookies, API tokens, customer org slugs, customer event data, member emails.

## Reference Architecture

- `SKILL.md`: workflow, evidence and target tables, capture rules, reporting contract
- `references/session-and-login.md`: session isolation, first-time login, account switching, auth troubleshooting
- `references/sentry-capture.md`: SPA waits, theme forcing, feature flags, failure diagnosis, devserver traps
- `scripts/sqa`: session-pinned agent-browser wrapper plus `whoami`, `ready`, `login`, `sync`, `serve`
- `scripts/dev-ui`: start/stop/status for the QA dev-ui server on its own port
- `scripts/sync-cookies` + `scripts/_sync_cookies.py`: mirror sentry.io auth cookies onto `.dev.getsentry.net`; values never printed or stored

## Validation

- Lightweight: `bash -n scripts/sqa`, and `sqa ready` against a down host (`UNREACHABLE`, exit 3), an unauthenticated dev-ui (`LOGIN_REQUIRED`, exit 2), and an authenticated one (`READY`, exit 0, `"devUi":true`)
- Deeper: one authenticated run producing a screenshot plus a matching `whoami`
- Acceptance gate: no captured artifact is reported without a preceding `READY`

## Known Limitations

- SSO logins need a one-time headed sign-in by a human on sentry.io, followed by `sqa sync`; the mirror must be re-run when that session refreshes
- Theme forcing works only when the QA account's theme option is `system`
- Flag-gated views depend on production flag state for the QA account; they cannot be toggled locally
- Every capture renders production data, so nothing is publishable without confirming the frame is clean
- Org access is limited to what the QA account can see; forbidden orgs are refused by `scripts/sqa`
- Video capture needs `ffmpeg`
- A broken frontend build shows as a stuck loading screen, not a rendering defect
- Before and after captures render live production data, so a live view can differ between the two frames for reasons unrelated to the branch; fixed targets (stories, a named issue or event) avoid it

## Maintenance Notes

- Update `SKILL.md` when the target list, evidence model, or reporting contract changes
- Update `scripts/sqa` when `agent-browser` changes its session, restore, or auth flags, or when Sentry changes `window.__initialData`
- Update `SOURCES.md` when re-syncing with the upstream junior skill
