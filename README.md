# tops-figma — Claude Code marketplace

One plugin, `figma-to-code`: paste a Figma frame link, get code in your project.

```
Figma file ──▶ official Figma MCP (needs edit access, plan quota)
          └──▶ figma-view MCP (fallback: view access + API token)
                    ▼
             Claude Code  /figma-to-code:design-to-code <link>
                    ▼
             your project (Next.js, …) or standalone HTML
```

## Install

1. Create a Figma personal access token (Figma → Settings → Security → Personal access tokens, read-only file scope is enough) and export it in your shell profile:
   ```bash
   export FIGMA_API_KEY=figd_...
   ```
2. In Claude Code:
   ```
   /plugin marketplace add <path-or-git-url-of-this-repo>
   /plugin install figma-to-code@tops-figma
   ```
3. Optional but recommended: also install the official Figma plugin (`/plugin install figma@claude-plugins-official`) — used first when you have edit access.

## Use

```
/figma-to-code:design-to-code https://www.figma.com/design/<fileKey>/<name>?node-id=1-2
```
Add the target if it isn't obvious: "…into apps/admin, route /signin" or "…as standalone HTML".

## Layout

```
.claude-plugin/marketplace.json
plugins/figma-to-code/
  .claude-plugin/plugin.json
  .mcp.json                         # figma-view = figma-developer-mcp (pinned)
  skills/design-to-code/SKILL.md    # the workflow
```
