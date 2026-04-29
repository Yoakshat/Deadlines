# UW Agent

Checks your UW course pages daily, stores homework and deadlines, speaks them out loud on your phone at 10am.

## Setup

### 1. Supabase
- Create a free project at supabase.com
- Go to SQL Editor → paste `schema.sql` → Run

### 2. GitHub
- Create a new repo
- Push all these files to it

### 3. Vercel
- Go to vercel.com → New Project → import your GitHub repo
- Add these environment variables in Project Settings → Environment Variables:

| Variable | Where to find it |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase → Settings → API → Project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase → Settings → API → anon public |
| `SUPABASE_URL` | same as above |
| `SUPABASE_SERVICE_KEY` | Supabase → Settings → API → service_role |
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `CRON_SECRET` | make up any random string |

- Deploy

### 4. Add your classes
- Open your Vercel URL → add your classes

### 5. Android app
- Fill in your Vercel URL in `SpeakerService.kt`
- Build and install via ADB

## How it works
- Vercel cron runs daily at 9am Seattle time
- Agent uses Claude + web search to find assignments on UW course pages  
- Stores everything in Supabase
- Android app wakes at 10am, queries Supabase, speaks what's due today
