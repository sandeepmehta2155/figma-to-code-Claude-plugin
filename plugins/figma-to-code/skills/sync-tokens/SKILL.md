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
| **LLM Export bundle** (recommended) | yes | all (`variables[]` has per-mode values) | none |
| Official Figma MCP `get_variable_defs(fileKey, nodeId)` | yes | the frame's current mode only | 1 MCP call |
| `figma-view` MCP | no (REST variables need Enterprise) | — | — |

- **Bundle**: `python3 <scripts>/split_payload.py <bundle.json> <tmp-dir>`, read `<tmp-dir>/payload.json`'s `variables[]`. The bundle only carries variables the exported selection uses: select the whole page or a frame that uses the full theme (a style guide frame, if the file has one) to get everything.
- **Link**: official MCP installed → show the cost first (`python3 <scripts>/figma_usage.py summary`, *"This sync = 1 MCP call. Logged here in the last 30 days: N."*), call `get_variable_defs`, then log it: `python3 <scripts>/figma_usage.py log official-mcp mcp 1 <fileKey>`. Only one mode comes back, so say that dark mode (etc.) won't be synced and offer a bundle instead.
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

- **Name**: the leaf of `Collection/group/name` in kebab-case (`Theme/Text/Primary` → `text-primary`). Two variables with the same leaf in different collections/groups → keep the group (`button-text-primary`) and list the collision.
- **Kind**: Figma `COLOR` → `--color-*`. `FLOAT` → by name/scope: radius → `--radius-*`, spacing/gap/padding → `--spacing-*`, font size → `--text-*`, line height → `--leading-*`, letter spacing → `--tracking-*`, weight → `--font-weight-*`. `STRING` font family → `--font-*`. Unclear → ask, don't guess. `FLOAT` px → `rem` only if the project's tokens use rem.
- **Modes**: the default/light mode goes in `:root`, a dark mode in the project's dark selector; other modes (brands, densities) → ask which selector.
- **Aliases**: a variable that points at another variable → `var(--that-token)`, not its resolved value, so the chain survives.

## 4. Diff, then ask

Compare against what the project has and show one table: token, Figma value(s), project value(s), status:

- **new**: in Figma, not in the project
- **changed**: same name, different value (show both)
- **same**: no change (count only, don't list)
- **project-only**: in the project, not in this Figma data. **Never delete.** List it; it may just be outside the exported selection.

Ask with AskUserQuestion: apply new + changed (Recommended) / new only / pick per token / stop. Nothing is written before the answer.

## 5. Apply and check

- Edit the source from step 2. Keep the file's order and comments; add new tokens next to their group.
- Run the token build (if any), then the project's typecheck/lint/build. Show the result.
- Report: what was added and changed (file:line), collisions, project-only tokens, modes not synced, and the source used. Changed values restyle every screen that uses them; say so. Don't commit unless asked.
