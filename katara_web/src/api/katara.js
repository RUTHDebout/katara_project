const API = '/api'
let _lastSource = 'demo'

export function isApiLive() { return _lastSource === 'live' }

// Données de démo si l'API est hors ligne
const DEMO_DASHBOARD = {
    timestamp: new Date().toISOString(),
    zones: [
        { zone_id: 'LOM-001', nom: 'Bè-Kpota',    latitude: 6.1319, longitude: 1.2228, population: 15000, probabilite: 78, niveau_alerte: 'critique', delai_heures: 1,    alerte_declenchee: true,  pluie_24h: 67, humidite: 82, ndwi: 0.38, sar_vv: 0.58 },
        { zone_id: 'LOM-002', nom: 'Agoè-Nyivé',  latitude: 6.1950, longitude: 1.2100, population: 22000, probabilite: 45, niveau_alerte: 'moyen',    delai_heures: 6,    alerte_declenchee: false, pluie_24h: 38, humidite: 65, ndwi: 0.12, sar_vv: 0.38 },
        { zone_id: 'LOM-003', nom: 'Baguida',      latitude: 6.1000, longitude: 1.3000, population:  8000, probabilite:  8, niveau_alerte: 'faible',   delai_heures: null, alerte_declenchee: false, pluie_24h:  4, humidite: 45, ndwi:-0.15, sar_vv: 0.20 },
        { zone_id: 'LOM-004', nom: 'Aflao-Gakli',  latitude: 6.0984, longitude: 1.1950, population: 11000, probabilite: 62, niveau_alerte: 'moyen',    delai_heures: 4,    alerte_declenchee: false, pluie_24h: 54, humidite: 78, ndwi: 0.28, sar_vv: 0.50 },
        { zone_id: 'LOM-005', nom: 'Lomé-Port',    latitude: 6.1341, longitude: 1.2637, population:  5000, probabilite: 82, niveau_alerte: 'critique', delai_heures: 1,    alerte_declenchee: true,  pluie_24h: 71, humidite: 88, ndwi: 0.45, sar_vv: 0.65 },
    ],
    resume: { total_zones: 5, alertes_critiques: 2, alertes_moyennes: 2, population_a_risque: 61000 }
}

async function fetchWithFallback(url, fallback) {
    try {
        const r = await fetch(url, { signal: AbortSignal.timeout(3000) })
        if (!r.ok) throw new Error()
        _lastSource = 'live'
        return await r.json()
    } catch {
        _lastSource = 'demo'
        return fallback
    }
}

export async function getDashboard() {
    return fetchWithFallback(`${API}/dashboard`, DEMO_DASHBOARD)
}

const DEMO_ALERTES = {
    timestamp: new Date().toISOString(),
    get zones() {
        return DEMO_DASHBOARD.zones.filter(z => z.niveau_alerte === 'critique' || z.niveau_alerte === 'moyen')
    },
    total_alertes: 2,
}

export async function getAlertesActives() {
    return fetchWithFallback(`${API}/alertes/actives`, DEMO_ALERTES)
}

export async function getPrediction(zoneId, scenario = 'pluie_forte') {
    return fetchWithFallback(`${API}/zones/${zoneId}/prediction?scenario=${scenario}`, null)
}

const DEMO_STATS = {
    predictions_7j:   840,
    alertes_7j:        14,
    prob_moyenne:    48.5,
    derniere_maj:    new Date().toISOString(),
    sms_envoyes_7j:   28,
    cout_sms_7j_fcfa: 1400,
}

export async function getStats() {
    return fetchWithFallback(`${API}/stats`, DEMO_STATS)
}



export async function getZones() {
    return fetchWithFallback(`${API}/zones`, [])
}

export async function getHistorique(zoneId) {
    return fetchWithFallback(`${API}/zones/${zoneId}/historique`, [])
}

export const COULEURS = {
    critique: { bg: '#FFEBEE', text: '#C62828', border: '#EF9A9A', label: 'CRITIQUE' },
    moyen:    { bg: '#FFF3E0', text: '#E65100', border: '#FFCC80', label: 'MOYEN' },
    faible:   { bg: '#FFF8E1', text: '#F57F17', border: '#FFE082', label: 'FAIBLE' },
    normal:   { bg: '#E8F5E9', text: '#2E7D32', border: '#A5D6A7', label: 'NORMAL' },
}

export const CONSEILS = {
    critique: [
        '🚨 Évacuez immédiatement les zones basses et les berges',
        '📱 Appelez le 117 (ANPC) ou le 118 (Pompiers)',
        '🚫 Ne traversez jamais une rue inondée, même à pied',
        '⬆️ Montez à l\'étage ou sur les toits en cas de crue rapide',
        '💼 Prenez vos documents importants, médicaments et eau potable',
    ],
    moyen: [
        '⚠️ Surveillez de près le niveau des ruisseaux et canaux proches',
        '🏠 Déplacez vos biens vers les étages si possible',
        '📻 Restez à l\'écoute des bulletins météo de Météo-Togo',
        '🚗 Évitez les déplacements inutiles en dehors des zones élevées',
    ],
    faible: [
        '📋 Vérifiez que vos drains sont dégagés',
        '📦 Protégez les biens sensibles (documents, électronique)',
        '📡 Restez informé via KATARA et la radio nationale',
    ],
    normal: [
        '✅ Pas de risque immédiat — Situation normale',
        '🌱 Bon moment pour vérifier vos équipements d\'urgence',
    ],
}
