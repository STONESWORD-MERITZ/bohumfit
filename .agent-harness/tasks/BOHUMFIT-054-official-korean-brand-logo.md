# BOHUMFIT-054 Official Korean Brand Logo

## Owner
Codex (Windows authority)

## Goal
Replace the temporary text/mark presentation with the official Korean-facing brand `보험핏` and the green emblem.

## Adaptation Note
The pasted instruction references a Next.js 14 App Router repo. This repository is Vite/React, so favicon and metadata changes are applied through `public/favicon.svg`, `public/og-image.svg`, and `index.html` instead of `app/icon.svg` / `app/layout.tsx`.

## Scope
- Replace `BrandWordmark` usage with an official `Logo` component: green emblem + `보험핏`.
- Update public favicon to the official green emblem (`#15663D`).
- Update visible title/OG/user-facing copy from `BohumFit` to `보험핏`.
- Preserve operational identifiers: package name, domain `bohumfit.ai`, task IDs, env/config files.

## Out Of Scope
- Backend/PDF report naming and tests; handle separately with pytest updates.
- `.env*`, config files, migrations, prisma, database/seed files.
- Non-brand logic or formula behavior.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`
- Dev smoke: header/login/footer/mission logo renders official emblem + `보험핏`, favicon/OG SVG returns 200, Korean text has no replacement characters.
