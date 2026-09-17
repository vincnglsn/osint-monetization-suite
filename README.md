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
3. Variables d'environnement requises :
   - `STRIPE_SECRET_KEY` (sk_live_...)
   - `STRIPE_WEBHOOK_SECRET` (whsec_...)
   - `DATABASE_URL` (Supabase connection string)
   - `BREVO_API_KEY`
   - `ADMIN_API_KEY` (Pour le feeder)

## 💸 Workflow Client
1. Le client achète sur le Lien de Paiement Stripe (49€).
2. Stripe appelle le Webhook `/stripe/webhook`.
3. L'API génère une clé secrète, la stocke dans Supabase, et envoie un email HTML au client via Brevo.
4. Le client consulte `dashboard.html` ou utilise `osint_sdk.py` avec sa nouvelle clé.
