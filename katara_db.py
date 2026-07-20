"""
╔══════════════════════════════════════════════════════════════╗
║         KATARA - Base de Données SQLite                     ║
║         Stocke toutes les prédictions et alertes            ║
╚══════════════════════════════════════════════════════════════╝
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional
import os

DB_PATH = os.getenv("KATARA_DB", "katara.db")


class DatabaseKATARA:
    """
    Gère la base de données SQLite de KATARA.
    Stocke : prédictions, données météo, données satellite, alertes SMS.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._creer_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # accès par nom de colonne
        return conn

    # ── CRÉATION DES TABLES ───────────────────────
    def _creer_tables(self):
        """Crée les tables si elles n'existent pas"""
        with self._connect() as conn:
            conn.executescript("""
                -- Prédictions
                CREATE TABLE IF NOT EXISTS predictions (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    zone_id         TEXT NOT NULL,
                    timestamp       TEXT NOT NULL,
                    probabilite     REAL NOT NULL,
                    niveau_alerte   TEXT NOT NULL,
                    delai_heures    REAL,
                    alerte_declenchee INTEGER NOT NULL DEFAULT 0,
                    message_sms     TEXT
                );

                -- Données météo
                CREATE TABLE IF NOT EXISTS meteo (
                    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                    zone_id               TEXT NOT NULL,
                    timestamp             TEXT NOT NULL,
                    precipitations_mm_h   REAL,
                    precipitations_mm_24h REAL,
                    humidite_sol_pct      REAL,
                    temperature_c         REAL,
                    evapotranspiration_mm REAL,
                    description           TEXT,
                    vitesse_vent_ms       REAL,
                    pression_hpa          REAL
                );

                -- Données satellitaires
                CREATE TABLE IF NOT EXISTS satellite (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    zone_id      TEXT NOT NULL,
                    timestamp    TEXT NOT NULL,
                    ndwi         REAL,
                    ndvi         REAL,
                    sentinel1_vv REAL
                );

                -- Alertes SMS envoyées
                CREATE TABLE IF NOT EXISTS alertes_sms (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    zone_id        TEXT NOT NULL,
                    timestamp      TEXT NOT NULL,
                    niveau_alerte  TEXT NOT NULL,
                    nb_envoyes     INTEGER DEFAULT 0,
                    nb_echecs      INTEGER DEFAULT 0,
                    cout_fcfa      REAL DEFAULT 0,
                    message        TEXT
                );

                -- Zones
                CREATE TABLE IF NOT EXISTS zones (
                    zone_id               TEXT PRIMARY KEY,
                    nom                   TEXT NOT NULL,
                    latitude              REAL,
                    longitude             REAL,
                    altitude_m            REAL,
                    superficie_bassin_km2 REAL,
                    type_sol              TEXT,
                    capacite_drainage     REAL,
                    population            INTEGER,
                    telephones            TEXT,  -- JSON array
                    actif                 INTEGER DEFAULT 1,
                    created_at            TEXT
                );

                -- Index pour performances
                CREATE INDEX IF NOT EXISTS idx_pred_zone ON predictions(zone_id);
                CREATE INDEX IF NOT EXISTS idx_pred_ts   ON predictions(timestamp);
                CREATE INDEX IF NOT EXISTS idx_meteo_zone ON meteo(zone_id);
            """)
        print(f" Base de données KATARA initialisée : {self.db_path}")

    # ── SAUVEGARDES ──────────────────────────────
    def sauvegarder_prediction(self, resultat, meteo, satellite):
        """Sauvegarde une prédiction complète"""
        with self._connect() as conn:
            # Prédiction
            conn.execute("""
                INSERT INTO predictions
                    (zone_id, timestamp, probabilite, niveau_alerte,
                     delai_heures, alerte_declenchee, message_sms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                resultat.zone_id,
                resultat.timestamp.isoformat(),
                resultat.probabilite,
                resultat.niveau_alerte,
                resultat.delai_heures,
                int(resultat.alerte_declenchee),
                resultat.message_sms,
            ))

            # Météo
            conn.execute("""
                INSERT INTO meteo
                    (zone_id, timestamp, precipitations_mm_h, precipitations_mm_24h,
                     humidite_sol_pct, temperature_c, evapotranspiration_mm,
                     description, vitesse_vent_ms, pression_hpa)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                meteo.zone_id,
                meteo.timestamp.isoformat(),
                meteo.precipitations_mm_h,
                meteo.precipitations_mm_24h,
                meteo.humidite_sol_pct,
                meteo.temperature_c,
                meteo.evapotranspiration_mm,
                meteo.description,
                getattr(meteo, 'vitesse_vent_ms', None),
                getattr(meteo, 'pression_hpa', None),
            ))

            # Satellite
            conn.execute("""
                INSERT INTO satellite (zone_id, timestamp, ndwi, ndvi, sentinel1_vv)
                VALUES (?, ?, ?, ?, ?)
            """, (
                satellite.zone_id,
                satellite.timestamp.isoformat(),
                satellite.ndwi,
                satellite.ndvi,
                satellite.sentinel1_vv,
            ))

    def sauvegarder_alerte_sms(self, rapport):
        """Sauvegarde un rapport d'envoi SMS"""
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO alertes_sms
                    (zone_id, timestamp, niveau_alerte, nb_envoyes, nb_echecs, cout_fcfa)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                rapport.zone_id,
                rapport.timestamp.isoformat(),
                rapport.niveau_alerte,
                rapport.total_envoyes,
                rapport.total_echecs,
                rapport.cout_total_fcfa,
            ))

    def sauvegarder_zone(self, zone):
        """Insère ou met à jour une zone"""
        with self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO zones
                    (zone_id, nom, latitude, longitude, altitude_m,
                     superficie_bassin_km2, type_sol, capacite_drainage,
                     population, telephones, actif, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """, (
                zone.zone_id, zone.nom, zone.latitude, zone.longitude,
                zone.altitude_m, zone.superficie_bassin_km2, zone.type_sol,
                zone.capacite_drainage, zone.population,
                json.dumps(zone.telephones),
                datetime.now().isoformat(),
            ))

    # ── LECTURES ──────────────────────────────────
    def get_historique(self, zone_id: str, limite: int = 24) -> List[dict]:
        """Récupère l'historique des prédictions pour une zone"""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT p.timestamp, p.probabilite, p.niveau_alerte,
                       p.delai_heures, p.alerte_declenchee,
                       m.precipitations_mm_24h, m.humidite_sol_pct,
                       s.ndwi, s.sentinel1_vv
                FROM predictions p
                LEFT JOIN (
                    SELECT zone_id, DATE(timestamp) AS jour,
                           MAX(timestamp) AS ts_max,
                           precipitations_mm_24h, humidite_sol_pct
                    FROM meteo
                    WHERE zone_id = ?
                    GROUP BY zone_id, jour
                ) m ON DATE(p.timestamp) = m.jour
                LEFT JOIN (
                    SELECT zone_id, DATE(timestamp) AS jour,
                           MAX(timestamp) AS ts_max,
                           ndwi, sentinel1_vv
                    FROM satellite
                    WHERE zone_id = ?
                    GROUP BY zone_id, jour
                ) s ON DATE(p.timestamp) = s.jour
                WHERE p.zone_id = ?
                ORDER BY p.timestamp DESC
                LIMIT ?
            """, (zone_id, zone_id, zone_id, limite)).fetchall()

            return [dict(row) for row in rows]

    def get_stats_globales(self) -> dict:
        """Statistiques globales du système"""
        with self._connect() as conn:
            stats = conn.execute("""
                SELECT
                    COUNT(*)                                          AS total_predictions,
                    SUM(alerte_declenchee)                           AS total_alertes,
                    AVG(probabilite)                                  AS prob_moyenne,
                    MAX(timestamp)                                    AS derniere_mise_a_jour
                FROM predictions
                WHERE timestamp >= datetime('now', '-7 days')
            """).fetchone()

            sms = conn.execute("""
                SELECT
                    SUM(nb_envoyes)  AS sms_envoyes,
                    SUM(cout_fcfa)   AS cout_total
                FROM alertes_sms
                WHERE timestamp >= datetime('now', '-7 days')
            """).fetchone()

            return {
                "predictions_7j":      stats["total_predictions"] or 0,
                "alertes_7j":          stats["total_alertes"] or 0,
                "prob_moyenne":        round((stats["prob_moyenne"] or 0) * 100, 1),
                "derniere_maj":        stats["derniere_mise_a_jour"],
                "sms_envoyes_7j":      sms["sms_envoyes"] or 0,
                "cout_sms_7j_fcfa":    sms["cout_total"] or 0,
            }

    def get_alertes_critiques_recentes(self, heures: int = 24) -> List[dict]:
        """Retourne les zones avec alerte critique dans les N dernières heures"""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT DISTINCT zone_id, niveau_alerte, MAX(timestamp) as derniere_alerte
                FROM predictions
                WHERE niveau_alerte IN ('critique', 'moyen')
                  AND timestamp >= datetime('now', ? || ' hours')
                GROUP BY zone_id
                ORDER BY derniere_alerte DESC
            """, (f"-{heures}",)).fetchall()
            return [dict(row) for row in rows]

    def purger_anciennes_donnees(self, jours: int = 90):
        """Supprime les données de plus de N jours (maintenance)"""
        TABLES_AUTORISEES = {"predictions", "meteo", "satellite"}
        with self._connect() as conn:
            for table in TABLES_AUTORISEES:
                conn.execute(
                    f"DELETE FROM {table} WHERE timestamp < datetime('now', ? || ' days')",
                    (f"-{jours}",)
                )
        print(f" Données de plus de {jours} jours supprimées")


# ─────────────────────────────────────────────
# 🚀 TEST
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))

    from katara_model import KataraModele, ZoneRisque, DonneesSatellitaires
    from katara_meteo import simuler_meteo_lome
    from katara_sat   import simuler_satellite

    print("=" * 55)
    print("  KATARA  Test Base de Données")
    print("=" * 55)

    db = DatabaseKATARA("katara_test.db")

    zone = ZoneRisque(
        "LOM-001", "Bè-Kpota", 6.1319, 1.2228,
        8.5, 42.3, "argileux", 120.0, 15000, [], ["+22890000001"]
    )

    # Sauvegarde quelques prédictions
    modele = KataraModele()
    for scenario in ["sec", "pluie_forte", "orage"]:
        meteo   = simuler_meteo_lome("LOM-001", scenario)
        sat_raw = simuler_satellite("LOM-001")
        sat = DonneesSatellitaires(
            zone_id="LOM-001", timestamp=datetime.now(),
            ndwi=sat_raw.ndwi, ndvi=sat_raw.ndvi, sentinel1_vv=sat_raw.sentinel1_vv
        )
        r = modele.predire(zone, meteo, sat)
        db.sauvegarder_prediction(r, meteo, sat)
        print(f"   Sauvegardé : {scenario}  {r.niveau_alerte} ({r.probabilite*100:.0f}%)")

    # Lecture
    historique = db.get_historique("LOM-001", limite=5)
    print(f"\n   Historique ({len(historique)} entrées) :")
    for h in historique:
        print(f"     {h['timestamp'][:16]} | {h['niveau_alerte']} | {h['probabilite']*100:.0f}%")

    stats = db.get_stats_globales()
    print(f"\n   Stats globales : {stats}")

    # Nettoyage test
    os.remove("katara_test.db")
    print("\n Test base de données réussi !")
