# Health Tracker — web

Next.js 16 (App Router, Cache Components) + TypeScript + Tailwind 4 + shadcn/ui, TanStack Query, Recharts.

```bash
npm install
API_URL=http://localhost:8000 npm run dev      # API must be running (see repo README)
npm run build && npm run lint
```

## How it talks to the API
The browser never holds a token.
- `src/app/api/auth/*`: login/signup/logout route handlers. They call FastAPI and keep the access and refresh tokens in **httpOnly cookies**.
- `src/app/api/proxy/[...path]`: forwards `/api/proxy/*` to FastAPI `/api/v1/*`. It attaches the token, refreshes it once when it expires, and returns a clean 502 if the API is unreachable.
- `src/proxy.ts` (Next 16's replacement for middleware): optimistic redirect of signed-out users to `/login`. Real authorization is enforced by the API.

## Structure
| Path | What |
|---|---|
| `src/app/(auth)` | Sign-in (with one-click demo roles) and patient sign-up |
| `src/app/(app)/dashboard`, `patients`, `schedule`, `insights` | Clinician: risk worklist, patient list, chart, consultation, schedule, panel analytics |
| `src/app/(app)/me` | Patient: own record, health-check questionnaire, appointments, privacy & access log |
| `src/app/(app)/admin` | Admin: population analytics, model drift monitoring, users, audit log |
| `src/components/patient` | Chart building blocks: header with allergy alerts, problems and meds, latest vitals, trends, timeline |
| `src/components/risk/risk-card.tsx` | Explainable risk card: band, percentile, SHAP drivers, model facts |
| `src/components/consult/consult-workspace.tsx` | Note → extract → review the editable draft → save |

Pages are server components that render a client component. Session-dependent data loads client-side, so each route still prerenders a static shell. Routes that read URL params sit behind `<Suspense>`.
