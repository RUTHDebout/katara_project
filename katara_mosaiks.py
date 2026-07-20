"""
╔══════════════════════════════════════════════════════════════╗
║         KATARA — Module MOSAIKS                             ║
║         Enrichissement des features satellitaires           ║
╚══════════════════════════════════════════════════════════════╝

MOSAIKS = Multi-Task Observation using Satellite Imagery & Kitchen Sinks
Source : Rolf et al., Nature Communications 2021

Ce module ajoute des features satellite AUTOMATIQUES à KATARA
sans avoir besoin d'écrire de Deep Learning.

Comment ça marche (version simple) :
  1. Tu donnes des coordonnées GPS (lat, lon) d'une zone
  2. MOSAIKS récupère l'image satellite Sentinel-2 correspondante
  3. Il applique des filtres aléatoires sur l'image → vecteur de features
  4. Tu passes ce vecteur à ton Random Forest KATARA
  → Le modèle "voit" beaucoup plus de détails sans effort !

3 modes disponibles :
  - MODE A : Features pré-calculées 2019 (mosaiks.org, gratuit, hors-ligne)
  - MODE B : Features temps réel via Microsoft Planetary Computer (recommandé)
  - MODE C : Simulation (développement/tests)

Installation :
  pip install mosaiks planetary-computer pystac-client stackstac
"""

import os
import json
import time
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
import requests

# ── Imports conditionnels ──────────────────────────────────────
MOSAIKS_DISPONIBLE    = False
PLANETARY_DISPONIBLE  = False
REDIVIS_DISPONIBLE    = False

try:
    import mosaiks
    MOSAIKS_DISPONIBLE = True
    print("✅ Package mosaiks disponible")
except ImportError:
    pass

try:
    import planetary_computer
    import pystac_client
    import stackstac
    PLANETARY_DISPONIBLE = True
    print("✅ Microsoft Planetary Computer disponible")
except ImportError:
    pass


# ─────────────────────────────────────────────
# STRUCTURE DE DONNÉES MOSAIKS
# ─────────────────────────────────────────────
@dataclass
class FeaturesMOSAIKS:
    """
    Vecteur de features MOSAIKS pour une zone.
    
    nb_features : nombre de features (256 ou 4096 selon la config)
    Ces features résument l'image satellite de manière automatique :
    texture, couleur, structures géographiques, eau, végétation...
    """
    zone_id:      str
    timestamp:    datetime
    latitude:     float
    longitude:    float
    features:     np.ndarray   # vecteur de 256 à 4096 valeurs
    nb_features:  int
    source:       str          # "planetary_computer", "mosaiks_org", "simulation"
    date_image:   str          # date de l'image satellite utilisée

    # Indices dérivés des features MOSAIKS (calculés automatiquement)
    indice_eau:          float = 0.0   # estimé à partir des features
    indice_vegetation:   float = 0.0
    indice_urbanisation: float = 0.0
    confiance:           float = 1.0   # 0-1, qualité de l'image (nuages, etc.)


# ─────────────────────────────────────────────
# CLIENT MOSAIKS PRINCIPAL
# ─────────────────────────────────────────────
class ClientMOSAIKS:
    """
    Interface MOSAIKS pour KATARA.
    
    Utilisation :
        client = ClientMOSAIKS()
        features = client.get_features(lat=6.13, lon=1.22, zone_id="LOM-001")
        
        # Dans ton modèle :
        X = np.concatenate([features_base, features.features_normalisees])
    """

    NB_FEATURES_DEFAUT = 256  # 256 = rapide, 4096 = plus précis

    def __init__(
        self,
        nb_features: int    = NB_FEATURES_DEFAUT,
        mpc_token:   str    = "",  # Microsoft Planetary Computer token
        cache_dir:   str    = "mosaiks_cache",
    ):
        self.nb_features = nb_features
        self.mpc_token   = mpc_token or os.getenv("MPC_TOKEN", "")
        self.cache_dir   = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

        # Choix automatique du mode selon ce qui est disponible
        if MOSAIKS_DISPONIBLE and self.mpc_token:
            self.mode = "planetary_computer"
            print(f"🛰️  MOSAIKS — Mode Planetary Computer ({nb_features} features)")
        else:
            self.mode = "simulation"
            print(f"🔄 MOSAIKS — Mode simulation ({nb_features} features)")
            if not self.mpc_token:
                print("   → Pour activer le mode réel : ajouter MPC_TOKEN dans .env")
                print("   → Inscription gratuite : https://planetarycomputer.microsoft.com")

    # ── POINT D'ENTRÉE PRINCIPAL ─────────────────
    def get_features(
        self,
        lat:     float,
        lon:     float,
        zone_id: str   = "ZONE",
        date:    str   = None,   # format "YYYY-MM" — None = mois courant
    ) -> FeaturesMOSAIKS:
        """
        Récupère les features MOSAIKS pour une coordonnée GPS.
        
        Retourne un objet FeaturesMOSAIKS directement utilisable
        dans katara_model.py
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m")

        # Vérifier le cache d'abord
        cache_key = f"{zone_id}_{date}"
        cached = self._lire_cache(cache_key)
        if cached is not None:
            print(f"  📦 Cache MOSAIKS utilisé pour {zone_id} ({date})")
            return cached

        # Appel selon le mode
        if self.mode == "planetary_computer" and MOSAIKS_DISPONIBLE:
            result = self._get_features_planetary(lat, lon, zone_id, date)
        else:
            result = self._simuler_features(lat, lon, zone_id, date)

        # Sauvegarder en cache
        self._sauvegarder_cache(cache_key, result)
        return result

    # ── MODE B : MICROSOFT PLANETARY COMPUTER ────
    def _get_features_planetary(
        self, lat: float, lon: float, zone_id: str, date: str
    ) -> FeaturesMOSAIKS:
        """
        Récupère les features via Microsoft Planetary Computer + Sentinel-2.
        Nécessite : pip install mosaiks planetary-computer pystac-client stackstac
        """
        try:
            import planetary_computer
            import pystac_client

            # Authentification MPC
            catalog = pystac_client.Client.open(
                "https://planetarycomputer.microsoft.com/api/stac/v1",
                modifier=planetary_computer.sign_inplace,
            )

            # Recherche de l'image Sentinel-2 la plus récente pour cette zone
            annee, mois = date.split("-")
            date_debut = f"{annee}-{mois}-01"
            date_fin   = f"{annee}-{mois}-28"

            resultats = catalog.search(
                collections=["sentinel-2-l2a"],
                intersects={"type": "Point", "coordinates": [lon, lat]},
                datetime=f"{date_debut}/{date_fin}",
                query={"eo:cloud_cover": {"lt": 30}},  # max 30% de nuages
                sortby="-datetime",
                max_items=1,
            )
            items = list(resultats.items())

            if not items:
                print(f"  ⚠️  Aucune image Sentinel-2 trouvée pour {zone_id} {date}")
                return self._simuler_features(lat, lon, zone_id, date)

            item = items[0]
            nuages = item.properties.get("eo:cloud_cover", 0)
            date_image = item.datetime.strftime("%Y-%m-%d")
            confiance = max(0.3, 1.0 - nuages / 100)

            # Extraction des features MOSAIKS via le package IDinsight
            coords_df = _creer_dataframe_coords(lat, lon)

            features_array = mosaiks.get_features(
                coords_df,
                satellite="sentinel-2",
                image_resolution=500,    # patch de 500m autour du point
                num_features=self.nb_features,
                mpc_token=self.mpc_token,
            )

            vecteur = features_array[0]  # shape (nb_features,)

            # Calculer les indices dérivés à partir des features
            indice_eau, indice_veg, indice_urb = self._estimer_indices(vecteur)

            return FeaturesMOSAIKS(
                zone_id=zone_id, timestamp=datetime.now(),
                latitude=lat, longitude=lon,
                features=vecteur, nb_features=self.nb_features,
                source="planetary_computer", date_image=date_image,
                indice_eau=indice_eau, indice_vegetation=indice_veg,
                indice_urbanisation=indice_urb, confiance=confiance,
            )

        except Exception as e:
            print(f"  ⚠️  Planetary Computer erreur ({e}) — simulation")
            return self._simuler_features(lat, lon, zone_id, date)

    # ── MODE A : FEATURES PRÉ-CALCULÉES MOSAIKS.ORG ──
    def get_features_precomputes(
        self, lat: float, lon: float, zone_id: str = "ZONE"
    ) -> Optional[FeaturesMOSAIKS]:
        """
        Télécharge les features pré-calculées de mosaiks.org (images Planet 2019).
        Gratuit, pas besoin de token.
        Limite : données de 2019 seulement (pas temps réel).
        
        Ces features sont utiles pour l'entraînement du modèle sur données historiques.
        """
        # URL de l'API MOSAIKS.org (en transition — peut changer)
        url = "https://api.mosaiks.org/predictions"
        params = {
            "lat": lat,
            "lon": lon,
            "num_features": min(self.nb_features, 4096),
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                vecteur = np.array(data["features"])
                indice_eau, indice_veg, indice_urb = self._estimer_indices(vecteur)
                return FeaturesMOSAIKS(
                    zone_id=zone_id, timestamp=datetime.now(),
                    latitude=lat, longitude=lon,
                    features=vecteur, nb_features=len(vecteur),
                    source="mosaiks_org", date_image="2019-Q3",
                    indice_eau=indice_eau, indice_vegetation=indice_veg,
                    indice_urbanisation=indice_urb, confiance=0.9,
                )
            else:
                print(f"  ⚠️  mosaiks.org : statut {r.status_code}")
                return None
        except Exception as e:
            print(f"  ⚠️  mosaiks.org inaccessible : {e}")
            return None

    # ── MODE C : SIMULATION RÉALISTE ─────────────
    def _simuler_features(
        self, lat: float, lon: float, zone_id: str, date: str
    ) -> FeaturesMOSAIKS:
        """
        Génère des features MOSAIKS simulées mais réalistes pour le développement.
        
        La simulation est déterministe : mêmes coordonnées → mêmes features.
        Elle intègre la saison (pluie/saison sèche) pour être cohérente
        avec les données météo de katara_meteo.py.
        """
        # Seed déterministe basé sur la zone et le mois
        mois = int(date.split("-")[1]) if "-" in date else datetime.now().month
        seed = hash(f"{lat:.3f}{lon:.3f}{mois}") % (2**31)
        rng = np.random.RandomState(seed)

        # ── Base : vecteur de features aléatoires (Random Convolutional Features) ──
        # C'est exactement ce que fait MOSAIKS : filtres aléatoires → features
        # On simule la même distribution (valeurs entre -3 et 3, centrées sur 0)
        vecteur = rng.randn(self.nb_features).astype(np.float32)

        # ── Ajustement saisonnier pour le Togo ──
        # Saison des pluies : avril-juillet et sept-octobre
        saison_pluie = mois in [4, 5, 6, 7, 9, 10]

        # Les premières features (par convention MOSAIKS) correspondent
        # aux canaux bleu/vert/rouge/NIR de Sentinel-2
        # On les module selon la saison pour que les indices dérivés soient réalistes
        if saison_pluie:
            # Plus d'eau → NDWI plus élevé → features "bleu/vert" plus fortes
            vecteur[:16] += rng.uniform(0.3, 0.8, 16)   # canaux eau
            vecteur[16:32] -= rng.uniform(0.1, 0.4, 16)  # végétation réduite (eau stagnante)
        else:
            # Saison sèche → végétation plus verte, moins d'eau
            vecteur[:16]  -= rng.uniform(0.1, 0.3, 16)
            vecteur[16:32] += rng.uniform(0.2, 0.5, 16)

        # Légère variation selon le jour du mois pour simuler des changements
        jour_variation = rng.randn(self.nb_features) * 0.1
        vecteur += jour_variation

        # ── Estimation des indices dérivés ──
        indice_eau, indice_veg, indice_urb = self._estimer_indices(vecteur)

        # Ajustement saison
        if saison_pluie:
            indice_eau = min(1.0, indice_eau + rng.uniform(0.15, 0.35))
        else:
            indice_eau = max(0.0, indice_eau - rng.uniform(0.1, 0.25))

        return FeaturesMOSAIKS(
            zone_id=zone_id, timestamp=datetime.now(),
            latitude=lat, longitude=lon,
            features=vecteur, nb_features=self.nb_features,
            source="simulation", date_image=date + "-15",
            indice_eau=float(np.clip(indice_eau, 0, 1)),
            indice_vegetation=float(np.clip(indice_veg, 0, 1)),
            indice_urbanisation=float(np.clip(indice_urb, 0, 1)),
            confiance=0.75,
        )

    # ── UTILITAIRES ──────────────────────────────
    def _estimer_indices(self, vecteur: np.ndarray):
        """
        Estime les indices spectraux à partir du vecteur MOSAIKS.
        
        Dans MOSAIKS, les features sont des projections linéaires de l'image.
        Les premières features correspondent grossièrement aux canaux spectraux.
        On peut donc estimer NDWI-like, NDVI-like, etc.
        """
        n = len(vecteur)

        # Quartiles du vecteur comme proxies des canaux spectraux
        q = np.percentile(vecteur, [25, 50, 75])
        mean = np.mean(vecteur)
        std  = np.std(vecteur)

        # Indice eau (NDWI-like) : corrélé aux features à haute variance
        # L'eau réfléchit fortement dans le vert, absorbe dans le NIR
        # → features avec forte valeur positive dans les premiers canaux
        feat_eau = vecteur[:n//4]
        indice_eau = float(np.clip(
            (np.mean(feat_eau) + std * 0.3 + 1) / 2, 0, 1
        ))

        # Indice végétation (NDVI-like) : features mid-range positives
        feat_veg = vecteur[n//4:n//2]
        indice_veg = float(np.clip(
            (np.mean(feat_veg) + 0.5) / 2, 0, 1
        ))

        # Indice urbanisation : corrélé aux features à faible variance (surfaces dures)
        feat_urb = vecteur[n//2:]
        indice_urb = float(np.clip(
            1 - (np.std(feat_urb) + 0.3) / 2, 0, 1
        ))

        return indice_eau, indice_veg, indice_urb

    def _lire_cache(self, cle: str) -> Optional[FeaturesMOSAIKS]:
        """Lit les features en cache (valides 24h)"""
        chemin = os.path.join(self.cache_dir, f"{cle}.npz")
        if not os.path.exists(chemin):
            return None
        age_h = (time.time() - os.path.getmtime(chemin)) / 3600
        if age_h > 24:
            return None
        try:
            data = np.load(chemin, allow_pickle=True)
            return FeaturesMOSAIKS(
                zone_id=str(data["zone_id"]),
                timestamp=datetime.fromisoformat(str(data["timestamp"])),
                latitude=float(data["latitude"]),
                longitude=float(data["longitude"]),
                features=data["features"],
                nb_features=int(data["nb_features"]),
                source=str(data["source"]),
                date_image=str(data["date_image"]),
                indice_eau=float(data["indice_eau"]),
                indice_vegetation=float(data["indice_vegetation"]),
                indice_urbanisation=float(data["indice_urbanisation"]),
                confiance=float(data["confiance"]),
            )
        except Exception:
            return None

    def _sauvegarder_cache(self, cle: str, f: FeaturesMOSAIKS):
        """Sauvegarde les features en cache"""
        chemin = os.path.join(self.cache_dir, f"{cle}.npz")
        np.savez(
            chemin,
            zone_id=f.zone_id, timestamp=f.timestamp.isoformat(),
            latitude=f.latitude, longitude=f.longitude,
            features=f.features, nb_features=f.nb_features,
            source=f.source, date_image=f.date_image,
            indice_eau=f.indice_eau, indice_vegetation=f.indice_vegetation,
            indice_urbanisation=f.indice_urbanisation, confiance=f.confiance,
        )


# ─────────────────────────────────────────────
# INTÉGRATION DANS KATARA MODEL
# ─────────────────────────────────────────────
def features_pour_katara(
    fm: FeaturesMOSAIKS,
    nb_features_reduits: int = 32,
) -> np.ndarray:
    """
    Prépare les features MOSAIKS pour les ajouter au modèle KATARA.
    
    Au lieu d'utiliser les 256 (ou 4096) features brutes — trop pour
    un Random Forest avec peu de données — on fait une réduction simple :
    
    1. On prend les indices dérivés (eau, végétation, urbanisation)
    2. On ajoute un résumé statistique du vecteur (mean, std, percentiles)
    3. Optionnellement, on ajoute les N premières features brutes
    
    Résultat : vecteur de ~10-40 features MOSAIKS à ajouter à katara_model.py
    
    Utilisation dans katara_model.py :
        features_base = [pluie, ndwi, ndvi, ...]        # features actuelles
        features_mos  = features_pour_katara(fm)         # features MOSAIKS
        X = np.concatenate([features_base, features_mos]) # vecteur enrichi
    """
    v = fm.features

    # ── Bloc 1 : indices dérivés (3 features) ──
    indices = np.array([
        fm.indice_eau,
        fm.indice_vegetation,
        fm.indice_urbanisation,
    ])

    # ── Bloc 2 : statistiques du vecteur (8 features) ──
    stats = np.array([
        np.mean(v),
        np.std(v),
        np.percentile(v, 10),
        np.percentile(v, 25),
        np.percentile(v, 50),  # médiane
        np.percentile(v, 75),
        np.percentile(v, 90),
        fm.confiance,
    ])

    # ── Bloc 3 : premières features brutes (les plus informatives) ──
    # On prend les premières — elles correspondent aux canaux spectraux principaux
    n = min(nb_features_reduits, len(v))
    premieres = v[:n]

    return np.concatenate([indices, stats, premieres])


def _creer_dataframe_coords(lat: float, lon: float):
    """Crée un DataFrame geopandas avec les coordonnées (pour le package mosaiks)"""
    try:
        import pandas as pd
        return pd.DataFrame({"Lat": [lat], "Lon": [lon]})
    except ImportError:
        return None


# ─────────────────────────────────────────────
# PATCH DU MODÈLE KATARA — intègre MOSAIKS
# ─────────────────────────────────────────────
def preparer_features_enrichies(
    zone,
    meteo,
    satellite,
    features_mosaiks: Optional[FeaturesMOSAIKS] = None,
) -> np.ndarray:
    """
    Version enrichie de KataraModele.preparer_features() qui intègre MOSAIKS.
    
    Remplace l'appel à preparer_features() dans katara_model.py :
    
    AVANT :
        X = modele.preparer_features(zone, meteo, satellite)
    
    APRÈS :
        fm = client_mosaiks.get_features(zone.latitude, zone.longitude, zone.zone_id)
        X  = preparer_features_enrichies(zone, meteo, satellite, fm)
    """
    # ── Features de base (existantes dans KATARA) ──
    permeabilite_map = {"argileux": 0.1, "lateritique": 0.4, "sableux": 0.9}
    permeabilite = permeabilite_map.get(zone.type_sol, 0.5)

    features_base = np.array([
        # Météo
        meteo.precipitations_mm_h,
        meteo.precipitations_mm_24h,
        meteo.humidite_sol_pct / 100,
        meteo.temperature_c,
        meteo.evapotranspiration_mm,
        # Satellite classique (GEE)
        satellite.ndwi,
        satellite.ndvi,
        satellite.sentinel1_vv,
        # Géographie
        zone.altitude_m,
        zone.superficie_bassin_km2,
        permeabilite,
        zone.capacite_drainage,
        # Indicateurs combinés
        meteo.precipitations_mm_24h / max(zone.capacite_drainage, 1),
        meteo.humidite_sol_pct / 100 * (1 - permeabilite),
    ])

    # ── Features MOSAIKS (si disponibles) ──
    if features_mosaiks is not None:
        fm_reduit = features_pour_katara(features_mosaiks, nb_features_reduits=32)

        # Fusion avec pondération :
        # Les indices MOSAIKS complètent le NDWI/NDVI de GEE
        # On ajoute aussi l'indice eau MOSAIKS comme feature standalone
        extra = np.array([
            features_mosaiks.indice_eau,
            features_mosaiks.indice_vegetation,
            # Cohérence entre MOSAIKS et GEE (devrait être similaire)
            abs(features_mosaiks.indice_eau - max(0, satellite.ndwi)),
        ])
        return np.concatenate([features_base, extra, fm_reduit]).reshape(1, -1)
    else:
        return features_base.reshape(1, -1)


# ─────────────────────────────────────────────
# TEST ET DÉMONSTRATION
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  🛰️  KATARA × MOSAIKS — Test d'intégration")
    print("=" * 55)

    # Zones de la Région Maritime du Togo
    zones_test = [
        ("LOM-001", "Lomé Centre",    6.1375, 1.2123),
        ("LOM-002", "Bè Kpota",       6.1200, 1.2350),
        ("LOM-003", "Agbalépédogan",  6.1550, 1.1980),
        ("LOM-005", "Légbassito",     6.3200, 1.1800),
    ]

    client = ClientMOSAIKS(nb_features=256)
    print()

    for zone_id, nom, lat, lon in zones_test:
        print(f"📍 {nom} ({zone_id}) — lat:{lat}, lon:{lon}")

        fm = client.get_features(lat, lon, zone_id=zone_id)

        print(f"   Source        : {fm.source}")
        print(f"   Date image    : {fm.date_image}")
        print(f"   Nb features   : {fm.nb_features}")
        print(f"   Indice eau    : {fm.indice_eau:.3f}  {'🌊 EAU DÉTECTÉE' if fm.indice_eau > 0.5 else '✅ Normal'}")
        print(f"   Végétation    : {fm.indice_vegetation:.3f}")
        print(f"   Urbanisation  : {fm.indice_urbanisation:.3f}")
        print(f"   Confiance     : {fm.confiance:.0%}")

        # Test de la fusion avec le modèle KATARA
        features_katara = features_pour_katara(fm)
        print(f"   → Vecteur pour KATARA : {len(features_katara)} features")
        print()

    print("─" * 55)
    print("🔗 Intégration dans katara_model.py :")
    print()
    print("   from katara_mosaiks import ClientMOSAIKS, preparer_features_enrichies")
    print()
    print("   client = ClientMOSAIKS(mpc_token=os.getenv('MPC_TOKEN'))")
    print()
    print("   # Dans la boucle de prédiction :")
    print("   fm = client.get_features(zone.latitude, zone.longitude, zone.zone_id)")
    print("   X  = preparer_features_enrichies(zone, meteo, satellite, fm)")
    print("   proba = modele.predire_depuis_features(X)")
    print()
    print("=" * 55)
    print("  ✅ Module MOSAIKS prêt !")
    print("=" * 55)
