---
paths:
  - "src/typescript/**"
---

# TypeScript Explorer's Guide

This guide exists because cross-stack fluency matters. You don't need to become a React expert to review a TS PR, fix a bug, or add a feature flag. AI is your bridge. This document gives you enough context that you + AI can be a competent TypeScript contributor.

## The TypeScript Packages

All packages live under `src/typescript/mx2/` and are managed as a pnpm workspace. Four are **shared libraries** (`common-ts`, `search`, `ai-doc-chat`, `bulk-chat`); three are **standalone apps** (`nextjs-app`, `ms-word-add-in`, `ms-outlook-add-in`).

| Package | What it does | Tech stack |
|---|---|---|
| **nextjs-app** | Main web app (MX2 LAW): document search, AI chat, expert search, med chron, doc gen admin | Next.js 14 (App Router), React, Redux Toolkit, React Query, MUI 6, AWS Amplify |
| **common-ts** | Shared library consumed by all other packages: components, hooks, API clients, config, types | React, MUI 6, esbuild |
| **ai-doc-chat** | Shared AI chat component library: conversational interface, prompt library, chat history | React, esbuild, DOMPurify, Sass |
| **bulk-chat** | Bulk Matter Chat component library (productized bulk-chat UI; gated by `isNewBulkChatExperienceEnabled`) | React, MUI 6, esbuild |
| **search** | Search utilities and components | React, MUI 6, esbuild |
| **ms-word-add-in** | Word task pane: matter connection, document init, AI chat, content generation | React, Office.js, MSAL, MUI 6, Webpack, Storybook |
| **ms-outlook-add-in** | Outlook task pane: AI document chat from email context | React, Office.js, MSAL, MUI 6, Webpack |

### Package Dependency & Cross-Import Rules

The packages form a tier pyramid, collapsed here as a left-to-right chain (lower tier on the left):

```
common-ts -> search -> ai-doc-chat / bulk-chat -> nextjs-app / ms-word-add-in / ms-outlook-add-in
```

A package may import only from tiers strictly to its **left**. Never sideways (within its own tier - `ai-doc-chat` ↛ `bulk-chat`, `nextjs-app` ↛ `ms-word-add-in`, etc.) and never to the right (upward). Concretely:

- `common-ts` imports nothing else in `mx2/` - it's the base tier.
- `search` imports only `common-ts`.
- `ai-doc-chat` and `bulk-chat` each import `common-ts` and `search`, but not each other.
- The three apps (`nextjs-app`, `ms-word-add-in`, `ms-outlook-add-in`) each import any library (`common-ts`, `search`, `ai-doc-chat`, `bulk-chat`), but not one another.

This keeps every tier independently buildable and the dependency arrow pointing one way, mirroring the dependency-direction rule in `architecture.md`. The boundary is enforced, not just documented: `src/typescript/mx2/eslint.boundaries.mjs` is the single source of truth and each package's `eslint.config.mjs` wires it into `no-restricted-imports`.

Changes to a shared library ripple to every consumer - verify cross-package after editing any of the shared libraries (and run the consuming libraries'/apps' checks).

## How TS Apps Connect to Python Services

The API connection architecture lives in `common-ts/config/web/index.ts`. A single `getCurrentConfig(app, hostname)` function returns all Python API base URLs based on the hostname (localhost = LOCAL, mx2.dev = DEV, mx2.law = PROD). URLs follow the pattern `https://{service}.api.{env-domain}`.

API calls use `fetch` with Bearer token auth via `common-ts/lib/api`. When you see a TS API call, the Python service it hits is identifiable from the base URL name (e.g., `searchApiBaseUrl` hits the enterprise-search service, `llmApiBaseUrl` hits the LLM service).

## Key Conventions (What's Different from Python)

**Named exports, not default exports.** The nextjs-app ESLint config enforces `no-restricted-exports` (default exports banned), except for Next.js special files (`page.tsx`, `layout.tsx`, `error.tsx`). This is the TS equivalent of explicit imports.

**ESLint is your mypy.** ESLint enforces import sorting, no-shadow, no-unused-vars, and more. You don't need to memorize these rules. Run `pnpm checks` and ESLint will tell you what's wrong. Think of it as `pants tlc` for TypeScript.

**Component structure.** React components are functions that return JSX (HTML-like syntax). Props are typed via TypeScript interfaces. State is managed via hooks (`useState`, `useEffect`, `useQuery`).

**Feature flags via LaunchDarkly.** The `useLDFlags()` hook provides flags. Components conditionally render based on flag values. This is the most common pattern in TS PRs - adding or removing feature-gated UI.

**Tests use Vitest + React Testing Library.** Tests render components into a virtual DOM and query by accessibility roles/text. API calls are intercepted at the network layer by MSW (Mock Service Worker), not mocked at the import boundary.

## Error Handling

TypeScript error handling follows the same principles as Python (`architecture.md`): let errors propagate, preserve context, fail explicitly.

- **Preserve error cause.** When catching and rethrowing, use `{ cause: err }` so the original error chain is preserved for debugging: `throw new Error('Enhancement failed', { cause: err })`. Never discard the original error.
- **No bare catch blocks.** `catch { return ''; }` silently swallows errors and makes failures invisible. Always capture the error parameter: `catch (err)`.
- **No silent swallows.** `catch (err) { console.error(err); }` followed by returning a default value hides failures from the user and from monitoring. If the operation failed, surface it: set error state, show a toast, or rethrow.
- **Type-narrow caught errors.** TypeScript catch clauses receive `unknown`. Narrow before accessing properties: `if (err instanceof Error) { ... }`.

## Common Tasks

**"I need to add a field to a card component."**
Find the component in `features/` (nextjs-app) or `src/app/modules/` (add-ins). The component's props interface defines what data it accepts. Add the field to the interface, pass it from the parent, and render it in the JSX. Run `pnpm checks` in the app directory.

**"I need to add a feature flag."**
1. Add the flag to `FLAG_MAPPING` (and its default value) in `common-ts/lib/launchdarkly-flags.ts`. The `useLDFlags()` return type is derived from these definitions and updates automatically.
2. Use it in the component: `const { myNewFlag } = useLDFlags();`
3. Wrap the conditional UI in `{myNewFlag && <MyComponent />}`
4. In tests, mock the flag via `vi.mock('@mx2/common-ts/providers/launch-darkly')`

Gotchas (learned the hard way):
- **Call `useLDFlags()` inside the `LaunchDarklyProvider`.** The provider is mounted *inside* `<AppPage>` (`app_page_layout/index.tsx`). A `useLDFlags()` call rendered *above* `<AppPage>` - e.g. at the top of a `page.tsx` - returns `undefined` for every flag, permanently. Put the hook in a child component rendered inside `<AppPage>`. Diagnostic: a flag reading `undefined` means the hook is outside the provider (or LD is still loading); a flag that exists but is off reads `false`. The two are not interchangeable, so `undefined` is a wiring smell, not "the flag is off."
- **Adding a flag to `FLAG_MAPPING` makes it a required key of `ConvertedFlags`.** This breaks every test that builds an exhaustive flag object, plus the runtime `toEqual` in `common-ts/__tests__/lib/launchdarkly-flags.test.ts`. Grep for an existing flag (e.g. `isChatShareLinkEnabled`) to find every spot that enumerates the full flag set and add yours alongside.

**"I need to fix a failing test."**
Run the single test: `pnpm test -- path/to/test.test.tsx` (add `-t "test name"` to filter by a specific test). Tests use `screen.getByText()`, `screen.getByRole()` to find elements and `expect(...).toBeInTheDocument()` to assert. If an API mock is wrong, check `__mocks__/handlers.ts` for the MSW handler.

## What ESLint Catches for You

You don't need to memorize TS conventions. ESLint enforces:
- **Import sorting** (simple-import-sort) - auto-fixable with `pnpm lint:fix`
- **No shadowed variables** (catches accidental name reuse)
- **No unused variables** (with `_` prefix escape hatch)
- **No default exports** (nextjs-app, except Next.js special files)
- **Prettier formatting** (consistent code style)

Three rules are temporarily disabled in nextjs-app with Jira tickets tracking re-enablement:
- `@typescript-eslint/no-explicit-any` (MX2-NNNNN) - `any` is allowed but discouraged
- `react-hooks/exhaustive-deps` (MX2-NNNNN)
- `react/no-unescaped-entities` (MX2-NNNNN)

## Reviewing a TS PR as a Python Dev

The principles you already know apply: naming, structure, error handling, single responsibility. Here's what to focus on in TS PRs:

- **Does it render what it claims to?** Read the component JSX like you'd read an API response shape.
- **Are API calls handled?** Look for loading states, error states, and empty states. The Python equivalent: does the caller handle the service returning an error?
- **Are props typed?** Untyped or `any`-typed props are the TS equivalent of `dict[str, Any]`.
- **Does the test assert behavior?** Same principle as Python: assert outcomes (text on screen, elements present/absent), not implementation (mock call counts).
- **Feature flag cleanup?** If a flag is being removed, is the non-flagged code path also removed?

Ask AI to explain patterns you don't recognize. "What does `useEffect` do in this component?" or "Why is this wrapped in `useMemo`?" are exactly the right questions.

## Gotchas & Lessons Learned

Hard-won specifics that have bitten real PRs. Add to this list as you hit new ones.

### Consuming MX2 design components (`MX2Chip`, `MX2Button`, `MX2Typography`, ...) from a new package

- **The MUI type augmentation must be in scope.** The `mx2*` Typography variants and `theme.palette.mx2` tokens are declared via MUI module augmentation in `common-ts/providers/theme.tsx`. `common-ts` ships no `.d.ts`, so a consumer type-checks against source and the augmentation is absent - `tsc` fails with errors like *"'mx2H1' is not assignable to ... TypographyPropsVariantOverrides"*, and the error points at *common-ts's* `MX2Typography.tsx`, not your code. Fix: add a root `global.d.ts` containing `import type {} from '@mx2/common-ts/providers/theme';` (type-only, zero runtime). Same pattern as `ai-doc-chat/global.d.ts`; the package's tsconfig `include` must cover root `*.ts`.
- **The CSS must reach the app.** MX2 components import their own `.css` (which relies on `--mx2-colors-*` CSS variables). If your package's esbuild bundles `common-ts`, that CSS is extracted into a stranded `dist/index.css` the app never imports → unstyled components. Fix: externalize `@mx2/common-ts` and `@mx2/common-ts/*` in your `esbuild.config.js`, and add your package to `nextjs-app/next.config.mjs` `transpilePackages` (alongside `@mx2/common-ts`) so Next transpiles it and resolves the CSS the same way.
- **Use MX2 tokens as CSS vars in `sx`, not `theme.palette.mx2.*`.** `var(--mx2-colors-divider-primary)`, `var(--mx2-colors-text-states-hover)`, etc. resolve at runtime via the provider and don't throw in jsdom unit tests that lack the MX2 ThemeProvider. Reaching into `theme.palette.mx2.*` inside an `sx` callback throws when the provider is absent (most unit tests).

### Workspace build & consumption model

- `@mx2/*` libraries build to `dist/` via esbuild and ship **no `.d.ts`**. `nextjs-app` consumes the built `dist` (the package `main`); subpath imports (`@mx2/common-ts/components/...`) resolve to **source** through the pnpm workspace symlink. Practical effects: a stale `dist` serves old runtime code (rebuild the library after editing it before testing in a consumer), and a surprising `undefined`/type error can trace to source-vs-dist resolution rather than your change.

### Figma → code

- `get_design_context` refuses to run without an asset-write directory. You can still derive a complete spec - layout, design tokens, structure - from `get_screenshot` + `get_variable_defs` + `get_metadata`, with no asset writes (works in plan mode). MX2 chip colors map cleanly: Figma `green/50` + `success/main` → `<MX2Chip color="success" variant="filled" />`.

### Agent / tooling

- **The Bash working directory persists across calls.** A stray `cd` into another package will silently run `pnpm test`/`pnpm checks` in the wrong package - the output looks real but covers the wrong code. Prefix package-scoped commands with an explicit `cd <package> &&`, and sanity-check the package name in the command's output header.

## When to Ask a TS-Experienced Teammate

- Performance concerns (re-render optimization, memoization strategy)
- Office.js API specifics (manifest changes, sideloading, platform quirks)
- Next.js routing or SSR/SSG decisions
- MUI theming or complex component composition
- Webpack/esbuild configuration changes
