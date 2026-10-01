---
name: implement-design
description: Implement a Figma frame as code in the current project (or as standalone HTML). Use when the user pastes a figma.com design/proto link, or points at a JSON export from the "LLM Export" Figma plugin, and asks to build, implement, or convert it. Uses the official Figma MCP when it has access, falls back to the view-access `figma-view` MCP when the file is view-only or the Figma plan's MCP quota is spent.
---

# Figma → code

Input: a Figma URL or an LLM Export `.json` file (`$ARGUMENTS`), plus optionally a target (app path, route, or "standalone HTML").

Step 2 (existing project) follows `<this-skill-dir>/references/component-map.md`; step 5 reviews the build with the user in rounds per `<this-skill-dir>/references/review-rounds.md`.

## 1. Hard gate — can this be built?

Runs first, on every input. **Nothing else happens until it passes** — no questions, no scaffolding, no code. Blockers surface now, not mid-build.

**Parse the input.**

LLM Export payload (a `.json` with `"source": "figma"`, `nodes`, `images`) — no MCP, no quota, works on any Figma plan. Don't `Read` it raw (base64 images can be megabytes). Split it first:

```bash
python3 <this-skill-dir>/scripts/split_payload.py <payload.json> <tmp-dir>
```

Then query `<tmp-dir>/payload.json` with python3, one subtree at a time (it's megabytes, too big to Read). Read the extracted `.png`/`.svg` files, and skip step 3.
- The PNG of the top-level selected node is the frame render (scale 2). SVGs are icon markup to reuse as-is.
- Any styled value bound to a Figma variable appears as `{ "value": …, "variable": "Collection/name" }`, and `<tmp-dir>/variables.json` lists the variables with their names and every mode.
- Instances carry `mainComponent` and `componentProperties`.
- The script also prints the missing assets (visible image and vector layers with no usable file, each with its reason) and the visible component instances.

Figma link:

- `figma.com/design/<fileKey>/…` and `figma.com/proto/<fileKey>/…` both work.
- `figma.com/design/<fileKey>/branch/<branchKey>/…` → use `branchKey` as the file key.
- `node-id=223-141` → node `223:141`. Never guess a node.

**Browser: free, so check it before any Figma call.** Open `about:blank` with the Playwright MCP this plugin ships. If the user also runs their own Playwright server, use this plugin's: it emulates the 2x display screenshots need.

If it fails, give the fix now: install Google Chrome, or run `npx -y @playwright/mcp@0.0.83 install-browser chromium` once, add `export PLAYWRIGHT_MCP_BROWSER=chromium` to the shell profile, and restart Claude Code.
- **Figma link**: ask in the same AskUserQuestion call as the source question, or alone if that one is skipped: **Fix it first** (Recommended: nothing is spent yet) / **Continue without visual check** (Verify ⚠, not asked again).
- **Bundle**: just mark Verify ⚠.

**Quota — show the cost before spending it** (Figma links only; LLM Export bundles use none). Figma has no usage API: remaining quota is never visible, and rate-limit details only arrive on a 429. So, before the first Figma call:
1. Run `python3 <this-skill-dir>/scripts/figma_usage.py summary` — this plugin's own tally for the last 30 days (this machine only, so a lower bound).
2. Estimate this run: `figma-view` = 1 `get_figma_data` + 1 image request per format (PNG, SVG) — all Tier 1 — plus 1 Tier 2 request if there are photo fills; the official MCP = its own quota, 1 call per tool used.
3. Show both in one line, e.g. *"This run ≈ 3 Tier-1 requests. Logged here in the last 30 days: 7. View/Collab seats get up to 20 Tier-1 a month (sometimes lower); Dev/Full get 10–20 a minute. Limits follow the plan that owns the file."*
4. **Ask which source to use** (AskUserQuestion; skip if the user already said):
   - **Fetch via Figma API** — costs the requests above. Recommended when the official MCP works or the user has a Dev/Full seat.
   - **Export with the LLM Export plugin** — no quota, no token, includes variable (token) names. Recommended when the tally plus this run would pass 20, on a free/Starter file, or after any 429.
   - Picked the plugin → give these steps, then wait: open the link in Figma (browser or desktop) → select the frame → Actions (`Ctrl/⌘ + /`) → search **LLM Export** → run it → **Download LLM bundle** (not "Download JSON", which drops the images) → say "done". Not in Actions → install it: see the README's LLM Export section. Then use the path the user gives, or the newest `.json` in `~/Downloads` containing `"source": "figma"` — confirm the filename with the user — and restart the gate with that bundle.

After **every** Figma call (success or failure), log it: `python3 <this-skill-dir>/scripts/figma_usage.py log <figma-view|official-mcp> <tier1|tier2|mcp> <requests> <fileKey>`.

**Probe.** Spends no extra quota: the design fetch *is* the probe. Run step 3's first fetch (official MCP, else `get_figma_data`) now, then download every asset (step 3 lists which) into `.figma-assets/` in the directory Claude Code was started in — the project's asset folder isn't known until step 2. Step 3 reuses all of it.

| Check | How | ✗ blocked / ⚠ degraded → tell the user |
|---|---|---|
| Frame link | `node-id` present | ✗ right-click the frame → Copy link to selection |
| Token (only if official MCP unavailable/failed) | `[ -n "$FIGMA_API_KEY" ]` in Bash | ✗ add `export FIGMA_API_KEY=figd_…` to the shell profile, restart Claude Code |
| Design data | the fetch succeeds | ✗ 403 → token expired / lacks file read scope, or no view access. 404 → wrong file/node. 429 → rate-limited: show the user everything the error carries — `Retry-After` (as a wait time), `X-Figma-Plan-Tier`, `X-Figma-Rate-Limit-Type` (`low` = View/Collab seat, `high` = Dev/Full), `X-Figma-Upgrade-Link` — and the raw error text if the MCP hides the headers; then offer: wait and re-run / LLM Export / stop. Never retry on your own. ⚠ official MCP refused (edit access/quota) but `figma-view` worked → no variable names below Enterprise, tokens matched by value |
| Bundle images (LLM Export only) | `images` have files | ✗ used "Download JSON" — re-export with "Download LLM bundle" |
| Frame render | the whole-frame PNG downloads (LLM Export: the top node's PNG) | ⚠ step 5 has nothing to compare against → ask the user for a frame screenshot |
| Assets | every asset downloads (LLM Export: `split_payload.py` lists no missing asset) | ⚠ any missing (export restricted for viewers, rate limit, expired URL, LLM Export's crop limits) → ask **Missing assets** below, now |
| Fonts | font families in the data | ⚠ not a Google Font → user supplies the font files, or accept a fallback (text widths will drift) |
| Verify | the browser opened (checked above, before the fetch) | ⚠ step 5: no screenshot or diff, code checks only |

**Decide.** Print one line per check (✓ / ⚠ / ✗), the source that worked, and the quota used: *"Used 3 Figma requests (Tier 1: 3). Last 30 days: 10."* (re-run `summary`).
- **Any ✗ → stop.** Ask with AskUserQuestion: fixed it, re-run the gate (Recommended) / switch to an LLM Export bundle (README) / stop. Never continue past a ✗.
- **Only ⚠ →** list what each one costs, then ask: proceed degraded / fix it and re-run the gate / stop. Missing assets get their own question (below) instead, in the same AskUserQuestion call.
- **All ✓ →** continue to step 2 without asking.

**Missing assets** — don't redraw them. List each one: node name, node id, type (photo / icon / logo), design size, and the filename it'll use (e.g. `hero-bg.png`, `logo.svg`). Leave out layers that step 2's heavy-widget question decides (maps, charts, timelines); list those as "decided in step 2". Ask with AskUserQuestion:
1. **I'll export them (Recommended)** — user opens the Figma link in the browser (view access is enough), selects each layer → Export panel (bottom right) → PNG @2x for photos, SVG for icons/logos → saves them into `.figma-assets/` with the listed filenames, then says "done". Check every file exists; anything still missing becomes a placeholder.
2. **Use placeholders** — built in step 4. Each placeholder sits in the asset's slot at its exact design size and radius, with no external service: a local neutral SVG (light gray box, the asset's name as label, diagonal cross for photos) saved under the listed filename, so swapping in the real file later needs no code change. Mark each with a comment, e.g. `<!-- PLACEHOLDER: hero-bg.png (1440×720), export from Figma node 223:150 -->`.

## 2. Ask before fetching much

Ask with AskUserQuestion (max 4 questions per call): question 1 first, then the remaining ones that apply, up to 4 per call. Skip any the user already answered. For an existing project, do the first two **Existing project** bullets below right after question 1, before asking the rest:

1. **Fresh project or existing project?**
2. **Fresh only — tech stack and component library?** (e.g. React + Tailwind + shadcn/ui (Recommended for React), Next.js + shadcn/ui, Vue + shadcn-vue, Angular + Angular Material, plain HTML/CSS). Existing projects use their own stack; don't ask.
3. **Responsive?** If yes, **which screen sizes** (e.g. 390 / 768 / 1280 / 1440px), and **a frame link per size** if the file has them. Sizes without a frame get an inferred layout, flagged as "inferred, not designed" in the report. If no, build at the frame's width only.
4. **Scope?** Static UI only / UI + mock data & state / wired to a real API (user names the endpoint).
5. **Where does it go?** Fresh: project folder name. Existing: route or file path, and whether it replaces an existing screen or is new.
6. **Existing only — off-theme values?** Match Figma exactly and comment each deviation (default) / snap to the closest theme token and list deviations in the report.
7. **Heavy widgets**: only if the design has charts, maps, data grids, carousels or timelines. The render and layer names (`map`, `chart`, `timeline`) show them. In an existing project, first grep `package.json` for a library that already draws them (e.g. `recharts`, `chart.js`, `echarts`, `maplibre-gl`, `leaflet`, `@tanstack/react-table`). Ask one question per kind of widget: use the project's library (name it) / add one (charts: shadcn `chart`, which is Recharts; maps: `maplibre-gl` or `leaflet`) / a static image from the design (no usable file yet → ask the Missing assets question for that layer now) / a placeholder. An instance widget (e.g. `Timeline / …`) with a non-null component-map row uses that row instead.

**Existing project** — then:
- Read its `package.json`, styling config (Tailwind config / CSS tokens / theme), and component folders. If it has no component library (no `components.json`, no UI kit in `package.json`), ask now, unless just reporting (rule 4): add one (shadcn/ui for React + Tailwind) / stop.
- **Search for an existing implementation first** (grep the design's headline text). If the screen already exists, don't build a second copy. This question replaces question 5:
  - **Fix it in place**: change only what differs, then run step 5's rounds. Ask questions 4 and 7 only for parts the screen doesn't have yet.
  - **Just report the diff** (what `/check-design` does): skip to step 5 for one round, no fixes.
  - **Build a new one anyway**: ask question 5.
- **Component map**: follow `<this-skill-dir>/references/component-map.md`. It shows one table mapping the design's Figma components to the project's, confirmed once and saved in `figma-components.json`.
- Several apps/routes and unclear which → ask once.

**Fresh project** — scaffold with the chosen stack's official starter (e.g. `npm create vite@latest`), then init the chosen component library (e.g. `npx shadcn@latest init`), nothing else.

## 3. Fetch the design — official first, fallback second

The gate already fetched the design and the assets; reuse them, don't fetch again. This step says what to fetch; once the project exists (step 2), move `.figma-assets/` into its asset dir (e.g. `public/images/…`), keep the frame PNG out of the project, and delete `.figma-assets/`.

**Official Figma MCP** (tools named `…figma…get_design_context`, from the official `figma` plugin), if installed:
- `get_design_context(fileKey, nodeId)` with the screenshot included; download the asset URLs it returns.
- `get_variable_defs(fileKey, nodeId)` → the Figma variables (design tokens) the frame uses, by name.
- `get_screenshot(fileKey, nodeId, contentsOnly: true)` with a `maxDimension` above the frame's long edge (e.g. 16384; the default 1024 shrinks it) → curl the PNG into `.figma-assets/` as the frame render (scale 1).
- If it errors with **"don't have edit access"** or a **rate limit**: do NOT retry it — each call spends the user's monthly quota (Starter/View/Collab seats get very few). Go to the fallback.

**Fallback: `figma-view` MCP** (this plugin; needs only view access + `FIGMA_API_KEY`):
- `get_figma_data(fileKey, nodeId)` → layout tree, text, colors, fonts, spacing, radii, shadows.
- `download_figma_images` — it can only write inside the directory Claude Code was started in. Fetch:
  - the **whole frame** as PNG (`pngScale: 1`) → the visual target, kept out of the project;
  - every `IMAGE` fill node, passing its `imageRef`;
  - every `IMAGE-SVG` node as `.svg` (logos, icons).
- Compress big photo exports before shipping (e.g. `cwebp -q 80 -resize 2560 0`).

## 4. Implement

- Build with the project's own stack: its components, tokens, form library, icon set, routing.
- **React / Next.js** — read `<this-skill-dir>/references/react/README.md` before writing components; open only the rule files it points to for what you're building. Existing-project conventions still win where they conflict.
- **shadcn/ui** (project has `components.json`) — read `<this-skill-dir>/references/shadcn/README.md`; map Figma instances to shadcn components and their variants, not hand-built lookalikes.
- **Tailwind v4** (CSS has `@import "tailwindcss"`) — read `<this-skill-dir>/references/tailwind-v4.md` before adding tokens.
- **Tokens: map the variable, not the value.** Official path and LLM Export payloads: map each Figma variable to the project token by the name `/sync-tokens` gives it: its `codeSyntax.WEB` if `variables.json` has one, else the name without its collection (`Theme/text-primary` → `--text-primary` / `text-text-primary`), keeping the collection when two collections define it with different values (`--ds-status-critical`). Bind the token, not the light/dark value — the app's theme switch handles modes. `figma-view` path has no variable bindings, so map by exact value instead. Either way, add a token only when none matches. Tokens generated from JSON (Style Dictionary / Tokens Studio: `$value` token files, a `style-dictionary` build script) → add to the source JSON and rebuild, never hand-edit the generated CSS.
- **Interactive controls come from the component library, never hand-built or native.** Select/dropdown, combobox, menu, dialog, popover, tooltip, tabs, checkbox, radio, switch, slider, date picker, toast, accordion → the library's component (shadcn: `Select`, `DropdownMenu`, `Combobox`, `Dialog`, …), added if missing. A native `<select>` opens an OS popup that can't be styled to the design; a hand-rolled `div` dropdown misses keyboard, focus and ARIA.
- **Instances → components.** Use the component map's row first (step 2); a `null` row is built from the design. Otherwise, a component instance's name and variant properties tell you which project component to use and which props to pass. Hidden sibling layers and other variants hint at hover/active/disabled/selected states — implement those states; selected vs unselected is one component with a prop, not two elements.
- Translate absolute positions into real layout (flex/grid). If responsive, make it work at every screen size the user gave. Read `<this-skill-dir>/references/layout.md` before writing layout: the auto-layout → CSS table and the fidelity checklist (per-side padding, per-corner radius, effects, hidden layers, text, table columns).
- Wire the obvious interactions: inputs, submit, show/hide password, links (`<a href>` / framework `Link`, not click-handlers, for navigation).
- **Mock data** (scope "UI + mock data"): copy the design's own rows into one typed fixture per screen, in design order, so the page shows exactly the text the design shows (`97,452`, `12.03%`). Never re-sort, dedupe, correct or invent rows. Copy an oddity as shown (an unsorted ranking, a duplicate, a county in a list of states) and list it under **Design data notes** in the report. For charts, use a series through the labelled points, marked as approximate.
- Use every asset in its design slot at its design size. Never redraw an exported asset; never ship a temporary Figma asset URL.
- **Trust the rendered frame over node properties**, unless the frame contradicts itself (cells of one row at different heights, identical cards spaced differently). Then build the consistent version and propose it as a design issue in step 5. Two traps seen in practice:
  - `textAlignHorizontal: CENTER` on a hug-width text node is invisible — the render shows the real alignment. On a fixed-width or fill text node it *is* real — keep it.
  - A background the project already has may be pre-composited (darkened) and not match the design's `IMAGE fill + opacity`. Compare against the render; prefer the design's own image.

**Existing-project rules** (all mandatory):
1. **Reuse existing components** wherever one fits; record each one's name and file path for the report.
2. **Consistency across pages** — the same UI element uses the same component everywhere; don't create a near-duplicate of one that already exists. If the design differs slightly, extend the existing component via props/variants rather than forking it.
3. **Don't break existing code** — never change an existing component's default behavior or public props in a breaking way; add optional props/variants instead. Run the project's typecheck, lint, and tests afterwards and fix anything you broke.
4. **Not feasible with the existing code?** (e.g. the component library can't do it, a needed dependency conflicts, it would require a breaking change) → stop on that part, tell the user **why**, and offer 1–3 alternatives (closest match with existing components, extend component X, add library Y) before proceeding.
5. **Off-theme design** (colors, fonts, spacing, radii not in the project's theme/tokens) → tell the user each deviation. If the user chose "match Figma", put a comment in the code at that spot, e.g. `/* OFF-THEME: #3B5BDB not in theme tokens (closest: primary-600) — per Figma design */`. If they chose "snap to theme", use the closest token and list the Figma value vs token used in the report.

## 5. Verify — with the user, in rounds

Serve the build and follow `<this-skill-dir>/references/review-rounds.md`, through cleanup.

## 6. Report

What was built and where, which source was used (official MCP, `figma-view`, or LLM Export payload) and why, what's not wired (e.g. no real API call), and any remaining differences from the design.

**Review rounds**: what `review-rounds.md` says to report.

**Placeholders** (if any): a table of filename, size, Figma node id — the user exports each from Figma under that exact filename to replace it, no code change needed.

Existing project — also list:
- **Reused components**: name + path for each, including library components (e.g. shadcn `Select`).
- **New / extended components**: what was added and why no existing one fit.
- **Component map**: rows added to `figma-components.json`; commit it so teammates build with the same components.
- **Off-theme changes**: each deviation and where it's commented (or which token it was snapped to).
- **Inferred screen sizes**: any responsive size built without a Figma frame.
- **Not feasible**: what, why, and the alternative taken.
- Typecheck / lint / test results.
