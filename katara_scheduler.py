"""
╔══════════════════════════════════════════════════════════════╗
║         KATARA - Scheduler Automatique                      ║
║         Lance la surveillance toutes les heures             ║
╚══════════════════════════════════════════════════════════════╝

Lance avec : python katara_scheduler.py

Ce script tourne en permanence et :
✅ Collecte météo + satellite toutes les heures
✅ Calcule les prédictions pour toutes les zones
✅ Envoie les SMS si alerte détectée
✅ Sauvegarde tout en base de données
✅ Envoie un rapport quotidien à 7h00

📌 Installation :
   pip install schedule
"""

import schedule
import time
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from katara_model import KataraModele, ZoneRisque, DonneesSatellitaires
from katara_meteo import CollecteurMeteo, simuler_meteo_lome
from katara_sat   import simuler_satellite
from katara_sms   import GestionnaireSMS
from katara_db    import DatabaseKATARA
from katara_zones import ZONES              # v6 : source unique

# ─────────────────────────────────────────────
# ⚙️ CONFIGURATION
# ─────────────────────────────────────────────
OWM_KEY  = os.getenv("OWM_API_KEY", "")
AT_USER  = os.getenv("AT_USERNAME", "sandbox")
AT_KEY   = os.getenv("AT_API_KEY",  "")
MODE_TEST = AT_USER == "sandbox" or not AT_KEY

# ── Initialisation ──
modele           = KataraModele()
db               = DatabaseKATARA()
sms_mgr          = GestionnaireSMS(AT_USER, AT_KEY, mode_test=MODE_TEST)
meteo_collecteur = CollecteurMeteo(OWM_KEY) if OWM_KEY else None

# Sauvegarde des zones en base
for z in ZONES:
    db.sauvegarder_zone(z)


# ─────────────────────────────────────────────
# 🔁 CYCLE DE SURVEILLANCE
# ─────────────────────────────────────────────
def cycle_surveillance():
    """
    Un cycle complet : météo → satellite → prédiction → SMS → DB
    S'exécute toutes les heures.
    """
    print("\n" + "" * 55)
    print(f"   KATARA  Cycle {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("" * 55)

    alertes_critiques = []
    alertes_moyennes  = []

    for zone in ZONES:
        print(f"\n {zone.nom} ({zone.zone_id})")

        # 1. Météo
        if meteo_collecteur:
            meteo = meteo_collecteur.get_meteo_complete(zone.zone_id, zone.latitude, zone.longitude)
        else:
            meteo = simuler_meteo_lome(zone.zone_id)

        if meteo is None:
            print(f"     Météo indisponible, ignoré")
            continue

        # 2. Satellite
        sat_raw = simuler_satellite(zone.zone_id)
        sat = DonneesSatellitaires(
            zone_id=zone.zone_id, timestamp=datetime.now(),
            ndwi=sat_raw.ndwi, ndvi=sat_raw.ndvi, sentinel1_vv=sat_raw.sentinel1_vv
        )

        # 3. Prédiction
        resultat = modele.predire(zone, meteo, sat)
        print(f"    {resultat.niveau_alerte.upper()}  {resultat.probabilite*100:.0f}% | Pluie: {meteo.precipitations_mm_24h:.0f}mm")

        # 4. Sauvegarde DB
        db.sauvegarder_prediction(resultat, meteo, sat)

        # 5. Collecte alertes
        if resultat.niveau_alerte == "critique":
            alertes_critiques.append((zone, resultat))
        elif resultat.niveau_alerte == "moyen":
            alertes_moyennes.append((zone, resultat))

    # 6. Envoi SMS (groupé pour éviter spam)
    _envoyer_alertes(alertes_critiques, "critique")
    _envoyer_alertes(alertes_moyennes,  "moyen")

    print(f"\n Cycle terminé | {len(alertes_critiques)} critique(s), {len(alertes_moyennes)} moyen(s)")
    _sauvegarder_etat(alertes_critiques, alertes_moyennes)


def _envoyer_alertes(alertes: list, niveau: str):
    """Envoie les SMS pour un niveau d'alerte"""
    if not alertes:
        return

    for zone, resultat in alertes:
        if not zone.telephones:
            continue
        rapport = sms_mgr.alerter_zone(
            zone_id       = zone.zone_id,
            zone_nom      = zone.nom,
            numeros       = zone.telephones,
            niveau_alerte = niveau,
            probabilite   = resultat.probabilite,
            delai_heures  = resultat.delai_heures,
            message_custom = resultat.message_sms,
        )
        db.sauvegarder_alerte_sms(rapport)


def _sauvegarder_etat(critiques, moyens):
    """Sauvegarde l'état courant dans un fichier JSON (pour le dashboard)"""
    etat = {
        "timestamp": datetime.now().isoformat(),
        "alertes_critiques": [z.zone_id for z, _ in critiques],
        "alertes_moyennes":  [z.zone_id for z, _ in moyens],
    }
    with open("katara_etat.json", "w") as f:
        json.dump(etat, f, indent=2)


# ─────────────────────────────────────────────
# 📊 RAPPORT QUOTIDIEN (7h00)
# ─────────────────────────────────────────────
def rapport_quotidien():
    """Envoie un résumé SMS quotidien à l'équipe KATARA"""
    print(f"\n RAPPORT QUOTIDIEN  {datetime.now().strftime('%d/%m/%Y')}")

    stats = db.get_stats_globales()
    alertes = db.get_alertes_critiques_recentes(heures=24)

    # Numéros de l'équipe KATARA
    equipe = os.getenv("KATARA_TEAM_PHONES", "").split(",")
    equipe = [p.strip() for p in equipe if p.strip()]

    if not equipe:
        print("     Pas de numéros d'équipe configurés (KATARA_TEAM_PHONES)")
        return

    message = (
        f"📊 KATARA Rapport {datetime.now().strftime('%d/%m')}\n"
        f"Prédictions 24h: {stats['predictions_7j']}\n"
        f"Alertes: {stats['alertes_7j']}\n"
        f"SMS envoyés: {stats['sms_envoyes_7j']}\n"
        f"Zones critiques: {len([a for a in alertes if a['niveau_alerte']=='critique'])}"
    )

    for numero in equipe:
        sms_mgr.envoyer_sms(numero, message)

    print(f"    Rapport envoyé à {len(equipe)} contacts")


# ─────────────────────────────────────────────
# ⚙️ PLANIFICATION
# ─────────────────────────────────────────────
def demarrer():
    print("=" * 55)
    print("   KATARA Scheduler  Démarrage")
    print(f"  Mode : {'TEST (simulation)' if MODE_TEST else 'PRODUCTION'}")
    print(f"  Zones surveillées : {len(ZONES)}")
    print(f"  Météo API : {'OpenWeatherMap' if meteo_collecteur else 'Simulation'}")
    print("=" * 55)

    # Premier cycle immédiat
    cycle_surveillance()

    # Planification
    schedule.every(1).hours.do(cycle_surveillance)
    schedule.every().day.at("07:00").do(rapport_quotidien)
    schedule.every().day.at("03:00").do(lambda: db.purger_anciennes_donnees(90))

    print(f"\n Prochains cycles planifiés :")
    print(f"    Surveillance : toutes les heures")
    print(f"    Rapport équipe : 07:00 quotidien")
    print(f"    Purge DB : 03:00 quotidien")
    print(f"\n[Ctrl+C pour arrêter]\n")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    try:
        demarrer()
    except KeyboardInterrupt:
        print("\n\n KATARA Scheduler arrêté.")
