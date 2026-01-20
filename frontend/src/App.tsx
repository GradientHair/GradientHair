import { useEffect, useMemo, useRef, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

type Participant = {
  name: string
  role?: string
}

type DemoScriptSummary = {
  id: string
  title: string
  description?: string
  agenda: string[]
  participants: Participant[]
}

type MeetingRecord = {
  id: string
  title: string
  agenda: string
  participants: Participant[]
  status: 'preparing' | 'in_progress' | 'completed'
  created_at: string
  started_at?: string | null
  ended_at?: string | null
}

type DemoEvent = {
  id: string
  type: 'system' | 'transcript' | 'intervention' | 'recap' | 'meeting_end'
  delay_ms: number
  payload: any
}

type TranscriptEntry = {
  id: string
  speaker: string
  text: string
  timestamp: string
}

type Intervention = {
  id: string
  type: string
  message: string
  timestamp: string
  metadata?: Record<string, any>
  playAlertSound?: boolean
}

type RecapData = {
  summary: string
  decisions: string[]
  actionItems: Array<{ description: string; assignee?: string; dueDate?: string; context?: string }>
  risks: string[]
  source?: string
}

const emptyParticipant = (): Participant => ({ name: '', role: '' })

export default function App() {
  const [scripts, setScripts] = useState<DemoScriptSummary[]>([])
  const [selectedScript, setSelectedScript] = useState<string>('')
  const [title, setTitle] = useState('')
  const [agenda, setAgenda] = useState('')
  const [participants, setParticipants] = useState<Participant[]>([emptyParticipant()])
  const [meeting, setMeeting] = useState<MeetingRecord | null>(null)
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([])
  const [interventions, setInterventions] = useState<Intervention[]>([])
  const [iceBreaker, setIceBreaker] = useState<any | null>(null)
  const [recap, setRecap] = useState<RecapData | null>(null)
  const [savedFiles, setSavedFiles] = useState<string[]>([])
  const [status, setStatus] = useState<'idle' | 'running' | 'done'>('idle')
  const [error, setError] = useState<string | null>(null)
  const timersRef = useRef<number[]>([])

  useEffect(() => {
    fetch(`${API_BASE}/api/demo/scripts`)
      .then((res) => res.json())
      .then((data) => {
        setScripts(data.scripts || [])
        if (data.scripts?.length) {
          setSelectedScript(data.scripts[0].id)
        }
      })
      .catch(() => setScripts([]))
  }, [])

  const speakerStats = useMemo(() => {
    const counts: Record<string, number> = {}
    transcripts.forEach((entry) => {
      counts[entry.speaker] = (counts[entry.speaker] || 0) + 1
    })
    return participants.map((participant) => ({
      name: participant.name,
      role: participant.role,
      count: counts[participant.name] || 0
    }))
  }, [participants, transcripts])

  const applyScriptDefaults = () => {
    const script = scripts.find((item) => item.id === selectedScript)
    if (!script) return
    setTitle(script.title)
    setAgenda(script.agenda.map((item, idx) => `${idx + 1}. ${item}`).join('\n'))
    setParticipants(script.participants.map((p) => ({ name: p.name, role: p.role })))
  }

  const resetDemo = () => {
    timersRef.current.forEach((timer) => window.clearTimeout(timer))
    timersRef.current = []
    setMeeting(null)
    setTranscripts([])
    setInterventions([])
    setIceBreaker(null)
    setRecap(null)
    setSavedFiles([])
    setStatus('idle')
    setError(null)
  }

  const startMeeting = async () => {
    setError(null)

    const filteredParticipants = participants.filter((p) => p.name.trim())
    if (!title.trim() || !agenda.trim() || filteredParticipants.length === 0) {
      setError('Please provide title, agenda, and at least one participant.')
      return
    }

    const payload = {
      title: title.trim(),
      agenda: agenda.trim(),
      participants: filteredParticipants,
      demo_script_id: selectedScript || null
    }

    try {
      const createRes = await fetch(`${API_BASE}/api/meetings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (!createRes.ok) {
        throw new Error('Failed to create meeting')
      }
      const meetingRecord = (await createRes.json()) as MeetingRecord
      setMeeting(meetingRecord)

      const startRes = await fetch(`${API_BASE}/api/meetings/${meetingRecord.id}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ demo_script_id: selectedScript || null })
      })
      if (!startRes.ok) {
        throw new Error('Failed to start meeting')
      }
      const data = await startRes.json()
      playEvents(data.events || [])
      setStatus('running')
    } catch (err: any) {
      setError(err.message || 'Failed to start demo')
    }
  }

  const playEvents = (events: DemoEvent[]) => {
    let totalDelay = 0
    events.forEach((event) => {
      totalDelay += event.delay_ms
      const timerId = window.setTimeout(() => {
        handleEvent(event)
      }, totalDelay)
      timersRef.current.push(timerId)
    })
  }

  const handleEvent = (event: DemoEvent) => {
    if (event.type === 'system') {
      setIceBreaker(event.payload)
    }
    if (event.type === 'transcript') {
      setTranscripts((prev) => [...prev, event.payload])
    }
    if (event.type === 'intervention') {
      setInterventions((prev) => [...prev, event.payload])
    }
    if (event.type === 'recap') {
      setRecap(event.payload)
    }
    if (event.type === 'meeting_end') {
      setSavedFiles(event.payload.savedFiles || [])
      setStatus('done')
    }
  }

  return (
    <div className="app">
      <header className="hero">
        <div>
          <p className="eyebrow">Meeting Operator Demo</p>
          <h1>Run a guided meeting with live moderation, even before the live stream ships.</h1>
          <p className="subtitle">
            This demo shows the flow: upload attendees, title, and agenda → ice breaker attendance
            check → corrections & interventions → recap and action items.
          </p>
        </div>
        <div className="hero-card">
          <div className="hero-card-label">Future Live Stream</div>
          <div className="hero-card-body">
            <div className="live-dot" />
            <p>Streaming capture integrates next. Today we simulate the operator timeline with test text.</p>
            <small>Planned: WebRTC + OpenAI Realtime API</small>
          </div>
        </div>
      </header>

      <main className="grid">
        <section className="panel">
          <div className="panel-header">
            <h2>1. Meeting Setup</h2>
            <div className="actions">
              <button type="button" className="ghost" onClick={applyScriptDefaults}>
                Apply demo defaults
              </button>
            </div>
          </div>

          <div className="field">
            <label>Demo script</label>
            <select
              value={selectedScript}
              onChange={(event) => setSelectedScript(event.target.value)}
            >
              {scripts.map((script) => (
                <option key={script.id} value={script.id}>
                  {script.title}
                </option>
              ))}
            </select>
            {scripts.length > 0 && (
              <p className="hint">{scripts.find((s) => s.id === selectedScript)?.description}</p>
            )}
          </div>

          <div className="field">
            <label>Meeting title</label>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="e.g. Weekly Product Sync"
            />
          </div>

          <div className="field">
            <label>Agenda</label>
            <textarea
              value={agenda}
              onChange={(event) => setAgenda(event.target.value)}
              placeholder="1. Review last sprint\n2. Plan next sprint\n3. Risks"
            />
          </div>

          <div className="field">
            <label>Participants</label>
            <div className="participant-list">
              {participants.map((participant, idx) => (
                <div key={idx} className="participant-row">
                  <input
                    value={participant.name}
                    placeholder="Name"
                    onChange={(event) => {
                      const updated = [...participants]
                      updated[idx] = { ...updated[idx], name: event.target.value }
                      setParticipants(updated)
                    }}
                  />
                  <input
                    value={participant.role}
                    placeholder="Role"
                    onChange={(event) => {
                      const updated = [...participants]
                      updated[idx] = { ...updated[idx], role: event.target.value }
                      setParticipants(updated)
                    }}
                  />
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => setParticipants(participants.filter((_, index) => index !== idx))}
                    disabled={participants.length === 1}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
            <button
              type="button"
              className="ghost"
              onClick={() => setParticipants([...participants, emptyParticipant()])}
            >
              + Add participant
            </button>
          </div>

          {error && <p className="error">{error}</p>}

          <div className="actions">
            <button type="button" className="primary" onClick={startMeeting} disabled={status === 'running'}>
              Start meeting demo
            </button>
            <button type="button" className="ghost" onClick={resetDemo}>
              Reset
            </button>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>2. Live Meeting Feed</h2>
            <span className={`status ${status}`}>{status === 'idle' ? 'waiting' : status}</span>
          </div>

          {iceBreaker && (
            <div className="icebreaker">
              <div className="badge">Ice Breaker</div>
              <p>{iceBreaker.message}</p>
            </div>
          )}

          <div className="columns">
            <div className="column">
              <h3>Transcript</h3>
              <div className="scroll">
                {transcripts.length === 0 && <p className="muted">Transcript will appear here.</p>}
                {transcripts.map((entry) => (
                  <div key={entry.id} className="transcript-row">
                    <div className="timestamp">{entry.timestamp}</div>
                    <div>
                      <strong>{entry.speaker}</strong> — {entry.text}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="column">
              <h3>Moderator Interventions</h3>
              <div className="scroll">
                {interventions.length === 0 && <p className="muted">Interventions show up when needed.</p>}
                {interventions.map((entry) => (
                  <div key={entry.id} className="intervention-card">
                    <div className="intervention-type">{entry.type.replace('_', ' ')}</div>
                    <p>{entry.message}</p>
                    {entry.metadata?.unknown_names && (
                      <small>Unknown attendees: {entry.metadata.unknown_names.join(', ')}</small>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="stats">
            <div>
              <h3>Participation</h3>
              {speakerStats.map((stat) => (
                <div key={stat.name} className="stat-row">
                  <span>{stat.name}</span>
                  <div className="bar">
                    <div style={{ width: `${Math.min(100, stat.count * 25)}%` }} />
                  </div>
                  <span className="count">{stat.count} turns</span>
                </div>
              ))}
            </div>
            <div>
              <h3>Agenda Tracker</h3>
              <ol className="agenda">
                {agenda
                  .split('\n')
                  .filter((line) => line.trim())
                  .map((line, idx) => (
                    <li key={idx}>{line.replace(/^\d+\.\s*/, '')}</li>
                  ))}
              </ol>
            </div>
          </div>
        </section>

        <section className="panel recap">
          <div className="panel-header">
            <h2>3. Meeting Recap</h2>
          </div>
          {!recap && <p className="muted">Recap appears after the meeting finishes.</p>}
          {recap && (
            <div className="recap-grid">
              <div>
                <h3>Summary</h3>
                <p>{recap.summary}</p>
              </div>
              <div>
                <h3>Decisions</h3>
                <ul>
                  {recap.decisions?.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h3>Action Items</h3>
                <ul>
                  {recap.actionItems?.map((item, idx) => (
                    <li key={idx}>
                      <strong>{item.description}</strong> — {item.assignee || 'TBD'} ({item.dueDate || 'TBD'})
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3>Risks</h3>
                <ul>
                  {recap.risks?.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
          {savedFiles.length > 0 && (
            <div className="saved">
              <h3>Saved Files</h3>
              <ul>
                {savedFiles.map((file, idx) => (
                  <li key={idx}>{file}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
