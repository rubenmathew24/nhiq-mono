# TEMPORARY — Remove when real auth ships

This directory holds a **file-backed user and lookup store** used only for
local development while the PostgreSQL `users` / `address_lookups` tables are
not yet implemented.

See full removal checklist:
`specs/001-web-app-pages/research.md` → *Temporary auth store removal checklist*

## Quick removal steps

1. Delete `TEMP_dev_users.jsonl` and `TEMP_dev_lookups.jsonl`.
2. Delete this file.
3. Replace `FileUserStore` / `FileLookupStore` with Postgres ORM repositories
   in `apps/api/app/services/user_store.py` and `apps/api/app/services/lookup_store.py`.
4. Update `AuthService` and `users` endpoint to use the new repositories.
5. Run `grep -r "TEMP_\|FileUserStore\|FileLookupStore\|dev_users.jsonl" apps/api` — should be zero hits.
6. Delete `apps/api/tests/test_auth_file_store.py` and replace with DB-fixture tests.
