"""
╔══════════════════════════════════════════════════════════════╗
║       KATARA - Module Données Satellitaires                 ║
║       Source : Google Earth Engine (GEE)                    ║
╚══════════════════════════════════════════════════════════════╝

Ce module récupère automatiquement :
- NDWI  : indice d'eau (Sentinel-2)
- NDVI  : indice de végétation (Sentinel-2)
- SAR   : radar Sentinel-1 (détecte l'eau même sous les nuages !)
- Landsat : historique des inondations passées

📌 Pour utiliser GEE :
   1. Crée un compte sur : https://earthengine.google.com
   2. Fais une demande d'accès (gratuit pour la recherche/ONG)
   3. Installe : pip install earthengine-api
   4. Authentifie : earthengine authenticate
   
📌 Alternative SANS GEE :
   Ce fichier inclut aussi un mode STAC/Planetary Computer
   de Microsoft (100% gratuit, sans inscription)
"""

import os
import json
import time
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Tuple

# ─────────────────────────────────────────────
# 📦 IMPORTS CONDITIONNELS
# ─────────────────────────────────────────────
# On gère le cas où les librairies ne sont pas encore installées

GEE_DISPONIBLE = False
PLANETARY_DISPONIBLE = False

try:
    import ee
    GEE_DISPONIBLE = True
except ImportError:
    pass

try:
    import requests
    REQUESTS_DISPONIBLE = True
except ImportError:
    REQUESTS_DISPONIBLE = False


# ─────────────────────────────────────────────
# 📦 STRUCTURE DES DONNÉES SATELLITAIRES
# ─────────────────────────────────────────────
@dataclass
class DonneesSatellitairesTempsReel:
    """Indices satellitaires extraits pour une zone"""
    
    zone_id: str
    timestamp: datetime
    
    # Indices spectraux (Sentinel-2)
    ndwi: float       # Eau : >0 = présence eau, <0 = sol/végétation
    ndvi: float       # Végétation : >0.3 = végétation dense, <0.1 = sol nu
    
    # Radar (Sentinel-1) - fonctionne même sous les nuages !
    sentinel1_vv: float    # polarisation VV : surfaces d'eau = valeurs élevées
    sentinel1_vh: float    # polarisation VH : complémentaire
    
    # Comparaison historique
    ndwi_anomalie: float   # différence avec la moyenne historique
    
    # Métadonnées
    source: str            # "GEE", "Planetary", "Simulation"
    couverture_nuages_pct: float  # % de nuages sur l'image
    qualite: str           # "bonne", "moyenne", "faible"


# ─────────────────────────────────────────────
# 🛰️ COLLECTEUR SATELLITAIRE - GOOGLE EARTH ENGINE
# ─────────────────────────────────────────────
class CollecteurGEE:
    """
    Récupère les indices satellitaires via Google Earth Engine.
    
    ⚠️  Nécessite un compte GEE approuvé.
    """
    
    def __init__(self, projet_gee: str = "katara-flood-prediction"):
        """
        projet_gee : ton nom de projet dans GEE
        """
        self.projet = projet_gee
        self.initialise = False
        self._initialiser()
    
    def _initialiser(self):
        """Initialise la connexion GEE"""
        if not GEE_DISPONIBLE:
            print("  earthengine-api non installé.")
            print("   Installe avec : pip install earthengine-api")
            return
        
        try:
            ee.Initialize(project=self.projet)
            self.initialise = True
            print(f" Google Earth Engine connecté (projet: {self.projet})")
        except Exception as e:
            print(f"  GEE non authentifié : {e}")
            print("   Lance : earthengine authenticate")
    
    def get_indices(
        self,
        zone_id: str,
        latitude: float,
        longitude: float,
        rayon_m: int = 5000,        # rayon autour du point en mètres
        jours_historique: int = 30  # on prend les 30 derniers jours
    ) -> Optional[DonneesSatellitairesTempsReel]:
        """
        Calcule NDWI, NDVI et Sentinel-1 pour une zone.
        """
        
        if not self.initialise:
            print(" GEE non initialisé")
            return None
        
        try:
            print(f"  Récupération satellite GEE pour zone {zone_id}...")
            
            # Définir la zone d'intérêt
            point = ee.Geometry.Point([longitude, latitude])
            zone = point.buffer(rayon_m)
            
            date_fin   = datetime.now()
            date_debut = date_fin - timedelta(days=jours_historique)
            
            # ── SENTINEL-2 : NDWI et NDVI ──
            s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(zone)
                .filterDate(date_debut.strftime("%Y-%m-%d"), date_fin.strftime("%Y-%m-%d"))
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
                .sort("CLOUDY_PIXEL_PERCENTAGE")
                .first()
            )
            
            # NDWI = (Vert - NIR) / (Vert + NIR)
            ndwi_image = s2.normalizedDifference(["B3", "B8"]).rename("NDWI")
            # NDVI = (NIR - Rouge) / (NIR + Rouge)
            ndvi_image = s2.normalizedDifference(["B8", "B4"]).rename("NDVI")
            
            ndwi_val = ndwi_image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=zone,
                scale=10
            ).get("NDWI").getInfo()
            
            ndvi_val = ndvi_image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=zone,
                scale=10
            ).get("NDVI").getInfo()
            
            # ── SENTINEL-1 : SAR Radar ──
            s1 = (ee.ImageCollection("COPERNICUS/S1_GRD")
                .filterBounds(zone)
                .filterDate(date_debut.strftime("%Y-%m-%d"), date_fin.strftime("%Y-%m-%d"))
                .filter(ee.Filter.eq("instrumentMode", "IW"))
                .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
                .sort("system:time_start", False)
                .first()
            )
            
            vv_val = s1.select("VV").reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=zone,
                scale=10
            ).get("VV").getInfo()
            
            vh_val = s1.select("VH").reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=zone,
                scale=10
            ).get("VH").getInfo() if "VH" in s1.bandNames().getInfo() else -20.0
            
            # ── ANOMALIE NDWI (comparaison historique) ──
            ndwi_historique = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(zone)
                .filterDate("2019-01-01", date_debut.strftime("%Y-%m-%d"))
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
                .map(lambda img: img.normalizedDifference(["B3", "B8"]).rename("NDWI"))
                .mean()
            )
            
            ndwi_moy = ndwi_historique.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=zone,
                scale=10
            ).get("NDWI").getInfo()
            
            anomalie = (ndwi_val or 0) - (ndwi_moy or 0)
            
            # Normalisation SAR (dB vers 0-1)
            vv_normalise = max(0, min(1, (vv_val + 30) / 30)) if vv_val else 0.3
            
            return DonneesSatellitairesTempsReel(
                zone_id              = zone_id,
                timestamp            = datetime.now(),
                ndwi                 = round(ndwi_val or 0, 4),
                ndvi                 = round(ndvi_val or 0, 4),
                sentinel1_vv         = round(vv_normalise, 4),
                sentinel1_vh         = round(max(0, min(1, ((vh_val or -25) + 30) / 30)), 4),
                ndwi_anomalie        = round(anomalie, 4),
                source               = "GEE",
                couverture_nuages_pct = 10.0,
                qualite              = "bonne"
            )
            
        except Exception as e:
            print(f" Erreur GEE pour zone {zone_id} : {e}")
            return None


# ─────────────────────────────────────────────
# 🌐 ALTERNATIVE : Microsoft Planetary Computer
# ─────────────────────────────────────────────
class CollecteurPlanetaryComputer:
    """
    Alternative à GEE via l'API STAC de Microsoft Planetary Computer.
    100% gratuit, sans inscription nécessaire !
    
    Installation : pip install pystac-client planetary-computer rasterio
    """
    
    STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
    
    def __init__(self):
        self.disponible = self._verifier_disponibilite()
    
    def _verifier_disponibilite(self) -> bool:
        try:
            import pystac_client
            import planetary_computer
            return True
        except ImportError:
            return False
    
    def get_indices(
        self,
        zone_id: str,
        latitude: float,
        longitude: float,
        rayon_deg: float = 0.05
    ) -> Optional[DonneesSatellitairesTempsReel]:
        """
        Récupère les indices via Planetary Computer (alternative gratuite).
        """
        
        if not self.disponible:
            print("  Planetary Computer non installé.")
            print("   pip install pystac-client planetary-computer rasterio")
            return None
        
        try:
            import pystac_client
            import planetary_computer
            import rasterio
            from rasterio.windows import from_bounds
            
            print(f" Récupération Planetary Computer pour zone {zone_id}...")
            
            catalog = pystac_client.Client.open(
                self.STAC_URL,
                modifier=planetary_computer.sign_inplace
            )
            
            bbox = [
                longitude - rayon_deg, latitude - rayon_deg,
                longitude + rayon_deg, latitude + rayon_deg
            ]
            
            date_fin   = datetime.now().strftime("%Y-%m-%d")
            date_debut = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            # Recherche Sentinel-2
            search = catalog.search(
                collections=["sentinel-2-l2a"],
                bbox=bbox,
                datetime=f"{date_debut}/{date_fin}",
                query={"eo:cloud_cover": {"lt": 20}},
                max_items=1,
                sortby="-datetime"
            )
            
            items = list(search.items())
            
            if not items:
                print(f"     Pas d'image S2 récente sans nuages pour {zone_id}")
                return self._valeurs_par_defaut(zone_id)
            
            item = items[0]
            
            # Lecture bandes B3 (vert), B4 (rouge), B8 (NIR)
            def lire_bande(bande: str) -> np.ndarray:
                href = item.assets[bande].href
                with rasterio.open(href) as src:
                    window = from_bounds(*bbox, src.transform)
                    return src.read(1, window=window).astype(float)
            
            b3 = lire_bande("B03")  # Vert
            b4 = lire_bande("B04")  # Rouge
            b8 = lire_bande("B08")  # NIR
            
            # Calcul NDWI et NDVI
            eps = 1e-10
            ndwi = np.nanmean((b3 - b8) / (b3 + b8 + eps))
            ndvi = np.nanmean((b8 - b4) / (b8 + b4 + eps))
            
            nuages = item.properties.get("eo:cloud_cover", 15.0)
            
            return DonneesSatellitairesTempsReel(
                zone_id               = zone_id,
                timestamp             = datetime.now(),
                ndwi                  = round(float(ndwi), 4),
                ndvi                  = round(float(ndvi), 4),
                sentinel1_vv          = 0.35,   # S1 non dispo sur Planetary pour Togo
                sentinel1_vh          = 0.20,
                ndwi_anomalie         = 0.0,
                source                = "Planetary Computer",
                couverture_nuages_pct = nuages,
                qualite               = "bonne" if nuages < 10 else "moyenne"
            )
            
        except Exception as e:
            print(f" Erreur Planetary Computer : {e}")
            return self._valeurs_par_defaut(zone_id)
    
    def _valeurs_par_defaut(self, zone_id: str) -> DonneesSatellitairesTempsReel:
        """Valeurs neutres quand aucune image disponible"""
        return DonneesSatellitairesTempsReel(
            zone_id=zone_id, timestamp=datetime.now(),
            ndwi=0.0, ndvi=0.3, sentinel1_vv=0.3, sentinel1_vh=0.2,
            ndwi_anomalie=0.0, source="défaut",
            couverture_nuages_pct=100.0, qualite="faible"
        )


# ─────────────────────────────────────────────
# 📡 MODE SIMULATION (toujours disponible)
# ─────────────────────────────────────────────
def simuler_satellite(
    zone_id: str = "LOM-001",
    scenario: str = "inondation_imminente"
) -> DonneesSatellitairesTempsReel:
    """
    Génère des données satellitaires simulées pour tester KATARA.
    
    Scénarios : "normal", "pre_inondation", "inondation_imminente", "inondation_active"
    """
    
    scenarios = {
        "normal": {
            "ndwi": -0.15, "ndvi": 0.45,
            "vv": 0.20, "vh": 0.12, "anomalie": 0.02,
            "nuages": 15
        },
        "pre_inondation": {
            "ndwi": 0.12, "ndvi": 0.28,
            "vv": 0.38, "vh": 0.22, "anomalie": 0.18,
            "nuages": 45
        },
        "inondation_imminente": {
            "ndwi": 0.38, "ndvi": 0.15,
            "vv": 0.58, "vh": 0.35, "anomalie": 0.42,
            "nuages": 70
        },
        "inondation_active": {
            "ndwi": 0.65, "ndvi": 0.08,
            "vv": 0.82, "vh": 0.61, "anomalie": 0.72,
            "nuages": 85
        }
    }
    
    s = scenarios.get(scenario, scenarios["normal"])
    
    qualite_map = {(0, 30): "bonne", (30, 60): "moyenne", (60, 101): "faible"}
    qualite = next(v for (lo, hi), v in qualite_map.items() if lo <= s["nuages"] < hi)
    
    return DonneesSatellitairesTempsReel(
        zone_id               = zone_id,
        timestamp             = datetime.now(),
        ndwi                  = s["ndwi"],
        ndvi                  = s["ndvi"],
        sentinel1_vv          = s["vv"],
        sentinel1_vh          = s["vh"],
        ndwi_anomalie         = s["anomalie"],
        source                = "Simulation",
        couverture_nuages_pct = s["nuages"],
        qualite               = qualite
    )


# ─────────────────────────────────────────────
# 🔀 COLLECTEUR INTELLIGENT (choisit la source)
# ─────────────────────────────────────────────
class CollecteurSatellitaire:
    """
    Interface unifiée : essaie GEE, puis Planetary Computer, puis simulation.
    Tu n'as qu'à utiliser cette classe, elle gère tout automatiquement.
    """
    
    def __init__(self, projet_gee: str = "katara-flood-prediction"):
        self.gee = CollecteurGEE(projet_gee) if GEE_DISPONIBLE else None
        self.planetary = CollecteurPlanetaryComputer()
    
    def get_indices(
        self,
        zone_id: str,
        latitude: float,
        longitude: float,
        forcer_simulation: bool = False
    ) -> DonneesSatellitairesTempsReel:
        """
        Récupère les données en utilisant la meilleure source disponible.
        """
        
        if forcer_simulation:
            print(f" Mode simulation pour zone {zone_id}")
            return simuler_satellite(zone_id)
        
        # Essai 1 : Google Earth Engine
        if self.gee and self.gee.initialise:
            result = self.gee.get_indices(zone_id, latitude, longitude)
            if result:
                return result
        
        # Essai 2 : Planetary Computer
        if self.planetary.disponible:
            result = self.planetary.get_indices(zone_id, latitude, longitude)
            if result:
                return result
        
        # Fallback : simulation
        print(f"     Utilisation de la simulation pour zone {zone_id}")
        return simuler_satellite(zone_id)
    
    def surveiller_zones(self, zones: list) -> list:
        """Récupère les données satellitaires pour toutes les zones"""
        resultats = []
        for zone in zones:
            data = self.get_indices(
                zone["zone_id"], zone["latitude"], zone["longitude"]
            )
            resultats.append(data)
            self._afficher_resume(data)
            time.sleep(0.3)
        return resultats
    
    def _afficher_resume(self, data: DonneesSatellitairesTempsReel):
        interpretation_ndwi = "💧 Eau présente" if data.ndwi > 0 else "🟫 Sol/végétation"
        interpretation_ndvi = "🌿 Végétation" if data.ndvi > 0.3 else "⚠️  Sol nu/stress"
        
        print(f"\n Zone {data.zone_id} | Source: {data.source}")
        print(f"   NDWI : {data.ndwi:+.3f}   {interpretation_ndwi}")
        print(f"   NDVI : {data.ndvi:+.3f}   {interpretation_ndvi}")
        print(f"   SAR (VV) : {data.sentinel1_vv:.3f}")
        print(f"   Anomalie NDWI : {data.ndwi_anomalie:+.3f}")
        print(f"   Nuages : {data.couverture_nuages_pct:.0f}% | Qualité : {data.qualite}")
        
        if data.ndwi > 0.3 or data.ndwi_anomalie > 0.3:
            print(f"    Signal satellite élevé  risque d'inondation !")


# ─────────────────────────────────────────────
# 🚀 TEST / DÉMONSTRATION
# ─────────────────────────────────────────────
if __name__ == "__main__":
    
    print("=" * 60)
    print("   KATARA - Module Satellitaire | Test")
    print("=" * 60)
    
    # ── TEST 1 : Simulation des 4 scénarios ──
    print("\n TEST 1 : Scénarios simulés")
    print("-" * 45)
    
    collecteur = CollecteurSatellitaire()
    
    for scenario in ["normal", "pre_inondation", "inondation_imminente", "inondation_active"]:
        data = simuler_satellite("LOM-001", scenario)
        print(f"\n Scénario : {scenario.upper()}")
        print(f"   NDWI={data.ndwi:+.2f} | NDVI={data.ndvi:.2f} | SAR={data.sentinel1_vv:.2f}")
        
        risque = "🔴 CRITIQUE" if data.ndwi > 0.5 else \
                 "🟠 MOYEN"   if data.ndwi > 0.2 else \
                 "🟡 FAIBLE"  if data.ndwi > 0   else "🟢 NORMAL"
        print(f"   Risque satellite : {risque}")
    
    # ── TEST 2 : Intégration complète ──
    print("\n\n TEST 2 : Pipeline complet KATARA")
    print("-" * 45)
    print("""
# ═══════════════════════════════════════════
# PIPELINE COMPLET KATARA (3 modules)
# ═══════════════════════════════════════════

from katara_model  import KataraModele, ZoneRisque
from katara_meteo  import CollecteurMeteo, simuler_meteo_lome
from katara_sat    import CollecteurSatellitaire

# 1. Initialiser les collecteurs
meteo_collecteur = CollecteurMeteo("TA_CLE_OWM")
sat_collecteur   = CollecteurSatellitaire("ton-projet-gee")
modele           = KataraModele()

# 2. Définir les zones Maritime
zones = [
    ZoneRisque("LOM-001", "Bè-Kpota", 6.1319, 1.2228,
               altitude_m=8.5, superficie_bassin_km2=42.3,
               type_sol="argileux", capacite_drainage=120,
               population=15000),
]

# 3. Boucle de surveillance (à lancer toutes les heures)
for zone in zones:
    meteo  = meteo_collecteur.get_meteo_complete(zone.zone_id, zone.latitude, zone.longitude)
    sat    = sat_collecteur.get_indices(zone.zone_id, zone.latitude, zone.longitude)
    result = modele.predire(zone, meteo, sat)
    
    if result.alerte_declenchee:
        print(result.message_sms)
        # → envoyer SMS via Africa's Talking (étape suivante !)
""")
    
    # ── TEST 3 : Simulation pipeline ──
    print(" TEST 3 : Simulation pipeline complet")
    print("-" * 45)
    
    from katara_meteo import simuler_meteo_lome
    
    # Import du modèle principal
    import sys
    sys.path.insert(0, '/home/claude')
    
    try:
        from katara_model import KataraModele, ZoneRisque
        
        zone = ZoneRisque(
            zone_id="LOM-001", nom="Bè-Kpota",
            latitude=6.1319, longitude=1.2228,
            altitude_m=8.5, superficie_bassin_km2=42.3,
            type_sol="argileux", capacite_drainage=120.0,
            population=15000, telephones=["+22890000001"]
        )
        
        scenarios_test = [
            ("sec",         "normal"),
            ("pluie_forte", "inondation_imminente"),
            ("orage",       "inondation_active"),
        ]
        
        modele = KataraModele()
        
        for s_meteo, s_sat in scenarios_test:
            meteo = simuler_meteo_lome("LOM-001", s_meteo)
            sat   = simuler_satellite("LOM-001", s_sat)
            
            # Adapter le format pour katara_model
            from katara_model import DonneesSatellitaires
            from datetime import datetime
            
            sat_model = DonneesSatellitaires(
                zone_id="LOM-001", timestamp=datetime.now(),
                ndwi=sat.ndwi, ndvi=sat.ndvi, sentinel1_vv=sat.sentinel1_vv
            )
            
            result = modele.predire(zone, meteo, sat_model)
            
            print(f"\n Météo={s_meteo} + Satellite={s_sat}")
            print(f"    Probabilité : {result.probabilite*100:.0f}%")
            print(f"    Alerte : {result.niveau_alerte.upper()}")
            if result.alerte_declenchee:
                print(f"    {result.message_sms.splitlines()[0]}")
    
    except Exception as e:
        print(f"   (Test d'intégration ignoré : {e})")
    
    print("\n" + "=" * 60)
    print("KATARA  2025 - Ruth | Lomé, Togo")
    print("=" * 60)
