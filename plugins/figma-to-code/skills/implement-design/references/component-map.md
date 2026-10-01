# Component map (implement-design, existing projects)

`figma-components.json` sits next to the target app's `package.json` and maps Figma components to the project's own components. The user confirms it once. Every later run builds with the same components, and so does every teammate once it's committed.

```json
{
  "Button": { "import": "@/components/ui/button", "name": "Button", "props": { "variant": "default" } },
  "Component 272": { "import": "@/components/layout/header", "name": "Header" },
  "Component 1 / variant=28": { "import": "lucide-react", "name": "Zap" },
  "Promo card": null
}
```

- **Key**: the Figma component set's name, which covers all its variants, or `Set / Prop=value` for a single variant (for example an icon set, where each variant is a different glyph). A component that isn't in a set is keyed by its own name. Look up the exact key first, then the set name.
- **`import`**: the specifier the project imports from (its path alias or a package), never a file path.
- **`props`**: defaults. The instance's own variant still sets the rest.
- **`null`**: there is no project component. Build it from the design, and don't ask about it again.

## Step 2: before any code

1. List the design's component instances, with counts:
   - **Bundle**: the visible instances `split_payload.py` printed: key, count and sizes, with instances under hidden layers left out. A value without ` / ` is a component outside a set, and that name is the key. A bare `Prop=value` (the set name didn't come through) falls back to the instance's layer name.
   - **`figma-view`**: the component and component-set maps in the `get_figma_data` result, plus the `componentId` on each instance.
   - **Official MCP**: the instance names in the `get_design_context` result.
   - Leave out widgets that question 7 already decided.
2. Look each one up in `figma-components.json`. For the rest, find the closest project component by name, role and props. Interactive controls map to the component library's component, never to a native element or a hand-rolled one (step 4).
3. Show one table: Figma component (count, size), project component (import, name, props), and why. Bundles carry no internals for instances, because LLM Export doesn't export their children. For those instances, the map is the only way to reuse the project's component instead of redrawing it from the render.
4. Ask once with AskUserQuestion: **Save all (Recommended)** / **I'll correct some rows** / **This run only** / **Don't map**. On save, merge the rows into `figma-components.json`: keep the existing rows and add the new ones.
