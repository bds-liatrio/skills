## Goals

Add a header language selector that persists locale via cookie.

## Non-goals

- Translating all clinic content in this change
- Per-user account locale preferences

## Functional Requirements

1. Header dropdown lists supported locales and updates UI text after selection.
2. Locale persists via cookie for subsequent requests.
3. `redirect=` after locale change is same-origin only (no open redirect).

## Constraints

- Reuse existing `WebConfiguration` / message-bundle wiring when present.
- Cookie is host-only; sensible max-age documented in Assumptions.

## Assumptions

- Cookie max-age: 1 year.
- Supported locales: en, es (extendable via bundles).

## Size

S — One vertical slice: header control → locale endpoint → cookie → UI text; bounded file set.

## User Acceptance Criteria

- [ ] User can switch language from the header on desktop and mobile nav.
- [ ] Refresh keeps the chosen language.
- [ ] Malicious external `redirect=` is rejected or ignored.

## Testable / Verifiable

1. Playwright covers language switch + persistence.
2. Unit/controller test covers open-redirect rejection.

---

## Original Ask

### Summary

Add a language dropdown.
