# Tailwind v4 tokens

Tailwind v4 is configured in CSS, not `tailwind.config.js`. Spot it by `@import "tailwindcss"` in the main CSS file. A project on v3 (a `tailwind.config.*` with `theme.extend`, no `@theme`) keeps adding tokens there. Never migrate a project between versions as part of a design build.

## Figma variable → utility class, in three layers

```css
@import "tailwindcss";

/* 1. The value, per mode — top level, not inside @layer */
:root {
  --text-primary: oklch(0.21 0.03 265);   /* Figma: Theme/text-primary, light */
}
.dark {
  --text-primary: oklch(0.97 0 0);        /* same variable, dark mode */
}

/* 2. Expose it to Tailwind */
@theme inline {
  --color-text-primary: var(--text-primary);
}

/* 3. Use it: text-text-primary, bg-text-primary, border-text-primary … */
```

- The `@theme` prefix decides which utilities exist: `--color-*` (bg/text/border/fill…), `--font-*` (font family), `--text-*` (font size), `--font-weight-*`, `--tracking-*`, `--leading-*`, `--radius-*`, `--shadow-*`, `--spacing` / `--spacing-*`, `--breakpoint-*`. Put a Figma radius variable under `--radius-*`, not `--color-*`.
- Use `@theme inline` when the value is a `var()`. Plain `@theme` resolves the variable where it's defined, so the `.dark` override never reaches the utility.
- Modes live in `:root` / `.dark` (or the project's own theme selector). Don't put `@theme` inside `.dark`: it's only valid at the top level.
- Store full colors in the variables (`oklch(…)`, `hsl(…)`, `#hex`) and use them as `var(--x)`. Don't wrap again with `hsl(var(--x))`; that pattern is only for older setups that store bare channel numbers. Follow whichever format the project already uses.
- One class per token. The theme switch swaps the variable, so never add `dark:` color overrides next to a semantic token.
- No token matches and the user chose "match Figma" → an arbitrary value (`bg-[#3B5BDB]`) with the OFF-THEME comment, not a new token.

## Source

Distilled from [secondsky/claude-skills `tailwind-v4-shadcn`](https://github.com/secondsky/claude-skills/tree/8837836/plugins/tailwind-v4-shadcn/skills/tailwind-v4-shadcn) (MIT, © 2025 Claude Skills Maintainers), commit `8837836`. Its setup steps are left out, as is its advice to delete `tailwind.config.*` and avoid `@apply`: both are wrong for existing projects.
