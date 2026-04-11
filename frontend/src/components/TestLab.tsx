import { useRef, useState } from 'react'
import { api, DeviceStatusResponse, FavoriteResponse } from '../api/client'
import { usePolling } from '../hooks/usePolling'

interface LogLine {
  type: 'prompt' | 'success' | 'error' | 'info'
  text: string
}

// Braille dot mask for each letter a-z
const BRAILLE_LABELS: Record<string, number> = {
  a:1, b:3, c:9, d:25, e:17, f:11, g:27, h:19, i:10, j:26,
  k:5, l:7, m:13, n:29, o:21, p:15, q:31, r:23, s:14, t:30,
  u:37, v:39, w:58, x:45, y:61, z:53,
}

export function TestLab() {
  const { data: status, refetch: refetchStatus } =
    usePolling<DeviceStatusResponse>(() => api.device.status(), 2000)

  const { data: contacts } =
    usePolling<FavoriteResponse[]>(() => api.contacts.list(), 10000)

  // ── Inject state ──
  const [senderName, setSenderName] = useState('')
  const [senderId,   setSenderId]   = useState('')
  const [msgText,    setMsgText]    = useState('')
  const [sending,    setSending]    = useState(false)

  // ── Compose demo state ──
  const [dots,       setDots]       = useState<number[]>([])   // active dot buttons
  const [busy,       setBusy]       = useState(false)

  // ── Shared log ──
  const [log, setLog] = useState<LogLine[]>([
    { type: 'info', text: 'Test Lab ready.' },
    { type: 'info', text: 'Inject messages to simulate incoming Telegram traffic.' },
    { type: 'info', text: 'Use the Compose Demo to simulate button presses on the glove.' },
  ])
  const terminalRef = useRef<HTMLDivElement>(null)

  const addLog = (line: LogLine) => {
    setLog(prev => {
      const next = [...prev, line]
      setTimeout(() => {
        terminalRef.current?.scrollTo({ top: 9999, behavior: 'smooth' })
      }, 50)
      return next
    })
  }

  // ── Inject message ──
  const handleInject = async () => {
    if (!msgText.trim()) return
    setSending(true)
    const ts = new Date().toLocaleTimeString('en-IN', { hour12: false })
    addLog({ type: 'prompt', text: `[${ts}] > inject "${msgText}" from ${senderName}` })
    try {
      await api.testing.inject({
        sender_name: senderName.trim(),
        sender_id:   senderId.trim(),
        text:        msgText.trim(),
      })
      addLog({ type: 'success', text: `  ✓ Enqueued.` })
      setMsgText('')
    } catch (e) {
      addLog({ type: 'error', text: `  ✗ ${e instanceof Error ? e.message : String(e)}` })
    } finally {
      setSending(false)
    }
  }

  // ── Button press ──
  const pressButton = async (button: string, event: string, dot_mask?: number) => {
    setBusy(true)
    const label = dot_mask != null
      ? `BRAILLE dots[${dot_mask.toString(2).padStart(6,'0')}]`
      : `${button} ${event}`
    const ts = new Date().toLocaleTimeString('en-IN', { hour12: false })
    addLog({ type: 'prompt', text: `[${ts}] > ${label}` })
    try {
      const res = await api.testing.button({ button, event, dot_mask })
      addLog({ type: 'success', text: `  ✓ mode → ${res.mode}` })
      refetchStatus()
    } catch (e) {
      addLog({ type: 'error', text: `  ✗ ${e instanceof Error ? e.message : String(e)}` })
    } finally {
      setBusy(false)
    }
  }

  const toggleDot = (d: number) =>
    setDots(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d])

  const dotMaskFromSelected = () =>
    dots.reduce((acc, d) => acc | (1 << (d - 1)), 0)

  const tapChord = async () => {
    if (dots.length === 0) return
    await pressButton('BRAILLE', 'SINGLE', dotMaskFromSelected())
    setDots([])
  }

  const tapLetter = async (letter: string) => {
    const mask = BRAILLE_LABELS[letter]
    if (mask == null) return
    addLog({ type: 'info', text: `  → '${letter}' = dot_mask ${mask}` })
    await pressButton('BRAILLE', 'SINGLE', mask)
  }

  return (
    <div className="col gap-lg">

      {/* ── Live status strip ── */}
      <div className="card" style={{ padding: '1rem 1.5rem' }}>
        <div className="row gap-md">
          <span className="text-xs uppercase" style={{ fontWeight: 700 }}>Live Status:</span>
          {status ? (
            <>
              <span className={`text-xs ${status.connected ? '' : 'text-muted'}`}>
                {status.connected ? '● CONNECTED' : '○ OFFLINE'}
              </span>
              <span className="text-xs text-muted">|</span>
              <span className="text-xs">{status.mode} MODE</span>
              <span className="text-xs text-muted">|</span>
              <span className="text-xs">{status.unread_count} unread</span>
            </>
          ) : (
            <span className="text-xs text-muted">Backend unreachable</span>
          )}
        </div>
      </div>

      <div className="grid-2" style={{ alignItems: 'start' }}>

        {/* ── Left column ── */}
        <div className="col gap-lg">

          {/* Inject form */}
          <div className="card">
            <div className="card-title">Inject Incoming Message</div>
            <p className="text-xs text-muted mb-sm">
              Simulates a Telegram message arriving without a real bot.
            </p>
            <hr className="divider" />
            <div className="col gap-md">
              <div className="field">
                <label className="field-label">Sender (from Contacts)</label>
                <select
                  className="field-input"
                  value={senderId}
                  onChange={e => {
                    const c = (contacts ?? []).find(x => x.telegram_id === e.target.value)
                    setSenderId(e.target.value)
                    setSenderName(c?.name ?? '')
                  }}
                >
                  <option value="">— pick a contact or type below —</option>
                  {(contacts ?? []).map(c => (
                    <option key={c.slot} value={c.telegram_id}>
                      #{c.slot} {c.name} ({c.telegram_id})
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label className="field-label">Message Text</label>
                <textarea className="field-textarea" value={msgText}
                  placeholder="Type message… (Ctrl+Enter to send)"
                  onChange={e => setMsgText(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleInject() }}
                />
              </div>
              <button className="btn btn-primary btn-full"
                disabled={sending || !msgText.trim() || !senderName.trim() || !senderId.trim()}
                onClick={handleInject}>
                {sending ? 'Injecting…' : '▶ Inject Message'}
              </button>
            </div>
          </div>

          {/* Compose demo */}
          <div className="card">
            <div className="card-title">Compose Demo (Simulate Glove)</div>
            <p className="text-xs text-muted mb-sm">
              Simulate button presses to test READ/COMPOSE flow without hardware.
            </p>
            <hr className="divider" />

            <div className="col gap-md">

              {/* Mode control */}
              <div className="col gap-xs">
                <span className="text-xs uppercase" style={{ fontWeight: 700, letterSpacing: '0.1em' }}>
                  Mode Control
                </span>
                <div className="row gap-sm" style={{ flexWrap: 'wrap' }}>
                  <button className="btn btn-sm btn-primary" disabled={busy}
                    onClick={() => pressButton('NEXT', 'DOUBLE')}>
                    ↵ Enter Compose
                  </button>
                  <button className="btn btn-sm btn-secondary" disabled={busy}
                    onClick={() => pressButton('NEXT', 'DOUBLE')}>
                    ↩ Exit Compose
                  </button>
                </div>
              </div>

              {/* Contact selector */}
              <div className="col gap-xs">
                <span className="text-xs uppercase" style={{ fontWeight: 700, letterSpacing: '0.1em' }}>
                  Select Contact to Send To
                </span>
                <select
                  className="field-input"
                  value={status?.compose_slot ?? 0}
                  disabled={busy || status?.mode !== 'COMPOSE'}
                  onChange={async e => {
                    const slot = Number(e.target.value)
                    setBusy(true)
                    const ts = new Date().toLocaleTimeString('en-IN', { hour12: false })
                    addLog({ type: 'prompt', text: `[${ts}] > select contact slot ${slot}` })
                    try {
                      const res = await api.testing.selectContact(slot)
                      addLog({ type: 'success', text: `  ✓ contact set → ${res.mode}` })
                      refetchStatus()
                    } catch (e) {
                      addLog({ type: 'error', text: `  ✗ ${e instanceof Error ? e.message : String(e)}` })
                    } finally {
                      setBusy(false)
                    }
                  }}
                >
                  {(contacts ?? []).length === 0
                    ? <option>No contacts saved</option>
                    : (contacts ?? []).map(c => (
                        <option key={c.slot} value={c.slot}>#{c.slot} {c.name}</option>
                      ))
                  }
                </select>
                {status?.compose_text && (
                  <div style={{ border: '2px solid black', padding: '0.4rem 0.75rem', background: '#f5f5f5' }}>
                    <span className="text-xs text-muted">typed: </span>
                    <span className="text-xs" style={{ fontWeight: 700 }}>{status.compose_text}</span>
                  </div>
                )}
                <div className="row gap-sm" style={{ flexWrap: 'wrap' }}>
                  <button className="btn btn-sm btn-primary" disabled={busy}
                    onClick={() => pressButton('ENTER', 'SINGLE')}>⏎ Send Message</button>
                  <button className="btn btn-sm btn-danger" disabled={busy}
                    onClick={() => pressButton('PREV', 'DOUBLE')}>⌫ Backspace</button>
                </div>
              </div>

              {/* Braille chord input */}
              <div className="col gap-xs">
                <span className="text-xs uppercase" style={{ fontWeight: 700, letterSpacing: '0.1em' }}>
                  Braille Chord (manual)
                </span>
                <p className="text-xs text-muted">
                  Toggle dots then tap — left hand: 1·2·3 (top→bottom), right: 4·5·6
                </p>
                <div className="row gap-sm" style={{ justifyContent: 'center', padding: '0.5rem 0' }}>
                  {/* Left column: dots 1,2,3 */}
                  <div className="col gap-xs">
                    {[1,2,3].map(d => (
                      <button key={d}
                        className={`btn btn-sm ${dots.includes(d) ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => toggleDot(d)}>
                        •{d}
                      </button>
                    ))}
                  </div>
                  {/* Right column: dots 4,5,6 */}
                  <div className="col gap-xs">
                    {[4,5,6].map(d => (
                      <button key={d}
                        className={`btn btn-sm ${dots.includes(d) ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => toggleDot(d)}>
                        •{d}
                      </button>
                    ))}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', paddingLeft: '0.5rem' }}>
                    <button className="btn btn-primary" disabled={busy || dots.length === 0}
                      onClick={tapChord}>
                      Tap Chord
                    </button>
                  </div>
                </div>
              </div>

              {/* Quick letter tap */}
              <div className="col gap-xs">
                <span className="text-xs uppercase" style={{ fontWeight: 700, letterSpacing: '0.1em' }}>
                  Quick Letter Tap
                </span>
                <div className="row gap-xs" style={{ flexWrap: 'wrap' }}>
                  {Object.keys(BRAILLE_LABELS).map(l => (
                    <button key={l} className="btn btn-sm btn-secondary"
                      disabled={busy} onClick={() => tapLetter(l)}
                      style={{ minWidth: '2rem', textTransform: 'uppercase' }}>
                      {l}
                    </button>
                  ))}
                </div>
              </div>

            </div>
          </div>

        </div>

        {/* ── Activity Log ── */}
        <div className="card">
          <div className="card-title row-between">
            <span>Activity Log</span>
            <button className="btn btn-sm btn-secondary" onClick={() => setLog([])}>Clear</button>
          </div>

          <div className="terminal" ref={terminalRef}>
            {log.length === 0 && <span className="terminal-line info">No activity yet.</span>}
            {log.map((line, i) => (
              <span key={i} className={`terminal-line ${line.type}`}>{line.text}</span>
            ))}
            <span className="terminal-line prompt blink">_</span>
          </div>

          <hr className="divider" />

          <div className="col gap-xs text-xs text-muted">
            <span>DEMO FLOW (no glove needed):</span>
            <span>1. Inject an incoming message above</span>
            <span>2. Click "Enter Compose" to switch mode</span>
            <span>3. Tap letters to build a reply</span>
            <span>4. Click Next/Prev to select a contact</span>
            <span>5. Click "Enter / Send" → message goes via Telegram</span>
          </div>
        </div>

      </div>
    </div>
  )
}
