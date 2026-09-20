# Design System — Web Admin Panel

The visual language for `web/`: a themed, dark, pixel-art admin panel. This
guide exists so the app stays consistent as new pages get added — read it
before hand-rolling a card, button, or status color that a primitive
already covers.

## The rule: theme is chrome, not content

Press Start 2P (the blocky pixel font, `font-minecraft`) belongs on
headings, nav labels, and buttons — the places a display font reads as
intentional. Body copy, tables, logs, and anything read at length uses
VT323 (`font-body`, and the default body font via `:root`), which is
designed to be legible at small sizes. If you're writing a paragraph,
a table cell, or a log line and reach for `font-minecraft`, stop — that's
the mistake that made most of the app hard to scan before this pass.

## Reach for a primitive first

`web/src/components/ui/` holds the shared components. Import from
`components/ui` (the barrel file) rather than reaching for
`.btn-minecraft`/`.card-minecraft`/etc. directly in new code:

| Primitive | Use it for |
| --- | --- |
| `Button` | Any clickable action. `variant`: `primary` \| `secondary` \| `danger` \| `ghost`. `size`: `sm` \| `md`. Icon-only buttons need `icon` + `iconLabel` for an accessible name. |
| `Card` | Any panel/container. `padding`: `none` \| `sm` \| `md` \| `lg`. `animateIn` opts into a one-time fade — leave it off for anything that re-renders on a poll. |
| `Input` / `Select` / `Textarea` | Any form field. Always pass `label`; they wire `htmlFor`/`id`/`aria-describedby` for you. `error` and `hint` render below the field. |
| `Badge` | A static status label (enabled/disabled, a role, a category). `status`: `success` \| `danger` \| `warning` \| `info` \| `neutral`. |
| `StatusPill` | An online/offline-style dot + label. Same `status` values as `Badge`, plus `pulse`. |
| `PageHeader` | The page title. `title`, optional `subtitle`, `actions`, `lastUpdated`. |
| `EmptyState` | "Nothing here yet." `icon`, `title`, optional `hint` and `action`. |
| `Alert` | A dismissible or persistent banner. `tone` matches the `Badge`/`StatusPill` status values. Pass `autoDismiss` (ms) + `onDismiss` for a toast-like banner; omit both for one that stays until the user acts. |
| `ErrorState` | A page-level failure: message + retry. Use this instead of falling through to an empty state when a fetch fails — three pages used to do exactly that. |
| `Table` / `TableHead` / `TableBody` / `TableRow` / `TableHeaderCell` / `TableCell` | Any tabular data. `Table` takes an optional `caption` (screen-reader only) and wraps in `overflow-x-auto` automatically. |
| `Modal` | Any overlay dialog. Handles focus trap, focus restore, Escape, and click-outside — don't reimplement these. |

Each primitive wraps the existing `.btn-minecraft*`/`.card-minecraft`/
`.input-minecraft` CSS classes, so using one doesn't change how anything
looks — it just means every page builds the same concept the same way.

## Tokens (`web/tailwind.config.js`)

- **Material palette** — `minecraft.{grass,dirt,stone,water,background,text}`,
  each `{ light, DEFAULT, dark }`. Use the bare name for the class, e.g.
  `bg-minecraft-grass` — **not** `bg-minecraft-grass-DEFAULT`. Tailwind maps
  a `DEFAULT` key onto the bare class name; the `-DEFAULT` suffix form was a
  real bug found during this pass (81 occurrences across the app, none of
  which ever generated a CSS rule) and doesn't work.
- **Semantic aliases** — `minecraft.{success,danger,warning,info}`, same
  shape. Reach for these over the material names when what you mean is a
  state (a success message, an error), not a material (grass green).
  `success` = `grass`, `info` = `water`; `danger`/`warning` are the red and
  orange the original palette never defined despite being used everywhere
  as raw hex.
- **Type scale** — `text-caption` (8px) / `text-body` (10px) /
  `text-label` (11px) / `text-h2` (16px) / `text-h1` (20px) /
  `text-display` (24px). Prefer these over a raw `text-[Npx]` arbitrary
  value in new code; the app still has ~285 of the latter left to convert.
- **Glows** — `shadow-glow-{success,danger,warning,info}`, matching
  `StatusCard`'s status-colored glow.

There is no dark-mode toggle and none is planned — the app is
intentionally always dark. There is no spacing scale beyond Tailwind's
defaults; card padding uses `Card`'s `padding` prop (`sm`/`md`/`lg`) rather
than an arbitrary `p-N`.

## Class-name utility

Use `cn()` from `web/src/utils/cn.js` (a thin wrapper over `clsx` +
`tailwind-merge`) for conditional classes, instead of building strings
with template literals and ternaries. It also means a later conflicting
Tailwind utility correctly wins over an earlier one on the same property.

## What not to do

- Don't write a new raw hex color in JSX (`bg-[#C62828]`). If the color you
  need isn't a token yet, add it to `tailwind.config.js` rather than
  inlining it — that's how the app ended up with 21 different hand-written
  hex values for the same handful of intended colors.
- Don't build a new button/card/input/modal/table by hand. If a primitive
  doesn't fit, extend the primitive rather than working around it.
- Don't use `window.confirm()` for a new destructive action — use `Modal`.
- Don't let a fetch failure fall through to an empty state. Track the
  error and render `ErrorState`.

## History

This system was introduced in a UI/UX consistency and performance pass
(see the repo's commit history around it). Before it, the app had six
global CSS classes and no shared component layer at all — 21 pages each
built their own version of a button, a card, a loading state, and an
error banner. See [WEB_INTERFACE.md](WEB_INTERFACE.md) for what the panel
does, and [WEB_UI_TESTING.md](WEB_UI_TESTING.md) for how it's tested.
