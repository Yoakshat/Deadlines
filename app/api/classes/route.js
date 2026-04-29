import { supabase } from '../../../lib/supabase'

export async function GET() {
  const { data, error } = await supabase
    .from('classes')
    .select('*')
    .order('created_at', { ascending: true })

  if (error) return Response.json({ error: error.message }, { status: 500 })
  return Response.json(data)
}

export async function POST(req) {
  const { name } = await req.json()
  if (!name) return Response.json({ error: 'name required' }, { status: 400 })

  const { data, error } = await supabase
    .from('classes')
    .insert({ name: name.trim().toUpperCase() })
    .select()
    .single()

  if (error) return Response.json({ error: error.message }, { status: 500 })
  return Response.json(data)
}

export async function DELETE(req) {
  const { id } = await req.json()

  const { error } = await supabase
    .from('classes')
    .delete()
    .eq('id', id)

  if (error) return Response.json({ error: error.message }, { status: 500 })
  return Response.json({ success: true })
}
