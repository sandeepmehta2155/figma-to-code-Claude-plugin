# React / Next.js rules

Read this index only for a React or Next.js build. Open a rule file only when it applies to the component you're writing.

## Components (from Figma instances and variants)

| Rule | Read when |
|---|---|
| `architecture-avoid-boolean-props.md` | a component has variants/states — never one boolean prop per variant |
| `patterns-explicit-variants.md` | variants differ in structure, not just style |
| `architecture-compound-components.md` | a component has named parts (Card.Header, Tabs.List…) |
| `patterns-children-over-render-props.md` | a slot takes arbitrary content |
| `state-lift-state.md` | siblings share state (tabs + panel, filter + list) |
| `state-decouple-implementation.md` | UI + mock data/state or real API scope |
| `state-context-interface.md` | the same UI is fed by different data sources |
| `react19-no-forwardref.md` | the project is on React 19 (`ref` is a normal prop, `use()` over `useContext`) |

## Rendering and state

| Rule | Read when |
|---|---|
| `rerender-no-inline-components.md` | always — never define a component inside another |
| `rendering-hoist-jsx.md` | static markup (icons, decorations) inside a component |
| `rendering-conditional-render.md` | conditional UI with `&&` on numbers |
| `rerender-derived-state-no-effect.md` | a value can be computed from props/state |
| `rerender-move-effect-to-event.md` | logic runs because of a user action |
| `rerender-lazy-state-init.md` | initial state reads storage or is expensive |
| `rerender-functional-setstate.md` | new state depends on previous state |
| `client-passive-event-listeners.md` | scroll/touch/wheel listeners |
| `rendering-hydration-no-flicker.md` | Next.js + theme/client-only values (dark mode, localStorage) |

## Assets and bundle

| Rule | Read when |
|---|---|
| `rendering-svg-precision.md` | inlining SVGs exported from Figma |
| `rendering-animate-svg-wrapper.md` | animating an SVG |
| `bundle-barrel-imports.md` | importing icons / UI library components |
| `bundle-dynamic-imports.md` | heavy widgets (charts, maps, editors) |

## Next.js server/client boundary (scope: wired to a real API)

| Rule | Read when |
|---|---|
| `async-suspense-boundaries.md` | a page fetches data |
| `server-serialization.md` | a Server Component passes props to a Client Component |

## Source

Copied unmodified from [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) at commit `063bee9` (2026-08-28): `skills/composition-patterns/rules/` (all) and a subset of `skills/react-best-practices/rules/`. © Vercel, released under the MIT License per those skills' `license: MIT` frontmatter. To update, re-copy the same filenames from a newer commit.
