# AGENTS.md — Web App (Next.js)

## File-backed auth — TEMPORARY

`apps/api/data/TEMP_dev_users.jsonl` and `apps/api/data/TEMP_dev_lookups.jsonl` back
a **temporary file store** used instead of PostgreSQL while the users table is not yet
implemented.

**Do NOT extend this store.** When the real Postgres backend ships:

1. Replace `FileUserStore` / `FileLookupStore` in `apps/api/app/services/`.
2. Update `AuthService`, auth endpoints, and user endpoints.
3. Delete `apps/api/tests/test_auth_file_store.py`.
4. Delete `apps/api/data/TEMP_*` files and `TEMP_REMOVE_WHEN_REAL_AUTH.md`.

See full removal checklist: `specs/001-web-app-pages/research.md`.

## Key conventions

- Client components only where interactivity is required — prefer Server Components.
- Auth via Auth.js (`next-auth`). Session includes `accessToken` and `tier`.
- All API calls go through `apiFetch` / `apiFetchServer` in `src/lib/api.ts`.
- Protected routes: `/dashboard` — guarded by `src/middleware.ts`.
- `/compare` is a public “Feature coming soon” placeholder until live compare ships.
- Styling tokens: CSS variables in `src/app/globals.css`; use `cn()` + Tailwind.
