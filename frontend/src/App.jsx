import { BrowserRouter as Router, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Fingerprint, ScanSearch, Link2, BarChart3, FlaskConical, FileSearch, Radar, Menu, X, Sun, Moon } from 'lucide-react'
import { useState, useEffect } from 'react'
import ErrorBoundary from './components/ErrorBoundary'
import Overview from './pages/Overview'
import ScanURL from './pages/ScanURL'
import History from './pages/History'
import Analytics from './pages/Analytics'
import ModelAPI from './pages/ModelAPI'
import Report from './pages/Report'
import NotFound from './pages/NotFound'
import { api } from './services/api'

const navItems = [
  { path: '/', label: 'Overview', icon: Radar },
  { path: '/scan', label: 'Scan', icon: ScanSearch },
  { path: '/history', label: 'History', icon: Link2 },
  { path: '/analytics', label: 'Analytics', icon: BarChart3 },
  { path: '/model-api', label: 'Model & API', icon: FlaskConical },
  { path: '/report', label: 'Report', icon: FileSearch },
]

function Rail({ mobileOpen, setMobileOpen }) {
  const location = useLocation()

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape' && mobileOpen) setMobileOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [mobileOpen, setMobileOpen])

  return (
    <>
      {mobileOpen && (
        <div
          className="no-print fixed inset-0 z-40 bg-black/70 lg:hidden"
          onClick={() => setMobileOpen(false)}
          role="button"
          tabIndex={-1}
          aria-label="Close menu"
        />
      )}

      <aside
        className={`
          no-print fixed top-0 left-0 z-50 flex h-full w-60 flex-col
          border-r border-hairline bg-void
          transition-transform duration-200 ease-out
          lg:translate-x-0
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="border-b border-hairline px-6 py-6">
          <div className="flex items-center gap-2.5">
            <Fingerprint className="h-6 w-6 text-signal" strokeWidth={2} aria-hidden="true" />
            <div>
              <p className="font-display text-base uppercase leading-none text-bone">PhishGuard</p>
              <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.22em] text-bone/60">Evidence bench</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Primary">
          <ul className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = item.path === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.path)
              return (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    onClick={() => setMobileOpen(false)}
                    aria-current={isActive ? 'page' : undefined}
                    className={`
                      flex items-center gap-3 rounded-sharp border px-4 py-2.5
                      font-mono text-xs uppercase tracking-[0.14em]
                      transition-colors duration-150
                      ${isActive
                        ? 'border-signal bg-signal-dim text-signal'
                        : 'border-transparent text-steel hover:border-hairline hover:text-bone'
                      }
                    `}
                  >
                    <Icon className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
                    {item.label}
                    {isActive && <span className="ml-auto h-1.5 w-1.5 bg-signal" aria-hidden="true" />}
                  </NavLink>
                </li>
              )
            })}
          </ul>
        </nav>

        <div className="border-t border-hairline px-6 py-5">
          <p className="eyebrow mb-2">Chain of custody</p>
          <p className="font-mono text-[11px] leading-relaxed text-bone/60">
            RF-V1 · SHAP TREE
            <br />
            LOCAL BENCH ONLY
          </p>
        </div>
      </aside>
    </>
  )
}

function CustodyBar({ onMenu, menuOpen, theme, onToggleTheme }) {
  const location = useLocation()
  const [clock, setClock] = useState('')
  const [model, setModel] = useState(null)
  const [benchDown, setBenchDown] = useState(false)

  useEffect(() => {
    const tick = () => {
      const d = new Date()
      setClock(d.toISOString().substring(11, 19) + 'Z')
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    api.modelInfo().then(setModel).catch(() => setBenchDown(true))
  }, [])

  const current = [...navItems].reverse().find((n) => n.path !== '/' && location.pathname.startsWith(n.path))
    || navItems.find((n) => n.path === location.pathname)
    || { label: 'PhishGuard' }

  return (
    <header className="no-print sticky top-0 z-30 border-b border-hairline bg-void/90 backdrop-blur-sm">
      <div className="flex items-center gap-4 px-4 py-3 lg:px-8">
        <button
          className="rounded-sharp border border-hairline p-2 text-bone lg:hidden"
          onClick={onMenu}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
        >
          {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>

        <p className="font-display text-sm uppercase tracking-wide text-bone">{current.label}</p>

        <div className="ml-auto flex items-center gap-3 font-mono text-[11px] text-steel sm:gap-4">
          <span className="hidden items-center gap-1.5 md:flex">
            <span className={`h-1.5 w-1.5 ${benchDown ? 'bg-danger' : 'bg-safe'}`} aria-hidden="true" />
            {benchDown ? 'BENCH OFFLINE' : 'BENCH LIVE'}
          </span>
          <span className="hidden sm:inline">{model ? String(model.version ?? '').toUpperCase() : benchDown ? 'MODEL OFFLINE' : 'MODEL …'}</span>
          <button
            onClick={onToggleTheme}
            role="switch"
            aria-checked={theme === 'light'}
            aria-label="Color theme"
            title={theme === 'light' ? 'Light mode on — switch to evidence-room dark' : 'Dark mode on — switch to daylight lab'}
            className={`flex items-center gap-2 rounded-sharp border px-2.5 py-1.5 transition-colors hover:border-signal hover:text-signal ${
              theme === 'light'
                ? 'border-signal bg-signal-dim text-signal'
                : 'border-hairline text-steel'
            }`}
          >
            {theme === 'light' ? (
              <Sun className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
            ) : (
              <Moon className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
            )}
            <span className="hidden sm:inline">{theme === 'light' ? 'LIGHT' : 'DARK'}</span>
          </button>
          <span className="text-bone" aria-label="Current UTC time">{clock}</span>
        </div>
      </div>
    </header>
  )
}

function AnimatedRoutes() {
  const location = useLocation()

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -6 }}
        transition={{ duration: 0.22, ease: 'easeOut' }}
      >
        <Routes location={location}>
          <Route path="/" element={<Overview />} />
          <Route path="/scan" element={<ScanURL />} />
          <Route path="/history" element={<History />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/model-api" element={<ModelAPI />} />
          <Route path="/report" element={<Report />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  )
}

function MobileBar() {
  const location = useLocation()
  // Report stays reachable via the rail/hamburger only — 5 slots fit the bar.
  const items = navItems.slice(0, 5)

  return (
    <nav className="no-print fixed bottom-0 left-0 right-0 z-40 border-t border-hairline bg-void/95 backdrop-blur-sm lg:hidden" aria-label="Mobile">
      <ul className="grid grid-cols-5">
        {items.map((item) => {
          const Icon = item.icon
          const isActive = item.path === '/'
            ? location.pathname === '/'
            : location.pathname.startsWith(item.path)
          return (
            <li key={item.path}>
              <NavLink
                to={item.path}
                aria-current={isActive ? 'page' : undefined}
                className={`flex flex-col items-center gap-1 py-2.5 font-mono text-[9px] uppercase tracking-[0.12em] ${
                  isActive ? 'text-signal' : 'text-bone/50'
                }`}
              >
                <Icon className="h-5 w-5" strokeWidth={2} aria-hidden="true" />
                {item.label.split(' ')[0]}
              </NavLink>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

function getInitialTheme() {
  try {
    const saved = localStorage.getItem('phishguard-theme')
    if (saved === 'light' || saved === 'dark') return saved
  } catch { /* private mode */ }
  return 'dark'
}

export default function App() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [theme, setTheme] = useState(getInitialTheme)

  useEffect(() => {
    document.documentElement.classList.toggle('light', theme === 'light')
    try {
      localStorage.setItem('phishguard-theme', theme)
    } catch { /* private mode */ }
  }, [theme])

  const toggleTheme = () => setTheme((t) => (t === 'light' ? 'dark' : 'light'))

  return (
    <Router>
      <a href="#main-content" className="skip-link">Skip to evidence</a>
      <div className="min-h-screen bg-void text-bone">
        <Rail mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />

        <div className="min-h-screen lg:ml-60">
          <CustodyBar onMenu={() => setMobileOpen((v) => !v)} menuOpen={mobileOpen} theme={theme} onToggleTheme={toggleTheme} />

          <main id="main-content" tabIndex={-1} className="px-4 pb-28 pt-6 sm:px-6 lg:px-10 lg:pt-10">
            <div className="mx-auto max-w-page">
              <ErrorBoundary>
                <AnimatedRoutes />
              </ErrorBoundary>
            </div>
          </main>

          <footer className="no-print border-t border-hairline px-4 py-5 sm:px-6 lg:px-10">
            <p className="mx-auto max-w-page font-mono text-[11px] uppercase tracking-[0.18em] text-steel">
              PhishGuard forensic bench · local analysis · no URL leaves this bench unlogged
            </p>
          </footer>
        </div>

        <MobileBar />
      </div>
    </Router>
  )
}
