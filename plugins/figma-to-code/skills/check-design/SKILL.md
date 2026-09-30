---
name: check-design
description: Check whether a page that already exists matches its Figma frame, without writing any code. Use when the user gives a Figma link (or an LLM Export `.json`) plus a URL of a running page and asks to check, compare, diff, or QA it against the design. Screenshots the page, pixel-diffs it against the frame render, and reports where and how much it drifts.
---

# Check a page against Figma

Input (`$ARGUMENTS`): a Figma frame link or an LLM Export `.json` file, and a page URL (e.g. `http://localhost:3000/signin`, a staging URL). Missing either one → ask for it. **Read-only**: never edit the project; this skill reports.

Scripts live in `<this-skill-dir>/../implement-design/scripts/`.

## 1. Get the frame render

Only the whole-frame PNG is needed, no layout tree or assets.

- **LLM Export bundle** (no quota): `python3 <scripts>/split_payload.py <bundle.json> <tmp-dir>`; the PNG of the top-level node is the render.
- **Figma link**: parse it the same way `implement-design` step 1 does (`node-id=223-141` → `223:141`, branch URLs use `branchKey`). Before the call, run `python3 <scripts>/figma_usage.py summary` and tell the user the cost: *"This check = 1 Tier-1 request. Logged here in the last 30 days: N."* Near or past 20 → offer an LLM Export bundle instead (steps are in the README). Then fetch the render with the official MCP's `get_screenshot` if installed, else `figma-view` `download_figma_images` (whole frame, `pngScale: 1`, into a temp folder in the directory Claude Code was started in). Log it afterwards, success or failure: `python3 <scripts>/figma_usage.py log <figma-view|official-mcp> <tier1|mcp> 1 <fileKey>`.
- Errors (403, 404, 429) → handle as `implement-design`'s gate table says. Never retry on your own.

## 2. Screenshot the page

Needs a Playwright MCP; none → stop and say so, since eyeballing isn't a check.

- Read the frame PNG's size. Viewport width = PNG width ÷ scale (scale 1 unless the export said otherwise), `deviceScaleFactor` = scale, full-page screenshot clipped to the PNG's height. The diff script refuses mismatched sizes; fix the screenshot, never resize.
- Page needs login, data, or a state (modal open, tab selected) to look like the frame → ask the user how to get there, then do it before the screenshot.
- Page not reachable → stop; ask the user to start the app. Don't start servers you weren't asked to.

## 3. Diff

```bash
node <scripts>/visual_diff.mjs <frame.png> <page.png> <diff.png>
```

Open the diff image: red pixels show *where* it drifts. For each red area, measure the element with `getBoundingClientRect()` and computed styles, and compare with the frame (position, size, color, font, spacing, radius). A few % comes from font rendering and live data; say which areas are that.

## 4. Report

- Mismatch % and the diff image path (keep the three PNGs in a temp folder; tell the user where).
- A table of real differences: element, what the design has, what the page has (measured values, not guesses), likely cause.
- What was noise (font anti-aliasing, live data, dynamic dates) and why.
- Nothing is fixed. Offer to fix it with `/implement-design` on the same link.

Delete the temp folder only if the user says so; the diff image is the evidence.
