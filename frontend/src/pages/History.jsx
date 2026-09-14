import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Trash2, ChevronLeft, ChevronRight, Download, Link2 } from 'lucide-react'
import SectionHead from '../components/SectionHead'
import VerdictTag from '../components/VerdictTag'
import { api } from '../services/api'
import { truncateUrl, downloadCsv } from '../utils/helpers'

const PER_PAGE = 10

export default function History() {
  const [items, setItems] = useState([])
  const [pagination, setPagination] = useState({ page: 1, total_pages: 0, total_items: 0 })
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [target, setTarget] = useState(null)
  const modalRef = useRef(null)

  const fetchPage = useCallback(async () => {
    setLoading(true)
    setFailed(false)
    try {
      const params = { page, per_page: PER_PAGE }
      if (filter !== 'all') params.prediction = filter
      const res = await api.history(params)
      setItems(res.items)
      setPagination(res.pagination)
    } catch {
      setItems([])
      setFailed(true)
    } finally {
      setLoading(false)
    }
  }, [page, filter])

  useEffect(() => { fetchPage() }, [fetchPage])

  useEffect(() => {
    if (!target) return
    modalRef.current?.focus()
    const onKey = (e) => {
      if (e.key === 'Escape') setTarget(null)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [target])

  const visible = search
    ? items.filter((i) => i.url.toLowerCase().includes(search.toLowerCase()))
    : items

  const confirmDelete = async () => {
    if (!target) return
    try {
      await api.deleteScan(target.scan_id)
      fetchPage()
    } catch { /* surface stays */ } finally {
      setTarget(null)
    }
  }

  const exportCsv = async () => {
    setExporting(true)
    try {
      const params = {}
      if (filter !== 'all') params.prediction = filter
      params.per_page = 100
      params.page = 1
      const first = await api.history(params)
      let all = [...first.items]
      const pages = first.pagination.total_pages || 1
      for (let p = 2; p <= pages; p += 1) {
        const r = await api.history({ ...params, page: p })
        all = all.concat(r.items)
      }
      const rows = search
        ? all.filter((i) => i.url.toLowerCase().includes(search.toLowerCase()))
        : all
      downloadCsv(`phishguard-chain-of-custody-${new Date().toISOString().slice(0, 10)}.csv`, [
        ['scan_id', 'url', 'prediction', 'confidence', 'risk_level', 'scanned_at'],
        ...rows.map((i) => [i.scan_id, i.url, i.prediction, i.confidence, i.risk_level, i.scanned_at]),
      ])
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="space-y-10">
      {/* Controls */}
      <section className="panel p-4 sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-steel" strokeWidth={2} aria-hidden="true" />
            <label htmlFor="history-search" className="sr-only">Filter loaded exhibits by URL</label>
            <input
              id="history-search"
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="FILTER LOADED PAGE BY URL…"
              className="input-mono pl-11 font-mono text-xs uppercase placeholder:text-steel"
            />
          </div>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by verdict">
            {['all', 'legitimate', 'phishing'].map((f) => (
              <button
                key={f}
                data-active={filter === f}
                onClick={() => { setFilter(f); setPage(1) }}
                className="toggle-pill"
                aria-pressed={filter === f}
              >
                {f === 'all' ? 'All' : f === 'legitimate' ? 'Safe' : 'Phishing'}
              </button>
            ))}
          </div>
          <button onClick={exportCsv} disabled={exporting} className="btn-ghost inline-flex items-center justify-center gap-2 whitespace-nowrap">
            <Download className="h-4 w-4" aria-hidden="true" />
            {exporting ? 'Exporting…' : 'CSV export'}
          </button>
        </div>
        <p className="mt-3 font-mono text-[11px] text-steel">
          {pagination.total_items} EXHIBITS IN CUSTODY
          {search && ` · ${visible.length} MATCH ON THIS PAGE`}
        </p>
      </section>

      {/* Dense table → stacked cards */}
      <section>
        <SectionHead index="CUSTODY" title="Chain of custody" hint="newest first" />

        {loading ? (
          <div className="panel p-12 text-center font-mono text-xs text-steel">PULLING RECORDS…</div>
        ) : failed ? (
          <div className="panel p-12 text-center">
            <p className="font-mono text-xs text-danger">CUSTODY LOG UNREACHABLE — BACKEND DOWN?</p>
            <button onClick={fetchPage} className="btn-ghost mt-4">Retry</button>
          </div>
        ) : visible.length === 0 ? (
          <div className="panel p-12 text-center">
            <Link2 className="mx-auto mb-3 h-8 w-8 text-steel" aria-hidden="true" />
            <p className="font-mono text-xs text-steel">NO EXHIBITS MATCH THIS FILTER.</p>
          </div>
        ) : (
          <>
            {/* Desktop: dense instrument table */}
            <div className="hidden overflow-x-auto border border-hairline bg-panel md:block">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-hairline">
                    {['ID', 'URL', 'Verdict', 'Conf', 'Risk', 'Scanned', ''].map((h) => (
                      <th key={h} scope="col" className="th px-4 py-3">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-hairline">
                  {visible.map((item) => (
                    <tr key={item.scan_id} className="transition-colors hover:bg-panel2">
                      <td className="whitespace-nowrap px-4 py-3 font-mono text-[11px] text-steel">{String(item.scan_id).padStart(4, '0')}</td>
                      <td className="max-w-[320px] truncate px-4 py-3 font-mono text-[13px] text-bone" title={item.url}>{item.url}</td>
                      <td className="whitespace-nowrap px-4 py-3"><VerdictTag prediction={item.prediction} risk_level={item.risk_level} /></td>
                      <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-bone">{(item.confidence * 100).toFixed(1)}%</td>
                      <td className="whitespace-nowrap px-4 py-3 font-mono text-xs uppercase text-steel">{item.risk_level}</td>
                      <td className="whitespace-nowrap px-4 py-3 font-mono text-[11px] text-steel">{new Date(item.scanned_at).toLocaleString()}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-right">
                        <button
                          onClick={() => setTarget(item)}
                          className="rounded-sharp border border-transparent p-1.5 text-steel transition-colors hover:border-danger hover:text-danger"
                          aria-label={`Strike exhibit ${item.scan_id} from custody`}
                          aria-haspopup="dialog"
                        >
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile: stacked evidence cards */}
            <ul className="space-y-3 md:hidden">
              {visible.map((item) => (
                <motion.li
                  key={item.scan_id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="panel p-4"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[11px] text-steel">#{String(item.scan_id).padStart(4, '0')}</span>
                    <VerdictTag prediction={item.prediction} risk_level={item.risk_level} />
                  </div>
                  <p className="mt-2 break-all font-mono text-[13px] leading-relaxed text-bone">{truncateUrl(item.url, 90)}</p>
                  <div className="mt-3 flex items-center justify-between border-t border-hairline pt-3 font-mono text-[11px] text-steel">
                    <span>CONF <span className="text-bone">{(item.confidence * 100).toFixed(1)}%</span></span>
                    <span className="uppercase">RISK <span className="text-bone">{item.risk_level}</span></span>
                    <button
                      onClick={() => setTarget(item)}
                      className="rounded-sharp border border-hairline p-2 text-steel"
                      aria-label={`Strike exhibit ${item.scan_id} from custody`}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                </motion.li>
              ))}
            </ul>
          </>
        )}
      </section>

      {/* Pagination */}
      {pagination.total_pages > 1 && (
        <section className="flex items-center justify-between" aria-label="Pagination">
          <span className="font-mono text-[11px] text-steel">PAGE {page} / {pagination.total_pages}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded-sharp border border-hairline p-2 text-steel transition-colors hover:border-signal hover:text-signal disabled:opacity-30"
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(pagination.total_pages, p + 1))}
              disabled={page === pagination.total_pages}
              className="rounded-sharp border border-hairline p-2 text-steel transition-colors hover:border-signal hover:text-signal disabled:opacity-30"
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </section>
      )}

      {/* Strike confirmation */}
      <AnimatePresence>
        {target && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="no-print fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby="strike-title"
            onClick={(e) => e.target === e.currentTarget && setTarget(null)}
          >
            <motion.div
              ref={modalRef}
              tabIndex={-1}
              initial={{ scale: 0.94, y: 12 }}
              animate={{ scale: 1, y: 0 }}
              transition={{ type: 'spring', stiffness: 380, damping: 26 }}
              className="w-full max-w-sm rounded-card border border-hairline bg-panel p-6 outline-none"
            >
              <div className="hazard-stripes-thin mb-4 h-1.5 w-full" aria-hidden="true" />
              <h3 id="strike-title" className="font-display text-base uppercase text-bone">Strike exhibit?</h3>
              <p className="mt-2 break-all font-mono text-xs text-steel">{target.url}</p>
              <p className="mt-2 font-mono text-[11px] uppercase text-danger">Permanent — removed from custody log.</p>
              <div className="mt-5 flex justify-end gap-3">
                <button onClick={() => setTarget(null)} className="btn-ghost">Keep</button>
                <button onClick={confirmDelete} className="btn-danger">
                  Strike
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
