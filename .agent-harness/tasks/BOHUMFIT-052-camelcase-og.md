# BOHUMFIT-052 CamelCase Lockup + OG Reference Fix

## Owner
Codex (Windows authority)

## Scope
- Change visible text lockup from `BOHUMFIT.` to `BohumFit.`
- Change HTML title and OG title from `BOHUMFIT` to `BohumFit`
- Change `og:image` reference from `/og-image.png` to `/og-image.svg`
- Change the brand text inside `public/og-image.svg` to `BohumFit`

## Non-Goals
- Do not change domain strings such as `bohumfit.ai` or `BOHUMFIT.AI`.
- Do not change formula, analysis, backend, or deployment logic.
- Do not change brand colors or tints.
- Do not sweep all body copy yet; leave broader text normalization for BOHUMFIT-053.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`
- Dev smoke: four visible lockup locations render `BohumFit.` + Korean sublabel; `/og-image.svg` returns 200.
