---
name: sync-tokens
description: Sync Figma variables (design tokens) into the current project's theme — Tailwind v4 `@theme`, Tailwind v3 config, plain CSS variables, or Style Dictionary / Tokens Studio JSON. Use when the user asks to sync, import, pull, or update design tokens / variables / theme colors from Figma, with a Figma link or an LLM Export `.json`. Shows a diff and asks before writing; never deletes project tokens.
---

# Figma variables → project tokens

Input (`$ARGUMENTS`): an LLM Export `.json` bundle (preferred) or a Figma frame link. Scripts live in `<this-skill-dir>/../implement-design/scripts/`.

## 1. Get the variables, with names

Tokens are synced **by name**; a value without a name can't become a token.

| Source | Names | Modes | Quota |
|---|---|---|---|
| **LLM Export bundle** (recommended) | yes | all | none |
| Official Figma MCP `get_variable_defs(fileKey, nodeId)` | yes | the frame's current mode only | 1 MCP call |
| `figma-view` MCP | no (REST variables need Enterprise) | — | — |

- **Bundle**: run `python3 <scripts>/split_payload.py <bundle.json> <tmp-dir>`, then read `<tmp-dir>/variables.json`.
  - `"source": "collections"` is the whole theme: every variable of the collections ticked under **Variable collections to export** in LLM Export, in every mode.
  - `"source": "selection"` holds only the variables the exported frame uses. Say so, and offer a re-export with the theme's collections ticked (LLM Export remembers the pick).
  - `"usedOnly": true` marks a variable the frame uses that isn't in a ticked collection: from a library, an unticked collection, or deleted but still bound. List these separately and sync them only if the user says so.
  - LLM Export lists only the file's own collections. For a theme that comes from a team library, run LLM Export in the library file (or a copy of it).
- **Link**: official MCP installed → before calling, run `python3 <scripts>/figma_usage.py summary` and ask with AskUserQuestion: *"This sync = 1 MCP call and returns only the frame's current mode, so dark mode (etc.) won't sync. Logged here in the last 30 days: N."* Options: use the link / use an LLM Export bundle (every mode, no quota; steps in the README). Skip the question if the user already said. On the link, call `get_variable_defs`, then log it: `python3 <scripts>/figma_usage.py log official-mcp mcp 1 <fileKey>`.
- **No official MCP** → there are no names to sync. Stop and give the LLM Export steps from the README. Don't invent names from values.

## 2. Find the project's token source

Write to the source, never to generated output. First match wins:

1. Style Dictionary / Tokens Studio: `$value` JSON token files, a `style-dictionary` build script → edit the JSON, then run the build.
2. Tailwind v4 (`@import "tailwindcss"` in CSS) → read `<this-skill-dir>/../implement-design/references/tailwind-v4.md` and follow its three layers (values per mode in `:root` / the dark selector, exposed through `@theme inline`).
3. Tailwind v3 (`tailwind.config.*` with `theme.extend`) → add to `theme.extend`, pointing at CSS variables if the project already does that.
4. Plain CSS variables in `:root` → add there.
5. None of these → ask where tokens should go. Don't set up a token pipeline unasked.

Use the project's existing conventions: color format (`oklch` / `hsl` / hex), naming (kebab-case), dark-mode selector (`.dark`, `[data-theme="dark"]`, `prefers-color-scheme`).

## 3. Map

- **Name**: the designer's own CSS name when `codeSyntax.WEB` is set (`var(--brand-primary)` → `brand-primary`). Otherwise use the leaf of `Collection/group/name` in kebab-case (`Theme/Text/Primary` → `text-primary`). When two variables share a leaf:
  - in different groups → keep the group (`button-text-primary`);
  - with the same name in two collections but different values → keep the collection too (`DS/status/critical` → `ds-status-critical`); with the same value → one token.

  List each collision.
- **Kind**: use `scopes` when they're specific:
  - `CORNER_RADIUS` → `--radius-*`
  - `GAP` → `--spacing-*`
  - `FONT_SIZE` → `--text-*`
  - `LINE_HEIGHT` → `--leading-*`
  - `LETTER_SPACING` → `--tracking-*`
  - `FONT_WEIGHT` → `--font-weight-*`; `FONT_STYLE` too, with the style name turned into its number (`Semi Bold` → 600)
  - `FONT_FAMILY` → `--font-*`
  - fill, stroke and text-fill scopes → `--color-*`

  For `ALL_SCOPES` or no scopes, go by type and name:
  - Figma `COLOR` → `--color-*`.
  - `FLOAT` → radius → `--radius-*`, spacing/gap/padding → `--spacing-*`, font size → `--text-*`, line height → `--leading-*`, letter spacing → `--tracking-*`, weight → `--font-weight-*`.
  - `STRING` font family → `--font-*`.

  Unclear → ask, don't guess. `FLOAT` px → `rem` only if the project's tokens use rem. A variable's `description` becomes a comment next to its token.
- **Modes**: the default/light mode goes in `:root`, a dark mode in the project's dark selector; other modes (brands, densities) → ask which selector.
- **Aliases**: a variable that points at another variable → `var(--that-token)`, not its resolved value, so the chain survives. When its target is neither synced nor in the project, use the alias's `value`, or, if the target is a skipped `usedOnly` entry, that variable's own value (its first mode).

## 4. Diff, then ask

Compare against what the project has and show one table: token, Figma value(s), project value(s), status:

- **new**: in Figma, not in the project
- **changed**: same name, different value (show both)
- **same**: no change (count only, don't list)
- **project-only**: in the project, not in this Figma data. **Never delete.** List it; it may just be outside the exported selection or the ticked collections.

Ask with AskUserQuestion: apply new + changed (Recommended) / new only / pick per token / stop. Nothing is written before the answer.

## 5. Apply and check

- Edit the source from step 2. Keep the file's order and comments; add new tokens next to their group.
- Run the token build (if any), then the project's typecheck/lint/build. Show the result.
- Report: what was added and changed (file:line), collisions, project-only tokens, modes not synced, and the source used. Changed values restyle every screen that uses them; say so. Don't commit unless asked.
