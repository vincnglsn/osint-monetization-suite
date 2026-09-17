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

    def get_threats(self, limit: int = 100, min_confidence: float = 0.0):
        """
        Récupère la liste des dernières menaces OSINT identifiées.
        Possibilité de filtrer par limite et par indice de confiance minimum.
        """
        url = f"{self.base_url}/threats/ips"
        params = {
            "limit": limit,
            "min_confidence": min_confidence
        }
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            if response.status_code == 403:
                raise Exception("Accès refusé : Clé API invalide ou abonnement inactif.")
            elif response.status_code == 429:
                raise Exception("Rate Limit dépassé : Vous avez effectué trop de requêtes.")
            else:
                raise Exception(f"Erreur HTTP: {err}")

    def export_firewall_rules(self, min_confidence: float = 0.0):
        """
        Télécharge la liste brute des IP (format texte/CSV) prête à être injectée
        dans un firewall matériel (ex: Palo Alto, pfSense).
        """
        url = f"{self.base_url}/threats/export"
        params = {"min_confidence": min_confidence}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.text
        except requests.exceptions.HTTPError as err:
            raise Exception(f"Erreur d'exportation HTTP: {err}")

    def get_threat_domains(self, limit: int = 100, min_confidence: float = 0.0):
        """
        Récupère la liste des domaines malveillants (Phishing, Ransomwares).
        Possibilité de filtrer par limite et par indice de confiance minimum.
        """
        url = f"{self.base_url}/threats/domains"
        params = {
            "limit": limit,
            "min_confidence": min_confidence
        }
        try:
            response = requests.get(url, headers=self.headers, params=params)
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
        print("Recuperation des donnees (Filtre: min_confidence=0.90, max 5)...")
        data = client.get_threats(limit=5, min_confidence=0.90)
        
        print("\n[SUCCES] Connexion reussie !")
        print(f"Source des donnees : {data.get('source')}")
        print(f"Total renvoye : {data.get('count', len(data.get('data', [])))}\n")
        
        threats = data.get("data", [])
        for t in threats:
            print(f" - IP: {t.get('ip')} | Menace: {t.get('threat')} | Confiance: {t.get('confidence')}")
            
    except Exception as e:
        print(f"[ERREUR] : {e}")
