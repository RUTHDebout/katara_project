import React from 'react'
import { AlertTriangle } from 'lucide-react'

export default class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props)
        this.state = { hasError: false, error: null }
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error }
    }

    componentDidCatch(error, info) {
        console.error('[KATARA] ErrorBoundary:', error, info)
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="page-container" style={{ textAlign: 'center', paddingTop: '5rem' }}>
                    <AlertTriangle size={56} color="#EF4444" style={{ margin: '0 auto 1.5rem' }} />
                    <h2 className="page-title" style={{ fontSize: '1.8rem' }}>Une erreur est survenue</h2>
                    <p className="page-subtitle" style={{ marginBottom: '2rem' }}>
                        {this.state.error?.message || 'Erreur inattendue'}
                    </p>
                    <button
                        className="refresh-btn"
                        style={{ margin: '0 auto', padding: '0.6rem 1.5rem', fontSize: '0.9rem' }}
                        onClick={() => { this.setState({ hasError: false, error: null }); window.location.href = '/' }}
                    >
                        Retour à l&#39;accueil
                    </button>
                </div>
            )
        }
        return this.props.children
    }
}
