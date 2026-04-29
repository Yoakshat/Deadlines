'use client'
import { useState, useEffect } from 'react'

const COLORS = ['#7F77DD','#1D9E75','#D85A30','#378ADD','#BA7517','#D4537E','#639922']

export default function Dashboard() {
  const [classes, setClasses] = useState([])
  const [input, setInput]     = useState('')
  const [loading, setLoading] = useState(true)
  const [adding, setAdding]   = useState(false)

  useEffect(() => { fetchClasses() }, [])

  async function fetchClasses() {
    const res  = await fetch('/api/classes')
    const data = await res.json()
    setClasses(data)
    setLoading(false)
  }

  async function addClass() {
    const name = input.trim().toUpperCase()
    if (!name) return
    setAdding(true)
    await fetch('/api/classes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    })
    setInput('')
    await fetchClasses()
    setAdding(false)
  }

  async function deleteClass(id) {
    await fetch('/api/classes', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id })
    })
    await fetchClasses()
  }

  function formatDate(dateStr) {
    if (!dateStr) return null
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  return (
    <main style={{ maxWidth: 420, margin: '2rem auto', padding: '0 1rem', fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: 22, fontWeight: 500, margin: 0 }}>My classes</h1>
        <p style={{ fontSize: 14, color: '#888', marginTop: 4 }}>Agent checks these daily for homework and deadlines</p>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: '1.5rem' }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && addClass()}
          placeholder="e.g. CSE 121"
          style={{ flex: 1, height: 36, padding: '0 12px', border: '0.5px solid #ccc', borderRadius: 8, fontSize: 14, outline: 'none' }}
        />
        <button
          onClick={addClass}
          disabled={adding}
          style={{ height: 36, padding: '0 16px', border: '0.5px solid #ccc', borderRadius: 8, background: 'white', fontSize: 14, cursor: adding ? 'not-allowed' : 'pointer', opacity: adding ? 0.6 : 1 }}
        >
          {adding ? '...' : 'Add'}
        </button>
      </div>

      <div style={{ fontSize: 12, color: '#aaa', marginBottom: 8 }}>Tracked classes</div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#aaa', fontSize: 14 }}>Loading...</div>
      ) : classes.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#aaa', fontSize: 14 }}>No classes added yet</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {classes.map((cls, i) => (
            <div key={cls.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: 'white', border: '0.5px solid #eee', borderRadius: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[i % COLORS.length], flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: 15 }}>{cls.name}</div>
                  <div style={{ fontSize: 12, color: '#aaa', marginTop: 2 }}>
                    {cls.last_checked ? `last checked ${formatDate(cls.last_checked)}` : 'will check tomorrow'}
                  </div>
                </div>
              </div>
              <button
                onClick={() => deleteClass(cls.id)}
                style={{ width: 28, height: 28, border: 'none', background: 'none', color: '#bbb', fontSize: 18, cursor: 'pointer', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                onMouseEnter={e => { e.target.style.background = '#fff0f0'; e.target.style.color = '#e24b4a' }}
                onMouseLeave={e => { e.target.style.background = 'none'; e.target.style.color = '#bbb' }}
              >×</button>
            </div>
          ))}
        </div>
      )}
    </main>
  )
}
