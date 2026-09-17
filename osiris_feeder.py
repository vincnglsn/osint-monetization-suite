import time
import requests
import random
from datetime import datetime

# ==========================================
# OSIRIS AI - MOTEUR D'INGESTION OSINT
# ==========================================
# Ce script tourne sur votre machine (ou un cron) et alimente votre SaaS en données fraîches.
# Il se connecte à votre endpoint Admin privé pour injecter les menaces.

# Remplacez par l'URL de votre serveur Render et votre clé admin
API_BASE_URL = "https://osint-monetization-suite.onrender.com/api/v1"
ADMIN_API_KEY = "super_secret_admin_osiris_2026"

def generate_simulated_threat():
    """Génère une menace OSINT hautement réaliste (Simulation OSIRIS AI)"""
    ip = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    threats = [
        "C2 Cobalt Strike détecté (Port 443)",
        "Botnet Mirai Variant - Scan Telnet/SSH",
        "Extraction de données Cloud (AWS S3 Bucket Bruteforce)",
        "Anomalie BGP - Détournement de route AS" + str(random.randint(1000, 9999)),
        "Serveur VPN Compromis (Vulnérabilité CVE-2026-X)",
        "Infrastructure Ransomware LockBit (Nœud de paiement)"
    ]
    return {
        "ip": ip,
        "threat_description": random.choice(threats),
        "confidence": round(random.uniform(0.75, 0.99), 2)
    }

def push_threat_to_saas(threat_data):
    """Envoie la menace directement dans la base de données du SaaS via l'API Admin"""
    url = f"{API_BASE_URL}/admin/threats"
    headers = {
        "x-admin-key": ADMIN_API_KEY
    }
    
    try:
        response = requests.post(url, headers=headers, params=threat_data)
        if response.status_code == 200:
            print(f"[+] INJECTÉ : {threat_data['ip']} ({threat_data['threat_description']}) - Confiance: {threat_data['confidence']}")
        else:
            print(f"[!] ERREUR API : {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[X] ERREUR RÉSEAU : {e}")

if __name__ == "__main__":
    print("="*50)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] DÉMARRAGE DU FEEDER OSIRIS AI")
    print("="*50)
    
    # Simulation d'une boucle d'ingestion continue (ex: 5 menaces pour le test)
    for _ in range(5):
        new_threat = generate_simulated_threat()
        push_threat_to_saas(new_threat)
        time.sleep(1.5) # Pause pour ne pas surcharger le réseau
        
    print("\n✅ Ingestion terminée. La base de données de vos clients est à jour !")
