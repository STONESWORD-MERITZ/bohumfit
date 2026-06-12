# BOHUMFIT-040 Insurance PDF Save UI Balance

## Owner
Codex (Windows authority)

## Scope
- `src/pages/InsuranceCalculator.tsx`
- Harness task/handoff/locks

## Goal
Clean up the `/insurance` PDF save button and status layout without changing formulas, API payloads, disclaimers, or existing calculation UI behavior.

## Requirements
- Move the PDF save action from an awkward floating/top-right feel into a balanced responsive header layout.
- Keep the button and status message in their own fixed-width action column.
- Place errors/instructions below the button, not inside the title/copy area.
- Support three states consistently:
  - Default: `PDF로 저장`
  - Loading: disabled button, spinner, `PDF 생성 중...`, no wrapping
  - Failure: message below button, retry possible
- On narrow screens, title/copy and button must not overlap; button stacks below naturally.
- Do not change formulas, PDF API call logic, or disclaimers.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`
- Visual/markup review: header action column width, no-wrap loading text, max two-line status text.
