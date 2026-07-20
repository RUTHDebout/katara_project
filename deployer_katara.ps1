# ╔══════════════════════════════════════════════════════════╗
# ║   KATARA — Déploiement sur Google Cloud Run             ║
# ║   Script PowerShell pour Windows                        ║
# ║   Lance avec : .\deployer_katara.ps1                    ║
# ╚══════════════════════════════════════════════════════════╝
#
# AVANT DE LANCER CE SCRIPT :
#   1. Installe Google Cloud CLI : https://cloud.google.com/sdk/docs/install
#   2. Ouvre PowerShell en tant qu'administrateur
#   3. Navigue dans le dossier katara_project
#   4. Lance : .\deployer_katara.ps1

# ── CONFIGURATION — MODIFIE CES 2 LIGNES ──────────────────
$PROJECT_ID = "katara-project-487820"
$REGION     = "us-central1"      # région (us-central1 = gratuit sur le free tier)
# ──────────────────────────────────────────────────────────

$SERVICE_NAME = "katara-api"
$IMAGE        = "gcr.io/$PROJECT_ID/$SERVICE_NAME"

# ── Couleurs pour le terminal ──
function OK   { Write-Host "  ✅ $args" -ForegroundColor Green }
function INFO { Write-Host "  ℹ️  $args" -ForegroundColor Cyan }
function WARN { Write-Host "  ⚠️  $args" -ForegroundColor Yellow }
function ERR  { Write-Host "  ❌ $args" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Blue
Write-Host "  🛰️  KATARA — Déploiement Google Cloud Run" -ForegroundColor Blue
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Blue
Write-Host ""

# ── Étape 0 : Vérifier les prérequis ──────────────────────
INFO "Vérification de Google Cloud CLI..."
try {
    $gcloudVersion = gcloud version --format="value(Google Cloud SDK)" 2>$null
    OK "gcloud détecté"
} catch {
    ERR "gcloud non trouvé. Installe-le sur : https://cloud.google.com/sdk/docs/install"
}

# ── Étape 1 : Authentification ────────────────────────────
Write-Host ""
Write-Host "── Étape 1/5 : Connexion à Google Cloud ──" -ForegroundColor Yellow
INFO "Ouverture du navigateur pour t'authentifier..."
gcloud auth login
if ($LASTEXITCODE -ne 0) { ERR "Authentification échouée" }
OK "Authentification réussie"

# ── Étape 2 : Configurer le projet ────────────────────────
Write-Host ""
Write-Host "── Étape 2/5 : Configuration du projet ──" -ForegroundColor Yellow
gcloud config set project $PROJECT_ID
if ($LASTEXITCODE -ne 0) { ERR "Projet '$PROJECT_ID' non trouvé. Vérifie l'ID dans Google Cloud Console." }
OK "Projet configuré : $PROJECT_ID"

# Activer les APIs nécessaires
INFO "Activation des APIs Cloud Run et Container Registry..."
gcloud services enable run.googleapis.com containerregistry.googleapis.com --quiet
OK "APIs activées"

# ── Étape 3 : Build et push de l'image Docker ────────────
Write-Host ""
Write-Host "── Étape 3/5 : Construction de l'image Docker ──" -ForegroundColor Yellow
INFO "Construction de l'image (2-3 minutes)..."
gcloud builds submit --tag $IMAGE .
if ($LASTEXITCODE -ne 0) { ERR "Échec de la construction Docker. Vérifie le Dockerfile." }
OK "Image construite et envoyée : $IMAGE"

# ── Étape 4 : Déployer sur Cloud Run ─────────────────────
Write-Host ""
Write-Host "── Étape 4/5 : Déploiement sur Cloud Run ──" -ForegroundColor Yellow
INFO "Déploiement en cours..."
gcloud run deploy $SERVICE_NAME `
    --image $IMAGE `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --memory 512Mi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 3 `
    --timeout 120 `
    --quiet

if ($LASTEXITCODE -ne 0) { ERR "Échec du déploiement Cloud Run" }
OK "Service déployé avec succès !"

# ── Étape 5 : Variables d'environnement ──────────────────
Write-Host ""
Write-Host "── Étape 5/5 : Configuration des variables ──" -ForegroundColor Yellow
WARN "Tu dois maintenant configurer tes clés API."
INFO "Ouvre Google Cloud Console → Cloud Run → katara-api → Modifier → Variables"
Write-Host ""
Write-Host "  Variables à ajouter :" -ForegroundColor Cyan
Write-Host "    OWM_API_KEY        = ta_cle_openweathermap" -ForegroundColor White
Write-Host "    AT_USERNAME        = sandbox  (ou ton vrai username AT)" -ForegroundColor White
Write-Host "    AT_API_KEY         = ta_cle_africastalking" -ForegroundColor White
Write-Host "    AT_SENDER          = KATARA" -ForegroundColor White
Write-Host "    KATARA_TEAM_PHONES = +22890000000" -ForegroundColor White
Write-Host ""

# ── Récupérer l'URL finale ────────────────────────────────
$SERVICE_URL = (gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)" 2>$null)

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  🎉 KATARA EST EN LIGNE !" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
if ($SERVICE_URL) {
    Write-Host "  🌐 URL de ton API :" -ForegroundColor Cyan
    Write-Host "     $SERVICE_URL" -ForegroundColor White
    Write-Host ""
    Write-Host "  📊 Dashboard :" -ForegroundColor Cyan
    Write-Host "     $SERVICE_URL/api/dashboard" -ForegroundColor White
    Write-Host ""
    Write-Host "  🔍 Test rapide :" -ForegroundColor Cyan
    Write-Host "     $SERVICE_URL/api/status" -ForegroundColor White
}
Write-Host ""
Write-Host "  📌 Copie cette URL dans tes dossiers :" -ForegroundColor Yellow
Write-Host "     UNDP · Xylem Challenge · DID Summit 2026" -ForegroundColor Yellow
Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
