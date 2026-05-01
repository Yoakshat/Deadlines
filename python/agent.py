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
from flask import Flask, jsonify, request as flask_request
import anthropic
from supabase import create_client
from browser_use import Agent, ChatAnthropic
from browser_use.browser.profile import BrowserProfile

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase         = create_client(SUPABASE_URL, SUPABASE_KEY)
llm              = ChatAnthropic(model="claude-sonnet-4-5")
anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

app = Flask(__name__)


# ── Agent task ─────────────────────────────────────────────────────────────────
def build_task(class_name: str) -> str:
    today = date.today().isoformat()
    return f"""
You are helping a University of Washington Seattle student find homework, deadlines, and the syllabus for {class_name}.

Today is {today}.

What to do:
- Search Google for "uw {class_name}" and find the official UW course website
- The site likely has multiple quarters listed — find and navigate to the most current one
- Explore the site — syllabus, schedule, assignments tab, anywhere relevant
- Collect the full syllabus content (copy it exactly, do not summarize)
- Find all homework, projects, quizzes, exams, and deadlines

Return ONLY a JSON object like this (no explanation, no markdown):
{{
  "class": "{class_name}",
  "syllabus": "full syllabus content as a markdown string",
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
- due_date: YYYY-MM-DD format if no time given, YYYY-MM-DD HH:MM if a specific time is available.
- type: homework | project | quiz | exam | reading | other
- If no due date found, use null
- If nothing found, return {{"class": "{class_name}", "syllabus": "", "items": []}}
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
    agent = Agent(task=build_task(class_name), llm=llm, browser_profile=BrowserProfile(headless=True), use_vision=False)
    try:
        result = await agent.run()
        raw    = result.final_result() if hasattr(result, "final_result") else str(result)
        data   = json.loads(raw)
        save_items(class_name, data.get("items", []))
        syllabus = data.get("syllabus", "")
        if syllabus:
            supabase.storage.from_("syllabi").upload(
                f"{class_name}.md",
                syllabus.encode("utf-8"),
                {"content-type": "text/markdown", "upsert": "true"},
            )
            log.info("Uploaded syllabus for %s", class_name)
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

    supabase.table("assignments").delete().neq("class", "").execute()
    log.info("Cleared assignments table")

    async def run_all():
        await asyncio.gather(*[process_class(cls) for cls in classes])

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


@app.route("/api/ask", methods=["POST"])
def ask():
    data     = flask_request.get_json(force=True, silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question required"}), 400

    today = date.today().isoformat()

    assignments_data = supabase.table("assignments").select("class,title,due_date,type,description").execute()
    assignments      = assignments_data.data or []

    syllabi_parts = []
    try:
        files = supabase.storage.from_("syllabi").list()
        for f in (files or []):
            name = f.get("name", "")
            if not name:
                continue
            content    = supabase.storage.from_("syllabi").download(name)
            class_name = name.replace(".md", "")
            syllabi_parts.append(f"=== SYLLABUS: {class_name} ===\n{content.decode('utf-8')}")
    except Exception as e:
        log.error("Syllabi fetch failed: %s", e)

    if assignments:
        rows = "\n".join(
            f"- {a['class']}: {a['title']} | due: {a.get('due_date', 'N/A')} | type: {a.get('type', 'N/A')} | {a.get('description', '')}"
            for a in assignments
        )
        context = f"=== ASSIGNMENTS ===\n{rows}"
    else:
        context = "=== ASSIGNMENTS ===\n(none)"

    if syllabi_parts:
        context += "\n\n" + "\n\n".join(syllabi_parts)

    msg = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system=(
            f"You are a concise academic assistant for a UW student. Today is {today}. "
            "Answer in 1-3 short sentences. Be direct. Use only the provided data."
        ),
        messages=[{"role": "user", "content": f"{context}\n\nQuestion: {question}"}],
    )
    return jsonify({"answer": msg.content[0].text})


# ── Start scheduler + Flask ────────────────────────────────────────────────────
if __name__ == "__main__":
    # scheduler = BackgroundScheduler(timezone="America/Los_Angeles")
    # scheduler.add_job(run_agent, "cron", hour=9, minute=0)
    # scheduler.start()
    # log.info("Scheduler started — agent runs daily at 9am Seattle time")

    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
