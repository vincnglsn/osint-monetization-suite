import sys
import os
import time

# Ajout des sous-dossiers au path pour faciliter les imports depuis ce point d'entrée
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading.algo_trader import AlpacaTrader
from newsletter.publisher import NewsletterPublisher

# Mock d'une alerte provenant de convergence_analyzer.py
mock_alert = {
    "risk_level": "Critique",
    "primary_threat": "Congestion maritime doublée d'une vague de scans de ports ciblés",
    "impacted_sector": "Semi-conducteurs",
    "executive_summary": "Blocage asymétrique détecté en Asie du Sud-Est (Malacca).",
    "recommended_action": "Activer les WAF de niveau 3 sur les sous-réseaux cloud asiatiques."
}

def main():
    print("="*65)
    print(" 🚀 LANCEMENT DE LA SUITE DE MONÉTISATION OSINT (ORCHESTRATEUR)")
    print("="*65)
    time.sleep(1)

    print("\n--- [1] MODULE DE TRADING ALGORITHMIQUE ---")
    trader = AlpacaTrader()
    trader.process_alert(mock_alert)
    time.sleep(1)

    print("\n--- [2] MODULE DE CONTENU PREMIUM (NEWSLETTER) ---")
    pub = NewsletterPublisher()
    pub.generate_and_publish(mock_alert)
    time.sleep(1)

    print("\n--- [3] MODULE SAAS (THREATFEED API) ---")
    print("[SaaS API] L'API est prête à servir les clients Premium.")
    print("👉 Pour démarrer le serveur de l'API et commencer à encaisser (Stripe), exécutez dans un terminal :")
    print(r"    .\.venv\Scripts\uvicorn monetization_suite.saas_api.main:app --reload")
    print("="*65)

if __name__ == "__main__":
    main()
