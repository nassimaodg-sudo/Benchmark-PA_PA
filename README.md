# PA Selection & Market Intelligence Tool — Streamlit

Port Streamlit du POC Thylios & Associés. Mêmes données réelles (166 PA,
451 points de données, 44 cas d'usage), même moteur de scoring que la
version HTML — aucune donnée inventée.

## Structure du dossier

```
streamlit_app/
├── app.py                  <- l'application
├── requirements.txt        <- dépendances
└── data/
    ├── pa_master.json          (166 PA, registre DGFiP)
    ├── pa_capabilities.json    (451 points de données réels sourcés)
    ├── cas_usage.json          (44 cas d'usage XP Z12-014 V1.4)
    └── weights_by_profile.json (pondérations par archétype)
```

Le dossier `data/` doit rester à côté de `app.py` — l'app lit ces
fichiers au démarrage, rien n'est codé en dur dans le script.

## Tester en local (2 minutes)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Ça ouvre automatiquement `http://localhost:8501` dans votre navigateur.

## Déployer sur Streamlit Community Cloud (gratuit, le plus simple)

1. Créez un dépôt GitHub (public ou privé) et poussez-y tout le contenu
   de ce dossier (`app.py`, `requirements.txt`, `data/`).
2. Allez sur **share.streamlit.io**, connectez-vous avec GitHub.
3. "New app" → sélectionnez le dépôt, la branche, et `app.py` comme
   fichier principal.
4. Déployez. Vous obtenez une URL publique du type
   `https://votre-app.streamlit.app` à partager avec vos collègues —
   plus besoin d'envoyer de fichier, juste le lien.

Chaque push sur la branche déclenche un redéploiement automatique.

## Déployer en interne (si Streamlit Cloud n'est pas envisageable)

L'app est un script Python standard, donc elle tourne sur n'importe
quel serveur qui peut exécuter `streamlit run app.py` en arrière-plan
(VM interne, conteneur Docker, service cloud type Azure App Service /
AWS). Un exemple minimal de `Dockerfile` :

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
```

## Ce qui est couvert dans cette version

Diagnostic (8 questions, priorités multi-choix), résultats avec Fit
Score et badge de confiance, What-If (curseurs de pondération en
direct), fiche PA détaillée (10 blocs sourcés), comparateur, explorateur
des 166 PA, module Cas d'usage.

## Ce qui n'est pas encore porté depuis la version HTML

Gap Analysis, RFI Mode, vues métier (DSI/Fiscal/Achats), Sensitivity
Analysis, export PDF/CSV. La version HTML autonome (`Thylios_Quiz_PA_POC.html`)
reste la version la plus complète si vous n'avez pas besoin d'un lien
web partagé — celle-ci est utile spécifiquement pour un déploiement web.
