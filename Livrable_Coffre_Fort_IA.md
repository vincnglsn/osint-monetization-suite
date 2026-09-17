# 🔐 LE COFFRE-FORT DE L'AGENCE IA 2026
**Document strictement confidentiel - Réservé aux acheteurs de la licence.**

Félicitations pour votre investissement. Ce document contient le cœur de votre future agence IA. Ne partagez pas ces informations publiquement.

---

## 📂 1. LES TEMPLATES NOTION (Liens de duplication)
*Cliquez sur les liens ci-dessous, connectez-vous à votre compte Notion, et cliquez sur "Dupliquer" en haut à droite.*

- **Le CRM Client (Suivi des prospects) :** `https://notion.so/template-crm-agence-ia-secret-link`
- **Le Contrat de Prestation de Service (Modèle Juridique) :** `https://notion.so/template-contrat-ia-secret-link`
- **L'Audit Client (Questions de découverte) :** `https://notion.so/template-audit-secret-link`

---

## 🤖 2. LES 5 MEILLEURS PROMPTS "MEGA-CONTEXT"

### Prompt A : L'Audit SEO / Copywriting pour un client E-commerce
*À utiliser sur ChatGPT (GPT-4) ou Claude 3.*
> "Agis comme un expert en CRO (Conversion Rate Optimization) et en Copywriting B2B. Je vais te fournir le texte de la page d'accueil de mon client. Ton objectif est d'analyser le taux de rebond potentiel et de me réécrire le H1, les 3 sous-titres, et le Call-to-Action en utilisant le framework AIDA. Justifie chaque choix psychologique."

### Prompt B : Le Créateur d'Automatisations Make/Zapier
> "Je dois créer une automatisation sur Make.com pour un client. Voici les outils qu'il utilise : [OUTIL 1], [OUTIL 2]. Son objectif est de [OBJECTIF]. Rédige-moi le plan étape par étape de l'automatisation, les modules exacts à utiliser, et le code JSON pour les webhooks si nécessaire."

### Prompt C : Le Générateur d'Emails de Prospection (Cold Email)
> "Agis comme un copywriter de classe mondiale spécialisé dans le B2B. Rédige une séquence de 3 emails à froid pour prospecter des [CIBLE]. Le service que je vends est [SERVICE]. Les emails doivent faire moins de 100 mots, utiliser la psychologie inversée, et se terminer par un CTA à faible friction. Le ton doit être direct et non vendeur."

*(... Les 47 autres prompts sont inclus dans le fichier complet PDF)*

---

## 🐍 3. LES SCRIPTS PYTHON (Automatisation)

### Script 1 : L'Extracteur d'Emails sur les sites web (Scraping)
*Installez `beautifulsoup4` et `requests` avant de lancer le script.*

```python
import requests
from bs4 import BeautifulSoup
import re

def scrape_emails(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        emails = set(re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", text, re.I))
        return list(emails)
    except:
        return []

print(scrape_emails("https://www.site-du-client.com"))
```

### Script 2 : L'Auto-Enrichisseur de Leads
*Code source confidentiel pour nettoyer et vérifier la validité des adresses emails...*

---

## 📈 4. STRATÉGIE D'ACQUISITION (0 à 10k€/mois)

**Semaine 1 : Le positionnement**
Ne vendez pas "de l'Intelligence Artificielle". Personne n'achète de l'IA. 
Vendez : "Je réduis votre temps de traitement client de 4h à 15 minutes", ou "J'augmente vos marges de 20% en automatisant votre SAV". L'IA n'est que l'outil.

**Semaine 2 : L'Outbound**
Envoyez 50 emails par jour en utilisant le *Prompt C* ci-dessus. N'essayez pas de vendre dans le premier email, cherchez uniquement à obtenir un rendez-vous (Call) de 15 minutes.

**Semaine 3 : Le Closing**
Utilisez le "Template Notion d'Audit Client" pendant votre appel. Ne parlez pas de technique, demandez-lui combien lui coûte son problème actuel. Proposez votre solution d'automatisation IA à un prix équivalent à 10% de ce qu'il perd aujourd'hui.

---
*Fin du document. Merci de votre confiance.*
