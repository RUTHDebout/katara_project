import React, { useEffect, useState, useCallback } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import { useNavigate } from 'react-router-dom'
import { RefreshCw, Wifi, WifiOff } from 'lucide-react'
import { getDashboard, COULEURS, isApiLive } from '../api/katara'
import 'leaflet/dist/leaflet.css'
import './Carte.css'

const REFRESH_INTERVAL = 60_000

const MAP_COLORS = {
    critique: '#EF4444',
    moyen:    '#F59E0B',
    faible:   '#EAB308',
    normal:   '#10B981',
}

export default function Carte() {
    const [zones, setZones] = useState([])
    const [loading, setLoading] = useState(true)
    const [apiLive, setApiLive] = useState(false)
    const [countdown, setCountdown] = useState(REFRESH_INTERVAL / 1000)
    const [selectedZone, setSelectedZone] = useState(null)
    const navigate = useNavigate()

    const refresh = useCallback(() => {
        getDashboard().then(res => {
            setZones(res.zones || [])
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

    if (loading) return (
        <div className="page-container">
            <div className="loader">Chargement de la carte...</div>
        </div>
    )

    const center = [6.1319, 1.2228]

    return (
        <div className="page-container carte-page">
            <div className="dashboard-header">
                <h1 className="page-title">Carte des Risques</h1>
                <div className="dashboard-meta">
                    <span className={`api-badge ${apiLive ? "live" : "demo"}`}>
                        {apiLive ? <Wifi size={13} /> : <WifiOff size={13} />}
                        {apiLive ? 'API connectée' : 'Mode démo'}
                    </span>
                    <button className="refresh-btn" onClick={refresh} title="Rafraîchir">
                        <RefreshCw size={14} /> {countdown}s
                    </button>
                </div>
            </div>

            <div className="carte-layout">
                <div className="map-wrapper glass-card">
                    <MapContainer
                        center={center}
                        zoom={12}
                        style={{ height: '100%', width: '100%', borderRadius: '12px' }}
                    >
                        <TileLayer
                            attribution="&copy; OpenStreetMap contributors"
                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        />
                        {zones.map(z => (
                            <CircleMarker
                                key={z.zone_id}
                                center={[z.latitude, z.longitude]}
                                radius={Math.max(14, z.probabilite / 4)}
                                pathOptions={{
                                    color: MAP_COLORS[z.niveau_alerte] || '#60A5FA',
                                    fillColor: MAP_COLORS[z.niveau_alerte] || '#60A5FA',
                                    fillOpacity: 0.6,
                                    weight: 2,
                                }}
                                eventHandlers={{ click: () => setSelectedZone(z) }}
                            >
                                <Popup>
                                    <div className="map-popup">
                                        <strong>{z.nom}</strong><br />
                                        Niveau : {COULEURS[z.niveau_alerte]?.label}<br />
                                        Probabilité : {z.probabilite}%<br />
                                        Pluie 24h : {z.pluie_24h} mm<br />
                                        Population : {z.population?.toLocaleString('fr-FR')} hab.
                                    </div>
                                </Popup>
                            </CircleMarker>
                        ))}
                    </MapContainer>
                </div>

                <div className="carte-legend glass-card">
                    <h3>Légende</h3>
                    {Object.entries(COULEURS).map(([key, c]) => (
                        <div key={key} className="legend-item">
                            <span className="legend-dot" style={{ background: MAP_COLORS[key] }} />
                            <span>{c.label}</span>
                        </div>
                    ))}

                    <h3 style={{ marginTop: '1.5rem' }}>Zones ({zones.length})</h3>
                    <div className="zone-list">
                        {zones.map(z => {
                            const c = COULEURS[z.niveau_alerte]
                            const isSel = selectedZone?.zone_id === z.zone_id
                            return (
                                <div
                                    key={z.zone_id}
                                    className={isSel ? 'zone-item selected' : 'zone-item'}
                                    onClick={() => setSelectedZone(z)}
                                >
                                    <span className="legend-dot" style={{ background: MAP_COLORS[z.niveau_alerte] }} />
                                    <div>
                                        <div className="zone-name">{z.nom}</div>
                                        <div className="zone-meta">{z.probabilite}% &bull; {c?.label}</div>
                                    </div>
                                </div>
                            )
                        })}
                    </div>

                    {selectedZone && (
                        <div className="zone-detail">
                            <h4>{selectedZone.nom}</h4>
                            <table>
                                <tbody>
                                    <tr><td>Probabilité</td><td><strong>{selectedZone.probabilite}%</strong></td></tr>
                                    <tr><td>Pluie 24h</td><td>{selectedZone.pluie_24h} mm</td></tr>
                                    <tr><td>NDWI</td><td>{selectedZone.ndwi}</td></tr>
                                    <tr><td>SAR VV</td><td>{selectedZone.sar_vv}</td></tr>
                                    <tr><td>Population</td><td>{selectedZone.population?.toLocaleString('fr-FR')}</td></tr>
                                    {selectedZone.delai_heures && <tr><td>Délai</td><td>~{selectedZone.delai_heures}h</td></tr>}
                                </tbody>
                            </table>
                        <button
                                className="refresh-btn"
                                style={{width:'100%', marginTop:'0.75rem', justifyContent:'center'}}
                                onClick={() => navigate(`/historique/${selectedZone.zone_id}`)}
                            >
                                Voir l&#39;historique &rarr;
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
