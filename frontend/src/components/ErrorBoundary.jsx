import { Component } from 'react'
import { ShieldAlert } from 'lucide-react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    // Surface render faults for debugging; the bench has no telemetry sink.
    console.error('ERR_RENDER_FAULT', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="panel min-h-[320px] flex items-center justify-center p-10">
          <div className="text-center max-w-md">
            <ShieldAlert className="w-10 h-10 text-danger mx-auto mb-4" strokeWidth={1.5} />
            <h2 className="font-display text-bone text-xl uppercase mb-2">Analysis interrupted</h2>
            <p className="font-mono text-xs text-steel mb-6">ERR_RENDER_FAULT — evidence panel failed to mount.</p>
            <button
              onClick={() => this.setState({ hasError: false })}
              className="btn-ghost"
            >
              Try again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="btn-ghost ml-3"
            >
              Reload bench
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
