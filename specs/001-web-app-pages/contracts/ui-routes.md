# Contract: Web UI routes & chrome

**Feature**: `001-web-app-pages` | **Date**: 2026-07-10

Visual contract: same tokens/fonts/header brand as splash (`/`) and report (`/report/[addressId]`).

## Routes

| Path | Auth | Purpose |
|------|------|---------|
| `/login` | Guest primary | Sign in form → Auth.js + API login |
| `/register` | Guest primary | Sign up form → API register → sign in |
| `/pricing` | Signed-in required | Upgrade/plans UI; current tier; plan CTAs are non-functional placeholders (no billing API) |
| `/dashboard` | Signed-in required | Address search + saved lookups list or empty state |
| `/compare` | Public | **Feature coming soon** placeholder (live compare deferred) |
| `/` | Public | Existing splash (header gains auth affordances; `#pricing` = marketing for guests, upgrade UI when signed in) |
| `/report/[addressId]` | Public (existing) | Report; shared Header/UserMenu; **Back to dashboard** only when signed in |

## Header nav

Section links that refer to splash content MUST use root-anchored hashes so they work off-home:

- Scores → `/#scores`
- AI Insights → `/#ai`
- Pricing → `/#pricing` (splash marketing — **not** `/pricing`)

## Header states

| State | Actions |
|-------|---------|
| Guest | Nav links; Sign in; Get started → register |
| Signed-in | UserMenu: display name/email; Dashboard; Plans & upgrade → `/pricing`; Compare (coming soon); Sign out |

## Footer

| State | Sign in link |
|-------|----------------|
| Guest | Visible → `/login` |
| Signed-in | Hidden |

## Splash `#pricing`

| State | Behavior |
|-------|----------|
| Guest | Marketing copy; register CTAs via `PricingTiersGrid` `mode="guest"` |
| Signed-in | Same upgrade UI as `/pricing` (current plan + Coming soon) via `mode="upgrade"` |

Shared component: `apps/web/src/components/pricing/PricingTiersGrid.tsx`.

## Report Back to dashboard

| State | Control |
|-------|---------|
| Guest | Hidden |
| Signed-in | Link → `/dashboard` |

## UpgradePrompt

Props conceptually: `feature` label + target tier. CTA navigates to `/pricing` (auth-gated upgrade page). Available for future gated UI; not required on the compare coming-soon page.

## Compare coming soon CTAs

| Priority | Control | Target |
|----------|---------|--------|
| Primary | `ButtonWithArrow` | `/dashboard` |
| Secondary | Text link | `/` |

## Out of scope (do not add in this feature)

- `PATCH /users/me/tier` or any billing/checkout API
- Functional plan upgrade buttons that change session tier
