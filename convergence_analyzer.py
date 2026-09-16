import os
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# 1. Simulation des flux de données (Croisement de sources)
MACRO_DATA = [
    "WORLD MONITOR ALERT: Congestion majeure signalée dans le détroit de Malacca.",
    "MARKET NEWS: Les actions des fondeurs de semi-conducteurs chutent de 4% en raison de craintes sur la logistique asiatique."
]

MICRO_DATA = [
    {"type": "ais_dark_ship", "vessel_type": "Cargo", "last_known_loc": "Port de Singapour", "status": "Signal perdu depuis 12h"},
    {"type": "ais_dark_ship", "vessel_type": "Cargo", "last_known_loc": "Détroit de Malacca", "status": "Signal perdu depuis 8h"},
    {"type": "cctv_analysis", "location": "Terminal de fret de Singapour", "observation": "Accumulation anormale de conteneurs, grues inactives. Activité réduite de 40% par rapport à la normale."}
]

# 2. Définition du format de sortie structuré avec Pydantic (Structured Outputs)
class ConvergenceAlert(BaseModel):
    risk_level: str = Field(description="Niveau de risque global (Faible, Moyen, Critique)")
    primary_threat: str = Field(description="La menace principale identifiée en croisant les données")
    impacted_sector: str = Field(description="Le secteur industriel le plus directement impacté")
    executive_summary: str = Field(description="Résumé analytique de la situation (2 phrases maximum)")
    recommended_action: str = Field(description="Action immédiate recommandée pour le gestionnaire logistique")

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("\n[ERREUR] La variable d'environnement GEMINI_API_KEY n'est pas définie.")
        print("Veuillez exécuter: $env:GEMINI_API_KEY=\"votre_cle_ici\" avant de lancer le script.\n")
        return

    print("\n[1/3] Initialisation de l'analyseur de convergence...")
    client = genai.Client(api_key=api_key)

    prompt = f"""
    En tant qu'analyste de renseignement OSINT, analysez ces données croisées :

    DONNÉES MACRO (World Monitor) :
    {json.dumps(MACRO_DATA, indent=2)}

    DONNÉES MICRO / OSINT (OSIRIS AI) :
    {json.dumps(MICRO_DATA, indent=2)}

    Déduisez la situation globale, l'impact sur la chaîne d'approvisionnement, et générez une alerte structurée de niveau professionnel.
    """

    print("[2/3] Envoi des données (Macro + Micro) à l'IA (Gemini 2.5 Flash) pour analyse...")
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ConvergenceAlert,
                temperature=0.2
            ),
        )

        print("[3/3] Analyse terminée avec succès.\n")
        print("="*50)
        print(" ALERTE DE CONVERGENCE GÉNÉRÉE ")
        print("="*50)
        
        # Affichage propre du JSON renvoyé par le modèle
        alert_json = json.loads(response.text)
        print(json.dumps(alert_json, indent=2, ensure_ascii=False))
        print("="*50 + "\n")

    except Exception as e:
        print(f"\n[ERREUR] L'API a renvoyé une erreur : {e}")

if __name__ == "__main__":
    main()
