import { ShieldCheck, AlertTriangle, AlertOctagon } from 'lucide-react'

/**
 * Single source of truth for verdict rendering.
 * Tier derives from ONE rule so icon, tag color, and headline
 * can never desync across Scan, History, and Report.
 *
 * NOTE: lucide-react 0.300 names — AlertOctagon / AlertTriangle
 * are the octagon-alert / triangle-alert glyphs.
 */
export const VERDICT = {
  safe: {
    icon: ShieldCheck,
    tag: 'verdict-safe',
    headline: 'Clean',
    label: 'URL is safe',
  },
  caution: {
    icon: AlertTriangle,
    tag: 'verdict-caution',
    headline: 'Caution',
    label: 'Caution',
  },
  danger: {
    icon: AlertOctagon,
    tag: 'verdict-danger',
    headline: 'Phishing',
    label: 'Phishing detected',
  },
}

export function tierOf({ prediction, risk_level, riskLevel } = {}) {
  if (prediction === 'phishing') return 'danger'
  const level = risk_level ?? riskLevel
  if (level === 'medium') return 'caution'
  return 'safe'
}
