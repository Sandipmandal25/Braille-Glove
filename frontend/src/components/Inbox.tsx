import { useState } from 'react'
import { api, MessageResponse } from '../api/client'
import { usePolling } from '../hooks/usePolling'

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleString('en-IN', {
    day:    '2-digit',
    month:  'short',
    hour:   '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export function Inbox() {
  const [filter, setFilter] = useState<'all' | 'unread' | 'read'>('all')

  const { data, loading, error, refetch } = usePolling(
    () => api.messages.list(filter === 'all' ? undefined : filter),
    4000,
    [filter],
  )

  const [deleting, setDeleting] = useState<number | null>(null)

  const handleMarkRead = async (id: number) => {
    try { await api.messages.markRead(id); refetch() } catch {}
  }

  const handleDelete = async (id: number) => {
    setDeleting(id)
    try { await api.messages.delete(id); refetch() }
    finally { setDeleting(null) }
  }

  const messages: MessageResponse[] = data?.items ?? []

  return (
    <div className="col gap-lg">

      {/* ── Toolbar ── */}
      <div className="card" style={{ padding: '1rem 1.5rem' }}>
        <div className="row-between">
          <div className="row gap-sm">
            {(['all', 'unread', 'read'] as const).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`btn btn-sm ${filter === f ? 'btn-primary' : 'btn-secondary'}`}
              >
                {f}
              </button>
            ))}
          </div>
          <span className="text-xs text-muted uppercase">
            {data?.total ?? 0} total
          </span>
        </div>
      </div>

      {/* ── List ── */}
      <div className="card">
        <div className="card-title">
          {filter === 'all' ? 'All Messages' : filter === 'unread' ? 'Unread' : 'Read'}
        </div>

        {loading && <p className="text-muted text-sm">Loading…</p>}
        {error   && <p className="text-sm" style={{ color: '#c00' }}>Failed to load messages.</p>}

        {!loading && messages.length === 0 && (
          <div className="empty-state">
            <span className="empty-icon">[ ]</span>
            <span className="text-xs uppercase">No messages yet</span>
          </div>
        )}

        {messages.length > 0 && (
          <div className="msg-list">
            {messages.map(msg => (
              <div key={msg.id} className={`msg-item ${msg.status}`}>
                <div>
                  <div className="msg-header">
                    <span className="msg-sender">{msg.sender_name}</span>
                    <span className={`msg-badge ${msg.status}`}>{msg.status}</span>
                    <span className="msg-time">{formatTime(msg.timestamp)}</span>
                  </div>
                  <p className="msg-text">{msg.text}</p>
                  <p className="text-xs text-muted mt-sm">
                    from: {msg.sender_id}
                  </p>
                </div>
                <div className="row gap-xs" style={{ alignItems: 'flex-start' }}>
                  {msg.status === 'unread' && (
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => handleMarkRead(msg.id)}
                    >
                      Mark Read
                    </button>
                  )}
                  <button
                    className="btn btn-sm btn-danger"
                    disabled={deleting === msg.id}
                    onClick={() => handleDelete(msg.id)}
                    style={{ lineHeight: 1, padding: '2px 8px', fontSize: '1rem' }}
                    aria-label="Delete"
                  >
                    {deleting === msg.id ? '…' : '×'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
