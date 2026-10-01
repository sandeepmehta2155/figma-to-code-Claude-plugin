# Review rounds (implement-design step 5)

The build is reviewed with the user in rounds. Nothing is changed toward the frame unless the user picked it. Rounds make no Figma calls: they reuse the frame render the gate downloaded.

No browser (Verify ⚠ in the gate): don't serve or screenshot. Run only round 1's two file checks (library controls; hex and `px` literals), and report the build as not visually checked.

## Each round

1. **Screenshot** in the Playwright MCP's own tab, so the page keeps its login and state and the measurements below see the same layout. This plugin's server emulates a 2x display.
   - `browser_resize` the tab to the frame's CSS width × a real screen height: the frame's height, capped at 1080 (844 for frames under 768px wide), or the screen size the user gave. A tab as tall as a long frame would stretch `vh`/`dvh`/`h-screen` sections. Take the frame's size from the design data, never from the PNG: a drop shadow makes the render larger.
   - Open the page with `browser_navigate` if it isn't open, and bring it into the frame's state (modal open, tab selected).
   - Call `browser_take_screenshot` with `fullPage: true` and a relative `filename` such as `.figma-check/round-1.png`: this MCP writes only inside the directory Claude Code was started in. Use `scale: "device"` for a 2x render (LLM Export) or `"css"` for a 1x render (`figma-view`, official `get_screenshot`).
   - If the shot comes back only screen-tall while the frame is taller (the page scrolls inside a container), resize the tab to the frame's height and shoot again.
2. **Diff**: `node <this-skill-dir>/scripts/visual_diff.mjs <frame.png> <build.png> <diff.png> --scale=<render scale>`. The first run installs its two deps into the script's folder, not the project. The script:
   - crops a shadowed render to its frame, and compares only the height both cover when the page runs past or ends above the frame's bottom (it says which);
   - prints the mismatch % (expect a few % from font rendering and live data);
   - writes a diff image with changed pixels in red;
   - lists the areas that differ most (160px cells, with the median cell as the noise floor).

   It refuses images of different sizes: fix the screenshot, never resize. The % shows the trend, and the area table and diff image show where to look. Neither one decides a finding.
3. **Measure, in the same tab**, rather than eyeball. Run one `browser_evaluate` over a fixed list of elements, keyed by text or selector, and run the same call every round. Return `getBoundingClientRect()` (page position = its top + `scrollY`) plus computed font, color and spacing. Compare with the design:
   - **sizes, paddings, gaps, fonts, colors**: from the node data;
   - **positions**: measured on the frame render, counted from the frame's own top-left corner (for a shadowed render, `visual_diff.mjs` prints where the frame sits). Never add up bundle x/y: a group's children are already in the enclosing frame's coordinates, flipped layers report a moved origin, and the top frame's x/y is its canvas position.

   **Round 1 also checks**:
   - every table or column: the header's and cells' left **and** right edges against the render (right-aligned columns only show up on the right edge);
   - each screen size the user gave, if responsive, plus one interaction (e.g. empty-submit validation);
   - the new or changed files, for `<select`, `<dialog`, `<input type="checkbox|radio|range|date"` and click-toggled `div` menus: each must be a library component (step 4);
   - every dropdown, menu and dialog, opened once and screenshotted open: the closed state hides a native or unstyled popup;
   - the new or changed files, for hex colors and `px` literals: each maps to a token or is a reported off-theme value.
4. **Group findings by root cause.** For example, one label that wraps and pushes ten cards down is one finding, not ten. Severity:
   - **High**: layout or alignment: position or size, wraps, misaligned columns, missing or extra elements, native controls.
   - **Med**: spacing, color, font, radius.
   - **Low**: off by 1–2px.
5. **Show one table** with these columns: #, severity, element, design, build (measured), cause, status (open / fixed / accepted / design issue). Restate the whole table every round: it is the loop's memory.
6. **Ask** with one AskUserQuestion call:
   - "Round N: what should I fix?" Options: **Fix all High** / **High + Med** / **Let me choose** (the user names the numbers) / **Stop**.
   - Only when there are suspects, a multiSelect question: "These look like mistakes in the frame itself. Mark them as design issues?" Use one option per suspect, at most 4; the rest wait for the next round. With a single suspect, ask **Yes, a design issue** / **No, match the frame** instead.
7. **Fix only the picked findings**, then start the next round.

## Design issues

Sometimes the frame contradicts itself: cells of one auto-layout row sit at different heights, identical cards are spaced differently, or a label can't fit its box. Don't copy that into the build.
- Build the consistent version and propose each one as a suspect.
- Once the user confirms it, it's a design issue: accepted, kept as built, and never offered again.

Data oddities are different: an unsorted ranking, a duplicate row, or an item in the wrong list is copied as shown (step 4's mock data rule) and listed under Design data notes.

## Accepted differences

These are accepted and never offered again; list each once with its reason:
- confirmed design issues;
- out of scope: parts this run didn't build, such as the app's shared layout, header or nav around a new screen. Change one only if the user names its number;
- the inside of data-drawn widgets (charts and maps decided in step 2);
- live data;
- font rendering: areas at the noise floor with no measured difference.

## Stop

Stop when any of these happens:
- the user picks Stop;
- nothing open is left;
- 5 rounds are done;
- 2 rounds in a row closed nothing (the fixes aren't landing).

If the last round changed code, run steps 1–3 once more without asking, so the final % and table match what ships. Then stop any server you started, delete `.figma-check/` and the temp downloads, and don't commit unless asked.

In the report, include:
- how many rounds ran and the mismatch % after each;
- what was fixed and the accepted differences;
- the design issues and the Design data notes, as a ready-to-paste list for the designer: node name, what's inconsistent, and what the build does instead.
