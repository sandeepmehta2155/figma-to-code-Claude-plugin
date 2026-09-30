# shadcn/ui rules

Read this index only when the project has a `components.json`. Open a file only when it applies.

| File | Read when |
|---|---|
| `rules/styling.md` | always — semantic colors, built-in variants first, `className` for layout only, `cn()`, no manual `dark:` overrides |
| `rules/composition.md` | mapping Figma instances to shadcn components instead of custom markup |
| `customization.md` | a Figma color/radius/font isn't in the theme — add it as a CSS variable the shadcn way |
| `rules/forms.md` | the design has inputs, selects, checkboxes, validation states |
| `rules/icons.md` | placing icons inside buttons, inputs, menus |
| `rules/base-vs-radix.md` | `components.json` shows which primitive library the project uses and an API differs |
| `rules/chat.md` | the design is a chat / messaging UI |

A Figma instance whose component isn't in the project yet → add it with the project's package runner (`npx shadcn@latest add <name>`, `pnpm dlx shadcn@latest add <name>`, or `bunx --bun shadcn@latest add <name>`), then style it through its variants — don't hand-build a lookalike.

## Source

Copied unmodified from [shadcn-ui/ui](https://github.com/shadcn-ui/ui) at commit `71f0e49` (2026-09-30): `skills/shadcn/rules/*.md` and `skills/shadcn/customization.md`. MIT License, © shadcn. Links to the upstream `SKILL.md`, `cli.md` and `registry.md` weren't copied. To update, re-copy the same files from a newer commit.
