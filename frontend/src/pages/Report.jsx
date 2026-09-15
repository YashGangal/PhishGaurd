import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Printer, FileSearch } from 'lucide-react'
import { tierOf, VERDICT } from '../utils/verdict'
import { URL_FEATURES, HTML_FEATURES } from '../utils/features'

function Row({ k, v }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-neutral-200 px-4 py-2 last:border-b-0">
      <span className="font-mono text-xs text-neutral-500">{k}</span>
      <span className="break-all text-right font-mono text-xs text-neutral-900">{String(v)}</span>
    </div>
  )
}

export default function Report() {
  const [scan, setScan] = useState(null)
  const [corrupt, setCorrupt] = useState(false)

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem('phishguard:last-scan')
      if (!raw) return
      const parsed = JSON.parse(raw)
      // Guard against stale schemas, partial writes, or manual tampering.
      if (parsed && typeof parsed.url === 'string' && Array.isArray(parsed.top_features)) {
        setScan(parsed)
      } else {
        setCorrupt(true)
      }
    } catch {
      setCorrupt(true)
    }
  }, [])

  if (!scan) {
    return (
      <div className="panel p-12 text-center">
        <FileSearch className="mx-auto mb-4 h-10 w-10 text-steel" aria-hidden="true" />
        <h1 className="font-display text-xl uppercase text-bone">{corrupt ? 'Exhibit unreadable' : 'No exhibit loaded'}</h1>
        <p className="mx-auto mt-2 max-w-md font-mono text-xs leading-relaxed text-steel">
          {corrupt
            ? 'THE STORED SCAN IS CORRUPT OR FROM AN OLDER SCHEMA. RUN A FRESH ANALYSIS TO PRINT A NEW SHEET.'
            : 'THE REPORT SHEET IS PRINTED FROM A COMPLETED SCAN. RUN AN ANALYSIS FIRST — THE SHEET PULLS THE LAST RESULT FROM THIS SESSION.'}
        </p>
        <Link to="/scan" className="btn-scan mt-6 inline-block">Open scan bench</Link>
      </div>
    )
  }

  const tier = tierOf(scan)
  const danger = tier === 'danger'
  const VerdictIcon = VERDICT[tier].icon
  const scannedTime = new Date(scan.scanned_at)
  const scannedDay = Number.isNaN(scannedTime.getTime()) ? 'unknown-date' : scannedTime.toISOString().slice(0, 10)
  const serial = `PG-${String(scan.scan_id ?? 0).padStart(6, '0')}-${scannedDay}`

  return (
    <div className="space-y-6">
      <div className="no-print flex flex-wrap items-center gap-3">
        <button onClick={() => window.print()} className="btn-scan inline-flex items-center gap-2">
          <Printer className="h-4 w-4" strokeWidth={2.5} aria-hidden="true" />
          Print / PDF
        </button>
        <Link to="/scan" className="btn-ghost">Back to bench</Link>
        <span className="font-mono text-[11px] text-steel">LIGHT SHEET — OPTIMIZED FOR PRINT, SAME MONO DISCIPLINE</span>
      </div>

      {/* ——— Light forensic sheet, inset in a dark matte gutter ——— */}
      <div className="sheet-matte border border-hairline bg-void p-3 sm:p-6">
      <article className="print-sheet overflow-hidden rounded-card border border-neutral-300 bg-white text-neutral-900 shadow-[0_12px_48px_rgba(0,0,0,0.45)]">
        {/* Audit header */}
        <header className="border-b-2 border-neutral-900 px-6 py-5 sm:px-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500">PhishGuard · forensic analysis report</p>
              <h1 className="mt-1 font-display text-2xl uppercase sm:text-3xl">URL threat sheet</h1>
            </div>
            <div className="text-right font-mono text-[11px] leading-relaxed text-neutral-600">
              SERIAL <span className="text-neutral-900">{serial}</span>
              <br />
              GENERATED <span className="text-neutral-900">{new Date().toLocaleString()}</span>
            </div>
          </div>
        </header>

        {danger && <div className="hazard-stripes h-2 w-full" aria-hidden="true" />}

        {/* Target */}
        <section className="border-b border-neutral-200 px-6 py-5 sm:px-8">
          <h2 className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500">01 · Target</h2>
          <p className="mt-2 break-all font-mono text-sm">{scan.url}</p>
          <p className="mt-1 font-mono text-xs text-neutral-600">DOMAIN {scan.domain} · MODEL {scan.model_version} · SCANNED {new Date(scan.scanned_at).toLocaleString()}</p>
        </section>

        {/* Verdict */}
        <section className="border-b border-neutral-200 px-6 py-5 sm:px-8">
          <h2 className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500">02 · Executive verdict</h2>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <VerdictIcon
              className={`h-8 w-8 ${tier === 'danger' ? 'text-red-600' : tier === 'caution' ? 'text-amber-600' : 'text-green-700'}`}
              aria-hidden="true"
            />
            <p className="font-display text-3xl uppercase sm:text-4xl">
              {VERDICT[tier].headline}
            </p>
          </div>
          {(scan.blocklist_hit || scan.needs_review) && (
            <p className="mt-2 font-mono text-xs uppercase tracking-[0.14em] text-neutral-700">
              {[scan.blocklist_hit ? `Feed-listed (${scan.blocklist_source ?? 'threat feed'})` : null,
                scan.needs_review ? 'Low margin — manual review advised' : null].filter(Boolean).join(' · ')}
            </p>
          )}
          <div className="mt-3 grid grid-cols-3 gap-px border border-neutral-300 bg-neutral-300">
            {[
              ['RISK', `${scan.risk_score ?? '—'}/100 (${scan.risk_level ?? '—'})`],
              ['CONFIDENCE', typeof scan.confidence === 'number' ? `${(scan.confidence * 100).toFixed(1)}%` : '—'],
              ['HTML PASS', scan.html_features_available ? 'FULL' : 'URL-ONLY'],
            ].map(([k, v]) => (
              <div key={k} className="bg-white p-3">
                <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500">{k}</p>
                <p className="mt-0.5 font-mono text-sm">{v}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Signals */}
        <section className="border-b border-neutral-200 px-6 py-5 sm:px-8">
          <h2 className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500">03 · Forensic signals (SHAP top-5)</h2>
          <table className="mt-3 w-full border border-neutral-300 text-left">
            <thead>
              <tr className="border-b border-neutral-300 bg-neutral-100">
                {['#', 'Feature', 'Value', 'Impact', 'Direction'].map((h) => (
                  <th key={h} scope="col" className="px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {scan.top_features.map((f, i) => (
                <tr key={f.name} className="border-b border-neutral-200 last:border-b-0">
                  <td className="px-3 py-2 font-mono text-xs">E{i + 1}</td>
                  <td className="px-3 py-2 font-mono text-xs">{f.name}</td>
                  <td className="px-3 py-2 font-mono text-xs">{String(f.value)}</td>
                  <td className="px-3 py-2 font-mono text-xs">{(Math.abs(f.impact_score) * 100).toFixed(1)}%</td>
                  <td className="px-3 py-2 font-mono text-xs">{f.direction}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* Full matrix */}
        <section className="border-b border-neutral-200 px-6 py-5 sm:px-8">
          <h2 className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500">04 · Complete 25-feature matrix</h2>
          <div className="mt-3 grid gap-px border border-neutral-300 bg-neutral-300 md:grid-cols-2">
            <div className="bg-white">
              <p className="border-b border-neutral-300 bg-neutral-100 px-4 py-2 font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-600">URL signals · 18</p>
              {URL_FEATURES.map((n) => <Row key={n} k={n} v={scan.features?.[n] ?? '—'} />)}
            </div>
            <div className="bg-white">
              <p className="border-b border-neutral-300 bg-neutral-100 px-4 py-2 font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-600">HTML / DOM · 7</p>
              {HTML_FEATURES.map((n) => <Row key={n} k={n} v={scan.features?.[n] ?? '—'} />)}
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="px-6 py-5 sm:px-8">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500">05 · Verification</p>
          <p className="mt-1 font-mono text-xs leading-relaxed text-neutral-700">
            GENERATED BY PHISHGUARD ML SYSTEM · MODEL {scan.model_version} · SERIAL {serial} ·
            VERIFY AGAINST CUSTODY LOG EXHIBIT #{scan.scan_id}.
          </p>
        </footer>
      </article>
      </div>
    </div>
  )
}
