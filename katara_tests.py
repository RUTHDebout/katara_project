"""
╔══════════════════════════════════════════════════════════════╗
║         KATARA — Tests automatisés                          ║
║         Lance avec : python katara_tests.py                 ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys, os, unittest
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))

from katara_model   import KataraModele, ZoneRisque, DonneesSatellitaires
from katara_meteo   import simuler_meteo_lome
from katara_sat     import simuler_satellite
from katara_db      import DatabaseKATARA

# ─────────────────────────────────────────────
class TestModele(unittest.TestCase):

    def setUp(self):
        self.modele = KataraModele()
        self.zone = ZoneRisque(
            "TEST-001", "Zone Test", 6.13, 1.22,
            8.5, 42.3, "argileux", 120.0, 10000, [], []
        )

    def test_prediction_scenario_sec(self):
        meteo = simuler_meteo_lome("TEST-001", "sec")
        sat = self._make_sat()
        r = self.modele.predire(self.zone, meteo, sat)
        self.assertIn(r.niveau_alerte, ["normal","faible","moyen","critique"])
        self.assertGreaterEqual(r.probabilite, 0)
        self.assertLessEqual(r.probabilite, 1)

    def test_prediction_orage_declenche_alerte(self):
        meteo = simuler_meteo_lome("TEST-001", "orage")
        sat = self._make_sat(ndwi=0.45)
        r = self.modele.predire(self.zone, meteo, sat)
        self.assertIn(r.niveau_alerte, ["moyen","critique"])
        self.assertTrue(r.alerte_declenchee)

    def test_prediction_sec_pas_alerte(self):
        meteo = simuler_meteo_lome("TEST-001", "sec")
        sat = self._make_sat(ndwi=-0.2)
        r = self.modele.predire(self.zone, meteo, sat)
        self.assertFalse(r.alerte_declenchee)

    def test_message_sms_critique_non_vide(self):
        meteo = simuler_meteo_lome("TEST-001", "orage")
        sat = self._make_sat(ndwi=0.45)
        r = self.modele.predire(self.zone, meteo, sat)
        if r.niveau_alerte == "critique":
            self.assertIsNotNone(r.message_sms)
            self.assertLessEqual(len(r.message_sms), 160)

    def test_cinq_zones_differentes(self):
        zones_ids = ["LOM-001","LOM-002","LOM-003","LOM-004","LOM-005"]
        for zid in zones_ids:
            meteo = simuler_meteo_lome(zid)
            sat = self._make_sat()
            r = self.modele.predire(self.zone, meteo, sat)
            self.assertIsNotNone(r.probabilite)

    def _make_sat(self, ndwi=0.1):
        sat_raw = simuler_satellite("TEST-001")
        return DonneesSatellitaires(
            zone_id="TEST-001", timestamp=datetime.now(),
            ndwi=ndwi, ndvi=sat_raw.ndvi, sentinel1_vv=sat_raw.sentinel1_vv
        )


# ─────────────────────────────────────────────
class TestMeteo(unittest.TestCase):

    def test_tous_scenarios(self):
        for scenario in ["sec","pluie_légère","pluie_forte","orage"]:
            m = simuler_meteo_lome("TEST-001", scenario)
            self.assertIsNotNone(m)
            self.assertGreaterEqual(m.precipitations_mm_24h, 0)
            self.assertGreaterEqual(m.humidite_sol_pct, 0)
            self.assertLessEqual(m.humidite_sol_pct, 100)

    def test_orage_pluie_superieure_sec(self):
        sec   = simuler_meteo_lome("TEST-001", "sec")
        orage = simuler_meteo_lome("TEST-001", "orage")
        self.assertGreater(orage.precipitations_mm_24h, sec.precipitations_mm_24h)


# ─────────────────────────────────────────────
class TestSatellite(unittest.TestCase):

    def test_ndwi_dans_intervalle(self):
        sat = simuler_satellite("TEST-001")
        self.assertGreaterEqual(sat.ndwi, -1)
        self.assertLessEqual(sat.ndwi, 1)

    def test_ndvi_dans_intervalle(self):
        sat = simuler_satellite("TEST-001")
        self.assertGreaterEqual(sat.ndvi, -1)
        self.assertLessEqual(sat.ndvi, 1)


# ─────────────────────────────────────────────
class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.db = DatabaseKATARA("katara_test_unit.db")
        self.modele = KataraModele()
        self.zone = ZoneRisque(
            "TEST-001","Zone Test",6.13,1.22,
            8.5,42.3,"argileux",120.0,10000,[],[]
        )

    def tearDown(self):
        import os
        if os.path.exists("katara_test_unit.db"):
            os.remove("katara_test_unit.db")

    def test_sauvegarder_et_relire(self):
        meteo   = simuler_meteo_lome("TEST-001", "pluie_forte")
        sat_raw = simuler_satellite("TEST-001")
        sat = DonneesSatellitaires(
            zone_id="TEST-001", timestamp=datetime.now(),
            ndwi=sat_raw.ndwi, ndvi=sat_raw.ndvi, sentinel1_vv=sat_raw.sentinel1_vv
        )
        r = self.modele.predire(self.zone, meteo, sat)
        self.db.sauvegarder_prediction(r, meteo, sat)

        historique = self.db.get_historique("TEST-001", limite=5)
        self.assertEqual(len(historique), 1)
        self.assertAlmostEqual(historique[0]["probabilite"], r.probabilite, places=2)

    def test_stats_globales(self):
        for s in ["sec","orage"]:
            meteo   = simuler_meteo_lome("TEST-001", s)
            sat_raw = simuler_satellite("TEST-001")
            sat = DonneesSatellitaires(
                zone_id="TEST-001", timestamp=datetime.now(),
                ndwi=sat_raw.ndwi, ndvi=sat_raw.ndvi, sentinel1_vv=sat_raw.sentinel1_vv
            )
            r = self.modele.predire(self.zone, meteo, sat)
            self.db.sauvegarder_prediction(r, meteo, sat)

        stats = self.db.get_stats_globales()
        self.assertGreaterEqual(stats["predictions_7j"], 2)

    def test_sauvegarder_zone(self):
        self.db.sauvegarder_zone(self.zone)
        # Pas d'exception = succès


# ─────────────────────────────────────────────
class TestAPI(unittest.TestCase):

    def setUp(self):
        from katara_api import app
        self.client = app.test_client()

    def test_status_ok(self):
        r = self.client.get("/api/status")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["status"], "ok")

    def test_zones_retourne_liste(self):
        r = self.client.get("/api/zones")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_dashboard_structure(self):
        r = self.client.get("/api/dashboard")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("zones", data)
        self.assertIn("resume", data)
        self.assertIn("total_zones", data["resume"])

    def test_prediction_zone_valide(self):
        r = self.client.get("/api/zones/LOM-001/prediction")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn("probabilite", data)
        self.assertIn("niveau_alerte", data)

    def test_prediction_zone_invalide(self):
        r = self.client.get("/api/zones/INEXISTANT/prediction")
        self.assertEqual(r.status_code, 404)

    def test_historique(self):
        r = self.client.get("/api/zones/LOM-001/historique")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.get_json(), list)


# ─────────────────────────────────────────────
def lancer_tests():
    print("=" * 55)
    print("  🧪 KATARA — Tests automatisés")
    print("=" * 55)

    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    for cls in [TestModele, TestMeteo, TestSatellite, TestDatabase, TestAPI]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 55)
    if result.wasSuccessful():
        print(f"  ✅ {result.testsRun} tests réussis — KATARA est prêt !")
    else:
        print(f"  ❌ {len(result.failures)} échec(s), {len(result.errors)} erreur(s)")
    print("=" * 55)

    return result.wasSuccessful()


if __name__ == "__main__":
    ok = lancer_tests()
    sys.exit(0 if ok else 1)
