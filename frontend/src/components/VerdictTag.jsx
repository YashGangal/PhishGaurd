import { tierOf, VERDICT } from '../utils/verdict'

export default function VerdictTag({ prediction, riskLevel, risk_level, size = 'md' }) {
  const tier = tierOf({ prediction, riskLevel, risk_level })
  const { icon: Icon, tag, label } = VERDICT[tier]
  const level = riskLevel ?? risk_level

  return (
    <span className={`verdict-tag ${tag} ${size === 'lg' ? 'text-base px-5 py-3' : ''}`} role="status">
      <Icon className={size === 'lg' ? 'w-6 h-6' : 'w-4 h-4'} strokeWidth={2} aria-hidden="true" />
      {label}
      {level && <span className="font-mono opacity-80">· {level}</span>}
    </span>
  )
}
