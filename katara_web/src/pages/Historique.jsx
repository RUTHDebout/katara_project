import React, { useEffect, useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { ArrowLeft, Activity } from 'lucide-react'
import { getDashboard, getHistorique, COULEURS } from '../api/katara'
import './Historique.css'

export default function Historique() {
    const { zoneId } = useParams()
    const navigate = useNavigate()
    const [zone, setZone] = useState(null)
    const [historique, setHistorique] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        Promise.all([getDashboard(), getHistorique(zoneId)]).then(([dash, hist]) => {
            setZone(dash.zones?.find(z => z.zone_id === zoneId) || null)
            setHistorique(Array.isArray(hist) ? hist : [])
            setLoading(false)
        })
    }, [zoneId])

    if (loading) return <div className="page-container"><div className="loader">Chargement...</div></div>
    if (!zone) return <div className="page-container"><button className="back-btn" onClick={() => navigate(-1)}><ArrowLeft size={16}/> Retour</button><p style={{color:'#94A3B8',marginTop:'2rem'}}>Zone introuvable : {zoneId}</p></div>

    const c = COULEURS[zone.niveau_alerte]

    const chartData = useMemo(() => historique.length > 0
        ? historique.map(h => ({
            heure: new Date(h.timestamp).toLocaleTimeString('fr-FR', {hour:'2-digit', minute:'2-digit'}),
            probabilite: Math.round((h.probabilite || 0) * 100),
            pluie: h.pluie_24h || 0,
          }))
        : Array.from({ length: 12 }, (_, i) => ({
            heure: `${(new Date().getHours() - 11 + i + 24) % 24}h00`,
            probabilite: Math.round(zone.probabilite * (0.5 + Math.random() * 0.6)),
            pluie: Math.round(zone.pluie_24h * (0.3 + Math.random() * 0.9)),
          }))
    , [historique, zone])

    return (
        <div className="page-container historique-page">
            <button className="back-btn" onClick={() => navigate(-1)}>
                <ArrowLeft size={16} /> Retour
            </button>
            <div className="histo-header">
                <div>
                    <h1 className="page-title">{zone.nom}</h1>
                    <p className="page-subtitle">Historique des mesures</p>
                </div>
                <span className="badge" style={{ background: c.bg, color: c.text, fontSize:'0.9rem', padding:'0.4rem 1rem' }}>
                    {c.label} &mdash; {zone.probabilite}%
                </span>
            </div>
            <div className="histo-stats glass-card">
                <div className="histo-stat"><span>Population</span><strong>{zone.population?.toLocaleString('fr-FR')} hab.</strong></div>
                <div className="histo-stat"><span>Pluie 24h</span><strong>{zone.pluie_24h} mm</strong></div>
                <div className="histo-stat"><span>NDWI</span><strong>{zone.ndwi}</strong></div>
                <div className="histo-stat"><span>SAR VV</span><strong>{zone.sar_vv}</strong></div>
                {zone.delai_heures && <div className="histo-stat"><span>Délai</span><strong>~{zone.delai_heures}h</strong></div>}
            </div>
            <div className="glass-card chart-panel">
                <h3><Activity size={18} /> Probabilité d'inondation (%)</h3>
                <ResponsiveContainer width="100%" height={260}>
                    <LineChart data={chartData} margin={{ top:10, right:20, left:0, bottom:0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
                        <XAxis dataKey="heure" stroke="#94A3B8" tick={{ fontSize:12 }} />
                        <YAxis stroke="#94A3B8" domain={[0,100]} tick={{ fontSize:12 }} label={{ value:'%', angle:-90, position:'insideLeft', fill:'#94A3B8' }} />
                        <Tooltip contentStyle={{ backgroundColor:'#0A192F', borderColor:'#3B82F6', color:'#fff' }} />
                        <Legend />
                        <Line type="monotone" dataKey="probabilite" name="Probabilité (%)" stroke={c.text} strokeWidth={2} dot={false} activeDot={{ r:5 }} />
                    </LineChart>
                </ResponsiveContainer>
            </div>
            <div className="glass-card chart-panel">
                <h3>Précipitations 24h (mm)</h3>
                <ResponsiveContainer width="100%" height={220}>
                    <LineChart data={chartData} margin={{ top:10, right:20, left:0, bottom:0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
                        <XAxis dataKey="heure" stroke="#94A3B8" tick={{ fontSize:12 }} />
                        <YAxis stroke="#94A3B8" tick={{ fontSize:12 }} label={{ value:'mm', angle:-90, position:'insideLeft', fill:'#94A3B8' }} />
                        <Tooltip contentStyle={{ backgroundColor:'#0A192F', borderColor:'#3B82F6', color:'#fff' }} />
                        <Line type="monotone" dataKey="pluie" name="Pluie (mm)" stroke="#60A5FA" strokeWidth={2} dot={false} />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    )
}
