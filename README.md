# TenantFlow — Multi-tenant SaaS Project Management
A runnable MVP: isolated workspaces, projects, issues, sprints, comments, audit events, workflow transitions, Stripe test checkout, Celery task wiring, React Kanban, Docker and CI.

## Quick start (Docker)
1. Copy `.env.example` to `.env`; set `DJANGO_SECRET_KEY` (Stripe keys optional).
2. `docker compose up --build`
3. API: http://localhost:8000/api/health/ — UI: http://localhost:5173
4. Create an account in UI. Registering creates a workspace and makes you its owner.

## Local dev
Backend: `python -m venv .venv && pip install -r backend/requirements.txt`; `cd backend && python manage.py migrate && python manage.py runserver`
Frontend: `cd frontend && npm install && npm run dev`
For local tasks without Redis, set `CELERY_TASK_ALWAYS_EAGER=True`.

## API
- `POST /api/auth/register/` `{email,password,workspace_name}`
- `POST /api/auth/token/` `{email,password}` -> JWT
- `GET/POST /api/projects/`
- `GET/POST /api/issues/` (filters `project`, `status`)
- `PATCH /api/issues/{id}/` (status, title, description, assignee, sprint)
- `POST /api/issues/{id}/comments/` `{body}`
- `GET /api/audit/`
- `POST /api/billing/checkout/` `{price_id}` creates Stripe test checkout session
- `POST /api/billing/webhook/` Stripe signed webhook endpoint

## Isolation/security notes
All tenant-owned querysets are scoped from the authenticated user's active workspace membership; client-supplied tenant IDs are ignored. Object writes re-check membership and project/issue relationships. Workspace membership roles: owner/admin/member/viewer. Do not treat UI hiding as authorization. JWT is used for the demo. Production hardening: invite flow, rate limiting, refresh rotation, virus scanning, signed attachment storage, observability, secrets manager, backup/restore drills, CSP, and verified Stripe webhook deployment settings.

## Test
`cd backend && python manage.py test`
