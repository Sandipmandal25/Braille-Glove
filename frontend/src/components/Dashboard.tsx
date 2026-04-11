import { api, DeviceStatusResponse } from '../api/client'
import { usePolling } from '../hooks/usePolling'

export function Dashboard() {
  const { data: status, loading, error, refetch } =
    usePolling<DeviceStatusResponse>(() => api.device.status(), 3000)

  const handleConnect = async () => {
    try { await api.device.connect(); refetch() } catch {}
  }
  const handleDisconnect = async () => {
    try { await api.device.disconnect(); refetch() } catch {}
  }

  return (
    <div className="col gap-lg">

      {/* ── Connection card ── */}
      <div className="card">
        <div className="card-title">Device Status</div>

        {loading && <p className="text-muted text-sm">Connecting to backend…</p>}

        {error && (
          <p className="text-sm" style={{ color: '#c00' }}>
            Backend unreachable — is the server running?
          </p>
        )}

        {status && (
          <>
            <div className="row gap-md" style={{ marginBottom: '0.5rem' }}>
              <span className={`status-display ${status.connected ? 'on' : 'off'}`}>
                {status.connected ? '● ONLINE' : '○ OFFLINE'}
              </span>
              {status.connected && (
                <span className={`mode-badge ${status.mode}`}>{status.mode} MODE</span>
              )}
            </div>

            <div className="stats-row">
              <div className="stat-box">
                <span className="stat-num">{status.unread_count}</span>
                <span className="stat-lbl">Unread</span>
              </div>
              <div className="stat-box">
                <span className="stat-num">{status.queue_length}</span>
                <span className="stat-lbl">In Queue</span>
              </div>
              <div className="stat-box">
                <span className="stat-num">{status.cursor_position}</span>
                <span className="stat-lbl">Cursor Pos</span>
              </div>
            </div>
          </>
        )}
      </div>

      {/* ── Controls ── */}
      <div className="grid-2">
        <div className="card">
          <div className="card-title">BLE Control</div>
          <div className="row gap-sm">
            <button className="btn btn-primary" onClick={handleConnect}>
              ▶ Connect Glove
            </button>
            <button className="btn btn-secondary" onClick={handleDisconnect}>
              ■ Disconnect
            </button>
          </div>
          <p className="text-xs text-muted mt-sm">
            CONNECT triggers a BLE scan (timeout: 10s).
            Make sure the glove is powered on first.
          </p>
        </div>

        <div className="card">
          <div className="card-title">Button Map</div>
          <div className="col gap-xs text-xs text-muted" style={{ lineHeight: 1.8 }}>
            <span><strong>PREV/NEXT</strong> → navigate messages (READ)</span>
            <span><strong>ENTER</strong> → mark read</span>
            <span><strong>2× NEXT</strong> → switch to COMPOSE</span>
            <span><strong>BRAILLE × 6</strong> → type chord</span>
            <span><strong>PREV/NEXT</strong> → scroll favorites (COMPOSE)</span>
            <span><strong>2× PREV</strong> → backspace</span>
          </div>
        </div>
      </div>

    </div>
  )
}
