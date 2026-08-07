---
paths:
  - "mcr-frontend/src/**/*.vue"
  - "mcr-frontend/src/**/*.css"
---

# Styling (Tailwind v4 + DSFR)

**Tailwind is the styling framework.** Style in the markup with utilities; a `<style>` block is the
exception you justify, not the default. **Layout is never CSS** — display, flex/grid, gap, padding,
margin, sizing, positioning belong in the `class` attribute, always.

Write CSS only when a utility structurally cannot reach the target:

- **DOM the component does not render** — third-party internals via `:deep()`. A child component's
  _root_ is reachable (`<DsfrFooter class="pb-4" />`); anything deeper is not.
- **`<Transition>` / `<TransitionGroup>` classes** (`.list-move`, `.fade-enter-active`) — Vue applies
  them at runtime. Never touch them.
- **`@keyframes`**, `::marker`, `mask-image`, `content: attr(...)`, parent-conditional selectors
  (`:not(.grid-cols-1) > .fr-input-group`).

Plain `::before`/`::after` are **not** on that list: `after:hidden after:content-none` reproduces
`::after { display: none; content: none }` exactly.

Forbidden: `@apply` (each SFC block compiles alone — it would need a `@reference` and rerun Tailwind
per block), `lang="scss"`, class names built by concatenation.

## The cascade is the main failure mode

`main.css` declares `@layer theme, base, dsfr, components, utilities`, so utilities beat DSFR. But
**scoped CSS is unlayered, and unlayered beats every layer.** Two silent consequences:

- **Moving a rule out of `<style scoped>` makes it descend** into `layer(utilities)`. If it existed to
  beat another _unlayered_ rule it now loses — `motion-reduce:transition-none` cannot override a
  scoped `.trigger { transition: … }` left in CSS.
- **Adding `scoped` to a global block raises specificity** by `0-1-0`, which can steal a rule from a
  competitor that won on source order (scoping `DsfrDropdown` flipped `.fr-accordion__btn` away from
  `AppHeader`).

Ask what a declaration was overriding before moving it, and settle it by diffing `dist/assets/*.css`
before/after — not by reasoning. Never add `!important` to patch a cascade you broke.

`.fr-h1`…`.fr-h6` carry `!important` on font-size, font-weight and line-height: a typography utility
on an element that also has `fr-h*` will not apply.
