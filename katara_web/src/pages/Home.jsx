import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, TrendingUp, ShieldCheck, Activity, Bell, BarChart2 } from 'lucide-react'
import { getStats } from '../api/katara'
import './Home.css'

export default function Home() {
    const [stats, setStats] = useState(null)

    useEffect(() => {
        getStats().then(s => setStats(s))
    }, [])

    const fmt = (v, fallback = '...') => v != null ? v : fallback

    return (
        <div className="home-page">
            <section className="hero">
                <div className="hero-content">
                    <h1>
                        Anticipez les Inondations.<br />
                        <span>Sauvez des Vies.</span>
                    </h1>
                    <p>
                        KATARA utilise l&#39;intelligence artificielle et l&#39;imagerie satellite pour
                        prédire les inondations au Togo avec 85 % de précision, jusqu&#39;à 48h à l&#39;avance.
                    </p>
                    <div className="hero-actions">
                        <Link to="/alertes" className="btn-primary">
                            Voir les alertes en direct
                        </Link>
                        <Link to="/carte" className="btn-secondary">
                            Carte des zones
                        </Link>
                    </div>
                </div>
            </section>

            <section className="stats-section">
                <div className="glass-card stat-card">
                    <Activity size={32} color="#60A5FA" />
                    <h3>85 %</h3>
                    <p>Précision des prédictions</p>
                </div>
                <div className="glass-card stat-card">
                    <AlertTriangle size={32} color="#F59E0B" />
                    <h3>48h</h3>
                    <p>Délai d&#39;anticipation</p>
                </div>
                <div className="glass-card stat-card">
                    <Bell size={32} color="#EF4444" />
                    <h3>{fmt(stats?.alertes_7j, '—')}</h3>
                    <p>Alertes déclenchées (7j)</p>
                </div>
                <div className="glass-card stat-card">
                    <BarChart2 size={32} color="#8B5CF6" />
                    <h3>{fmt(stats?.predictions_7j, '…')}</h3>
                    <p>Prédictions (7 jours)</p>
                </div>
            </section>

            <section className="mission-section">
                <div className="mission-text">
                    <h2>Pourquoi KATARA ?</h2>
                    <p>
                        Les inondations affectent des milliers de ménages chaque année au Togo.
                        Les systèmes actuels sont réactifs. Nous voulons passer à la <strong>prévention active</strong>.
                    </p>
                    <p>
                        En combinant les prévisions météorologiques locales, les données d&#39;élévation,
                        les images radar (SAR) qui voient à travers les nuages, et un modèle de Machine Learning,
                        KATARA fournit une alerte précoce et fiable à la communauté et aux autorités.
                    </p>
                    {stats && stats.prob_moyenne > 0 && (
                        <div className="glass-card" style={{marginTop:'1.5rem', padding:'1rem 1.5rem', display:'inline-flex', gap:'1rem', alignItems:'center'}}>
                            <ShieldCheck size={20} color="#10B981" />
                            <span>Probabilité moyenne actuelle : <strong style={{color:'#10B981'}}>{stats.prob_moyenne} %</strong></span>
                        </div>
                    )}
                </div>
            </section>
        </div>
    )
}
