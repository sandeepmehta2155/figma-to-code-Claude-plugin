---
name: design-to-code
description: Implement a Figma frame as code in the current project (or as standalone HTML). Use when the user pastes a figma.com design/proto link and asks to build, implement, or convert it. Uses the official Figma MCP when it has access, falls back to the view-access `figma-view` MCP when the file is view-only or the Figma plan's MCP quota is spent.
---

# Figma → code

Input: a Figma URL (`$ARGUMENTS`), plus optionally a target (app path, route, or "standalone HTML").

## 1. Parse the link

- `figma.com/design/<fileKey>/…` and `figma.com/proto/<fileKey>/…` both work.
- `figma.com/design/<fileKey>/branch/<branchKey>/…` → use `branchKey` as the file key.
- `node-id=223-141` → node `223:141`. No `node-id` → ask for a frame link (right-click frame → Copy link to selection). Never guess a node.

## 2. Decide the target before fetching much

- Read the target project's `package.json`, styling config (Tailwind config / CSS tokens), and component folders.
- **Search for an existing implementation first** (grep the design's headline text). If the screen already exists, report the diff against the design instead of building a second copy.
- Target unclear (several apps, or the design's brand doesn't match the repo) → ask once, offering: which app/route, or standalone HTML.

## 3. Fetch the design — official first, fallback second

**Official Figma MCP** (tools named `…figma…get_design_context`, from the official `figma` plugin), if installed:
- `get_design_context(fileKey, nodeId)` with the screenshot included.
- If it errors with **"don't have edit access"** or a **rate limit**: do NOT retry it — each call spends the user's monthly quota (Starter/View/Collab seats get very few). Go to the fallback.

**Fallback: `figma-view` MCP** (this plugin; needs only view access + `FIGMA_API_KEY`):
- `get_figma_data(fileKey, nodeId)` → layout tree, text, colors, fonts, spacing, radii, shadows.
- `download_figma_images` — it can only write inside the directory Claude Code was started in, so download into the project's asset dir (e.g. `public/images/…`) or a temp dir you delete afterwards. Fetch:
  - the **whole frame** as PNG (`pngScale: 1`) → the visual target, kept out of the project;
  - every `IMAGE` fill node, passing its `imageRef`;
  - every `IMAGE-SVG` node as `.svg` (logos, icons).
- Compress big photo exports before shipping (e.g. `cwebp -q 80 -resize 2560 0`).

## 4. Implement

- Build with the project's own stack: its components, tokens, form library, icon set, routing. Map Figma hex values onto existing tokens when they match exactly; add a token only when none matches.
- Translate absolute positions into real layout (flex/grid); make it responsive (check ~390px wide).
- Wire the obvious interactions: inputs, submit, show/hide password, links (`<a href>` / framework `Link`, not click-handlers, for navigation).
- Use every asset in its design slot at its design size. Never redraw an exported asset; never ship a temporary Figma asset URL.
- **Trust the rendered frame over node properties.** Two traps seen in practice:
  - `textAlignHorizontal: CENTER` on a hug-width text node is invisible — the render shows the real alignment.
  - A background the project already has may be pre-composited (darkened) and not match the design's `IMAGE fill + opacity`. Compare against the render; prefer the design's own image.

## 5. Verify

- Serve it and screenshot at the frame's size (Playwright). **Measure** key boxes with `getBoundingClientRect()` rather than eyeballing — the browser may be zoomed (`devicePixelRatio ≠ 1`), which makes screenshots look off.
- Compare with the frame render: layout, alignment, colors, asset positions/sizes. Fix mismatches in scope; list out-of-scope ones without changing them.
- Check the narrow (~390px) layout and one interaction (e.g. empty-submit validation).
- Clean up: stop any server you started, delete temp downloads/screenshots, don't commit unless asked.

## 6. Report

What was built and where, which MCP path was used (official or `figma-view`) and why, what's not wired (e.g. no real API call), and any remaining differences from the design.
