# BOHUMFIT-055 Header Text Wordmark

## Owner
Codex (Windows authority)

## Goal
Change the site header/logo component from emblem + Korean text to the FitHere-style text wordmark `BohumFit 보험핏`. Keep the official green emblem reserved for favicon/app-icon usage only.

## Scope
- Replace `src/components/Logo.tsx` with a text-only wordmark component.
- Preserve `public/favicon.svg` as the green emblem.
- Do not touch env/config/migrations/prisma/db/seed files.
- No routing, formula, backend, or page logic changes.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm run build`
- Smoke check: rendered logo text contains `BohumFit 보험핏`, header logo has no emblem SVG, favicon still contains green emblem `#15663D`.
