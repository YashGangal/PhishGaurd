/**
 * Feature-tree diagram — the URL decomposition visual.
 * Shared verbatim between Overview and the Scan idle state.
 */
export default function UrlTreeArt() {
  return (
    <svg viewBox="0 0 400 180" className="block h-auto w-full" role="img" aria-label="URL structure decomposition diagram">
      <line x1="200" y1="18" x2="60" y2="70" className="stroke-hairline" strokeWidth="1" />
      <line x1="200" y1="18" x2="200" y2="70" className="stroke-hairline" strokeWidth="1" />
      <line x1="200" y1="18" x2="340" y2="70" className="stroke-hairline" strokeWidth="1" />
      <line x1="60" y1="70" x2="30" y2="130" className="stroke-hairline" strokeWidth="1" />
      <line x1="60" y1="70" x2="95" y2="130" className="stroke-hairline" strokeWidth="1" />
      <line x1="340" y1="70" x2="340" y2="130" className="stroke-signal" strokeWidth="1.5" />

      <rect x="140" y="4" width="120" height="26" className="fill-panel stroke-hairline" />
      <text x="200" y="21" textAnchor="middle" className="fill-bone" fontSize="11" fontFamily="JetBrains Mono, monospace">URL_STRING</text>

      {[
        { x: 10, label: 'SCHEME' },
        { x: 150, label: 'HOST' },
        { x: 290, label: 'PATH+QUERY' },
      ].map((n) => (
        <g key={n.label}>
          <rect x={n.x} y="58" width="100" height="24" className={n.label === 'PATH+QUERY' ? 'fill-signal-dim stroke-signal' : 'fill-panel stroke-hairline'} />
          <text x={n.x + 50} y="74" textAnchor="middle" className={n.label === 'PATH+QUERY' ? 'fill-signal' : 'fill-steel'} fontSize="10" fontFamily="JetBrains Mono, monospace">{n.label}</text>
        </g>
      ))}

      <rect x="2" y="122" width="56" height="22" className="fill-panel stroke-hairline" />
      <text x="30" y="137" textAnchor="middle" className="fill-steel" fontSize="9" fontFamily="JetBrains Mono, monospace">https</text>
      <rect x="67" y="122" width="56" height="22" className="fill-panel stroke-hairline" />
      <text x="95" y="137" textAnchor="middle" className="fill-steel" fontSize="9" fontFamily="JetBrains Mono, monospace">ip?</text>
      <rect x="292" y="122" width="96" height="22" className="fill-signal-dim stroke-signal" />
      <text x="340" y="137" textAnchor="middle" className="fill-signal" fontSize="9" fontFamily="JetBrains Mono, monospace">entropy▲</text>

      <text x="200" y="168" textAnchor="middle" className="fill-steel" fontSize="9" fontFamily="JetBrains Mono, monospace">22-FEATURE VECTOR → CLASSIFIER</text>
    </svg>
  )
}
