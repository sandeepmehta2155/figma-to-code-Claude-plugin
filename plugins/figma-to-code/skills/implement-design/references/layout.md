# Layout (implement-design step 4)

## Auto-layout → CSS

| Figma | CSS |
|---|---|
| `layoutMode` HORIZONTAL / VERTICAL / GRID | `flex` row / `flex` column / `grid` (`gridColumnsSizing` → `grid-template-columns`) |
| `itemSpacing` | `gap` — except with `SPACE_BETWEEN`, where the stored spacing is stale: use `justify-content: space-between`, no gap |
| `primaryAxisAlignItems` MIN / CENTER / MAX / SPACE_BETWEEN | `justify-content` start / center / flex-end / space-between |
| `counterAxisAlignItems` MIN / CENTER / MAX / BASELINE | `align-items` start / center / flex-end / baseline; every child FILL on the cross axis → `stretch` |
| child sizing FIXED / HUG / FILL | explicit size / no size (content) / `flex-1` on the main axis (`layoutGrow`), `align-self: stretch` on the cross axis (`layoutAlign: STRETCH`) |
| `layoutPositioning: ABSOLUTE` inside auto-layout | `position: absolute` at its offset from the parent; parent `position: relative` |
| `layoutWrap: WRAP` | `flex-wrap: wrap`; `counterAxisSpacing` → row gap |
| the **top-level frame's** FIXED width/height | not a real constraint — it's the artboard. Fill the container (`width: 100%`, `max-width` = design width if centered), don't pin it |
| text `letterSpacing` px | `em` = px ÷ font size (survives font-size changes) |

## Fidelity checklist

Details that routinely get dropped; account for each one the design has:

- Padding is per side and often asymmetric (`0/16/0/0` = right padding only); gaps come from the parent's item spacing (`0` is real). Auto-layout has no margins.
- Corner radius is per corner, stroke weight per side (`bottom: 1` = bottom border only) — don't round or border the whole box.
- Shadows/blur (effects), gradients, layer opacity, blend modes, rotation, clipping (`overflow-hidden`).
- Hidden layers: don't render them (they're usually other states).
- Text: letter spacing, text case, decoration, truncation/line clamp.
- Tables / column lists: each column's alignment (numbers are often right-aligned) — header and cells share it, so align both. Take each column's width from the design, wide enough for its widest cell *including the header*; a `nowrap` header wider than its grid track overflows and breaks the alignment.
- Flex children: grow (`flex-1`), stretch (`self-stretch`), absolute-positioned inside auto-layout, wrap.
