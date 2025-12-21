# 🎬 SynthetIA - YouTube Summarizer & Synthesizer

Une application puissante alimentée par l'IA pour **résumer**, **synthétiser** et **analyser** des vidéos YouTube ou des fichiers locaux. 
Utilise **Ollama** (LLM local) et **Whisper** (Transcription) pour garantir confidentialité et performance sans frais d'API.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-App-red) ![Ollama](https://img.shields.io/badge/AI-Ollama-orange) ![Version](https://img.shields.io/badge/Version-2.0-green)

---

## 🚀 Pourquoi cet outil ?

Ne perdez plus de temps à regarder des heures de vidéo pour trouver une information.
*   **Veille Technologique** : Scannez 10 vidéos sur un sujet en 2 minutes.
*   **Études & Recherche** : Synthétisez des conférences ou des cours complexes.
*   **Création de Contenu** : Transformez des vidéos en articles de blog ou posts LinkedIn en un clic.

---

## ✨ Fonctionnalités Clés

### 🔍 1. Recherche & Veille (Moteur Dynamique)
*   **Recherche YouTube intégrée** : Plus besoin de copier-coller des liens.
*   **Filtres Avancés** : Triez par *Date*, *Pertinence*, *Vues* ou filtrez par *Durée*.
*   **Affichage Dynamique** : Grille infinie de résultats avec vignettes intelligentes.

### 📝 2. Synthèse Multi-Sources
Sélectionnez plusieurs vidéos et générez une **synthèse unique** qui compile et structure les informations de toutes les sources.

### 🧠 3. Intelligence Artificielle (Local & Privé)
*   **Transcription** : Whisper (modèle configurable : `base`, `small`, `medium`...)
*   **Analyse** : Ollama (ex: `mistral`, `llama3`)
*   **5 Modes de Résumés** : `Short`, `Medium`, `Long`, `News`, `Meeting`

### 🎨 4. Édition & Raffinement
*   **Éditeur Riche** : Modifiez le texte avec Quill Editor
*   **Refine / Regenerate** : Demandez à l'IA de réécrire selon vos critères
*   **Templates** : Rapport Structuré, Note de Synthèse, Article de Blog, Email Exécutif

---

## 🆕 Nouveautés v2.0

### 📤 Export Multi-Format
- **Word (.docx)** et **PowerPoint (.pptx)** automatique
- Génération de slides avec 1 slide par section H2

### 📂 Gestion de Projets
- **Base SQLite** pour persistance des synthèses
- **Dossiers/Collections** pour organiser par thème
- **Tags colorés** pour retrouver facilement

### 🔬 Analyse & Comparaison
- **Extraction de faits** : Tableau des dates, nombres, noms
- **Comparaison côte à côte** avec score de similarité
- **Détection de contradictions** entre sources

### 🤖 Automatisation
- **Scheduler** : Tâches planifiées (quotidien, hebdo, intervalle)
- **Alertes** : Système de notifications
- **API REST** : Intégration externe via FastAPI

### 📊 Analytics Dashboard
- **KPIs** : Synthèses, vidéos, temps gagné
- **Graphiques Plotly** : Activité, sujets populaires
- **Distribution** : Types de synthèse, formats d'export

---

## ⚙️ Installation & Configuration

### Pré-requis
*   Python 3.10+
*   [FFmpeg](https://ffmpeg.org/download.html) installé et accessible dans le PATH
*   [Ollama](https://ollama.com/) installé avec un modèle téléchargé

### 1. Cloner et Installer
```bash
git clone https://github.com/votre-user/summaries_youtube.git
cd summaries_youtube

# Installer les dépendances
pip install -r requirements.txt

# Ou avec uv
uv sync
```

### 2. Configuration (.env)
```env
OUTPUT_DIR=src/summaries
MODEL=base              # Modèle Whisper
DEVICE=cuda             # cpu ou cuda
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral
FORMAT=md
```

---

## ▶️ Utilisation

### Interface Streamlit (recommandé)
```bash
streamlit run src/app.py
```
→ Ouvre sur `http://localhost:8501`

### API REST
```bash
cd src
python api.py
```
→ API sur `http://localhost:8001/docs`

---

## 📂 Structure du Projet

```
.
├── src/
│   ├── app.py           # Interface Streamlit (7 onglets)
│   ├── workflow.py      # Orchestrateur
│   ├── summarizer.py    # Logique IA
│   ├── transcriber.py   # Whisper
│   ├── downloader.py    # YouTube & Audio
│   ├── exporter.py      # PDF/HTML/MD/DOCX/PPTX
│   ├── database.py      # SQLite persistence
│   ├── analyzer.py      # Faits & comparaison
│   ├── scheduler.py     # Tâches planifiées
│   ├── api.py           # REST API (FastAPI)
│   ├── analytics.py     # Statistiques
│   └── data/            # SQLite DB & configs
└── README.md
```

## 📦 Dépendances Principales

| Package | Usage |
|---------|-------|
| streamlit | Interface |
| openai-whisper | Transcription |
| ollama | LLM local |
| python-docx | Export Word |
| python-pptx | Export PowerPoint |
| fastapi | API REST |
| plotly | Graphiques |

## ⚠️ Notes
*   **Performance** : GPU (CUDA) recommandé pour Whisper `medium` ou `large`
*   **Contexte** : Attention aux vidéos longues (limite contexte LLM)

---
*Fait avec ❤️ et beaucoup de café.*
