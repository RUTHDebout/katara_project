"""
╔══════════════════════════════════════════════════════════════╗
║         KATARA v6 — Configuration des Zones                 ║
║         Source unique de vérité pour toutes les zones       ║
║         Importé par katara_api.py et katara_scheduler.py    ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from katara_model import ZoneRisque

# ─────────────────────────────────────────────
# 🗺️ ZONES SURVEILLÉES — Région Maritime, Togo
# ─────────────────────────────────────────────
ZONES = [
    ZoneRisque("LOM-001", "Bè-Kpota",    6.1319, 1.2228, 8.5,  42.3, "argileux",    120.0, 15000, [], ["+22890000001"]),
    ZoneRisque("LOM-002", "Agoè-Nyivé",  6.1950, 1.2100, 12.0, 38.0, "lateritique", 150.0, 22000, [], ["+22890000002"]),
    ZoneRisque("LOM-003", "Baguida",     6.1000, 1.3000, 5.0,  28.0, "sableux",     200.0,  8000, [], ["+22890000003"]),
    ZoneRisque("LOM-004", "Aflao-Gakli", 6.0984, 1.1950, 7.0,  35.0, "argileux",    110.0, 11000, [], ["+22890000004"]),
    ZoneRisque("LOM-005", "Lomé-Port",   6.1341, 1.2637, 3.0,  18.0, "sableux",     180.0,  5000, [], ["+22890000005"]),
]
