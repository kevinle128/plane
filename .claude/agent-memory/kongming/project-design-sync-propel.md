---
name: project-design-sync-propel
description: State of the @plane/propel -> claude.ai/design sync (first sync 2026-09-22) and the review findings Kongming returned; check whether they were applied before re-advising
metadata:
  type: project
---

First design-sync of `@plane/propel` to claude.ai/design project `85052822-...` completed 2026-09-22 (377 stories graded, 376 match, TabNavigationList `close` for a compare.mjs framer-motion clock artefact; Dialog `AllWidths` skipped). Durable set lives in `.design-sync/` (config, NOTES.md, conventions.md, previews/, overrides/dts.mjs).

Kongming's second-opinion review flagged, in priority order:

1. `conventions.md` spacing row used range notation (`p-0.5 … p-8` etc.) that names non-existent utilities (`p-7`, `px-7`, `py-5`, `gap-5`, `gap-7`); margins/`mx-auto` absent from the CSS but not warned about.
2. Emitted `Button.d.ts` has unqualified `CSSProperties`/`ReactElement` (Button's dist type is `ForwardRefExoticComponent<ButtonHTMLAttributes...>`); suggested `dtsPropsFor.Button`.
3. NOTES.md did not record the `--max-stories` value used (compare default is 6; Toast has 22 graded).
4. `libOverrides["dts.mjs"]` reason covered only one of the two fork edits; `inject-reference-fonts.mjs` duplicates `extraFonts` and skips existing files.

**Why:** the user asked for an independent audit of the durable set before committing it; these items are the ones a re-sync would silently inherit.
**How to apply:** on any later design-sync question in this repo, verify first whether these were fixed (grep `conventions.md` for `p-7`, check `dtsPropsFor.Button`, grep NOTES.md for `max-stories`) rather than re-raising them.
