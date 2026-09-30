---
name: implement-design
description: Implement a Figma frame as code in the current project (or as standalone HTML). Use when the user pastes a figma.com design/proto link, or points at a JSON export from the "LLM Export" Figma plugin, and asks to build, implement, or convert it. Uses the official Figma MCP when it has access, falls back to the view-access `figma-view` MCP when the file is view-only or the Figma plan's MCP quota is spent.
---

# Figma → code

Input: a Figma URL or an LLM Export `.json` file (`$ARGUMENTS`), plus optionally a target (app path, route, or "standalone HTML").

## 1. Hard gate — can this be built?

Runs first, on every input. **Nothing else happens until it passes** — no questions, no scaffolding, no code. Blockers surface now, not mid-build.

**Parse the input.**

LLM Export payload (a `.json` with `"source": "figma"`, `nodes`, `images`) — no MCP, no quota, works on any Figma plan. Don't `Read` it raw (base64 images can be megabytes). Split it first:

```bash
python3 <this-skill-dir>/scripts/split_payload.py <payload.json> <tmp-dir>
```

Then read `<tmp-dir>/payload.json` and the extracted `.png`/`.svg` files, and skip step 3. The PNG of the top-level selected node is the frame render; SVGs are icon markup to reuse as-is. Any styled value bound to a Figma variable appears as `{ "value": …, "variable": "Collection/name" }`; `variables[]` lists every referenced variable with its per-mode values. Instances carry `mainComponent` and `componentProperties`.

Figma link:

- `figma.com/design/<fileKey>/…` and `figma.com/proto/<fileKey>/…` both work.
- `figma.com/design/<fileKey>/branch/<branchKey>/…` → use `branchKey` as the file key.
- `node-id=223-141` → node `223:141`. Never guess a node.

**Quota — show the cost before spending it** (Figma links only; LLM Export bundles use none). Figma has no usage API: remaining quota is never visible, and rate-limit details only arrive on a 429. So, before the first Figma call:
1. Run `python3 <this-skill-dir>/scripts/figma_usage.py summary` — this plugin's own tally for the last 30 days (this machine only, so a lower bound).
2. Estimate this run: `figma-view` = 1 `get_figma_data` + 1 image request per format (PNG, SVG) — all Tier 1 — plus 1 Tier 2 request if there are photo fills; the official MCP = its own quota, 1 call per tool used.
3. Tell the user both in one line, e.g. *"This run ≈ 3 Tier-1 requests. Logged here in the last 30 days: 7. View/Collab seats get up to 20 Tier-1 a month (sometimes lower); Dev/Full get 10–20 a minute. Limits follow the plan that owns the file."* Don't ask — continue unless they object. If the tally plus this run would pass 20, recommend an LLM Export bundle (no quota) first.

After **every** Figma call (success or failure), log it: `python3 <this-skill-dir>/scripts/figma_usage.py log <figma-view|official-mcp> <tier1|tier2|mcp> <requests> <fileKey>`.

**Probe.** Spends no extra quota: the design fetch *is* the probe. Run step 3's first fetch (official MCP, else `get_figma_data`) now, then download every asset (step 3 lists which) into `.figma-assets/` in the directory Claude Code was started in — the project's asset folder isn't known until step 2. Step 3 reuses all of it.

| Check | How | ✗ blocked / ⚠ degraded → tell the user |
|---|---|---|
| Frame link | `node-id` present | ✗ right-click the frame → Copy link to selection |
| Token (only if official MCP unavailable/failed) | `[ -n "$FIGMA_API_KEY" ]` in Bash | ✗ add `export FIGMA_API_KEY=figd_…` to the shell profile, restart Claude Code |
| Design data | the fetch succeeds | ✗ 403 → token expired / lacks file read scope, or no view access. 404 → wrong file/node. 429 → rate-limited: show the user everything the error carries — `Retry-After` (as a wait time), `X-Figma-Plan-Tier`, `X-Figma-Rate-Limit-Type` (`low` = View/Collab seat, `high` = Dev/Full), `X-Figma-Upgrade-Link` — and the raw error text if the MCP hides the headers; then offer: wait and re-run / LLM Export / stop. Never retry on your own. ⚠ official MCP refused (edit access/quota) but `figma-view` worked → no variable names below Enterprise, tokens matched by value |
| Bundle images (LLM Export only) | `images` have files | ✗ used "Download JSON" — re-export with "Download LLM bundle" |
| Frame render | the whole-frame PNG downloads (LLM Export: the top node's PNG) | ⚠ step 5 has nothing to compare against → ask the user for a frame screenshot |
| Assets | every asset downloads (LLM Export: every asset has an extracted file) | ⚠ any missing (export restricted for viewers, rate limit, expired URL) → ask **Missing assets** below, now |
| Fonts | font families in the data | ⚠ not a Google Font → user supplies the font files, or accept a fallback (text widths will drift) |
| Verify | a Playwright MCP is available | ⚠ step 5 can only eyeball, not measure |

**Decide.** Print one line per check (✓ / ⚠ / ✗), the source that worked, and the quota used: *"Used 3 Figma requests (Tier 1: 3). Last 30 days: 10."* (re-run `summary`).
- **Any ✗ → stop.** Ask with AskUserQuestion: fixed it, re-run the gate (Recommended) / switch to an LLM Export bundle (README) / stop. Never continue past a ✗.
- **Only ⚠ →** list what each one costs, then ask: proceed degraded / fix it and re-run the gate / stop. Missing assets get their own question (below) instead, in the same AskUserQuestion call.
- **All ✓ →** continue to step 2 without asking.

**Missing assets** — don't redraw them. List each one: node name, node id, type (photo / icon / logo), design size, and the filename it'll use (e.g. `hero-bg.png`, `logo.svg`). Ask with AskUserQuestion:
1. **I'll export them (Recommended)** — user opens the Figma link in the browser (view access is enough), selects each layer → Export panel (bottom right) → PNG @2x for photos, SVG for icons/logos → saves them into `.figma-assets/` with the listed filenames, then says "done". Check every file exists; anything still missing becomes a placeholder.
2. **Use placeholders** — built in step 4. Each placeholder sits in the asset's slot at its exact design size and radius, with no external service: a local neutral SVG (light gray box, the asset's name as label, diagonal cross for photos) saved under the listed filename, so swapping in the real file later needs no code change. Mark each with a comment, e.g. `<!-- PLACEHOLDER: hero-bg.png (1440×720), export from Figma node 223:150 -->`.

## 2. Ask before fetching much

Ask with AskUserQuestion (max 4 questions per call): question 1 first, then the remaining ones that apply in a second call. Skip any the user already answered:

1. **Fresh project or existing project?**
2. **Fresh only — tech stack?** (e.g. React + Tailwind, Next.js, Vue, Angular, plain HTML/CSS). Existing projects use their own stack; don't ask.
3. **Responsive?** If yes, **which screen sizes** (e.g. 390 / 768 / 1280 / 1440px), and **a frame link per size** if the file has them. Sizes without a frame get an inferred layout, flagged as "inferred, not designed" in the report. If no, build at the frame's width only.
4. **Scope?** Static UI only / UI + mock data & state / wired to a real API (user names the endpoint).
5. **Where does it go?** Fresh: project folder name. Existing: route or file path, and whether it replaces an existing screen or is new.
6. **Existing only — off-theme values?** Match Figma exactly and comment each deviation (default) / snap to the closest theme token and list deviations in the report.

**Existing project** — then:
- Read its `package.json`, styling config (Tailwind config / CSS tokens / theme), and component folders.
- **Search for an existing implementation first** (grep the design's headline text). If the screen already exists, report the diff against the design instead of building a second copy.
- Several apps/routes and unclear which → ask once.

**Fresh project** — scaffold with the chosen stack's official starter (e.g. `npm create vite@latest`), nothing extra.

## 3. Fetch the design — official first, fallback second

The gate already fetched the design and the assets; reuse them, don't fetch again. This step says what to fetch; once the project exists (step 2), move `.figma-assets/` into its asset dir (e.g. `public/images/…`), keep the frame PNG out of the project, and delete `.figma-assets/`.

**Official Figma MCP** (tools named `…figma…get_design_context`, from the official `figma` plugin), if installed:
- `get_design_context(fileKey, nodeId)` with the screenshot included; download the asset URLs it returns.
- `get_variable_defs(fileKey, nodeId)` → the Figma variables (design tokens) the frame uses, by name.
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
- **Tokens: map the variable, not the value.** Official path and LLM Export payloads: map each Figma variable to the project token by name (`Theme/text-primary` → `--text-primary` / `text-text-primary`); the collection prefix is noise, the leaf name is the key. Bind the token, not the light/dark value — the app's theme switch handles modes. `figma-view` path has no variable bindings, so map by exact value instead. Either way, add a token only when none matches. Tokens generated from JSON (Style Dictionary / Tokens Studio: `$value` token files, a `style-dictionary` build script) → add to the source JSON and rebuild, never hand-edit the generated CSS.
- **Instances → components.** A component instance's name and variant properties tell you which project component to use and which props to pass. Hidden sibling layers and other variants hint at hover/active/disabled/selected states — implement those states; selected vs unselected is one component with a prop, not two elements.
- Translate absolute positions into real layout (flex/grid). If responsive, make it work at every screen size the user gave. Auto-layout maps like this:

  | Figma | CSS |
  |---|---|
  | `layoutMode` HORIZONTAL / VERTICAL / GRID | `flex` row / `flex` column / `grid` (`gridColumnsSizing` → `grid-template-columns`) |
  | `itemSpacing` | `gap` — except with `SPACE_BETWEEN`, where the stored spacing is stale: use `justify-content: space-between`, no gap |
  | `primaryAxisAlignItems` MIN / CENTER / MAX / SPACE_BETWEEN | `justify-content` start / center / flex-end / space-between |
  | `counterAxisAlignItems` MIN / CENTER / MAX / BASELINE | `align-items` start / center / flex-end / baseline; every child FILL on the cross axis → `stretch` |
  | child sizing FIXED / HUG / FILL | explicit size / no size (content) / `flex-1` on the main axis (`layoutGrow`), `align-self: stretch` on the cross axis (`layoutAlign: STRETCH`) |
  | `layoutPositioning: ABSOLUTE` inside auto-layout | `position: absolute` at its offset from the parent; parent `position: relative` |
  | `layoutWrap: WRAP` | `flex-wrap: wrap`; `counterAxisSpacing` → row gap |
  | the **top-level frame's** FIXED width/height | not a real constraint — it's the artboard. Fill the container (`width: 100%`, `max-width` = design width if centered), don't pin it |
  | text `letterSpacing` px | `em` = px ÷ font size (survives font-size changes) |
- Wire the obvious interactions: inputs, submit, show/hide password, links (`<a href>` / framework `Link`, not click-handlers, for navigation).
- Use every asset in its design slot at its design size. Never redraw an exported asset; never ship a temporary Figma asset URL.
- **Trust the rendered frame over node properties.** Two traps seen in practice:
  - `textAlignHorizontal: CENTER` on a hug-width text node is invisible — the render shows the real alignment. On a fixed-width or fill text node it *is* real — keep it.
  - A background the project already has may be pre-composited (darkened) and not match the design's `IMAGE fill + opacity`. Compare against the render; prefer the design's own image.
- **Fidelity checklist** — details that routinely get dropped; account for each one the design has:
  - Padding is per side and often asymmetric (`0/16/0/0` = right padding only); gaps come from the parent's item spacing (`0` is real). Auto-layout has no margins.
  - Corner radius is per corner, stroke weight per side (`bottom: 1` = bottom border only) — don't round or border the whole box.
  - Shadows/blur (effects), gradients, layer opacity, blend modes, rotation, clipping (`overflow-hidden`).
  - Hidden layers: don't render them (they're usually other states).
  - Text: letter spacing, text case, decoration, truncation/line clamp.
  - Tables / column lists: each column's alignment (numbers are often right-aligned) — header and cells share it, so align both. Take each column's width from the design, wide enough for its widest cell *including the header*; a `nowrap` header wider than its grid track overflows and breaks the alignment.
  - Flex children: grow (`flex-1`), stretch (`self-stretch`), absolute-positioned inside auto-layout, wrap.

**Existing-project rules** (all mandatory):
1. **Reuse existing components** wherever one fits; record each one's name and file path for the report.
2. **Consistency across pages** — the same UI element uses the same component everywhere; don't create a near-duplicate of one that already exists. If the design differs slightly, extend the existing component via props/variants rather than forking it.
3. **Don't break existing code** — never change an existing component's default behavior or public props in a breaking way; add optional props/variants instead. Run the project's typecheck, lint, and tests afterwards and fix anything you broke.
4. **Not feasible with the existing code?** (e.g. the component library can't do it, a needed dependency conflicts, it would require a breaking change) → stop on that part, tell the user **why**, and offer 1–3 alternatives (closest match with existing components, extend component X, add library Y) before proceeding.
5. **Off-theme design** (colors, fonts, spacing, radii not in the project's theme/tokens) → tell the user each deviation. If the user chose "match Figma", put a comment in the code at that spot, e.g. `/* OFF-THEME: #3B5BDB not in theme tokens (closest: primary-600) — per Figma design */`. If they chose "snap to theme", use the closest token and list the Figma value vs token used in the report.

## 5. Verify

- Serve it and screenshot at the frame's size (Playwright, viewport = frame width, `deviceScaleFactor` = the frame PNG's scale, clipped to the frame height).
- **Pixel diff** — `node <this-skill-dir>/scripts/visual_diff.mjs <frame.png> <build.png> <diff.png>` (first run installs its two deps into the script's folder, not the project). It prints the mismatch % and writes a diff image with changed pixels in red; open the diff to see *where* the build drifts, then measure those spots. It refuses images of different sizes instead of resizing — fix the screenshot size, don't scale. Expect a few % from font rendering and live data; re-run after fixes to confirm the number drops. **Measure** key boxes with `getBoundingClientRect()` rather than eyeballing — the browser may be zoomed (`devicePixelRatio ≠ 1`), which makes screenshots look off.
- Compare with the frame render: layout, alignment, colors, asset positions/sizes. For every table/column, compare the header's and cells' left **and** right edges with the render — right-aligned columns only show up on the right edge. Fix mismatches in scope; list out-of-scope ones without changing them.
- If responsive, screenshot each screen size the user gave; check one interaction (e.g. empty-submit validation).
- Grep the new/changed files for hex colors and `px` literals; each one must map to a token or be a reported off-theme value.
- Clean up: stop any server you started, delete temp downloads/screenshots, don't commit unless asked.

## 6. Report

What was built and where, which source was used (official MCP, `figma-view`, or LLM Export payload) and why, what's not wired (e.g. no real API call), and any remaining differences from the design.

**Placeholders** (if any): a table of filename, size, Figma node id — the user exports each from Figma under that exact filename to replace it, no code change needed.

Existing project — also list:
- **Reused components**: name + path for each.
- **New / extended components**: what was added and why no existing one fit.
- **Off-theme changes**: each deviation and where it's commented (or which token it was snapped to).
- **Inferred screen sizes**: any responsive size built without a Figma frame.
- **Not feasible**: what, why, and the alternative taken.
- Typecheck / lint / test results.
