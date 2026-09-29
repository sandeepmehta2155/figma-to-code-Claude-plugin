---
name: implement-design
description: Implement a Figma frame as code in the current project (or as standalone HTML). Use when the user pastes a figma.com design/proto link and asks to build, implement, or convert it. Uses the official Figma MCP when it has access, falls back to the view-access `figma-view` MCP when the file is view-only or the Figma plan's MCP quota is spent.
---

# Figma → code

Input: a Figma URL (`$ARGUMENTS`), plus optionally a target (app path, route, or "standalone HTML").

## 1. Parse the link

- `figma.com/design/<fileKey>/…` and `figma.com/proto/<fileKey>/…` both work.
- `figma.com/design/<fileKey>/branch/<branchKey>/…` → use `branchKey` as the file key.
- `node-id=223-141` → node `223:141`. No `node-id` → ask for a frame link (right-click frame → Copy link to selection). Never guess a node.

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

**Official Figma MCP** (tools named `…figma…get_design_context`, from the official `figma` plugin), if installed:
- `get_design_context(fileKey, nodeId)` with the screenshot included.
- `get_variable_defs(fileKey, nodeId)` → the Figma variables (design tokens) the frame uses, by name.
- If it errors with **"don't have edit access"** or a **rate limit**: do NOT retry it — each call spends the user's monthly quota (Starter/View/Collab seats get very few). Go to the fallback.

**Fallback: `figma-view` MCP** (this plugin; needs only view access + `FIGMA_API_KEY`):
- `get_figma_data(fileKey, nodeId)` → layout tree, text, colors, fonts, spacing, radii, shadows.
- `download_figma_images` — it can only write inside the directory Claude Code was started in, so download into the project's asset dir (e.g. `public/images/…`) or a temp dir you delete afterwards. Fetch:
  - the **whole frame** as PNG (`pngScale: 1`) → the visual target, kept out of the project;
  - every `IMAGE` fill node, passing its `imageRef`;
  - every `IMAGE-SVG` node as `.svg` (logos, icons).
- Compress big photo exports before shipping (e.g. `cwebp -q 80 -resize 2560 0`).

## 4. Implement

- Build with the project's own stack: its components, tokens, form library, icon set, routing.
- **Tokens: map the variable, not the value.** Official path: map each Figma variable to the project token by name (`Theme/text-primary` → `--text-primary` / `text-text-primary`); the collection prefix is noise, the leaf name is the key. Bind the token, not the light/dark value — the app's theme switch handles modes. `figma-view` path has no variable bindings, so map by exact value instead. Either way, add a token only when none matches.
- **Instances → components.** A component instance's name and variant properties tell you which project component to use and which props to pass. Hidden sibling layers and other variants hint at hover/active/disabled/selected states — implement those states; selected vs unselected is one component with a prop, not two elements.
- Translate absolute positions into real layout (flex/grid). If responsive, make it work at every screen size the user gave.
- Wire the obvious interactions: inputs, submit, show/hide password, links (`<a href>` / framework `Link`, not click-handlers, for navigation).
- Use every asset in its design slot at its design size. Never redraw an exported asset; never ship a temporary Figma asset URL.
- **Trust the rendered frame over node properties.** Two traps seen in practice:
  - `textAlignHorizontal: CENTER` on a hug-width text node is invisible — the render shows the real alignment.
  - A background the project already has may be pre-composited (darkened) and not match the design's `IMAGE fill + opacity`. Compare against the render; prefer the design's own image.
- **Fidelity checklist** — details that routinely get dropped; account for each one the design has:
  - Padding is per side and often asymmetric (`0/16/0/0` = right padding only); gaps come from the parent's item spacing (`0` is real). Auto-layout has no margins.
  - Corner radius is per corner, stroke weight per side (`bottom: 1` = bottom border only) — don't round or border the whole box.
  - Shadows/blur (effects), gradients, layer opacity, blend modes, rotation, clipping (`overflow-hidden`).
  - Hidden layers: don't render them (they're usually other states).
  - Text: letter spacing, text case, decoration, truncation/line clamp.
  - Flex children: grow (`flex-1`), stretch (`self-stretch`), absolute-positioned inside auto-layout, wrap.

**Existing-project rules** (all mandatory):
1. **Reuse existing components** wherever one fits; record each one's name and file path for the report.
2. **Consistency across pages** — the same UI element uses the same component everywhere; don't create a near-duplicate of one that already exists. If the design differs slightly, extend the existing component via props/variants rather than forking it.
3. **Don't break existing code** — never change an existing component's default behavior or public props in a breaking way; add optional props/variants instead. Run the project's typecheck, lint, and tests afterwards and fix anything you broke.
4. **Not feasible with the existing code?** (e.g. the component library can't do it, a needed dependency conflicts, it would require a breaking change) → stop on that part, tell the user **why**, and offer 1–3 alternatives (closest match with existing components, extend component X, add library Y) before proceeding.
5. **Off-theme design** (colors, fonts, spacing, radii not in the project's theme/tokens) → tell the user each deviation. If the user chose "match Figma", put a comment in the code at that spot, e.g. `/* OFF-THEME: #3B5BDB not in theme tokens (closest: primary-600) — per Figma design */`. If they chose "snap to theme", use the closest token and list the Figma value vs token used in the report.

## 5. Verify

- Serve it and screenshot at the frame's size (Playwright). **Measure** key boxes with `getBoundingClientRect()` rather than eyeballing — the browser may be zoomed (`devicePixelRatio ≠ 1`), which makes screenshots look off.
- Compare with the frame render: layout, alignment, colors, asset positions/sizes. Fix mismatches in scope; list out-of-scope ones without changing them.
- If responsive, screenshot each screen size the user gave; check one interaction (e.g. empty-submit validation).
- Grep the new/changed files for hex colors and `px` literals; each one must map to a token or be a reported off-theme value.
- Clean up: stop any server you started, delete temp downloads/screenshots, don't commit unless asked.

## 6. Report

What was built and where, which MCP path was used (official or `figma-view`) and why, what's not wired (e.g. no real API call), and any remaining differences from the design.

Existing project — also list:
- **Reused components**: name + path for each.
- **New / extended components**: what was added and why no existing one fit.
- **Off-theme changes**: each deviation and where it's commented (or which token it was snapped to).
- **Inferred screen sizes**: any responsive size built without a Figma frame.
- **Not feasible**: what, why, and the alternative taken.
- Typecheck / lint / test results.
