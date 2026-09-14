export default function SectionHead({ index, title, hint }) {
  return (
    <div className="mb-5 flex flex-wrap items-baseline gap-x-3 gap-y-1">
      <span className="font-mono text-[11px] text-signal">{index}</span>
      <h2 className="font-display text-sm uppercase tracking-wide text-bone">{title}</h2>
      {hint && <span className="font-mono text-[11px] text-steel">// {hint}</span>}
      <span className="ml-2 hidden h-px flex-1 bg-hairline sm:block" aria-hidden="true" />
    </div>
  )
}
