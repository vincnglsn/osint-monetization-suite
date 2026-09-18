import os
import stripe
import secrets
import psycopg2
import requests
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from psycopg2.extras import RealDictCursor
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialisation du Limiter (basé sur l'IP du visiteur)
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="OSINT ThreatFeed API", description="API de monétisation des flux OSINT")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configuration CORS pour autoriser le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Clés d'environnement
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_dummy")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Configuration Email
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "contact@osint-saas.com")
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")

# Base de données en mémoire de secours
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

def init_db():
    if not DATABASE_URL:
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
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

        conn.commit()
        cur.close()
        conn.close()
        print("[DATABASE] Supabase initialisé avec succès (api_keys, ips, domaines) !")
    except Exception as e:
        print(f"[DATABASE ERROR] Impossible de se connecter à Supabase: {e}")

@app.on_event("startup")
def startup_event():
    init_db()


def send_api_key_email(recipient_email: str, api_key: str):
    """ Envoie la clé API par email au client en utilisant l'API HTTP de Brevo """
    if not BREVO_API_KEY:
        print("[EMAIL] La variable BREVO_API_KEY n'est pas configurée sur Render.")
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
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"[EMAIL] 🚀 Email envoyé via Brevo avec succès à {recipient_email} !")
    except Exception as e:
        print(f"[EMAIL ERROR] Erreur lors de l'envoi via Brevo: {e}")
        if hasattr(e, 'response') and getattr(e, 'response') is not None:
            print(f"[EMAIL ERROR DETAILS] {e.response.text}")


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        if STRIPE_WEBHOOK_SECRET != "whsec_dummy":
            raise HTTPException(status_code=400, detail="Invalid signature")
        event = {"type": "checkout.session.completed", "data": {"object": {"customer_details": {"email": "contact@startup.com"}}}}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        
        session_dict = session.to_dict() if hasattr(session, "to_dict") else session
        customer_email = session_dict.get("customer_details", {}).get("email", "unknown@email.com")
        
        # 1. Génération de la clé API
        new_api_key = "osint_live_" + secrets.token_hex(16)
        
        # 2. Sauvegarde de la clé dans Supabase
        if DATABASE_URL:
            try:
                conn = psycopg2.connect(DATABASE_URL)
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO api_keys (api_key, customer_email) VALUES (%s, %s)",
                    (new_api_key, customer_email)
                )
                conn.commit()
                cur.close()
                conn.close()
                print(f"[TIROIR-CAISSE] 💰 [SUPABASE] Clé sauvegardée à vie pour {customer_email} !")
            except Exception as e:
                print(f"[DATABASE ERROR] Erreur sauvegarde clé: {e}")
                VALID_API_KEYS[new_api_key] = customer_email
        else:
            VALID_API_KEYS[new_api_key] = customer_email
        
        print(f"[TIROIR-CAISSE] 💰 NOUVEAU PAIEMENT DE {customer_email} ! Clé générée: {new_api_key}")
        
        # 3. Envoi de l'email automatique via Brevo
        send_api_key_email(customer_email, new_api_key)

    return {"status": "success"}

def verify_stripe_subscription(x_api_key: str = Header(...)):
    if DATABASE_URL:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            cur.execute("SELECT customer_email FROM api_keys WHERE api_key = %s", (x_api_key,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            
            if not row:
                raise HTTPException(status_code=403, detail="Abonnement inactif ou clé API invalide.")
            return row[0]
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            print(f"[DATABASE ERROR] {e}")
            raise HTTPException(status_code=500, detail="Erreur interne de la base de données")
    else:
        if x_api_key not in VALID_API_KEYS:
            raise HTTPException(status_code=403, detail="Abonnement inactif ou clé API invalide.")
        return VALID_API_KEYS[x_api_key]

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "super_secret_admin_osiris_2026")

def verify_admin_key(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Accès admin refusé.")
    return True

@app.get("/api/v1/threats/ips", dependencies=[Depends(verify_stripe_subscription)])
@limiter.limit("60/minute")  # Limite augmentée suite à l'optimisation
def get_threat_ips(request: Request, limit: int = 100, min_confidence: float = 0.0):
    """
    Récupère les menaces.
    Filtres disponibles : limit (défaut 100), min_confidence (ex: 0.90)
    """
    if DATABASE_URL:
        try:
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            cur = conn.cursor()
            cur.execute(
                "SELECT ip, threat_description as threat, confidence, detected_at FROM threat_intelligence WHERE confidence >= %s ORDER BY detected_at DESC LIMIT %s",
                (min_confidence, limit)
            )
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return {"status": "success", "source": "OSIRIS AI (Supabase)", "count": len(rows), "data": rows}
        except Exception as e:
            print(f"[DATABASE ERROR] {e}")
            return {"status": "success", "source": "OSIRIS AI (Fallback Mém)", "data": blocked_ips_db}
    
    # Fallback mémoire
    filtered_db = [t for t in blocked_ips_db if t["confidence"] >= min_confidence][:limit]
    return {"status": "success", "source": "OSIRIS AI (Mémoire)", "count": len(filtered_db), "data": filtered_db}

@app.get("/api/v1/threats/export", dependencies=[Depends(verify_stripe_subscription)])
@limiter.limit("10/minute")
def export_threats_firewall(request: Request, min_confidence: float = 0.0):
    """
    [NOUVEAU] Export des adresses IP au format texte brut (CSV) pour intégration directe 
    dans les pare-feux (Palo Alto, Fortinet, pfSense).
    """
    csv_content = "# OSINT ThreatFeed - Export Auto-généré\n# Format : IP\n"
    if DATABASE_URL:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            cur.execute("SELECT ip FROM threat_intelligence WHERE confidence >= %s ORDER BY detected_at DESC", (min_confidence,))
            rows = cur.fetchall()
            cur.close()
            conn.close()
            for r in rows:
                csv_content += f"{r[0]}\n"
            return PlainTextResponse(content=csv_content)
        except Exception as e:
            print(f"[DATABASE ERROR] {e}")
    
    # Fallback mémoire
    for t in blocked_ips_db:
        if t["confidence"] >= min_confidence:
            csv_content += f"{t['ip']}\n"
    return PlainTextResponse(content=csv_content)

@app.post("/api/v1/admin/threats", dependencies=[Depends(verify_admin_key)])
def inject_new_threat(request: Request, ip: str, threat_description: str, confidence: float):
    """
    [ADMIN] Injecte une nouvelle menace en base de données sans redémarrer le serveur.
    """
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="Base de données non configurée.")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO threat_intelligence (ip, threat_description, confidence)
            VALUES (%s, %s, %s)
            ON CONFLICT (ip) DO UPDATE SET confidence = EXCLUDED.confidence, detected_at = CURRENT_TIMESTAMP
        """, (ip, threat_description, confidence))
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "success", "message": f"Menace {ip} injectée avec succès."}
    except Exception as e:
        print(f"[DATABASE ERROR] {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'insertion.")

@app.get("/api/v1/threats/domains", dependencies=[Depends(verify_stripe_subscription)])
@limiter.limit("60/minute")
def get_threat_domains(request: Request, limit: int = 100, min_confidence: float = 0.0):
    """
    [NOUVEAU] Récupère les Noms de Domaines malveillants (Phishing, Ransomware).
    """
    if DATABASE_URL:
        try:
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            cur = conn.cursor()
            cur.execute(
                "SELECT domain, threat_description as threat, confidence, detected_at FROM domain_intelligence WHERE confidence >= %s ORDER BY detected_at DESC LIMIT %s",
                (min_confidence, limit)
            )
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return {"status": "success", "source": "OSIRIS AI (Supabase)", "count": len(rows), "data": rows}
        except Exception as e:
            print(f"[DATABASE ERROR] {e}")
            return {"status": "success", "source": "OSIRIS AI (Fallback Mém)", "data": blocked_domains_db}
    
    # Fallback mémoire
    filtered_db = [t for t in blocked_domains_db if t["confidence"] >= min_confidence][:limit]
    return {"status": "success", "source": "OSIRIS AI (Mémoire)", "count": len(filtered_db), "data": filtered_db}

@app.post("/api/v1/admin/domains", dependencies=[Depends(verify_admin_key)])
def inject_new_domain(request: Request, domain: str, threat_description: str, confidence: float):
    """
    [ADMIN] Injecte un nom de domaine malveillant en base de données.
    """
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="Base de données non configurée.")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO domain_intelligence (domain, threat_description, confidence)
            VALUES (%s, %s, %s)
            ON CONFLICT (domain) DO UPDATE SET confidence = EXCLUDED.confidence, detected_at = CURRENT_TIMESTAMP
        """, (domain, threat_description, confidence))
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "success", "message": f"Domaine {domain} injecté avec succès."}
    except Exception as e:
        print(f"[DATABASE ERROR] {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'insertion.")

 i m p o r t   u r l l i b . r e q u e s t 
 @ a p p . g e t ( ' / a p i / v 1 / t r a c k ' ) 
 d e f   t r a c k _ v i s i t ( p a g e :   s t r   =   ' U n k n o w n ' ) : 
         t r y : 
                 t o k e n   =   o s . g e t e n v ( ' T E L E G R A M _ B O T _ T O K E N ' ,   ' 8 9 0 7 7 3 6 8 1 5 : A A H F L m K E g l x f H K 5 S O o X y 9 4 O b b o _ U f y c 3 A P o ' ) 
                 c h a t _ i d   =   o s . g e t e n v ( ' T E L E G R A M _ C H A T _ I D ' ,   ' 6 0 2 0 3 4 2 3 4 4 ' ) 
                 m s g   =   f ' =�@�  N o u v e l l e   v i s i t e   e n   d i r e c t   s u r   :   { p a g e } ' 
                 u r l   =   f ' h t t p s : / / a p i . t e l e g r a m . o r g / b o t { t o k e n } / s e n d M e s s a g e ? c h a t _ i d = { c h a t _ i d } & t e x t = { u r l l i b . p a r s e . q u o t e ( m s g ) } ' 
                 u r l l i b . r e q u e s t . u r l o p e n ( u r l ,   t i m e o u t = 2 ) 
         e x c e p t   E x c e p t i o n   a s   e : 
                 p a s s 
         r e t u r n   { ' s t a t u s ' :   ' o k ' } 
 
 
 
