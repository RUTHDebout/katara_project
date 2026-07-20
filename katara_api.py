"""
╔══════════════════════════════════════════════════════════════╗
║         KATARA - API Flask                                  ║
║         Pont entre le dashboard et les modules Python       ║
╚══════════════════════════════════════════════════════════════╝

Lance avec : python katara_api.py
Puis ouvre : http://localhost:5000

📌 Installation :
   pip install flask flask-cors
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import json
import os
import sys

# Import des modules KATARA
sys.path.insert(0, os.path.dirname(__file__))
from katara_model import KataraModele, ZoneRisque, DonneesSatellitaires
from katara_meteo import CollecteurMeteo, simuler_meteo_lome
from katara_sat   import simuler_satellite
from katara_sms   import GestionnaireSMS
from katara_db    import DatabaseKATARA
from katara_zones import ZONES as ZONES_CONFIG   # v6 : source unique

app = Flask(__name__)
CORS(app)

# ── Initialisation des composants ──
modele   = KataraModele()          # auto-entraîne le RF au démarrage (v6)
db       = DatabaseKATARA()
sms_mgr  = GestionnaireSMS(mode_test=True)

OWM_KEY  = os.getenv("OWM_API_KEY", "")
meteo_collecteur = CollecteurMeteo(OWM_KEY) if OWM_KEY else None

def zone_to_dict(zone: ZoneRisque) -> dict:
    return {
        "zone_id": zone.zone_id, "nom": zone.nom,
        "latitude": zone.latitude, "longitude": zone.longitude,
        "altitude_m": zone.altitude_m, "population": zone.population,
        "type_sol": zone.type_sol,
    }

# ─────────────────────────────────────────────
# 📡 ROUTES API
# ─────────────────────────────────────────────

@app.route("/api/status")
def status():
    """Santé de l'API"""
    return jsonify({
        "status": "ok",
        "version": "6.1.0",
        "timestamp": datetime.now().isoformat(),
        "zones": len(ZONES_CONFIG),
        "meteo_api": "connectée" if meteo_collecteur else "simulation",
    })


@app.route("/api/zones")
def get_zones():
    """Liste toutes les zones surveillées"""
    return jsonify([zone_to_dict(z) for z in ZONES_CONFIG])


@app.route("/api/zones/<zone_id>/prediction")
def get_prediction(zone_id):
    """Calcule la prédiction pour une zone"""
    zone = next((z for z in ZONES_CONFIG if z.zone_id == zone_id), None)
    if not zone:
        return jsonify({"error": "Zone introuvable"}), 404

    # Météo
    scenario_meteo = request.args.get("scenario", "pluie_forte")
    if meteo_collecteur:
        meteo = meteo_collecteur.get_meteo_complete(zone.zone_id, zone.latitude, zone.longitude)
    else:
        meteo = simuler_meteo_lome(zone.zone_id, scenario_meteo)

    # Satellite
    sat_raw = simuler_satellite(zone.zone_id)
    sat = DonneesSatellitaires(
        zone_id=zone.zone_id, timestamp=datetime.now(),
        ndwi=sat_raw.ndwi, ndvi=sat_raw.ndvi, sentinel1_vv=sat_raw.sentinel1_vv
    )

    # Prédiction
    resultat = modele.predire(zone, meteo, sat)

    # Sauvegarde en base
    db.sauvegarder_prediction(resultat, meteo, sat)

    return jsonify({
        "zone_id":        resultat.zone_id,
        "timestamp":      resultat.timestamp.isoformat(),
        "probabilite":    resultat.probabilite,
        "probabilite_pct": round(resultat.probabilite * 100, 1),
        "niveau_alerte":  resultat.niveau_alerte,
        "delai_heures":   resultat.delai_heures,
        "alerte_declenchee": resultat.alerte_declenchee,
        "message_sms":    resultat.message_sms,
        "meteo": {
            "pluie_1h":  meteo.precipitations_mm_h,
            "pluie_24h": meteo.precipitations_mm_24h,
            "humidite":  meteo.humidite_sol_pct,
            "temperature": meteo.temperature_c,
            "description": meteo.description,
        },
        "satellite": {
            "ndwi":  sat.ndwi,
            "ndvi":  sat.ndvi,
            "sar_vv": sat.sentinel1_vv,
        }
    })


@app.route("/api/dashboard")
def get_dashboard():
    """Données complètes pour le dashboard — toutes les zones"""
    resultats = []
    for zone in ZONES_CONFIG:
        meteo = simuler_meteo_lome(zone.zone_id)
        sat_raw = simuler_satellite(zone.zone_id)
        sat = DonneesSatellitaires(
            zone_id=zone.zone_id, timestamp=datetime.now(),
            ndwi=sat_raw.ndwi, ndvi=sat_raw.ndvi, sentinel1_vv=sat_raw.sentinel1_vv
        )
        r = modele.predire(zone, meteo, sat)
        resultats.append({
            "zone_id": zone.zone_id,
            "nom": zone.nom,
            "latitude": zone.latitude,
            "longitude": zone.longitude,
            "population": zone.population,
            "probabilite": round(r.probabilite * 100, 1),
            "niveau_alerte": r.niveau_alerte,
            "delai_heures": r.delai_heures,
            "alerte_declenchee": r.alerte_declenchee,
            "pluie_24h": round(meteo.precipitations_mm_24h, 1),
            "humidite": round(meteo.humidite_sol_pct, 1),
            "ndwi": round(sat.ndwi, 3),
            "sar_vv": round(sat.sentinel1_vv, 3),
        })
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "zones": resultats,
        "resume": {
            "total_zones": len(resultats),
            "alertes_critiques": sum(1 for r in resultats if r["niveau_alerte"] == "critique"),
            "alertes_moyennes":  sum(1 for r in resultats if r["niveau_alerte"] == "moyen"),
            "population_a_risque": sum(z.population for z in ZONES_CONFIG
                                       if any(r["niveau_alerte"] in ("critique","moyen")
                                              and r["zone_id"] == z.zone_id for r in resultats))
        }
    })




@app.route("/api/alertes/actives")
def get_alertes_actives():
    """Zones en alerte critique ou moyenne uniquement"""
    resultats = []
    for zone in ZONES_CONFIG:
        meteo = simuler_meteo_lome(zone.zone_id)
        sat_raw = simuler_satellite(zone.zone_id)
        sat = DonneesSatellitaires(
            zone_id=zone.zone_id, timestamp=datetime.now(),
            ndwi=sat_raw.ndwi, ndvi=sat_raw.ndvi, sentinel1_vv=sat_raw.sentinel1_vv
        )
        r = modele.predire(zone, meteo, sat)
        if r.niveau_alerte in ("critique", "moyen"):
            resultats.append({
                "zone_id": zone.zone_id,
                "nom": zone.nom,
                "latitude": zone.latitude,
                "longitude": zone.longitude,
                "population": zone.population,
                "probabilite": round(r.probabilite * 100, 1),
                "niveau_alerte": r.niveau_alerte,
                "delai_heures": r.delai_heures,
                "alerte_declenchee": r.alerte_declenchee,
                "pluie_24h": round(meteo.precipitations_mm_24h, 1),
                "humidite": round(meteo.humidite_sol_pct, 1),
                "ndwi": round(sat.ndwi, 3),
                "sar_vv": round(sat.sentinel1_vv, 3),
            })
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "zones": resultats,
        "total_alertes": len(resultats),
    })

@app.route("/api/zones/<zone_id>/historique")
def get_historique(zone_id):
    """Historique des 24 dernières prédictions pour une zone"""
    historique = db.get_historique(zone_id, limite=24)
    return jsonify(historique)


@app.route("/api/alertes/log")
def get_alertes_log():
    """Journal des alertes SMS envoyées"""
    try:
        with open("katara_alertes_log.json") as f:
            logs = json.load(f)
        return jsonify(logs[-50:])  # 50 dernières
    except FileNotFoundError:
        return jsonify([])


@app.route("/api/zones/<zone_id>/sms", methods=["POST"])
def envoyer_alerte_manuelle(zone_id):
    """Déclenche manuellement une alerte SMS pour une zone"""
    zone = next((z for z in ZONES_CONFIG if z.zone_id == zone_id), None)
    if not zone:
        return jsonify({"error": "Zone introuvable"}), 404

    data = request.get_json() or {}
    niveau  = data.get("niveau", "moyen")
    message = data.get("message", f"⚠️ Alerte manuelle KATARA — {zone.nom}")

    rapport = sms_mgr.alerter_zone(
        zone_id=zone.zone_id, zone_nom=zone.nom,
        numeros=zone.telephones, niveau_alerte=niveau,
        probabilite=0.8, message_custom=message
    )

    return jsonify({
        "envoyes": rapport.total_envoyes,
        "echecs":  rapport.total_echecs,
        "cout_fcfa": rapport.cout_total_fcfa,
    })



@app.route("/api/stats")
def get_stats():
    """Statistiques globales des 7 derniers jours"""
    return jsonify(db.get_stats_globales())



# ─────────────────────────────────────────────
# Serving React build (katara_web/dist)
# ─────────────────────────────────────────────
DIST_DIR = os.path.join(os.path.dirname(__file__), 'katara_web', 'dist')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    """Sert l'interface React (prod build)"""
    if path and os.path.exists(os.path.join(DIST_DIR, path)):
        return send_from_directory(DIST_DIR, path)
    return send_from_directory(DIST_DIR, 'index.html')


if __name__ == "__main__":
    print("=" * 55)
    print("   KATARA v6 - Interface + API")
    print("  Interface : http://localhost:5000")
    print("  API       : http://localhost:5000/api/dashboard")
    print("=" * 55)
    app.run(debug=True, host="0.0.0.0", port=5000)
