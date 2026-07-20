"""
╔══════════════════════════════════════════════════════════════╗
║          KATARA - Modèle de Prédiction d'Inondations        ║
║          Région Maritime du Togo | by Ruth / KATARA         ║
╚══════════════════════════════════════════════════════════════╝

Ce modèle combine :
- Données météo en temps réel
- Données satellitaires (NDWI, NDVI, Sentinel-1)
- Données géographiques locales
- Historique des inondations

Pour produire :
- Probabilité d'inondation (0 à 1)
- Niveau d'alerte (faible / moyen / critique)
- Délai estimé avant inondation (heures)
- Déclenchement automatique d'alertes SMS
"""

# ─────────────────────────────────────────────
# 📦 IMPORTS
# ─────────────────────────────────────────────
import pandas as pd
import numpy as np
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
import json
import os

# Pour le modèle ML (installe avec : pip install scikit-learn)
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib  # pour sauvegarder/charger le modèle


# ─────────────────────────────────────────────
# 📍 STRUCTURE D'UNE ZONE À RISQUE
# ─────────────────────────────────────────────
@dataclass
class ZoneRisque:
    """Représente une zone géographique surveillée par KATARA"""
    
    zone_id: str                    # ex: "LOM-001"
    nom: str                        # ex: "Bè-Kpota"
    latitude: float
    longitude: float
    altitude_m: float               # en mètres
    superficie_bassin_km2: float    # superficie du bassin versant
    type_sol: str                   # "argileux", "sableux", "lateritique"
    capacite_drainage: float        # capacité des canaux (m³/h)
    population: int                 # nombre d'habitants
    infrastructures: list = field(default_factory=list)  # routes, hôpitaux...
    telephones: list = field(default_factory=list)       # numéros SMS de la zone


# ─────────────────────────────────────────────
# 🌦️ DONNÉES MÉTÉO EN TEMPS RÉEL
# ─────────────────────────────────────────────
@dataclass
class DonneesMeteo:
    """Données météo collectées pour une zone et un instant donnés"""
    
    zone_id: str
    timestamp: datetime
    precipitations_mm_h: float      # pluie en mm par heure
    precipitations_mm_24h: float    # pluie cumulée sur 24h
    humidite_sol_pct: float         # humidité du sol en %
    temperature_c: float
    evapotranspiration_mm: float    # eau qui repart dans l'air


# ─────────────────────────────────────────────
# 🛰️ DONNÉES SATELLITAIRES (Google Earth Engine)
# ─────────────────────────────────────────────
@dataclass
class DonneesSatellitaires:
    """Indices satellitaires extraits de GEE"""
    
    zone_id: str
    timestamp: datetime
    ndwi: float     # Indice d'eau : >0 = présence d'eau (Sentinel-2)
    ndvi: float     # Indice de végétation : faible = sol nu = risque élevé
    sentinel1_vv: float  # Radar Sentinel-1 : détecte eau même sous nuages
    landsat_historique: Optional[float] = None  # Comparaison historique


# ─────────────────────────────────────────────
# 🚨 RÉSULTAT DE PRÉDICTION
# ─────────────────────────────────────────────
@dataclass
class ResultatPrediction:
    """Résultat produit par le modèle pour une zone"""
    
    zone_id: str
    timestamp: datetime
    probabilite: float              # entre 0 et 1
    niveau_alerte: str              # "faible", "moyen", "critique"
    delai_heures: Optional[float]   # délai estimé avant inondation
    alerte_declenchee: bool
    message_sms: str


# ─────────────────────────────────────────────
# 🧠 MOTEUR DE PRÉDICTION KATARA
# ─────────────────────────────────────────────
class KataraModele:
    """
    Cerveau de KATARA.
    Combine toutes les données et prédit le risque d'inondation.
    """
    
    # Seuils de déclenchement des alertes
    SEUIL_FAIBLE    = 0.30   # 30% de probabilité
    SEUIL_MOYEN     = 0.55   # 55% de probabilité
    SEUIL_CRITIQUE  = 0.75   # 75% de probabilité
    
    # Seuil météo de base (mm en 24h)
    SEUIL_PLUIE_24H = 50.0   # >50mm en 24h = alerte déclenchée
    
    def __init__(self, auto_train: bool = True):
        self.modele_ml = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.est_entraine = False
        if auto_train:
            self.auto_entrainer()
    
    # ── PRÉPARATION DES FEATURES ──────────────────
    def preparer_features(
        self,
        zone: ZoneRisque,
        meteo: DonneesMeteo,
        satellite: DonneesSatellitaires
    ) -> np.ndarray:
        """
        Assemble toutes les variables en un vecteur pour le modèle.
        C'est ici que les données brutes deviennent de l'IA !
        """
        
        # Perméabilité du sol (plus c'est bas, plus l'eau stagne)
        permeabilite_map = {
            "argileux": 0.1,
            "lateritique": 0.4,
            "sableux": 0.9
        }
        permeabilite = permeabilite_map.get(zone.type_sol, 0.5)
        
        features = [
            # --- Météo ---
            meteo.precipitations_mm_h,
            meteo.precipitations_mm_24h,
            meteo.humidite_sol_pct / 100,        # normalisation 0-1
            meteo.temperature_c,
            meteo.evapotranspiration_mm,
            
            # --- Satellite ---
            satellite.ndwi,                       # >0 = eau présente
            satellite.ndvi,                       # faible = risque
            satellite.sentinel1_vv,               # radar eau
            
            # --- Géographie ---
            zone.altitude_m,
            zone.superficie_bassin_km2,
            permeabilite,
            zone.capacite_drainage,
            
            # --- Indicateur combiné ---
            meteo.precipitations_mm_24h / max(zone.capacite_drainage, 1),  # pluie vs drainage
            meteo.humidite_sol_pct / 100 * (1 - permeabilite),             # saturation sol
        ]
        
        return np.array(features).reshape(1, -1)
    
    # ── ENTRAÎNEMENT DU MODÈLE ────────────────────
    def entrainer(self, df_historique: pd.DataFrame):
        """
        Entraîne le modèle sur l'historique des inondations.
        
        df_historique doit contenir :
        - toutes les features (colonnes)
        - une colonne 'inondation' (0 ou 1)
        """
        
        colonnes_features = [
            'precipitations_mm_h', 'precipitations_mm_24h',
            'humidite_sol_pct', 'temperature_c', 'evapotranspiration_mm',
            'ndwi', 'ndvi', 'sentinel1_vv',
            'altitude_m', 'superficie_bassin_km2', 'permeabilite',
            'capacite_drainage', 'ratio_pluie_drainage', 'saturation_sol'
        ]
        
        X = df_historique[colonnes_features]
        y = df_historique['inondation']
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Normalisation
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled  = self.scaler.transform(X_test)
        
        # Entraînement
        self.modele_ml.fit(X_train_scaled, y_train)
        self.est_entraine = True
        
        # Évaluation
        y_pred = self.modele_ml.predict(X_test_scaled)
        print(" Performance du modèle KATARA :")
        print(classification_report(y_test, y_pred,
              target_names=["Pas d'inondation", "Inondation"]))
        
        return self
    
    # ── PRÉDICTION ────────────────────────────────
    def predire(
        self,
        zone: ZoneRisque,
        meteo: DonneesMeteo,
        satellite: DonneesSatellitaires
    ) -> ResultatPrediction:
        """
        Prédit le risque d'inondation pour une zone.
        Retourne un ResultatPrediction avec le niveau d'alerte.
        """
        
        features = self.preparer_features(zone, meteo, satellite)
        
        # Calcul de la probabilité
        if self.est_entraine:
            features_scaled = self.scaler.transform(features)
            probabilite = self.modele_ml.predict_proba(features_scaled)[0][1]
        else:
            # Modèle de règles simples si pas encore entraîné
            probabilite = self._regles_simples(meteo, satellite)
        
        # Détermination du niveau d'alerte
        if probabilite >= self.SEUIL_CRITIQUE:
            niveau = "critique"
            delai_heures = self._estimer_delai(meteo, probabilite)
            alerte = True
        elif probabilite >= self.SEUIL_MOYEN:
            niveau = "moyen"
            delai_heures = self._estimer_delai(meteo, probabilite)
            alerte = True
        elif probabilite >= self.SEUIL_FAIBLE:
            niveau = "faible"
            delai_heures = None
            alerte = False
        else:
            niveau = "faible"
            delai_heures = None
            alerte = False
        
        # Vérification seuil pluie (règle de sécurité absolue)
        if meteo.precipitations_mm_24h >= self.SEUIL_PLUIE_24H:
            alerte = True
            if niveau == "faible":
                niveau = "moyen"
        
        # Construction du SMS
        message = self._construire_sms(zone, niveau, probabilite, delai_heures)
        
        return ResultatPrediction(
            zone_id=zone.zone_id,
            timestamp=datetime.now(),
            probabilite=round(probabilite, 3),
            niveau_alerte=niveau,
            delai_heures=delai_heures,
            alerte_declenchee=alerte,
            message_sms=message
        )
    
    # ── RÈGLES SIMPLES (fallback sans ML) ─────────
    def _regles_simples(self, meteo: DonneesMeteo, satellite: DonneesSatellitaires) -> float:
        """Score de risque basé sur des règles expertes"""
        score = 0.0
        
        # Pluie
        if meteo.precipitations_mm_24h > 100: score += 0.40
        elif meteo.precipitations_mm_24h > 50:  score += 0.25
        elif meteo.precipitations_mm_24h > 20:  score += 0.10
        
        # Humidité du sol
        if meteo.humidite_sol_pct > 80: score += 0.20
        elif meteo.humidite_sol_pct > 60: score += 0.10
        
        # Satellite
        if satellite.ndwi > 0.3:    score += 0.20
        if satellite.sentinel1_vv > 0.5: score += 0.15
        if satellite.ndvi < 0.2:    score += 0.05
        
        return min(score, 1.0)
    
    # ── ESTIMATION DU DÉLAI ───────────────────────
    def _estimer_delai(self, meteo: DonneesMeteo, probabilite: float) -> float:
        """Estime le délai en heures avant inondation"""
        if probabilite >= 0.9:
            return 1.0
        elif probabilite >= 0.75:
            return max(1.0, 6.0 - meteo.precipitations_mm_h * 0.5)
        else:
            return max(3.0, 12.0 - meteo.precipitations_mm_h * 0.8)
    
    # ── CONSTRUCTION DU MESSAGE SMS ───────────────
    def _construire_sms(
        self, zone: ZoneRisque, niveau: str, prob: float, delai: Optional[float]
    ) -> str:
        """Génère le message SMS d'alerte"""
        
        emoji_map = {"faible": "🟡", "moyen": "🟠", "critique": "🔴"}
        emoji = emoji_map.get(niveau, "⚠️")
        
        delai_texte = f" dans ~{delai:.0f}h" if delai else ""
        
        return (
            f"{emoji} ALERTE KATARA - {zone.nom}\n"
            f"Risque inondation : {niveau.upper()}{delai_texte}\n"
            f"Probabilité : {prob*100:.0f}%\n"
            f"Evacuez les zones basses. Plus d'infos : katara.tg"
        )
    

    # ── GÉNÉRATION DE DONNÉES SYNTHÉTIQUES ───────
    def _generer_donnees_entrainement(self, n_samples: int = 2000) -> pd.DataFrame:
        """
        Génère des données synthétiques pour bootstrapper le modèle RF.
        Basé sur les plages de valeurs réalistes de Lomé, Togo.
        Remplace par un vrai historique dès que disponible.
        """
        np.random.seed(42)
        permeabilite_map = {"argileux": 0.1, "lateritique": 0.4, "sableux": 0.9}
        types_sol = list(permeabilite_map.keys())
        rows = []

        for _ in range(n_samples):
            pluie_h   = float(np.random.exponential(5))
            pluie_24h = pluie_h * float(np.random.uniform(6, 24))
            humidite  = float(np.random.uniform(40, 100))
            temp      = float(np.random.uniform(22, 35))
            eto       = max(0.0, (0.0023 * (temp + 17.8) * 5.0) * (1 - humidite / 100))

            ndwi        = float(np.random.uniform(-0.4, 0.7))
            ndvi        = float(np.random.uniform(0.0,  0.6))
            sentinel_vv = float(np.random.uniform(0.1,  0.9))

            altitude   = float(np.random.uniform(2,  20))
            superficie = float(np.random.uniform(15, 80))
            sol        = np.random.choice(types_sol)
            permeab    = permeabilite_map[sol]
            drainage   = float(np.random.uniform(80, 250))

            ratio_pluie = pluie_24h / max(drainage, 1)
            saturation  = humidite / 100 * (1 - permeab)

            # Score expert (même logique que _regles_simples)
            score = 0.0
            if pluie_24h > 100: score += 0.40
            elif pluie_24h > 50: score += 0.25
            elif pluie_24h > 20: score += 0.10
            if humidite > 80: score += 0.20
            elif humidite > 60: score += 0.10
            if ndwi > 0.3:        score += 0.20
            if sentinel_vv > 0.5: score += 0.15
            if ndvi < 0.2:        score += 0.05
            if altitude < 5:      score += 0.10
            score = min(score, 1.0)

            label = 1 if score >= 0.55 else 0
            # 10 % de bruit pour éviter surapprentissage
            if np.random.random() < 0.10:
                label = 1 - label

            rows.append([
                pluie_h, pluie_24h, humidite / 100, temp, eto,
                ndwi, ndvi, sentinel_vv,
                altitude, superficie, permeab, drainage,
                ratio_pluie, saturation, label
            ])

        colonnes = [
            'precipitations_mm_h', 'precipitations_mm_24h',
            'humidite_sol_pct', 'temperature_c', 'evapotranspiration_mm',
            'ndwi', 'ndvi', 'sentinel1_vv',
            'altitude_m', 'superficie_bassin_km2', 'permeabilite',
            'capacite_drainage', 'ratio_pluie_drainage', 'saturation_sol',
            'inondation'
        ]
        return pd.DataFrame(rows, columns=colonnes)

    MODEL_CACHE = "katara_modele.pkl"

    def auto_entrainer(self):
        """Charge le modele s'il existe, sinon entraine et sauvegarde."""
        import os
        if os.path.exists(self.MODEL_CACHE):
            print(f"[KATARA v6] Chargement modele cache : {self.MODEL_CACHE}")
            self.charger(self.MODEL_CACHE)
        else:
            print("[KATARA v6] Auto-entrainement du modele RandomForest...")
            df = self._generer_donnees_entrainement(2000)
            self.entrainer(df)
            self.sauvegarder(self.MODEL_CACHE)
            print("[OK] Modele operationnel et sauvegarde.")
        return self

    # ── SAUVEGARDE / CHARGEMENT ───────────────────
    def sauvegarder(self, chemin: str = "katara_modele.pkl"):
        """Sauvegarde le modèle entraîné"""
        joblib.dump({'modele': self.modele_ml, 'scaler': self.scaler}, chemin)
        print(f" Modèle sauvegardé : {chemin}")
    
    def charger(self, chemin: str = "katara_modele.pkl"):
        """Charge un modèle déjà entraîné"""
        data = joblib.load(chemin)
        self.modele_ml = data['modele']
        self.scaler    = data['scaler']
        self.est_entraine = True
        print(f" Modèle chargé : {chemin}")
        return self


# ─────────────────────────────────────────────
# 🚀 EXEMPLE D'UTILISATION
# ─────────────────────────────────────────────
if __name__ == "__main__":
    
    print("=" * 60)
    print("       KATARA - Test du Modèle de Prédiction")
    print("=" * 60)
    
    # 1. Définir une zone à risque (Bè-Kpota, Lomé)
    zone_be = ZoneRisque(
        zone_id        = "LOM-001",
        nom            = "Bè-Kpota",
        latitude       = 6.1319,
        longitude      = 1.2228,
        altitude_m     = 8.5,
        superficie_bassin_km2 = 42.3,
        type_sol       = "argileux",
        capacite_drainage = 120.0,
        population     = 15000,
        infrastructures = ["marché central", "école primaire", "route nationale"],
        telephones     = ["+22890000001", "+22890000002", "+22890000003"]
    )
    
    # 2. Données météo actuelles (simule une pluie forte)
    meteo_actuelle = DonneesMeteo(
        zone_id              = "LOM-001",
        timestamp            = datetime.now(),
        precipitations_mm_h  = 18.5,   # forte pluie
        precipitations_mm_24h = 67.0,  # dépasse le seuil de 50mm
        humidite_sol_pct     = 82.0,   # sol quasi-saturé
        temperature_c        = 28.5,
        evapotranspiration_mm = 4.2
    )
    
    # 3. Données satellitaires
    satellite_actuel = DonneesSatellitaires(
        zone_id       = "LOM-001",
        timestamp     = datetime.now(),
        ndwi          = 0.42,    # eau présente (>0)
        ndvi          = 0.18,    # végétation faible
        sentinel1_vv  = 0.61,   # signal radar élevé = eau
        landsat_historique = 0.35
    )
    
    # 4. Lancer la prédiction
    modele = KataraModele()
    resultat = modele.predire(zone_be, meteo_actuelle, satellite_actuel)
    
    # 5. Afficher les résultats
    print(f"\n Zone analysée : {zone_be.nom} ({zone_be.zone_id})")
    print(f" Timestamp     : {resultat.timestamp.strftime('%Y-%m-%d %H:%M')}")
    print(f" Probabilité   : {resultat.probabilite * 100:.1f}%")
    print(f" Niveau alerte : {resultat.niveau_alerte.upper()}")
    
    if resultat.delai_heures:
        print(f"  Délai estimé  : ~{resultat.delai_heures:.0f} heure(s)")
    
    print(f"\n MESSAGE SMS :")
    print("-" * 40)
    print(resultat.message_sms)
    print("-" * 40)
    
    if resultat.alerte_declenchee:
        print(f"\n Alerte déclenchée pour {len(zone_be.telephones)} numéros")
        print("    Intégrer ici l'envoi via Africa's Talking API")
    else:
        print("\n  Pas d'alerte nécessaire pour le moment")
    
    print("\n" + "=" * 60)
    print("KATARA  2025 - Ruth | Lomé, Togo")
    print("=" * 60)
