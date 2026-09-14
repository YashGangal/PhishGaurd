import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import SectionHead from '../components/SectionHead'
import { api } from '../services/api'

/* Real numbers — phishing_detector/backend/ml/comparison_report.json
   trained 2026-09-13, dataset n=1,225,480, selected RandomForest. */
const TRAINING_MODELS = [
  { name: 'RandomForest', accuracy: 0.9195, precision: 0.8992, recall: 0.8873, f1: 0.8932, rocAuc: 0.9693, selected: true, stroke: 'solid' },
  { name: 'XGBoost', accuracy: 0.8909, precision: 0.8793, recall: 0.8256, f1: 0.8516, rocAuc: 0.9497, selected: false, stroke: 'bone' },
  { name: 'LogisticRegression', accuracy: 0.7539, precision: 0.6587, recall: 0.7283, f1: 0.6917, rocAuc: 0.8252, selected: false, stroke: 'steel' },
  { name: 'SVM', accuracy: 0.7497, precision: 0.6499, recall: 0.7362, f1: 0.6904, rocAuc: 0.8232, selected: false, stroke: 'faint' },
]

/* Operating points derived from reported precision/recall (per-100 normalization).
   Confusion cells for the selected model follow the same derivation. */
function operatingPoint(m) {
  const tp = m.recall * 100
  const fp = tp / m.precision - tp
  return { fpr: fp / 100, tpr: m.recall }
}

const RF_CONFUSION = (() => {
  const m = TRAINING_MODELS[0]
  const tp = Math.round(m.recall * 100)
  const fn = 100 - tp
  const fp = Math.round((tp / m.precision - tp))
  const tn = 100 - fp
  return { tn, fp, fn, tp }
})()

/* Curve identity is weight + graphite hue-step first, dash second:
   serving violet 3px → bone 2.5px → steel 2px → dim steel 1.5px dashed. */
const STROKE_STYLE = {
  solid: { stroke: 'rgb(var(--signal))', strokeWidth: 3, strokeDasharray: 'none' },
  bone: { stroke: 'rgb(var(--bone))', strokeWidth: 2.5, strokeDasharray: 'none' },
  steel: { stroke: 'rgb(var(--steel))', strokeWidth: 2, strokeDasharray: 'none' },
  faint: { stroke: 'rgb(var(--steel))', strokeWidth: 1.5, strokeDasharray: '6 4', opacity: 0.7 },
}

/* Bounded ROC schematic: two cubic segments joined with a vertical
   tangent at the operating point. Every control point lies inside the
   [0,fpr]x[0,tpr] / [fpr,1]x[tpr,1] boxes, so curves can never leave
   the plot area — unlike the previous reflected-T construction. */
function rocPath(px, py, fpr, tpr) {
  return [
    `M ${px(0)} ${py(0)}`,
    `C ${px(fpr * 0.55)} ${py(0)} ${px(fpr)} ${py(tpr * 0.45)} ${px(fpr)} ${py(tpr)}`,
    `C ${px(fpr)} ${py(tpr + (1 - tpr) * 0.55)} ${px(fpr + (1 - fpr) * 0.45)} ${py(1)} ${px(1)} ${py(1)}`,
  ].join(' ')
}

function RocChart() {
  const W = 320
  const H = 256
  const px = (fpr) => 40 + fpr * (W - 56)
  const py = (tpr) => H - 32 - tpr * (H - 56)

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="img" aria-label="ROC curves for the four candidate models">
      {[0, 0.25, 0.5, 0.75, 1].map((t) => (
        <g key={t}>
          <line x1={px(t)} y1={py(0)} x2={px(t)} y2={py(1)} className="stroke-hairline" strokeWidth="1" />
          <line x1={px(0)} y1={py(t)} x2={px(1)} y2={py(t)} className="stroke-hairline" strokeWidth="1" />
          <text x={px(t)} y={H - 20} textAnchor="middle" className="fill-steel" fontSize="9" fontFamily="JetBrains Mono, monospace">{t.toFixed(2)}</text>
          <text x={30} y={py(t) + 3} textAnchor="end" className="fill-steel" fontSize="9" fontFamily="JetBrains Mono, monospace">{t.toFixed(2)}</text>
        </g>
      ))}
      <line x1={px(0)} y1={py(0)} x2={px(1)} y2={py(1)} className="stroke-hairline" strokeWidth="1" strokeDasharray="4 4" />
      {TRAINING_MODELS.map((m) => {
        const { fpr, tpr } = operatingPoint(m)
        const s = STROKE_STYLE[m.stroke]
        return (
          <g key={m.name}>
            <path
              d={rocPath(px, py, fpr, tpr)}
              fill="none"
              {...s}
            />
            <circle cx={px(fpr)} cy={py(tpr)} r={m.selected ? 4 : 3} fill={m.selected ? 'rgb(var(--signal))' : 'rgb(var(--panel))'} stroke={m.selected ? 'rgb(var(--signal))' : 'rgb(var(--steel))'} strokeWidth="1.5" />
          </g>
        )
      })}
      <text x={px(0.5)} y={H - 6} textAnchor="middle" className="fill-steel" fontSize="9" fontFamily="JetBrains Mono, monospace">FPR →</text>
      <text x={10} y={py(0.5)} textAnchor="middle" className="fill-steel" fontSize="9" fontFamily="JetBrains Mono, monospace" transform={`rotate(-90 10 ${py(0.5)})`}>→ TPR</text>
    </svg>
  )
}

export default function Analytics() {
  const [live, setLive] = useState({ total: null, phishing: null })
  const [model, setModel] = useState(null)

  useEffect(() => {
    api.history({ per_page: 1 }).then((r) => setLive((l) => ({ ...l, total: r.pagination.total_items }))).catch(() => {})
    api.history({ per_page: 1, prediction: 'phishing' })
      .then((r) => setLive((l) => ({ ...l, phishing: r.pagination.total_items })))
      .catch(() => {})
    api.modelInfo().then(setModel).catch(() => {})
  }, [])

  const cells = [
    { k: 'TN', v: RF_CONFUSION.tn, label: 'True negative' },
    { k: 'FP', v: RF_CONFUSION.fp, label: 'False positive' },
    { k: 'FN', v: RF_CONFUSION.fn, label: 'False negative' },
    { k: 'TP', v: RF_CONFUSION.tp, label: 'True positive' },
  ]

  return (
    <div className="space-y-10">
      {/* Live counters */}
      <section className="grid grid-cols-2 gap-px border border-hairline bg-hairline lg:grid-cols-4">
        {[
          ['Exhibits live', live.total ?? '…', 'text-bone', false],
          ['Flagged live', live.phishing ?? '…', live.phishing > 0 ? 'text-danger' : 'text-bone', false],
          ['Flag rate', live.total ? `${((live.phishing / live.total) * 100).toFixed(1)}%` : '—', 'text-bone', false],
          ['Serving model', model ? model.version.toUpperCase() : '…', 'text-bone', true],
        ].map(([k, v, cls, tight]) => (
          <div key={k} className="min-w-0 bg-panel p-5">
            <p className="eyebrow mb-1.5">{k}</p>
            <p className={`font-mono text-bone ${tight ? 'truncate text-lg' : 'text-2xl'} ${cls}`} title={String(v)}>{v}</p>
          </div>
        ))}
      </section>

      {/* Model matrix — real training numbers */}
      <section>
        <SectionHead index="M1" title="Candidate matrix" hint="training report · 2026-09-13 · n=1,225,480" />
        <div className="scroll-fade-x overflow-x-auto border border-hairline bg-panel">
          <table className="w-full min-w-[640px] text-left">
            <thead>
              <tr className="border-b border-hairline">
                {['Model', 'Acc', 'Prec', 'Rec', 'F1', 'ROC-AUC', ''].map((h) => (
                  <th key={h} scope="col" className="th px-4 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {TRAINING_MODELS.map((m, i) => (
                <motion.tr
                  key={m.name}
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true, margin: '-40px' }}
                  transition={{ delay: i * 0.06 }}
                >
                  <td className="px-4 py-3">
                    <span className={`font-mono text-[13px] ${m.selected ? 'text-signal' : 'text-bone'}`}>{m.name}</span>
                    {m.selected && <span className="ml-2 border border-signal px-1.5 py-0.5 font-mono text-[10px] text-signal">SERVING</span>}
                  </td>
                  {[m.accuracy, m.precision, m.recall, m.f1].map((v, j) => (
                    <td key={j} className="px-4 py-3 font-mono text-[13px] text-bone">{(v * 100).toFixed(2)}%</td>
                  ))}
                  <td className="px-4 py-3 font-mono text-[13px] text-bone">{m.rocAuc.toFixed(4)}</td>
                  <td className="px-4 py-3">
                    <span className="flex h-1.5 w-20 bg-void" role="img" aria-label={`ROC-AUC ${(m.rocAuc * 100).toFixed(2)} percent`}>
                      <span className={`h-full ${m.selected ? 'bg-signal' : 'bg-steel'}`} style={{ width: `${m.rocAuc * 100}%` }} />
                    </span>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 font-mono text-[11px] text-steel">SELECTION RULE — HIGHEST F1, THEN ROC-AUC. SOURCE: ml/comparison_report.json</p>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Confusion heatmap */}
        <motion.section
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-40px' }}
          className="panel min-w-0 p-6"
        >
          <p className="eyebrow mb-1">RandomForest · confusion</p>
          <p className="mb-4 font-mono text-[11px] text-steel">NORMALIZED PER 100/CLASS — DERIVED FROM REPORTED PRECISION/RECALL</p>
          <div className="grid grid-cols-2 gap-px border border-hairline bg-hairline" role="img" aria-label={`Confusion matrix: true negatives ${RF_CONFUSION.tn}, false positives ${RF_CONFUSION.fp}, false negatives ${RF_CONFUSION.fn}, true positives ${RF_CONFUSION.tp}`}>
            {cells.map((c) => {
              const correct = c.k === 'TP' || c.k === 'TN'
              return (
                <div
                  key={c.k}
                  className={`border-l-[3px] bg-panel p-5 ${correct ? 'border-l-safe/60' : 'border-l-danger/60'}`}
                >
                  <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-steel">{c.label}</p>
                  <p className="mt-1 font-mono text-4xl text-bone">{c.v}</p>
                </div>
              )
            })}
          </div>
          <div className="mt-3 flex justify-between font-mono text-[10px] uppercase text-steel">
            <span>← predicted legit</span>
            <span>predicted phish →</span>
          </div>
          <dl className="mt-4 grid grid-cols-3 gap-px border border-hairline bg-hairline">
            {[
              ['Precision', `${(TRAINING_MODELS[0].precision * 100).toFixed(1)}%`],
              ['Recall', `${(TRAINING_MODELS[0].recall * 100).toFixed(1)}%`],
              ['F1', `${(TRAINING_MODELS[0].f1 * 100).toFixed(1)}%`],
            ].map(([k, v]) => (
              <div key={k} className="bg-panel px-3 py-2.5">
                <dt className="font-mono text-[10px] uppercase tracking-[0.18em] text-steel">{k}</dt>
                <dd className="mt-0.5 font-mono text-sm text-bone">{v}</dd>
              </div>
            ))}
          </dl>
        </motion.section>

        {/* ROC */}
        <motion.section
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-40px' }}
          className="panel min-w-0 p-6"
        >
          <p className="eyebrow mb-1">ROC · four candidates</p>
          <p className="mb-4 font-mono text-[11px] text-steel">SCHEMATIC — ANCHORED TO REPORTED OPERATING POINTS</p>
          <RocChart />
          <ul className="mt-4 divide-y divide-hairline border-t border-hairline">
            {TRAINING_MODELS.map((m) => {
              const { fpr, tpr } = operatingPoint(m)
              return (
                <li key={m.name} className="py-2">
                  <div className="flex items-baseline gap-3 font-mono">
                    <svg width="32" height="10" className="shrink-0 self-center" aria-hidden="true">
                      <line x1="0" y1="5" x2="32" y2="5" {...STROKE_STYLE[m.stroke]} />
                    </svg>
                    <span className={`min-w-0 flex-1 truncate text-sm ${m.selected ? 'text-signal' : 'text-steel'}`}>{m.name}</span>
                    <span className="shrink-0 whitespace-nowrap text-sm text-bone">AUC {m.rocAuc.toFixed(4)}</span>
                  </div>
                  <p className="mt-0.5 pl-11 font-mono text-[11px] text-steel">FPR {fpr.toFixed(2)} · TPR {tpr.toFixed(2)}</p>
                </li>
              )
            })}
          </ul>
        </motion.section>
      </div>
    </div>
  )
}
