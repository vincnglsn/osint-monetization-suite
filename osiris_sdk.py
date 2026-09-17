import urllib.request
import json

class OsirisClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://osint-monetization-suite.onrender.com/api/v1"

    def _fetch(self, endpoint, min_confidence=0.0):
        url = f"{self.base_url}{endpoint}?min_confidence={min_confidence}"
        req = urllib.request.Request(url, headers={"x-api-key": self.api_key})
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 403:
                raise Exception("Abonnement inactif ou clé API invalide.")
            raise Exception(f"Erreur API: {e.code}")

    def get_malicious_ips(self, min_confidence=0.80):
        """Récupère les IPs dangereuses avec un score de confiance minimum."""
        return self._fetch("/threats/ips", min_confidence)

    def get_malicious_domains(self, min_confidence=0.80):
        """Récupère les domaines malveillants (Phishing, C2)."""
        return self._fetch("/threats/domains", min_confidence)

    def export_firewall_rules(self, min_confidence=0.0):
        """Exporte les IPs au format texte brut pour iptables, pfSense, etc."""
        url = f"{self.base_url}/threats/export?min_confidence={min_confidence}"
        req = urllib.request.Request(url, headers={"x-api-key": self.api_key})
        with urllib.request.urlopen(req) as response:
            return response.read().decode()

if __name__ == "__main__":
    # Test d'intégration rapide
    client = OsirisClient("premium_subscriber_key_49usd")
    print("🛡️ Connexion à OSIRIS AI...")
    
    ips = client.get_malicious_ips(0.90)
    print(f"✅ {ips['count']} IPs hautement dangereuses détectées.")
    
    rules = client.export_firewall_rules(0.95)
    print("\n--- RÈGLES PARE-FEU PRÊTES À L'EMPLOI ---")
    print(rules[:150] + "...\n---------------------------------------")
