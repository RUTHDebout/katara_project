"""
╔══════════════════════════════════════════════════════════════╗
║         KATARA - Module Alertes SMS                         ║
║         Source : Africa's Talking API                       ║
╚══════════════════════════════════════════════════════════════╝

Ce module envoie automatiquement les alertes SMS
aux populations des zones à risque.

📌 Pour obtenir ta clé API Africa's Talking :
   1. Va sur : https://africastalking.com
   2. Crée un compte → Dashboard → API Key
   3. Compte sandbox GRATUIT pour tester
   4. Compte live pour envoyer de vrais SMS

📌 Installation :
   pip install africastalking
"""

import os
import json
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─────────────────────────────────────────────
# ⚙️ CONFIGURATION
# ─────────────────────────────────────────────

AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")       # "sandbox" pour tester
AT_API_KEY  = os.getenv("AT_API_KEY",  "METS_TA_CLE_ICI")
AT_SENDER   = os.getenv("AT_SENDER",   "KATARA")        # nom affiché sur le SMS

# Limite de caractères SMS
SMS_MAX_CHARS = 160


# ─────────────────────────────────────────────
# 📦 STRUCTURE D'UN ENVOI SMS
# ─────────────────────────────────────────────
@dataclass
class ResultatSMS:
    """Résultat d'un envoi SMS"""
    numero: str
    statut: str          # "envoyé", "échec", "simulé"
    message_id: str
    cout: float          # en FCFA
    timestamp: datetime
    erreur: Optional[str] = None


@dataclass
class RapportAlertes:
    """Rapport complet d'une campagne d'alertes"""
    zone_id: str
    niveau_alerte: str
    timestamp: datetime
    total_envoyes: int
    total_echecs: int
    cout_total_fcfa: float
    resultats: List[ResultatSMS] = field(default_factory=list)
    
    @property
    def taux_succes(self) -> float:
        total = self.total_envoyes + self.total_echecs
        return (self.total_envoyes / total * 100) if total > 0 else 0


# ─────────────────────────────────────────────
# 📱 GESTIONNAIRE SMS KATARA
# ─────────────────────────────────────────────
class GestionnaireSMS:
    """
    Envoie les alertes SMS via Africa's Talking.
    Gère automatiquement les tentatives, logs, et rapports.
    """

    # Coût approx par SMS au Togo (CFA)
    COUT_SMS_FCFA = 10.0

    def __init__(
        self,
        username: str = AT_USERNAME,
        api_key: str  = AT_API_KEY,
        sender: str   = AT_SENDER,
        mode_test: bool = False
    ):
        self.username  = username
        self.api_key   = api_key
        self.sender    = sender
        self.mode_test = mode_test or (username == "sandbox")
        self.sdk        = None
        self.sms        = None
        self._initialiser()

    def _initialiser(self):
        """Initialise le SDK Africa's Talking"""
        if self.api_key == "METS_TA_CLE_ICI":
            print("  Clé API Africa's Talking non configurée.")
            print("    https://africastalking.com pour en obtenir une\n")
            self.mode_test = True
            return

        try:
            import africastalking
            africastalking.initialize(self.username, self.api_key)
            self.sms = africastalking.SMS
            mode = "SANDBOX (test)" if self.mode_test else "PRODUCTION"
            print(f" Africa's Talking connecté  Mode : {mode}")
        except ImportError:
            print("  africastalking non installé.")
            print("   pip install africastalking")
            self.mode_test = True
        except Exception as e:
            print(f"  Erreur initialisation AT : {e}")
            self.mode_test = True

    # ── ENVOI D'UN SMS ────────────────────────────
    def envoyer_sms(
        self,
        numero: str,
        message: str,
        tentatives: int = 3
    ) -> ResultatSMS:
        """
        Envoie un SMS à un numéro.
        Format numéro : +228XXXXXXXX (Togo)
        """

        # Troncature si > 160 caractères
        if len(message) > SMS_MAX_CHARS:
            message = message[:SMS_MAX_CHARS - 3] + "..."

        # Mode simulation
        if self.mode_test or self.sms is None:
            return ResultatSMS(
                numero     = numero,
                statut     = "simulé",
                message_id = f"SIM-{datetime.now().strftime('%H%M%S')}",
                cout       = self.COUT_SMS_FCFA,
                timestamp  = datetime.now()
            )

        # Envoi réel avec tentatives
        for tentative in range(1, tentatives + 1):
            try:
                response = self.sms.send(
                    message    = message,
                    recipients = [numero],
                    sender_id  = self.sender
                )

                recipient = response["SMSMessageData"]["Recipients"][0]
                statut    = "envoyé" if recipient["status"] == "Success" else "échec"
                cout      = float(recipient.get("cost", "0").replace("XAF ", "").replace(",", ".") or self.COUT_SMS_FCFA)

                return ResultatSMS(
                    numero     = numero,
                    statut     = statut,
                    message_id = recipient.get("messageId", ""),
                    cout       = cout,
                    timestamp  = datetime.now()
                )

            except Exception as e:
                if tentative == tentatives:
                    return ResultatSMS(
                        numero     = numero,
                        statut     = "échec",
                        message_id = "",
                        cout       = 0.0,
                        timestamp  = datetime.now(),
                        erreur     = str(e)
                    )
                time.sleep(2 ** tentative)  # attente exponentielle

    # ── ALERTE ZONE COMPLÈTE ──────────────────────
    def alerter_zone(
        self,
        zone_id: str,
        zone_nom: str,
        numeros: List[str],
        niveau_alerte: str,
        probabilite: float,
        delai_heures: Optional[float] = None,
        message_custom: Optional[str] = None
    ) -> RapportAlertes:
        """
        Envoie une alerte à tous les numéros d'une zone.
        Ne déclenche que pour alertes "moyen" ou "critique".
        """

        if niveau_alerte == "faible":
            print(f"  Zone {zone_id} : alerte faible, pas d'envoi SMS")
            return RapportAlertes(
                zone_id=zone_id, niveau_alerte=niveau_alerte,
                timestamp=datetime.now(), total_envoyes=0,
                total_echecs=0, cout_total_fcfa=0.0
            )

        # Construction du message
        message = message_custom or self._construire_message(
            zone_nom, niveau_alerte, probabilite, delai_heures
        )

        print(f"\n Envoi alertes zone {zone_id} ({zone_nom})")
        print(f"   Niveau : {niveau_alerte.upper()} | {len(numeros)} destinataires")
        print(f"   Message ({len(message)} car.) :")
        print(f"    {message} \n")

        resultats  = []
        nb_envoyes = 0
        nb_echecs  = 0
        cout_total = 0.0

        for i, numero in enumerate(numeros, 1):
            print(f"   [{i}/{len(numeros)}] {numero}...", end=" ")
            result = self.envoyer_sms(numero, message)
            resultats.append(result)

            if result.statut in ("envoyé", "simulé"):
                nb_envoyes += 1
                cout_total += result.cout
                print(f" {result.statut}")
            else:
                nb_echecs += 1
                print(f" {result.erreur or 'échec'}")

            # Pause entre envois (évite spam API)
            if i < len(numeros):
                time.sleep(0.2)

        rapport = RapportAlertes(
            zone_id        = zone_id,
            niveau_alerte  = niveau_alerte,
            timestamp      = datetime.now(),
            total_envoyes  = nb_envoyes,
            total_echecs   = nb_echecs,
            cout_total_fcfa = cout_total,
            resultats      = resultats
        )

        self._afficher_rapport(rapport)
        self._sauvegarder_log(rapport, message)

        return rapport

    # ── CONSTRUCTION DU MESSAGE ───────────────────
    def _construire_message(
        self,
        zone_nom: str,
        niveau: str,
        prob: float,
        delai: Optional[float]
    ) -> str:
        """Génère le SMS selon le niveau d'alerte"""

        emoji = {"moyen": "⚠️", "critique": "🚨"}.get(niveau, "⚠️")
        delai_txt = f" dans ~{delai:.0f}h" if delai else ""

        if niveau == "critique":
            return (
                f"{emoji} ALERTE KATARA\n"
                f"DANGER INONDATION{delai_txt} - {zone_nom}\n"
                f"Risque: {prob*100:.0f}%\n"
                f"Evacuez immediatement les zones basses!\n"
                f"Info: katara.tg"
            )
        else:
            return (
                f"{emoji} VIGILANCE KATARA\n"
                f"Risque inondation - {zone_nom}\n"
                f"Probabilite: {prob*100:.0f}%\n"
                f"Restez vigilants, suivez les consignes.\n"
                f"Info: katara.tg"
            )

    # ── AFFICHAGE RAPPORT ─────────────────────────
    def _afficher_rapport(self, rapport: RapportAlertes):
        print(f"\n RAPPORT ALERTES  Zone {rapport.zone_id}")
        print(f"    Envoyés  : {rapport.total_envoyes}")
        print(f"    Échecs   : {rapport.total_echecs}")
        print(f"    Succès   : {rapport.taux_succes:.0f}%")
        print(f"    Coût     : {rapport.cout_total_fcfa:.0f} FCFA")

    # ── LOG PERSISTANT ────────────────────────────
    def _sauvegarder_log(self, rapport: RapportAlertes, message: str):
        """Sauvegarde chaque alerte dans un fichier JSON"""
        log = {
            "timestamp"     : rapport.timestamp.isoformat(),
            "zone_id"       : rapport.zone_id,
            "niveau_alerte" : rapport.niveau_alerte,
            "total_envoyes" : rapport.total_envoyes,
            "total_echecs"  : rapport.total_echecs,
            "cout_fcfa"     : rapport.cout_total_fcfa,
            "message"       : message,
        }
        try:
            logs = []
            if os.path.exists("katara_alertes_log.json"):
                with open("katara_alertes_log.json") as f:
                    logs = json.load(f)
            logs.append(log)
            with open("katara_alertes_log.json", "w") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # le log est optionnel


# ─────────────────────────────────────────────
# 🔁 PIPELINE COMPLET KATARA (TOUS LES MODULES)
# ─────────────────────────────────────────────
def lancer_surveillance_katara(zones_config: list, mode_test: bool = True):
    """
    Lance un cycle complet de surveillance KATARA :
    Météo → Satellite → Prédiction → SMS

    zones_config = liste de dicts avec les infos de chaque zone
    """

    import sys
    sys.path.insert(0, os.path.dirname(__file__))

    from katara_model import KataraModele, ZoneRisque, DonneesSatellitaires
    from katara_meteo import simuler_meteo_lome
    from katara_sat   import simuler_satellite

    print("\n" + "=" * 60)
    print(f"    KATARA  Cycle de surveillance")
    print(f"   {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    modele = KataraModele()
    sms    = GestionnaireSMS(mode_test=mode_test)

    for config in zones_config:
        zone = ZoneRisque(**config["zone"])
        print(f"\n Analyse zone : {zone.nom} ({zone.zone_id})")

        # Météo (simulation ou réelle)
        meteo = simuler_meteo_lome(zone.zone_id, config.get("scenario_meteo", "pluie_forte"))

        # Satellite
        sat_raw = simuler_satellite(zone.zone_id, config.get("scenario_sat", "inondation_imminente"))
        sat = DonneesSatellitaires(
            zone_id=zone.zone_id, timestamp=datetime.now(),
            ndwi=sat_raw.ndwi, ndvi=sat_raw.ndvi, sentinel1_vv=sat_raw.sentinel1_vv
        )

        # Prédiction
        resultat = modele.predire(zone, meteo, sat)
        print(f"    Probabilité : {resultat.probabilite*100:.0f}%")
        print(f"    Niveau      : {resultat.niveau_alerte.upper()}")

        # Envoi SMS si alerte
        if resultat.alerte_declenchee and zone.telephones:
            sms.alerter_zone(
                zone_id       = zone.zone_id,
                zone_nom      = zone.nom,
                numeros       = zone.telephones,
                niveau_alerte = resultat.niveau_alerte,
                probabilite   = resultat.probabilite,
                delai_heures  = resultat.delai_heures,
                message_custom = resultat.message_sms
            )
        else:
            print(f"    Pas d'alerte nécessaire")

    print("\n" + "=" * 60)
    print("   Cycle terminé. Prochain cycle dans 1h.")
    print("=" * 60)


# ─────────────────────────────────────────────
# 🚀 TEST
# ─────────────────────────────────────────────
if __name__ == "__main__":

    print("=" * 60)
    print("   KATARA - Module SMS | Test complet")
    print("=" * 60)

    # Configuration des zones de la région Maritime
    zones_config = [
        {
            "scenario_meteo": "orage",
            "scenario_sat"  : "inondation_imminente",
            "zone": dict(
                zone_id="LOM-001", nom="Bè-Kpota",
                latitude=6.1319, longitude=1.2228,
                altitude_m=8.5, superficie_bassin_km2=42.3,
                type_sol="argileux", capacite_drainage=120.0,
                population=15000,
                telephones=["+22890000001", "+22890000002", "+22891234567"]
            )
        },
        {
            "scenario_meteo": "pluie_forte",
            "scenario_sat"  : "pre_inondation",
            "zone": dict(
                zone_id="LOM-002", nom="Agoè-Nyivé",
                latitude=6.1950, longitude=1.2100,
                altitude_m=12.0, superficie_bassin_km2=38.0,
                type_sol="lateritique", capacite_drainage=150.0,
                population=22000,
                telephones=["+22890000003", "+22890000004"]
            )
        },
        {
            "scenario_meteo": "sec",
            "scenario_sat"  : "normal",
            "zone": dict(
                zone_id="LOM-003", nom="Baguida",
                latitude=6.1000, longitude=1.3000,
                altitude_m=5.0, superficie_bassin_km2=28.0,
                type_sol="sableux", capacite_drainage=200.0,
                population=8000,
                telephones=["+22890000005"]
            )
        },
    ]

    # Lancer le pipeline complet en mode test (pas de vrais SMS)
    lancer_surveillance_katara(zones_config, mode_test=True)

    print("\n Pour activer les vrais SMS :")
    print("   1. Va sur https://africastalking.com")
    print("   2. Crée ton compte  récupère username + API key")
    print("   3. Dans ton fichier .env ajoute :")
    print("      AT_USERNAME=ton_username")
    print("      AT_API_KEY=ta_cle_api")
    print("      AT_SENDER=KATARA")
    print("   4. Change mode_test=False dans lancer_surveillance_katara()")
