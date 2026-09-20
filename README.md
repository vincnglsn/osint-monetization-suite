# OSINT ThreatFeed Monetization Suite 🛡️

Plateforme SaaS complète (Backend + Frontend + Billing) de monétisation de flux de renseignements sur les menaces (OSINT).

## 🚀 Architecture Globale
- **Backend** : FastAPI (Python) hébergé sur Render.
- **Base de données** : PostgreSQL hébergé sur Supabase (Pooler actif).
- **Billing** : Stripe Payment Links & Webhooks.
- **Emails** : Brevo API HTTP.
- **Frontend** : Dashboard Blueprint JS (React) & Landing Page TailwindCSS.

## 📦 Fonctionnalités
- **`GET /api/v1/threats/ips`** : Endpoint premium protégé par API Key, retourne la liste des menaces avec des filtres (`limit`, `min_confidence`). Rate Limiting : 60 req/min.
- **`POST /api/v1/admin/threats`** : Endpoint caché pour injecter dynamiquement des menaces depuis le feeder.
- **`osiris_feeder.py`** : Script Python autonome pour l'ingestion de données OSINT.
- **`osint_sdk.py`** : SDK Client Python prêt à être distribué aux abonnés.

## 🛠️ Déploiement
1. Pousser le code sur GitHub.
2. Déployer sur **Render** en tant que Web Service (build cmd: `pip install -r requirements.txt`, start cmd: `uvicorn monetization_suite.saas_api.main:app --host 0.0.0.0 --port 10000`).
3. Variables d'environnement (voir `.env.example` pour le detail) :
   - `STRIPE_SECRET_KEY` (sk_live_...)
   - `STRIPE_WEBHOOK_SECRET` (whsec_...)
   - `DATABASE_URL` (Supabase connection string)
   - `BREVO_API_KEY` et `EMAIL_SENDER`
   - `ADMIN_API_KEY` : **obligatoire**. Sans elle, les endpoints `/api/v1/admin/*`
     renvoient `503`. C'est aussi la cle que doit exporter `osiris_feeder.py`.
   - `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID` (optionnels) : si absents,
     `/api/v1/track` repond `200` sans notifier.
   - `ALLOWED_ORIGINS` (optionnel) : liste d'origines CORS separees par des virgules.
   - `ALLOW_UNVERIFIED_STRIPE_WEBHOOK` : **ne jamais definir en production**.
     A `1`, un webhook a signature invalide genere quand meme une cle API.

> Aucun secret ne doit etre commite. Le feeder et la page `admin.html` lisent
> desormais la cle admin depuis l'environnement ou une saisie manuelle.

## Pieges connus

- **Encodage des fichiers Python.** Ne modifiez jamais un `.py` avec `Out-File` ou
  `>` sous PowerShell : la sortie par defaut est en UTF-16, ce qui insere des
  octets nuls dans la source. Python refuse alors d'importer le module
  (`source code string cannot contain null bytes`) et le deploiement Render
  echoue silencieusement en continuant a servir l'ancien build. Utilisez
  `Out-File -Encoding utf8` ou un editeur.
- **Verifier un deploiement.** Comparez le nombre de routes reellement servies
  a celles attendues :
  `curl -s https://osint-monetization-suite.onrender.com/openapi.json`

## 💸 Workflow Client
1. Le client achète sur le Lien de Paiement Stripe (49€).
2. Stripe appelle le Webhook `/stripe/webhook`.
3. L'API génère une clé secrète, la stocke dans Supabase, et envoie un email HTML au client via Brevo.
4. Le client consulte `dashboard.html` ou utilise `osint_sdk.py` avec sa nouvelle clé.
