# KATARA v6 - Systeme d'Alerte Precoce Inondations

> Plateforme IA de prediction et d'alerte pour les inondations en Afrique de l'Ouest
> Développée pour Lomé, Togo · 2026

---

## Architecture

```
katara_project/
├── katara_api.py         # API Flask + serveur de l'interface React
├── katara_model.py       # Moteur IA RandomForest (auto-entrainement + cache pkl)
├── katara_meteo.py       # Collecte météo temps réel (OpenWeatherMap)
├── katara_sat.py         # Données satellitaires Sentinel-1 (SAR/NDWI)
├── katara_sms.py         # Alertes SMS (Africa's Talking)
├── katara_db.py          # Base de données SQLite (historique + stats)
├── katara_scheduler.py   # Surveillance automatique (toutes les heures)
├── katara_zones.py       # Source unique des 5 zones surveillées
├── requirements.txt      # Dépendances Python
├── start.bat             # Lanceur Windows (double-clic = tout demarre)
└── katara_web/           # Interface React (Vite + Recharts + Leaflet)
    ├── src/
    │   ├── pages/        # Home, Alertes, Dashboard, Carte, Historique, APropos
    │   ├── components/   # Navbar, Footer, ErrorBoundary
    │   └── api/          # katara.js (API calls + demo data)
    └── dist/             # Build de production (servi par Flask)
```

---

## Demarrage rapide (Windows)

### Option 1 — Double-clic

```
Double-cliquez sur start.bat
```

Cela demarre l'API Flask qui sert egalement l'interface React.
Ouvre automatiquement http://localhost:5000 dans le navigateur.

### Option 2 — Ligne de commande

```bash
# 1. Installer les dependances
pip install -r requirements.txt

# 2. Construire l'interface (si nécessaire)
cd katara_web && npm install && npm run build && cd ..

# 3. Lancer le systeme
python katara_api.py
```

Interface disponible sur : **http://localhost:5000**

---

## Scheduler (surveillance automatique)

```bash
python katara_scheduler.py
```

Le scheduler tourne toutes les heures, enregistre les predictions en DB,
et envoie des SMS d'alerte si une zone passe en niveau CRITIQUE.

---

## Pages de l'interface

| Page | URL | Description |
|------|-----|-------------|
| Accueil | `/` | Stats live + liens rapides |
| Alertes | `/alertes` | Zones en alerte (critique/moyen) - refresh 30s |
| Dashboard | `/dashboard` | Tableau de bord technique - refresh 60s |
| Carte | `/carte` | Carte Leaflet interactive avec zones colorees |
| Historique | `/historique/:id` | Courbes historiques par zone |
| A propos | `/a-propos` | Mission + equipe + stack technologique |

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/status` | Sante de l'API |
| `GET /api/dashboard` | Donnees completes (5 zones) |
| `GET /api/alertes/actives` | Zones en alerte uniquement |
| `GET /api/zones` | Liste des zones |
| `GET /api/zones/:id/historique` | Historique des predictions |
| `GET /api/stats` | Stats globales (7 derniers jours) |

---

## Zones surveillees

| ID | Nom | Coord. | Population |
|----|-----|--------|-----------|
| LOM-001 | Be-Kpota | 6.1319, 1.2228 | 15 000 |
| LOM-002 | Agoe-Nyive | 6.1950, 1.2100 | 22 000 |
| LOM-003 | Baguida | 6.1000, 1.3000 | 8 000 |
| LOM-004 | Aflao-Gakli | 6.0984, 1.1950 | 11 000 |
| LOM-005 | Lome-Port | 6.1341, 1.2637 | 5 000 |

---

## Variables d'environnement

```env
OWM_API_KEY=       # OpenWeatherMap (meteo temps reel)
AT_API_KEY=        # Africa's Talking (SMS)
AT_USERNAME=       # Africa's Talking username
```

Sans ces cles, le systeme fonctionne en mode simulation.

---

## Stack Technologique

- **Backend** : Python 3.11 · Flask · SQLite · scikit-learn (RandomForest)
- **Frontend** : React 18 · Vite · Recharts · react-leaflet · lucide-react
- **Donnees** : Sentinel-1 SAR · OpenWeatherMap · OpenStreetMap
- **Alertes** : Africa's Talking SMS Gateway
- **Deploiement** : Render / Railway (Procfile + render.yaml inclus)
