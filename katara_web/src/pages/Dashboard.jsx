import React, { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDashboard, COULEURS, isApiLive } from '../api/katara'
import { Activity, Droplets, Wind, UploadCloud, Users, AlertTriangle, Wifi, WifiOff, RefreshCw } from 'lucide-react'
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts'
import './Dashboard.css'

const REFRESH_INTERVAL = 60_000  // 60 secondes

export default function Dashboard() {
    const [data, setData]       = useState(null)
    const [loading, setLoading] = useState(true)
    const [apiLive, setApiLive] = useState(false)
    const [countdown, setCountdown] = useState(REFRESH_INTERVAL / 1000)
    const navigate = useNavigate()

    const refresh = useCallback(() => {
        getDashboard().then(res => {
            setData(res)
            setLoading(false)
            setApiLive(isApiLive())
            setCountdown(REFRESH_INTERVAL / 1000)
        })
    }, [])

    // Chargement initial + auto-refresh toutes les 60s
    useEffect(() => {
        refresh()
        const timer = setInterval(refresh, REFRESH_INTERVAL)
        return () => clearInterval(timer)
    }, [refresh])

    // Décompte visuel
    useEffect(() => {
        if (loading) return
        const tick = setInterval(() => setCountdown(c => c > 0 ? c - 1 : REFRESH_INTERVAL / 1000), 1000)
        return () => clearInterval(tick)
    }, [loading])

    if (loading) return (
        <div className="page-container">
            <div className="loader">Chargement du dashboard technique...</div>
        </div>
    )

    const { resume, zones } = data
    const getCouleurHex = (niveau) => COULEURS[niveau]?.text || '#fff'

    return (
        <div className="page-container dashboard-page">
            <div className="dashboard-header">
                <h1 className="page-title">Dashboard Technique</h1>
                <div className="dashboard-meta">
                    <span className={`api-badge ${apiLive ? 'live' : 'demo'}`}>
                        {apiLive ? <Wifi size={13} /> : <WifiOff size={13} />}
                        {apiLive ? 'API connectée' : 'Mode démo'}
                    </span>
                    <button className="refresh-btn" onClick={refresh} title="Rafraîchir">
                        <RefreshCw size={14} /> {countdown}s
                    </button>
                    <div className="last-sync">
                        Synchro: {new Date(data.timestamp).toLocaleTimeString()}
                    </div>
                </div>
            </div>

            <div className="metrics-grid">
                <div className="glass-card metric">
                    <Activity color="#60A5FA" size={24} />
                    <div>
                        <h4>Zones Surveillées</h4>
                        <h2>{resume.total_zones}</h2>
                    </div>
                </div>
                <div className="glass-card metric">
                    <AlertTriangle color="#F59E0B" size={24} />
                    <div>
                        <h4>Alertes Critiques</h4>
                        <h2 style={{ color: '#EF4444' }}>{resume.alertes_critiques}</h2>
                    </div>
                </div>
                <div className="glass-card metric">
                    <Users color="#10B981" size={24} />
                    <div>
                        <h4>Pop. à Risque</h4>
                        <h2>{resume.population_a_risque?.toLocaleString('fr-FR')}</h2>
                    </div>
                </div>
            </div>

            <div className="dashboard-content">
                <div className="glass-card main-chart-panel">
                    <h3>Probabilité d'inondation par zone</h3>
                    <div className="chart-wrapper">
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={zones} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis dataKey="nom" stroke="#94A3B8" />
                                <YAxis stroke="#94A3B8" label={{ value: '%', angle: -90, position: 'insideLeft', fill: '#94A3B8' }} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0A192F', borderColor: '#3B82F6', color: '#fff' }}
                                    cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                />
                                <Bar dataKey="probabilite" onClick={(data) => navigate(`/historique/${data.zone_id}`)} cursor="pointer">
                                    {zones.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={getCouleurHex(entry.niveau_alerte)} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="glass-card table-panel">
                    <h3>Détails Télémétriques</h3>
                    <div className="table-responsive">
                        <table>
                            <thead>
                                <tr>
                                    <th>Zone</th>
                                    <th>Pluie 24h</th>
                                    <th>NDWI</th>
                                    <th>SAR (VV)</th>
                                    <th>Statut</th>
                                </tr>
                            </thead>
                            <tbody>
                                {zones.map(z => {
                                    const c = COULEURS[z.niveau_alerte]
                                    return (
                                        <tr key={z.zone_id} onClick={() => navigate(`/historique/${z.zone_id}`)} style={{cursor:'pointer'}} title="Voir l'historique">
                                            <td>{z.nom}</td>
                                            <td><Droplets size={14} className="icon-inline" /> {z.pluie_24h} mm</td>
                                            <td><UploadCloud size={14} className="icon-inline" /> {z.ndwi?.toFixed(2) || 'N/A'}</td>
                                            <td><Wind size={14} className="icon-inline" /> {z.sar_vv?.toFixed(2) || 'N/A'}</td>
                                            <td>
                                                <span className="badge" style={{ background: c.bg, color: c.text }}>{c.label}</span>
                                            </td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    )
}
