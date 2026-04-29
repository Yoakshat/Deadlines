#!/usr/bin/env python3
"""
UW Agent — Python service on Railway
- Cron job runs daily at 9am Seattle time
- browser-use navigates UW course sites
- Stores hw/deadlines in Supabase
"""

import os
import json
import asyncio
import logging
import threading
from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify
from supabase import create_client
from browser_use import Agent
from langchain_anthropic import ChatAnthropic

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
SUPABASE_URL      = os.environ["SUPABASE_URL"]
SUPABASE_KEY      = os.environ["SUPABASE_SERVICE_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
llm      = ChatAnthropic(model="claude-opus-4-5", api_key=ANTHROPIC_API_KEY)

app = Flask(__name__)


# ── Agent task ─────────────────────────────────────────────────────────────────
def build_task(class_name: str) -> str:
    today = date.today().isoformat()
    return f"""
You are helping a University of Washington Seattle student find homework and deadlines for {class_name}.

Today is {today}.

What to do:
- Search Google for "uw {class_name}" and find the official UW course website
- The site likely has multiple quarters listed — find and navigate to the most current one
- Explore the site freely — syllabus, schedule, assignments tab, anywhere relevant
- Find all homework, projects, quizzes, exams, and deadlines

Return ONLY a JSON object like this (no explanation, no markdown):
{{
  "class": "{class_name}",
  "items": [
    {{
      "title": "Homework 1",
      "due_date": "2025-04-15 23:59",
      "type": "homework",
      "description": "brief description if available"
    }}
  ]
}}

Rules:
- due_date: YYYY-MM-DD HH:MM format. Default to 23:59 if no time given.
- type: homework | project | quiz | exam | reading | other
- If no due date found, use null
- If nothing found, return {{"class": "{class_name}", "items": []}}
"""


# ── Save to Supabase ───────────────────────────────────────────────────────────
def save_items(class_name: str, items: list):
    if not items:
        return
    rows = [{
        "class":       class_name,
        "title":       item.get("title", "Untitled"),
        "due_date":    item.get("due_date"),
        "type":        item.get("type", "other"),
        "description": item.get("description", ""),
        "notified":    False,
    } for item in items]

    supabase.table("assignments").upsert(rows, on_conflict="class,title").execute()
    log.info("Saved %d items for %s", len(rows), class_name)


# ── Run agent for one class ────────────────────────────────────────────────────
async def process_class(class_name: str):
    log.info("Processing %s", class_name)
    agent = Agent(task=build_task(class_name), llm=llm)
    try:
        result = await agent.run()
        raw    = result.final_result() if hasattr(result, "final_result") else str(result)
        data   = json.loads(raw)
        save_items(class_name, data.get("items", []))
        supabase.table("classes").update({"last_checked": date.today().isoformat()}).eq("name", class_name).execute()
    except Exception as e:
        log.error("Agent failed for %s: %s", class_name, e)


# ── Daily job ──────────────────────────────────────────────────────────────────
def run_agent():
    log.info("=== Daily agent run — %s ===", date.today().isoformat())
    result   = supabase.table("classes").select("name").execute()
    classes  = [r["name"] for r in result.data] if result.data else []

    if not classes:
        log.info("No classes found in DB")
        return

    async def run_all():
        for cls in classes:
            await process_class(cls)

    asyncio.run(run_all())
    log.info("=== Done ===")


# ── Flask health check (Railway needs a web server to stay alive) ──────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/run")
def trigger():
    """Manual trigger endpoint — hit this to run agent immediately"""
    threading.Thread(target=run_agent).start()
    return jsonify({"status": "started"})


# ── Start scheduler + Flask ────────────────────────────────────────────────────
if __name__ == "__main__":
    scheduler = BackgroundScheduler(timezone="America/Los_Angeles")
    scheduler.add_job(run_agent, "cron", hour=9, minute=0)
    scheduler.start()
    log.info("Scheduler started — agent runs daily at 9am Seattle time")

    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
