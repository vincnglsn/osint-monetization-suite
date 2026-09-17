import requests
import json

class OsintThreatFeedClient:
    """
    SDK Python officiel pour interagir avec l'API OSINT ThreatFeed.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Mettre à jour avec l'URL de votre serveur Render en production
        self.base_url = "https://osint-monetization-suite.onrender.com/api/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def get_threats(self):
        """
        Récupère la liste des dernières menaces OSINT identifiées.
        """
        url = f"{self.base_url}/threats/ips"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            if response.status_code == 403:
                raise Exception("Accès refusé : Clé API invalide ou abonnement inactif.")
            elif response.status_code == 429:
                raise Exception("Rate Limit dépassé : Vous avez effectué trop de requêtes.")
            else:
                raise Exception(f"Erreur HTTP: {err}")

if __name__ == "__main__":
    # Exemple d'utilisation
    print("--- Test du SDK OSINT ThreatFeed ---")
    
    # Remplacer par la clé API reçue par e-mail après achat
    CLIENT_API_KEY = "premium_subscriber_key_49usd" 
    
    client = OsintThreatFeedClient(api_key=CLIENT_API_KEY)
    
    try:
        print("Récupération des données en cours...")
        data = client.get_threats()
        
        print("\n✅ Connexion réussie !")
        print(f"Source des données : {data.get('source')}\n")
        
        threats = data.get("data", [])
        print(f"[{len(threats)} menaces détectées] :")
        for t in threats:
            print(f" - IP: {t.get('ip')} | Menace: {t.get('threat')} | Confiance: {t.get('confidence')}")
            
    except Exception as e:
        print(f"❌ Erreur : {e}")
