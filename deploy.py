"""
╔══════════════════════════════════════════════════════════════╗
║         KATARA - Script de déploiement                      ║
║         Configure l'URL de l'API dans le dashboard          ║
╚══════════════════════════════════════════════════════════════╝

Lance avec : python deploy.py --url https://katara-api.railway.app
"""

import argparse
import re
import os
import subprocess
import sys

DASHBOARD = "katara_dashboard.html"

def mettre_a_jour_url_api(url: str):
    """Remplace l'URL API dans le dashboard HTML"""
    if not os.path.exists(DASHBOARD):
        print(f"❌ {DASHBOARD} introuvable")
        return False

    with open(DASHBOARD, "r", encoding="utf-8") as f:
        contenu = f.read()

    # Injecte la config API au début du script JS
    config_js = f"""
  // ── CONFIG API ──
  const API_URL = "{url}";
  const API_ENABLED = true;
"""

    # Remplace ou insère après <script>
    if "const API_URL" in contenu:
        contenu = re.sub(
            r"const API_URL = \".*?\";",
            f'const API_URL = "{url}";',
            contenu
        )
    else:
        contenu = contenu.replace(
            "// ═══════════════════════════════════════════════",
            config_js + "// ═══════════════════════════════════════════════",
            1
        )

    with open(DASHBOARD, "w", encoding="utf-8") as f:
        f.write(contenu)

    print(f"✅ Dashboard configuré avec l'URL : {url}")
    return True


def verifier_api(url: str) -> bool:
    """Vérifie que l'API répond"""
    try:
        import requests
        r = requests.get(f"{url}/api/status", timeout=10)
        data = r.json()
        print(f"✅ API en ligne : {data['status']} | {data['zones']} zones")
        return True
    except Exception as e:
        print(f"⚠️  API non joignable : {e}")
        return False


def guide_deploiement():
    print("""
╔══════════════════════════════════════════════════════════════╗
║         KATARA — Guide de Déploiement Cloud                 ║
╚══════════════════════════════════════════════════════════════╝

━━━ OPTION 1 : Railway (recommandé, gratuit) ━━━━━━━━━━━━━━━━

1. Va sur https://railway.app → connecte ton compte GitHub
2. "New Project" → "Deploy from GitHub repo"
3. Sélectionne ton repo KATARA
4. Railway détecte le Procfile automatiquement ✅
5. Dans "Variables" → ajoute :
   • OWM_API_KEY   = ta_cle_openweathermap
   • AT_USERNAME   = ton_username_africastalking
   • AT_API_KEY    = ta_cle_africastalking
   • AT_SENDER     = KATARA
6. Ton URL sera : https://katara-api-xxxx.railway.app

━━━ OPTION 2 : Render (aussi gratuit) ━━━━━━━━━━━━━━━━━━━━━━

1. Va sur https://render.com → connecte GitHub
2. "New" → "Blueprint" → sélectionne ton repo
3. Render lit render.yaml automatiquement ✅
4. Ajoute les variables d'environnement
5. Ton URL sera : https://katara-api.onrender.com

━━━ OPTION 3 : Déploiement manuel ━━━━━━━━━━━━━━━━━━━━━━━━━━

Sur n'importe quel serveur Linux :

   # Cloner le projet
   git clone https://github.com/ton-compte/katara.git
   cd katara

   # Installer
   pip install -r requirements.txt

   # Configurer
   cp .env.example .env
   nano .env  # remplir les clés

   # Lancer (avec screen pour garder actif)
   screen -S katara-api
   python katara_api.py

   screen -S katara-scheduler
   python katara_scheduler.py

━━━ APRÈS DÉPLOIEMENT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Configure le dashboard avec ton URL :

   python deploy.py --url https://ton-url.railway.app

Puis vérifie :

   https://ton-url.railway.app/api/status
   https://ton-url.railway.app/api/dashboard

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KATARA Deploy Helper")
    parser.add_argument("--url", help="URL de l'API déployée")
    parser.add_argument("--check", help="Vérifie que l'API répond", action="store_true")
    parser.add_argument("--guide", help="Affiche le guide de déploiement", action="store_true")
    args = parser.parse_args()

    if args.guide or (not args.url and not args.check):
        guide_deploiement()

    if args.url:
        mettre_a_jour_url_api(args.url)

    if args.check and args.url:
        verifier_api(args.url)
