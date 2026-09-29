# tops-figma — Claude Code marketplace

One plugin, `figma-to-code`: paste a Figma frame link, get code in your project.

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

## Layout

```
.claude-plugin/marketplace.json
plugins/figma-to-code/
  .claude-plugin/plugin.json
  .mcp.json                         # figma-view = figma-developer-mcp (pinned)
  skills/implement-design/SKILL.md  # the workflow
```
