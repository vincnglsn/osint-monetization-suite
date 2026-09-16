import os
import stripe
import secrets
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

# Clés Stripe chargées depuis l'environnement Render (Sécurité)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_dummy")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_dummy")

# Base de données en mémoire pour le MVP (les clés valides)
# On garde la clé de démo pour que le Dashboard actuel continue de fonctionner
VALID_API_KEYS = {
    "premium_subscriber_key_49usd": "demo@admin.com"
}

blocked_ips_db = [
    {"ip": "192.168.1.100", "threat": "Port Scanning automatisé (22, 443)", "confidence": 0.95},
    {"ip": "45.33.12.9", "threat": "Anomalie relais Malacca Strait", "confidence": 0.88},
    {"ip": "203.0.113.42", "threat": "Attaque DDoS (Live !)", "confidence": 0.99}
]

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
        # On ignore l'erreur de signature en mode test local, mais on bloque en prod
        if STRIPE_WEBHOOK_SECRET != "whsec_dummy":
            raise HTTPException(status_code=400, detail="Invalid signature")
        event = {"type": "checkout.session.completed", "data": {"object": {"customer_details": {"email": "nouveau@client.com"}}}}

    # Si le paiement est réussi
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        
        # FIX: Stripe retourne un StripeObject, on doit le convertir en dictionnaire classique
        session_dict = session.to_dict() if hasattr(session, "to_dict") else session
        customer_email = session_dict.get("customer_details", {}).get("email", "unknown@email.com")
        
        # 1. On génère une clé API unique et sécurisée pour le client
        new_api_key = "osint_live_" + secrets.token_hex(16)
        
        # 2. On l'ajoute à notre base de clients payants
        VALID_API_KEYS[new_api_key] = customer_email
        
        # 3. Dans la vraie vie, on utiliserait un service email pour envoyer la clé au client ici
        print(f"[TIROIR-CAISSE] 💰 NOUVEAU PAIEMENT DE {customer_email} ! Clé générée: {new_api_key}")

    return {"status": "success"}


def verify_stripe_subscription(x_api_key: str = Header(...)):
    """ Vérifie si la clé envoyée par le client existe bien dans notre base de données """
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=403, detail="Abonnement inactif ou clé API invalide.")
    # Retourne l'email du client pour les logs
    return VALID_API_KEYS[x_api_key]


@app.get("/api/v1/threats/ips", dependencies=[Depends(verify_stripe_subscription)])
def get_threat_ips():
    return {"status": "success", "source": "OSIRIS AI", "data": blocked_ips_db}
