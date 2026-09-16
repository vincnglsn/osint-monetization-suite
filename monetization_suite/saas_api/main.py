from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="OSINT ThreatFeed API (Premium)", version="1.0.0")

# Configuration CORS pour permettre au Dashboard local de communiquer avec l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base de données mock des IPs bloquées
blocked_ips_db = [
    {"ip": "192.168.1.100", "threat": "Port Scanning automatisé (22, 443)", "confidence": 0.95},
    {"ip": "45.33.12.9", "threat": "Anomalie relais Malacca Strait", "confidence": 0.88},
    {"ip": "203.0.113.42", "threat": "Attaque DDoS (Live !)", "confidence": 0.99}
]

def verify_stripe_subscription(x_api_key: str = Header(...)):
    if x_api_key != "premium_subscriber_key_49usd":
        raise HTTPException(status_code=403, detail="Abonnement Stripe inactif ou clé invalide.")
    return True

@app.get("/api/v1/threats/ips", dependencies=[Depends(verify_stripe_subscription)])
def get_threat_ips():
    return {"status": "success", "source": "OSIRIS AI", "data": blocked_ips_db}
