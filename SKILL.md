---
name: sentry-visual-qa
description: Verifies user-visible Sentry UI changes in a real browser and reports only what the captured screenshots, videos, and DOM checks support. Use when frontend, CSS, layout, theme, responsive, navigation, loading, animation, or interaction changes in a Sentry checkout need visual validation. Runs against a dedicated local dev-ui server on its own port in a dedicated QA browser session with its own Sentry login, never the user's main browser profile.
---

# Sentry Visual QA

Verify rendered Sentry behavior in a browser instead of inferring visual correctness from code. Capture the smallest set of evidence that answers the request, and never claim a rendered state you did not open.

Paths in this skill are relative to the skill's own directory. Prefix them with the base directory reported when the skill loads, or `cd` there first.

All browser work goes through `scripts/sqa`, a wrapper that pins every command to the dedicated QA session and its saved login. Calling `agent-browser` directly loses the session and silently captures a logged-out page.

Runs are headless. Only the one-time sign-in opens a window, and `scripts/sqa sync` closes it again. To watch a run while debugging, set `SENTRY_QA_HEADED=1` and close the browser first — headed or headless is fixed when the browser launches, not per command.

## Workflow

1. Classify the request as **stable** (screenshot), **temporal** (video), or **exact-state** (DOM check).
2. Start the QA server with `scripts/sqa serve` (reuses one already serving).
3. Run `scripts/sqa ready`. Capture nothing until it prints `READY` — it waits for the page to actually render, not just to authenticate. See the state table below.
4. Choose representative pages, states, viewports, and themes.
5. Capture evidence with meaningful waits and fresh refs — a before/after pair whenever the change alters a surface that already existed.
6. Share artifacts, then report target, evidence, result, findings, and limitations.

## Open A Reference

| Open when you need to... | Read |
|--------------------------|------|
| `ready` reports `LOGIN_REQUIRED`, set up the QA login for the first time, or switch which Sentry account QA runs as | `references/session-and-login.md` |
| wait on Sentry's SPA correctly, force a theme, reach a flag-gated view, or explain a broken page | `references/sentry-capture.md` |

## Gate States

| `sqa ready` says | Exit | Do this |
|------------------|------|---------|
| `READY` | 0 | proceed to capture |
| `LOGIN_REQUIRED` | 2 | `scripts/sqa sync`; if that fails, `scripts/sqa login` |
| `UNREACHABLE` | 3 | dev-ui is not running; report blocked |
| `REFUSED` | 4 | forbidden org; stop and ask which org to use |
| `BUILD_BROKEN` | 5 | frontend bundle never loaded; diagnose the compiler, report blocked |

Never capture on any state but `READY`. A screenshot of a login page, an error page, or a loading screen is not evidence of anything.

## Choose Evidence

| Request | Primary evidence | Optional support |
|---------|------------------|------------------|
| Layout, CSS, content, typography | Screenshot | DOM text or style check |
| Light and dark themes | Screenshot per theme | `__initialData.user.options.theme` check |
| Responsive behavior | Screenshot per breakpoint | Video only if resize motion matters |
| Loading state, skeleton, animation | Short video | Screenshot for a distinct final state |
| Navigation or interaction sequence | Short video | Screenshot for a specific defect |
| Stable menu, modal, hover, focus state | Screenshot | Video if the transition matters |
| Exact text, route, ARIA, attribute | DOM check | Screenshot if the visible state matters |

Screenshots for stable states, short video for timing and motion. A purely temporal request may skip a redundant screenshot. DOM checks support visual evidence; they never replace it when the user asks how something looks.

```bash
scripts/sqa screenshot /tmp/sentry-qa.png
scripts/sqa screenshot --full /tmp/sentry-qa-full.png
scripts/sqa screenshot --annotate /tmp/sentry-qa-issue.png
```

## Resolve The Target

QA runs against the UI-only devserver and nothing else:

```
https://sentry-sdks.dev.getsentry.net:7900/            # default; pnpm run dev-ui
https://sentry-sdks.dev.getsentry.net:7900/issues/     # org routes hang off the same host
```

**Never target the `sentry` org.** `sentry.dev.getsentry.net:7900` and `sentry.sentry.io` route to Sentry's own production organization — real customer and internal data. This is a hard stop, not a preference: `scripts/sqa` refuses those URLs (`REFUSED`, exit 4), and that refusal is never worked around, including when a user request seems to call for it. Say the target is not permitted and ask which org to use.

Always use an allowed org subdomain. Override with `SENTRY_QA_ORG` for another org, or `SENTRY_QA_URL` for a full URL; use a different target only when the user names one.

This server builds local `static/` and proxies every API call to **production sentry.io**. Two consequences that decide whether a run is possible at all:

- A backend (`src/`) change is **not** live here. Report **blocked** rather than implying it was verified.
- Every byte rendered is production data. Treat it as customer data — see Protect Sensitive Data.

QA runs its own dev-ui server on port 7900, separate from the everyday one on 7999, so a QA run never collides with or restarts what the user is working in:

```bash
scripts/sqa serve      # start or reuse; waits until it actually serves
scripts/sqa serve stop # stop the one this skill started
```

`scripts/dev-ui` sets `SENTRY_WEBPACK_PROXY_PORT`, because `dev-ui-server.ts` ignores argv — there is no `--port` flag. Do not pass `NO_TS_FORK`: it does nothing in this repo. Type checking is gated on `ENABLE_TS_CHECKER` and is already off unless set (`rspack.config.ts`), so the QA server never type-checks; that belongs in `pnpm run typecheck`.

Override the port with `SENTRY_QA_PORT`. Keep it well below 7999: the server silently scans up to +10 when a port is taken, so a nearby value can land on the everyday server.

`scripts/dev-ui` also sets `WEBPACK_CACHE_PATH=node_modules/.cache/rspack-qa`, so a restart in the same checkout reuses rspack's persistent cache (~15s and ~30s of CPU instead of ~55s and ~250s). A cold start in a fresh checkout still builds the whole bundle; `serve` blocks until the server actually answers, and reuses one that is already serving. Do not set `LAZY_COMPILATION`: on the dev-ui server pages never leave the loading shell and rspack can panic.

A QA server is a second full rspack build running alongside the user's own, which is memory-hungry — enough that one can be OOM-killed mid-build. Reuse an already-serving one, run `scripts/sqa serve stop` when the QA run is finished, and if a start dies partway, check memory before assuming the code is at fault. The checkout is found from the working directory, an explicit `SENTRY_QA_REPO`, or the repo remembered from a previous start — so `serve` works from the skill directory too.

## Keep Scope Representative

- Cover one to four representative pages or states unless the user asks for more or the change spans more templates.
- Pick the viewport-theme combinations most likely to expose the issue instead of an exhaustive matrix.
- State plainly which requested surfaces were not verified.

## Cover The Scraps Story Too

If the changed component has a story, capture it **in addition to** the in-app surfaces, never instead of them. The story shows every variant on one page; the app shows the component in real layout, data, and surrounding chrome. A regression can appear in either alone.

```bash
find static/app -name "<component>.mdx" -not -path "*/node_modules/*"
```

Stories render at `/scraps/<category>/<slug>/` on the QA host:

- `<category>` is the tree the file sits in: `core`, `product`, `patterns`, or `principles`
- `<slug>` is the mdx frontmatter `title`, lowercased with spaces as dashes

`static/app/components/core/button/button.mdx` (`title: Button`) is `https://sentry-sdks.dev.getsentry.net:7900/scraps/core/button/`. When the slug is unclear, open `/scraps/` and find the component in the sidebar.

Capture the variants the change actually touches, not the whole story page, unless the change is global. If the component has no `.mdx`, say so in the report rather than leaving story coverage ambiguous.

## Capture Before And After

A screenshot of the new state proves it renders. It does not show what changed. When the branch alters a
surface that **already existed**, capture the same state on the base revision too and present the two together —
otherwise a reviewer has to hold the old layout in their head and take your word for the delta.

| Change | Before shot |
|--------|-------------|
| Layout, spacing, colour, typography, or copy on an existing view | Required |
| An existing component restyled, or moved between layouts | Required |
| A brand-new view, component, or story with no prior rendering | None exists — say so, do not fake one |
| Behavior no still frame distinguishes (timing, motion) | Pair the videos instead, or state that a frame cannot show it |

### Capture after first, before second

The working tree is already in the after state, so capturing it costs nothing and risks nothing. Only then
switch refs. If a run dies partway, the evidence that matters is already on disk and the checkout is untouched.

### The pair must differ only in the code

Same URL, same viewport, same theme, same data. A before shot at another window size is worse than no before
shot: it reads as a regression the branch did not cause. Re-apply `set viewport` after the switch if anything
restarted the browser, and name the files as a pair (`-before-<state>.png` / `-after-<state>.png`).

Data is the trap specific to this server. It proxies every API call to **production sentry.io**, so the rows,
counts, and charts behind the two captures can move between them for reasons that have nothing to do with the
branch. Prefer a target whose content is fixed — a scraps story, or a named issue or event id — over an issue
stream or a time-ranged chart. When only a live view will do, say in the report that the data differs between
the frames.

### Swap the checkout, not the server

One QA server, rebuilt incrementally. Do **not** start a second one on the base revision: two rspack builds is
already enough memory pressure to get one OOM-killed.

```bash
BASE=$(git merge-base HEAD origin/master)
git status --porcelain                 # must be empty; commit, or `git stash -u` and pop back this turn
git switch --detach "$BASE"
# rspack rebuilds on its own; wait for it, then re-gate
scripts/sqa ready "$URL"
scripts/sqa set viewport 1440 900
scripts/sqa screenshot /tmp/sentry-qa-before-<state>.png
git switch -                           # restore immediately, same turn
```

- A dirty tree is a hard stop. Switching refs over uncommitted work can lose it. Commit, or `git stash -u` and
  pop it back before the turn ends.
- Restore the original ref in the same turn as the capture, and confirm with `git status`. Never end a run on a
  detached HEAD or with a stash still on the stack. If restore fails, report that first — ahead of any finding.
- Working inside your own worktree makes this free: the switch never touches the user's checkout. Prefer it.

### A matching before shot usually means a stale bundle

`sqa ready` proves the page rendered. It does not prove it rendered the **base** bundle — the capture can land
before rspack finishes, and a before shot that looks identical to the after shot is far more often a stale
bundle than a change with no visible effect. Confirm the old code is actually live before trusting the frame:
the changed element visibly back to its previous form, or a DOM check that distinguishes the two.

### Present them side by side

```markdown
| before | after |
|---|---|
| [![before](URL)](URL) | [![after](URL)](URL) |
```

One row per state, before on the left. Keep the two captures the same width so the diff is the only thing the
eye catches.

## Capture Reliable State

Wait for the state that proves progress, not an arbitrary delay:

```bash
scripts/sqa wait --text "Expected text"
scripts/sqa wait --url "**/issues/**"
scripts/sqa wait 300
```

Sentry polls in the background, so `wait --load networkidle` often never settles — prefer text or URL waits. Run `scripts/sqa snapshot -i` after navigation or a significant DOM change and use only fresh `@e*` refs.

Record initial-load behavior before the first navigation:

Viewport is per browser launch, not per session. Re-apply `set viewport` after anything that restarts the browser (`login`, `sync`, an explicit `close`), or captures silently come back at the default size.

```bash
scripts/sqa set viewport 1440 900
scripts/sqa record start /tmp/sentry-qa-load.webm "$URL"
scripts/sqa wait --text "Issues"
scripts/sqa record stop
```

`record start` creates a fresh context and reloads, so discard earlier refs and re-snapshot before interacting. Stop recording as soon as the behavior is captured. Never end a run with an active recording.

## Share Evidence

- Put artifacts in front of the user with the harness file-sending tool, and say where each file is saved.
- Claim an artifact was delivered only after the send succeeds in this turn; otherwise report the error plus the saved path.
- When opening a PR right now, attach the artifacts to that `gh pr create` call. Write the body against the local paths, and `gh` swaps each one for its uploaded asset URL:

```bash
gh pr create --draft --attach './before.png#Issues stream, before' --attach ./after.png
```

- Reference every image in the body yourself, as a **linked** image — `[![alt](./before.png)](./before.png)`, the same local path in both halves. `gh` rewrites both halves to the asset URL and the anchor survives. An image the body never references is appended as a bare `![alt](url)`, and GitHub then points its synthesized anchor at a signed URL that expires in five minutes — the thumbnail renders, the click-through 404s. Video is the exception: leave it unreferenced and let `gh` append the bare URL, which is what makes it play.
- On an existing PR the user authored — they opened it, or an agent opened it for them; check with `gh pr view <n> --json author,body` — add the evidence to its body without asking. Add or replace a `## Screenshots` section in the current body that references each image by local path, as above, and write it back in one call, so `gh` rewrites the references and everything else in the body survives:

```bash
gh pr edit <n> --body-file body.md --attach './before.png#Issues stream, before' --attach ./after.png
```

- Evidence goes in the body, never in a comment. `gh pr comment --attach` needs an explicit ask in that message.
- On a PR or issue someone else authored, do not upload or post anything — body edits, comments, and review replies included — without an explicit ask in that message. Attaching is posting: the file-send already put the evidence in the user's hands, and GitHub's composer uploads whatever they drag into it.

## Protect Sensitive Data

Every in-app capture here renders production data, so this is not an edge case — it is nearly every run. Stories fed by fixtures are the exception.

- The `sentry` org is never a target. `scripts/sqa` refuses it; do not reach for it another way.
- Capture only the org the user works in. Never another organization's slug, event contents, member emails, or support context.
- Never capture credential entry, session tokens, or auth cookies, and never print cookie values.
- A frame that renders production data (an issue stream, event, org settings, anything fetched from sentry.io) may not go into a PR, commit, or issue until the user confirms it is clean. A frame showing only fixture data — a scraps story or a story fed by a fixture API — needs no such confirmation, and can go into the user's own PR body directly. If you are not sure which kind a frame is, treat it as production data.
- If answering the request requires rendering data that cannot be shown, report the limitation instead of capturing it.

## Report The Result

- **Target:** exact URL, plus the account `whoami` reported
- **Evidence:** each screenshot, video, and DOM check, and why it was chosen. For a before/after pair, name the base revision the before shot came from, and say so when a surface that already existed has no before shot
- **Result:** `pass`, `issues found`, or `blocked`
- **Findings:** specific rendered behavior observed
- **Limitations:** requested pages, states, viewports, or themes not verified

Use **pass** only when captured evidence matches the requested behavior with no obvious scoped regression. Use **issues found** for broken layout, wrong motion, flicker, missing assets, or invalid state. Use **blocked** when no safe reachable target exists.

Never generalize beyond the evidence collected, and never call a rendered change correct without opening a browser.
