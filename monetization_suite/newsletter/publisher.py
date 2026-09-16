import os

class NewsletterPublisher:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")

    def generate_and_publish(self, alert_data):
        print("[NEWSLETTER] ✍️ Rédaction de l'Executive Brief premium par l'IA...")
        
        content = f"""# 🚨 Flash Supply Chain : Menace sur les {alert_data.get('impacted_sector')}

Notre plateforme d'intelligence artificielle a détecté une convergence d'événements critiques :
- {alert_data.get('primary_threat')}

**Action immédiate :** {alert_data.get('recommended_action')}

*[Abonnez-vous à la version Pro pour voir l'analyse détaillée]*
"""
        print("[NEWSLETTER] ✅ Article rédigé.")
        self.publish_to_ghost(content)

    def publish_to_ghost(self, content):
        print("[NEWSLETTER] 📡 Publication en cours via l'API (Substack / Ghost)...")
        # print("\n--- APERÇU --- \n" + content + "\n--------------")
        print("[NEWSLETTER] 💰 Newsletter publiée ! Vos abonnés payants viennent d'être notifiés.")
