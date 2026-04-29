import { supabase } from '../../../lib/supabase'
import Anthropic from '@anthropic-ai/sdk'

const client = new Anthropic()

export const maxDuration = 300 // 5 min max for browser-use

export async function GET(req) {
  // Verify this is coming from Vercel cron, not a random person hitting the URL
  const authHeader = req.headers.get('authorization')
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 })
  }

  // Fetch class list from Supabase
  const { data: classes, error } = await supabase
    .from('classes')
    .select('name')

  if (error || !classes?.length) {
    return Response.json({ error: 'No classes found' }, { status: 400 })
  }

  const today = new Date().toISOString().split('T')[0]
  const results = []

  for (const cls of classes) {
    try {
      const items = await runAgentForClass(cls.name, today)
      if (items.length > 0) {
        await upsertAssignments(cls.name, items)
      }
      results.push({ class: cls.name, found: items.length })

      // Update last_checked
      await supabase
        .from('classes')
        .update({ last_checked: new Date().toISOString() })
        .eq('name', cls.name)

    } catch (e) {
      console.error(`Agent failed for ${cls.name}:`, e.message)
      results.push({ class: cls.name, error: e.message })
    }
  }

  return Response.json({ date: today, results })
}


async function runAgentForClass(className, today) {
  // Use Claude with a computer use / tool use approach
  // browser-use runs as a subprocess via Python since Next.js is JS
  // We call our Python agent script via a Claude tool-use prompt instead
  const response = await client.messages.create({
    model: 'claude-opus-4-5',
    max_tokens: 2000,
    system: `You are a UW homework extraction assistant. Today is ${today}.
    
You will be given raw text from a UW course webpage. Extract all homework, projects, quizzes, exams, and deadlines.

Return ONLY valid JSON, no explanation:
{
  "items": [
    {
      "title": "Homework 1",
      "due_date": "2025-04-15 23:59",
      "type": "homework",
      "description": "optional short description"
    }
  ]
}

Rules:
- due_date: YYYY-MM-DD HH:MM format. Default time to 23:59 if not specified.
- type: homework | project | quiz | exam | reading | other
- If nothing found: { "items": [] }`,
    messages: [
      {
        role: 'user',
        content: `Find all assignments and deadlines for UW ${className}. 
Search for "uw ${className} course" and navigate to the most current quarter's website. 
Look through the syllabus, schedule, and assignments pages.
Return the JSON with everything you find.`
      }
    ],
    tools: [
      {
        type: 'web_search_20250305',
        name: 'web_search'
      }
    ]
  })

  // Parse the final text response
  const textBlock = response.content.find(b => b.type === 'text')
  if (!textBlock) return []

  try {
    const raw = textBlock.text.replace(/```json|```/g, '').trim()
    const data = JSON.parse(raw)
    return data.items || []
  } catch {
    console.error('JSON parse failed for', className, textBlock.text.slice(0, 200))
    return []
  }
}


async function upsertAssignments(className, items) {
  const rows = items.map(item => ({
    class: className,
    title: item.title || 'Untitled',
    due_date: item.due_date || null,
    type: item.type || 'other',
    description: item.description || '',
    notified: false
  }))

  await supabase
    .from('assignments')
    .upsert(rows, { onConflict: 'class,title' })
}
