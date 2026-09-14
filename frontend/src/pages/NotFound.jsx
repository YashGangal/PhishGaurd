import { Link } from 'react-router-dom'
import { Fingerprint } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="panel mx-auto max-w-md p-12 text-center">
      <Fingerprint className="mx-auto mb-4 h-10 w-10 text-steel" aria-hidden="true" />
      <h1 className="font-display text-2xl uppercase text-bone">Dead end</h1>
      <p className="mt-2 font-mono text-xs text-steel">NO EXHIBIT AT THIS ADDRESS — 404.</p>
      <Link to="/" className="btn-ghost mt-6 inline-block">Back to bench</Link>
    </div>
  )
}
