# tops-figma — Claude Code marketplace

One plugin, `figma-to-code`: paste a Figma frame link, get code in your project. It can also check an existing page against its Figma frame and sync Figma variables into your theme.

```
Figma file ──▶ official Figma MCP (needs edit access, plan quota)
          └──▶ figma-view MCP (fallback: view access + API token)
                    ▼
             Claude Code  /implement-design <link>
                    ▼
             your project (Next.js, …) or standalone HTML
```

## Install

Everyone needs their own Figma token first:
```bash
export FIGMA_API_KEY=figd_...     # add this line to ~/.bashrc or ~/.zshrc
```
Then, inside Claude Code:
```
/plugin marketplace add sandeepmehta2155/figma-to-code-marketplace
/plugin install figma-to-code@tops-figma
```
Or from the terminal:
```bash
claude plugin marketplace add sandeepmehta2155/figma-to-code-marketplace
claude plugin install figma-to-code@tops-figma
```
If the repo is private, each user needs read access to it on GitHub, plus working `git` credentials (SSH key or `gh auth login`).

## Use

```
/implement-design https://www.figma.com/design/<fileKey>/<name>?node-id=1-2
```
Add the target if it isn't obvious: "…into apps/admin, route /signin" or "…as standalone HTML".

### Check a page against Figma

```
/check-design https://www.figma.com/design/<fileKey>/<name>?node-id=1-2 http://localhost:3000/signin
```
Screenshots the running page at the frame's size, pixel-diffs it against the Figma render, and reports each difference with measured values. Changes no code. Costs 1 Figma request (none with an LLM Export bundle). Needs a Playwright MCP.

### Sync design tokens

```
/sync-tokens ~/Downloads/<bundle>.json
```
Brings Figma variables into the project's theme (Tailwind v4 `@theme`, Tailwind v3 config, CSS variables, or Style Dictionary / Tokens Studio JSON). Shows new / changed / project-only tokens and asks before writing; never deletes a token. Use an LLM Export bundle: it's the only source with variable names and every mode (light and dark). A Figma link works with the official Figma MCP, but it only returns the current mode. Export a frame that uses the whole theme, since the bundle only has the variables its selection uses.

### No MCP quota? Export from inside Figma instead

The [LLM Export](https://github.com/Gamma-Software/figma-llm-export) Figma plugin (MIT) reads the design through Figma's plugin API: no token, no rate limit, any plan, and it includes **variable (token) names**, which the REST API only gives on Enterprise. Plugins generally need edit access, so work in a file you can edit (if you only have view access, duplicate the file to your drafts, when the owner allows copying).

`/implement-design` offers this automatically when you give it a Figma link. To do it by hand:

1. First time only, if **LLM Export** isn't in Figma's Actions menu: `git clone https://github.com/Gamma-Software/figma-llm-export && cd figma-llm-export && npm install && npm run build`, then Figma desktop → Plugins → Development → Import plugin from manifest… → pick its `manifest.json`.
2. Select the frame → Actions (`Ctrl/⌘ + /`) → **LLM Export** → **Download LLM bundle** (not "Download JSON", which drops the images). It has also shown up in the browser's Actions menu after being set up.
3. `/implement-design ~/Downloads/<bundle>.json`

## Layout

```
.claude-plugin/marketplace.json
plugins/figma-to-code/
  .claude-plugin/plugin.json
  .mcp.json                         # figma-view = figma-developer-mcp (pinned)
  skills/implement-design/SKILL.md  # the workflow
  skills/check-design/SKILL.md      # Figma frame vs a running page, report only
  skills/sync-tokens/SKILL.md       # Figma variables → project theme
  skills/implement-design/scripts/split_payload.py  # LLM Export bundle → JSON + image files
  skills/implement-design/references/react/         # React/Next.js rules (from vercel-labs/agent-skills, MIT)
  skills/implement-design/references/shadcn/        # shadcn/ui rules (from shadcn-ui/ui, MIT)
  skills/implement-design/references/tailwind-v4.md # Tailwind v4 token mapping
  skills/implement-design/scripts/visual_diff.mjs   # pixel diff: Figma render vs build (pixelmatch, ISC)
  skills/implement-design/scripts/figma_usage.py    # local tally of Figma requests (~/.figma-to-code/usage.jsonl)
```
