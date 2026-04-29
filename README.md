# UW Agent

Scrapes UW course pages daily, stores deadlines in Supabase, speaks them to your phone at 10am.

## Repo structure
```
nextjs/   → dashboard UI + due-today API  (Railway service 1)
python/   → browser-use agent + cron      (Railway service 2)
schema.sql → run once in Supabase
```

## Setup

### 1. Supabase
- New project at supabase.com
- SQL Editor → paste schema.sql → Run

### 2. GitHub
- Push this repo to GitHub

### 3. Railway
- railway.app → New Project → Deploy from GitHub repo
- Add Service → select `nextjs/` folder
- Add Service → select `python/` folder
- Add these env vars to BOTH services:

| Variable | Where |
|---|---|
| `SUPABASE_URL` | Supabase → Settings → API → Project URL |
| `SUPABASE_SERVICE_KEY` | Supabase → Settings → API → service_role |
| `ANTHROPIC_API_KEY` | console.anthropic.com |

### 4. Add classes
- Open your Railway Next.js URL → add your classes

### 5. Android
- Point `SpeakerService.kt` at your Railway Next.js URL + `/api/due-today`
