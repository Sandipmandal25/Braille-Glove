import { useState } from 'react'
import { Dashboard } from './components/Dashboard'
import { Inbox }     from './components/Inbox'
import { Contacts }  from './components/Contacts'
import { TestLab }   from './components/TestLab'

type Tab = 'dashboard' | 'inbox' | 'contacts' | 'testlab'

const TABS: { id: Tab; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'inbox',     label: 'Inbox'     },
  { id: 'contacts',  label: 'Contacts'  },
  { id: 'testlab',   label: 'Test Lab'  },
]

export default function App() {
  const [tab, setTab] = useState<Tab>('dashboard')

  return (
    <div>
      {/* ── Header ── */}
      <header className="header">
        <div className="header-meta">
          <span className="header-title">BRAILLE GLOVE<span className="blink">_</span></span>
          <span className="header-sub">PDPM IIITDM Jabalpur · Control Panel</span>
        </div>
        <div style={{ marginLeft: 'auto' }}>
          <span className="header-pill">
            <span className="blink" style={{ fontSize: '0.5rem' }}>●</span>
            LIVE
          </span>
        </div>
      </header>

      {/* ── Nav ── */}
      <nav className="nav">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`nav-tab ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* ── Content ── */}
      <main className="main">
        {tab === 'dashboard' && <Dashboard />}
        {tab === 'inbox'     && <Inbox />}
        {tab === 'contacts'  && <Contacts />}
        {tab === 'testlab'   && <TestLab />}
      </main>
    </div>
  )
}
