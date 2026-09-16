import os
import stripe
import secrets
import psycopg2
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="OSINT ThreatFeed API (Premium)", version="1.0.0")

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

# Base de données en mémoire de secours (si Supabase n'est pas configuré)
VALID_API_KEYS = {
    "premium_subscriber_key_49usd": "demo@admin.com"
}

blocked_ips_db = [
    {"ip": "192.168.1.100", "threat": "Port Scanning automatisé (22, 443)", "confidence": 0.95},
    {"ip": "45.33.12.9", "threat": "Anomalie relais Malacca Strait", "confidence": 0.88},
    {"ip": "203.0.113.42", "threat": "Attaque DDoS (Live !)", "confidence": 0.99}
]

def init_db():
    if not DATABASE_URL:
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        # Création de la table si elle n'existe pas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                api_key VARCHAR PRIMARY KEY,
                customer_email VARCHAR NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Injection de la clé démo par défaut
        cur.execute("""
            INSERT INTO api_keys (api_key, customer_email)
            VALUES ('premium_subscriber_key_49usd', 'demo@admin.com')
            ON CONFLICT (api_key) DO NOTHING
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("[DATABASE] Supabase initialisé avec succès !")
    except Exception as e:
        print(f"[DATABASE ERROR] Impossible de se connecter à Supabase: {e}")

@app.on_event("startup")
def startup_event():
    init_db()

@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """ Endpoint appelé par Stripe quand un client paie par carte bleue """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        if STRIPE_WEBHOOK_SECRET != "whsec_dummy":
            raise HTTPException(status_code=400, detail="Invalid signature")
        event = {"type": "checkout.session.completed", "data": {"object": {"customer_details": {"email": "nouveau@client.com"}}}}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        
        session_dict = session.to_dict() if hasattr(session, "to_dict") else session
        customer_email = session_dict.get("customer_details", {}).get("email", "unknown@email.com")
        
        # 1. On génère une clé API unique et sécurisée pour le client
        new_api_key = "osint_live_" + secrets.token_hex(16)
        
        # 2. Sauvegarde de la clé
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
                VALID_API_KEYS[new_api_key] = customer_email # Fallback mémoire
        else:
            VALID_API_KEYS[new_api_key] = customer_email
        
        print(f"[TIROIR-CAISSE] 💰 NOUVEAU PAIEMENT DE {customer_email} ! Clé générée: {new_api_key}")

    return {"status": "success"}


def verify_stripe_subscription(x_api_key: str = Header(...)):
    """ Vérifie si la clé envoyée par le client existe bien dans notre base de données Supabase """
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
        # Fallback si pas de DB
        if x_api_key not in VALID_API_KEYS:
            raise HTTPException(status_code=403, detail="Abonnement inactif ou clé API invalide.")
        return VALID_API_KEYS[x_api_key]


@app.get("/api/v1/threats/ips", dependencies=[Depends(verify_stripe_subscription)])
def get_threat_ips():
    return {"status": "success", "source": "OSIRIS AI", "data": blocked_ips_db}
