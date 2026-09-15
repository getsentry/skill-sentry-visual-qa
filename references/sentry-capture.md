# Capturing Sentry's UI

Open when waiting on Sentry's SPA, forcing a theme, reaching a flag-gated view, or explaining a page that renders wrong.

## Contents

- Waiting on the SPA
- Forcing light and dark
- Reaching flag-gated UI
- Explaining a broken page
- Dev-UI traps
- The page is stuck loading JavaScript

## Waiting On The SPA

Sentry polls in the background and streams data after first paint, so `wait --load networkidle` frequently never resolves.

| Goal | Wait on |
|------|---------|
| Route change | `sqa wait --url "**/issues/**"` |
| View finished rendering | `sqa wait --text "<a heading only that view renders>"` |
| Data arrived, not just the skeleton | `sqa wait --text "<a value from the row/chart>"` |
| Animation with no completion signal | `sqa wait 300` |

Screenshot the loaded state, not the skeleton: wait for real content before capturing, or the evidence just shows placeholders. Re-run `sqa snapshot -i` after every navigation or significant DOM change and use only fresh `@e*` refs.

## Forcing Light And Dark

The account's `user.options.theme` wins. `prefers-color-scheme` only decides when that option is `system` — see `useColorscheme`.

```bash
scripts/sqa whoami            # confirm "theme":"system" first
scripts/sqa set media dark
scripts/sqa set media light
```

If `whoami` reports `"theme":"dark"` or `"light"`, `set media` changes nothing. Either change the QA account's theme in user settings, or say the theme could not be switched — do not present one theme's screenshot as both.

Confirm which theme actually rendered before reporting it:

```bash
scripts/sqa eval "getComputedStyle(document.body).backgroundColor"
```

## Reaching Flag-Gated UI

Most new Sentry UI sits behind a feature flag, so an empty page usually means the flag is off, not that the change is broken.

```bash
scripts/sqa eval "JSON.stringify(window.__initialData.features)"
```

On the local devserver, enable a flag in `~/.sentry/sentry.conf.py` and restart the devserver:

```python
SENTRY_FEATURES["organizations:my-new-feature"] = True
```

Organization-level flags also need the org in scope; project-level flags need the right project selected. If the flag cannot be enabled, report **blocked** and name the flag.

## Explaining A Broken Page

Check the browser and the server before concluding the change is at fault:

```bash
scripts/sqa errors     # uncaught page errors
scripts/sqa console    # console output, including failed chunk loads
tail -100 .artifacts/dev.log   # devserver output: tracebacks, reload failures
```

| Symptom | Likely cause |
|---------|--------------|
| Blank page, chunk 404s in console | webpack still rebuilding, or a stale dev build |
| Page renders, panel empty | feature flag off, or org/project not in scope |
| 403 or a redirect to login | QA account lacks access to that org, project, or view |
| 500 with a traceback in `dev.log` | backend change, not a visual regression |
| Layout fine locally, wrong on the dev-ui server | UI-only server runs local `static/` against production APIs |

## Dev-UI Traps

- The server builds local `static/` and proxies APIs to **production** sentry.io. A `src/` change is not live here; report **blocked** instead of implying it was checked.
- Always use an allowed org subdomain (`https://sentry-sdks.dev.getsentry.net:7900/...`). The `sentry.` host is Sentry's own production org and is refused outright; never route around that.
- `whoami` should report `"devUi":true`. If it does not, the capture is not coming from the dev-ui server.
- Data is production data, so empty states are real. Do not report a rendering bug without a DOM check confirming the view is actually empty.

## Hydration Is Not Rendering

`window.__initialData` is set by `bootWithHydration` before React mounts and before route chunks compile, so `whoami` can report `"authed":true` while the loading shell is still on screen. An identity check alone is not proof the page rendered.

`scripts/sqa ready` handles this: after hydration it waits for the loading shell to disappear (up to `SENTRY_QA_RENDER_TIMEOUT`, default 120s) before reporting `READY`. On a freshly started server the first visit to a route compiles its chunk on demand, so that wait is normal, not a hang.

If capturing outside the gate, confirm the view rendered before the screenshot:

```bash
scripts/sqa wait --text "<a heading only that view renders>"
```

## The Page Is Stuck Loading JavaScript

`Loading a $#!%-ton of JavaScript…` means the bundle never arrived. This is almost always a build failure, not a rendering bug. Check the compiler before touching the component:

`scripts/sqa ready` already polls for 20s before reporting `BUILD_BROKEN`, so a slow boot is not mistaken for a failure. When it does report it, diagnose like this:

```bash
scripts/sqa console --clear && scripts/sqa reload && scripts/sqa wait 5000
scripts/sqa console | grep -i "rspack-dev-server\|Errors while compiling"
curl -skS -o /dev/null -w '%{http_code}\n' https://sentry-sdks.dev.getsentry.net:7900/_assets/app.js
```

**Clear the console first.** `sqa console` returns a buffered log for the whole session, so errors from an earlier navigation will otherwise look like errors on the current page — the fastest way to report a fixed build as still broken.

The bundle entrypoints are `/_assets/runtime.js`, `/_assets/app.js`, and `/_assets/sentry.js`. Read them off the page rather than assuming a path:

```bash
scripts/sqa eval "Array.from(document.querySelectorAll('script[src]')).map(s=>s.src).join('\n')"
```

A 200 on `app.js` plus a React DevTools or React Router message in a freshly cleared console means the app booted and the problem is elsewhere.

| Compiler error | Cause | Fix |
|----------------|-------|-----|
| `Package subpath './x' is not defined by "exports"` | `node_modules` is older than `package.json` requires | `pnpm install`, then let the server rebuild |
| `Module not found` for a repo path | file renamed or not saved | fix the import |
| Type or syntax error naming a changed file | the change under QA does not compile | fix it before capturing |

Compare the installed version against the requirement before concluding anything:

```bash
python3 -c "import json;print(json.load(open('node_modules/<pkg>/package.json'))['version'])"
grep '"<pkg>"' package.json
```

Report **blocked** with the compiler error while the bundle is broken. Never screenshot the loading screen and describe it as the change rendering.
