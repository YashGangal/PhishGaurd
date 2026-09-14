import { useState, useEffect, useRef, useCallback } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ScanSearch, Copy, Check, ChevronDown, FlaskConical, FileSearch, AlertTriangle } from 'lucide-react'
import SectionHead from '../components/SectionHead'
import ScanBeam from '../components/ScanBeam'
import UrlTreeArt from '../components/UrlTreeArt'
import VerdictTag from '../components/VerdictTag'
import { api } from '../services/api'
import { getRiskColor, truncateUrl } from '../utils/helpers'
import { tierOf, VERDICT } from '../utils/verdict'
import { URL_FEATURES, HTML_FEATURES } from '../utils/features'

/* Beam floor: the ALS sweep always plays long enough to read,
   even when the classifier answers instantly. */
const MIN_BEAM_MS = 1200

function FeatureRow({ name, value }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-hairline px-4 py-2 last:border-b-0">
      <span className="font-mono text-xs text-steel">{name}</span>
      <span className="font-mono text-xs text-bone">{String(value)}</span>
    </div>
  )
}

export default function ScanURL() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [url, setUrl] = useState(searchParams.get('url') || '')
  const [scanning, setScanning] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)
  const [matrixOpen, setMatrixOpen] = useState(false)
  const [recent, setRecent] = useState([])
  const [recentFailed, setRecentFailed] = useState(false)
  const abortRef = useRef(null)
  const timerRef = useRef(null)
  const beamTimerRef = useRef(null)
  const copyTimerRef = useRef(null)
  const runRef = useRef(0)

  useEffect(() => {
    return () => {
      runRef.current += 1
      abortRef.current?.abort()
      clearInterval(timerRef.current)
      clearTimeout(beamTimerRef.current)
      clearTimeout(copyTimerRef.current)
    }
  }, [])

  const runScan = useCallback(async (target) => {
    let parsed
    try {
      parsed = new URL(target)
    } catch {
      setError('ENTER A VALID URL — SCHEME AND HOST REQUIRED (https://…)')
      return
    }
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      setError('ONLY HTTP AND HTTPS EVIDENCE ACCEPTED')
      return
    }

    const myRun = ++runRef.current
    setError('')
    setResult(null)
    setMatrixOpen(false)
    setScanning(true)
    setElapsed(0)
    abortRef.current?.abort()
    abortRef.current = new AbortController()
    clearInterval(timerRef.current)
    clearTimeout(beamTimerRef.current)
    const started = performance.now()
    timerRef.current = setInterval(() => setElapsed(performance.now() - started), 47)

    try {
      const data = await api.predict(target, abortRef.current.signal)
      const held = performance.now() - started
      if (held < MIN_BEAM_MS) {
        await new Promise((resolve) => {
          beamTimerRef.current = setTimeout(resolve, MIN_BEAM_MS - held)
        })
      }
      if (runRef.current !== myRun) return
      setResult(data)
      try {
        sessionStorage.setItem('phishguard:last-scan', JSON.stringify(data))
      } catch { /* storage unavailable */ }
    } catch (err) {
      if (runRef.current !== myRun) return
      if (err.name !== 'AbortError') setError(err.message || 'ANALYSIS FAILED — RETRY')
    } finally {
      if (runRef.current !== myRun) return
      clearInterval(timerRef.current)
      clearTimeout(beamTimerRef.current)
      setScanning(false)
    }
  }, [])

  useEffect(() => {
    api.history({ per_page: 3 }).then((r) => setRecent(r.items)).catch(() => setRecentFailed(true))
  }, [])

  useEffect(() => {
    const q = searchParams.get('url')
    if (q) {
      setUrl(q)
      runScan(q)
      setSearchParams({}, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const submit = (e) => {
    e.preventDefault()
    if (!url.trim()) {
      setError('ENTER A URL TO ANALYZE')
      return
    }
    runScan(url.trim())
  }

  const copyResult = () => {
    if (!result) return
    const signals = Array.isArray(result.top_features) ? result.top_features : []
    const lines = [
      `PHISHGUARD FORENSIC SHEET`,
      `TARGET: ${result.url ?? '—'}`,
      `VERDICT: ${String(result.prediction ?? 'unknown').toUpperCase()} (${result.risk_level ?? '—'})`,
      `CONFIDENCE: ${typeof result.confidence === 'number' ? `${(result.confidence * 100).toFixed(1)}%` : '—'}`,
      `RISK: ${result.risk_score ?? '—'}/100`,
      ...signals.map((f, i) => `E${i + 1} ${f.name}=${f.value} ${f.direction} ${(Math.abs(f.impact_score) * 100).toFixed(1)}%`),
    ]
    navigator.clipboard.writeText(lines.join('\n')).catch(() => {})
    setCopied(true)
    copyTimerRef.current = setTimeout(() => setCopied(false), 2000)
  }

  const tier = result ? tierOf(result) : 'safe'
  const danger = tier === 'danger'
  const textTone = tier === 'danger' ? 'text-danger' : tier === 'caution' ? 'text-caution' : 'text-safe'

  return (
    <div className="space-y-10">
      {/* Intake */}
      <section className="panel p-6 sm:p-8">
        <p className="eyebrow mb-3">Exhibit intake · monospace only</p>
        <form onSubmit={submit} className="flex flex-col gap-3 lg:flex-row">
          <label htmlFor="scan-url" className="sr-only">Target URL</label>
          <input
            id="scan-url"
            type="url"
            value={url}
            onChange={(e) => { setUrl(e.target.value); setError('') }}
            placeholder="https://suspicious-link.example/account/verify"
            className="input-mono lg:text-base"
            autoComplete="off"
            spellCheck="false"
          />
          <button type="submit" disabled={scanning || !url.trim()} className="btn-scan inline-flex items-center justify-center gap-2 whitespace-nowrap">
            <ScanSearch className="h-4 w-4" strokeWidth={2.5} aria-hidden="true" />
            {scanning ? 'Under light…' : 'Analyze URL'}
          </button>
        </form>
        {error && (
          <p className="mt-3 flex items-center gap-2 font-mono text-xs text-danger" role="alert">
            <AlertTriangle className="h-4 w-4" aria-hidden="true" /> {error}
          </p>
        )}
      </section>

      {/* Idle state — bench is never empty */}
      {!result && !scanning && !error && (
        <section className="grid gap-6 lg:grid-cols-12">
          <div className="lg:col-span-7">
            <SectionHead index="LOG" title="Recent activity" hint="last 3 exhibits" />
            {recent.length === 0 ? (
              <div className="panel p-6">
                <p className="font-mono text-xs text-steel">{recentFailed ? 'RECENT ACTIVITY UNREACHABLE — BACKEND DOWN?' : 'NO EXHIBITS ON RECORD — THIS SCAN WILL BE THE FIRST.'}</p>
              </div>
            ) : (
              <ul className="divide-y divide-hairline border border-hairline bg-panel">
                {recent.map((item) => (
                  <li key={item.scan_id} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center">
                    <span className="font-mono text-[11px] text-steel">{String(item.scan_id).padStart(4, '0')}</span>
                    <span className="min-w-0 flex-1 truncate font-mono text-sm text-bone" title={item.url}>{truncateUrl(item.url, 56)}</span>
                    <span className="flex items-center gap-3">
                      <VerdictTag prediction={item.prediction} risk_level={item.risk_level} />
                      <span className="font-mono text-xs text-steel">{Math.round(item.confidence * 100)}%</span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <Link to="/history" className="btn-ghost mt-4 inline-flex items-center gap-2">
              Full custody log
            </Link>
          </div>
          <div className="lg:col-span-5">
            <SectionHead index="HOW" title="What the light reveals" hint="idle diagram" />
            <div className="panel p-6">
              <UrlTreeArt />
              <p className="mt-3 font-mono text-[11px] leading-relaxed text-steel">
                EVERY URL IS SPLIT, MEASURED ACROSS 25 FEATURES, AND RANKED — NOTHING VISIBLE UNTIL THE LIGHT HITS IT.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Suspense sequence */}
      <AnimatePresence mode="wait">
        {scanning && (
          <motion.section
            key="beam"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <ScanBeam label="SCANNING" />
            <div className="mt-3 flex items-center justify-between font-mono text-[11px] text-steel">
              <span>EXTRACTING 25-FEATURE VECTOR → CLASSIFIER → SHAP</span>
              <span className="text-signal" aria-live="polite">T+{(elapsed / 1000).toFixed(2)}S</span>
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      {/* Verdict block — dominates the viewport */}
      <AnimatePresence>
        {result && !scanning && (
          <motion.section
            key={`verdict-${result.scan_id}`}
            initial={{ scale: 0.92, y: 28, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            transition={{ type: 'spring', stiffness: 380, damping: 24 }}
            className="overflow-hidden rounded-card border border-hairline bg-panel"
            aria-label="Verdict"
          >
            {danger && <div className="hazard-stripes h-2.5 w-full" aria-hidden="true" />}

            <div className="grid gap-8 p-6 sm:p-8 lg:grid-cols-12 lg:p-10">
              <div className="lg:col-span-8">
                <p className="eyebrow mb-3">Verdict · exhibit #{String(result.scan_id).padStart(4, '0')}</p>
                <h2
                  className={`font-display uppercase leading-[0.9] text-5xl sm:text-6xl lg:text-7xl ${textTone}`}
                >
                  {VERDICT[tier].headline}
                </h2>
                <div className="mt-4">
                  <VerdictTag prediction={result.prediction} riskLevel={result.risk_level} size="lg" />
                </div>
                <p className="mt-5 max-w-xl break-all font-mono text-xs leading-relaxed text-steel">
                  TARGET&nbsp;&nbsp;<span className="text-bone">{result.url}</span>
                  <br />
                  DOMAIN&nbsp;&nbsp;<span className="text-bone">{result.domain}</span>
                </p>
              </div>

              <div className="flex flex-row gap-8 lg:col-span-4 lg:flex-col lg:items-end lg:justify-center lg:border-l lg:border-hairline lg:pl-8">
                <div>
                  <p className="eyebrow mb-1">Risk score</p>
                  <p className="font-mono text-6xl leading-none lg:text-7xl">
                    <span className={getRiskColor(result.risk_score)}>{result.risk_score}</span>
                    <span className="text-xl text-steel">/100</span>
                  </p>
                </div>
                <div>
                  <p className="eyebrow mb-1">Confidence</p>
                  <p className="font-mono text-3xl text-bone">{(result.confidence * 100).toFixed(1)}%</p>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-hairline px-6 py-3 font-mono text-[11px] text-steel sm:px-8 lg:px-10">
              <span>MODEL <span className="text-bone">{result.model_version}</span></span>
              <span aria-hidden="true">·</span>
              <span>SCANNED <span className="text-bone">{new Date(result.scanned_at).toLocaleString()}</span></span>
              <span aria-hidden="true">·</span>
              <span>{result.html_features_available ? 'FULL 25-FEATURE PASS' : 'URL STRUCTURE ONLY — PAGE UNREACHABLE'}</span>
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      {/* SHAP evidence — keyed by exhibit so the stagger + bar fills
          replay from zero on every scan, not just the first */}
      {result && !scanning && (
        <section key={`evidence-${result.scan_id}`}>
          <SectionHead index="E1–E5" title="Signals the light found" hint="SHAP · ranked by contribution" />
          <ul className="space-y-3">
            {result.top_features.map((f, i) => {
              const pct = Math.min(100, Math.abs(f.impact_score) * 100)
              const up = f.direction === 'increases_risk'
              return (
                <motion.li
                  key={f.name}
                  initial={{ opacity: 0, x: -14 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.15 + i * 0.09, type: 'spring', stiffness: 260, damping: 26 }}
                  className="panel p-4 sm:p-5"
                >
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                    <span className="font-mono text-[11px] text-signal">E{i + 1}</span>
                    <span className="font-mono text-sm text-bone">{f.name}</span>
                    <span className="font-mono text-[11px] text-steel">= {String(f.value)}</span>
                    <span className={`ml-auto font-mono text-sm ${up ? 'text-signal' : 'text-steel'}`}>
                      {up ? '+' : '−'}{pct.toFixed(1)}%
                    </span>
                  </div>
                  <div className="mt-3 h-1.5 w-full bg-void" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100} aria-label={`${f.name} contribution`}>
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ delay: 0.3 + i * 0.09, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                      className={`h-full ${up ? 'bg-signal' : 'bg-steel'}`}
                    />
                  </div>
                  <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.14em] text-steel">
                    {up ? 'Pushes toward phishing' : 'Pushes toward legitimate'}
                  </p>
                </motion.li>
              )
            })}
          </ul>

          {/* 25-feature accordion */}
          <div className="mt-6 overflow-hidden rounded-card border border-hairline bg-panel">
            <button
              onClick={() => setMatrixOpen((v) => !v)}
              aria-expanded={matrixOpen}
              className="flex w-full items-center gap-3 px-4 py-4 text-left transition-colors hover:bg-panel2 sm:px-5"
            >
              <FlaskConical className="h-4 w-4 text-signal" aria-hidden="true" />
              <span className="font-display text-xs uppercase tracking-wide text-bone">Full 25-feature matrix</span>
              <span className="font-mono text-[11px] text-steel">{matrixOpen ? 'COLLAPSE' : 'EXPAND'}</span>
              <ChevronDown className={`ml-auto h-4 w-4 text-steel transition-transform duration-200 ${matrixOpen ? 'rotate-180' : ''}`} aria-hidden="true" />
            </button>
            <AnimatePresence initial={false}>
              {matrixOpen && (
                <motion.div
                  key="matrix"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
                  className="overflow-hidden"
                >
                  <div className="grid gap-px border-t border-hairline bg-hairline md:grid-cols-2">
                    <div className="bg-panel">
                      <p className="subhead border-b border-hairline px-4 py-2">URL signals · 18</p>
                      {URL_FEATURES.map((n) => (
                        <FeatureRow key={n} name={n} value={result.features?.[n] ?? '—'} />
                      ))}
                    </div>
                    <div className="bg-panel">
                      <p className="subhead border-b border-hairline px-4 py-2">HTML / DOM · 7</p>
                      {HTML_FEATURES.map((n) => (
                        <FeatureRow key={n} name={n} value={result.features?.[n] ?? '—'} />
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Actions */}
          <div className="no-print mt-6 flex flex-wrap gap-3">
            <button onClick={copyResult} className="btn-ghost inline-flex items-center gap-2">
              {copied ? <Check className="h-4 w-4 text-safe" aria-hidden="true" /> : <Copy className="h-4 w-4" aria-hidden="true" />}
              {copied ? 'Copied' : 'Copy sheet'}
            </button>
            <button onClick={() => navigate('/report')} className="btn-ghost inline-flex items-center gap-2">
              <FileSearch className="h-4 w-4" aria-hidden="true" />
              Print report
            </button>
            <button onClick={() => { setResult(null); setUrl('') }} className="btn-ghost">
              Next exhibit
            </button>
          </div>
        </section>
      )}
    </div>
  )
}
