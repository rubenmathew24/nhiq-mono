# AGENTS.md — Web App (Next.js)

## Auth storage

Auth and saved lookups live in **Docker Compose PostgreSQL** (`users`, `saved_lookups`,
`address_lookups`) via FastAPI repositories. The web app never talks to SQL —
use Auth.js + `apiFetch` only.

See `specs/001-web-app-pages/research.md` and `quickstart.md`.

## Key conventions

- Client components only where interactivity is required — prefer Server Components.
- Auth via Auth.js (`next-auth`). Session includes `accessToken` and `tier`.
- All API calls go through `apiFetch` / `apiFetchServer` in `src/lib/api.ts`.
- Protected routes: `/dashboard` — guarded by `src/middleware.ts`.
- `/compare` is a public “Feature coming soon” placeholder until live compare ships.
- Styling tokens: CSS variables in `src/app/globals.css`; use `cn()` + Tailwind.
