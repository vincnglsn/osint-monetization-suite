import logging
import os
import secrets
from contextlib import contextmanager
from ipaddress import ip_address

import psycopg2
import requests
import stripe
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("osint_api")

# Initialisation du Limiter (basé sur l'IP du visiteur)
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="OSINT ThreatFeed API", description="API de monétisation des flux OSINT")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configuration CORS pour autoriser le frontend.
# ALLOWED_ORIGINS accepte une liste separee par des virgules pour restreindre les domaines.
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # L'API s'authentifie par l'en-tete x-api-key, jamais par cookie : garder
    # allow_credentials a False evite que Starlette renvoie en echo n'importe
    # quelle origine appelante.
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Clés d'environnement
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_dummy")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
# Mode local uniquement : accepte un webhook dont la signature est invalide.
ALLOW_UNVERIFIED_STRIPE_WEBHOOK = os.getenv("ALLOW_UNVERIFIED_STRIPE_WEBHOOK", "") == "1"
# Le compte Stripe vend d'autres produits : seul ce lien de paiement donne droit a une cle API.
OSINT_PAYMENT_LINK_ID = "plink_1UGLo7E925DdRdvYEhKI3und"
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Configuration Email
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "contact@osint-saas.com")
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")

# Bornes de pagination pour eviter qu'un client ne demande des exports geants.
MAX_LIMIT = 1000
DEFAULT_LIMIT = 100

# Base de données en mémoire de secours (utilisée uniquement si DATABASE_URL est absent).
VALID_API_KEYS = {
    "premium_subscriber_key_49usd": "demo@admin.com"
}

blocked_ips_db = [
    {"ip": "192.168.1.100", "threat": "Port Scanning automatisé (22, 443)", "confidence": 0.95},
    {"ip": "45.33.12.9", "threat": "Anomalie relais Malacca Strait - Nœud Alpha", "confidence": 0.88},
    {"ip": "203.0.113.42", "threat": "Attaque DDoS (Live !)", "confidence": 0.99},
    # Nouvelles menaces injectées automatiquement suite au rapport OSIRIS AI
    {"ip": "45.33.12.10", "threat": "Anomalie relais Malacca Strait - Nœud Beta", "confidence": 0.92},
    {"ip": "45.33.12.11", "threat": "Anomalie relais Malacca Strait - Exfiltration", "confidence": 0.94},
    {"ip": "45.33.12.15", "threat": "Anomalie relais Malacca Strait - C2 Server", "confidence": 0.97},
    {"ip": "118.99.22.1", "threat": "BGP Hijacking - Asie-Pacifique (AS45999)", "confidence": 0.89},
    {"ip": "118.99.22.4", "threat": "BGP Hijacking - Asie-Pacifique (AS45999)", "confidence": 0.91},
    {"ip": "185.10.55.20", "threat": "Infrastructure Telecom Scan - Europe de l'Est", "confidence": 0.85},
    {"ip": "185.10.55.22", "threat": "Infrastructure Telecom Scan - Europe de l'Est", "confidence": 0.86},
]

blocked_domains_db = [
    {"domain": "update-windows-critical.com", "threat": "Phishing Microsoft 365", "confidence": 0.98},
    {"domain": "secure-login-apple-id.net", "threat": "Phishing Apple ID", "confidence": 0.95},
    {"domain": "ransom-payment-gateway.org", "threat": "Serveur de paiement Ransomware", "confidence": 0.99},
]

# ------------------------------------------------------------------
# Accès base de données : pool de connexions partagé (au lieu d'ouvrir
# une connexion TCP par requête, ce qui epuise vite le pooler Supabase
# sous charge).
# ------------------------------------------------------------------
_db_pool: SimpleConnectionPool | None = None


def _get_pool() -> SimpleConnectionPool:
    global _db_pool
    if _db_pool is None:
        _db_pool = SimpleConnectionPool(minconn=1, maxconn=10, dsn=DATABASE_URL)
    return _db_pool


@contextmanager
def get_db_cursor(dict_cursor: bool = False):
    """Emprunte une connexion au pool, la rend toujours a la fin (succes ou erreur)."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        cursor_factory = RealDictCursor if dict_cursor else None
        cur = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield conn, cur
            conn.commit()
        finally:
            cur.close()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def clamp_limit(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))


def init_db():
    if not DATABASE_URL:
        return
    try:
        with get_db_cursor() as (conn, cur):
            # Table des clés API
            cur.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    api_key VARCHAR PRIMARY KEY,
                    customer_email VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                INSERT INTO api_keys (api_key, customer_email)
                VALUES ('premium_subscriber_key_49usd', 'demo@admin.com')
                ON CONFLICT (api_key) DO NOTHING
            """)

            # Table des menaces OSINT
            cur.execute("""
                CREATE TABLE IF NOT EXISTS threat_intelligence (
                    id SERIAL PRIMARY KEY,
                    ip VARCHAR NOT NULL UNIQUE,
                    threat_description VARCHAR NOT NULL,
                    confidence FLOAT NOT NULL,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Insertion des données par défaut si la table est vide
            cur.execute("SELECT COUNT(*) FROM threat_intelligence")
            count = cur.fetchone()[0]
            if count == 0:
                for threat in blocked_ips_db:
                    cur.execute("""
                        INSERT INTO threat_intelligence (ip, threat_description, confidence)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (ip) DO NOTHING
                    """, (threat["ip"], threat["threat"], threat["confidence"]))

            # Table des domaines malveillants
            cur.execute("""
                CREATE TABLE IF NOT EXISTS domain_intelligence (
                    id SERIAL PRIMARY KEY,
                    domain VARCHAR NOT NULL UNIQUE,
                    threat_description VARCHAR NOT NULL,
                    confidence FLOAT NOT NULL,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Insertion des domaines par défaut
            cur.execute("SELECT COUNT(*) FROM domain_intelligence")
            d_count = cur.fetchone()[0]
            if d_count == 0:
                for threat in blocked_domains_db:
                    cur.execute("""
                        INSERT INTO domain_intelligence (domain, threat_description, confidence)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (domain) DO NOTHING
                    """, (threat["domain"], threat["threat"], threat["confidence"]))

        logger.info("Supabase initialisé avec succès (api_keys, ips, domaines) !")
    except Exception:
        logger.exception("Impossible d'initialiser la base de données Supabase")


@app.on_event("startup")
def startup_event():
    init_db()


@app.on_event("shutdown")
def shutdown_event():
    if _db_pool is not None:
        _db_pool.closeall()


@app.get("/health")
def health_check():
    """Endpoint leger pour les sondes de disponibilite (Render, uptime monitors)."""
    return {"status": "ok", "database": bool(DATABASE_URL)}


def send_api_key_email(recipient_email: str, api_key: str):
    """ Envoie la clé API par email au client en utilisant l'API HTTP de Brevo """
    if not BREVO_API_KEY:
        logger.warning("BREVO_API_KEY n'est pas configurée : email non envoyé à %s", recipient_email)
        return

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    html_email = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f5; padding: 40px; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h2 style="color: #0ea5e9; text-align: center;">Bienvenue sur OSINT ThreatFeed</h2>
            <p>Bonjour !</p>
            <p>Merci pour votre confiance. Votre accès à l'intelligence artificielle OSIRIS est désormais activé.</p>

            <div style="background-color: #0f172a; color: #38bdf8; padding: 20px; border-radius: 6px; text-align: center; margin: 30px 0; font-family: monospace; font-size: 18px;">
                <strong>{api_key}</strong>
            </div>

            <h3>Comment démarrer ?</h3>
            <ol style="line-height: 1.6;">
                <li>Utilisez cette clé dans le header <code>x-api-key</code> de vos requêtes HTTP.</li>
                <li>Accédez au flux en temps réel sur <code>/api/v1/threats/ips</code>.</li>
                <li>Consultez la documentation OpenAPI sur <code>/docs</code>.</li>
            </ol>

            <p style="margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px; font-size: 12px; color: #999; text-align: center;">
                Ce message a été généré automatiquement. Conservez votre clé API en toute sécurité.
            </p>
        </div>
    </body>
    </html>
    """

    payload = {
        "sender": {"name": "OSINT ThreatFeed", "email": EMAIL_SENDER},
        "to": [{"email": recipient_email}],
        "subject": "🚀 Votre clé API OSINT ThreatFeed est prête !",
        "htmlContent": html_email
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info("Email envoyé via Brevo avec succès à %s", recipient_email)
    except Exception as e:
        logger.error("Erreur lors de l'envoi via Brevo: %s", e)
        if hasattr(e, "response") and getattr(e, "response") is not None:
            logger.error("Détails Brevo: %s", e.response.text)


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        # Echec ferme par defaut : sans signature valide, aucune cle API n'est generee.
        if not ALLOW_UNVERIFIED_STRIPE_WEBHOOK:
            raise HTTPException(status_code=400, detail="Invalid signature")
        logger.warning(
            "Signature Stripe non verifiee acceptee car ALLOW_UNVERIFIED_STRIPE_WEBHOOK=1. "
            "A n'utiliser qu'en local."
        )
        event = {"type": "checkout.session.completed", "data": {"object": {"payment_link": OSINT_PAYMENT_LINK_ID, "customer_details": {"email": "contact@startup.com"}}}}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        session_dict = session.to_dict() if hasattr(session, "to_dict") else session
        if session_dict.get("payment_link") != OSINT_PAYMENT_LINK_ID:
            logger.info("Paiement ignore : lien %s hors OSINT", session_dict.get("payment_link"))
            return {"status": "ignored"}

        customer_email = session_dict.get("customer_details", {}).get("email", "unknown@email.com")

        # 1. Génération de la clé API
        new_api_key = "osint_live_" + secrets.token_hex(16)

        # 2. Sauvegarde de la clé dans Supabase
        if DATABASE_URL:
            try:
                with get_db_cursor() as (conn, cur):
                    cur.execute(
                        "INSERT INTO api_keys (api_key, customer_email) VALUES (%s, %s)",
                        (new_api_key, customer_email)
                    )
                logger.info("[TIROIR-CAISSE] Clé sauvegardée à vie pour %s !", customer_email)
            except Exception:
                logger.exception("Erreur sauvegarde clé API")
                VALID_API_KEYS[new_api_key] = customer_email
        else:
            VALID_API_KEYS[new_api_key] = customer_email

        logger.info("[TIROIR-CAISSE] Nouveau paiement de %s ! Clé générée: %s", customer_email, new_api_key)

        # 3. Envoi de l'email automatique via Brevo
        send_api_key_email(customer_email, new_api_key)

    return {"status": "success"}


def verify_stripe_subscription(x_api_key: str = Header(...)):
    if DATABASE_URL:
        try:
            with get_db_cursor() as (conn, cur):
                cur.execute("SELECT customer_email FROM api_keys WHERE api_key = %s", (x_api_key,))
                row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=403, detail="Abonnement inactif ou clé API invalide.")
            return row[0]
        except HTTPException:
            raise
        except Exception:
            logger.exception("Erreur lors de la vérification de la clé API")
            raise HTTPException(status_code=500, detail="Erreur interne de la base de données")
    else:
        if x_api_key not in VALID_API_KEYS:
            raise HTTPException(status_code=403, detail="Abonnement inactif ou clé API invalide.")
        return VALID_API_KEYS[x_api_key]


ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")


def verify_admin_key(x_admin_key: str = Header(...)):
    if not ADMIN_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Endpoints admin désactivés : la variable ADMIN_API_KEY n'est pas configurée.",
        )
    if not secrets.compare_digest(x_admin_key, ADMIN_API_KEY):
        raise HTTPException(status_code=403, detail="Accès admin refusé.")
    return True


def _fetch_intel(table: str, id_col: str, memory_fallback: list, source_label: str,
                  min_confidence: float, limit: int):
    """Factorise la logique commune (DB -> fallback mémoire) des endpoints threats/domains."""
    limit = clamp_limit(limit)
    if DATABASE_URL:
        try:
            with get_db_cursor(dict_cursor=True) as (conn, cur):
                cur.execute(
                    f"SELECT {id_col}, threat_description as threat, confidence, detected_at "
                    f"FROM {table} WHERE confidence >= %s ORDER BY detected_at DESC LIMIT %s",
                    (min_confidence, limit)
                )
                rows = cur.fetchall()
            return {"status": "success", "source": f"{source_label} (Supabase)", "count": len(rows), "data": rows}
        except Exception:
            logger.exception("Erreur DB sur %s, bascule en fallback mémoire", table)
            return {"status": "success", "source": f"{source_label} (Fallback Mém)", "data": memory_fallback}

    filtered_db = [t for t in memory_fallback if t["confidence"] >= min_confidence][:limit]
    return {"status": "success", "source": f"{source_label} (Mémoire)", "count": len(filtered_db), "data": filtered_db}


@app.get("/api/v1/threats/ips", dependencies=[Depends(verify_stripe_subscription)])
@limiter.limit("60/minute")  # Limite augmentée suite à l'optimisation
def get_threat_ips(request: Request, limit: int = DEFAULT_LIMIT, min_confidence: float = 0.0):
    """
    Récupère les menaces.
    Filtres disponibles : limit (défaut 100, max 1000), min_confidence (ex: 0.90)
    """
    return _fetch_intel("threat_intelligence", "ip", blocked_ips_db, "OSIRIS AI", min_confidence, limit)


@app.get("/api/v1/threats/export", dependencies=[Depends(verify_stripe_subscription)])
@limiter.limit("10/minute")
def export_threats_firewall(request: Request, min_confidence: float = 0.0):
    """
    Export des adresses IP au format texte brut (CSV) pour intégration directe
    dans les pare-feux (Palo Alto, Fortinet, pfSense).
    """
    csv_content = "# OSINT ThreatFeed - Export Auto-généré\n# Format : IP\n"
    if DATABASE_URL:
        try:
            with get_db_cursor() as (conn, cur):
                cur.execute(
                    "SELECT ip FROM threat_intelligence WHERE confidence >= %s ORDER BY detected_at DESC",
                    (min_confidence,)
                )
                rows = cur.fetchall()
            for r in rows:
                csv_content += f"{r[0]}\n"
            return PlainTextResponse(content=csv_content)
        except Exception:
            logger.exception("Erreur DB lors de l'export CSV, bascule en fallback mémoire")

    # Fallback mémoire
    for t in blocked_ips_db:
        if t["confidence"] >= min_confidence:
            csv_content += f"{t['ip']}\n"
    return PlainTextResponse(content=csv_content)


@app.get("/api/v1/threats/domains", dependencies=[Depends(verify_stripe_subscription)])
@limiter.limit("60/minute")
def get_threat_domains(request: Request, limit: int = DEFAULT_LIMIT, min_confidence: float = 0.0):
    """
    Récupère les Noms de Domaines malveillants (Phishing, Ransomware).
    Filtres disponibles : limit (défaut 100, max 1000), min_confidence (ex: 0.90)
    """
    return _fetch_intel("domain_intelligence", "domain", blocked_domains_db, "OSIRIS AI", min_confidence, limit)


class ThreatIn(BaseModel):
    ip: str
    threat_description: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, value: str) -> str:
        try:
            ip_address(value)
        except ValueError as exc:
            raise ValueError("Adresse IP invalide") from exc
        return value


class DomainIn(BaseModel):
    domain: str = Field(min_length=1, max_length=253, pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")
    threat_description: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)


@app.post("/api/v1/admin/threats", dependencies=[Depends(verify_admin_key)])
def inject_new_threat(payload: ThreatIn):
    """
    [ADMIN] Injecte une nouvelle menace en base de données sans redémarrer le serveur.
    """
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="Base de données non configurée.")

    try:
        with get_db_cursor() as (conn, cur):
            cur.execute("""
                INSERT INTO threat_intelligence (ip, threat_description, confidence)
                VALUES (%s, %s, %s)
                ON CONFLICT (ip) DO UPDATE SET confidence = EXCLUDED.confidence, detected_at = CURRENT_TIMESTAMP
            """, (payload.ip, payload.threat_description, payload.confidence))
        return {"status": "success", "message": f"Menace {payload.ip} injectée avec succès."}
    except Exception:
        logger.exception("Erreur lors de l'insertion d'une menace IP")
        raise HTTPException(status_code=500, detail="Erreur lors de l'insertion.")


@app.post("/api/v1/admin/domains", dependencies=[Depends(verify_admin_key)])
def inject_new_domain(payload: DomainIn):
    """
    [ADMIN] Injecte un nom de domaine malveillant en base de données.
    """
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="Base de données non configurée.")

    try:
        with get_db_cursor() as (conn, cur):
            cur.execute("""
                INSERT INTO domain_intelligence (domain, threat_description, confidence)
                VALUES (%s, %s, %s)
                ON CONFLICT (domain) DO UPDATE SET confidence = EXCLUDED.confidence, detected_at = CURRENT_TIMESTAMP
            """, (payload.domain, payload.threat_description, payload.confidence))
        return {"status": "success", "message": f"Domaine {payload.domain} injecté avec succès."}
    except Exception:
        logger.exception("Erreur lors de l'insertion d'un domaine")
        raise HTTPException(status_code=500, detail="Erreur lors de l'insertion.")


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


@app.get("/api/v1/track")
@limiter.limit("30/minute")
def track_visit(request: Request, page: str = "Unknown"):
    """
    Notifie une visite en direct via Telegram. Silencieux si le bot n'est pas configure.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"status": "ok"}

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": f"Nouvelle visite en direct sur : {page}"},
            timeout=2,
        )
    except Exception as e:
        logger.warning("Erreur notification Telegram: %s", e)

    return {"status": "ok"}
