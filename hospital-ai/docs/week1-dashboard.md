# Week 1 — Hospital Administration Integration

Run migration `backend/migrations/006_create_resources_announcements.sql` after medical records.

## Added

- Hospital resources CRUD + dashboard resource summary
- Announcements + in-app notifications
- Dashboard KPIs, Recharts analytics, recent activity, quick actions
- Global search (`GET /search?q=`)
- Profile (password change via Supabase Auth)
- Settings (local preferences + AI config placeholder)
- AI Center + agent placeholder pages (“Coming in Week 2”)
- 404 / 401 / 500 pages
- Lazy-loaded routes + code splitting

## Dashboard APIs

- `GET /dashboard/statistics`
- `GET /dashboard/charts`
- `GET /dashboard/recent-activities`
- `GET /dashboard/upcoming-appointments`
- `GET /dashboard/resource-summary`

## Module APIs

- `/resources` CRUD
- `/announcements` CRUD
- `/notifications` list / mark read / mark all read
- `/search` global search
