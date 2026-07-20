"""
╔══════════════════════════════════════════════════════════════╗
║         KATARA - Module Météo en Temps Réel                 ║
║         Source : OpenWeatherMap API (gratuit)               ║
╚══════════════════════════════════════════════════════════════╝

Ce module récupère automatiquement les données météo
pour chaque zone surveillée par KATARA.

📌 Pour obtenir ta clé API gratuite :
   → https://openweathermap.org/api
   → Crée un compte, copie ta clé API
   → Plan gratuit = 1000 appels/jour (largement suffisant !)

📌 Installation :
   pip install requests python-dotenv
"""

import requests
import os
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, List
import json
import time

# Pour charger la clé API depuis un fichier .env (plus sécurisé)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # pas grave si pas installé


# ─────────────────────────────────────────────
# ⚙️ CONFIGURATION
# ─────────────────────────────────────────────

# Ta clé API OpenWeatherMap
# Option 1 : directement ici (pour tester)
# Option 2 : dans un fichier .env avec la ligne : OWM_API_KEY=ta_cle_ici
OWM_API_KEY = os.getenv("OWM_API_KEY", "METS_TA_CLE_ICI")

# URLs de l'API
OWM_BASE_URL    = "https://api.openweathermap.org/data/2.5"
OWM_CURRENT_URL = f"{OWM_BASE_URL}/weather"
OWM_FORECAST_URL = f"{OWM_BASE_URL}/forecast"   # prévisions 5 jours
OWM_ONECALL_URL  = "https://api.openweathermap.org/data/3.0/onecall"


# ─────────────────────────────────────────────
# 📦 STRUCTURE DES DONNÉES MÉTÉO RETOURNÉES
# ─────────────────────────────────────────────
@dataclass
class DonneesMeteoTempsReel:
    """Données météo enrichies récupérées depuis OpenWeatherMap"""
    
    zone_id: str
    timestamp: datetime
    
    # Précipitations
    precipitations_mm_h: float      # pluie dernière heure (mm)
    precipitations_mm_3h: float     # pluie 3 dernières heures
    precipitations_mm_24h: float    # estimé 24h (somme prévisions)
    
    # Conditions
    humidite_sol_pct: float         # humidité de l'air (proxy sol)
    temperature_c: float
    evapotranspiration_mm: float    # calculé à partir temp + humidité
    
    # Infos supplémentaires
    description: str                # "pluie légère", "orage", etc.
    vitesse_vent_ms: float
    pression_hpa: float
    couverture_nuages_pct: float
    
    # Prévisions (prochaines heures)
    previsions_3h: Optional[list] = None   # liste de précipitations prévues


# ─────────────────────────────────────────────
# 🌦️ COLLECTEUR MÉTÉO
# ─────────────────────────────────────────────
class CollecteurMeteo:
    """
    Récupère les données météo en temps réel depuis OpenWeatherMap
    pour n'importe quelle zone géographique.
    """
    
    def __init__(self, api_key: str = OWM_API_KEY):
        self.api_key = api_key
        self._verifier_cle()
    
    def _verifier_cle(self):
        """Vérifie que la clé API est configurée"""
        if self.api_key == "METS_TA_CLE_ICI":
            print("  ATTENTION : Clé API OpenWeatherMap non configurée !")
            print("    Va sur https://openweathermap.org/api pour en obtenir une gratuite")
            print("    Puis remplace 'METS_TA_CLE_ICI' par ta vraie clé\n")
    
    # ── RÉCUPÉRATION MÉTÉO ACTUELLE ───────────────
    def get_meteo_actuelle(
        self,
        zone_id: str,
        latitude: float,
        longitude: float
    ) -> Optional[DonneesMeteoTempsReel]:
        """
        Récupère la météo actuelle pour des coordonnées GPS.
        
        Exemple :
            meteo = collecteur.get_meteo_actuelle("LOM-001", 6.1319, 1.2228)
        """
        
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": self.api_key,
            "units": "metric",   # Celsius
            "lang": "fr"         # descriptions en français
        }
        
        try:
            print(f" Récupération météo pour zone {zone_id}...")
            response = requests.get(OWM_CURRENT_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extraction des précipitations (OWM met ça dans 'rain')
            pluie_1h = data.get("rain", {}).get("1h", 0.0)
            pluie_3h = data.get("rain", {}).get("3h", 0.0)
            
            # Calcul evapotranspiration simplifié (formule de Hargreaves)
            temp = data["main"]["temp"]
            humidite = data["main"]["humidity"]
            eto = max(0, (0.0023 * (temp + 17.8) * 5.0) * (1 - humidite/100))
            
            return DonneesMeteoTempsReel(
                zone_id                = zone_id,
                timestamp              = datetime.fromtimestamp(data["dt"]),
                precipitations_mm_h    = pluie_1h,
                precipitations_mm_3h   = pluie_3h,
                precipitations_mm_24h  = pluie_3h * 8,  # estimation (sera affiné avec prévisions)
                humidite_sol_pct       = humidite,
                temperature_c          = temp,
                evapotranspiration_mm  = round(eto, 2),
                description            = data["weather"][0]["description"],
                vitesse_vent_ms        = data["wind"]["speed"],
                pression_hpa           = data["main"]["pressure"],
                couverture_nuages_pct  = data["clouds"]["all"],
            )
            
        except requests.exceptions.ConnectionError:
            print(f" Pas de connexion internet pour zone {zone_id}")
            return None
        except requests.exceptions.HTTPError as e:
            if "401" in str(e):
                print(f" Clé API invalide ! Vérifie ta clé OpenWeatherMap.")
            else:
                print(f" Erreur API : {e}")
            return None
        except Exception as e:
            print(f" Erreur inattendue : {e}")
            return None
    
    # ── PRÉVISIONS 24H ────────────────────────────
    def get_previsions_24h(
        self,
        latitude: float,
        longitude: float
    ) -> List[dict]:
        """
        Récupère les prévisions sur les 24 prochaines heures.
        Utile pour estimer les précipitations cumulées.
        """
        
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": self.api_key,
            "units": "metric",
            "cnt": 8,   # 8 créneaux de 3h = 24h
            "lang": "fr"
        }
        
        try:
            response = requests.get(OWM_FORECAST_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            previsions = []
            for item in data["list"]:
                previsions.append({
                    "heure": datetime.fromtimestamp(item["dt"]).strftime("%H:%M"),
                    "temp": item["main"]["temp"],
                    "humidite": item["main"]["humidity"],
                    "pluie_3h": item.get("rain", {}).get("3h", 0.0),
                    "description": item["weather"][0]["description"]
                })
            
            return previsions
            
        except Exception as e:
            print(f" Impossible de récupérer les prévisions : {e}")
            return []
    
    # ── MÉTÉO COMPLÈTE (actuelle + prévisions) ────
    def get_meteo_complete(
        self,
        zone_id: str,
        latitude: float,
        longitude: float
    ) -> Optional[DonneesMeteoTempsReel]:
        """
        Version enrichie : météo actuelle + prévisions 24h intégrées.
        C'est cette fonction que KATARA utilise principalement.
        """
        
        meteo = self.get_meteo_actuelle(zone_id, latitude, longitude)
        
        if meteo is None:
            return None
        
        # Enrichir avec les prévisions
        previsions = self.get_previsions_24h(latitude, longitude)
        
        if previsions:
            # Calcul des précipitations cumulées sur 24h
            pluie_24h = sum(p["pluie_3h"] for p in previsions)
            meteo.precipitations_mm_24h = meteo.precipitations_mm_3h + pluie_24h
            meteo.previsions_3h = previsions
        
        return meteo
    
    # ── SURVEILLANCE MULTI-ZONES ──────────────────
    def surveiller_zones(self, zones: list) -> List[DonneesMeteoTempsReel]:
        """
        Récupère la météo pour toutes les zones KATARA.
        
        zones = liste de dicts avec : zone_id, latitude, longitude
        
        Exemple :
            zones = [
                {"zone_id": "LOM-001", "latitude": 6.1319, "longitude": 1.2228},
                {"zone_id": "LOM-002", "latitude": 6.1500, "longitude": 1.2100},
            ]
        """
        
        resultats = []
        
        for zone in zones:
            meteo = self.get_meteo_complete(
                zone["zone_id"],
                zone["latitude"],
                zone["longitude"]
            )
            
            if meteo:
                resultats.append(meteo)
                self._afficher_resume(meteo)
            
            # Petite pause entre les appels (respect des limites API)
            time.sleep(0.5)
        
        return resultats
    
    # ── AFFICHAGE RÉSUMÉ ──────────────────────────
    def _afficher_resume(self, meteo: DonneesMeteoTempsReel):
        """Affiche un résumé lisible dans la console"""
        
        print(f"\n Zone {meteo.zone_id} | {meteo.timestamp.strftime('%d/%m/%Y %H:%M')}")
        print(f"     Pluie dernière heure  : {meteo.precipitations_mm_h:.1f} mm")
        print(f"     Pluie estimée 24h     : {meteo.precipitations_mm_24h:.1f} mm")
        print(f"    Humidité              : {meteo.humidite_sol_pct:.0f}%")
        print(f"     Température           : {meteo.temperature_c:.1f}C")
        print(f"    Vent                  : {meteo.vitesse_vent_ms:.1f} m/s")
        print(f"    Conditions            : {meteo.description}")
        
        # Alerte rapide si pluie forte
        if meteo.precipitations_mm_24h >= 50:
            print(f"    ATTENTION : Seuil de 50mm/24h dépassé !")
        elif meteo.precipitations_mm_24h >= 20:
            print(f"     Pluie significative, surveillance renforcée")


# ─────────────────────────────────────────────
# 📡 MODE SIMULATION (sans clé API)
# ─────────────────────────────────────────────
def simuler_meteo_lome(zone_id: str = "LOM-001", scenario: str = "orage") -> DonneesMeteoTempsReel:
    """
    Génère des données météo simulées pour tester KATARA
    sans avoir besoin de la clé API.
    
    Scénarios disponibles : "sec", "pluie_legere", "pluie_forte", "orage"
    """
    
    scenarios = {
        "sec": {
            "pluie_h": 0.0, "pluie_24h": 2.0, "humidite": 55,
            "temp": 32.0, "description": "ciel dégagé", "vent": 2.5
        },
        "pluie_legere": {
            "pluie_h": 3.5, "pluie_24h": 18.0, "humidite": 72,
            "temp": 26.0, "description": "pluie légère", "vent": 4.0
        },
        "pluie_forte": {
            "pluie_h": 14.0, "pluie_24h": 58.0, "humidite": 88,
            "temp": 24.0, "description": "forte pluie", "vent": 7.5
        },
        "orage": {
            "pluie_h": 25.0, "pluie_24h": 95.0, "humidite": 96,
            "temp": 22.0, "description": "orage violent", "vent": 15.0
        }
    }
    
    s = scenarios.get(scenario, scenarios["orage"])
    
    return DonneesMeteoTempsReel(
        zone_id               = zone_id,
        timestamp             = datetime.now(),
        precipitations_mm_h   = s["pluie_h"],
        precipitations_mm_3h  = s["pluie_h"] * 3,
        precipitations_mm_24h = s["pluie_24h"],
        humidite_sol_pct      = s["humidite"],
        temperature_c         = s["temp"],
        evapotranspiration_mm = round(max(0, (0.0023 * (s["temp"] + 17.8) * 5.0) * (1 - s["humidite"]/100)), 2),
        description           = s["description"],
        vitesse_vent_ms       = s["vent"],
        pression_hpa          = 1008.0,
        couverture_nuages_pct = 95 if "pluie" in s["description"] or "orage" in s["description"] else 20,
        previsions_3h         = None
    )


# ─────────────────────────────────────────────
# 🚀 TEST / DÉMONSTRATION
# ─────────────────────────────────────────────
if __name__ == "__main__":
    
    print("=" * 60)
    print("   KATARA - Module Météo Temps Réel | Test")
    print("=" * 60)
    
    # ── TEST 1 : Simulation (fonctionne toujours) ──
    print("\n TEST 1 : Données simulées (scénario orage)")
    print("-" * 45)
    
    for scenario in ["sec", "pluie_forte", "orage"]:
        meteo_sim = simuler_meteo_lome("LOM-001", scenario)
        print(f"\n Scénario : {scenario.upper()}")
        print(f"   Pluie 1h  : {meteo_sim.precipitations_mm_h} mm")
        print(f"   Pluie 24h : {meteo_sim.precipitations_mm_24h} mm")
        print(f"   Humidité  : {meteo_sim.humidite_sol_pct}%")
        print(f"   Conditions: {meteo_sim.description}")
        
        if meteo_sim.precipitations_mm_24h >= 50:
            print(f"     Seuil d'alerte KATARA dépassé !")
    
    # ── TEST 2 : API Réelle ──
    print("\n\n TEST 2 : API OpenWeatherMap (Lomé, Togo)")
    print("-" * 45)
    
    if OWM_API_KEY != "METS_TA_CLE_ICI":
        collecteur = CollecteurMeteo(OWM_API_KEY)
        
        # Zones à surveiller dans la région Maritime
        zones_maritimes = [
            {"zone_id": "LOM-001", "nom": "Bè-Kpota",    "latitude": 6.1319, "longitude": 1.2228},
            {"zone_id": "LOM-002", "nom": "Agoè",         "latitude": 6.1950, "longitude": 1.2100},
            {"zone_id": "LOM-003", "nom": "Baguida",      "latitude": 6.1000, "longitude": 1.3000},
        ]
        
        print(f"\n  Surveillance de {len(zones_maritimes)} zones...")
        resultats = collecteur.surveiller_zones(zones_maritimes)
        
        print(f"\n {len(resultats)} zones surveillées avec succès")
        
        # Afficher les prévisions de la première zone
        if resultats and resultats[0].previsions_3h:
            print(f"\n Prévisions 24h pour {resultats[0].zone_id} :")
            for prev in resultats[0].previsions_3h[:4]:
                print(f"   {prev['heure']}  {prev['pluie_3h']:.1f}mm | {prev['description']}")
    
    else:
        print("\n  Clé API non configurée - utilise la simulation pour l'instant")
        print("   Pour activer l'API réelle :")
        print("   1. Va sur https://openweathermap.org/api")
        print("   2. Crée un compte gratuit")
        print("   3. Copie ta clé API")
        print("   4. Remplace 'METS_TA_CLE_ICI' par ta clé dans ce fichier")
        print("      OU crée un fichier .env avec : OWM_API_KEY=ta_cle")
    
    # ── INTÉGRATION AVEC KATARA MODÈLE ──
    print("\n\n TEST 3 : Intégration avec katara_model.py")
    print("-" * 45)
    print("""
# Comment utiliser les deux ensemble :

from katara_model import KataraModele, ZoneRisque, DonneesSatellitaires
from katara_meteo import CollecteurMeteo, simuler_meteo_lome
from datetime import datetime

# 1. Définir la zone
zone = ZoneRisque(
    zone_id="LOM-001", nom="Bè-Kpota",
    latitude=6.1319, longitude=1.2228,
    altitude_m=8.5, superficie_bassin_km2=42.3,
    type_sol="argileux", capacite_drainage=120.0,
    population=15000
)

# 2. Récupérer météo (API ou simulation)
collecteur = CollecteurMeteo("TA_CLE_API")
meteo = collecteur.get_meteo_complete("LOM-001", zone.latitude, zone.longitude)
# OU en simulation :
# meteo = simuler_meteo_lome("LOM-001", "orage")

# 3. Ajouter les données satellitaires
satellite = DonneesSatellitaires(
    zone_id="LOM-001", timestamp=datetime.now(),
    ndwi=0.42, ndvi=0.18, sentinel1_vv=0.61
)

# 4. Prédire !
modele = KataraModele()
resultat = modele.predire(zone, meteo, satellite)
print(resultat.message_sms)
""")
    
    print("=" * 60)
    print("KATARA  2025 - Ruth | Lomé, Togo")
    print("=" * 60)
