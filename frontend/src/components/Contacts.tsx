import { useEffect, useRef, useState } from 'react'
import { api, FavoriteResponse } from '../api/client'
import { usePolling } from '../hooks/usePolling'

const TOTAL_SLOTS = 10

interface EditForm {
  slot:        number
  name:        string
  telegram_id: string
}

export function Contacts() {
  const { data: contacts, loading, refetch } =
    usePolling<FavoriteResponse[]>(() => api.contacts.list(), 5000)

  const [editing, setEditing]   = useState<EditForm | null>(null)
  const [saving,  setSaving]    = useState(false)
  const [deleting, setDeleting] = useState<number | null>(null)
  const editPanelRef            = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (editing !== null) {
      editPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [editing?.slot])

  const contactMap = new Map<number, FavoriteResponse>(
    (contacts ?? []).map(c => [c.slot, c])
  )

  const openNew = (slot: number) =>
    setEditing({ slot, name: '', telegram_id: '' })

  const openEdit = (c: FavoriteResponse) =>
    setEditing({ slot: c.slot, name: c.name, telegram_id: c.telegram_id })

  const handleSave = async () => {
    if (!editing || !editing.name.trim() || !editing.telegram_id.trim()) return
    setSaving(true)
    try {
      await api.contacts.upsert(editing.slot, {
        name:        editing.name.trim(),
        telegram_id: editing.telegram_id.trim(),
      })
      setEditing(null)
      refetch()
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (slot: number) => {
    setDeleting(slot)
    try { await api.contacts.delete(slot); refetch() }
    finally { setDeleting(null) }
  }

  return (
    <div className="col gap-lg">

      <div className="card">
        <div className="card-title">Favorites (max 10)</div>
        <p className="text-xs text-muted mb-sm">
          These are the 10 contacts the user can send messages to.
          Slots are addressed by number on the glove.
        </p>

        {loading && <p className="text-muted text-sm">Loading…</p>}

        <div className="contacts-grid">
          {Array.from({ length: TOTAL_SLOTS }, (_, i) => {
            const c    = contactMap.get(i)
            const isEditing = editing?.slot === i
            return (
              <div
                key={i}
                className={`slot ${c ? '' : 'empty'} ${isEditing ? 'selected' : ''}`}
                onClick={!c ? () => openNew(i) : undefined}
              >
                <span className="slot-num">#{i}</span>
                {c ? (
                  <>
                    <span className="slot-name">{c.name}</span>
                    <span className="slot-id">{c.telegram_id}</span>
                    <div className="row gap-xs mt-sm" style={{ marginTop: 'auto' }}>
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={() => openEdit(c)}
                      >Edit</button>
                      <button
                        className="btn btn-sm btn-danger"
                        disabled={deleting === i}
                        onClick={() => handleDelete(i)}
                      >{deleting === i ? '…' : 'Del'}</button>
                    </div>
                  </>
                ) : (
                  <span className="text-xs text-muted uppercase">+ Add</span>
                )}
              </div>
            )
          })}
        </div>

        {/* ── Edit panel ── */}
        {editing !== null && (
          <div className="slot-edit-panel" ref={editPanelRef}>
            <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
              <p className="text-xs uppercase" style={{ fontWeight: 700, letterSpacing: '0.12em', margin: 0 }}>
                {contactMap.has(editing.slot) ? `Editing Slot #${editing.slot}` : `Add to Slot #${editing.slot}`}
              </p>
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => setEditing(null)}
                style={{ lineHeight: 1, padding: '2px 8px', fontSize: '1rem' }}
                aria-label="Close"
              >×</button>
            </div>
            <div className="grid-2">
              <div className="field">
                <label className="field-label">Name</label>
                <input
                  className="field-input"
                  value={editing.name}
                  placeholder="e.g. Mum"
                  onChange={e => setEditing({ ...editing, name: e.target.value })}
                />
              </div>
              <div className="field">
                <label className="field-label">Telegram Chat ID</label>
                <input
                  className="field-input"
                  value={editing.telegram_id}
                  placeholder="e.g. 123456789"
                  onChange={e => setEditing({ ...editing, telegram_id: e.target.value })}
                />
              </div>
            </div>
            <div className="row gap-sm">
              <button
                className="btn btn-primary"
                disabled={saving || !editing.name.trim() || !editing.telegram_id.trim()}
                onClick={handleSave}
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button className="btn btn-secondary" onClick={() => setEditing(null)}>
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

    </div>
  )
}
