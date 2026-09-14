/**
 * UV scan beam — a real animated SVG, not a CSS glow pulse.
 * An EKG trace draws itself via stroke-dashoffset while a
 * vertical ALS sweep line traverses the chamber.
 * All colors inherit the bench theme (signal violet + hairlines).
 */
export default function ScanBeam({ label = 'SCANNING' }) {
  return (
    <div className="relative overflow-hidden border border-hairline bg-void rounded-card" role="status" aria-label={label}>
      <svg viewBox="0 0 640 120" preserveAspectRatio="none" className="block h-28 w-full text-signal">
        {/* chamber grid */}
        {Array.from({ length: 16 }, (_, i) => (
          <line key={`v${i}`} x1={i * 40} y1="0" x2={i * 40} y2="120" className="stroke-hairline" strokeWidth="1" opacity="0.6" />
        ))}
        {Array.from({ length: 4 }, (_, i) => (
          <line key={`h${i}`} x1="0" y1={i * 30} x2="640" y2={i * 30} className="stroke-hairline" strokeWidth="1" opacity="0.6" />
        ))}

        {/* EKG trace */}
        <path
          className="ekg-path"
          d="M0,60 L120,60 L140,60 L150,30 L162,88 L174,60 L260,60 L280,60 L290,18 L304,96 L318,60 L420,60 L436,60 L444,44 L452,74 L460,60 L640,60"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
        />

        {/* ALS sweep line */}
        <g className="beam-sweep">
          <rect x="0" y="0" width="56" height="120" fill="url(#beamGrad)" opacity="0.85" />
          <line x1="56" y1="0" x2="56" y2="120" stroke="currentColor" strokeWidth="2" />
        </g>

        <defs>
          <linearGradient id="beamGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="currentColor" stopOpacity="0" />
            <stop offset="1" stopColor="currentColor" stopOpacity="0.35" />
          </linearGradient>
        </defs>
      </svg>

      <div className="flex items-center justify-between border-t border-hairline px-4 py-2">
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-signal">{label}</span>
        <span className="font-mono text-[11px] text-steel">ALS // 365NM</span>
      </div>
    </div>
  )
}
