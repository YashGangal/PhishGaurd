import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Copy, Check, Terminal, ExternalLink, ScanSearch, Database, Cpu } from 'lucide-react'
import SectionHead from '../components/SectionHead'
import { api, API_ORIGIN, DOCS_URL } from '../services/api'

const ENDPOINTS = [
  {
    method: 'POST', path: '/predict',
    desc: 'Submit a URL. Returns verdict, confidence, 0–100 risk score, SHAP top-5, and the full 25-feature vector. Persists the exhibit to custody.',
    body: '{ "url": "https://example.com/verify" }',
  },
  {
    method: 'GET', path: '/history',
    desc: 'Newest-first custody log. Query: page, per_page (1–100), prediction=phishing|legitimate.',
    body: '/history?page=1&per_page=10&prediction=phishing',
  },
  {
    method: 'DELETE', path: '/history/{scan_id}',
    desc: 'Strike one exhibit from custody by scan id. Returns 204, no body.',
    body: 'DELETE /history/42 → 204',
  },
  {
    method: 'GET', path: '/model-info',
    desc: 'Serving-model metadata: name, version, accuracy, precision, recall, F1, ROC-AUC, dataset size, training timestamp.',
    body: null,
  },
  {
    method: 'GET', path: '/health',
    desc: 'Liveness probe: status, model_loaded, database_connected.',
    body: null,
  },
]

const METHOD_CLS = { POST: 'method-post', GET: 'method-get', DELETE: 'method-delete' }

export default function ModelAPI() {
  const [model, setModel] = useState(null)
  const [modelFailed, setModelFailed] = useState(false)
  const [tryUrl, setTryUrl] = useState('')
  const [tryResult, setTryResult] = useState(null)
  const [tryError, setTryError] = useState('')
  const [trying, setTrying] = useState(false)
  const [copied, setCopied] = useState(null)
  const copyTimer = useRef(null)

  useEffect(() => {
    api.modelInfo().then(setModel).catch(() => setModelFailed(true))
    return () => clearTimeout(copyTimer.current)
  }, [])

  const tryIt = async () => {
    if (!tryUrl.trim()) return
    setTrying(true)
    setTryResult(null)
    setTryError('')
    try {
      setTryResult(await api.predict(tryUrl.trim()))
    } catch (err) {
      setTryError(err.message || 'REQUEST FAILED')
    } finally {
      setTrying(false)
    }
  }

  const copy = async (text, key) => {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      // Clipboard API unavailable (http/file contexts) — legacy fallback.
      const ta = document.createElement('textarea')
      ta.value = text
      document.body.appendChild(ta)
      ta.select()
      try {
        document.execCommand('copy')
      } catch { /* clipboard unavailable */ }
      document.body.removeChild(ta)
    }
    setCopied(key)
    clearTimeout(copyTimer.current)
    copyTimer.current = setTimeout(() => setCopied(null), 2000)
  }

  return (
    <div className="space-y-10">
      {/* Serving instrument */}
      <section className="panel overflow-hidden">
        <div className="flex items-center gap-2 border-b border-hairline px-5 py-3">
          <Cpu className="h-4 w-4 text-signal" aria-hidden="true" />
          <p className="eyebrow">Serving instrument</p>
        </div>
        {model ? (
          <div className="grid gap-px bg-hairline sm:grid-cols-2 lg:grid-cols-5">
            {[
              ['MODEL', String(model.model_name ?? '').toUpperCase()],
              ['VERSION', String(model.version ?? '').toUpperCase()],
              ['DATASET', Number(model.dataset_size).toLocaleString()],
              ['TRAINED', new Date(model.trained_at).toLocaleDateString()],
              ['THRESHOLD', typeof model.decision_threshold === 'number' ? model.decision_threshold.toFixed(2) : '—'],
            ].map(([k, v]) => (
              <div key={k} className="bg-panel p-5">
                <p className="eyebrow mb-1.5">{k}</p>
                <p className="truncate font-mono text-sm text-bone" title={v}>{v}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="p-5 font-mono text-xs text-steel">{modelFailed ? 'MODEL UNREACHABLE — BACKEND DOWN?' : 'PROBING MODEL…'}</p>
        )}
      </section>

      {/* Endpoint registry */}
      <section>
        <SectionHead index="REG" title="Endpoint registry" hint="5 routes · versioned by contract, not prefix" />
        <ul className="space-y-3">
          {ENDPOINTS.map((e, i) => (
            <motion.li
              key={`${e.method}-${e.path}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="panel p-4 sm:p-5"
            >
              <div className="flex flex-wrap items-center gap-3">
                <span className={`method-tag ${METHOD_CLS[e.method]}`}>{e.method}</span>
                <code className="font-mono text-sm text-bone">{e.path}</code>
                <button
                  onClick={() => copy(`${API_ORIGIN}${e.path}`, e.path)}
                  className="ml-auto rounded-sharp border border-transparent p-1.5 text-steel transition-colors hover:border-signal hover:text-signal"
                  aria-label={`Copy ${e.method} ${e.path} URL`}
                >
                  {copied === e.path ? <Check className="h-4 w-4 text-safe" aria-hidden="true" /> : <Copy className="h-4 w-4" aria-hidden="true" />}
                </button>
              </div>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-steel">{e.desc}</p>
              {e.body && (
                <pre className="mt-3 overflow-x-auto border border-hairline bg-void p-3 font-mono text-xs text-signal">{e.body}</pre>
              )}
            </motion.li>
          ))}
        </ul>
      </section>

      {/* Live fire */}
      <section className="panel p-5 sm:p-6">
        <div className="mb-4 flex items-center gap-2">
          <Terminal className="h-4 w-4 text-signal" aria-hidden="true" />
          <p className="eyebrow">Live fire · POST /predict</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <label htmlFor="try-url" className="sr-only">URL to test against the live API</label>
          <input
            id="try-url"
            type="url"
            value={tryUrl}
            onChange={(e) => { setTryUrl(e.target.value); setTryError('') }}
            placeholder="https://suspicious-link.example/verify"
            className="input-mono"
            autoComplete="off"
            spellCheck="false"
            onKeyDown={(e) => e.key === 'Enter' && tryIt()}
          />
          <button onClick={tryIt} disabled={!tryUrl.trim() || trying} className="btn-scan inline-flex items-center justify-center gap-2 whitespace-nowrap">
            <ScanSearch className="h-4 w-4" strokeWidth={2.5} aria-hidden="true" />
            {trying ? 'Analyzing…' : 'Analyze'}
          </button>
        </div>
        {tryError && <p className="mt-3 font-mono text-xs uppercase text-danger" role="alert">{tryError}</p>}
        {tryResult && (
          <motion.pre
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 overflow-x-auto border border-hairline bg-void p-4 font-mono text-xs leading-relaxed text-bone"
          >
{JSON.stringify({ scan_id: tryResult.scan_id, prediction: tryResult.prediction, confidence: tryResult.confidence, risk_score: tryResult.risk_score, risk_level: tryResult.risk_level, model_version: tryResult.model_version }, null, 2)}
          </motion.pre>
        )}
      </section>

      {/* Swagger, framed */}
      <section>
        <SectionHead index="DOC" title="Interactive contract" hint="FastAPI Swagger · framed, not floating" />
        <div className="overflow-hidden rounded-card border border-hairline bg-panel">
          <div className="flex items-center justify-between border-b border-hairline px-5 py-3">
            <p className="eyebrow">swagger · /docs</p>
            <a
              href={DOCS_URL}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-[0.14em] text-signal hover:text-bone"
            >
              Open full <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
            </a>
          </div>
          <iframe
            title="PhishGuard Swagger API documentation"
            src={DOCS_URL}
            className="h-[560px] w-full bg-white"
            loading="lazy"
          />
        </div>
      </section>

      {/* Integration note */}
      <section className="panel flex items-start gap-3 p-5">
        <Database className="mt-0.5 h-4 w-4 shrink-0 text-signal" aria-hidden="true" />
        <p className="font-mono text-xs leading-relaxed text-steel">
          FRONTEND PROXIES <span className="text-bone">/api → :8000</span> IN DEV. EVERY SCAN ABOVE WRITES TO THE SAME
          CUSTODY LOG THE HISTORY PAGE READS — NO MOCK LAYER.
        </p>
      </section>
    </div>
  )
}
