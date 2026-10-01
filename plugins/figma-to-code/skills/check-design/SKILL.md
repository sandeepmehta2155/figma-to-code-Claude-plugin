---
name: check-design
description: Check whether a page that already exists matches its Figma frame, without writing any code. Use when the user gives a Figma link (or an LLM Export `.json`) plus a URL of a running page and asks to check, compare, diff, or QA it against the design. Screenshots the page, pixel-diffs it against the frame render, and reports where and how much it drifts.
---

# Check a page against Figma

Input (`$ARGUMENTS`): a Figma frame link or an LLM Export `.json` file, and a page URL (e.g. `http://localhost:3000/signin`, a staging URL). Missing either one → ask for it. **Read-only**: never edit the project; this skill reports.

Scripts live in `<this-skill-dir>/../implement-design/scripts/`.

## 1. Open the page first

Opening the page costs nothing, so do it before any Figma request. Use the Playwright MCP this plugin ships. If the user also runs their own Playwright server, use this plugin's: it emulates the 2x display screenshots need.

- The browser won't start → stop and give the fix: install Google Chrome, or run `npx -y @playwright/mcp@0.0.83 install-browser chromium` once and add `export PLAYWRIGHT_MCP_BROWSER=chromium` to the shell profile, then restart Claude Code. Eyeballing isn't a check.
- Page not reachable → stop; ask the user to start the app. Don't start servers you weren't asked to.
- The page needs a login → ask the user how, and log in.

## 2. Get the frame render

Only the whole-frame PNG is needed, no layout tree or assets. Keep every file of this check (render, screenshot, diff) in `.figma-check/`, in the directory Claude Code was started in: the Playwright MCP and `figma-view` can write only there.

- **LLM Export bundle** (no quota): `python3 <scripts>/split_payload.py <bundle.json> .figma-check`. The PNG of the top-level node is the render, at scale 2.
- **Figma link**: parse it the same way `implement-design` step 1 does (`node-id=223-141` → `223:141`, branch URLs use `branchKey`). Before the call, run `python3 <scripts>/figma_usage.py summary` and tell the user the cost: *"This check = 1 Tier-1 request. Logged here in the last 30 days: N."* Near or past 20 → offer an LLM Export bundle instead (steps are in the README).
  - Fetch the render at scale 1. If the official MCP is installed, use its `get_screenshot` with `contentsOnly: true` (the frame alone, like the other sources) and a `maxDimension` above the frame's long edge (e.g. 16384; the default 1024 shrinks it), and curl the PNG into `.figma-check/`. Otherwise use `figma-view` `download_figma_images` (whole frame, `pngScale: 1`, into `.figma-check/`).
  - Log it afterwards, success or failure: `python3 <scripts>/figma_usage.py log <figma-view|official-mcp> <tier1|mcp> 1 <fileKey>`.
- Errors (403, 404, 429) → handle as `implement-design`'s gate table says. Never retry on your own.

## 3. Screenshot the page

- **Frame size**, never the PNG's (a drop shadow makes the render larger):
  - bundle: the top-level node's width and height in `payload.json`;
  - Figma link: `node <scripts>/visual_diff.mjs --frame <frame.png> --scale=1`.
- In the MCP's own tab, `browser_resize` to the frame's CSS width × a real screen height: the frame's height, capped at 1080 (844 for frames under 768px wide). A tab as tall as a long frame would stretch `vh`/`dvh`/`h-screen` sections. Then bring the page into the frame's state (modal open, tab selected): compare with the render, and ask the user how to get there if it isn't clear.
- Call `browser_take_screenshot` with `fullPage: true` and the relative `filename` `.figma-check/page.png`. Use `scale: "device"` for a 2x render or `"css"` for 1x. If the shot comes back only screen-tall while the frame is taller (the page scrolls inside a container), resize to the frame's height and shoot again.
- The diff script refuses mismatched sizes; fix the screenshot, never resize.

## 4. Diff

```bash
node <scripts>/visual_diff.mjs <frame.png> <page.png> <diff.png> --scale=<scale>
```

The script crops a shadowed render to its frame. When the page runs past or ends above the frame's bottom, it compares only the height both cover and says so. It prints the mismatch %, then lists the areas that differ most: 160px cells ranked by the share of 8px blocks that changed, with the median cell as the noise floor.

- Work the worst cells first. Find each cell's element with one `browser_evaluate`: `scrollTo(0, y - 100)`, then `document.elementsFromPoint` at the cell's red spots (start from its center, x + 80 and y + 80 - `scrollY`), plus `getBoundingClientRect()` (page position = its top + `scrollY`) and computed styles. Then compare it with the frame: position, size, color, font, spacing, radius. Count positions on the render from the frame's own corner, which `--frame` prints.
- Cells near the median are font rendering or live data. Still check asset sizes and text widths there, because a smaller logo barely moves its cell.
- Open the diff image to see the shape of each difference (red = changed).

## 5. Report

- Mismatch % and the diff image path (the three PNGs stay in `.figma-check/`; tell the user where).
- A table of real differences, worst area first: element, what the design has, what the page has (measured values, not guesses), likely cause.
- What was noise (font anti-aliasing, live data, dynamic dates) and why.
- Nothing is fixed. Offer to fix it with `/implement-design` on the same link: it finds the existing page and fixes it with the user in rounds.

Delete `.figma-check/` only if the user says so; the diff image is the evidence.
