import { createSupabaseClient } from '../../../lib/supabase'

export async function GET() {
  const supabase = createSupabaseClient()
  const today = new Date().toISOString().split('T')[0]

  const { data, error } = await supabase
    .from('assignments')
    .select('class, title, due_date, type')
    .gte('due_date', `${today}T00:00:00`)
    .lte('due_date', `${today}T23:59:59`)
    .order('due_date', { ascending: true })

  if (error) return Response.json({ error: error.message }, { status: 500 })
  return Response.json({ items: data })
}
