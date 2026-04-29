#!/usr/bin/env python3
"""
UW Course Agent
---------------
Gives the LLM a high-level goal and lets it navigate completely on its own.
Runs daily via GitHub Actions, stores hw/deadlines in Supabase.
"""

import os
import json
import asyncio
import logging
from datetime import date
from supabase import create_client
from browser_use import Agent
from langchain_anthropic import ChatAnthropic

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SUPABASE_URL      = os.environ["SUPABASE_URL"]
SUPABASE_KEY      = os.environ["SUPABASE_KEY"]

# Just list your classes — agent figures everything else out
CLASSES = [
    "CSE 121",
    "MATH 124",
    "ENGL 131",
]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
llm      = ChatAnthropic(model="claude-opus-4-5", api_key=ANTHROPIC_API_KEY)


# ── Task prompt ────────────────────────────────────────────────────────────────
def build_task(class_name: str) -> str:
    today = date.today().isoformat()
    return f"""
You are helping a University of Washington Seattle student find homework and deadlines for {class_name}.

Today is {today}.

What to do:
- Search Google for "uw {class_name}" and find the official UW course website
- The site likely has multiple quarters listed — find and navigate to the most current one
- You are now on the course wbesite. Explore the site freely to find any homework, projects, quizzes, exams, or deadlines
- You likely need to check schedule, assignment page. 

Once done, return ONLY a JSON object like this (no explanation, no markdown):
{{
  "class": "{class_name}",
  "items": [
    {{
      "title": "Homework 1",
      "due_date": "2025-04-15 23:59",
      "type": "homework",
      "description": "Brief description if available"
    }}
  ]
}}

Rules:
- due_date must be YYYY-MM-DD HH:MM format (24hr). Example: "2025-04-15 23:59"
- If no time is listed assume 11:59pm that day
- If only month/day is given assume current year
- type must be one of: homework, project, quiz, exam, reading, other
- If no due date found at all, set to null
- If nothing found at all, return {{"class": "{class_name}", "items": []}}
"""


# ── Save to Supabase ───────────────────────────────────────────────────────────
def save_items(class_name: str, items: list[dict]):
    if not items:
        log.info("No items found for %s", class_name)
        return

    rows = [
        {
            "class":       class_name,
            "title":       item.get("title", "Untitled"),
            "due_date":    item.get("due_date"),
            "type":        item.get("type", "other"),
            "description": item.get("description", ""),
            "notified":    False,
        }
        for item in items
    ]

    # upsert so re-runs never create duplicates
    supabase.table("assignments") \
        .upsert(rows, on_conflict="class,title") \
        .execute()

    log.info("Saved %d items for %s", len(rows), class_name)


# ── Run one class ──────────────────────────────────────────────────────────────
async def process_class(class_name: str):
    log.info("Starting agent for %s", class_name)

    agent = Agent(
        task=build_task(class_name),
        llm=llm,
    )

    try:
        result = await agent.run()
        raw = result.final_result() if hasattr(result, "final_result") else str(result)
        data = json.loads(raw)
        save_items(class_name, data.get("items", []))

    except json.JSONDecodeError:
        log.error("Could not parse JSON for %s: %s", class_name, raw[:300])
    except Exception as e:
        log.error("Agent failed for %s: %s", class_name, e)


# ── Main ───────────────────────────────────────────────────────────────────────
async def main():
    log.info("=== UW Course Agent — %s ===", date.today().isoformat())
    for class_name in CLASSES:
        await process_class(class_name)
    log.info("=== All classes processed ===")


if __name__ == "__main__":
    asyncio.run(main())