import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Waves, ArrowLeft, Home } from 'lucide-react'

export default function NotFound() {
    const navigate = useNavigate()
    return (
        <div className="page-container" style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '70vh',
            textAlign: 'center',
            gap: '1.5rem',
        }}>
            <div style={{ position: 'relative', marginBottom: '0.5rem' }}>
                <Waves size={80} color="#3B82F6" style={{ opacity: 0.25 }} />
                <span style={{
                    position: 'absolute', inset: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '2.5rem', fontWeight: 900, color: '#60A5FA',
                }}>404</span>
            </div>

            <h1 className="page-title" style={{ fontSize: '2rem', marginBottom: 0 }}>
                Page introuvable
            </h1>
            <p className="page-subtitle" style={{ maxWidth: 420, lineHeight: 1.6 }}>
                Cette page n&apos;existe pas ou a ete deplacee.
                Verifiez l&apos;adresse ou retournez a l&apos;accueil.
            </p>

            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}>
                <button
                    className="refresh-btn"
                    onClick={() => navigate(-1)}
                    style={{ padding: '0.6rem 1.25rem' }}
                >
                    <ArrowLeft size={16} /> Retour
                </button>
                <Link to="/" className="btn-primary" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Home size={16} /> Accueil
                </Link>
            </div>

            <p style={{ color: '#475569', fontSize: '0.8rem', marginTop: '1rem' }}>
                KATARA &mdash; Systeme d&apos;alerte aux inondations &bull; Lome, Togo
            </p>
        </div>
    )
}