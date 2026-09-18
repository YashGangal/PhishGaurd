import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ScanSearch, Fingerprint, ArrowRight } from 'lucide-react'
import SectionHead from '../components/SectionHead'
import UrlTreeArt from '../components/UrlTreeArt'
import VerdictTag from '../components/VerdictTag'
import { api } from '../services/api'
import { truncateUrl } from '../utils/helpers'

function RadarDial({ live }) {
  return (
    <div className="relative mx-auto h-36 w-36" role="img" aria-label={live ? 'Live monitoring indicator' : 'Monitoring idle'}>
      <svg viewBox="0 0 144 144" className="h-full w-full">
        <circle cx="72" cy="72" r="66" fill="none" className="stroke-hairline" strokeWidth="1" />
        <circle cx="72" cy="72" r="44" fill="none" className="stroke-hairline" strokeWidth="1" />
        <circle cx="72" cy="72" r="22" fill="none" className="stroke-hairline" strokeWidth="1" />
        <line x1="72" y1="6" x2="72" y2="138" className="stroke-hairline" strokeWidth="1" />
        <line x1="6" y1="72" x2="138" y2="72" className="stroke-hairline" strokeWidth="1" />
        {live && (
          <g className="radar-sweep">
            <line x1="72" y1="72" x2="72" y2="10" className="stroke-signal" strokeWidth="2" />
            <circle cx="72" cy="72" r="3" className="fill-signal" />
          </g>
        )}
        {!live && <circle cx="72" cy="72" r="3" className="fill-steel" />}
        {live && <circle cx="102" cy="52" r="4" className="fill-safe" />}
      </svg>
    </div>
  )
}

export default function Overview() {
  const navigate = useNavigate()
  const [quickUrl, setQuickUrl] = useState('')
  const [health, setHealth] = useState(null)
  const [healthFailed, setHealthFailed] = useState(false)
  const [model, setModel] = useState(null)
  const [recent, setRecent] = useState([])
  const [totals, setTotals] = useState({ total: null, phishing: null })

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealthFailed(true))
    api.modelInfo().then(setModel).catch(() => {})
    api.history({ per_page: 5 }).then((r) => setRecent(r.items)).catch(() => {})
    api.history({ per_page: 1 }).then((r) => setTotals((t) => ({ ...t, total: r.pagination.total_items }))).catch(() => {})
    api.history({ per_page: 1, prediction: 'phishing' })
      .then((r) => setTotals((t) => ({ ...t, phishing: r.pagination.total_items })))
      .catch(() => {})
  }, [])

  const submit = (e) => {
    e.preventDefault()
    if (!quickUrl.trim()) return
    navigate(`/scan?url=${encodeURIComponent(quickUrl.trim())}`)
  }

  const live = health?.status === 'ok'

  return (
    <div className="space-y-10">
      {/* HERO: quick-scan is the hero */}
      <section className="grid gap-6 lg:grid-cols-12">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="panel p-6 sm:p-8 lg:col-span-7 lg:p-10"
        >
          <p className="eyebrow mb-3">01 · Exhibit intake</p>
          <h1 className="font-display text-5xl uppercase leading-[0.95] text-bone sm:text-6xl lg:text-6xl">
            Submit<br />evidence
          </h1>
          <span className="mt-3 block h-1 w-16 bg-signal" aria-hidden="true" />
          <p className="mt-4 max-w-md text-sm leading-relaxed text-steel">
            One URL in. A verdict out — with the five signals that decided it, measured and cited.
          </p>
          {healthFailed && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 rounded-sharp border border-caution bg-caution-dim px-4 py-3 font-mono text-xs text-caution"
              role="alert"
            >
              ⚠ API backend unavailable — demo mode. Scans use heuristic rules locally; real ML verdicts need the backend (see README).
            </motion.div>
          )}

          <form onSubmit={submit} className="mt-6 flex flex-col gap-3 sm:flex-row">
            <label htmlFor="quick-url" className="sr-only">URL to scan</label>
            <input
              id="quick-url"
              type="url"
              value={quickUrl}
              onChange={(e) => setQuickUrl(e.target.value)}
              placeholder="https://suspicious-link.example/verify"
              className="input-mono"
              autoComplete="off"
              spellCheck="false"
            />
            <button type="submit" disabled={!quickUrl.trim()} className="btn-scan inline-flex items-center justify-center gap-2 whitespace-nowrap">
              <ScanSearch className="h-4 w-4" strokeWidth={2.5} aria-hidden="true" />
              Scan
            </button>
          </form>

          <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-2 font-mono text-[11px] text-steel">
            <span><span className="text-bone">{totals.total ?? '—'}</span> EXHIBITS LOGGED</span>
            <span><span className="text-danger">{totals.phishing ?? '—'}</span> FLAGGED</span>
            <span className="inline-flex items-center gap-1.5">
              <Fingerprint className="h-3.5 w-3.5 text-signal" aria-hidden="true" />
              SHAP-CITED EVERY TIME
            </span>
          </div>
        </motion.div>

        {/* Instrument stack */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.08 }}
          className="flex flex-col gap-6 lg:col-span-5"
        >
          <div className="panel p-6">
            <div className="mb-4 flex items-center justify-between">
              <p className="eyebrow">Bench status · live</p>
              <span className="inline-flex items-center gap-1.5 font-mono text-[11px] text-safe">
                <span className="h-1.5 w-1.5 bg-safe" aria-hidden="true" />
                {live ? 'LIVE' : healthFailed ? 'OFFLINE' : '…'}
              </span>
            </div>
            <RadarDial live={live} />
            <dl className="mt-4 space-y-2 font-mono text-xs">
              {[
                ['MODEL', health?.model_loaded ? 'LOADED' : '—', health?.model_loaded],
                ['DATABASE', health?.database_connected ? 'CONNECTED' : '—', health?.database_connected],
                ['ACTIVE MODEL', model ? String(model.version ?? '').toUpperCase() : '—', true],
              ].map(([k, v, ok]) => (
                <div key={k} className="flex items-center justify-between border-t border-hairline pt-2">
                  <dt className="text-steel">{k}</dt>
                  <dd className={ok ? 'text-bone' : 'text-steel'}>{v}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="panel p-6">
            <p className="eyebrow mb-3">What the light reveals</p>
            <UrlTreeArt />
          </div>
        </motion.div>
      </section>

      {/* Recent exhibits */}
      <section>
        <SectionHead index="02" title="Recent exhibits" hint="newest first" />
        {recent.length === 0 ? (
          <div className="panel p-8 text-center">
            <p className="font-mono text-xs text-steel">{healthFailed ? 'BENCH UNREACHABLE — IS THE BACKEND (:8000) RUNNING?' : 'NO EXHIBITS ON RECORD — SUBMIT THE FIRST URL.'}</p>
            <Link to="/scan" className="btn-ghost mt-4 inline-flex items-center gap-2">
              Open scan bench <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        ) : (
          <ul className="divide-y divide-hairline border border-hairline bg-panel">
            {recent.map((item, i) => (
              <motion.li
                key={item.scan_id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center"
              >
                <span className="font-mono text-[11px] text-steel">{String(item.scan_id).padStart(4, '0')}</span>
                <span className="min-w-0 flex-1 truncate font-mono text-sm text-bone">{truncateUrl(item.url, 64)}</span>
                <span className="flex items-center gap-3">
                  <VerdictTag prediction={item.prediction} risk_level={item.risk_level} />
                  <span className="font-mono text-xs text-steel">{Math.round(item.confidence * 100)}%</span>
                </span>
              </motion.li>
            ))}
          </ul>
        )}
      </section>

      {/* Model strip */}
      {model && (
        <section>
          <SectionHead index="03" title="Loaded instrument" hint={model.version} />
          <div className="grid grid-cols-2 gap-px border border-hairline bg-hairline sm:grid-cols-3 lg:grid-cols-6">
            {[
              ['MODEL', String(model.model_name ?? '').toUpperCase()],
              ['ACCURACY', `${(model.accuracy * 100).toFixed(2)}%`],
              ['PRECISION', `${(model.precision * 100).toFixed(2)}%`],
              ['RECALL', `${(model.recall * 100).toFixed(2)}%`],
              ['F1', `${(model.f1_score * 100).toFixed(2)}%`],
              ['ROC-AUC', model.roc_auc.toFixed(4)],
            ].map(([k, v]) => (
              <div key={k} className="bg-panel p-5">
                <p className="eyebrow mb-1.5">{k}</p>
                <p className="font-mono text-sm text-bone">{v}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 flex items-center gap-3">
            <Link to="/analytics" className="btn-ghost inline-flex items-center gap-2">
              Full evaluation matrix <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </section>
      )}
    </div>
  )
}
