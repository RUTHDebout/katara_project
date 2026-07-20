import React, { useEffect, useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { AlertOctagon, Info, MapPin, RefreshCw, Wifi, WifiOff } from "lucide-react"
import { getAlertesActives, COULEURS, CONSEILS, isApiLive } from "../api/katara"
import "./Alertes.css"

const REFRESH_INTERVAL = 30_000

export default function Alertes() {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const [apiLive, setApiLive] = useState(false)
    const [countdown, setCountdown] = useState(REFRESH_INTERVAL / 1000)
    const navigate = useNavigate()

    const refresh = useCallback(() => {
        getAlertesActives().then(res => {
            setData(res)
            setLoading(false)
            setApiLive(isApiLive())
            setCountdown(REFRESH_INTERVAL / 1000)
        })
    }, [])

    useEffect(() => {
        refresh()
        const timer = setInterval(refresh, REFRESH_INTERVAL)
        return () => clearInterval(timer)
    }, [refresh])

    useEffect(() => {
        if (loading) return
        const tick = setInterval(() => setCountdown(c => c > 0 ? c - 1 : REFRESH_INTERVAL / 1000), 1000)
        return () => clearInterval(tick)
    }, [loading])

    if (loading) return <div className="page-container"><div className="loader">Chargement des alertes...</div></div>

    const alertes = data?.zones || []

    return (
        <div className="page-container">
            <div className="alertes-header">
                <div>
                    <h1 className="page-title">Alertes en Direct</h1>
                    <p className="page-subtitle">Risques d'inondation en temps réel dans votre zone.</p>
                </div>
                <div className="dashboard-meta">
                    <span className={`api-badge ${apiLive ? "live" : "demo"}`}>
                        {apiLive ? <Wifi size={13} /> : <WifiOff size={13} />}
                        {apiLive ? "API connectée" : "Mode démo"}
                    </span>
                    <button className="refresh-btn" onClick={refresh} title="Rafraîchir">
                        <RefreshCw size={14} /> {countdown}s
                    </button>
                </div>
            </div>

            {alertes.length === 0 ? (
                <div className="glass-card success-banner">
                    <Info size={24} />
                    <div>
                        <h3>Aucune alerte majeure</h3>
                        <p>La situation est actuellement stable dans toutes les zones surveillées.</p>
                    </div>
                </div>
            ) : (
                <div className="alertes-grid">
                    {alertes.map(z => {
                        const couleur = COULEURS[z.niveau_alerte]
                        const conseils = CONSEILS[z.niveau_alerte]
                        return (
                            <div key={z.zone_id} className="glass-card alerte-card" style={{ borderColor: couleur.border }}>
                                <div className="alerte-header">
                                    <div className="alerte-title">
                                        <MapPin color={couleur.text} />
                                        <h2>{z.nom}</h2>
                                    </div>
                                    <span className="badge" style={{ background: couleur.bg, color: couleur.text }}>
                                        {couleur.label}
                                    </span>
                                </div>

                                <div className="alerte-stats">
                                    <div><strong>Probabilité:</strong> {z.probabilite}%</div>
                                    {z.delai_heures && <div><strong>Délai estimé:</strong> ~{z.delai_heures}h</div>}
                                    <div><strong>Pluie 24h:</strong> {z.pluie_24h} mm</div>
                                </div>

                                <div className="alerte-conseils">
                                    <h4>Consignes de sécurité :</h4>
                                    <ul>
                                        {conseils.map((c, i) => <li key={i}>{c}</li>)}
                                    </ul>
                                </div>
                                <button
                                    className="refresh-btn"
                                    style={{marginTop:'0.75rem', width:'100%', justifyContent:'center'}}
                                    onClick={() => navigate(`/historique/${z.zone_id}`)}
                                >
                                    Voir l&#39;historique &rarr;
                                </button>
                            </div>
                        )
                    })}
                </div>
            )}
        </div>
    )
}
